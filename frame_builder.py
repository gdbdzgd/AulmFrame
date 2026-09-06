# -*- coding: utf-8 -*-
"""
Frame builder module for Aluminum Frame Generator.
Orchestrates the creation of all frame components.
"""

try:
    import FreeCAD
    from FreeCAD import Base
    import Draft
except ImportError:
    FreeCAD = None
    Base = None
    Draft = None

from .config import PROFILES
from .position_calculator import FramePositionCalculator
from .beam_factory import BeamFactory


class FrameBuilder:
    """Builder class for creating aluminum frames."""
    
    # Parameters stored on the Frame group so frames can be edited later
    _PARAM_PROPS = [
        ('FrameProfile', 'App::PropertyString', 'profile'),
        ('FrameLength', 'App::PropertyLength', 'length'),
        ('FrameWidth', 'App::PropertyLength', 'width'),
        ('FrameHeight', 'App::PropertyLength', 'height'),
        ('FrameMaterial', 'App::PropertyString', 'material'),
        ('FrameZLayers', 'App::PropertyInteger', 'z_layers'),
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
    
    def build_frame(self, profile, length, width, height, material='Aluminum 6061', z_layers=1, doc=None):
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
        
        # Get profile size
        profile_size = PROFILES[profile]['w'] if PROFILES[profile]['type'] != 'round' else PROFILES[profile]['d']
        
        # Create position calculator
        calc = FramePositionCalculator(length, width, height, profile_size)
        
        # Draft.make_array creates objects in the ACTIVE document, so the
        # target document must be active during the build; restore after.
        prev_active = FreeCAD.ActiveDocument
        FreeCAD.setActiveDocument(doc.Name)
        try:
            self._build_into_doc(doc, calc, profile, profile_size,
                                 length, width, height, material, z_layers)
        finally:
            if prev_active is not None:
                FreeCAD.setActiveDocument(prev_active.Name)
        
        self.doc.recompute()
        return self.doc, self.all_beams
    
    def _build_into_doc(self, doc, calc, profile, profile_size,
                        length, width, height, material, z_layers):
        """Create all frame objects in doc (doc must be the active document)."""
        # Create main frame group
        frame_group = doc.addObject('App::DocumentObjectGroup', 'Frame')
        frame_group.Label = u'Frame'
        
        # Store parameters on the group for later editing
        self._store_params(frame_group, profile, length, width, height, material, z_layers)
        
        # ========== Create Horizontal Layer (X + Y Beams) ==========
        layer_compound = self._create_horizontal_layer(calc, profile, frame_group)
        
        # ========== Array Horizontal Layer in Z Direction ==========
        self._array_horizontal_layer(calc, layer_compound, z_layers, frame_group)
        
        # ========== Create Z Posts ==========
        self._create_z_posts(calc, profile, height, frame_group)
        
        # ========== Create BOM ==========
        self._create_bom(material, z_layers, frame_group)
        
        # ========== Create Measurements ==========
        self._create_measurements(frame_group, length, width, height, z_layers, profile_size)
    
    # ========== Parameter storage / frame lookup ==========
    def _store_params(self, group, profile, length, width, height, material, z_layers):
        """Store build parameters as properties on the Frame group."""
        values = {'profile': profile, 'length': length, 'width': width,
                  'height': height, 'material': material, 'z_layers': z_layers}
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
            if hasattr(obj, 'FrameProfile') or obj.Name in ('Frame', 'BOM'):
                collect(obj)
        # Sweep orphans left over from partial/legacy builds
        for obj in list(doc.Objects):
            if obj not in doomed and obj.Name.startswith(
                    ('Array', 'XBeamBase', 'YBeamBase', 'ZPostBase',
                     'LayerCompound', 'Dim')):
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
            'XBeamBase'
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
        
        # Create Y beams
        y_base = self.beam_factory.create_beam(
            calc.get_y_beam_length(),
            profile,
            'Y',
            'YBeamBase'
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
        
        # Create compound
        layer_compound = self.doc.addObject('Part::Compound', 'LayerCompound')
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
        
        # Record beam metadata
        for z_pos in z_positions:
            self.all_beams.append({
                'part': u'X-横梁',
                'profile': layer_compound.Links[0].Base.ProfileSpec,
                'length': calc.get_x_beam_length(),
                'qty': 2,
                'z': z_pos
            })
            self.all_beams.append({
                'part': u'Y-纵梁',
                'profile': layer_compound.Links[1].Base.ProfileSpec,
                'length': calc.get_y_beam_length(),
                'qty': 2,
                'z': z_pos
            })
    
    def _create_z_posts(self, calc, profile, height, frame_group):
        """Create Z posts via Array - position set on Base, Array placement stays at origin."""
        z_base = self.beam_factory.create_beam(
            height,
            profile,
            'Z',
            'ZPostBase'
        )
        self._bases['Z'] = z_base
        
        z_placement = calc.get_z_post_placement()
        z_spacing_x, z_spacing_y = calc.get_z_post_spacing()
        
        # Position assigned on the Base object, not on the Array
        z_base.Placement = Base.Placement(
            Base.Vector(z_placement[0], z_placement[1], z_placement[2]),
            Base.Rotation()
        )
        
        # 2x2 array, copies follow the Base position
        z_array = Draft.make_array(
            z_base,
            Base.Vector(z_spacing_x, 0, 0),
            Base.Vector(0, z_spacing_y, 0),
            2, 2
        )
        z_array.Label = u'Z-立柱'
        frame_group.addObject(z_array)
        
        # Record Z post metadata
        self.all_beams.append({
            'part': u'Z-立柱',
            'profile': profile,
            'length': height,
            'qty': 4,
            'z': 0.0
        })
    
    def _create_bom(self, material, z_layers, frame_group):
        """Create BOM spreadsheet (kept inside the Frame group)."""
        # Import BOM module here to avoid circular imports
        from .bom import create_bom_spreadsheet
        bom = create_bom_spreadsheet(self.doc, self.all_beams, material, z_layers)
        frame_group.addObject(bom)
        return bom
    
    def _create_measurements(self, frame_group, length, width, height, z_layers, profile_size):
        """Create measurement annotations (standard Measure objects)."""
        from .measurements import add_measurement_annotations
        add_measurement_annotations(
            self.doc, frame_group, length, width, height, z_layers,
            self._bases, profile_size)
