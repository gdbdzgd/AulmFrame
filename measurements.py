# -*- coding: utf-8 -*-
"""
Measurement annotations module for Aluminum Frame Generator.
"""

try:
    from FreeCAD import Base
    import Part
except ImportError:
    Base = None
    Part = None


def add_measurement_annotations(doc, group, outer_length, outer_width, outer_height, z_layers):
    """Add dimension annotations using text labels at frame corners.
    
    Parameters
    ----------
    doc : FreeCAD document
    group : App::DocumentObjectGroup
        Frame group to add annotations to
    outer_length : float
        Frame outer length
    outer_width : float
        Frame outer width
    outer_height : float
        Frame outer height
    z_layers : int
        Number of Z layers
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
    """Create a dimension line with text label.
    
    Parameters
    ----------
    doc : FreeCAD document
    group : App::DocumentObjectGroup
        Dimension group
    name : str
        Object name
    start : Base.Vector
        Line start point
    end : Base.Vector
        Line end point
    label_text : str
        Label text
    """
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
        # Silently ignore errors to avoid breaking frame generation
        pass
