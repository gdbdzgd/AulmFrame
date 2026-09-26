# -*- coding: utf-8 -*-
"""
DXF Profile Parser for Aluminum Frame Generator.

Parses 2D DXF files, chains LINE/ARC/CIRCLE entities into closed contours
and identifies the outer profile boundary plus its inner cavities (T-slots,
centre bores, ...). Pure Python — safe to import without FreeCAD.
"""

import math
import os
from collections import defaultdict
from functools import lru_cache


def parse_dxf_tokens(path):
    """Parse DXF file into list of (code, value) tokens."""
    with open(path, 'r', errors='replace') as f:
        content = f.read()

    tokens = []
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        code = lines[i].strip()
        i += 1
        if i >= len(lines):
            break
        value = lines[i].strip()
        i += 1
        tokens.append((code, value))
    return tokens


def extract_entities(tokens):
    """Extract entities from DXF tokens."""
    entities = []
    in_entities = False
    current = None

    for code, value in tokens:
        if code == '2' and value == 'ENTITIES':
            in_entities = True
        elif code == '0' and value == 'ENDSEC' and in_entities:
            in_entities = False
        elif in_entities and code == '0':
            if current:
                entities.append(current)
            current = {'type': value}
        elif in_entities and current is not None:
            current[code] = value

    if current:
        entities.append(current)
    return entities


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _entity_segment(e):
    """Convert a DXF entity to a segment dict, or None if not supported.

    Segment dicts:
        {'kind': 'line', 'p0': (x, y), 'p1': (x, y)}
        {'kind': 'arc',  'p0': (x, y), 'p1': (x, y),
         'center': (cx, cy), 'radius': r,
         'start_angle': a0, 'extent': dA}   # angles in radians, CCW from p0
    """
    t = e.get('type')
    try:
        if t == 'LINE':
            return {
                'kind': 'line',
                'p0': (float(e['10']), float(e['20'])),
                'p1': (float(e['11']), float(e['21'])),
            }
        if t == 'ARC':
            cx, cy = float(e['10']), float(e['20'])
            r = float(e['40'])
            a0 = math.radians(float(e['50']))
            a1 = math.radians(float(e['51']))
            return {
                'kind': 'arc',
                'p0': (cx + r * math.cos(a0), cy + r * math.sin(a0)),
                'p1': (cx + r * math.cos(a1), cy + r * math.sin(a1)),
                'center': (cx, cy),
                'radius': r,
                'start_angle': a0,
                'extent': (a1 - a0) % (2 * math.pi),
            }
    except (KeyError, ValueError):
        return None
    return None


def _reverse_segment(s):
    """Return the same segment traversed in the opposite direction."""
    if s['kind'] == 'line':
        return {'kind': 'line', 'p0': s['p1'], 'p1': s['p0']}
    return {
        'kind': 'arc',
        'p0': s['p1'],
        'p1': s['p0'],
        'center': s['center'],
        'radius': s['radius'],
        'start_angle': (s['start_angle'] + s['extent']) % (2 * math.pi),
        'extent': (2 * math.pi) - s['extent'],
    }


def _point_key(p, tol):
    return (round(p[0] / tol), round(p[1] / tol))


def chain_loops(entities, tol=1e-4):
    """Chain LINE/ARC entities into closed loops.

    Parameters
    ----------
    entities : list
        Entities as returned by :func:`extract_entities`.
    tol : float
        Endpoint matching tolerance (mm).

    Returns
    -------
    loops : list of list of segment
        Each inner list is an ordered, closed chain of segments.
    circles : list of (cx, cy, r)
        Standalone CIRCLE entities (treated as closed loops).
    """
    segments = []
    circles = []
    for e in entities:
        if e.get('type') == 'CIRCLE':
            try:
                circles.append((float(e['10']), float(e['20']), float(e['40'])))
            except (KeyError, ValueError):
                pass
            continue
        seg = _entity_segment(e)
        if seg is not None:
            segments.append(seg)

    # Snap near-coincident endpoints onto shared canonical points so the
    # resulting chains are exactly connected (OCC wire building needs this).
    canon = {}

    def _snap(p):
        k = _point_key(p, tol)
        if k not in canon:
            canon[k] = p
        return canon[k]

    for s in segments:
        s['p0'] = _snap(s['p0'])
        s['p1'] = _snap(s['p1'])

    adjacency = defaultdict(list)
    for i, s in enumerate(segments):
        adjacency[_point_key(s['p0'], tol)].append((i, 'p0'))
        adjacency[_point_key(s['p1'], tol)].append((i, 'p1'))

    used = [False] * len(segments)
    loops = []
    for i0 in range(len(segments)):
        if used[i0]:
            continue
        used[i0] = True
        loop = [segments[i0]]
        start_key = _point_key(segments[i0]['p0'], tol)
        cur_key = _point_key(segments[i0]['p1'], tol)
        closed = True
        while cur_key != start_key:
            nxt = None
            for j, end in adjacency.get(cur_key, []):
                if not used[j]:
                    nxt = (j, end)
                    break
            if nxt is None:
                closed = False
                break
            j, end = nxt
            used[j] = True
            seg = segments[j]
            if end == 'p1':
                seg = _reverse_segment(seg)
            loop.append(seg)
            cur_key = _point_key(seg['p1'], tol)
        if closed and len(loop) >= 3:
            loops.append(loop)
    return loops, circles


