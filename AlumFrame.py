# -*- coding: utf-8 -*-
"""
FreeCAD Aluminum Frame Generator
================================
Generates a centered aluminum extrusion frame using Draft.make_rect_array.

Structure:
  - X beams: horizontal beams along X direction, placed symmetrically at outer face of posts
  - Y beams: horizontal beams along Y direction, placed symmetrically at outer face of posts  
  - Z posts: vertical posts at 4 corners

All beams are positioned for seamless outer face connection.
Uses Draft.make_rect_array for creating beam arrays.
Uses Part::Box for parametric editing.
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


def _profile_height(profile_spec):
    """Get profile height (for rectangular profiles)."""
    p = PROFILES[profile_spec]
    if p['type'] == 'round':
        return p['d']
    else:
        return p['h']


def _make_beam_box(doc, length, profile_spec, direction='Z', name='Beam'):
    """Create a parametric beam using Part::Box.
    
    Returns the box object which has Length, Width, Height properties.
    """
    p = PROFILES[profile_spec]
    
    if p['type'] == 'round':
        # For round tubes, use cylinder (Part::Feature with cylinder shape)
        d = p['d']
        shape = Part.makeCylinder(d / 2.0, length, Base.Vector(0, 0, 0))
        shape.translate(Base.Vector(0, 0, -length / 2.0))
        if direction == 'X':
            shape.rotate(Base.Vector(0, 0, 0), Base.Vector(0, 1, 0), 90)
        elif direction == 'Y':
            shape.rotate(Base.Vector(0, 0, 0), Base.Vector(1, 0, 0), -90)
        
        obj = doc.addObject('Part::Feature', name)
        obj.Shape = shape
        # Add custom properties for round profile
        obj.addProperty('App::PropertyLength', 'BeamLength', 'Beam', 'Length of the beam')
        obj.addProperty('App::PropertyLength', 'ProfileDiameter', 'Beam', 'Profile diameter')
        obj.BeamLength = length
        obj.ProfileDiameter = d
        return obj
    else:
        # For rectangular profiles, use Part::Box
        w, h = p['w'], p['h']
        
        if direction == 'X':
            # Length along X, width along Y, height along Z
            obj = doc.addObject('Part::Box', name)
            obj.Length = length
            obj.Width = w
            obj.Height = h
            # Center the box
            obj.Placement = Base.Placement(Base.Vector(-length/2, -w/2, -h/2), Base.Rotation())
        elif direction == 'Y':
            # Width along X, length along Y, height along Z
            obj = doc.addObject('Part::Box', name)
            obj.Length = w
            obj.Width = length
            obj.Height = h
            # Center in XY, Z at 0
            obj.Placement = Base.Placement(Base.Vector(-w/2, -length/2, 0), Base.Rotation())
        elif direction == 'Z':
            # Width along X, height along Y, length along Z
            obj = doc.addObject('Part::Box', name)
            obj.Length = w
            obj.Width = h
            obj.Height = length
            # Start from Z=0 (bottom), XY at origin (array will handle positioning)
            obj.Placement = Base.Placement(Base.Vector(0, 0, 0), Base.Rotation())
        
        # Add custom properties for identification
        obj.addProperty('App::PropertyString', 'BeamType', 'Beam', 'Type of beam')
        obj.addProperty('App::PropertyString', 'ProfileSpec', 'Beam', 'Profile specification')
        obj.BeamType = direction
        obj.ProfileSpec = profile_spec
        
        return obj


def _z_layer_positions(height, layers):
    """Compute Z positions for horizontal layers (starting from Z=0).
      layers=1 -> 2 positions (top=height, bottom=0)
      layers=2 -> 3 positions (top=height, mid=height/2, bottom=0)
      layers=n -> n+1 evenly spaced positions from bottom to top
    """
    if layers < 1:
        layers = 1
    positions = []
    for i in range(layers + 1):
        z = float(i) * height / float(layers)
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
    profile_height = _profile_height(profile)

    doc = FreeCAD.ActiveDocument
    if doc is None:
        doc = FreeCAD.newDocument('AluminumFrame')
        doc.Label = u'铝型材框架'

    frame_group = doc.addObject('App::DocumentObjectGroup', 'Frame')
    frame_group.Label = u'Frame'

    all_beams = []

    # Cutting rule for seamless connection:
    # X beam length = outer_length - 2*profile_size (fits between inner faces of Z posts)
    # Y beam length = outer_width - 2*profile_size (fits between inner faces of Z posts)
    # Z post length = full height
    x_len = length - 2 * profile_size
    y_len = width - 2 * profile_size
    z_len = height

    # Z positions for horizontal layers
    z_positions = _z_layer_positions(height, z_layers)

    # ---- Create First Layer (Z=0) ----
    # First layer contains X beams and Y beams at Z=0
    # Other layers will be created by arraying this layer in Z direction
    
    # Create X beams for first layer
    x_base = _make_beam_box(doc, x_len, profile, 'X', 'XBeamBase')
    x_base.Placement.Base.z = 0
    
    # Array: 2 items along Y direction with spacing = width - profile_size
    y_spacing = width - profile_size
    x_array = Draft.make_array(x_base, 
                               Base.Vector(0, 0, 0),      # xvector (not used)
                               Base.Vector(0, y_spacing, 0), # yvector - spacing between inner faces
                               1, 2)                        # xnum=1, ynum=2
    x_array.Label = u'X-横梁'
    # First beam Y = -width/2 + profile_size/2 (aligned with Z post inner face)
    y_start = -width/2 + profile_size/2
    x_array.Placement = Base.Placement(Base.Vector(0, y_start, 0), Base.Rotation())
    frame_group.addObject(x_array)
    
    # Create Y beams for first layer
    y_base = _make_beam_box(doc, y_len, profile, 'Y', 'YBeamBase')
    
    # Array: 2 items along X direction with spacing = length - profile_size
    x_spacing = length - profile_size
    y_array = Draft.make_array(y_base,
                               Base.Vector(x_spacing, 0, 0),   # xvector - spacing between inner faces
                               Base.Vector(0, 0, 0),           # yvector (not used)
                               2, 1)                           # xnum=2, ynum=1
    y_array.Label = u'Y-纵梁'
    # First beam X = -length/2 + profile_size/2 (aligned with Z post inner face)
    x_start = -length/2 + profile_size/2
    y_array.Placement = Base.Placement(Base.Vector(x_start, 0, 0), Base.Rotation())
    frame_group.addObject(y_array)
    
    # ---- Create Compound from X and Y arrays ----
    # Use Part::Compound to combine X and Y beams (better than group for array operations)
    layer_compound = doc.addObject('Part::Compound', 'LayerCompound')
    layer_compound.Label = u'水平层复合体'
    layer_compound.Links = [x_array, y_array]
    frame_group.addObject(layer_compound)
    
    # ---- Array layers in Z direction ----
    # Array the compound in Z direction for multiple layers
    if z_layers >= 1:
        z_positions = _z_layer_positions(height, z_layers)
        z_spacing = z_positions[1] - z_positions[0] if len(z_positions) > 1 else height
        
        layer_array = Draft.make_array(layer_compound,
                                       Base.Vector(0, 0, 0),           # xvector (not used)
                                       Base.Vector(0, 0, 0),           # yvector (not used)
                                       1, 1)                           # xnum=1, ynum=1
        layer_array.Label = u'水平层阵列'
        # Use IntervalZ for Z spacing
        layer_array.IntervalZ = Base.Vector(0, 0, z_spacing)
        layer_array.NumberZ = len(z_positions)
        layer_array.Placement = Base.Placement(Base.Vector(0, 0, 0), Base.Rotation())
        frame_group.addObject(layer_array)
    
    # ---- Z Posts ----
    # Z posts at corners
    # Base position: (-20 - (length-profile_size)/2, -20 - (width-profile_size)/2, 0)
    # For 600x400 frame with 40x40 profile: (-300, -200, 0)
    z_base = _make_beam_box(doc, z_len, profile, 'Z', 'ZPostBase')
    
    # Array: 2x2 grid in XY plane with spacing = outer dimensions - profile_size
    z_array = Draft.make_array(z_base,
                               Base.Vector(length - profile_size, 0, 0),       # xvector = length - profile_size
                               Base.Vector(0, width - profile_size, 0),         # yvector = width - profile_size
                               2, 2)                                 # xnum, ynum
    z_array.Label = u'Z-立柱'
    frame_group.addObject(z_array)
    
    # Set placement after adding to group
    # First post at (-20 - (length-profile_size)/2, -20 - (width-profile_size)/2)
    z_array.Placement = Base.Placement(
        Base.Vector(-profile_size/2 - (length - profile_size)/2, -profile_size/2 - (width - profile_size)/2, 0), 
        Base.Rotation()
    )
    
    # Build BOM
    all_beams = []
    for z_pos in z_positions:
        all_beams.append({'part': u'X-横梁', 'profile': profile, 'length': x_len, 'qty': 2, 'z': z_pos})
        all_beams.append({'part': u'Y-纵梁', 'profile': profile, 'length': y_len, 'qty': 2, 'z': z_pos})
    all_beams.append({'part': u'Z-立柱', 'profile': profile, 'length': z_len, 'qty': 4, 'z': 0.0})

    # ---- BOM Spreadsheet ----
    _create_bom_spreadsheet(doc, all_beams, material, z_layers)

    # ---- Measure outer dimensions ----
    # Note: Using Std_Measure is not directly available via Python API
    # We'll create measurement annotations using TechDraw or simple text labels
    _add_measurement_annotations(doc, frame_group, length, width, height, z_layers)

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


def _add_measurement_annotations(doc, group, outer_length, outer_width, outer_height, z_layers):
    """Add dimension annotations using text labels at frame corners.
    
    Note: Std_Measure tool is a GUI feature not directly accessible via Python.
    We create visual dimension lines and text labels instead.
    """
    # Create a dimension annotation group
    dim_group = doc.addObject('App::DocumentObjectGroup', 'Dimensions')
    dim_group.Label = u'尺寸标注'
    group.addObject(dim_group)
    
    # X dimension (length) - along front bottom edge at Z=0
    _create_dimension_line(doc, dim_group, 'DimX',
                        Base.Vector(-outer_length/2, outer_width/2 + 20, 0),
                        Base.Vector(outer_length/2, outer_width/2 + 20, 0),
                        u'L=%d' % outer_length)

    # Y dimension (width) - along right bottom edge at Z=0
    _create_dimension_line(doc, dim_group, 'DimY',
                        Base.Vector(outer_length/2 + 20, -outer_width/2, 0),
                        Base.Vector(outer_length/2 + 20, outer_width/2, 0),
                        u'W=%d' % outer_width)

    # Z dimension (height) - along right back edge at X/Y offset
    _create_dimension_line(doc, dim_group, 'DimZ',
                        Base.Vector(outer_length/2 + 20, outer_width/2 + 20, 0),
                        Base.Vector(outer_length/2 + 20, outer_width/2 + 20, outer_height),
                        u'H=%d' % outer_height)


def _create_dimension_line(doc, group, name, start, end, label_text):
    """Create a dimension line with text label."""
    try:
        # Create the dimension line
        line = Part.makeLine(start, end)
        line_obj = doc.addObject('Part::Feature', name)
        line_obj.Shape = line
        line_obj.Label = label_text
        group.addObject(line_obj)
        
        # Create text label at midpoint
        mid = Base.Vector((start.x + end.x) / 2, (start.y + end.y) / 2, (start.z + end.z) / 2)
        # Add a small offset for text visibility
        text_pos = Base.Vector(mid.x, mid.y, mid.z + 10)
        
        # Store dimension info as document property for reference
        if not hasattr(doc, 'DimensionInfo'):
            doc.addProperty('App::PropertyString', 'DimensionInfo', 'Frame', 'Dimension annotations')
        doc.DimensionInfo = f"L={label_text} from ({start.x},{start.y},{start.z}) to ({end.x},{end.y},{end.z})"
        
    except Exception as e:
        pass
