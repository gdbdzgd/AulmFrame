# -*- coding: utf-8 -*-
"""
BOM (Bill of Materials) module for Aluminum Frame Generator.
"""


def create_bom_spreadsheet(doc, beams, material, z_layers):
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
    """
    bom = doc.addObject('Spreadsheet::Sheet', 'BOM')
    bom.Label = u'BOM 规格表'
    
    headers = [u'序号', u'部件', u'型材规格', u'长度(mm)', u'数量', u'材料', u'总长(mm)']
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
        total_len += tl
        row += 1
    
    bom.set('A' + str(row), '')
    bom.set('B' + str(row), u'合计')
    bom.set('G' + str(row), str(total_len))
    
    row += 2
    bom.set('A' + str(row), u'外形尺寸')
    bom.set('B' + str(row), u'Z层数: %d' % z_layers)
    
    return bom


def export_bom_csv(beams, filepath, material='Aluminum 6061'):
    """Export BOM to a CSV file.
    
    Parameters
    ----------
    beams : list
        List of beam metadata
    filepath : str
        Output file path
    material : str
        Material name
    """
    import csv
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([u'序号', u'部件', u'型材规格', u'长度(mm)', u'数量', u'材料', u'总长(mm)'])
        agg = {}
        for b in beams:
            key = (b['part'], b['profile'], b['length'])
            agg[key] = agg.get(key, 0) + b.get('qty', 1)
        total = 0
        for idx, ((part, profile, length), qty) in enumerate(sorted(agg.items()), 1):
            tl = length * qty
            total += tl
            writer.writerow([idx, part, profile, length, qty, material, tl])
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