def loop_points(loop):
    """Return the start point of every segment in a loop."""
    return [s['p0'] for s in loop]


def point_in_polygon(pt, poly):
    """Ray-casting point-in-polygon test."""
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            x_cross = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < x_cross:
                inside = not inside
    return inside


def select_contours(loops, circles):
    """Pick the outer boundary and the cavities nested inside it.

    The profile's outer contour is the closed loop built from the most
    segments (drawing annotations / title blocks are simple 4-segment
    rectangles). Cavities are loops/circles fully inside that boundary.

    Returns
    -------
    dict or None
        {'outer': loop, 'holes': [loop, ...], 'circles': [(x, y, r), ...]}
    """
    if not loops:
        return None
    outer = max(loops, key=len)
    poly = loop_points(outer)
    holes = [l for l in loops
             if l is not outer and point_in_polygon(l[0]['p0'], poly)]
    hole_circles = [c for c in circles
                    if point_in_polygon((c[0], c[1]), poly)]
    return {'outer': outer, 'holes': holes, 'circles': hole_circles}


def _bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _translate_loop(loop, dx, dy):
    def _t(p):
        return (p[0] - dx, p[1] - dy)

    out = []
    for s in loop:
        ns = dict(s)
        ns['p0'] = _t(s['p0'])
        ns['p1'] = _t(s['p1'])
        if 'center' in s:
            ns['center'] = _t(s['center'])
        out.append(ns)
    return out


def get_contours(path, tol=1e-4, center=True):
    """Parse a DXF file and return its profile contours.

    Results are cached per (path, mtime, tolerance, centering) so repeated
    builds (and the multiple beams sharing one profile) do not re-parse.

    Parameters
    ----------
    path : str
        DXF file path.
    tol : float
        Endpoint matching tolerance (mm).
    center : bool
        If True, translate the profile so its bounding-box centre is at
        the origin (DXF coordinates vary between drawings).

    Returns
    -------
    dict or None
        {'outer': loop, 'holes': [...], 'circles': [...],
         'width': float, 'height': float, 'center': (x, y)}
        or None when no closed contour could be extracted.
    """
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = 0.0
    return _get_contours_cached(os.path.abspath(path), mtime, tol, center)


@lru_cache(maxsize=128)
def _get_contours_cached(path, mtime, tol, center):
    del mtime  # cache key only
    entities = extract_entities(parse_dxf_tokens(path))
    loops, circles = chain_loops(entities, tol=tol)
    sel = select_contours(loops, circles)
    if not sel:
        return None

    outer = sel['outer']

    # Guard against picking up an annotation/title-block rectangle when the
    # real profile lives in an unsupported entity (e.g. a REGION proxy):
    # a 4-segment "outer" that leaves most entities unchained is not a profile.
    n_supported = sum(1 for e in entities if _entity_segment(e) is not None)
    n_chained = sum(len(l) for l in loops)
    if len(outer) <= 4 and n_supported and n_chained < 0.6 * n_supported:
        return None
    pts = loop_points(outer) + [s['p1'] for s in outer]
    x_min, y_min, x_max, y_max = _bbox(pts)
    cx = (x_min + x_max) / 2.0
    cy = (y_min + y_max) / 2.0
    width = x_max - x_min
    height = y_max - y_min

    holes = sel['holes']
    hole_circles = sel['circles']
    if center and (abs(cx) > tol or abs(cy) > tol):
        outer = _translate_loop(outer, cx, cy)
        holes = [_translate_loop(l, cx, cy) for l in holes]
        hole_circles = [(c[0] - cx, c[1] - cy, c[2]) for c in hole_circles]

    return {
        'outer': outer,
        'holes': holes,
        'circles': hole_circles,
        'width': width,
        'height': height,
        'center': (cx, cy),
    }


# ---------------------------------------------------------------------------
# Legacy helpers (bounding-box based)
# ---------------------------------------------------------------------------

