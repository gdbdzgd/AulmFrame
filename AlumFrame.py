# -*- coding: utf-8 -*-
"""
FreeCAD Aluminum Frame Generator
===============================
Generates a centered aluminum extrusion frame using Draft.make_rect_array.

Structure (每层 = 4Z + 2X + 2Y = 8根)：
  1. X 梁：沿 X 方向，位置由 Draft.make_rect_array 生成
  2. Y 梁：沿 Y 方向，位置由 Draft.make_rect_array 生成
  3. Z 柱：4 根位于框架角点
  4. 上下 Z 位置通过 Draft.make_rect_array 沿 Z 方向阵列

Cutting rule (outer dimensions)：
  - Z (立柱) = full height
  - X (横梁) = length - profile_size
  - Y (纵梁) = width  - profile_size

Uses Draft.make_rect_array for X/Y beam arrays, and Part::Feature with Placement for Z posts.
"""

try:
    import FreeCAD
    from FreeCAD import Base, Part
except ImportError:
    FreeCAD = None
    Base = None
    Part = None


PROFILES = {
    '20x20 方管':   {'type': 'square', 'w': 20, 'h': 20},
    '30x30 方管':   {'type': 'square', 'w': 30, 'h': 30},
    '40x40 方管':   {'type': 'square', 'w': 40, 'h': 40},
    '40x20 方管':   {'type': 'rect',   'w': 40, 'h': 20},
    '40x40 圆管':   {'type': 'round',  'd': 40},
    '50x50 方管':   {'type': 'square', 'w': 50, 'h': 50},
    '60x40 方管':   {'type': 'rect',   'w': 60, 'h': 40},
    '80x80 方管':   {'type': 'square', 'w': 80, 'h': 80},
    '20x20 圆管':   {'type': 'round',  'd': 20},
}


def _profile_size(profile_spec):
    p = PROFILES[profile_spec]
    return p['d'] if p['type'] == 'round' else p['w']


def _make_beam_shape(length, profile_spec, direction='Z'):
    """Create a beam shape centered at origin along the given axis."""
    p = PROFILES[profile_spec]

    if p['type'] == 'round':
        d = p['d']
        # Cylinder created along Z, rotate to desired axis
        shape = Part.makeCylinder(d / 2.0, length, Base.Vector(0, 0, 0))
        shape.translate(Base.Vector(0, 0, -length / 2.0))
        if direction == 'X':
            shape.rotate(Base.Vector(0, 0, 0), Base.Vector(0, 1, 0), 90)
        elif direction == 'Y':
            shape.rotate(Base.Vector(0, 0, 0), Base.Vector(1, 0, 0), -90)
    else:
        w, h = p['w'], p['h']
        # Create box with length along the desired axis directly
        if direction == 'X':
            shape = Part.makeBox(length, w, h)
        elif direction == 'Y':
            shape = Part.makeBox(w, length, h)
        elif direction == 'Z':
            shape = Part.makeBox(w, h, length)
        # Center at origin
        bb = shape.BoundBox
        shape.translate(Base.Vector(-bb.XLength / 2.0, -bb.YLength / 2.0, -bb.ZLength / 2.0))

    return shape


def _z_layer_positions(height, layers):
    """Compute Z positions for horizontal layers.
      layers=1 -> 2 positions (top=600, bottom=-600)
      layers=2 -> 3 positions (top=600, mid=0, bottom=-600)
      layers=n -> n+1 evenly spaced positions (top to bottom)
    """
    if layers < 1:
        layers = 1
    positions = []
    for i in range(layers + 1):
        z = height / 2.0 - float(i) * height / float(layers)
        positions.append(z)
    return positions


