"""Bounded host file access and registered application discovery. No shell tool."""

import configparser
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import subprocess
import tempfile

from .memory import Memory


BLOCKED_PARTS = {'.ssh', '.gnupg', '.aws', '.azure', '.kube', '.codex', '.agents',
                 '.mozilla', '.thunderbird', '.password-store', '.docker', '.git',
                 'BraveSoftware', 'google-chrome', 'chromium', 'kwalletd', 'keyrings',
                 'gcloud', '1Password', 'Bitwarden'}
BLOCKED_NAMES = {'.git-credentials', '.netrc', '.npmrc', '.pypirc', '.bash_history',
                 '.zsh_history', 'credentials', 'credentials.json', 'secrets.json',
                 'passwords', 'passwords.txt', 'shadow', 'gshadow'}
BLOCKED_SUFFIXES = {'.key', '.pem', '.p12', '.pfx', '.kdbx', '.jks', '.sqlite', '.sqlite3', '.db'}
SEARCH_SKIP = {'.cache', '.tools', '.eve', '.venv', 'venv', '__pycache__', 'node_modules'}


def roots():
    # Broad owner-authorized PC reads, still subject to OS permissions and exclusions.
    return [Path('/')]


def _check(path, allowed_roots):
    if not any(path.is_relative_to(root) for root in allowed_roots):
        raise ValueError('Path is outside the permitted file roots')
    if set(path.parts) & BLOCKED_PARTS or path.name in BLOCKED_NAMES or path.name.startswith('.env'):
        raise ValueError('Credential stores and private runtime data are excluded')
    if path.suffix.lower() in BLOCKED_SUFFIXES:
        raise ValueError('Key stores and private database files are excluded')
    restricted = ['/proc', '/sys', '/dev', '/run', '/etc/ssl/private',
                  '/etc/NetworkManager/system-connections']
    if any(path.is_relative_to(Path(item)) for item in restricted) or path.is_relative_to(Memory().directory):
        raise ValueError('Private storage is excluded from general file tools')


def resolve(path, allowed_roots=None):
    raw = str(path)
    if any(character in raw for character in ('\0', '\n', '\r')) or '://' in raw:
        raise ValueError('Expected a local file path')
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute() or '..' in candidate.parts:
        raise ValueError('Use an absolute path or ~/path without parent traversal')
    permitted = roots() if allowed_roots is None else [Path(item) for item in allowed_roots]
    _check(candidate, permitted)
    canonical = candidate.resolve(strict=True)
    _check(canonical, permitted)
    return canonical


