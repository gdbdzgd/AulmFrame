# -*- coding: utf-8 -*-
"""
Frame builder module for Aluminum Frame Generator.
Orchestrates the creation of all frame components.
"""

try:
    import FreeCAD
    from FreeCAD import Base
    import Draft
    import Part
except ImportError:
    FreeCAD = None
    Base = None
    Draft = None
    Part = None

from .config import (PROFILES, HOLE_SPECS, hole_specs_for_profile,
                     OBJ_FRAME, OBJ_PARAMS, OBJ_BOM,
                     OBJ_DIMENSIONS, OBJ_X_BASE, OBJ_Y_BASE, OBJ_Z_BASE,
                     OBJ_LAYER_COMPOUND)
from .position_calculator import FramePositionCalculator
from .beam_factory import BeamFactory


class FrameBuilder:
    """Builder class for creating aluminum frames."""
    
    # Parameters stored on the Frame group so frames can be edited later.
    # These also drive the geometry via expressions (see _bind_expressions).
    _PARAM_PROPS = [
        ('FrameProfile', 'App::PropertyString', 'profile'),
        ('FrameProfileSize', 'App::PropertyLength', 'profile_size'),
        ('FrameProfileHeight', 'App::PropertyLength', 'profile_height'),
        ('FrameLength', 'App::PropertyLength', 'length'),
        ('FrameWidth', 'App::PropertyLength', 'width'),
        ('FrameHeight', 'App::PropertyLength', 'height'),
        ('FrameMaterial', 'App::PropertyString', 'material'),
        ('FrameZLayers', 'App::PropertyInteger', 'z_layers'),
        ('FramePostAlongX', 'App::PropertyString', 'post_along_x'),
        ('FrameBeamVertical', 'App::PropertyString', 'beam_vertical'),
        ('FrameConnection', 'App::PropertyString', 'connection'),
    ]
    
    def __init__(self, doc=None):
        """Initialize frame builder.
        
        Parameters
        ----------
        doc : FreeCAD document, optional
            Target document. If None, build_frame creates a new one.
        """
        self.doc = doc
        self.beam_factory = BeamFactory(doc) if doc else None
        self.all_beams = []
        self._bases = {}
    
    def build_frame(self, profile, length, width, height, material='Aluminum 6061',
                    z_layers=1, doc=None, post_along_x='a', beam_vertical='b',
                    connection='end_tap', techdraw=True, hole_params=None):
        """Build complete aluminum frame.

        Parameters
        ----------
        profile : str
            Profile specification from PROFILES
        length : float
            Frame outer dimension along X (mm)
        width : float
            Frame outer dimension along Y (mm)
        height : float
            Frame outer dimension along Z (mm)
        material : str
            Material label for BOM
        z_layers : int
            Number of Z horizontal layers
        doc : FreeCAD document, optional
            Target document. If given, existing frame objects are removed
            and the frame is rebuilt in place. If None, a new document is
            created.
        post_along_x : {'a', 'b'}
            Which section dimension the Z post uses along frame X.
        beam_vertical : {'a', 'b'}
            Which section dimension the X/Y beams use vertically.

        Returns
        -------
        doc : FreeCAD document
        beams : list
            List of beam metadata
        """
        # Validate inputs
        if profile not in PROFILES:
            raise ValueError(f'Unknown profile: {profile}. Available: {", ".join(PROFILES.keys())}')

        if FreeCAD is None or Draft is None:
            raise RuntimeError('FreeCAD or Draft module is not available')

        post_along_x = post_along_x if post_along_x in ('a', 'b') else 'a'
        beam_vertical = beam_vertical if beam_vertical in ('a', 'b') else 'b'
        self._orientation = {'post_along_x': post_along_x,
                            'beam_vertical': beam_vertical}
        self._connection = connection or 'end_tap'
        self._connection_notes = {}
        self._hardware = []
        self._techdraw = bool(techdraw)
        self._hole_params = dict(hole_params or {})

        doc = doc or self.doc
        if doc is None:
            doc = FreeCAD.newDocument('AluminumFrame')
            doc.Label = u'铝型材框架'
        else:
            # In-place update: remove the previous frame first
            self._remove_existing_frame(doc)

        self.doc = doc
        self.beam_factory = BeamFactory(doc)
        self.all_beams = []
        self._bases = {}
        
        # Get profile cross-section dimensions
        p = PROFILES[profile]
        if p['type'] == 'round':
            profile_size = p['d']
            profile_height = p['d']
        else:
            profile_size = p['w']
            profile_height = p.get('h', p['w'])

        # Create position calculator (orientation-aware)
        calc = FramePositionCalculator(length, width, height, profile_size,
                                       profile_height,
                                       self._orientation['post_along_x'],
                                       self._orientation['beam_vertical'])

        # Draft.make_array creates objects in the ACTIVE document, so the
        # target document must be active during the build; restore after.
        prev_active = FreeCAD.ActiveDocument
        FreeCAD.setActiveDocument(doc.Name)
        try:
            self._build_into_doc(doc, calc, profile, profile_size, profile_height,
                                 length, width, height, material, z_layers)
        finally:
            if prev_active is not None:
                FreeCAD.setActiveDocument(prev_active.Name)

        self.doc.recompute()

        # A single pass may leave Part::Cut shapes unbuilt (they depend on the
        # sketch-driven extrusions); recompute until the bases are real.
        for _ in range(3):
            if all((self._bases.get(k) is None
                    or len(self._bases[k].Shape.Faces) > 0)
                   for k in ('X', 'Y', 'Z')):
                break
            self.doc.recompute()

        # ========== Measurements + TechDraw (need computed shapes) ==========
        try:
            self._create_measurements(*self._measure_args)
        except Exception:
            pass
        if self._techdraw:
            try:
                self._create_techdraw(*self._techdraw_args)
            except Exception:
                pass

        return self.doc, self.all_beams

    def _build_into_doc(self, doc, calc, profile, profile_size, profile_height,
                        length, width, height, material, z_layers):
        """Create all frame objects in doc (doc must be the active document)."""
        # Parameters spreadsheet first: single source of truth, lives OUTSIDE
        # the Frame group (objects inside the group cannot reference the
        # group itself - that would be a cyclic dependency)
        self._create_params_sheet(profile, length, width, height,
                                  material, z_layers, profile_size, profile_height,
                                  self._orientation, self._connection)

        # Create main frame group
        frame_group = doc.addObject('App::DocumentObjectGroup', OBJ_FRAME)
        frame_group.Label = u'Frame'

        # Store parameters on the group for identification / editing
        self._store_params(frame_group, profile, length, width, height,
                           material, z_layers, profile_size, profile_height,
                           self._orientation, self._connection)

        # ========== Create Horizontal Layer (X + Y Beams) ==========
        layer_compound = self._create_horizontal_layer(calc, profile, frame_group)

        # ========== Array Horizontal Layer in Z Direction ==========
        self._array_horizontal_layer(calc, layer_compound, z_layers, frame_group)

        # ========== Create Z Posts ==========
        self._create_z_posts(calc, profile, height, frame_group)

        # ========== Organise editable profile sketches ==========
        for key, label in (('X', u'X-横梁'), ('Y', u'Y-纵梁'),
                           ('Z', u'Z-立柱')):
            base = self._bases.get(key)
            sketch = self.doc.getObject(('XBeamBase' if key == 'X' else
                                         'YBeamBase' if key == 'Y' else
                                         'ZPostBase') + '_Sketch')
            if sketch is not None:
                sketch.Label = label + u' 截面'
                try:
                    frame_group.addObject(sketch)
                except Exception:
                    pass
                try:
                    if FreeCADGui is not None:
                        FreeCADGui.ActiveDocument.getObject(
                            sketch.Name).Visibility = True
                except Exception:
                    pass
            if base is not None:
                base.Label = label + u'(阵列源)'

        # ========== Connection holes ==========
        self._apply_connections(calc, length, width, height, z_layers,
                                profile, profile_size, profile_height)
        # Persist the machining notes so drawings can be regenerated later.
        if not hasattr(frame_group, 'FrameHoleNotes'):
            frame_group.addProperty('App::PropertyString', 'FrameHoleNotes',
                                    'AlumFrame', u'打孔说明(内部)')
        try:
            import json
            frame_group.FrameHoleNotes = json.dumps(
                self._connection_notes, ensure_ascii=False)
            if not hasattr(frame_group, 'FrameHoleAxis'):
                frame_group.addProperty('App::PropertyString', 'FrameHoleAxis',
                                        'AlumFrame', u'孔轴位置(内部)')
            frame_group.FrameHoleAxis = json.dumps(
                getattr(self, '_hole_axis', {}), ensure_ascii=False)
        except Exception:
            pass

        # ========== Bind expressions (true parametric) ==========
        self._bind_expressions(frame_group)

        # ========== Create BOM ==========
        self._create_bom(material, z_layers, frame_group, profile)

        # Measurements and drawings are created after the final recompute
        # (sketch-driven beams and Part::Cut need computed shapes first).
        self._measure_args = (frame_group, length, width, height, z_layers,
                              profile_size, profile_height)
        self._techdraw_args = (profile, material, z_layers)
    
    def _create_params_sheet(self, profile, length, width, height,
                             material, z_layers, profile_size, profile_height,
                             orientation, connection='end_tap'):
        """Create the Parameters spreadsheet (single source of truth).

        Cell map: B1 profile, B2 profile size (a), B3 length, B4 width,
        B5 height, B6 z layers, B7 material, B8 profile height (b),
        B9 post orientation, B10 beam orientation.
        """
        sh = self.doc.addObject('Spreadsheet::Sheet', OBJ_PARAMS)
        sh.Label = u'框架参数'
        rows = [
            (u'型材规格', profile),
            (u'型材宽度', '%g mm' % profile_size),
            (u'长度 X', '%g mm' % length),
            (u'宽度 Y', '%g mm' % width),
            (u'高度 Z', '%g mm' % height),
            (u'Z层数', str(int(z_layers))),
            (u'材料', material),
            (u'型材高度Y', '%g mm' % profile_height),
            (u'立柱方向', orientation.get('post_along_x', 'a')),
            (u'横梁竖直', orientation.get('beam_vertical', 'b')),
            (u'连接方式', connection),
        ]
        for i, (label, value) in enumerate(rows, 1):
            sh.set('A%d' % i, label)
            sh.set('B%d' % i, value)
        return sh

    def _bind_expressions(self, frame_group):
        """Bind geometry to the Parameters spreadsheet (true parametric).

        Editing e.g. Parameters.B3 (length) updates boxes, arrays, frame
        group properties and measurements live. References go to the
        spreadsheet (outside the Frame group), never to the group itself.
        Only square Part::Box beams are driven by expressions; generated /
        DXF profiles are pre-built solids and stay static.
        """
        P = OBJ_PARAMS
        ps = P + '.B2'   # profile size (X)
        ph = P + '.B8'   # profile height (Y)
        L = P + '.B3'    # length
        W = P + '.B4'    # width
        H = P + '.B5'    # height
        Z = P + '.B6'    # z layers

        # Mirror parameters onto the Frame group (identification + editing)
        frame_group.setExpression('FrameProfile', P + '.B1')
        frame_group.setExpression('FrameProfileSize', ps)
        frame_group.setExpression('FrameProfileHeight', ph)
        frame_group.setExpression('FrameLength', L)
        frame_group.setExpression('FrameWidth', W)
        frame_group.setExpression('FrameHeight', H)
        frame_group.setExpression('FrameZLayers', Z)
        frame_group.setExpression('FrameMaterial', P + '.B7')

        # DXF/parametric beams are pre-created at fixed size (Part::Feature
        # has no Length/Width/Height), so only bind box expressions when the
        # bases actually expose those properties and the section is square.
        def _box_like(obj):
            return hasattr(obj, 'Length') and hasattr(obj, 'Width') and hasattr(obj, 'Height')

        square = abs(float(frame_group.FrameProfileSize)
                     - float(frame_group.FrameProfileHeight)) < 1e-6
        if square and _box_like(self._bases.get('Z')) and _box_like(self._bases.get('X')) and _box_like(self._bases.get('Y')):
            # Z post base (corner-anchored box) and its 2x2 array
            z_base = self._bases['Z']
            z_base.setExpression('Length', ps)
            z_base.setExpression('Width', ps)
            z_base.setExpression('Height', H)
            z_base.setExpression('Placement.Base.x', L + ' / -2')
            z_base.setExpression('Placement.Base.y', W + ' / -2')
            self._z_array.setExpression('IntervalX.x', '(%s - %s) / 1mm' % (L, ps))
            self._z_array.setExpression('IntervalY.y', '(%s - %s) / 1mm' % (W, ps))
            
            # X beam base (centered box, z from 0) and its 1x2 array
            x_base = self._bases['X']
            x_base.setExpression('Length', '%s - 2 * %s' % (L, ps))
            x_base.setExpression('Width', ps)
            x_base.setExpression('Height', ps)
            x_base.setExpression('Placement.Base.x', '%s - %s / 2' % (ps, L))
            x_base.setExpression('Placement.Base.y', ps + ' / -2')
            self._x_array.setExpression('Placement.Base.y', '%s / 2 - %s / 2' % (ps, W))
            self._x_array.setExpression('IntervalY.y', '(%s - %s) / 1mm' % (W, ps))
            
            # Y beam base and its 2x1 array
            y_base = self._bases['Y']
            y_base.setExpression('Length', ps)
            y_base.setExpression('Width', '%s - 2 * %s' % (W, ps))
            y_base.setExpression('Height', ps)
            y_base.setExpression('Placement.Base.x', ps + ' / -2')
            y_base.setExpression('Placement.Base.y', '%s - %s / 2' % (ps, W))
            self._y_array.setExpression('Placement.Base.x', '%s / 2 - %s / 2' % (ps, L))
            self._y_array.setExpression('IntervalX.x', '(%s - %s) / 1mm' % (L, ps))
            
            # Z layer array: spacing and count
            self._layer_array.setExpression(
                'IntervalZ.z', '(%s - %s) / %s / 1mm' % (H, ps, Z))
            self._layer_array.setExpression('NumberZ', '%s + 1' % Z)
    
    # ========== Parameter storage / frame lookup ==========
    def _store_params(self, group, profile, length, width, height, material,
                      z_layers, profile_size, profile_height, orientation,
                      connection='end_tap'):
        """Store build parameters as properties on the Frame group."""
        orientation = orientation or {}
        values = {'profile': profile, 'length': length, 'width': width,
                  'height': height, 'material': material, 'z_layers': z_layers,
                  'profile_size': profile_size, 'profile_height': profile_height,
                  'post_along_x': orientation.get('post_along_x', 'a'),
                  'beam_vertical': orientation.get('beam_vertical', 'b'),
                  'connection': connection or 'end_tap'}
        for prop, ptype, key in self._PARAM_PROPS:
            if not hasattr(group, prop):
                group.addProperty(ptype, prop, 'AlumFrame', u'框架参数(可编辑)')
            setattr(group, prop, values[key])

    @staticmethod
    def get_frame_params(frame_group):
        """Read stored parameters from a Frame group."""
        return {
            'profile': frame_group.FrameProfile,
            'length': float(frame_group.FrameLength),
            'width': float(frame_group.FrameWidth),
            'height': float(frame_group.FrameHeight),
            'material': frame_group.FrameMaterial,
            'z_layers': int(frame_group.FrameZLayers),
            'post_along_x': getattr(frame_group, 'FramePostAlongX', 'a'),
            'beam_vertical': getattr(frame_group, 'FrameBeamVertical', 'b'),
            'connection': getattr(frame_group, 'FrameConnection', 'end_tap'),
        }
    
    @staticmethod
    def find_frame_group(obj=None, doc=None):
        """Locate a Frame group from an object (walks up parents) or a document."""
        if obj is not None:
            cur, seen = obj, set()
            while cur is not None and id(cur) not in seen:
                seen.add(id(cur))
                if hasattr(cur, 'FrameProfile'):
                    return cur
                # Parent may be a group, a Draft array (Base) or a compound (Links)
                parents = [p for p in cur.InList
                           if (hasattr(p, 'Group') and cur in p.Group)
                           or (hasattr(p, 'Base') and p.Base is cur)
                           or (hasattr(p, 'Links') and cur in p.Links)]
                cur = parents[0] if parents else None
        if doc is not None:
            for o in doc.Objects:
                if hasattr(o, 'FrameProfile'):
                    return o
        return None
    
    @staticmethod
    def _remove_existing_frame(doc):
        """Remove a previously generated frame (and its BOM) from doc."""
        doomed = []
        
        def collect(obj):
            if obj in doomed:
                return
            doomed.append(obj)
            if hasattr(obj, 'Group'):
                for child in obj.Group:
                    collect(child)
        
        for obj in list(doc.Objects):
            if hasattr(obj, 'FrameProfile') or obj.Name in (OBJ_FRAME, OBJ_BOM, OBJ_PARAMS):
                collect(obj)
        # TechDraw objects need an ordered removal (detach views, delete views
        # before pages) or FreeCAD can crash on stale references.
        try:
            from .techdraw_bom import remove_drawings
            remove_drawings(doc)
        except Exception:
            pass
        # Sweep orphans left over from partial/legacy builds
        for obj in list(doc.Objects):
            if obj not in doomed and obj.Name.startswith(
                    ('Array', OBJ_X_BASE, OBJ_Y_BASE, OBJ_Z_BASE,
                     OBJ_LAYER_COMPOUND, 'Dim')):
                doomed.append(obj)
        for obj in doomed:
            try:
                doc.removeObject(obj.Name)
            except Exception:
                pass
    
    def _create_horizontal_layer(self, calc, profile, frame_group):
        """Create first horizontal layer (X + Y beams)."""
        # Create X beams
        x_base = self.beam_factory.create_beam(
            calc.get_x_beam_length(),
            profile,
            'X',
            OBJ_X_BASE,
            orientation=self._orientation
        )
        self._bases['X'] = x_base
        
        x_placement = calc.get_x_beam_placement()
        x_spacing = calc.get_x_beam_spacing()
        
        x_array = Draft.make_array(
            x_base,
            Base.Vector(0, 0, 0),
            Base.Vector(0, x_spacing, 0),
            1, 2
        )
        x_array.Label = u'X-横梁'
        x_array.Placement = Base.Placement(
            Base.Vector(x_placement[0], x_placement[1], x_placement[2]),
            Base.Rotation()
        )
        frame_group.addObject(x_array)
        self._x_array = x_array
        
        # Create Y beams
        y_base = self.beam_factory.create_beam(
            calc.get_y_beam_length(),
            profile,
            'Y',
            OBJ_Y_BASE,
            orientation=self._orientation
        )
        self._bases['Y'] = y_base
        
        y_placement = calc.get_y_beam_placement()
        y_spacing = calc.get_y_beam_spacing()
        
        y_array = Draft.make_array(
            y_base,
            Base.Vector(y_spacing, 0, 0),
            Base.Vector(0, 0, 0),
            2, 1
        )
        y_array.Label = u'Y-纵梁'
        y_array.Placement = Base.Placement(
            Base.Vector(y_placement[0], y_placement[1], y_placement[2]),
            Base.Rotation()
        )
        frame_group.addObject(y_array)
        self._y_array = y_array
        
        # Create compound
        layer_compound = self.doc.addObject('Part::Compound', OBJ_LAYER_COMPOUND)
        layer_compound.Label = u'水平层复合体'
        layer_compound.Links = [x_array, y_array]
        frame_group.addObject(layer_compound)
        
        return layer_compound
    
    def _array_horizontal_layer(self, calc, layer_compound, z_layers, frame_group):
        """Array horizontal layer in Z direction."""
        z_spacing = calc.get_z_layer_spacing(z_layers)
        z_positions = calc.get_z_layer_positions(z_layers)
        
        layer_array = Draft.make_array(
            layer_compound,
            Base.Vector(0, 0, 0),
            Base.Vector(0, 0, 0),
            1, 1
        )
        layer_array.Label = u'水平层阵列'
        layer_array.IntervalZ = Base.Vector(0, 0, z_spacing)
        layer_array.NumberZ = z_layers + 1
        layer_array.Placement = Base.Placement(
            Base.Vector(0, 0, 0),
            Base.Rotation()
        )
        frame_group.addObject(layer_array)
        self._layer_array = layer_array
        
        # Record beam metadata (qty derived from array counts, not hardcoded)
        x_qty = self._x_array.NumberX * self._x_array.NumberY
        y_qty = self._y_array.NumberX * self._y_array.NumberY
        x_profile = layer_compound.Links[0].Base.ProfileSpec
        y_profile = layer_compound.Links[1].Base.ProfileSpec
        for z_pos in z_positions:
            self.all_beams.append({
                'part': u'X-横梁',
                'profile': x_profile,
                'length': calc.get_x_beam_length(),
                'qty': x_qty,
                'z': z_pos
            })
            self.all_beams.append({
                'part': u'Y-纵梁',
                'profile': y_profile,
                'length': calc.get_y_beam_length(),
                'qty': y_qty,
                'z': z_pos
            })
    
    def _create_z_posts(self, calc, profile, height, frame_group):
        """Create Z posts via Array - position set on Base, Array placement stays at origin."""
        z_base = self.beam_factory.create_beam(
            height,
            profile,
            'Z',
            OBJ_Z_BASE,
            orientation=self._orientation
        )
        self._bases['Z'] = z_base
        
        z_placement = calc.get_z_post_placement()
        z_spacing_x, z_spacing_y = calc.get_z_post_spacing()
        
        # Position assigned on the Base object, not on the Array. Compose with
        # any placement the beam factory already set (DXF profiles carry a
        # half-profile offset so their centred geometry lands corner-anchored);
        # Part::Box beams have an identity placement, so this is a no-op there.
        anchor = Base.Placement(
            Base.Vector(z_placement[0], z_placement[1], z_placement[2]),
            Base.Rotation()
        )
        z_base.Placement = anchor * z_base.Placement
        
        # 2x2 array, copies follow the Base position
        z_array = Draft.make_array(
            z_base,
            Base.Vector(z_spacing_x, 0, 0),
            Base.Vector(0, z_spacing_y, 0),
            2, 2
        )
        z_array.Label = u'Z-立柱'
        frame_group.addObject(z_array)
        self._z_array = z_array
        
        # Record Z post metadata (qty derived from array counts)
        z_qty = z_array.NumberX * z_array.NumberY
        self.all_beams.append({
            'part': u'Z-立柱',
            'profile': profile,
            'length': height,
            'qty': z_qty,
            'z': 0.0
        })
    
    # ========== Connection holes ==========
    def _ensure_shapes(self):
        """Recompute once if sketch-driven bases have no shape yet."""
        for key in ('X', 'Y', 'Z'):
            base = self._bases.get(key)
            if base is not None and base.TypeId == 'Part::Extrusion':
                try:
                    if len(base.Shape.Faces) == 0:
                        self.doc.recompute()
                        return
                except Exception:
                    pass

    def _apply_connections(self, calc, length, width, height, z_layers,
                           profile, profile_size, profile_height):
        """Cut the holes required by the selected connection method.

        Holes are computed in each base object's LOCAL frame: the X/Y/Z bases
        are shared by symmetric array copies, so machining both ends of a beam
        base (and the post centreline in both directions) covers every copy.
        """
        from .connections import (joint_hardware, method_params, METHODS,
                                  METHOD_ORDER)

        # Sketch-driven beams need one recompute before their bbox is known.
        try:
            self._ensure_shapes()
        except Exception:
            pass

        method = self._connection
        px, py = calc.get_post_section()
        t, v = calc.get_beam_section()
        layers = calc.get_z_layer_positions(z_layers)
        params = method_params(method)
        meta = METHODS.get(method, {})
        machining = meta.get('machining', 'none')

        spec = hole_specs_for_profile(profile)
        tap = spec['tap']
        tap_dia = spec['tap_dia']
        tap_depth = spec['tap_depth']
        clearance = spec['clearance']

        # Optional user overrides from the task panel. Hole diameter may never
        # exceed half of the smaller section dimension.
        ov = self._hole_params or {}
        max_dia = min(profile_size, profile_height) / 2.0
        if ov.get('diameter'):
            try:
                clearance = min(float(ov['diameter']), max_dia)
            except (TypeError, ValueError):
                pass
        params = dict(params)
        if ov.get('depth'):
            try:
                params['hole_depth'] = min(float(ov['depth']),
                                          min(profile_size, profile_height))
            except (TypeError, ValueError):
                pass
        if ov.get('offset'):
            try:
                off = float(ov['offset'])
                params['side_offset'] = off
                params['anchor_offset'] = off
                params['nut_offset'] = off
            except (TypeError, ValueError):
                pass

        r_tap = tap_dia / 2.0
        r_clr = clearance / 2.0

        has_end_tap = machining in ('end_tap', 'end_tap+post_through',
                                    'end_tap+side_access+post_through')

        notes = {'X': [], 'Y': [], 'Z': []}
        member_axis_holes = {'X': [], 'Y': [], 'Z': []}

        def _center(obj):
            b = obj.Shape.BoundBox
            return ((b.XMin + b.XMax) / 2.0, (b.YMin + b.YMax) / 2.0,
                    (b.ZMin + b.ZMax) / 2.0), b

        # ---- X / Y horizontal beams ----
        for key in ('X', 'Y'):
            base = self._bases.get(key)
            if base is None:
                continue
            (cx, cy, cz), b = _center(base)
            beam_axis = (1.0, 0.0, 0.0) if key == 'X' else (0.0, 1.0, 0.0)
            # horizontal transverse axis (perpendicular to the beam, in plane)
            cross_axis = (0.0, 1.0, 0.0) if key == 'X' else (1.0, 0.0, 0.0)
            if key == 'X':
                ends = [(b.XMin, 1.0), (b.XMax, -1.0)]
            else:
                ends = [(b.YMin, 1.0), (b.YMax, -1.0)]

            holes = []

            def at(off, x0=None):
                x0 = end + inward * off if x0 is None else x0
                return (x0, cy, cz) if key == 'X' else (cx, x0, cz)

            for end, inward in ends:
                if has_end_tap:
                    holes.append({'pos': at(tap_depth / 2.0), 'axis': beam_axis,
                                  'radius': r_tap, 'depth': tap_depth,
                                  'kind': 'tap'})
                if machining == 'end_through+post_through':
                    # transverse through hole for a slot nut (打孔攻丝)
                    off = params.get('nut_offset', 20.0)
                    p = at(off)
                    holes.append({'pos': p, 'axis': cross_axis,
                                  'radius': r_clr, 'depth': t + 4.0,
                                  'kind': 'through'})
                if machining == 'end_tap+side_access+post_through':
                    off = params.get('side_offset', 18.0)
                    d = params.get('access_d', 6.8)
                    depth = params.get('hole_depth', v / 2.0 + 1.0)
                    p = at(off)
                    holes.append({'pos': (p[0], p[1], cz + v / 2.0 - depth / 2.0),
                                  'axis': (0.0, 0.0, 1.0), 'radius': d / 2.0,
                                  'depth': depth, 'kind': 'access'})
                if machining == 'anchor_hole+post_through':
                    off = params.get('anchor_offset', 15.0)
                    depth = params.get('hole_depth', v / 2.0 + 1.0)
                    p = at(off)
                    holes.append({'pos': (p[0], p[1], cz + v / 2.0 - depth / 2.0),
                                  'axis': (0.0, 0.0, 1.0), 'radius': r_clr,
                                  'depth': depth, 'kind': 'anchor'})
            if holes:
                cut = self._wrap_cut(base, holes, key + 'BeamBase')
                if cut is not None:
                    self._bases[key] = cut
                    arr = self._x_array if key == 'X' else self._y_array
                    try:
                        arr.Base = cut
                    except Exception:
                        pass
                else:
                    self._cut_holes(base, holes)

            # interior hole positions (mm from the member's start), used to
            # place hole dimensions on the drawing
            _lo = b.XMin if key == 'X' else b.YMin
            _hi = b.XMax if key == 'X' else b.YMax
            _vals = sorted(set(
                round((h['pos'][0] if key == 'X' else h['pos'][1]) - _lo, 1)
                for h in holes if h.get('kind') not in ('tap', 'end')))
            member_axis_holes[key] = [v for v in _vals
                                      if 0.5 < v < (_hi - _lo) - 0.5]

            bore_txt = spec.get('center_bore')
            if has_end_tap:
                notes[key].append(
                    u'端面攻丝【两端，每端1处，共2处/根】：'
                    u'%s 底孔Ø%g 深%.0f，沿梁轴攻入截面中心（中心孔）'
                    % (tap, bore_txt or tap_dia, tap_depth))
            if machining == 'end_through+post_through':
                notes[key].append(
                    u'打孔【两端，每端1处】：距梁端%.0f，垂直于梁轴、水平方向，'
                    u'Ø%g 贯通截面，配槽内螺母锁紧'
                    % (params.get('nut_offset', 20.0), clearance))
            if machining == 'end_tap+side_access+post_through':
                notes[key].append(
                    u'工艺孔【两端，每端1处】：距梁端%.0f，从顶面垂直向下、'
                    u'Ø%.1f 深%.0f（只穿透顶面一层，通入槽内用于拧紧）'
                    % (params.get('side_offset', 18.0),
                       params.get('access_d', 6.8),
                       params.get('hole_depth', v / 2.0 + 1.0)))
            if machining == 'anchor_hole+post_through':
                notes[key].append(
                    u'锚孔【两端，每端1处】：距梁端%.0f，从顶面垂直向下、'
                    u'Ø%g 深%.0f（只穿透顶面一层，槽内装锚件）'
                    % (params.get('anchor_offset', 15.0),
                       clearance, params.get('hole_depth', v / 2.0 + 1.0)))

        # ---- Z posts ----
        zbase = self._bases.get('Z')
        if zbase is not None:
            (zx, zy, _zz), _b = _center(zbase)
            holes = []
            if 'post_through' in machining:
                for z in layers:
                    gz = z + v / 2.0
                    holes.append({'pos': (zx, zy, gz), 'axis': (1.0, 0.0, 0.0),
                                  'radius': r_clr, 'depth': px + 4.0,
                                  'kind': 'through'})
                    holes.append({'pos': (zx, zy, gz), 'axis': (0.0, 1.0, 0.0),
                                  'radius': r_clr, 'depth': py + 4.0,
                                  'kind': 'through'})
                z_txt = u'、'.join(u'z=%.0f' % z for z in layers)
                notes['Z'].append(
                    u'打孔【每柱每层 2 处，X向+Y向各1】：沿梁轴方向水平贯穿，'
                    u'Ø%g 间隙孔（螺栓通过）；层高 %s，共 %d 层'
                    % (clearance, z_txt, len(layers)))
            if machining == 'post_end_tap':
                holes.append({'pos': (zx, zy, tap_depth / 2.0),
                              'axis': (0.0, 0.0, 1.0), 'radius': r_tap,
                              'depth': tap_depth, 'kind': 'tap'})
                holes.append({'pos': (zx, zy, height - tap_depth / 2.0),
                              'axis': (0.0, 0.0, 1.0), 'radius': r_tap,
                              'depth': tap_depth, 'kind': 'tap'})
                notes['Z'].append(
                    u'端面攻丝【两端，每端1处】：柱底沿 +Z 向上攻入、'
                    u'柱顶沿 -Z 向下攻入，%s 底孔Ø%g 深%.0f'
                    % (tap, spec.get('center_bore') or tap_dia, tap_depth))
            if holes:
                _zvals = sorted(set(round(h['pos'][2] - _b.ZMin, 1)
                                     for h in holes
                                     if h.get('kind') == 'through'))
                member_axis_holes['Z'] = [v for v in _zvals
                                          if 0.5 < v < height - 0.5]
                cut = self._wrap_cut(zbase, holes, 'ZPostBase')
                if cut is not None:
                    self._bases['Z'] = cut
                    try:
                        self._z_array.Base = cut
                    except Exception:
                        pass
                else:
                    self._cut_holes(zbase, holes)

        self._connection_notes = {k: u'\n'.join(dict.fromkeys(v))
                                  for k, v in notes.items() if v}
        self._hole_axis = member_axis_holes

        # ---- hardware totals ----
        if meta.get('joint_based'):
            units = 8 * len(layers)            # 4 X + 4 Y joints per layer
        elif method == 'base_plate':
            units = 8                          # 4 posts x 2 ends
        else:
            units = 0
        hardware = {}
        for name, qty in joint_hardware(method):
            hardware[name] = hardware.get(name, 0) + qty * units
        self._hardware = sorted(hardware.items())

    def _wrap_cut(self, base, holes, name):
        """Wrap a sketch-driven Part::Extrusion with a Part::Cut for holes.

        Returns the object to be used as the beam (the cut), or None if the
        base is not an extrusion (plain Part::Feature keeps the direct cut).
        """
        if base is None or base.TypeId != 'Part::Extrusion':
            return None
        try:
            tool = self.doc.addObject('Part::Feature', name + '_Holes')
            shapes = []
            for h in holes:
                direction = Base.Vector(*h['axis'])
                if direction.Length < 1e-9:
                    continue
                direction.normalize()
                center = Base.Vector(*h['pos'])
                depth = max(float(h['depth']), 0.1)
                start = center - direction * (depth / 2.0)
                shapes.append(Part.makeCylinder(h['radius'], depth,
                                                start, direction))
            if not shapes:
                return None
            merged = shapes[0]
            for sh in shapes[1:]:
                merged = merged.fuse(sh)
            tool.Shape = merged

            cut = self.doc.addObject('Part::Cut', name + '_Cut')
            cut.Base = base
            cut.Tool = tool
            # auxiliary boolean result: keep it out of the 3D view
            try:
                if FreeCADGui is not None and cut.ViewObject is not None:
                    cut.ViewObject.Visibility = False
            except Exception:
                pass
            return cut
        except Exception as exc:
            if FreeCAD is not None:
                FreeCAD.Console.PrintWarning(
                    u'AlumFrame: hole cut on %s failed (%s)\n' % (name, exc))
            return None

    def _cut_holes(self, obj, holes):
        """Cut hole cylinders into a base shape.

        The base's placement is baked into the geometry first, so hole
        coordinates (expressed in frame/global space from the object's own
        bounding box) line up; the placement is then reset to identity.
        """
        if Part is None or obj is None:
            return
        try:
            # TopoShape.cut() works in world space (the shape's Placement is
            # taken into account), so hole coordinates from the object's world
            # bounding box are used directly.
            shape = obj.Shape.copy()
            for h in holes:
                direction = Base.Vector(*h['axis'])
                if direction.Length < 1e-9:
                    continue
                direction.normalize()
                center = Base.Vector(*h['pos'])
                depth = max(float(h['depth']), 0.1)
                start = center - direction * (depth / 2.0)
                cyl = Part.makeCylinder(h['radius'], depth, start, direction)
                shape = shape.cut(cyl)
            obj.Shape = shape
        except Exception as exc:
            if FreeCAD is not None:
                FreeCAD.Console.PrintWarning(
                    u'AlumFrame: hole cutting on %s failed (%s)\n'
                    % (obj.Name, exc))

    def _create_techdraw(self, profile, material, z_layers):
        """Create TechDraw pages: one per member spec (qty + hole method)."""
        from .techdraw_bom import create_techdraw_bom, remove_drawings
        remove_drawings(self.doc)

        labels = {'X': u'X-横梁', 'Y': u'Y-纵梁', 'Z': u'Z-立柱'}
        agg = {}
        for b in self.all_beams:
            part = b['part']
            if part not in agg:
                agg[part] = {'length': b['length'], 'qty': 0}
            agg[part]['qty'] += b.get('qty', 1)

        specs = []
        for key, label in labels.items():
            base = self._bases.get(key)
            info = agg.get(label)
            if base is None or info is None:
                continue
            specs.append({'key': key, 'label': label, 'base': base,
                          'length': info['length'], 'qty': info['qty']})

        note_map = {label: self._connection_notes.get(key, '')
                    for key, label in labels.items()}
        try:
            create_techdraw_bom(self.doc, specs, note_map,
                                profile, material, self._connection, z_layers)
        except Exception as exc:
            if FreeCAD is not None:
                FreeCAD.Console.PrintWarning(
                    u'AlumFrame: TechDraw generation failed (%s)\n' % exc)
            return
        try:
            from .techdraw_bom import add_frame_dimensions
            group = self.doc.getObject(OBJ_FRAME)
            if group is not None:
                add_frame_dimensions(self.doc, group, profile)
        except Exception:
            pass

    def _create_bom(self, material, z_layers, frame_group, profile):
        """Create BOM spreadsheet (kept inside the Frame group)."""
        from .bom import create_bom_spreadsheet
        p = PROFILES[profile]
        pw = p['w']
        ph = p.get('h', pw)
        calc = FramePositionCalculator(
            float(frame_group.FrameLength),
            float(frame_group.FrameWidth),
            float(frame_group.FrameHeight),
            pw, ph)
        spec_sheet = HOLE_SPECS.get(profile) or {}
        note_map = {u'X-横梁': self._connection_notes.get('X', ''),
                    u'Y-纵梁': self._connection_notes.get('Y', ''),
                    u'Z-立柱': self._connection_notes.get('Z', '')}
        bom = create_bom_spreadsheet(
            self.doc, self.all_beams, material, z_layers,
            hole_spec=spec_sheet,
            profile_size=pw,
            z_layer_positions=calc.get_z_layer_positions(z_layers),
            hole_notes=note_map,
            hardware=self._hardware,
            connection=self._connection)
        frame_group.addObject(bom)
        return bom

    def _create_measurements(self, frame_group, length, width, height, z_layers,
                             profile_size, profile_height):
        """Create measurement annotations (standard Measure objects)."""
        from .measurements import add_measurement_annotations
        add_measurement_annotations(
            self.doc, frame_group, length, width, height, z_layers,
            self._bases, profile_size, profile_height)
