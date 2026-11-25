#!/usr/bin/env python3
"""Read a bounded snapshot of visible Brave accessibility nodes via AT-SPI."""

import json
import re
import sys


MAX_WINDOWS = 8
MAX_NODES = 500
MAX_TEXT_NODES = 100
MAX_TEXT_BYTES = 8000


def _safe(call, default=None):
    try:
        return call()
    except Exception:
        return default


def _redact(text):
    text = re.sub(
        r'(?i)\b((?:[A-Z0-9_.-]*(?:API[_ -]?KEY|ACCESS[_ -]?TOKEN|AUTHORIZATION|PASSWORD|CLIENT[_ -]?SECRET)[A-Z0-9_.-]*))'
        r'(\s*[:=]\s*)([^\s"\'`]+)', r'\1\2[REDACTED]', text,
    )
    return re.sub(
        r'\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{20,}|vck_[A-Za-z0-9_-]{16,})\b',
        '[REDACTED TOKEN]', text,
    )


def _state(accessible, state, Atspi):
    state_set = _safe(accessible.get_state_set)
    return bool(state_set and _safe(lambda: state_set.contains(state), False))


def _role(accessible):
    return str(_safe(accessible.get_role_name, '') or '').casefold()


def _name(accessible):
    return str(_safe(accessible.get_name, '') or '').strip()


def _extents(accessible, Atspi):
    component = _safe(accessible.get_component_iface)
    if not component:
        return None
    rect = _safe(lambda: component.get_extents(Atspi.CoordType.SCREEN))
    if rect is None:
        return None
    return {'x': int(rect.x), 'y': int(rect.y), 'width': int(rect.width), 'height': int(rect.height)}


def _text(accessible):
    text_iface = _safe(accessible.get_text_iface)
    if not text_iface:
        return ''
    count = _safe(text_iface.get_character_count, 0) or 0
    if count <= 0:
        return ''
    value = _safe(lambda: text_iface.get_text(0, min(int(count), 2000)), '') or ''
    return _redact(str(value).strip())


def _node_summary(accessible, Atspi):
    return {
        'role': _role(accessible),
        'name': _name(accessible)[:300],
        'text': _text(accessible)[:1200],
        'showing': _state(accessible, Atspi.StateType.SHOWING, Atspi),
        'visible': _state(accessible, Atspi.StateType.VISIBLE, Atspi),
        'bounds': _extents(accessible, Atspi),
        'child_count': int(_safe(accessible.get_child_count, 0) or 0),
    }


def inspect_brave(Atspi):
    desktop = Atspi.get_desktop(0)
    if desktop is None:
        raise RuntimeError('AT-SPI returned no desktop object.')

    windows = []
    visited = 0
    text_bytes = 0

    def walk(node, path, depth, window_rows):
        nonlocal visited, text_bytes
        if node is None or visited >= MAX_NODES or depth > 24:
            return
        visited += 1
        role = _role(node)
        name = _name(node)
        showing = _state(node, Atspi.StateType.SHOWING, Atspi)
        visible = _state(node, Atspi.StateType.VISIBLE, Atspi)
        if showing or visible:
            value = _text(node)
            label = value or name
            if label and len(window_rows) < MAX_TEXT_NODES and text_bytes < MAX_TEXT_BYTES:
                label = label[:max(0, MAX_TEXT_BYTES - text_bytes)]
                text_bytes += len(label.encode('utf-8', errors='replace'))
                window_rows.append({
                    'path': path,
                    'role': role,
                    'name': name[:300],
                    'text': label[:2000],
                    'bounds': _extents(node, Atspi),
                })

        child_count = _safe(node.get_child_count, 0) or 0
        for index in range(min(int(child_count), 120)):
            if visited >= MAX_NODES or len(window_rows) >= MAX_TEXT_NODES or text_bytes >= MAX_TEXT_BYTES:
                break
            child = _safe(lambda: node.get_child_at_index(index))
            walk(child, f'{path}/{index}', depth + 1, window_rows)

    app_count = _safe(desktop.get_child_count, 0) or 0
    for app_index in range(min(int(app_count), 100)):
        app = _safe(lambda: desktop.get_child_at_index(app_index))
        if app is None:
            continue
        app_name = _name(app)
        if 'brave' not in app_name.casefold():
            continue
        child_count = _safe(app.get_child_count, 0) or 0
        for window_index in range(min(int(child_count), MAX_WINDOWS)):
            window = _safe(lambda: app.get_child_at_index(window_index))
            if window is None:
                continue
            window_name = _name(window)
            rows = []
            walk(window, f'app[{app_index}]/window[{window_index}]', 0, rows)
            bounds = _extents(window, Atspi)
            point_queries = []
            component = _safe(window.get_component_iface)
            if component and bounds and bounds['width'] > 0 and bounds['height'] > 0:
                for label, rx, ry in [('upper_page', 0.5, 0.25),
                                      ('center_page', 0.5, 0.5),
                                      ('lower_page', 0.5, 0.75)]:
                    x = bounds['x'] + int(bounds['width'] * rx)
                    y = bounds['y'] + int(bounds['height'] * ry)
                    try:
                        accessible = component.get_accessible_at_point(x, y, Atspi.CoordType.SCREEN)
                        point_queries.append({
                            'region': label,
                            'point': {'x': x, 'y': y},
                            'node': _node_summary(accessible, Atspi) if accessible else None,
                        })
                        if accessible and accessible != window:
                            walk(accessible, f'app[{app_index}]/window[{window_index}]/{label}', 1, rows)
                    except Exception as error:
                        point_queries.append({
                            'region': label,
                            'point': {'x': x, 'y': y},
                            'error': f'{type(error).__name__}: {str(error)[:180]}',
                        })
            windows.append({
                'application': app_name[:160],
                'window': window_name[:300],
                'active': _state(window, Atspi.StateType.ACTIVE, Atspi),
                'showing': _state(window, Atspi.StateType.SHOWING, Atspi),
                'bounds': bounds,
                'point_queries': point_queries,
                'nodes': rows,
            })
    return {'backend': 'AT-SPI2', 'windows': windows,
            'limits': {'nodes_visited': visited, 'text_nodes_per_window': MAX_TEXT_NODES,
                       'total_text_bytes': MAX_TEXT_BYTES},
            'scope': 'Visible/showing accessibility nodes from Brave only; read-only snapshot.'}


def main():
    try:
        import gi
        gi.require_version('Atspi', '2.0')
        from gi.repository import Atspi
        Atspi.init()
        result = inspect_brave(Atspi)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(f'AT-SPI probe failed ({type(error).__name__}): {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
