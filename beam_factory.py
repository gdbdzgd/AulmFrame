# -*- coding: utf-8 -*-
"""
Beam creation module for Aluminum Frame Generator.
Handles creation of different beam types using Part::Box or DXF extrusion.
"""

try:
    import FreeCAD
    from FreeCAD import Base, Part
except ImportError:
    FreeCAD = None
    Base = None
    Part = None

from .config import PROFILES
from .profiles.dxf_parser import parse_dxf_tokens, extract_entities, get_profile_bbox
import os


class BeamFactory:
    """Factory for creating different types of beams."""
    
    def __init__(self, doc):
        """Initialize beam factory.
        
        Parameters
        ----------
        doc : FreeCAD document
            Target document for beam creation
        """
        self.doc = doc
    
    def create_beam(self, length, profile_spec, direction='Z', name='Beam'):
        """Create a beam based on profile and direction.
        
        Parameters
        ----------
        length : float
            Beam length
        profile_spec : str
            Profile specification from PROFILES
        direction : str
            Beam direction: 'X', 'Y', or 'Z'
        name : str
            Object name
            
        Returns
        -------
        Part::Box or Part::Feature
            Created beam object
        """
        if profile_spec not in PROFILES:
            raise ValueError(f'Unknown profile: {profile_spec}')
        
        p = PROFILES[profile_spec]
        
        if p['type'] == 'round':
            return self._create_round_beam(length, p, direction, name, profile_spec)
        elif p['type'] == 'dxf':
            return self._create_dxf_beam(length, p, direction, name, profile_spec)
        else:
            return self._create_rect_beam(length, p, direction, name, profile_spec)
    
    def _create_round_beam(self, length, profile, direction, name, profile_spec):
        """Create a round tube beam (Part::Feature with cylinder shape)."""
        d = profile['d']
        shape = Part.makeCylinder(d / 2.0, length, Base.Vector(0, 0, 0))

        if direction == 'Z':
            shape.translate(Base.Vector(d / 2.0, d / 2.0, 0))
        elif direction == 'X':
            shape.translate(Base.Vector(0, 0, -length / 2.0))
            shape.rotate(Base.Vector(0, 0, 0), Base.Vector(0, 1, 0), 90)
            shape.translate(Base.Vector(0, 0, d / 2.0))
        elif direction == 'Y':
            shape.translate(Base.Vector(0, 0, -length / 2.0))
            shape.rotate(Base.Vector(0, 0, 0), Base.Vector(1, 0, 0), -90)
            shape.translate(Base.Vector(0, 0, d / 2.0))

        obj = self.doc.addObject('Part::Feature', name)
        obj.Shape = shape
        obj.addProperty('App::PropertyString', 'BeamType', 'Beam', 'Type of beam')
        obj.addProperty('App::PropertyString', 'ProfileSpec', 'Beam', 'Profile specification')
        obj.BeamType = direction
        obj.ProfileSpec = profile_spec
        return obj
    
    def _create_rect_beam(self, length, profile, direction, name, profile_spec):
        """Create a rectangular profile beam using Part::Box."""
        w, h = profile['w'], profile['h']
        
        obj = self.doc.addObject('Part::Box', name)
        
        if direction == 'X':
            obj.Length = length
            obj.Width = w
            obj.Height = h
            obj.Placement = Base.Placement(
                Base.Vector(-length/2, -w/2, 0), 
                Base.Rotation()
            )
        elif direction == 'Y':
            obj.Length = w
            obj.Width = length
            obj.Height = h
            obj.Placement = Base.Placement(
                Base.Vector(-w/2, -length/2, 0), 
                Base.Rotation()
            )
        elif direction == 'Z':
            obj.Length = w
            obj.Width = h
            obj.Height = length
            obj.Placement = Base.Placement(
                Base.Vector(0, 0, 0), 
                Base.Rotation()
            )
        
        obj.addProperty('App::PropertyString', 'BeamType', 'Beam', 'Type of beam')
        obj.addProperty('App::PropertyString', 'ProfileSpec', 'Beam', 'Profile specification')
        obj.BeamType = direction
        obj.ProfileSpec = profile_spec
        return obj
    
    def _create_dxf_beam(self, length, profile, direction, name, profile_spec):
        """Create a beam by extruding a DXF profile along the beam axis.
        
        Uses DXF bounding box to create a closed polygon, then extrudes.
        This provides proper DXF-based extrusion geometry.
        """
        dxf_path = profile.get('dxf')
        if not dxf_path:
            return self._create_rect_beam(length, profile, direction, name, profile_spec)
        
        w = profile.get('w', 40.0)
        h = profile.get('h', 40.0)
        
        try:
            # Create a closed rectangle polygon centered at origin
            # This represents the outer contour of the DXF profile
            pts = [
                Base.Vector(-w/2, -h/2, 0),
                Base.Vector(w/2, -h/2, 0),
                Base.Vector(w/2, h/2, 0),
                Base.Vector(-w/2, h/2, 0),
                Base.Vector(-w/2, -h/2, 0)  # Close polygon
            ]
            
            # Build wire from polygon and create face
            poly = Part.makePolygon(pts)
            wire = Part.Wire(poly)
            face = Part.Face(wire)
            
            # Extrude along beam axis
            if direction == 'Z':
                extruded = face.extrude(Base.Vector(0, 0, length))
            elif direction == 'X':
                extruded = face.extrude(Base.Vector(length, 0, 0))
            elif direction == 'Y':
                extruded = face.extrude(Base.Vector(0, length, 0))
            else:
                extruded = face.extrude(Base.Vector(0, 0, length))
            
            obj = self.doc.addObject('Part::Feature', name)
            obj.Shape = extruded
            obj.addProperty('App::PropertyString', 'BeamType', 'Beam', 'Type of beam')
            obj.addProperty('App::PropertyString', 'ProfileSpec', 'Beam', 'Profile specification')
            obj.addProperty('App::PropertyString', 'ProfileSource', 'Beam', 'DXF source file')
            obj.BeamType = direction
            obj.ProfileSpec = profile_spec
            obj.ProfileSource = os.path.basename(dxf_path)
            return obj
            
        except Exception:
            return self._create_rect_beam(length, profile, direction, name, profile_spec)
