# -*- coding: utf-8 -*-
"""Measurement annotations module.

Uses standard FreeCAD Measure objects (Measure::MeasureLength, the same
type created by Std_Measure) so annotations are parametric measurements
of real geometry instead of decorative lines.

Each dimension is a chain of real edges:
- Length (X): post X-edge + X-beam edge + post X-edge
- Width  (Y): post Y-edge + Y-beam edge + post Y-edge
- Height (Z): post vertical edge
"""

try:
    import FreeCAD
except ImportError:
    FreeCAD = None


def add_measurement_annotations(doc, group, outer_length, outer_width,
                                outer_height, z_layers, bases, profile_size):
    """Add dimension annotations using Measure::MeasureLength objects.

    Parameters
    ----------
    doc : FreeCAD document
    group : App::DocumentObjectGroup
        Frame group; the Dimensions group is created inside it
    outer_length, outer_width, outer_height : float
        Frame outer dimensions (mm)
    z_layers : int
        Number of Z layers (reserved for future use)
    bases : dict
        {'X': x_beam_base, 'Y': y_beam_base, 'Z': z_post_base}
    profile_size : float
        Profile width (mm)
    """
    post = bases.get('Z')
    x_base = bases.get('X')
    y_base = bases.get('Y')
    if post is None or x_base is None or y_base is None:
        return None

    dim_group = doc.addObject('App::DocumentObjectGroup', 'Dimensions')
    dim_group.Label = u'尺寸标注'
    group.addObject(dim_group)

    # Length (X) = profile + (L - 2*profile) + profile
    _add_length_measure(doc, dim_group, 'DimX', u'长度 (X)', [
        (post, profile_size, 'x'),
        (x_base, outer_length - 2 * profile_size, 'x'),
        (post, profile_size, 'x'),
    ])

    # Width (Y) = profile + (W - 2*profile) + profile
    _add_length_measure(doc, dim_group, 'DimY', u'宽度 (Y)', [
        (post, profile_size, 'y'),
        (y_base, outer_width - 2 * profile_size, 'y'),
        (post, profile_size, 'y'),
    ])

    # Height (Z) - single vertical post edge
    _add_length_measure(doc, dim_group, 'DimZ', u'高度 (Z)', [
        (post, outer_height, 'z'),
    ])

    return dim_group


def _pick_edge(obj, target_len, axis, used):
    """Pick an edge of the given length/axis, avoiding already-used ones."""
    names = _find_edges(obj, target_len, axis)
    for n in names:
        if (obj.Name, n) not in used:
            used.add((obj.Name, n))
            return n
    return names[0] if names else None


def _find_edges(obj, target_len, axis):
    """Find edge subelement names with the given length along an axis."""
    names = []
    for i, e in enumerate(obj.Shape.Edges, 1):
        if abs(e.Length - target_len) < 1e-6:
            d = e.Vertexes[-1].Point - e.Vertexes[0].Point
            if abs(getattr(d, axis)) > 1e-6:
                names.append('Edge%d' % i)
    return names


def _add_length_measure(doc, group, name, label, chain):
    """Create a Measure::MeasureLength bound to a chain of edges.

    chain: [(obj, target_length, axis), ...]. Skips gracefully when an
    edge cannot be found (e.g. round posts have no axial short edges).
    """
    used = set()
    elements = []
    for obj, tlen, axis in chain:
        edge = _pick_edge(obj, tlen, axis, used)
        if edge is None:
            FreeCAD.Console.PrintWarning(
                u'Measure "%s" skipped: no %s-edge of length %.1f on %s\n'
                % (label, axis, tlen, obj.Name))
            return None
        elements.append((obj, edge))
    try:
        m = doc.addObject('Measure::MeasureLength', name)
        m.Label = label
        m.Elements = elements
        doc.recompute()
        group.addObject(m)
        return m
    except Exception as e:
        FreeCAD.Console.PrintWarning(
            u'Measure annotation "%s" failed: %s\n' % (label, str(e)))
        return None