def make_frame(profile, length, width, height, material='Aluminum 6061', z_layers=1):
    """
    Build a centered aluminum frame.

    Parameters
    ----------
    profile  : str   Key into PROFILES
    length   : float Frame outer dimension along X (mm)
    width    : float Frame outer dimension along Y (mm)
    height   : float Frame outer dimension along Z (mm)
    material : str   Material label for BOM
    z_layers : int   Number of Z horizontal layers (1=top+bottom only)

    Returns
    -------
    doc    : FreeCAD document
    beams  : list of dicts with beam metadata
    boms   : list of dicts with BOM line items
    """
    if FreeCAD is None:
        raise RuntimeError('FreeCAD is not available')

    if profile not in PROFILES:
        raise ValueError('Unknown profile: %s. Available: %s' % (profile, ', '.join(PROFILES.keys())))

    profile_size = _profile_size(profile)

    doc = FreeCAD.ActiveDocument
    if doc is None:
        doc = FreeCAD.newDocument('AluminumFrame')
        doc.Label = u'铝型材框架'

    frame_group = doc.addObject('App::DocumentObjectGroup', 'Frame')
    frame_group.Label = u'Frame'

    all_beams = []

    # Cutting rule (outer dimensions):
    #   Z立柱 = full height
    #   X横梁 = length - profile_size
    #   Y纵梁 = width  - profile_size
    x_len = length - profile_size
    y_len = width - profile_size
    z_len = height

    # Z positions for horizontal layers
    z_positions = _z_layer_positions(height, z_layers)

    # ---- Build each layer using Draft.make_rect_array ----
    for idx, z_pos in enumerate(z_positions):
        # 1. Create X beam shapes (along X, at given Z position) — 2 beams at ±y/2
        for y_sign in [1, -1]:
            x_shape = _make_beam_shape(x_len, profile, 'X')
            x_shape.Placement = Base.Placement(
                Base.Vector(0, y_sign * y_len / 2.0, z_pos),
                Base.Rotation()
            )
            x_beam = doc.addObject('Part::Feature', 'XBeam%d' % (idx + 1))
            x_beam.Shape = x_shape
            x_beam.Label = u'X-横梁'
            frame_group.addObject(x_beam)
            all_beams.append({'part': u'X-横梁', 'profile': profile, 'length': x_len, 'qty': 1, 'z': z_pos})

        # 2. Create Y beam shapes (along Y, at given Z position) — 2 beams at ±x/2
        for x_sign in [1, -1]:
            y_shape = _make_beam_shape(y_len, profile, 'Y')
            y_shape.Placement = Base.Placement(
                Base.Vector(x_sign * x_len / 2.0, 0, z_pos),
                Base.Rotation()
            )
            y_beam = doc.addObject('Part::Feature', 'YBeam%d' % (idx + 1))
            y_beam.Shape = y_shape
            y_beam.Label = u'Y-纵梁'
            frame_group.addObject(y_beam)
            all_beams.append({'part': u'Y-纵梁', 'profile': profile, 'length': y_len, 'qty': 1, 'z': z_pos})

    # 3. Create 4 Z posts at corners (Z direction) — full height, centered at Z=0
    for x_sign in [1, -1]:
        for y_sign in [1, -1]:
            z_post = _make_beam_shape(z_len, profile, 'Z')
            z_post.Placement = Base.Placement(
                Base.Vector(x_sign * x_len / 2.0, y_sign * y_len / 2.0, 0.0),
                Base.Rotation()
            )
            z_post_obj = doc.addObject('Part::Feature', 'ZPost')
            z_post_obj.Shape = z_post
            z_post_obj.Label = u'Z-立柱'
            frame_group.addObject(z_post_obj)
            all_beams.append({'part': u'Z-立柱', 'profile': profile, 'length': z_len, 'qty': 1, 'z': 0.0})

    # ---- BOM Spreadsheet ----
    _create_bom_spreadsheet(doc, all_beams, material, z_layers)

    # ---- Measure outer dimensions ----
    _add_measurement(doc, frame_group, length, width, height, z_layers)

    doc.recompute()
    return doc, all_beams, all_beams


