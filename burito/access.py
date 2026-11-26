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
import time
import secrets
from urllib.parse import parse_qs, quote_plus, urlsplit

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


def _approved_application_snapshot(app_id, expected_sha256, directories=None):
    registry = {app['app_id']: app for app in applications(directories=directories)}
    if app_id not in registry or registry[app_id]['sha256'] != expected_sha256:
        raise ValueError('Application is missing or changed; list applications again before approving a launch')
    app = registry[app_id]
    # Launch a private copy of the approved bytes, not a mutable registry entry.
    data = Path(app['desktop_file']).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError('Application launcher changed before launch')
    cache_home = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache')
    if not cache_home.is_absolute():
        raise ValueError('Application snapshot cache must be an absolute path')
    snapshot_root = cache_home / 'burito' / 'launchers'
    snapshot_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if snapshot_root.is_symlink() or snapshot_root.stat().st_uid != os.getuid():
        raise ValueError('Application snapshot cache must be owned by you and not a symlink')
    snapshot_root.chmod(0o700)
    snapshot_dir = snapshot_root / expected_sha256
    snapshot_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    snapshot = snapshot_dir / Path(app['desktop_file']).name
    try:
        fd = os.open(snapshot, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
    except FileExistsError:
        if snapshot.is_symlink() or hashlib.sha256(snapshot.read_bytes()).hexdigest() != expected_sha256:
            raise ValueError('Stored application launch snapshot is invalid')
    return app, snapshot


def launch_application(app_id, expected_sha256, directories=None):
    # Only the eve application tool exposes launch, gated by always() approval.
    app, snapshot = _approved_application_snapshot(app_id, expected_sha256, directories)
    result = subprocess.run(['gio', 'launch', str(snapshot)], capture_output=True,
                            text=True, timeout=8, check=False)
    if result.returncode:
        raise ValueError('Desktop rejected the launch: ' + result.stderr.strip()[:300])
    return {'app_id': app_id, 'status': 'launch_request_accepted',
            'detail': 'Desktop accepted the launch request; window visibility and readiness are not verified.'}


def brave_search_url(query):
    if not isinstance(query, str):
        raise ValueError('Brave search needs a text query.')
    query = query.strip()
    if not query or len(query) > 500 or any(ord(ch) < 32 or ord(ch) == 127 for ch in query):
        raise ValueError('Use a Brave search query of 1 to 500 printable characters.')
    return 'https://search.brave.com/search?q=' + quote_plus(query)


def brave_tab_count(max_age_seconds=15):
    """Read the fresh count-only snapshot written by the approved Brave extension."""
    runtime_dir = os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')
    snapshot = Path(runtime_dir) / 'burito-brave-tab-count.json'
    try:
        fd = os.open(snapshot, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError as error:
        raise ValueError('Brave tab count is unavailable; install and enable the Burito Brave extension first.') from error
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_size > 1024):
            raise ValueError('Brave tab count snapshot failed its local-file safety checks.')
        with os.fdopen(fd, 'r', encoding='utf-8') as handle:
            fd = None
            record = json.load(handle)
    finally:
        if fd is not None:
            os.close(fd)
    if not isinstance(record, dict):
        raise ValueError('Brave tab count snapshot is malformed.')
    count, updated_at = record.get('count'), record.get('updated_at')
    if (isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 10000
            or isinstance(updated_at, bool) or not isinstance(updated_at, (int, float))):
        raise ValueError('Brave tab count snapshot is malformed.')
    age = time.time() - updated_at
    if age < -5 or age > max_age_seconds:
        try:
            snapshot.unlink()
        except OSError:
            pass
        raise ValueError('Brave tab count is stale; check that the extension is connected in Brave.')
    return {'tab_count': count, 'observed_at': datetime.fromtimestamp(updated_at, timezone.utc).isoformat(),
            'scope': 'Open tabs in the Brave profile connected to Burito; only the count is shared.'}


def brave_tab_command(command, *, query=None, tab_id=None, expected_title=None, data=None, text=None, timeout=12):
    """Send one approved, short-lived command through the local Native Messaging host."""
    runtime_dir = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
    info = runtime_dir.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError('Brave command channel is not in a user-owned runtime directory.')
    request_id = secrets.token_hex(16)
    command_path = runtime_dir / 'burito-brave-command.json'
    response_path = runtime_dir / f'burito-brave-response-{request_id}.json'
    pending_path = runtime_dir / f'burito-brave-pending-{request_id}'
    if command_path.exists():
        try:
            if time.time() - command_path.stat().st_mtime > 20:
                command_path.unlink()
            else:
                raise ValueError('Another Brave tab request is still pending; wait and retry.')
        except FileNotFoundError:
            pass
    record = {'request_id': request_id, 'command': command, 'requested_at': time.time()}
    if query is not None:
        record['query'] = query
    if tab_id is not None:
        record.update({'tab_id': tab_id, 'expected_title': expected_title})
    if data is not None:
        record['data'] = data
    if text is not None:
        record['text'] = text
    payload = json.dumps(record, separators=(',', ':')).encode()
    temporary = runtime_dir / f'.burito-brave-command-{request_id}.tmp'
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.link(temporary, command_path)
    except FileExistsError as error:
        raise ValueError('Another Brave tab request is still pending; wait and retry.') from error
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            try:
                fd = os.open(response_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            except FileNotFoundError:
                time.sleep(0.15)
                continue
            try:
                meta = os.fstat(fd)
                if not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.getuid() or meta.st_mode & 0o077 or meta.st_size > 131072:
                    raise ValueError('Brave tab response failed its local-file safety checks.')
                with os.fdopen(fd, 'r', encoding='utf-8') as source:
                    fd = None
                    result = json.load(source)
            finally:
                if fd is not None:
                    os.close(fd)
            if not isinstance(result, dict) or result.get('request_id') != request_id:
                raise ValueError('Brave returned a mismatched tab request response.')
            if not result.get('ok'):
                raise ValueError(str(result.get('error') or 'Brave rejected the tab request.')[:300])
            return result.get('result')
        raise ValueError('Brave did not answer the tab request. Confirm the Burito extension is connected in Brave.')
    finally:
        for path in (command_path, response_path, pending_path):
            try:
                if path == command_path:
                    current = json.loads(path.read_text(encoding='utf-8'))
                    if current.get('request_id') == request_id:
                        path.unlink()
                else:
                    path.unlink()
            except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError):
                pass


def brave_find_tabs(query, limit=10):
    if not isinstance(query, str) or not query.strip() or len(query) > 100 or any(ord(c) < 32 for c in query):
        raise ValueError('Use a tab-title search of 1 to 100 printable characters.')
    result = brave_tab_command('find', query=query.strip())
    if not isinstance(result, dict) or not isinstance(result.get('tabs'), list):
        raise ValueError('Brave returned a malformed tab list.')
    tabs = result['tabs'][:limit]
    return {'matches': tabs, 'count': len(tabs), 'scope': 'Matching Brave tab labels only; URLs and page contents are not shared.'}


def brave_activate_tab(tab_id, expected_title):
    if isinstance(tab_id, bool) or not isinstance(tab_id, int) or tab_id < 0:
        raise ValueError('Use a tab ID returned by a recent Brave tab search.')
    if not isinstance(expected_title, str) or not expected_title or len(expected_title) > 512:
        raise ValueError('The exact expected tab title is required.')
    result = brave_tab_command('activate', tab_id=tab_id, expected_title=expected_title)
    if not isinstance(result, dict) or result.get('status') != 'activated':
        raise ValueError('Brave did not confirm that the requested tab became active.')
    return result


def brave_read_active_page():
    result = brave_tab_command('read_page')
    if (not isinstance(result, dict) or not isinstance(result.get('title'), str)
            or not isinstance(result.get('text'), str) or len(result['text']) > 9000
            or not isinstance(result.get('click_targets'), list) or len(result['click_targets']) > 50
            or not isinstance(result.get('video_targets', []), list) or len(result.get('video_targets', [])) > 20):
        raise ValueError('Brave returned a malformed page reading.')
    for target in [*result['click_targets'], *result.get('video_targets', [])]:
        if (not isinstance(target, dict) or not isinstance(target.get('label'), str)
                or not isinstance(target.get('role'), str) or len(target['label']) > 120):
            raise ValueError('Brave returned malformed visible page controls.')
    return {**result, 'scope': 'Visible text from the active Brave page; local only.'}


def brave_copy_text(text):
    if (not isinstance(text, str) or not text or len(text) > 5000
            or any(ord(ch) == 0 or (ord(ch) < 32 and ch not in '\n\r\t') for ch in text)):
        raise ValueError('Clipboard copy requires 1–5,000 printable characters.')
    result = brave_tab_command('copy_text', text=text, timeout=12)
    if not isinstance(result, dict) or result.get('status') != 'copied' or result.get('characters') != len(text):
        raise ValueError('Brave did not confirm the clipboard write.')
    return result


def clipboard_write_text(text):
    """Write exact approved text to the user's OS clipboard without reading it."""
    if (not isinstance(text, str) or not text or len(text) > 5000
            or any(ord(ch) == 0 or (ord(ch) < 32 and ch not in '\n\r\t') for ch in text)):
        raise ValueError('Clipboard copy requires 1–5,000 printable characters.')
    attempts = []
    writers = []
    wl_copy = shutil.which('wl-copy')
    xclip = shutil.which('xclip')
    if wl_copy:
        writers.append(([wl_copy], 'wl-copy'))
    if xclip:
        writers.append(([xclip, '-selection', 'clipboard', '-in'], 'xclip'))
    for command, method in writers:
        try:
            result = subprocess.run(command, input=text, capture_output=True,
                                    text=True, timeout=8, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            attempts.append(f'{method}: {str(error)[:120]}')
            continue
        if result.returncode == 0:
            return {'status': 'copied', 'characters': len(text), 'method': method,
                    'scope': 'Local system clipboard; write-only.'}
        attempts.append(f'{method}: {(result.stderr or "clipboard writer failed").strip()[:120]}')
    try:
        result = brave_copy_text(text)
        return {**result, 'method': 'Brave extension fallback',
                'scope': 'Local system clipboard via the connected Brave extension; write-only.'}
    except (ValueError, OSError) as error:
        attempts.append(f'Brave extension: {str(error)[:160]}')
    if attempts:
        detail = '; '.join(attempts)
        raise ValueError(f'No local clipboard write was confirmed ({detail}).')
    raise ValueError('No local clipboard writer is installed. Install wl-clipboard (wl-copy) or xclip, then retry.')


def brave_page_action(action, target=None, text=None, direction=None, amount=None, key=None, url=None):
    if action not in {'click_text', 'type_text', 'scroll', 'back', 'forward', 'press_key', 'navigate'}:
        raise ValueError('Unsupported browser action.')
    data = {'action': action}
    if action in {'click_text', 'type_text'}:
        if not isinstance(target, str) or not target.strip() or len(target) > 200:
            raise ValueError('A visible button/link label or field label is required.')
        data['target'] = target.strip()
    if action == 'type_text':
        if not isinstance(text, str) or len(text) > 2000 or any(ord(ch) < 32 and ch not in '\n\t' for ch in text):
            raise ValueError('Text entry must be printable and 2,000 characters or less.')
        data['text'] = text
    if action == 'scroll':
        if direction not in {'up', 'down'} or isinstance(amount, bool) or not isinstance(amount, int) or not 50 <= amount <= 2000:
            raise ValueError('Scroll direction must be up/down and amount 50–2,000 pixels.')
        data.update({'direction': direction, 'amount': amount})
    if action == 'press_key':
        if not isinstance(target, str) or not target.strip() or len(target) > 200 or key not in {'Enter', 'Tab', 'Escape'}:
            raise ValueError('Choose a visible field label and one of Enter, Tab, or Escape.')
        data.update({'target': target.strip(), 'key': key})
    if action == 'navigate':
        if not isinstance(url, str) or not url or len(url) > 2000 or any(ord(ch) < 32 for ch in url):
            raise ValueError('Use one printable HTTP or HTTPS URL up to 2,000 characters.')
        parsed = urlsplit(url)
        if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Browser navigation only accepts HTTP or HTTPS URLs without embedded credentials.')
        data['url'] = url
    result = brave_tab_command('page_action', data=data)
    expected_status = 'navigation_requested' if action == 'navigate' else 'completed'
    if not isinstance(result, dict) or result.get('status') != expected_status:
        raise ValueError('Brave did not confirm the browser action.')
    return result


def desktop_insert_text(internal_id, expected_caption, text):
    """Insert approved text at the caret in an exact focused AT-SPI text control."""
    if not isinstance(internal_id, str) or not re.fullmatch(r'[0-9a-fA-F-]{36}', internal_id):
        raise ValueError('Use an exact current KWin window ID.')
    if not isinstance(expected_caption, str) or not expected_caption or len(expected_caption) > 512:
        raise ValueError('Use the exact current KWin window caption.')
    if (not isinstance(text, str) or not text or len(text) > 5000
            or any(ord(ch) < 32 and ch not in '\n\r\t' for ch in text)):
        raise ValueError('Text insertion requires 1–5,000 characters and no control characters.')

    from . import windows
    snapshot = windows.list_windows()
    target = next((item for item in snapshot['windows']
                   if item.get('internalId') == internal_id
                   and item.get('caption') == expected_caption), None)
    if target is None:
        raise ValueError('The selected window is gone or its caption changed; list windows again.')
    windows.focus_window(internal_id)
    time.sleep(0.25)
    active = [item for item in windows.list_windows()['windows'] if item.get('active')]
    if len(active) != 1 or active[0].get('internalId') != internal_id:
        raise ValueError('KWin did not confirm that the selected destination window is active; no text was inserted.')

    try:
        import gi
        gi.require_version('Atspi', '2.0')
        from gi.repository import Atspi
    except (ImportError, ValueError) as error:
        raise ValueError('Native text insertion needs the system AT-SPI accessibility bindings.') from error

    init_result = Atspi.init()
    if init_result not in (0, 1):
        raise ValueError('The desktop accessibility bus could not be initialized.')
    desktop = Atspi.get_desktop(0)
    pending = [desktop]
    visited = 0
    matches = []
    while pending and visited < 6000:
        accessible = pending.pop()
        visited += 1
        try:
            states = accessible.get_state_set()
            if (states.contains(Atspi.StateType.FOCUSED)
                    and states.contains(Atspi.StateType.EDITABLE)):
                matches.append(accessible)
            child_count = accessible.get_child_count()
            for index in range(min(child_count, 200)):
                child = accessible.get_child_at_index(index)
                if child is not None:
                    pending.append(child)
        except Exception:
            continue
    if len(matches) != 1:
        raise ValueError('No unique focused editable text field was found in the approved window; no text was inserted.')
    try:
        editable = matches[0].queryEditableText()
        text_iface = matches[0].queryText()
        caret = text_iface.get_caret_offset()
        inserted = editable.insert_text(caret, text, len(text))
    except Exception as error:
        raise ValueError(f'AT-SPI could not insert text into the focused field ({type(error).__name__}).') from error
    if not inserted:
        raise ValueError('The focused field rejected text insertion.')
    return {'status': 'inserted', 'characters': len(text),
            'window': {'internalId': internal_id, 'caption': expected_caption},
            'method': 'AT-SPI insertion at the current caret; existing text is not replaced.'}


def launch_brave_search(query, directories=None):
    url = brave_search_url(query)
    parsed = urlsplit(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    if (parsed.scheme != 'https' or parsed.netloc != 'search.brave.com' or parsed.path != '/search'
            or set(params) != {'q'} or len(params['q']) != 1 or params['q'][0] != query.strip()
            or parsed.fragment):
        raise ValueError('Refusing an unexpected Brave search URL.')
    matches = [app for app in applications(query='Brave Origin', directories=directories)
               if Path(app['desktop_file']).name == 'brave-origin.desktop'
               and app['name'].casefold() == 'brave origin']
    if len(matches) != 1:
        raise ValueError('Could not uniquely identify the registered Brave Origin launcher.')
    app, snapshot = _approved_application_snapshot(matches[0]['app_id'], matches[0]['sha256'], directories)
    result = subprocess.run(['gio', 'launch', str(snapshot), url], capture_output=True,
                            text=True, timeout=8, check=False)
    if result.returncode:
        raise ValueError('Desktop rejected the approved Brave search request.')
    return {'app_id': app['app_id'], 'status': 'launch_request_accepted',
            'detail': 'Desktop accepted the approved search navigation; page readiness and results are not verified.'}


def search_brave_and_verify(query, request, memory=None):
    """Search in the owner's regular Brave profile and verify its active window with OCR."""
    try:
        launched = launch_brave_search(query)
        from . import windows
        deadline = time.monotonic() + 12
        target = None
        last_error = 'Brave has not reported the search window yet.'
        while time.monotonic() < deadline:
            try:
                snapshot = windows.list_windows()
                candidates = [item for item in snapshot.get('windows', [])
                              if 'brave' in str(item.get('resourceClass', '')).casefold()]
                active = [item for item in candidates if item.get('active') is True]
                if len(active) == 1:
                    target = active[0]
                    break
                if not active and len(candidates) == 1:
                    target = candidates[0]
                    break
                last_error = ('KWin reported multiple Brave windows and no unique active one.'
                              if len(candidates) > 1 else 'KWin has not reported a Brave window yet.')
            except Exception as error:
                last_error = f'{type(error).__name__}: {str(error)[:200]}'
            time.sleep(0.4)
        if target is None:
            return {**launched, 'verification': 'not_confirmed', 'detail':
                    'Brave accepted the query, but Burito could not identify one active Brave window to inspect. ' + last_error}
        if not begin_screen_capture(request.get('session_id'), request.get('turn_id'),
                                    request.get('call_id'), memory):
            return {**launched, 'verification': 'not_confirmed', 'window': target,
                    'detail': 'Brave accepted the query, but the one-capture-per-message reservation was unavailable.'}
        time.sleep(1.0)
        try:
            inspected = windows.focus_and_read_window(target.get('internalId'))
        except Exception as error:
            return {**launched, 'verification': 'not_confirmed', 'window': target,
                    'detail': f'Brave was identified, but focusing it or local OCR failed ({type(error).__name__}): {str(error)[:250]}'}
        capture = inspected.get('capture', {})
        lines = capture.get('lines', []) if isinstance(capture, dict) else []
        ocr_text = ' '.join(str(line.get('text', '')) for line in lines if isinstance(line, dict))
        compact_query = re.sub(r'[^a-z0-9]', '', query.casefold())
        compact_ocr = re.sub(r'[^a-z0-9]', '', ocr_text.casefold())
        page_lines = [line for line in lines if isinstance(line, dict)
                      and isinstance(line.get('y_percent'), list)
                      and len(line['y_percent']) == 2
                      and isinstance(line['y_percent'][0], (int, float))
                      and line['y_percent'][0] >= 18]
        if page_lines:
            verification = 'page_content_text_detected'
            detail = 'Local OCR detected text below the Brave browser chrome. This does not prove that a search-result entry or an accurate result was shown.'
        elif lines:
            verification = 'browser_chrome_text_only'
            detail = 'Local OCR detected text only in Brave browser chrome; search-result content was not confirmed visible.'
        else:
            verification = 'no_text_detected'
            detail = 'Brave was focused and captured, but local OCR recognized no text.'
        return {**launched, 'verification': verification,
                'query_visible_in_ocr': bool(compact_query and compact_query in compact_ocr),
                'page_content_text_lines': page_lines, 'window': inspected.get('window'),
                'capture': {
                    'screen_size_px': capture.get('screen_size_px'),
                    'scope': capture.get('scope'),
                    'truncated': capture.get('truncated'),
                    'note': capture.get('note'),
                },
                'detail': detail}
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        return {'status': 'page_read_failed', 'verification': 'not_confirmed',
                'detail': f'{type(error).__name__}: {str(error)[:400]}'}


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


def _ensure_screen_capture_schema(connection):
    connection.execute('''CREATE TABLE IF NOT EXISTS pc_screen_capture_turns (
        session_id TEXT NOT NULL, turn_id TEXT NOT NULL, reserved_at TEXT NOT NULL,
        PRIMARY KEY(session_id, turn_id))''')
    columns = {row[1] for row in connection.execute('PRAGMA table_info(pc_screen_capture_turns)')}
    if 'call_id' not in columns:
        connection.execute('ALTER TABLE pc_screen_capture_turns ADD COLUMN call_id TEXT')
    if 'capture_started' not in columns:
        connection.execute('ALTER TABLE pc_screen_capture_turns ADD COLUMN capture_started INTEGER NOT NULL DEFAULT 0')


def reserve_screen_capture(session_id, turn_id, call_id, memory=None):
    """Reserve one capture per turn; repeated approval callbacks for one Eve call are idempotent."""
    if not isinstance(session_id, str) or not session_id or len(session_id) > 300:
        raise ValueError('Screen capture needs a valid Eve session ID.')
    if not isinstance(turn_id, str) or not turn_id or len(turn_id) > 300:
        raise ValueError('Screen capture needs a valid Eve turn ID.')
    if not isinstance(call_id, str) or not call_id or len(call_id) > 300:
        raise ValueError('Screen capture needs a valid Eve tool call ID.')
    connection = (memory or Memory())._connect()
    try:
        with connection:
            _ensure_screen_capture_schema(connection)
            connection.execute(
                'DELETE FROM pc_screen_capture_turns WHERE reserved_at < ?',
                ((datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),),
            )
            connection.execute(
                '''INSERT OR IGNORE INTO pc_screen_capture_turns
                   (session_id, turn_id, reserved_at, call_id, capture_started)
                   VALUES (?, ?, ?, ?, 0)''',
                (session_id, turn_id, datetime.now(timezone.utc).isoformat(), call_id),
            )
            row = connection.execute(
                'SELECT call_id, capture_started FROM pc_screen_capture_turns WHERE session_id = ? AND turn_id = ?',
                (session_id, turn_id),
            ).fetchone()
            if row is None or row[0] != call_id:
                raise ValueError('One screen capture was already reserved for a different tool call in this turn.')
    finally:
        connection.close()


def begin_screen_capture(session_id, turn_id, call_id, memory=None):
    """Consume the turn reservation once, before touching the desktop capture API."""
    if (not isinstance(session_id, str) or not session_id or
            not isinstance(turn_id, str) or not turn_id or
            not isinstance(call_id, str) or not call_id):
        return False
    connection = (memory or Memory())._connect()
    try:
        with connection:
            _ensure_screen_capture_schema(connection)
            cursor = connection.execute(
                '''UPDATE pc_screen_capture_turns SET capture_started = 1
                   WHERE session_id = ? AND turn_id = ? AND call_id = ? AND capture_started = 0''',
                (session_id, turn_id, call_id),
            )
            return cursor.rowcount == 1
    except sqlite3.OperationalError:
        return False
    finally:
        connection.close()


def dispatch(request, memory=None, allowed_roots=None):
    """Bridge used by model tools; read operations require no approval prompt."""
    action = request.get('action')
    audit_connection = None
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
            audit_connection = (memory if memory is not None else Memory())._connect()
            # A bridge call is not itself proof of approval; require launcher-side gate too.
            if os.environ.get('BURITO_APPROVED_APP_LAUNCH') != '1':
                raise ValueError('Application launch requires the approved eve tool path')
            result = launch_application(request['app_id'], request['sha256'])
        elif action == 'browser_search':
            if os.environ.get('BURITO_BROWSER_SEARCH') != '1':
                raise ValueError('Brave search is disabled for this chat')
            if os.environ.get('BURITO_APPROVED_BROWSER_SEARCH') != '1':
                raise ValueError('Brave search requires the approved eve tool path')
            result = search_brave_and_verify(request.get('query'), request, memory)
        elif action == 'browser_search_reserve':
            if os.environ.get('BURITO_BROWSER_SEARCH') != '1':
                raise ValueError('Brave search is disabled for this chat')
            reserve_screen_capture(request.get('session_id'), request.get('turn_id'), request.get('call_id'), memory)
            result = {'reserved': True}
        elif action == 'browser_tabs':
            if os.environ.get('BURITO_BRAVE_TABS') != '1':
                raise ValueError('Brave tab-count access is disabled for this chat')
            if os.environ.get('BURITO_APPROVED_BROWSER_TABS') != '1':
                raise ValueError('Brave tab-count access requires the approved eve tool path')
            result = brave_tab_count()
        elif action in ('browser_find_tabs', 'browser_activate_tab'):
            if os.environ.get('BURITO_BRAVE_TABS') != '1':
                raise ValueError('Brave tab access is disabled for this chat')
            if os.environ.get('BURITO_APPROVED_BROWSER_TABS') != '1':
                raise ValueError('Brave tab access requires the approved eve tool path')
            if action == 'browser_find_tabs':
                result = brave_find_tabs(request.get('query'))
            else:
                result = brave_activate_tab(request.get('tab_id'), request.get('expected_title'))
        elif action in ('browser_read_page', 'browser_page_action', 'browser_copy_text'):
            if os.environ.get('BURITO_BROWSER_CONTROL') != '1':
                raise ValueError('Brave page access is disabled for this chat')
            if os.environ.get('BURITO_APPROVED_BROWSER_CONTROL') != '1':
                raise ValueError('Brave page access requires the approved eve tool path')
            if action == 'browser_read_page':
                result = brave_read_active_page()
            elif action == 'browser_copy_text':
                result = brave_copy_text(request.get('text'))
            else:
                result = brave_page_action(request.get('browser_action'), request.get('target'),
                                           request.get('text'), request.get('direction'),
                                           request.get('amount'), request.get('key'), request.get('url'))
        elif action in ('windows', 'focus_window', 'inspect_window'):
            if os.environ.get('BURITO_DESKTOP_CONTROL') != '1':
                raise ValueError('Desktop window access is disabled for this chat')
            from . import desktop, windows
            if action == 'windows':
                result = desktop.list_windows()
            else:
                if os.environ.get('BURITO_APPROVED_WINDOW_FOCUS') != '1':
                    raise ValueError('Window focus requires the approved eve tool path')
                if action == 'focus_window':
                    result = desktop.focus_window(request.get('internalId'))
                else:
                    if os.environ.get('BURITO_SCREEN_READ') != '1':
                        raise ValueError('Active-window OCR is disabled for this chat')
                    if not begin_screen_capture(request.get('session_id'), request.get('turn_id'), request.get('call_id'), memory):
                        raise ValueError('Window capture was already used or was not reserved for this tool call; send a new message to capture again.')
                    result = windows.focus_and_read_window(request.get('internalId'))
        elif action == 'desktop_insert_text':
            if os.environ.get('BURITO_DESKTOP_CONTROL') != '1':
                raise ValueError('Desktop text insertion is disabled for this chat')
            if os.environ.get('BURITO_APPROVED_DESKTOP_TEXT') != '1':
                raise ValueError('Desktop text insertion requires the approved eve tool path')
            result = desktop_insert_text(request.get('internalId'), request.get('expected_caption'), request.get('text'))
        elif action == 'clipboard_write_text':
            if os.environ.get('BURITO_DESKTOP_CONTROL') != '1':
                raise ValueError('Desktop clipboard writes are disabled for this chat')
            if os.environ.get('BURITO_APPROVED_CLIPBOARD_WRITE') != '1':
                raise ValueError('Clipboard writes require the approved eve tool path')
            result = clipboard_write_text(request.get('text'))
        elif action == 'screen_read':
            if os.environ.get('BURITO_SCREEN_READ') != '1':
                raise ValueError('Screen reading was not enabled for this chat')
            if request.get('scope') not in ('full_screen', 'active_window'):
                raise ValueError('Screen reader only accepts the approved full_screen or active_window scope')
            if not begin_screen_capture(request.get('session_id'), request.get('turn_id'), request.get('call_id'), memory):
                raise ValueError('Screen capture was already used or was not reserved for this tool call; send a new message to capture again.')
            result = read_screen_text(request['scope'])
        elif action == 'screen_reserve':
            if os.environ.get('BURITO_SCREEN_READ') != '1':
                raise ValueError('Screen reading was not enabled for this chat')
            reserve_screen_capture(request.get('session_id'), request.get('turn_id'), request.get('call_id'), memory)
            result = {'reserved': True}
        else:
            raise ValueError('Unknown PC access action')
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as error:
        try:
            if audit_connection is not None:
                audit(action, request, 'failed', memory, audit_connection)
            elif action != 'launch':
                audit(action, request, 'failed', memory)
        finally:
            if audit_connection is not None:
                audit_connection.close()
        raise ValueError(str(error)) from error
    try:
        audit(action, request, 'success', memory, audit_connection)
    finally:
        if audit_connection is not None:
            audit_connection.close()
    return result


def audit(action, request, outcome, memory=None, connection=None):
    memory = memory if memory is not None else Memory()
    owns_connection = connection is None
    connection = connection if connection is not None else memory._connect()
    try:
        with connection:
            connection.execute('''CREATE TABLE IF NOT EXISTS pc_access_audit (
                id INTEGER PRIMARY KEY, observed_at TEXT, action TEXT, target TEXT, outcome TEXT)''')
            if action in ('windows', 'focus_window', 'inspect_window', 'desktop_insert_text', 'clipboard_write_text'):
                # Window captions are transient response data and never enter the audit log.
                target = ('Approved native text insertion' if action == 'desktop_insert_text'
                          else 'Approved local clipboard write' if action == 'clipboard_write_text'
                          else 'Desktop window request')
            elif action == 'browser_search':
                # Search terms can contain sensitive user text; never persist them in the audit log.
                target = 'Approved Brave search'
            elif action in ('browser_tabs', 'browser_find_tabs', 'browser_activate_tab',
                            'browser_read_page', 'browser_page_action', 'browser_copy_text'):
                # Tab labels and the requested match are transient response data only.
                target = 'Approved Brave tab request'
            else:
                target = str(request.get('path') or request.get('root') or request.get('app_id') or request.get('title') or request.get('scope') or '')[:4096]
            connection.execute('INSERT INTO pc_access_audit(observed_at, action, target, outcome) VALUES (?, ?, ?, ?)',
                               (datetime.now(timezone.utc).isoformat(), str(action)[:30], target, outcome))
            connection.execute('DELETE FROM pc_access_audit WHERE id NOT IN (SELECT id FROM pc_access_audit ORDER BY id DESC LIMIT 2000)')
    finally:
        if owns_connection:
            connection.close()
