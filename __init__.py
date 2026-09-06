# -*- coding: utf-8 -*-
"""
FreeCAD Aluminum Frame Generator - Refactored Version
=====================================================
Generates a centered aluminum extrusion frame using modular architecture.

Structure:
  - config.py: Configuration and constants
  - position_calculator.py: Position calculation based on frame properties
  - beam_factory.py: Beam creation using Part::Box
  - frame_builder.py: Main builder orchestrating frame creation
  - bom.py: BOM spreadsheet generation
  - measurements.py: Dimension annotations
"""

# Version info
__version__ = '2.0.0'
__author__ = 'AlumFrame Team'

# Import main entry point
from .frame_builder import FrameBuilder
from .config import PROFILES


def make_frame(profile, length, width, height, material='Aluminum 6061', z_layers=1):
    """Build an aluminum frame - main entry point.
    
    Parameters
    ----------
    profile : str
        Profile specification from PROFILES
    length : float
        Frame outer dimension along X (mm)
    width : float
        Frame outer dimension along Y (mm)
    height : float
        Frame outer dimension along Z (mm)
    material : str
        Material label for BOM
    z_layers : int
        Number of Z horizontal layers
        
    Returns
    -------
    doc : FreeCAD document
    beams : list
        List of beam metadata
    """
    builder = FrameBuilder()
    return builder.build_frame(profile, length, width, height, material, z_layers)


# Backward compatibility
from .bom import get_bom_summary, export_bom_csv
