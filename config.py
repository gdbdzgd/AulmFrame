# -*- coding: utf-8 -*-
"""
Configuration module for Aluminum Frame Generator.
Separates data from code for easy customization and extension.

Note: all position/length formulas live in position_calculator.py
(single source of truth) — do NOT duplicate them here.
"""

# Profile definitions.
# Only regular sections are offered:
#   'square'      plain square/rectangular tube
#   'parametric'  generated standard T-slot series (see below)
# The old DXF-contour profiles (hfs8 / nefs8 / nfs5 / nfsl8 ...) produced
# irregular shapes and are intentionally NOT registered any more. The DXF
# parsing code remains available for reference only.
PROFILES = {
    '20x20 方管': {'type': 'square', 'w': 20, 'h': 20},
    '30x30 方管': {'type': 'square', 'w': 30, 'h': 30},
    '40x40 方管': {'type': 'square', 'w': 40, 'h': 40},
    '60x60 方管': {'type': 'square', 'w': 60, 'h': 60},
}

# Kept for reference; not used to register selectable profiles.
DXF_PROFILES = []

# Hole / tap specs for bolted connections (edit to match your fasteners):
#   beam_cross: cross-through hole on horizontal beams at Z-post connections
#   post_tap:   tapped hole on Z post ends (top & bottom)
HOLE_SPECS = {
    '20x20 方管': {'beam_cross': 'M5', 'post_tap': 'M6'},
    '30x30 方管': {'beam_cross': 'M6', 'post_tap': 'M8'},
    '40x40 方管': {'beam_cross': 'M8', 'post_tap': 'M10'},
    '60x60 方管': {'beam_cross': 'M10', 'post_tap': 'M12'},
}


def hole_specs_for_size(profile_size):
    """Pick fastener specs from the profile width (mm)."""
    ps = round(profile_size)
    if ps <= 20:
        return {'beam_cross': 'M5', 'post_tap': 'M6'}
    if ps <= 30:
        return {'beam_cross': 'M6', 'post_tap': 'M8'}
    if ps <= 40:
        return {'beam_cross': 'M8', 'post_tap': 'M10'}
    return {'beam_cross': 'M10', 'post_tap': 'M12'}


# Metric coarse taps: designation -> (tap drill diameter, clearance hole)
TAP_TABLE = [
    ('M3', 2.5, 3.4),
    ('M4', 3.3, 4.5),
    ('M5', 4.2, 5.5),
    ('M6', 5.0, 6.6),
    ('M8', 6.8, 9.0),
    ('M10', 8.5, 11.0),
    ('M12', 10.2, 13.5),
]
TAP_DRILL_BY_BORE_TOL = 0.5


def tap_for_center_bore(bore):
    """Match a profile centre bore to the tap whose pilot drill fits it.

    End-face tapping uses the profile's centre hole as the pilot, so the tap
    size must follow the real bore (e.g. Ø4.2 -> M5, Ø6.8 -> M8, Ø10.2 -> M12).
    Returns (designation, pilot_dia, clearance_dia) or None.
    """
    if not bore or bore <= 0:
        return None
    best = None
    for name, pilot, clearance in TAP_TABLE:
        diff = abs(pilot - bore)
        if diff <= TAP_DRILL_BY_BORE_TOL and (best is None or diff < best[0]):
            best = (diff, name, pilot, clearance)
    if best is None:
        return None
    return (best[1], best[2], best[3])


def _loop_equivalent_diameter(loop):
    """Approximate a closed loop by an equivalent circle diameter."""
    import math as _math
    area = 0.0
    pts = [s['p0'] for s in loop]
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    area = abs(area) / 2.0
    if area <= 0:
        return 0.0
    return 2.0 * _math.sqrt(area / _math.pi)


def profile_center_bore(profile):
    """Return the centre-hole diameter of a profile, or None if solid/unknown."""
    p = PROFILES.get(profile)
    if not p:
        return None

    if p['type'] == 'parametric':
        try:
            from .profiles.extrusion_profiles import EXTRUSIONS
            entry = EXTRUSIONS.get(p.get('series'))
            if entry:
                d1 = entry[2]
                return abs(d1) if d1 < 0 else None
        except Exception:
            return None

    if p['type'] == 'dxf':
        try:
            from .profiles.dxf_parser import get_contours
            contours = get_contours(p['dxf'])
            if not contours:
                return None
            # Prefer a circle centred near the origin
            best = None
            for cx, cy, r in contours.get('circles', []):
                if (cx * cx + cy * cy) ** 0.5 < 1.0 and r > 0:
                    best = max(best or 0.0, 2.0 * r)
            if best:
                return best
            # Else the innermost (smallest) cavity loop
            diams = [_loop_equivalent_diameter(h)
                     for h in contours.get('holes', [])]
            diams = [d for d in diams if d > 0]
            return min(diams) if diams else None
        except Exception:
            return None

    return None


def hole_specs_for_profile(profile):
    """Fastener sizes for a profile, derived from its real centre bore.

    Returns dict with keys: tap, tap_dia, tap_depth, clearance, source.
    Falls back to the size table when the profile has no measurable bore
    (solid rectangular beams).
    """
    p = PROFILES.get(profile) or {}
    bore = profile_center_bore(profile)
    match = tap_for_center_bore(bore)
    if match:
        tap, tap_dia, clearance = match
    else:
        size = p.get('w', 20)
        spec = hole_specs_for_size(size)
        tap = spec['post_tap']
        tap_dia = int(str(tap)[1:])
        clearance = dict((n, c) for n, _, c in TAP_TABLE).get(tap, tap_dia + 1.0)
    return {
        'tap': tap,
        'tap_dia': float(tap_dia),
        'tap_depth': round(tap_dia * 1.5),
        'clearance': float(clearance),
        'center_bore': bore,
    }


# Standard parametric T-slot families (generated, not parsed from DXF).
try:
    from .profiles.extrusion_profiles import EXTRUSIONS

    for _series, _entry in EXTRUSIONS.items():
        _w, _h = _entry[0], _entry[1]
        _size = '%gx%g' % (_w, _h)
        _key = '%s %s' % (_size, _series)
        PROFILES[_key] = {
            'type': 'parametric',
            'series': _series,
            'w': _w,
            'h': _h,
            'variant_of': _size,
        }
        HOLE_SPECS[_key] = hole_specs_for_size(_w)
except Exception:
    pass


# Document object names (referenced by expressions and cleanup logic)
OBJ_FRAME = 'Frame'
OBJ_PARAMS = 'Parameters'
OBJ_BOM = 'BOM'
OBJ_DIMENSIONS = 'Dimensions'
OBJ_X_BASE = 'XBeamBase'
OBJ_Y_BASE = 'YBeamBase'
OBJ_Z_BASE = 'ZPostBase'
OBJ_LAYER_COMPOUND = 'LayerCompound'
