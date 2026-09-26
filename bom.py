# -*- coding: utf-8 -*-
"""
BOM (Bill of Materials) module for Aluminum Frame Generator.
"""


def create_bom_spreadsheet(doc, beams, material, z_layers,
                           hole_spec=None, profile_size=0,
                           z_layer_positions=None, hole_notes=None,
                           hardware=None, connection=None):
    """Create a BOM spreadsheet in the document.

    Parameters
    ----------
    doc : FreeCAD document
    beams : list
        List of beam metadata dictionaries
    material : str
        Material name
    z_layers : int
        Number of Z layers
    hole_spec : dict, optional
        Hole/tap spec from config.HOLE_SPECS for the current profile:
        {'beam_cross': 'M5', 'post_tap': 'M6'}
    profile_size : float, optional
        Profile width (mm), used to compute hole positions
    z_layer_positions : list, optional
        Z positions of each layer (mm), for Z post hole calculation
    hole_notes : dict, optional
        Pre-computed per-part machining notes
        (u'X-横梁' / u'Y-纵梁' / u'Z-立柱' -> text). Overrides the default
        per-profile hole_note() when the connection method supplies its own.
    hardware : list, optional
        [(name, qty)] connector hardware summary.
    connection : str, optional
        Connection method id used for this frame.
    """
    bom = doc.addObject('Spreadsheet::Sheet', 'BOM')
    bom.Label = u'BOM 规格表'
    
    headers = [u'序号', u'部件', u'型材规格', u'长度(mm)', u'数量', u'材料',
               u'总长(mm)', u'打孔说明']
    for col, h in enumerate(headers):
        bom.set(chr(ord('A') + col) + '1', h)
    
    agg = {}
    for b in beams:
        key = (b['part'], b['profile'], b['length'])
        agg[key] = agg.get(key, 0) + b.get('qty', 1)
    
    row = 2
    total_len = 0
    for idx, ((part, profile, length), qty) in enumerate(sorted(agg.items()), 1):
        bom.set('A' + str(row), str(idx))
        bom.set('B' + str(row), part)
        bom.set('C' + str(row), profile)
        bom.set('D' + str(row), str(length))
        bom.set('E' + str(row), str(qty))
        bom.set('F' + str(row), material)
        tl = length * qty
        bom.set('G' + str(row), str(tl))
        if hole_notes and part in hole_notes:
            bom.set('H' + str(row), hole_notes[part])
        else:
            bom.set('H' + str(row),
                    hole_note(part, length, hole_spec, profile_size,
                              z_layers=z_layers,
                              z_layer_positions=z_layer_positions))
        total_len += tl
        row += 1
    
    bom.set('A' + str(row), '')
    bom.set('B' + str(row), u'合计')
    bom.set('G' + str(row), str(total_len))
    
    row += 2
    bom.set('A' + str(row), u'外形尺寸')
    bom.set('B' + str(row), u'Z层数: %d' % z_layers)
    if connection:
        row += 1
        bom.set('A' + str(row), u'连接方式')
        bom.set('B' + str(row), connection)

    if hardware:
        row += 2
        bom.set('A' + str(row), u'连接五金')
        bom.set('B' + str(row), u'名称')
        bom.set('C' + str(row), u'数量')
        row += 1
        for name, qty in hardware:
            bom.set('B' + str(row), name)
            bom.set('C' + str(row), str(qty))
            row += 1

    return bom


