# -*- coding: utf-8 -*-
"""
DXF Profile Parser for Aluminum Frame Generator.

Parses 2D DXF files from MISUMI/铝型材-米思米 resources and
provides profile geometry for beam generation.
"""

import os
import re


def parse_dxf_tokens(path):
    """Parse DXF file into list of (code, value) tokens."""
    with open(path, 'r', errors='replace') as f:
        content = f.read()
    
    tokens = []
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        code = lines[i].strip()
        i += 1
        if i >= len(lines):
            break
        value = lines[i].strip()
        i += 1
        tokens.append((code, value))
    return tokens


def extract_entities(tokens):
    """Extract entities from DXF tokens."""
    entities = []
    in_entities = False
    current = None
    
    for code, value in tokens:
        if code == '2' and value == 'ENTITIES':
            in_entities = True
        elif code == '0' and value == 'ENDSEC' and in_entities:
            in_entities = False
        elif in_entities and code == '0':
            if current:
                entities.append(current)
            current = {'type': value}
        elif in_entities and current is not None:
            current[code] = value
    
    if current:
        entities.append(current)
    return entities


def get_profile_bbox(entities):
    """Get bounding box of profile from entities."""
    xs, ys = [], []
    circles = []
    arcs = []
    
    for e in entities:
        etype = e.get('type')
        if etype == 'LINE':
            x1 = float(e.get('10', 0))
            y1 = float(e.get('20', 0))
            x2 = float(e.get('11', 0))
            y2 = float(e.get('21', 0))
            # Filter out extreme values (likely annotation errors)
            if abs(x1) < 5000 and abs(y1) < 5000:
                xs.extend([x1, x2])
                ys.extend([y1, y2])
        elif etype == 'CIRCLE':
            cx = float(e.get('10', 0))
            cy = float(e.get('20', 0))
            r = float(e.get('40', 0))
            circles.append((cx, cy, r))
        elif etype == 'ARC':
            cx = float(e.get('10', 0))
            cy = float(e.get('20', 0))
            r = float(e.get('40', 0))
            thetas = [float(e.get('50', 0)), float(e.get('51', 0))]
            arcs.append((cx, cy, r, thetas))
    
    if xs:
        return {
            'width': max(xs) - min(xs),
            'height': max(ys) - min(ys),
            'x_min': min(xs),
            'x_max': max(xs),
            'y_min': min(ys),
            'y_max': max(ys),
            'circles': circles,
            'arcs': arcs,
            'lines': [(float(e.get('10', 0)), float(e.get('20', 0)),
                      float(e.get('11', 0)), float(e.get('21', 0)))
                      for e in entities if e.get('type') == 'LINE']
        }
    return None


def get_profile_for_size(size, dxf_dir=None):
    """Get profile info for a given size string like '20x20', '30x30', etc.
    
    Parameters
    ----------
    size : str
        Profile size like '20x20', '40x40'
    dxf_dir : str, optional
        Path to DXF directory
    """
    if dxf_dir is None:
        dxf_dir = os.path.join(os.path.dirname(__file__), 'dxf')
    
    # Map size to DXF filename
    name_map = {
        '20x20': 'nfs5-2020.dxf',
        '30x30': 'LCF8-3030.dxf',
        '40x40': 'nfs5-4040.dxf',
        '60x60': None,  # no 6060 DXF available
    }
    
    size_lower = size.lower().replace('方管', '').strip()
    dxf_name = name_map.get(size_lower)
    if not dxf_name:
        dxf_name = f'nfs5-{size_lower.replace("x", "")}.dxf'
    
    dxf_path = os.path.join(dxf_dir, dxf_name)
    if not os.path.exists(dxf_path):
        return None
    
    tokens = parse_dxf_tokens(dxf_path)
    entities = extract_entities(tokens)
    bbox = get_profile_bbox(entities)
    
    if bbox:
        return {
            'profile': size,
            'width': bbox['width'],
            'height': bbox['height'],
            'profile_size': min(bbox['width'], bbox['height']),
            'bbox': bbox,
            'dxf_file': dxf_path
        }
    return None


def get_all_profiles(dxf_dir=None):
    """Get list of all available profiles."""
    profiles = []
    if dxf_dir is None:
        dxf_dir = os.path.join(os.path.dirname(__file__), 'dxf')
    
    if not os.path.exists(dxf_dir):
        return profiles
    
    for fname in sorted(os.listdir(dxf_dir)):
        if not fname.endswith('.dxf'):
            continue
        
        # Extract size from filename like nfs5-2020.dxf -> 20x20
        # or LCF8-3030.dxf -> 30x30
        base = fname.replace('.dxf', '')
        
        # Try common patterns: LCF8-3030 -> 30x30, nfs5-2020 -> 20x20
        size_match = re.search(r'(\d{2})x?(\d{2})', base)
        if size_match:
            size = f"{size_match.group(1)}x{size_match.group(2)}"
        else:
            size_match = re.search(r'(\d{2})(\d{2})$', base)
            if size_match:
                size = f"{size_match.group(1)}x{size_match.group(2)}"
            else:
                continue
        
        p = get_profile_for_size(size, dxf_dir)
        if p:
            profiles.append(p)
    return profiles