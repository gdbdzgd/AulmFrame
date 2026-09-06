# -*- coding: utf-8 -*-
"""
Configuration module for Aluminum Frame Generator.
Separates data from code for easy customization and extension.
"""

# Profile definitions - can be extended via JSON in the future
PROFILES = {
    '20x20 方管': {'type': 'square', 'w': 20, 'h': 20},
    '30x30 方管': {'type': 'square', 'w': 30, 'h': 30},
    '40x40 方管': {'type': 'square', 'w': 40, 'h': 40},
    '40x20 方管': {'type': 'rect',   'w': 40, 'h': 20},
    '40x40 圆管': {'type': 'round',  'd': 40},
    '50x50 方管': {'type': 'square', 'w': 50, 'h': 50},
    '60x40 方管': {'type': 'rect',   'w': 60, 'h': 40},
    '80x80 方管': {'type': 'square', 'w': 80, 'h': 80},
    '20x20 圆管': {'type': 'round',  'd': 20},
}

# Default frame parameters
DEFAULTS = {
    'material': 'Aluminum 6061',
    'z_layers': 1,
}

# Position calculation constants
class PositionConfig:
    """Configuration for position calculations.
    
    All positions are calculated based on:
    - Frame outer dimensions (length, width, height)
    - Profile size
    - Z post first position (anchor point)
    """
    
    # Z post first position formula
    # X = -profile_size/2 - (length - profile_size)/2
    # Y = -profile_size/2 - (width - profile_size)/2
    Z_POST_ANCHOR_X = lambda length, profile_size: -profile_size/2 - (length - profile_size)/2
    Z_POST_ANCHOR_Y = lambda width, profile_size: -profile_size/2 - (width - profile_size)/2
    
    # Z post spacing
    Z_POST_SPACING_X = lambda length, profile_size: length - profile_size
    Z_POST_SPACING_Y = lambda width, profile_size: width - profile_size
    
    # X beam Y position (aligned with Z post inner face)
    # Y = Z_post_anchor_Y + profile_size
    X_BEAM_START_Y = lambda width, profile_size: -width/2 + profile_size/2
    
    # Y beam X position (aligned with Z post inner face)
    # X = Z_post_anchor_X + profile_size
    Y_BEAM_START_X = lambda length, profile_size: -length/2 + profile_size/2
    
    # Beam spacing
    X_BEAM_SPACING_Y = lambda width, profile_size: width - profile_size
    Y_BEAM_SPACING_X = lambda length, profile_size: length - profile_size
    
    # Z layer spacing
    Z_LAYER_SPACING = lambda height, profile_size, z_layers: (height - profile_size) / z_layers if z_layers > 0 else height


# Beam length calculations
class BeamLengthConfig:
    """Configuration for beam length calculations."""
    
    # X beam length = outer_length - 2*profile_size (fits between inner faces of Z posts)
    X_BEAM_LENGTH = lambda length, profile_size: length - 2 * profile_size
    
    # Y beam length = outer_width - 2*profile_size (fits between inner faces of Z posts)
    Y_BEAM_LENGTH = lambda width, profile_size: width - 2 * profile_size
    
    # Z post length = full height
    Z_POST_LENGTH = lambda height: height
