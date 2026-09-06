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
        (post, _find_edges(post, profile_size, 'x')[0]),
        (x_base, _find_edges(x_base, outer_length - 2 * profile_size, 'x')[0]),
        (post, _find_edges(post, profile_size, 'x')[1]),
    ])

    # Width (Y) = profile + (W - 2*profile) + profile
    _add_length_measure(doc, dim_group, 'DimY', u'宽度 (Y)', [
        (post, _find_edges(post, profile_size, 'y')[0]),
        (y_base, _find_edges(y_base, outer_width - 2 * profile_size, 'y')[0]),
        (post, _find_edges(post, profile_size, 'y')[1]),
    ])

    # Height (Z) - single vertical post edge
    _add_length_measure(doc, dim_group, 'DimZ', u'高度 (Z)', [
        (post, _find_edges(post, outer_height, 'z')[0]),
    ])

    return dim_group


def _find_edges(obj, target_len, axis):
    """Find edge subelement names with the given length along an axis."""
    names = []
    for i, e in enumerate(obj.Shape.Edges, 1):
        if abs(e.Length - target_len) < 1e-6:
            d = e.Vertexes[-1].Point - e.Vertexes[0].Point
            if abs(getattr(d, axis)) > 1e-6:
                names.append('Edge%d' % i)
    return names


def _add_length_measure(doc, group, name, label, elements):
    """Create a Measure::MeasureLength object bound to the given edges."""
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
