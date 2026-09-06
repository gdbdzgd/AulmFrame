# -*- coding: utf-8 -*-
"""
FreeCAD Aluminum Frame Generator
================================
Generates a centered aluminum extrusion frame using Draft.make_rect_array.

Structure:
  - X beams: horizontal beams along X direction, placed symmetrically at ±Y/2
  - Y beams: horizontal beams along Y direction, placed symmetrically at ±X/2  
  - Z posts: vertical posts at 4 corners

All beams are centered at origin (symmetric placement).
Uses Draft.make_rect_array for creating beam arrays.

Cutting rule (outer dimensions):
  - Z (posts)    = full height
  - X (beams)    = length - profile_size
  - Y (beams)    = width  - profile_size
"""

try:
    import FreeCAD
    from FreeCAD import Base, Part
    import Draft
except ImportError:
    FreeCAD = None
    Base = None
    Part = None
    Draft = None


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
        shape = Part.makeCylinder(d / 2.0, length, Base.Vector(0, 0, 0))
        shape.translate(Base.Vector(0, 0, -length / 2.0))
        if direction == 'X':
            shape.rotate(Base.Vector(0, 0, 0), Base.Vector(0, 1, 0), 90)
        elif direction == 'Y':
            shape.rotate(Base.Vector(0, 0, 0), Base.Vector(1, 0, 0), -90)
    else:
        w, h = p['w'], p['h']
        if direction == 'X':
            shape = Part.makeBox(length, w, h)
        elif direction == 'Y':
            shape = Part.makeBox(w, length, h)
        elif direction == 'Z':
            shape = Part.makeBox(w, h, length)
        bb = shape.BoundBox
        shape.translate(Base.Vector(-bb.XLength / 2.0, -bb.YLength / 2.0, -bb.ZLength / 2.0))

    return shape


def _z_layer_positions(height, layers):
    """Compute Z positions for horizontal layers (symmetric around Z=0).
      layers=1 -> 2 positions (top=+H/2, bottom=-H/2)
      layers=2 -> 3 positions (top=+H/2, mid=0, bottom=-H/2)
      layers=n -> n+1 evenly spaced positions
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
    Build a centered aluminum frame using Draft.make_rect_array.

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

    if Draft is None:
        raise RuntimeError('Draft module is not available')

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

    # Correct cutting rule for seamless connection:
    # X beam length = outer_length - 2*profile_size (fits between inner faces of Z posts)
    # Y beam length = outer_width - 2*profile_size (fits between inner faces of Z posts)
    # Z post length = full height
    x_len = length - 2 * profile_size
    y_len = width - 2 * profile_size
    z_len = height

    # Z positions for horizontal layers
    z_positions = _z_layer_positions(height, z_layers)

    # ---- X Beams: use Draft.make_array ----
    # X beams span between inner faces of Z posts
    # Position: Y = ±(width/2 - profile_size) = inner face of Z post
    for idx, z_pos in enumerate(z_positions):
        x_shape = _make_beam_shape(x_len, profile, 'X')
        x_base = doc.addObject('Part::Feature', 'XBeamBase%d' % idx)
        x_base.Shape = x_shape
        x_base.Placement = Base.Placement(Base.Vector(0, 0, z_pos), Base.Rotation())
        
        # Array: 2 items along Y, spaced by 2*(width/2 - profile_size)
        y_spacing = width - 2 * profile_size  # distance between inner faces
        x_array = Draft.make_array(x_base, 
                                   Base.Vector(0, y_spacing, 0),  # xvector
                                   Base.Vector(0, 0, 0),         # yvector (not used)
                                   2, 1)                           # xnum, ynum
        x_array.Label = u'X-横梁-层%d' % (idx + 1)
        # First beam at Y = -(width/2 - profile_size), second at Y = +(width/2 - profile_size)
        x_array.Placement = Base.Placement(Base.Vector(0, -(width/2 - profile_size), 0), Base.Rotation())
        frame_group.addObject(x_array)
        
        all_beams.append({'part': u'X-横梁', 'profile': profile, 'length': x_len, 'qty': 2, 'z': z_pos})

    # ---- Y Beams: use Draft.make_array ----
    # Y beams span between inner faces of Z posts
    # Position: X = ±(length/2 - profile_size) = inner face of Z post
    for idx, z_pos in enumerate(z_positions):
        y_shape = _make_beam_shape(y_len, profile, 'Y')
        y_base = doc.addObject('Part::Feature', 'YBeamBase%d' % idx)
        y_base.Shape = y_shape
        y_base.Placement = Base.Placement(Base.Vector(0, 0, z_pos), Base.Rotation())
        
        # Array: 2 items along X, spaced by 2*(length/2 - profile_size)
        x_spacing = length - 2 * profile_size  # distance between inner faces
        y_array = Draft.make_array(y_base,
                                   Base.Vector(x_spacing, 0, 0),   # xvector
                                   Base.Vector(0, 0, 0),           # yvector (not used)
                                   2, 1)                           # xnum, ynum
        y_array.Label = u'Y-纵梁-层%d' % (idx + 1)
        # First beam at X = -(length/2 - profile_size), second at X = +(length/2 - profile_size)
        y_array.Placement = Base.Placement(Base.Vector(-(length/2 - profile_size), 0, 0), Base.Rotation())
        frame_group.addObject(y_array)
        
        all_beams.append({'part': u'Y-纵梁', 'profile': profile, 'length': y_len, 'qty': 2, 'z': z_pos})

    # ---- Z Posts: use Draft.make_array ----
    # Z posts at corners, outer faces aligned with frame outer dimensions
    # Position: X = ±(length/2 - profile_size/2), Y = ±(width/2 - profile_size/2)
    z_shape = _make_beam_shape(z_len, profile, 'Z')
    z_base = doc.addObject('Part::Feature', 'ZPostBase')
    z_base.Shape = z_shape
    z_base.Placement = Base.Placement(Base.Vector(0, 0, 0), Base.Rotation())
    
    # Array: 2x2 grid in XY plane
    # X spacing = length - profile_size (center-to-center)
    # Y spacing = width - profile_size (center-to-center)
    x_spacing = length - profile_size
    y_spacing = width - profile_size
    z_array = Draft.make_array(z_base,
                               Base.Vector(x_spacing, 0, 0),       # xvector
                               Base.Vector(0, y_spacing, 0),         # yvector
                               2, 2)                                 # xnum, ynum
    z_array.Label = u'Z-立柱'
    # First post at (-(length/2 - profile_size/2), -(width/2 - profile_size/2))
    z_array.Placement = Base.Placement(
        Base.Vector(-(length/2 - profile_size/2), -(width/2 - profile_size/2), 0), 
        Base.Rotation()
    )
    frame_group.addObject(z_array)
    
    all_beams.append({'part': u'Z-立柱', 'profile': profile, 'length': z_len, 'qty': 4, 'z': 0.0})

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
        agg[key] = agg.get(key, 0) + b.get('qty', 1)

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
        summary[key]['length'] += b['length'] * b.get('qty', 1)
        summary[key]['qty'] += b.get('qty', 1)
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
            agg[key] = agg.get(key, 0) + b.get('qty', 1)
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
