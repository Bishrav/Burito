#!/usr/bin/env python3
"""Brave Native Messaging host for count snapshots and approved tab requests."""

import json
import os
from pathlib import Path
import stat
import struct
import sys
import time


MAX_MESSAGE = 131072


def _state_path():
    runtime_dir = os.environ.get('XDG_RUNTIME_DIR')
    if not runtime_dir:
        raise RuntimeError('XDG_RUNTIME_DIR is unavailable')
    directory = Path(runtime_dir)
    info = directory.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise RuntimeError('XDG_RUNTIME_DIR is not owned by this user')
    return directory / 'burito-brave-tab-count.json'


def _runtime_dir():
    path = _state_path().parent
    return path


def _write_count(count):
    target = _state_path()
    data = json.dumps({'count': count, 'updated_at': time.time()}, separators=(',', ':')).encode()
    temporary = target.with_name(f'.{target.name}.{os.getpid()}.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
        os.chmod(target, 0o600)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _atomic_json(path, record):
    data = json.dumps(record, separators=(',', ':')).encode()
    if len(data) > MAX_MESSAGE:
        raise ValueError('Native messaging response is too large')
    temporary = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _take_command():
    path = _runtime_dir() / 'burito-brave-command.json'
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_size > 16384:
            return None
        with os.fdopen(fd, 'r', encoding='utf-8') as source:
            fd = None
            command = json.load(source)
    finally:
        if fd is not None:
            os.close(fd)
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    if not isinstance(command, dict) or not isinstance(command.get('request_id'), str):
        return None
    if len(command['request_id']) != 32 or any(ch not in '0123456789abcdef' for ch in command['request_id']):
        return None
    if time.time() - float(command.get('requested_at', 0)) > 15:
        return None
    kind = command.get('command')
    if kind == 'find':
        query = command.get('query')
        if not isinstance(query, str) or not query.strip() or len(query) > 100:
            return None
        _mark_pending(command['request_id'])
        return {'request_id': command['request_id'], 'command': kind, 'query': query}
    if kind == 'activate':
        tab_id, title = command.get('tab_id'), command.get('expected_title')
        if isinstance(tab_id, bool) or not isinstance(tab_id, int) or tab_id < 0 or not isinstance(title, str) or not title or len(title) > 512:
            return None
        _mark_pending(command['request_id'])
        return {'request_id': command['request_id'], 'command': kind, 'tab_id': tab_id, 'expected_title': title}
    if kind == 'read_page':
        _mark_pending(command['request_id'])
        return {'request_id': command['request_id'], 'command': kind}
    if kind == 'copy_text':
        text = command.get('text')
        if not isinstance(text, str) or not text or len(text) > 5000 or any(ord(ch) == 0 for ch in text):
            return None
        _mark_pending(command['request_id'])
        return {'request_id': command['request_id'], 'command': kind, 'text': text}
    if kind == 'page_action':
        data = command.get('data')
        allowed = {'click_text', 'type_text', 'scroll', 'back', 'forward', 'press_key', 'navigate'}
        if not isinstance(data, dict) or data.get('action') not in allowed:
            return None
        if data['action'] in {'click_text', 'type_text', 'press_key'}:
            target = data.get('target')
            if not isinstance(target, str) or not target or len(target) > 200:
                return None
        if data['action'] == 'type_text' and (not isinstance(data.get('text'), str) or len(data['text']) > 2000):
            return None
        if data['action'] == 'scroll' and (data.get('direction') not in {'up', 'down'}
                or isinstance(data.get('amount'), bool) or not isinstance(data.get('amount'), int)
                or not 50 <= data['amount'] <= 2000):
            return None
        if data['action'] == 'press_key' and (data.get('key') not in {'Enter', 'Tab', 'Escape'}
                or not isinstance(data.get('target'), str) or not data['target']):
            return None
        if data['action'] == 'navigate':
            url = data.get('url')
            if not isinstance(url, str) or not url or len(url) > 2000 or any(ord(ch) < 32 for ch in url):
                return None
        _mark_pending(command['request_id'])
        return {'request_id': command['request_id'], 'command': kind, 'data': data}
    return None


def _mark_pending(request_id):
    path = _runtime_dir() / f'burito-brave-pending-{request_id}'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w', encoding='ascii') as marker:
        marker.write(str(time.time()))


def _write_command_result(message):
    request_id = message.get('request_id')
    if not isinstance(request_id, str) or len(request_id) != 32 or any(ch not in '0123456789abcdef' for ch in request_id):
        raise ValueError('Invalid request ID')
    pending_path = _runtime_dir() / f'burito-brave-pending-{request_id}'
    try:
        pending_info = pending_path.stat()
    except FileNotFoundError:
        return
    if (not stat.S_ISREG(pending_info.st_mode) or pending_info.st_uid != os.getuid()
            or pending_info.st_mode & 0o077 or time.time() - pending_info.st_mtime > 15):
        try:
            pending_path.unlink()
        except FileNotFoundError:
            pass
        return
    if not isinstance(message.get('ok'), bool):
        raise ValueError('Invalid command result')
    record = {'request_id': request_id, 'ok': message['ok']}
    if message['ok']:
        result = message.get('result')
        if not isinstance(result, dict):
            raise ValueError('Invalid command result payload')
        record['result'] = result
    else:
        record['error'] = str(message.get('error', 'Brave rejected the request'))[:300]
    _atomic_json(_runtime_dir() / f'burito-brave-response-{request_id}.json', record)
    try:
        pending_path.unlink()
    except FileNotFoundError:
        pass


def _read_exact(stream, size):
    chunks = []
    remaining = size
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            if not chunks:
                return None
            raise EOFError('Native messaging frame ended early')
        chunks.append(chunk)
        remaining -= len(chunk)
    return b''.join(chunks)


def _send(response):
    payload = json.dumps(response, separators=(',', ':')).encode()
    sys.stdout.buffer.write(struct.pack('<I', len(payload)))
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def main():
    while True:
        header = _read_exact(sys.stdin.buffer, 4)
        if header is None:
            return 0
        length = struct.unpack('<I', header)[0]
        if not 0 < length <= MAX_MESSAGE:
            return 1
        raw = _read_exact(sys.stdin.buffer, length)
        try:
            message = json.loads(raw)
            if not isinstance(message, dict) or not isinstance(message.get('type'), str):
                raise ValueError('Invalid Native Messaging message')
            if message['type'] == 'tab_count':
                count = message.get('count')
                if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 10000:
                    raise ValueError('Invalid tab count')
                _write_count(count)
                _send({'ok': True})
            elif message['type'] == 'poll':
                command = _take_command()
                _send({'type': 'command', **command} if command else {'type': 'idle'})
            elif message['type'] == 'command_result':
                _write_command_result(message)
                _send({'ok': True})
            else:
                raise ValueError('Unsupported Native Messaging message')
        except (ValueError, OSError, RuntimeError, EOFError):
            # Never log browser data or protocol input.
            _send({'ok': False})


if __name__ == '__main__':
    raise SystemExit(main())
