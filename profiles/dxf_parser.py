# -*- coding: utf-8 -*-
"""
DXF Profile Parser for Aluminum Frame Generator.

Parses 2D DXF files and extracts the main profile contour.
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
    lines = []
    
    for e in entities:
        if e.get('type') == 'LINE':
            x1 = float(e.get('10', 0))
            y1 = float(e.get('20', 0))
            x2 = float(e.get('11', 0))
            y2 = float(e.get('21', 0))
            # Filter extreme values
            if abs(x1) < 5000 and abs(y1) < 5000 and abs(x2) < 5000 and abs(y2) < 5000:
                xs.extend([x1, x2])
                ys.extend([y1, y2])
                lines.append((x1, y1, x2, y2))
    
    if not xs:
        return None
    
    # Find centroid
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    
    # Find distance of each point from centroid
    dists = []
    for x, y in zip(xs, ys):
        d = ((x - cx)**2 + (y - cy)**2)**0.5
        dists.append(d)
    
    # Use 80% closest points for bbox
    dists_sorted = sorted(dists)
    cutoff = dists_sorted[int(len(dists_sorted) * 0.8)]
    
    # Filter lines within cutoff
    filtered = []
    for l in lines:
        x1, y1, x2, y2 = l
        d1 = ((x1 - cx)**2 + (y1 - cy)**2)**0.5
        d2 = ((x2 - cx)**2 + (y2 - cy)**2)**0.5
        if d1 <= cutoff and d2 <= cutoff:
            filtered.append(l)
    
    # Get filtered bbox
    if filtered:
        x_coords = [l[0] for l in filtered] + [l[2] for l in filtered]
        y_coords = [l[1] for l in filtered] + [l[3] for l in filtered]
        return {
            'width': max(x_coords) - min(x_coords),
            'height': max(y_coords) - min(y_coords),
            'x_min': min(x_coords),
            'x_max': max(x_coords),
            'y_min': min(y_coords),
            'y_max': max(y_coords),
            'lines': filtered
        }
    
    return {
        'width': max(xs) - min(xs),
        'height': max(ys) - min(ys),
        'x_min': min(xs),
        'x_max': max(xs),
        'y_min': min(ys),
        'y_max': max(ys),
        'lines': lines
    }


def get_profile_for_size(size, dxf_dir=None):
    """Get profile info for a given size string like '20x20', '30x30', etc."""
    if dxf_dir is None:
        dxf_dir = os.path.join(os.path.dirname(__file__), 'dxf')
    
    name_map = {
        '20x20': 'nfs5-2020.dxf',
        '30x30': 'LCF8-3030.dxf',
        '40x40': 'hfs8-4040.dxf',
        '60x60': None,
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
    
    seen = {}
    for fname in sorted(os.listdir(dxf_dir)):
        if not fname.endswith('.dxf'):
            continue
        
        base = fname.replace('.dxf', '')
        size_match = re.search(r'(\d{2})x?(\d{2})', base)
        if size_match:
            size = f"{size_match.group(1)}x{size_match.group(2)}"
        else:
            continue
        
        p = get_profile_for_size(size, dxf_dir)
        if p:
            if size not in seen:
                seen[size] = p
                profiles.append(p)
            elif len(p['bbox'].get('lines', [])) > len(seen[size]['bbox'].get('lines', [])):
                seen[size] = p
                profiles = [x for x in profiles if x['profile'] != size] + [p]
    return profiles