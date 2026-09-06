# -*- coding: utf-8 -*-
"""AlumFrame — Aluminum extrusion frame generator for FreeCAD."""

__all__ = ['PROFILES', 'make_frame', 'get_bom_summary', 'export_bom_csv']

# 延迟导入，避免循环依赖
def __getattr__(name):
    if name in ('PROFILES', 'make_frame', 'get_bom_summary', 'export_bom_csv'):
        from .AlumFrame import PROFILES, make_frame, get_bom_summary, export_bom_csv
        return locals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
