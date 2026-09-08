# -*- coding: utf-8 -*-
"""
Configuration module for Aluminum Frame Generator.
Separates data from code for easy customization and extension.

Note: all position/length formulas live in position_calculator.py
(single source of truth) — do NOT duplicate them here.
"""

# Profile definitions - square tubes supported
PROFILES = {
    '20x20 方管': {'type': 'square', 'w': 20, 'h': 20},
    '30x30 方管': {'type': 'square', 'w': 30, 'h': 30},
    '40x40 方管': {'type': 'square', 'h': 40, 'w': 40},
    '60x60 方管': {'type': 'square', 'w': 60, 'h': 60},
}

# DXF-based profiles from MISUMI resource directory (override hardcoded profiles)
try:
    from .profiles.dxf_parser import get_profile_for_size, get_all_profiles as _get_all_profiles
    DXF_PROFILES = _get_all_profiles()
    
    # Override all core profiles with DXF type
    for size in ['20x20', '30x30', '40x40', '60x60']:
        key = size + ' 方管'
        if key in PROFILES:
            p = get_profile_for_size(size)
            if p:
                PROFILES[key] = {
                    'type': 'dxf',
                    'w': p['width'],
                    'h': p['height'],
                    'dxf': p['dxf_file'],
                }
    
    # Use hfs8-4040.dxf specifically for 40x40
    hfs8_path = '/home/gdzhang/gits/AulmFrame/profiles/dxf/hfs8-4040.dxf'
    import os
    if os.path.exists(hfs8_path):
        from .profiles.dxf_parser import parse_dxf_tokens, extract_entities, get_profile_bbox
        tokens = parse_dxf_tokens(hfs8_path)
        entities = extract_entities(tokens)
        bbox = get_profile_bbox(entities)
        if bbox:
            PROFILES['40x40 方管'] = {
                'type': 'dxf',
                'w': bbox['width'],
                'h': bbox['height'],
                'dxf': hfs8_path,
            }
except Exception:
    DXF_PROFILES = []

# Hole / tap specs for bolted connections (edit to match your fasteners):
#   beam_cross: cross-through hole on horizontal beams at Z-post connections
#   post_tap:   tapped hole on Z post ends (top & bottom)
HOLE_SPECS = {
    '20x20 方管': {'beam_cross': 'M5', 'post_tap': 'M6'},
    '30x30 方管': {'beam_cross': 'M6', 'post_tap': 'M8'},
    '40x40 方管': {'beam_cross': 'M8', 'post_tap': 'M10'},
    '60x60 方管': {'beam_cross': 'M10', 'post_tap': 'M12'},
}

# Auto-generate hole specs for DXF profiles based on profile size
try:
    for p in DXF_PROFILES:
        key = p['profile'] + ' 方管'
        if key not in HOLE_SPECS:
            ps = int(round(p['profile_size'] / 4))
            if ps >= 10:
                HOLE_SPECS[key] = {'beam_cross': f'M{ps}', 'post_tap': f'M{ps*1.2:.0f}'}
except Exception:
    pass

# Document object names (referenced by expressions and cleanup logic)
OBJ_FRAME = 'Frame'
OBJ_PARAMS = 'Parameters'
OBJ_BOM = 'BOM'
OBJ_DIMENSIONS = 'Dimensions'
OBJ_X_BASE = 'XBeamBase'
OBJ_Y_BASE = 'YBeamBase'
OBJ_Z_BASE = 'ZPostBase'
OBJ_LAYER_COMPOUND = 'LayerCompound'
