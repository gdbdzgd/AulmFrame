# -*- coding: utf-8 -*-
"""
Parametric aluminum T-slot extrusion cross-sections.

Instead of relying on vendor DXF exports (often non-standard or missing), the
standard T-slot families are generated from a small parameter table. The
geometry recipe follows the well-known open-source NopSCADlib extrusion model
(https://github.com/nophead/NopSCADlib, GPL-3.0) as a reference; only the
public industry dimensions are used here and the construction is re-implemented
with FreeCAD's Part booleans.

Parameter tuple layout (NopSCADlib `extrusions.scad`):
    (Width, Height, center_hole, corner_hole, center_square,
     channel_width, channel_width_internal, tab_thickness, spar_thickness,
     fillet, recess)
Negative diameters are circles, positive are squares; recess is either False
or (half_width_y, depth_x).

FreeCAD is imported lazily so this module can be imported (and its table read)
without FreeCAD for tests.
"""

import math

# name: (W, H, d1, d2, sq, cw, cwi, t, st, f, recess)
EXTRUSIONS = {
    'E1515':  (15, 15, -3.3,   0.0,  5.5,  6.2,  9.5, 1.0, 0.9, 0.5, False),
    'E2020':  (20, 20, -4.2,   0.0,  8.0,  6.0, 12.0, 2.0, 2.0, 1.0, False),
    'E2020t': (20, 20, -5.0,   0.0,  7.8,  6.2, 11.0, 1.8, 1.5, 1.5, (7.2, 0.5)),
    'E3030':  (30, 30, -6.8,  -4.2, 12.0,  8.0, 16.5, 2.0, 2.0, 1.0, False),
    'E4040':  (40, 40, -10.5, -6.0, 15.0, 10.0, 20.0, 5.5, 3.0, 1.0, False),
    'E4040t': (40, 40, -10.0,  6.8, -16.0, 10.0, 20.0, 4.0, 2.4, 1.5, (12.0, 1.0)),
    'E2040':  (20, 40, -4.2,   0.0,  8.0,  6.0, 12.0, 2.0, 2.0, 1.0, False),
    'E2060':  (20, 60, -4.2,   0.0,  8.0,  6.0, 12.0, 2.0, 2.0, 1.0, False),
    'E2080':  (20, 80, -4.2,   0.0,  8.0,  6.0, 12.0, 2.0, 2.0, 1.0, False),
    'E3060':  (30, 60, -6.8,  -4.2, 12.0,  8.0, 16.5, 2.0, 2.0, 1.0, False),
    'E4080':  (40, 80, -10.5, -6.0, 15.0, 10.0, 20.0, 5.5, 3.0, 1.0, False),
}


def dimensions(series):
    """Return (width, height) for a series name."""
    entry = EXTRUSIONS[series]
    return entry[0], entry[1]


def is_square(series):
    w, h = dimensions(series)
    return abs(w - h) < 1e-6


# ---------------------------------------------------------------------------
# FreeCAD geometry construction
# ---------------------------------------------------------------------------

def _rect(x0, y0, x1, y1):
    import Part
    from FreeCAD import Base
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    return Part.Face(Part.makePolygon([Base.Vector(x, y, 0) for x, y in pts]))


def _circle(cx, cy, r):
    import Part
    from FreeCAD import Base
    return Part.Face(Part.Wire(Part.makeCircle(r, Base.Vector(cx, cy, 0))))


def _squircle(d, cx, cy):
    if d > 0:
        return _rect(cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2)
    if d < 0:
        return _circle(cx, cy, -d / 2)
    return None


def _corner(p):
    from FreeCAD import Base
    w, _h, _d1, d2, _sq, cw, cwi, t, _st, f, _ = p
    corner_size = (w - cw) / 2.0
    corner_square = (w - cwi) / 2.0
    c = _rect(f, 0, corner_size, t)
    c = c.fuse(_rect(0, f, t, corner_size))
    c = c.fuse(_circle(f, f, f))
    c = c.fuse(_rect(f, f, corner_square, corner_square))
    if d2:
        c = c.cut(_squircle(d2, corner_square / 2.0, corner_square / 2.0))
    c.translate(Base.Vector(-w / 2.0, -w / 2.0, 0))
    return c


