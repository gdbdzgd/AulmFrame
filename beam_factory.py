# -*- coding: utf-8 -*-
"""
Beam creation module for Aluminum Frame Generator.
Handles creation of different beam types using Part::Box or DXF extrusion.
"""

try:
    import FreeCAD
    from FreeCAD import Base
    import Part
except ImportError:
    FreeCAD = None
    Base = None
    Part = None

from .config import PROFILES
from .profiles.dxf_parser import get_contours
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

    def create_beam(self, length, profile_spec, direction='Z', name='Beam',
                    orientation=None):
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
        orientation : dict, optional
            {'post_along_x': 'a'|'b', 'beam_vertical': 'a'|'b'} for
            rectangular sections. Ignored for square sections.

        Returns
        -------
        Part::Box or Part::Feature
            Created beam object
        """
        if profile_spec not in PROFILES:
            raise ValueError(f'Unknown profile: {profile_spec}')

        p = PROFILES[profile_spec]
        orientation = orientation or {}

        if p['type'] == 'round':
            return self._create_round_beam(length, p, direction, name, profile_spec)
        elif p['type'] == 'dxf':
            return self._create_dxf_beam(length, p, direction, name,
                                         profile_spec, orientation)
        elif p['type'] == 'parametric':
            return self._create_parametric_beam(length, p, direction, name,
                                                profile_spec, orientation)
        else:
            return self._create_rect_beam(length, p, direction, name,
                                          profile_spec, orientation)

    def _tag(self, obj, direction, profile_spec):
        obj.addProperty('App::PropertyString', 'BeamType', 'Beam', 'Type of beam')
        obj.addProperty('App::PropertyString', 'ProfileSpec', 'Beam', 'Profile specification')
        obj.BeamType = direction
        obj.ProfileSpec = profile_spec

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
        self._tag(obj, direction, profile_spec)
        return obj

    def _create_rect_beam(self, length, profile, direction, name, profile_spec,
                          orientation=None):
        """Create a rectangular profile beam as a Part::Feature solid.

        A solid (rather than a parametric Part::Box) is used so connection
        holes can be cut into the base shape; arrays still copy it normally.
        """
        orientation = orientation or {}
        a, b = profile['w'], profile['h']
        post = orientation.get('post_along_x', 'a')
        vertical = orientation.get('beam_vertical', 'b')

        px, py = (a, b) if post == 'a' else (b, a)
        # horizontal beam cross-section: (transverse, vertical)
        t, v = (a, b) if vertical == 'b' else (b, a)

        if direction == 'X':
            shape = Part.makeBox(length, t, v)
            placement = Base.Placement(Base.Vector(-length / 2, -t / 2, 0),
                                       Base.Rotation())
        elif direction == 'Y':
            shape = Part.makeBox(t, length, v)
            placement = Base.Placement(Base.Vector(-t / 2, -length / 2, 0),
                                       Base.Rotation())
        else:  # Z
            shape = Part.makeBox(px, py, length)
            placement = Base.Placement(Base.Vector(0, 0, 0), Base.Rotation())

        obj = self.doc.addObject('Part::Feature', name)
        obj.Shape = shape
        obj.Placement = placement
        self._tag(obj, direction, profile_spec)
        return obj

    # ========== Parametric (generated) profiles ==========

    def _create_parametric_beam(self, length, profile, direction, name,
                                profile_spec, orientation=None):
        """Create a beam from a generated standard T-slot cross-section.

        The face is produced by profiles.extrusion_profiles from a parameter
        table, so no external DXF is required. Orientation maps the section's
        two dimensions onto the frame axes (see position_calculator). Falls
        back to a rectangular beam if the geometry cannot be built.
        """
        orientation = orientation or {}
        a = profile['w']
        b = profile['h']
        post = orientation.get('post_along_x', 'a')
        vertical = orientation.get('beam_vertical', 'b')

        def _fallback(exc=None):
            if FreeCAD is not None and exc is not None:
                FreeCAD.Console.PrintWarning(
                    u'AlumFrame: parametric profile "%s" failed (%s); using square beam\n'
                    % (profile.get('series'), exc))
            return self._create_rect_beam(length, profile, direction, name,
                                          profile_spec, orientation)

        # ---- Placement (same convention as before) ----
        if direction == 'X':
            if vertical == 'a':
                placement = Base.Placement(
                    Base.Vector(-length / 2.0, 0, a / 2.0),
                    Base.Rotation(Base.Vector(0, 1, 0), 90))
            else:
                placement = Base.Placement(
                    Base.Vector(-length / 2.0, 0, b / 2.0),
                    Base.Rotation(Base.Vector(1, 1, 1), 120))
        elif direction == 'Y':
            if vertical == 'a':
                placement = Base.Placement(
                    Base.Vector(0, -length / 2.0, a / 2.0),
                    Base.Rotation(Base.Vector(1, 1, 1), -120))
            else:
                placement = Base.Placement(
                    Base.Vector(0, -length / 2.0, b / 2.0),
                    Base.Rotation(Base.Vector(1, 0, 0), -90))
        else:  # Z
            if post == 'b':
                placement = Base.Placement(
                    Base.Vector(b / 2.0, a / 2.0, 0),
                    Base.Rotation(Base.Vector(0, 0, 1), 90))
            else:
                placement = Base.Placement(
                    Base.Vector(a / 2.0, b / 2.0, 0), Base.Rotation())

        # ---- Build a closed profile *sketch* and extrude it ----
        sketch = None
        obj = None
        try:
            import Draft
            from .profiles.extrusion_profiles import cached_face

            face = cached_face(profile['series'])
            if not face.isValid() or face.Area <= 1e-6:
                raise ValueError('invalid profile face')

            tmp = self.doc.addObject('Part::Feature', name + '_Profile')
            tmp_name = tmp.Name
            tmp.Shape = face
            tmp.recompute()
            sketch = Draft.make_sketch([tmp], autoconstraints=True, delete=True,
                                       name=name + '_Sketch')
            sketch.Label = name + u'_截面'
            if self.doc.getObject(tmp_name) is not None:
                try:
                    self.doc.removeObject(tmp_name)
                except Exception:
                    pass

            # The sketch drives the beam: a Part::Extrusion referencing the
            # closed profile sketch. Connection holes are added later as a
            # Part::Cut on top of this object (see FrameBuilder), so they
            # survive recomputes while the sketch stays editable.
            obj = self.doc.addObject('Part::Extrusion', name)
            obj.Base = sketch
            obj.Dir = (0, 0, 1)
            for prop in ('Length', 'LengthFwd'):
                if hasattr(obj, prop):
                    setattr(obj, prop, float(length))
                    break
            if hasattr(obj, 'Solid'):
                obj.Solid = True
            obj.Placement = placement
        except Exception as exc:
            # clean up partial objects and fall back to a solid beam
            for o in (obj, sketch):
                if o is not None:
                    try:
                        self.doc.removeObject(o.Name)
                    except Exception:
                        pass
            return _fallback(exc)

        self._tag(obj, direction, profile_spec)
        obj.addProperty('App::PropertyString', 'ProfileSource', 'Beam',
                        'Generated series')
        obj.ProfileSource = profile.get('series', '')
        return obj

    # ========== DXF contour beams ==========

    def _create_dxf_beam(self, length, profile, direction, name, profile_spec,
                         orientation=None):
        """Create a beam by extruding the real DXF cross-section contour.

        The contour is extracted from LINE/ARC/CIRCLE entities, turned into a
        closed profile *sketch* (Sketcher::SketchObject), and the solid is
        derived from that sketch's closed wires. Falls back to a plain
        rectangular beam if the contour cannot be parsed.
        """
        dxf_path = profile.get('dxf')
        if not dxf_path or not os.path.exists(dxf_path):
            return self._create_rect_beam(length, profile, direction, name,
                                          profile_spec, orientation)

        try:
            contours = get_contours(dxf_path)
            if not contours:
                return self._create_rect_beam(length, profile, direction, name,
                                              profile_spec, orientation)
            solid, sketch, placement = self._extrude_contours(
                contours, length, direction, name)
        except Exception as exc:
            # Remove the half-built sketch and fall back to a rectangular beam.
            orphan = self.doc.getObject(name + '_Sketch')
            if orphan is not None:
                try:
                    self.doc.removeObject(orphan.Name)
                except Exception:
                    pass
            if FreeCAD is not None:
                FreeCAD.Console.PrintWarning(
                    u'AlumFrame: DXF contour "%s" unusable (%s); using square beam\n'
                    % (os.path.basename(dxf_path), exc))
            return self._create_rect_beam(length, profile, direction, name,
                                          profile_spec, orientation)

        obj = self.doc.addObject('Part::Feature', name)
        obj.Shape = solid
        obj.Placement = placement
        self._tag(obj, direction, profile_spec)
        obj.addProperty('App::PropertyString', 'ProfileSource', 'Beam', 'DXF source file')
        obj.ProfileSource = os.path.basename(dxf_path)
        return obj

    def _segment_geometry(self, seg):
        """Build a Sketcher/Part geometry object from a contour segment."""
        p0 = Base.Vector(seg['p0'][0], seg['p0'][1], 0)
        p1 = Base.Vector(seg['p1'][0], seg['p1'][1], 0)
        if seg['kind'] == 'line':
            return Part.LineSegment(p0, p1)
        cx, cy = seg['center']
        r = seg['radius']
        circle = Part.Circle(Base.Vector(cx, cy, 0),
                             Base.Vector(0, 0, 1), r)
        return Part.ArcOfCircle(circle, seg['start_angle'],
                                seg['start_angle'] + seg['extent'])

    def _extrude_contours(self, contours, length, direction, name):
        """Create a closed sketch from contours and extrude it into a solid.

        Returns (solid_shape, sketch_object, placement). The solid's local
        geometry starts at the origin and the returned placement mirrors the
        convention used by :meth:`_create_rect_beam` (Part::Box) so existing
        arrays/positions align both beam kinds identically. The sketch holds
        the closed outer contour plus every cavity, so the extrusion is driven
        by the sketch's own geometry.
        """
        import Sketcher

        sketch = self.doc.addObject('Sketcher::SketchObject', name + '_Sketch')
        sketch.Label = name + u'_截面'

        # Collect all geometry and coincidence constraints first, then add them
        # in bulk: per-call addGeometry/addConstraint overhead is what makes
        # the ~120-segment T-slot profile slow otherwise.
        geometries = []
        constraints = []
        base = 0
        for loop in [contours['outer']] + list(contours['holes']):
            geometries.extend(self._segment_geometry(s) for s in loop)
            n = len(loop)
            for i in range(n):
                constraints.append(Sketcher.Constraint(
                    'Coincident', base + i, 2, base + (i + 1) % n, 1))
            base += n
        for (cx, cy, r) in contours['circles']:
            geometries.append(
                Part.Circle(Base.Vector(cx, cy, 0), Base.Vector(0, 0, 1), r))
        sketch.addGeometry(geometries, False)
        sketch.addConstraint(constraints)
        # Recompute only the sketch (not the whole document, which would also
        # re-solve every array/compound already built).
        sketch.recompute()

        # Build a planar face with holes from the sketch's closed wires.
        wires = [w for w in sketch.Shape.Wires if w.isClosed()]
        if not wires:
            raise ValueError('DXF sketch produced no closed wires')

        outer_face = None
        for maker in ('Part::FaceMakerCheese', 'Part::FaceMakerBullseye'):
            try:
                candidate = Part.makeFace(wires, maker)
                if candidate.isValid() and candidate.Area > 0:
                    outer_face = candidate
                    break
            except Exception:
                pass
        if outer_face is None:
            # Fallback: subtract each cavity with a boolean cut.
            faces = [Part.Face(w) for w in wires]
            outer_face = max(faces, key=lambda f: f.Area)
            for f in faces:
                if f is not outer_face:
                    outer_face = outer_face.cut(f)

        # Extruded along +Z with the profile centred on the origin.
        solid = outer_face.extrude(Base.Vector(0, 0, length))

        # Re-orient so the finished beam occupies exactly the same space a
        # Part::Box beam would, keeping arrays/positions aligned across both
        # kinds. X/Y need only a rotation, which the object Placement carries;
        # the Z post frame is corner-anchored (the builder overwrites its
        # Placement), so its translation is baked into the geometry.
        w = contours['width']
        h = contours['height']
        if direction == 'X':
            placement = Base.Placement(
                Base.Vector(-length / 2.0, 0, w / 2.0),
                Base.Rotation(Base.Vector(0, 1, 0), 90))
        elif direction == 'Y':
            placement = Base.Placement(
                Base.Vector(0, -length / 2.0, h / 2.0),
                Base.Rotation(Base.Vector(1, 0, 0), -90))
        else:  # Z
            # Keep the centred geometry and carry the corner offset in the
            # Placement; the builder composes it with the post anchor. Baking
            # it via transformGeometry can invalidate some complex solids.
            placement = Base.Placement(
                Base.Vector(w / 2.0, h / 2.0, 0), Base.Rotation())

        # Reject degenerate results (self-intersecting / multi-cluster wires in
        # some third-party DXFs). Callers fall back to a plain rectangular beam
        # instead of shipping an invalid Part::Feature.
        if not solid.isValid() or solid.Volume <= 1e-3 or not solid.Solids:
            raise ValueError('DXF contour did not yield a valid solid')

        return solid, sketch, placement
