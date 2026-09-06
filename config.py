# -*- coding: utf-8 -*-
"""
Configuration module for Aluminum Frame Generator.
Separates data from code for easy customization and extension.

Note: all position/length formulas live in position_calculator.py
(single source of truth) — do NOT duplicate them here.
"""

# Profile definitions - currently only square tubes are supported
PROFILES = {
    '20x20 方管': {'type': 'square', 'w': 20, 'h': 20},
    '30x30 方管': {'type': 'square', 'w': 30, 'h': 30},
    '40x40 方管': {'type': 'square', 'w': 40, 'h': 40},
    '60x60 方管': {'type': 'square', 'w': 60, 'h': 60},
}

# Hole / tap specs for bolted connections (edit to match your fasteners):
#   beam_cross: cross-through hole on horizontal beams at Z-post connections
#   post_tap:   tapped hole on Z post ends (top & bottom)
HOLE_SPECS = {
    '20x20 方管': {'beam_cross': 'M5', 'post_tap': 'M6'},
    '30x30 方管': {'beam_cross': 'M6', 'post_tap': 'M8'},
    '40x40 方管': {'beam_cross': 'M8', 'post_tap': 'M10'},
    '60x60 方管': {'beam_cross': 'M10', 'post_tap': 'M12'},
}

# Document object names (referenced by expressions and cleanup logic)
OBJ_FRAME = 'Frame'
OBJ_PARAMS = 'Parameters'
OBJ_BOM = 'BOM'
OBJ_DIMENSIONS = 'Dimensions'
OBJ_X_BASE = 'XBeamBase'
OBJ_Y_BASE = 'YBeamBase'
OBJ_Z_BASE = 'ZPostBase'
OBJ_LAYER_COMPOUND = 'LayerCompound'