def open_path(path):
    """Open a canonical path without following replaced path components."""
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    if path == Path('/'):
        return directory
    try:
        for part in path.parts[1:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = next_fd
        return os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    finally:
        os.close(directory)


def list_files(path, offset=0, limit=60, allowed_roots=None):
    if not 0 <= offset <= 100000 or not 1 <= limit <= 100:
        raise ValueError('Invalid listing offset or limit')
    target = resolve(path, allowed_roots)
    fd = open_path(target)
    try:
        if not stat.S_ISDIR(os.fstat(fd).st_mode):
            raise ValueError('Path is not a directory')
        entries, truncated, index = [], False, 0
        with os.scandir(fd) as children:
            for child in children:
                if index < offset:
                    index += 1
                    continue
                if len(entries) >= limit:
                    truncated = True
                    break
                try:
                    info = child.stat(follow_symlinks=False)
                    kind = 'symlink' if child.is_symlink() else 'directory' if stat.S_ISDIR(info.st_mode) else 'file'
                    entries.append({'name': child.name, 'kind': kind, 'size': info.st_size})
                except OSError:
                    entries.append({'name': child.name, 'kind': 'unavailable'})
    finally:
        os.close(fd)
    return {'path': str(target), 'entries': entries, 'offset': offset,
            'next_offset': offset + len(entries) if truncated else None,
            'note': 'Filesystem order; concurrent changes can affect pagination. Listing is not permission to read protected entries.'}


def read_text(path, start_line=1, max_lines=60, allowed_roots=None):
    if not 1 <= start_line <= 100000 or not 1 <= max_lines <= 200:
        raise ValueError('Invalid line range')
    target = resolve(path, allowed_roots)
    fd = open_path(target)
    with os.fdopen(fd, 'rb') as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('Only regular text files can be read')
        if info.st_size > 262144:
            raise ValueError('Text reader is limited to files of 256 KiB or less')
        data = handle.read(262145)
    if len(data) > 262144 or b'\0' in data:
        raise ValueError('Binary or oversized file; a dedicated reader is required')
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError as error:
        raise ValueError('This reader supports UTF-8 text only') from error
    if any(ord(character) < 32 and character not in '\n\r\t' for character in text):
        raise ValueError('File contains binary control characters')
    lines = text.splitlines()
    selected = '\n'.join(lines[start_line - 1:start_line - 1 + max_lines])
    return {'path': str(target), 'start_line': start_line, 'total_lines': len(lines),
            'text': selected[:8000], 'truncated': len(selected) > 8000 or len(lines) > start_line - 1 + max_lines,
            'mtime_ns': info.st_mtime_ns, 'sha256': hashlib.sha256(data).hexdigest()}


def find_files(query, root, allowed_roots=None, limit=30):
    if not query.strip() or len(query) > 200:
        raise ValueError('Use a nonempty filename query up to 200 characters')
    target = resolve(root, allowed_roots)
    # Traverse via the same descriptor-safe directory interface as browsing.
    pending, matches, inspected, problems = [target], [], 0, []
    while pending:
        directory = pending.pop()
        try:
            offset = 0
            while True:
                page = list_files(directory, offset, 100, allowed_roots)
                for item in page['entries']:
                    inspected += 1
                    if inspected > 20000:
                        return {'matches': matches, 'truncated': True, 'detail': 'Search entry limit reached', 'problems': problems[:10]}
                    path = directory / item['name']
                    try:
                        resolve(path, allowed_roots)
                    except (ValueError, OSError):
                        continue
                    if query.casefold() in item['name'].casefold():
                        matches.append({'path': str(path), 'kind': item['kind']})
                        if len(matches) >= limit:
                            return {'matches': matches, 'truncated': True, 'problems': problems[:10]}
                    if item['kind'] == 'directory' and item['name'] not in SEARCH_SKIP:
                        pending.append(path)
                if page['next_offset'] is None:
                    break
                offset = page['next_offset']
        except (ValueError, OSError) as error:
            problems.append(str(error)[:200])
    return {'matches': matches, 'truncated': False, 'problems': problems[:10]}


def app_directories():
    return {'system': Path('/usr/share/applications'),
            'local-system': Path('/usr/local/share/applications'),
            'user': Path.home() / '.local/share/applications',
            'snap': Path('/var/lib/snapd/desktop/applications'),
            'flatpak': Path('/var/lib/flatpak/exports/share/applications'),
            'user-flatpak': Path.home() / '.local/share/flatpak/exports/share/applications'}


def applications(query='', directories=None):
    locations = app_directories() if directories is None else directories
    result = []
    for origin, directory in locations.items():
        for path in sorted(directory.glob('*.desktop')):
            try:
                info = path.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_size > 65536:
                    continue
                data = path.read_bytes()
                parser = configparser.ConfigParser(interpolation=None, strict=False)
                parser.read_string(data.decode('utf-8'))
                entry = parser['Desktop Entry']
                if entry.get('Type') != 'Application' or entry.get('Hidden', '').lower() == 'true':
                    continue
                name = entry.get('Name', path.stem)
                if query.casefold() not in (name + ' ' + path.name).casefold():
                    continue
                result.append({'app_id': origin + ':' + path.name, 'name': name,
                               'desktop_file': str(path), 'sha256': hashlib.sha256(data).hexdigest()})
            except (OSError, ValueError, KeyError, configparser.Error):
                continue
    return sorted(result, key=lambda item: item['name'].casefold())


def launch_application(app_id, expected_sha256, directories=None):
    # Only the eve application tool exposes launch, gated by always() approval.
    registry = {app['app_id']: app for app in applications(directories=directories)}
    if app_id not in registry or registry[app_id]['sha256'] != expected_sha256:
        raise ValueError('Application is missing or changed; list applications again before approving a launch')
    app = registry[app_id]
    # Launch a private copy of the approved bytes, not a mutable registry entry.
    data = Path(app['desktop_file']).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError('Application launcher changed before launch')
    snapshot_dir = Memory().directory / 'launchers' / expected_sha256
    snapshot_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    snapshot = snapshot_dir / Path(app['desktop_file']).name
    try:
        fd = os.open(snapshot, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
    except FileExistsError:
        if snapshot.is_symlink() or hashlib.sha256(snapshot.read_bytes()).hexdigest() != expected_sha256:
            raise ValueError('Stored application launch snapshot is invalid')
    result = subprocess.run(['gio', 'launch', str(snapshot)], capture_output=True,
                            text=True, timeout=8, check=False)
    if result.returncode:
        raise ValueError('Desktop rejected the launch: ' + result.stderr.strip()[:300])
    return {'app_id': app_id, 'status': 'launch_request_accepted',
            'detail': 'Desktop accepted the launch request; window visibility and readiness are not verified.'}


def read_screen_text(scope='full_screen'):
    """Capture one screen or active window on demand, OCR locally, delete image."""
    spectacle = shutil.which('spectacle')
    tesseract = shutil.which('tesseract')
    if not spectacle or not tesseract:
        raise ValueError('Screen reading needs KDE Spectacle and Tesseract installed.')
    with tempfile.TemporaryDirectory(prefix='burito-screen-') as directory:
        os.chmod(directory, 0o700)
        image = Path(directory) / 'capture.png'
        if scope not in ('full_screen', 'active_window'):
            raise ValueError('Screen reader accepts full_screen or active_window scope')
        area = '--activewindow' if scope == 'active_window' else '--fullscreen'
        capture = subprocess.run(
            [spectacle, '--background', '--nonotify', area, '--output', str(image)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        if capture.returncode or not image.is_file():
            detail = (capture.stderr or capture.stdout).strip()[:300]
            raise ValueError('Screen capture failed' + (': ' + detail if detail else '.'))
        if image.stat().st_size > 30 * 1024 * 1024:
            raise ValueError('Screen image exceeds the 30 MiB processing limit.')
        ocr = subprocess.run([tesseract, str(image), 'stdout', 'tsv'], capture_output=True,
                             text=True, timeout=30, check=False)
        if ocr.returncode:
            raise ValueError('Local OCR failed: ' + ocr.stderr.strip()[:300])
        rows = list(csv.DictReader(ocr.stdout.splitlines(), delimiter='\t'))
        page = next((row for row in rows if row.get('level') == '1'), {})
        try:
            page_width, page_height = int(page['width']), int(page['height'])
        except (KeyError, TypeError, ValueError):
            raise ValueError('Local OCR did not return screen dimensions.')
        grouped = {}
        for row in rows:
            if row.get('level') != '5' or not row.get('text', '').strip():
                continue
            try:
                key = (row['page_num'], row['block_num'], row['par_num'], row['line_num'])
                left, top = int(row['left']), int(row['top'])
                width, height = int(row['width']), int(row['height'])
                confidence = float(row['conf'])
            except (KeyError, TypeError, ValueError):
                continue
            line = grouped.setdefault(key, {'left': left, 'top': top, 'right': left + width,
                                             'bottom': top + height, 'words': [], 'confidence': []})
            line['left'] = min(line['left'], left)
            line['top'] = min(line['top'], top)
            line['right'] = max(line['right'], left + width)
            line['bottom'] = max(line['bottom'], top + height)
            line['words'].append((left, row['text'].strip()))
            if confidence >= 0:
                line['confidence'].append(confidence)
        positioned_lines = []
        redacted_count = 0
        for line in sorted(grouped.values(), key=lambda item: (item['top'], item['left'])):
            text = ' '.join(word for _, word in sorted(line['words']))
            text, redacted = redact_screen_secrets(text)
            redacted_count += redacted
            positioned_lines.append({
                'x_percent': [round(100 * line['left'] / page_width),
                              round(100 * line['right'] / page_width)],
                'y_percent': [round(100 * line['top'] / page_height),
                              round(100 * line['bottom'] / page_height)],
                'confidence_percent': round(sum(line['confidence']) / len(line['confidence']))
                    if line['confidence'] else None,
                'text': text,
            })
        compact_size = sum(len(line['text']) for line in positioned_lines)
        truncated = len(positioned_lines) > 250 or compact_size > 12000
        remaining, bounded_lines = 12000, []
        for line in positioned_lines[:250]:
            if remaining <= 0:
                break
            line['text'] = line['text'][:remaining]
            remaining -= len(line['text'])
            bounded_lines.append(line)
        return {'screen_size_px': [page_width, page_height], 'scope': scope,
                'lines': bounded_lines, 'truncated': truncated,
                'method': 'KDE Spectacle one-shot capture + local Tesseract OCR',
                'image_retained': False,
                'redacted_values': redacted_count,
                'note': ('OCR lines include approximate coordinates within the captured image. OCR can misread text and does not identify visual objects. '
                         + ('This was a capture of the active window, whose app identity was separately checked by KWin.'
                            if scope == 'active_window' else 'This was a full-screen capture and does not verify which application owns a region.'))}


def redact_screen_secrets(text):
    """Mask obvious credential assignments and common token formats in OCR output."""
    assignment = re.compile(
        r'(?i)\b((?:[A-Z0-9_.-]*(?:API[_ -]?KEY|ACCESS[_ -]?TOKEN|AUTHORIZATION|PASSWORD|CLIENT[_ -]?SECRET)[A-Z0-9_.-]*))'
        r'(\s*[:=]\s*)([^\s"\'`]+)'
    )
    text, assignments = assignment.subn(r'\1\2[REDACTED]', text)
    token = re.compile(r'\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{20,}|vck_[A-Za-z0-9_-]{16,})\b')
    text, tokens = token.subn('[REDACTED TOKEN]', text)
    return text, assignments + tokens


def reserve_screen_capture(session_id, turn_id, memory=None):
    """Atomically allow at most one requested capture for an Eve turn."""
    if not isinstance(session_id, str) or not session_id or len(session_id) > 300:
        raise ValueError('Screen capture needs a valid Eve session ID.')
    if not isinstance(turn_id, str) or not turn_id or len(turn_id) > 300:
        raise ValueError('Screen capture needs a valid Eve turn ID.')
    connection = (memory or Memory())._connect()
    try:
        with connection:
            connection.execute('''CREATE TABLE IF NOT EXISTS pc_screen_capture_turns (
                session_id TEXT NOT NULL, turn_id TEXT NOT NULL, reserved_at TEXT NOT NULL,
                PRIMARY KEY(session_id, turn_id))''')
            connection.execute(
                'DELETE FROM pc_screen_capture_turns WHERE reserved_at < ?',
                ((datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),),
            )
            connection.execute(
                'INSERT INTO pc_screen_capture_turns(session_id, turn_id, reserved_at) VALUES (?, ?, ?)',
                (session_id, turn_id, datetime.now(timezone.utc).isoformat()),
            )
    except sqlite3.IntegrityError as error:
        raise ValueError('One screen capture was already attempted in this turn. Answer using its result, or ask the owner to send a new message for another capture.') from error
    finally:
        connection.close()


def screen_capture_reserved(session_id, turn_id, memory=None):
    if not isinstance(session_id, str) or not session_id or not isinstance(turn_id, str) or not turn_id:
        return False
    connection = (memory or Memory())._connect()
    try:
        row = connection.execute(
            'SELECT 1 FROM pc_screen_capture_turns WHERE session_id = ? AND turn_id = ?',
            (session_id, turn_id),
        ).fetchone()
        return row is not None
    except sqlite3.OperationalError:
        return False
    finally:
        connection.close()


def dispatch(request, memory=None, allowed_roots=None):
    """Bridge used by model tools; read operations require no approval prompt."""
    action = request.get('action')
    try:
        if action == 'list':
            result = list_files(request['path'], request.get('offset', 0), request.get('limit', 60), allowed_roots)
        elif action == 'read':
            result = read_text(request['path'], request.get('start_line', 1), request.get('max_lines', 60), allowed_roots)
        elif action == 'find':
            result = find_files(request['query'], request['root'], allowed_roots)
        elif action == 'apps':
            all_apps = applications(request.get('query', ''))
            result = {'applications': all_apps[:60], 'truncated': len(all_apps) > 60}
        elif action == 'launch':
            # A bridge call is not itself proof of approval; require launcher-side gate too.
            if os.environ.get('BURITO_APPROVED_APP_LAUNCH') != '1':
                raise ValueError('Application launch requires the approved eve tool path')
            result = launch_application(request['app_id'], request['sha256'])
        elif action in ('windows', 'focus_window', 'inspect_window'):
            if os.environ.get('BURITO_DESKTOP_CONTROL') != '1':
                raise ValueError('Desktop window access is disabled for this chat')
            from . import windows
            if action == 'windows':
                result = windows.list_windows()
            else:
                if os.environ.get('BURITO_APPROVED_WINDOW_FOCUS') != '1':
                    raise ValueError('Window focus requires the approved eve tool path')
                if action == 'focus_window':
                    result = windows.focus_window(request.get('internalId'))
                else:
                    if os.environ.get('BURITO_SCREEN_READ') != '1':
                        raise ValueError('Active-window OCR is disabled for this chat')
                    if not screen_capture_reserved(request.get('session_id'), request.get('turn_id'), memory):
                        raise ValueError('Window capture was not reserved for this turn; request approval in a new message.')
                    result = windows.focus_and_read_window(request.get('internalId'))
        elif action == 'screen_read':
            if os.environ.get('BURITO_SCREEN_READ') != '1':
                raise ValueError('Screen reading was not enabled for this chat')
            if request.get('scope') not in ('full_screen', 'active_window'):
                raise ValueError('Screen reader only accepts the approved full_screen or active_window scope')
            if not screen_capture_reserved(request.get('session_id'), request.get('turn_id'), memory):
                raise ValueError('Screen capture was not reserved for this turn; request approval again in a new user message.')
            result = read_screen_text(request['scope'])
        elif action == 'screen_reserve':
            if os.environ.get('BURITO_SCREEN_READ') != '1':
                raise ValueError('Screen reading was not enabled for this chat')
            reserve_screen_capture(request.get('session_id'), request.get('turn_id'), memory)
            result = {'reserved': True}
        else:
            raise ValueError('Unknown PC access action')
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as error:
        audit(action, request, 'failed', memory)
        raise ValueError(str(error)) from error
    audit(action, request, 'success', memory)
    return result


def audit(action, request, outcome, memory=None):
    memory = memory if memory is not None else Memory()
    connection = memory._connect()
    try:
        with connection:
            connection.execute('''CREATE TABLE IF NOT EXISTS pc_access_audit (
                id INTEGER PRIMARY KEY, observed_at TEXT, action TEXT, target TEXT, outcome TEXT)''')
            if action in ('windows', 'focus_window', 'inspect_window'):
                # Window captions are transient response data and never enter the audit log.
                target = 'KWin window request'
            else:
                target = str(request.get('path') or request.get('root') or request.get('app_id') or request.get('title') or request.get('scope') or '')[:4096]
            connection.execute('INSERT INTO pc_access_audit(observed_at, action, target, outcome) VALUES (?, ?, ?, ?)',
                               (datetime.now(timezone.utc).isoformat(), str(action)[:30], target, outcome))
            connection.execute('DELETE FROM pc_access_audit WHERE id NOT IN (SELECT id FROM pc_access_audit ORDER BY id DESC LIMIT 2000)')
    finally:
        connection.close()