def hole_note(part, length, hole_spec=None, profile_size=0,
              z_layers=0, z_layer_positions=None):
    """Compute hole/tap positions for one beam type (detailed per-hole list).

    Parameters
    ----------
    part : str
        Beam type (u'X-横梁', u'Y-纵梁', u'Z-立柱')
    length : float
        Beam length (mm)
    hole_spec : dict, optional
        {'beam_cross': 'M5', 'post_tap': 'M6'}
    profile_size : float
        Profile width (mm)
    z_layers : int
        Number of Z horizontal layers (for Z post holes)
    z_layer_positions : list, optional
        Z positions of each layer (mm). If None, only bottom+top holes.

    Returns
    -------
    str
        Multi-line note with per-hole coordinates.
    """
    if not hole_spec or profile_size <= 0:
        return ''
    c = profile_size / 2.0  # center offset from end face
    h = profile_size / 2.0  # center height in profile cross-section

    if part in (u'X-横梁', u'Y-纵梁'):
        d = hole_spec['post_tap']
        depth = round(int(d[1:]) * 1.5)
        lb = length
        p1 = 0.0
        p2 = lb
        
        if part == u'X-横梁':
            coord1 = '(x=%.0f, y=%.0f, z=%.0f)' % (p1, h, h)
            coord2 = '(x=%.0f, y=%.0f, z=%.0f)' % (p2, h, h)
        else:
            coord1 = '(x=%.0f, y=%.0f, z=%.0f)' % (h, p1, h)
            coord2 = '(x=%.0f, y=%.0f, z=%.0f)' % (h, p2, h)
        
        return (
            u'每根2处攻丝（沿梁轴），截面中心\n'
            u'  端1: %s距端面%.0fmm 深%.0fmm  %s\n'
            u'  端2: %s距端面%.0fmm 深%.0fmm  %s'
            % (d, p1, depth, coord1,
               d, p2, depth, coord2))

    if part == u'Z-立柱':
        cross_d = hole_spec['beam_cross']
        tap_d = hole_spec['post_tap']
        tap_depth = round(int(tap_d[1:]) * 1.5)
        h = profile_size / 2.0

        if z_layer_positions:
            positions = z_layer_positions
        else:
            positions = [c, round(length - c, 1)]

        lines = []
        for i, z in enumerate(positions):
            coord = '(x=%.0f, y=%.0f, z=%.0f)' % (h, h, z)

            if i == 0 or i == len(positions) - 1:
                label = u'底部' if i == 0 else u'顶部'
                lines.append(
                    u'  %s: %s十字通孔 + %s攻丝 距底面%.0fmm/深%.0fmm  %s'
                    % (label, cross_d, tap_d, z, tap_depth, coord))
            else:
                label = u'第%d层' % (i + 1)
                lines.append(
                    u'  %s: %s十字通孔  %s'
                    % (label, cross_d, coord))

        total = len(positions)
        return (u'Z柱 %d层：每层%s十字通孔，顶底%s攻丝\n%s'
                % (total, cross_d, tap_d, '\n'.join(lines)))
    return ''


def export_bom_csv(beams, filepath, material='Aluminum 6061',
                   hole_spec=None, profile_size=0,
                   z_layers=0, z_layer_positions=None):
    """Export BOM to a CSV file.

    Parameters
    ----------
    beams : list
        List of beam metadata
    filepath : str
        Output file path
    material : str
        Material name
    hole_spec : dict, optional
        Hole/tap spec from config.HOLE_SPECS (adds a hole-note column)
    profile_size : float, optional
        Profile width (mm) for hole position computation
    z_layers : int, optional
        Number of Z layers
    z_layer_positions : list, optional
        Z positions of each layer (mm)
    """
    import csv
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([u'序号', u'部件', u'型材规格', u'长度(mm)', u'数量',
                         u'材料', u'总长(mm)', u'打孔说明'])
        agg = {}
        for b in beams:
            key = (b['part'], b['profile'], b['length'])
            agg[key] = agg.get(key, 0) + b.get('qty', 1)
        total = 0
        for idx, ((part, profile, length), qty) in enumerate(sorted(agg.items()), 1):
            tl = length * qty
            total += tl
            writer.writerow([idx, part, profile, length, qty, material, tl,
                             hole_note(part, length, hole_spec, profile_size,
                                       z_layers=z_layers,
                                       z_layer_positions=z_layer_positions)])
        writer.writerow(['', u'合计', '', '', '', '', total])


def get_bom_summary(beams):
    """Summarize BOM by part type + profile.
    
    Parameters
    ----------
    beams : list
        List of beam metadata
        
    Returns
    -------
    dict
        Summary dictionary
    """
    summary = {}
    for b in beams:
        key = b['part'] + ' (' + b['profile'] + ')'
        if key not in summary:
            summary[key] = {'length': 0, 'qty': 0}
        summary[key]['length'] += b['length'] * b.get('qty', 1)
        summary[key]['qty'] += b.get('qty', 1)
    return summary


def export_bom_sheet_csv(bom_obj, filepath):
    """Export an existing BOM spreadsheet object to a CSV file."""
    import csv
    cols = 'ABCDEFGH'
    rows = []
    blanks = 0
    for r in range(1, 400):
        line = []
        empty = True
        for c in cols:
            try:
                v = bom_obj.get(c + str(r))
            except Exception:
                v = None
            if v not in (None, ''):
                empty = False
            line.append('' if v is None else v)
        if empty:
            blanks += 1
            if blanks >= 3 and rows:
                break
            continue
        blanks = 0
        rows.append(line)
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    return filepath