def get_profile_bbox(entities):
    """Get bounding box of profile from entities (legacy heuristic)."""
    xs, ys = [], []
    lines = []

    for e in entities:
        if e.get('type') == 'LINE':
            try:
                x1 = float(e.get('10', 0))
                y1 = float(e.get('20', 0))
                x2 = float(e.get('11', 0))
                y2 = float(e.get('21', 0))
            except ValueError:
                continue
            # Filter extreme values
            if abs(x1) < 5000 and abs(y1) < 5000 and abs(x2) < 5000 and abs(y2) < 5000:
                xs.extend([x1, x2])
                ys.extend([y1, y2])
                lines.append((x1, y1, x2, y2))

    if not xs:
        return None

    # Find centroid
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)

    # Find distance of each point from centroid
    dists = [((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 for x, y in zip(xs, ys)]

    # Use 80% closest points for bbox
    dists_sorted = sorted(dists)
    cutoff = dists_sorted[int(len(dists_sorted) * 0.8)]

    # Filter lines within cutoff
    filtered = []
    for l in lines:
        x1, y1, x2, y2 = l
        d1 = ((x1 - cx) ** 2 + (y1 - cy) ** 2) ** 0.5
        d2 = ((x2 - cx) ** 2 + (y2 - cy) ** 2) ** 0.5
        if d1 <= cutoff and d2 <= cutoff:
            filtered.append(l)

    if filtered:
        x_coords = [l[0] for l in filtered] + [l[2] for l in filtered]
        y_coords = [l[1] for l in filtered] + [l[3] for l in filtered]
        return {
            'width': max(x_coords) - min(x_coords),
            'height': max(y_coords) - min(y_coords),
            'x_min': min(x_coords),
            'x_max': max(x_coords),
            'y_min': min(y_coords),
            'y_max': max(y_coords),
            'lines': filtered,
        }

    return {
        'width': max(xs) - min(xs),
        'height': max(ys) - min(ys),
        'x_min': min(xs),
        'x_max': max(xs),
        'y_min': min(ys),
        'y_max': max(ys),
        'lines': lines,
    }


# ---------------------------------------------------------------------------
# Profile lookup
# ---------------------------------------------------------------------------

_NAME_MAP = {
    '20x20': 'nfs5-2020.dxf',
    '30x30': 'LCF8-3030.dxf',
    '40x40': 'hfs8-4040.dxf',
    '60x60': None,
}


def default_dxf_dir():
    """Return the bundled DXF resource directory (portable, no absolutes)."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dxf')


def get_profile_for_size(size, dxf_dir=None):
    """Get profile info for a size string like '20x20', '30x30', etc.

    Only returns a result when a real closed contour can be extracted; the
    legacy bounding-box heuristic is deliberately not used as a fallback so
    that drawings whose geometry lives in unsupported entities (e.g. REGION
    proxies) are not mistaken for profiles.
    """
    if dxf_dir is None:
        dxf_dir = default_dxf_dir()

    size_lower = size.lower()
    for token in (u'方管', u'方', 'mm'):
        size_lower = size_lower.replace(token, '')
    size_lower = size_lower.strip()

    dxf_name = _NAME_MAP.get(size_lower)
    if not dxf_name:
        dxf_name = 'nfs5-%s.dxf' % size_lower.replace('x', '')

    dxf_path = os.path.join(dxf_dir, dxf_name)
    if not os.path.exists(dxf_path):
        return None

    contours = get_contours(dxf_path)
    if not contours:
        return None

    width = round(contours['width'], 1)
    height = round(contours['height'], 1)
    return {
        'profile': size,
        'width': width,
        'height': height,
        'profile_size': min(width, height),
        'dxf_file': dxf_path,
    }


def get_all_profiles(dxf_dir=None):
    """Scan the DXF resource directory for usable profile contours.

    Profile sizes are derived from the measured contour bounding box (mm,
    rounded) rather than the file name, which is more reliable across the
    MISUMI naming schemes.
    """
    profiles = []
    if dxf_dir is None:
        dxf_dir = default_dxf_dir()

    if not os.path.exists(dxf_dir):
        return profiles

    seen = {}
    for fname in sorted(os.listdir(dxf_dir)):
        if not fname.endswith('.dxf'):
            continue
        path = os.path.join(dxf_dir, fname)
        try:
            contours = get_contours(path)
        except Exception:
            continue
        if not contours:
            continue
        w = round(contours['width'], 1)
        h = round(contours['height'], 1)
        if w < 5 or h < 5:
            continue
        size = '%gx%g' % (w, h)
        info = {
            'profile': size,
            'width': w,
            'height': h,
            'profile_size': min(w, h),
            'dxf_file': path,
        }
        if size not in seen or len(contours['outer']) > seen[size]['_segs']:
            info['_segs'] = len(contours['outer'])
            seen[size] = info

    for size, info in seen.items():
        info.pop('_segs', None)
        profiles.append(info)
    return sorted(profiles, key=lambda p: (p['width'], p['height']))
