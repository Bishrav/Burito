"""Bounded host file access and registered application discovery. No shell tool."""

import configparser
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

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
            target = str(request.get('path') or request.get('root') or request.get('app_id') or '')[:4096]
            connection.execute('INSERT INTO pc_access_audit(observed_at, action, target, outcome) VALUES (?, ?, ?, ?)',
                               (datetime.now(timezone.utc).isoformat(), str(action)[:30], target, outcome))
            connection.execute('DELETE FROM pc_access_audit WHERE id NOT IN (SELECT id FROM pc_access_audit ORDER BY id DESC LIMIT 2000)')
    finally:
        connection.close()
