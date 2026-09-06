# -*- coding: utf-8 -*-
"""
Beam creation module for Aluminum Frame Generator.
Handles creation of different beam types using Part::Box.
"""

try:
    import FreeCAD
    from FreeCAD import Base, Part
except ImportError:
    FreeCAD = None
    Base = None
    Part = None

from .config import PROFILES


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
        else:
            return self._create_rect_beam(length, p, direction, name, profile_spec)
    
    def _create_round_beam(self, length, profile, direction, name, profile_spec):
        """Create a round tube beam (Part::Feature with cylinder shape).

        Local coordinate conventions match the rectangular beams:
        - Z: base corner at origin, spans 0..length (axis at d/2, d/2)
        - X/Y: centered on the beam axis, Z from 0..d
        """
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

        # Custom properties (same as rectangular beams, required by BOM/metadata)
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
            # Length along X, width along Y, height along Z
            obj.Length = length
            obj.Width = w
            obj.Height = h
            # Centered in XY, Z starts at 0 (consistent with Y direction)
            obj.Placement = Base.Placement(
                Base.Vector(-length/2, -w/2, 0), 
                Base.Rotation()
            )
        elif direction == 'Y':
            # Width along X, length along Y, height along Z
            obj.Length = w
            obj.Width = length
            obj.Height = h
            # Center in XY, Z at 0
            obj.Placement = Base.Placement(
                Base.Vector(-w/2, -length/2, 0), 
                Base.Rotation()
            )
        elif direction == 'Z':
            # Width along X, height along Y, length along Z
            obj.Length = w
            obj.Width = h
            obj.Height = length
            # Start from Z=0 (bottom), XY at origin
            obj.Placement = Base.Placement(
                Base.Vector(0, 0, 0), 
                Base.Rotation()
            )
        
        # Add custom properties
        obj.addProperty('App::PropertyString', 'BeamType', 'Beam', 'Type of beam')
        obj.addProperty('App::PropertyString', 'ProfileSpec', 'Beam', 'Profile specification')
        obj.BeamType = direction
        obj.ProfileSpec = profile_spec  # Use the string, not the dict
        
        return obj
