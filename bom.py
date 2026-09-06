# -*- coding: utf-8 -*-
"""
BOM (Bill of Materials) module for Aluminum Frame Generator.
"""


def create_bom_spreadsheet(doc, beams, material, z_layers,
                           hole_spec=None, profile_size=0):
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
        bom.set('H' + str(row),
                hole_note(part, length, hole_spec, profile_size))
        total_len += tl
        row += 1
    
    bom.set('A' + str(row), '')
    bom.set('B' + str(row), u'合计')
    bom.set('G' + str(row), str(total_len))
    
    row += 2
    bom.set('A' + str(row), u'外形尺寸')
    bom.set('B' + str(row), u'Z层数: %d' % z_layers)
    
    return bom


def hole_note(part, length, hole_spec=None, profile_size=0):
    """Compute hole/tap positions for one beam type (detailed per-hole list).

    - Horizontal beams (X/Y): cross-through holes at both ends where they
      connect to the Z posts.  Each cross-hole site has 2 perpendicular holes
      along the two transverse axes (forming a '+').  Listed per instance.
    - Z posts: tapped hole on top & bottom end faces (each 1 hole along beam
      axis).  Listed per instance.

    Returns a multi-line human-readable note string ('' when no spec given).
    """
    if not hole_spec or profile_size <= 0:
        return ''
    c = profile_size / 2.0  # center offset from end face = profile/2
    h = profile_size / 2.0  # center height in profile cross-section

    if part in (u'X-横梁', u'Y-纵梁'):
        d = hole_spec['beam_cross']
        lb = length  # net beam length
        p1 = c                          # distance from near end face
        p2 = round(lb - c, 1)           # distance from far end face
        # Transverse axes differ by beam orientation
        if part == u'X-横梁':
            trans = u'Y+Z'
            p1_coord = '(x=%.0f, y=%.0f, z=%.0f)' % (p1, h, h)
            p2_coord = '(x=%.0f, y=%.0f, z=%.0f)' % (p2, h, h)
        else:
            trans = u'X+Z'
            p1_coord = '(x=%.0f, y=%.0f, z=%.0f)' % (h, p1, h)
            p2_coord = '(x=%.0f, y=%.0f, z=%.0f)' % (h, p2, h)
        return (
            u'每根2处十字孔，每处2孔（%s轴⊥梁轴），截面中心z=%.0fmm\n'
            u'  孔1: %s距端面%.0fmm  %s\n'
            u'  孔2: %s距端面%.0fmm  %s'
            % (trans, h,
               d, p1, p1_coord,
               d, p2, p2_coord))

    if part == u'Z-立柱':
        d = hole_spec['post_tap']
        depth = round(int(d[1:]) * 1.5)
        p1 = c
        p2 = round(length - c, 1)
        return (
            u'每根2处攻丝（沿Z轴），截面中心\n'
            u'  底孔: %s距底面%.0fmm  (x=%.0f, y=%.0f, z=%.0f)\n'
            u'  顶孔: %s距底面%.0fmm  (x=%.0f, y=%.0f, z=%.0f)'
            % (d, p1, h, h, p1,
               d, p2, h, h, p2))
    return ''


def export_bom_csv(beams, filepath, material='Aluminum 6061',
                   hole_spec=None, profile_size=0):
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
                             hole_note(part, length, hole_spec, profile_size)])
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