def _cell(w, p):
    from FreeCAD import Base
    _, _, d1, _, sq, _cw, cwi, _t, st, _f, _ = p
    corner_square = (w - cwi) / 2.0
    center_square = abs(sq)
    c = _squircle(sq, 0, 0)
    if d1:
        c = c.cut(_squircle(d1, 0, 0))
    length = (w / math.sqrt(2.0) - corner_square * math.sqrt(2.0)
              - center_square / 2.0 + st * (1.0 + math.tan(math.radians(22.5))))
    for j in range(4):
        spar = _rect(center_square / 2.0 - st / 2.0, -st / 2.0,
                     center_square / 2.0 - st / 2.0 + length, st / 2.0)
        spar.rotate(Base.Vector(0, 0, 0), Base.Vector(0, 0, 1), 45 + 90 * j)
        c = c.fuse(spar)
    return c


def _center_section(w, p):
    _w, _h, _d1, _d2, _sq, cw, cwi, t, st, _f, _ = p
    corner_square = (w - cwi) / 2.0
    c = None
    for side in (-1, 1):
        cx = side * (w / 2.0 - t / 2.0)
        c = _rect(cx - t / 2.0, -(w - cw) / 2.0, cx + t / 2.0, (w - cw) / 2.0) if c is None \
            else c.fuse(_rect(cx - t / 2.0, -(w - cw) / 2.0, cx + t / 2.0, (w - cw) / 2.0))
        length = (corner_square + st * math.tan(math.radians(22.5))
                  - st / math.sqrt(2.0))
        for end in (-1, 1):
            cy = end * (corner_square - st / 2.0)
            cx2 = side * (w / 2.0 - length / 2.0)
            c = c.fuse(_rect(cx2 - length / 2.0, cy - st / 2.0,
                             cx2 + length / 2.0, cy + st / 2.0))
    return c


def _prism(face):
    from FreeCAD import Base
    return face.extrude(Base.Vector(0, 0, 1.0))


def cross_section_face(series):
    """Return a Part face (in the XY plane, centred at the origin) of the
    material cross-section, holes included. 3D booleans let overlapping prisms
    merge into one connected solid; its bottom face is the profile."""
    from FreeCAD import Base
    p = EXTRUSIONS[series]
    w, h = p[0], p[1]
    count = int(round(h / w - 1))

    solid = None

    def add(face):
        nonlocal solid
        v = _prism(face)
        solid = v if solid is None else solid.fuse(v)

    for i in range(count + 1):
        cell = _cell(w, p)
        cell.translate(Base.Vector(0, i * w + (w - h) / 2.0, 0))
        add(cell)

    for side in (-1, 1):
        y = side * (w - h) / 2.0
        for angle in (0, 90):
            c = _corner(p)
            c.rotate(Base.Vector(0, 0, 0), Base.Vector(0, 0, 1),
                     angle + (180 if side < 0 else 0))
            c.translate(Base.Vector(0, y, 0))
            add(c)

    for i in range(1, count + 1):
        cs = _center_section(w, p)
        cs.translate(Base.Vector(0, i * w - h / 2.0, 0))
        add(cs)

    recess = p[10]
    if recess:
        depth_x, half_y = recess
        for i in range(count + 1):
            y = i * w + (w - h) / 2.0
            for j in range(4):
                s = _rect(w / 2.0 - half_y, -depth_x / 2.0,
                          w / 2.0 + half_y, depth_x / 2.0)
                s.rotate(Base.Vector(0, 0, 0), Base.Vector(0, 0, 1), j * 90)
                s.translate(Base.Vector(0, y, 0))
                solid = solid.cut(_prism(s))

    solid = solid.removeSplitter()

    bottoms = [f for f in solid.Faces
               if abs(f.BoundBox.ZMin) < 1e-6 and abs(f.BoundBox.ZMax) < 1e-6
               and abs(abs(f.normalAt(0, 0).z) - 1.0) < 1e-6]
    if not bottoms:
        raise ValueError('cross-section produced no bottom face for %s' % series)
    return max(bottoms, key=lambda f: f.Area)


_FACE_CACHE = {}


def cached_face(series):
    """Return a cached copy of the cross-section face for a series."""
    if series not in _FACE_CACHE:
        _FACE_CACHE[series] = cross_section_face(series)
    return _FACE_CACHE[series].copy()