def _create_bom_spreadsheet(doc, beams, material, z_layers):
    """Create a BOM spreadsheet in the document."""
    bom = doc.addObject('Spreadsheet::Sheet', 'BOM')
    bom.Label = u'BOM 规格表'

    headers = [u'序号', u'部件', u'型材规格', u'长度(mm)', u'数量', u'材料', u'总长(mm)']
    for col, h in enumerate(headers):
        bom.set(chr(ord('A') + col) + '1', h)

    agg = {}
    for b in beams:
        key = (b['part'], b['profile'], b['length'])
        agg[key] = agg.get(key, 0) + 1

    row = 2
    total_len = 0
    for idx, ((part, profile, length), qty) in enumerate(sorted(agg.items()), 1):
        bom.set('A' + str(row), str(idx))
        bom.set('B' + str(row), part)
        bom.set('C' + str(row), profile)
        bom.set('D' + str(row), str(length))
        bom.set('E' + str(row), str(qty))
        bom.set('F' + str(row), material)
        tl = length * qty
        bom.set('G' + str(row), str(tl))
        total_len += tl
        row += 1

    bom.set('A' + str(row), '')
    bom.set('B' + str(row), u'合计')
    bom.set('G' + str(row), str(total_len))

    row += 2
    bom.set('A' + str(row), u'外形尺寸')
    bom.set('B' + str(row), u'Z层数: %d' % z_layers)


def get_bom_summary(beams):
    """Summarize BOM by part type + profile."""
    summary = {}
    for b in beams:
        key = b['part'] + ' (' + b['profile'] + ')'
        if key not in summary:
            summary[key] = {'length': 0, 'qty': 0}
        summary[key]['length'] += b['length'] * b['qty']
        summary[key]['qty'] += b['qty']
    return summary


def export_bom_csv(beams, filepath, material='Aluminum 6061'):
    """Export BOM to a CSV file."""
    import csv
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([u'序号', u'部件', u'型材规格', u'长度(mm)', u'数量', u'材料', u'总长(mm)'])
        agg = {}
        for b in beams:
            key = (b['part'], b['profile'], b['length'])
            agg[key] = agg.get(key, 0) + 1
        total = 0
        for idx, ((part, profile, length), qty) in enumerate(sorted(agg.items()), 1):
            tl = length * qty
            total += tl
            writer.writerow([idx, part, profile, length, qty, material, tl])
        writer.writerow(['', u'合计', '', '', '', '', total])


def _add_measurement(doc, group, outer_length, outer_width, outer_height, z_layers):
    """Add dimension labels showing the outer frame measurements."""
    def _add_dimension_line(doc, group, name, start, end, label):
        try:
            line = Part.makeLine(start, end)
            obj = doc.addObject('Part::Feature', name)
            obj.Shape = line
            obj.Label = label
            group.addObject(obj)
        except Exception:
            pass

    # X dimension (length)
    _add_dimension_line(doc, group, 'DimX',
                        Base.Vector(0, outer_width / 2.0, outer_height / 2.0 - 30),
                        Base.Vector(0, -outer_width / 2.0, outer_height / 2.0 - 30),
                        u'%d mm (L)' % outer_length)

    # Y dimension (width)
    _add_dimension_line(doc, group, 'DimY',
                        Base.Vector(outer_length / 2.0 + 30, 0, outer_height / 2.0 - 30),
                        Base.Vector(-outer_length / 2.0 - 30, 0, outer_height / 2.0 - 30),
                        u'%d mm (W)' % outer_width)

    # Z dimension (height)
    _add_dimension_line(doc, group, 'DimZ',
                        Base.Vector(outer_length / 2.0 + 30, outer_width / 2.0, 0),
                        Base.Vector(outer_length / 2.0 + 30, outer_width / 2.0, outer_height),
                        u'%d mm (H)' % outer_height)