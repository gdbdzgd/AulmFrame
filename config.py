# -*- coding: utf-8 -*-
"""
Configuration module for Aluminum Frame Generator.
Separates data from code for easy customization and extension.

Note: all position/length formulas live in position_calculator.py
(single source of truth) — do NOT duplicate them here.
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
