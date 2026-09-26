# -*- coding: utf-8 -*-
"""
TechDraw drawing generation for aluminum frames.

Creates a single TechDraw page holding every member specification (X beam /
Y beam / Z post): each spec gets a lengthwise view + an end view plus an
annotation listing the profile spec, quantity and the hole machining method
required by the selected connection.

All objects are named with a ``TD_`` prefix so the frame rebuild can clean
them up together with the rest of the frame.
"""

import os

try:
    import FreeCAD
except ImportError:
    FreeCAD = None


from .i18n import current_language, tr

PAGE_PREFIX = 'TD_'


def _template_path():
    """Prefer the bundled A2 landscape template with border, then A4."""
    bundled = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'templates', 'A2_Landscape.svg')
    if os.path.exists(bundled):
        return bundled
    try:
        res = FreeCAD.getResourceDir()
    except Exception:
        return None
    path = os.path.join(res, 'Mod', 'TechDraw', 'Templates',
                        'Default_Template_A4_Landscape.svg')
    return path if os.path.exists(path) else None


MARGIN = 22.0
TOP = 22.0
BOTTOM = 22.0
ROW_GAP = 3.0
END_BOX = 46.0


def plan_layout(items, page_w, page_h, keepout=None):
    """Plan the drawing layout: one common scale, members aligned left.

    Parameters
    ----------
    items : list of (length, cross_max)
        Member length and its largest cross-section dimension (mm).
    page_w, page_h : float
        Sheet size (mm).

    Returns
    -------
    dict with 'scale', 'row_h' and 'rows': list of
    {'x_left', 'x_center', 'y_center', 'row_top', 'end_x', 'end_scale'}.
    Drawn length never exceeds the available drawing width.
    """
    n = max(len(items), 1)

    # Reserve the title block: when it sits in the lower half of the sheet,
    # keep all rows above it.
    bottom = BOTTOM
    if keepout is not None:
        _kx0, _ky0, _kx1, _ky1 = keepout
        if _ky1 < page_h * 0.5:
            bottom = max(bottom, _ky1 + 6.0)

    draw_w = max(page_w - 2 * MARGIN - END_BOX - 10.0, 10.0)
    row_h = (page_h - TOP - bottom - ROW_GAP * (n - 1)) / n

    scale = 1.0
    for length, cross_max in items:
        scale = min(scale, draw_w / max(length, 1e-6),
                    (row_h * 0.52) / max(cross_max, 1e-6))
    scale = max(scale, 1e-5)

    rows = []
    for i, (length, cross_max) in enumerate(items):
        row_top = page_h - TOP - i * (row_h + ROW_GAP)
        row_cy = row_top - row_h / 2.0
        drawn = length * scale
        rows.append({
            'x_left': MARGIN,
            'x_center': MARGIN + drawn / 2.0,   # one-end aligned (left)
            'y_center': row_cy + row_h * 0.10,
            'row_top': row_top,
            'row_h': row_h,
            'drawn': drawn,
            'end_x': page_w - MARGIN - END_BOX / 2.0,
            'end_scale': min(scale, END_BOX / max(cross_max, 1e-6)),
        })
    return {'scale': scale, 'row_h': row_h, 'draw_w': draw_w,
            'bottom': bottom, 'rows': rows}


def _template_keepout(template_path, page_w, page_h):
    """Return the title-block keep-out rect in page coords (Y up), or None.

    The template marks its title block with id="titleblock"; the rect is
    given in SVG coordinates (Y down) and converted to page coordinates.
    """
    try:
        import re
        head = open(template_path, encoding='utf-8', errors='replace').read()
        m = re.search(r'<rect[^>]*id="titleblock"[^>]*>', head)
        if not m:
            return None
        tag = m.group(0)
        def val(name):
            mm = re.search(r'%s="([0-9.]+)"' % name, tag)
            return float(mm.group(1)) if mm else None
        x, y = val('x'), val('y')
        w, h = val('width'), val('height')
        if None in (x, y, w, h):
            return None
        return (x, page_h - (y + h), x + w, page_h - y)
    except Exception:
        return None


def _template_size(template_path, default=(297.0, 210.0)):
    """Read the page size (mm) from the SVG template header."""
    try:
        import re
        head = open(template_path, encoding='utf-8', errors='replace').read(800)
        mw = re.search(r'width\s*=\s*"([0-9.]+)\s*mm"', head)
        mh = re.search(r'height\s*=\s*"([0-9.]+)\s*mm"', head)
        if mw and mh:
            return float(mw.group(1)), float(mh.group(1))
        mw = re.search(r'width\s*=\s*"([0-9.]+)"', head)
        mh = re.search(r'height\s*=\s*"([0-9.]+)"', head)
        if mw and mh:
            return float(mw.group(1)), float(mh.group(1))
    except Exception:
        pass
    return default


def _to_fullwidth(text):
    """Convert ASCII to full-width forms so every glyph is the same width.

    TechDraw renders CJK at ~1.49em and ASCII at ~0.91em; mixing them makes
    equal character counts unequal in width. Full-width forms unify the
    advance, so padded (equal-length) lines render equally wide and every
    annotation block gets the exact same left edge.
    """
    out = []
    for ch in text or '':
        o = ord(ch)
        if o == 0x20:
            out.append(u'\u3000')
        elif 0x21 <= o <= 0x7E:
            out.append(chr(o + 0xFEE0))
        else:
            out.append(ch)
    return ''.join(out)


def _wrap(text, width):
    """Soft-wrap a line to at most `width` characters."""
    text = text or ''
    return [text[i:i + width] for i in range(0, len(text), width)] or ['']


def _set_line_width(view, width):
    """Set the TechDraw line width (a Gui-side property)."""
    try:
        import FreeCADGui
        gv = FreeCADGui.ActiveDocument.getObject(view.Name)
        if gv is not None and hasattr(gv, 'LineWidth'):
            gv.LineWidth = width
    except Exception:
        pass


def _materialize_template(template, values):
    """Write a copy of the template with editable fields filled in.

    TechDraw's page only substitutes editable fields reliably when they are
    present in the template file itself, so a per-frame copy is generated.
    Returns the new path (or the original on failure).
    """
    try:
        import hashlib
        import re
        cache = os.path.join(os.path.expanduser('~'), '.cache', 'AlumFrame')
        os.makedirs(cache, exist_ok=True)
        with open(template, encoding='utf-8', errors='replace') as f:
            svg = f.read()
        for key, value in (values or {}).items():
            if not key:
                continue
            pat = re.compile(r'(<text[^>]*freecad:editable="%s"[^>]*>)[^<]*(</text>)'
                             % re.escape(key))
            svg = pat.sub(lambda m, v=str(value): m.group(1) + v + m.group(2), svg)
        if current_language() == 'en':
            for zh in (u'铝型材加工图纸', u'规格:', u'比例:', u'图号:',
                       u'材料:', u'连接:'):
                svg = svg.replace('>%s<' % zh, '>%s<' % tr(zh))
        digest = hashlib.md5(svg.encode('utf-8')).hexdigest()[:12]
        out = os.path.join(cache, 'A2_%s.svg' % digest)
        with open(out, 'w', encoding='utf-8') as f:
            f.write(svg)
        return out
    except Exception:
        return template


def _new_page(doc, name, template):
    page = doc.addObject('TechDraw::DrawPage', PAGE_PREFIX + 'Page_' + name)
    page.Label = tr(u'图纸') + ' ' + name
    tpl = doc.addObject('TechDraw::DrawSVGTemplate', PAGE_PREFIX + 'Tpl_' + name)
    tpl.Template = template
    page.Template = tpl
    return page


def create_techdraw_bom(doc, base_specs, hole_notes, profile, material,
                        connection, z_layers=None):
    """Create TechDraw pages for the BOM and for every member spec.

    Parameters
    ----------
    doc : FreeCAD document
    base_specs : list of dict
        [{'key': 'X'|'Y'|'Z', 'label': u'X-横梁', 'base': obj,
          'length': float, 'qty': int}]
    hole_notes : dict
        {label: multi-line machining note}
    profile : str
        Profile spec string
    material : str
    connection : str
        Connection method id (used for the page title)
    z_layers : int, optional
    """
    if FreeCAD is None:
        return []
    try:
        import TechDraw  # noqa: F401
    except ImportError:
        return []

    template = _template_path()
    if not template:
        FreeCAD.Console.PrintWarning(
            u'AlumFrame: TechDraw template not found; skipping drawings\n')
        return []

    try:
        from .connections import method_label
        # method_label() may have been captured at import time; translate
        # again here so the label follows the language used at build time.
        conn_label = tr(method_label(connection))
    except Exception:
        conn_label = connection

    pages = []

    # ---- Single page with every member specification ----
    page = _new_page(doc, 'Specs', template)
    page.Label = tr(u'型材加工图纸')
    page_w, page_h = _template_size(template)

    # Fill the template's editable title-block fields (best effort)
    try:
        tpl_obj = page.Template
        fields = {'spec': profile, 'sheet': '1/1',
                  'material': material, 'note': conn_label}
        if hasattr(tpl_obj, 'setEditFieldContent'):
            for k, v in fields.items():
                try:
                    tpl_obj.setEditFieldContent(k, v)
                except Exception:
                    pass
        elif hasattr(tpl_obj, 'EditableTexts'):
            tpl_obj.EditableTexts = fields
    except Exception:
        pass

    margin = MARGIN
    valid_specs = [sp for sp in base_specs if sp.get('base') is not None]

    extents = {}
    layout_items = []
    for sp in valid_specs:
        b = sp['base'].Shape.BoundBox
        dx, dy, dz = b.XMax - b.XMin, b.YMax - b.YMin, b.ZMax - b.ZMin
        key = sp['key']
        if key == 'X':
            longest, cross_w, cross_h = dx, dy, dz
        elif key == 'Y':
            longest, cross_w, cross_h = dy, dx, dz
        else:
            longest, cross_w, cross_h = dz, dx, dy
        extents[key] = (longest, cross_w, cross_h)
        layout_items.append((longest, max(cross_w, cross_h)))

    keepout = _template_keepout(template, page_w, page_h)
    layout = plan_layout(layout_items, page_w, page_h, keepout=keepout)
    common_scale = layout['scale']

    try:
        tpl_obj = page.Template
        ratio = 1.0 / common_scale if common_scale < 0.999 else 1.0
        if hasattr(tpl_obj, 'setEditFieldContent'):
            tpl_obj.setEditFieldContent('scale', '1:%.1f' % ratio)
        elif hasattr(tpl_obj, 'EditableTexts'):
            d = dict(tpl_obj.EditableTexts or {})
            d['scale'] = '1:%.1f' % ratio
            tpl_obj.EditableTexts = d
    except Exception:
        pass
    row_h = layout['row_h']

    # Bake the title-block values into the template file so the TechDraw page
    # itself (and any export) shows them.
    ratio_txt = '1:%.1f' % (1.0 / common_scale if common_scale < 0.999 else 1.0)
    baked = _materialize_template(template, {
        'spec': profile, 'scale': ratio_txt, 'sheet': '1/1',
        'material': material, 'note': conn_label})
    try:
        page.Template.Template = baked
        page.Template.EditableTexts = {
            'spec': profile, 'scale': ratio_txt, 'sheet': '1/1',
            'material': material, 'note': conn_label}
        page.Template.touch()
    except Exception:
        pass

    # ---- annotation text: wrap to frame width, pad to a common column ----
    tsize = 1.6
    char_w = tsize * 1.44             # full-width glyph advance (calibrated)
    avail_w = page_w - 2 * MARGIN
    max_chars = max(int(avail_w / char_w), 8)

    def _spec_note_lines(sp):
        _l, cw, ch = extents[sp['key']]
        _e = max(min(1.0, END_BOX / max(cw, 1e-6),
                     END_BOX / max(ch, 1e-6)), 0.2)
        _dr = 1.0 / _e if _e < 0.999 else 1.0
        head = [
            tr(u'部件: %s') % tr(sp['label']),
            tr(u'规格: %s   长度: %.0f mm   数量: %d')
            % (profile, sp['length'], sp['qty']),
            tr(u'主视图比例 1:%.1f（各型材一致，便于比长短）')
            % (1.0 / common_scale if common_scale < 0.999 else 1.0),
            tr(u'端面视图为细节，比例 1:%.1f') % _dr,
            u'—' * 22,
            tr(u'打孔方式:'),
        ]
        out = []
        for raw in head:
            out.extend(_wrap(raw, max_chars))
        note = (hole_notes or {}).get(sp['label'], '')
        if note:
            for raw in note.split('\n'):
                out.extend(_wrap(raw, max_chars))
        else:
            out.append(tr(u'无型材加工'))
        return out

    note_lines = {sp['key']: _spec_note_lines(sp) for sp in valid_specs}
    align_chars = min(max((len(ln) for ls in note_lines.values()
                          for ln in ls), default=8), max_chars)
    align_x = MARGIN + min(align_chars * char_w, avail_w) / 2.0

    annotations = []

    # One row per spec, full sheet width, longest side horizontal
    for i, spec in enumerate(valid_specs):
        key = spec['key']
        base = spec['base']
        direction = (0.0, -1.0, 0.0) if key in ('X', 'Z') else (-1.0, 0.0, 0.0)
        longest, cross_w, cross_h = extents[key]
        cross_max = max(cross_w, cross_h, 1e-6)

        plan = layout['rows'][i]
        y_top = plan['row_top']
        row_cy = plan['y_center']

        # Same scale for every member (longest side defines the scale)
        main_scale = common_scale

        try:
            view = doc.addObject('TechDraw::DrawViewPart', PAGE_PREFIX + 'View_' + key)
            view.Label = u'主视图 ' + spec['label']
            view.Source = [base]
            view.Direction = direction
            try:
                view.ScaleType = 'Custom'
            except Exception:
                pass
            view.Scale = main_scale
            # dir(-X) and dir(-Y) both render the member length vertically;
            # rotate so the longest side lies horizontally.
            if key in ('Y', 'Z'):
                view.Rotation = 90.0
            page.addView(view)
            view.ScaleType = 'Custom'
            view.Scale = main_scale
            view.X, view.Y = plan['x_center'], plan['y_center']
            _set_line_width(view, 0.10 if main_scale < 0.1 else 0.18)
            view.touch()
        except Exception as exc:
            FreeCAD.Console.PrintWarning(
                u'AlumFrame: TechDraw view failed for %s (%s)\n' % (key, exc))

        # End view (cross-section) on the right of the row
        end_direction = (1.0, 0.0, 0.0) if key == 'X' else (
            (0.0, 1.0, 0.0) if key == 'Y' else (0.0, 0.0, 1.0))
        # End view is a DETAIL view: independent scale, fitted to its box so
        # the cross-section (T-slots, holes) stays visible even for very long
        # members drawn at a small common scale.
        end_scale = min(1.0, END_BOX / max(cross_w, 1e-6),
                        END_BOX / max(cross_h, 1e-6))
        end_scale = max(end_scale, 0.2)
        try:
            end = doc.addObject('TechDraw::DrawViewPart', PAGE_PREFIX + 'End_' + key)
            end.Label = u'端面视图 ' + spec['label']
            end.Source = [base]
            end.Direction = end_direction
            try:
                end.ScaleType = 'Custom'
            except Exception:
                pass
            end.Scale = end_scale
            if key in ('Y', 'Z'):
                end.Rotation = 90.0
            page.addView(end)
            end.ScaleType = 'Custom'
            end.Scale = end_scale
            end.X, end.Y = plan['end_x'], plan['y_center']
            _set_line_width(end, 0.25)
            end.touch()
        except Exception as exc:
            FreeCAD.Console.PrintWarning(
                u'AlumFrame: TechDraw end view failed for %s (%s)\n' % (key, exc))

        # Annotation block (spec / quantity / machining method), left aligned
        conv = _to_fullwidth if current_language() == 'zh' else (lambda t: t)
        lines = [conv(ln) for ln in note_lines.get(key, [])]
        # A rule line identical in every annotation makes all blocks exactly
        # the same width, so a shared X gives an identical left edge.
        lines.append(u'\u2500' * align_chars)
        try:
            ann = doc.addObject('TechDraw::DrawViewAnnotation', PAGE_PREFIX + 'Note_' + key)
            ann.Label = u'打孔说明 ' + spec['label']
            ann.Text = lines
            page.addView(ann)
            annotations.append(ann)
            ann.TextSize = tsize
            est_h = len(lines) * tsize * 1.9
            ann.X = align_x
            ann.Y = (y_top - row_h) + est_h / 2.0 + 1.0
        except Exception as exc:
            FreeCAD.Console.PrintWarning(
                u'AlumFrame: TechDraw annotation failed for %s (%s)\n' % (key, exc))

    pages.append(page)

    try:
        doc.recompute()
    except Exception:
        pass


    # Best-effort: ask the GUI to build the projected geometry right away.
    try:
        import FreeCADGui
        for obj in doc.Objects:
            if obj.Name.startswith(PAGE_PREFIX) and \
                    obj.TypeId == 'TechDraw::DrawViewPart':
                gv = FreeCADGui.ActiveDocument.getObject(obj.Name)
                if gv is not None:
                    gv.update()
        FreeCADGui.updateGui()
    except Exception:
        pass
    return pages


def export_page_pdf(page, filepath):
    """Export a TechDraw page to PDF/SVG **including the template border**.

    TechDraw's SVG/PDF export draws only the page content, not the template
    background, so the border/title block would be missing. The content SVG
    is merged into the template SVG here, then converted to PDF.
    """
    try:
        import TechDrawGui
    except ImportError:
        return None
    import os
    import re
    import subprocess
    import tempfile

    base = os.path.splitext(filepath)[0]
    content_svg = base + '.content.svg'
    merged_svg = base + '.svg'
    try:
        TechDrawGui.exportPageAsSvg(page, content_svg)
    except Exception:
        return None

    # Merge template (border/title block) under the drawing content
    try:
        template = page.Template.Template if page.Template else None
        if template and os.path.exists(template):
            with open(content_svg, encoding='utf-8', errors='replace') as f:
                content = f.read()
            with open(template, encoding='utf-8', errors='replace') as f:
                tpl = f.read()

            m = re.search(r'<svg[^>]*>', content)
            head = m.group(0) if m else '<svg>'
            vb = re.search(r'viewBox="([0-9.\s.]+)"', head)
            wh = re.search(r'width="([0-9.]+)mm"', head)
            k = 10.0
            if vb and wh:
                parts = [float(v) for v in vb.group(1).split()]
                if len(parts) == 4 and float(wh.group(1)) > 0:
                    k = parts[2] / float(wh.group(1))

            body = re.search(r'<svg[^>]*>(.*)</svg>', tpl, re.S)
            tpl_body = body.group(1) if body else ''
            tpl_body = re.sub(r'<\?xml[^>]*\?>', '', tpl_body)
            # strip metadata/comments we do not need
            tpl_body = re.sub(r'<metadata.*?</metadata>', '', tpl_body, flags=re.S)

            # substitute editable field values (title block)
            try:
                texts = dict(page.Template.EditableTexts or {})
                for key, value in texts.items():
                    if not key:
                        continue
                    pat = re.compile(
                        r'(<text[^>]*freecad:editable="%s"[^>]*>)[^<]*(</text>)'
                        % re.escape(key))
                    tpl_body = pat.sub(
                        lambda m, v=value: m.group(1) + str(v) + m.group(2),
                        tpl_body)
            except Exception:
                pass

            inject = '<g id="AlumFrameTemplate" transform="scale(%g)">%s</g>' % (
                k, tpl_body)
            idx = content.find('>', content.find('<svg')) + 1
            merged = content[:idx] + '\n' + inject + '\n' + content[idx:]
            with open(merged_svg, 'w', encoding='utf-8') as f:
                f.write(merged)
        else:
            merged_svg = content_svg
    except Exception:
        merged_svg = content_svg

    # Convert SVG -> PDF
    try:
        import cairosvg
        cairosvg.svg2pdf(url=merged_svg, write_to=filepath)
        return filepath
    except Exception:
        pass
    try:
        subprocess.run(['inkscape', merged_svg, '--export-type=pdf',
                        '--export-filename=' + filepath],
                       check=True, capture_output=True)
        return filepath
    except Exception:
        return merged_svg


def remove_drawings(doc):
    """Remove previously generated TechDraw objects (TD_ prefix).

    Views/annotations are detached from their pages and deleted before the
    pages themselves, otherwise FreeCAD can crash on stale references.
    """
    if doc is None:
        return
    td_objs = [o for o in list(doc.Objects) if o.Name.startswith(PAGE_PREFIX)]
    if not td_objs:
        return

    # 1) detach every view from its page
    for o in td_objs:
        try:
            page = getattr(o, 'Owner', None) or getattr(o, 'Page', None)
            if page is not None and hasattr(page, 'removeView'):
                page.removeView(o)
        except Exception:
            pass

    # 2) remove non-page objects first, pages last
    ordered = sorted(td_objs,
                     key=lambda o: 1 if o.TypeId == 'TechDraw::DrawPage' else 0)
    for o in ordered:
        try:
            doc.removeObject(o.Name)
        except Exception:
            pass


def create_drawings_for_frame(doc, frame_group):
    """(Re)generate the TechDraw page for an existing Frame group."""
    import json
    labels = {'X': u'X-横梁', 'Y': u'Y-纵梁', 'Z': u'Z-立柱'}
    names = {'X': 'XBeamBase', 'Y': 'YBeamBase', 'Z': 'ZPostBase'}

    profile = frame_group.FrameProfile
    material = getattr(frame_group, 'FrameMaterial', '')
    connection = getattr(frame_group, 'FrameConnection', 'end_tap')
    layers = int(getattr(frame_group, 'FrameZLayers', 1))
    try:
        notes = json.loads(getattr(frame_group, 'FrameHoleNotes', '') or '{}')
    except Exception:
        notes = {}

    specs = []
    for key, label in labels.items():
        base = doc.getObject(names[key])
        cut = doc.getObject(names[key] + '_Cut')
        if cut is not None:
            try:
                if len(cut.Shape.Faces) > 0:
                    base = cut
            except Exception:
                pass
        if base is None:
            continue
        bb = base.Shape.BoundBox
        if key == 'X':
            length = bb.XMax - bb.XMin
            qty = 2 * (layers + 1)
        elif key == 'Y':
            length = bb.YMax - bb.YMin
            qty = 2 * (layers + 1)
        else:
            length = bb.ZMax - bb.ZMin
            qty = 4
        specs.append({'key': key, 'label': label, 'base': base,
                      'length': length, 'qty': qty})

    note_map = {label: notes.get(key, '') for key, label in labels.items()}
    remove_drawings(doc)
    page = create_techdraw_bom(doc, specs, note_map, profile, material,
                               connection, layers)
    try:
        add_frame_dimensions(doc, frame_group, profile)
    except Exception:
        pass
    return page


def add_frame_dimensions(doc, frame_group, profile):
    """Add TechDraw dimensions to the generated drawing page.

    * every member: length = distance between the two end-face edges;
    * members with drilled holes: distance from the end face to each hole
      centre plus the spacing between consecutive holes.

    Sub-element names are resolved through ``getEdgeByIndex`` /
    ``getVertexByIndex`` (which return geometry in model mm centred on the
    view), so no fragile name guessing is needed.
    """
    import json

    page = doc.getObject(PAGE_PREFIX + 'Page_Specs')
    if page is None:
        return 0
    try:
        holes_axis = json.loads(getattr(frame_group, 'FrameHoleAxis', '') or '{}')
    except Exception:
        holes_axis = {}

    views = {}
    for key in ('X', 'Y', 'Z'):
        v = doc.getObject(PAGE_PREFIX + 'View_' + key)
        if v is not None:
            views[key] = v

    # Freshly created views have no projected geometry until HLR has run:
    # give the GUI a bounded amount of time to catch up. HLR can be only
    # partially done, so wait until the vertex count stops growing.
    try:
        import time as _time
        import FreeCADGui
        last_counts = None
        stable = 0
        for _attempt in range(16):
            counts = []
            for v in views.values():
                try:
                    counts.append(len(v.getVisibleVertexes()))
                except Exception:
                    counts.append(0)
            if counts and all(c > 0 for c in counts):
                if last_counts is not None and counts == last_counts:
                    stable += 1
                    if stable >= 2:
                        break
                else:
                    stable = 0
            last_counts = counts
            for v in views.values():
                try:
                    gv = FreeCADGui.ActiveDocument.getObject(v.Name)
                    if gv is not None:
                        gv.update()
                except Exception:
                    pass
            FreeCADGui.updateGui()
            _time.sleep(0.6)
    except Exception:
        pass

    # keep dimensions inside the drawing frame (clear of the title block)
    page_w, page_h = 594.0, 420.0
    try:
        page_w, page_h = _template_size(page.Template.Template)
        ko = _template_keepout(page.Template.Template, page_w, page_h)
    except Exception:
        ko = None

    pending = []  # (dimension object, expected value)

    for key in ('X', 'Y', 'Z'):
        view = doc.getObject(PAGE_PREFIX + 'View_' + key)
        if view is None:
            continue
        vx = float(view.X)
        vy = float(view.Y)
        try:
            n_verts = len(view.getVisibleVertexes())
        except Exception:
            n_verts = 0
        if not n_verts:
            # HLR may not have run yet (freshly created view): ask the GUI.
            try:
                import FreeCADGui
                gv = FreeCADGui.ActiveDocument.getObject(view.Name)
                if gv is not None:
                    gv.update()
                    FreeCADGui.updateGui()
                n_verts = len(view.getVisibleVertexes())
            except Exception:
                n_verts = 0
        if not n_verts:
            continue
        axis = []
        xs = []
        ys = []
        for i in range(1, n_verts + 1):
            try:
                p = view.getVertexByIndex(i).Point
            except Exception:
                continue
            xs.append(p.x)
            ys.append(p.y)
            if abs(p.y) < 0.1:
                axis.append((round(p.x, 1), i))
        if not xs:
            continue
        half = max(abs(min(xs)), abs(max(xs)))
        # The true member length comes from the source body (vertices may be
        # only partially projected by a still-running HLR job).
        try:
            src = view.Source[0] if view.Source else None
            bb = src.Shape.BoundBox
            true_len = {'X': bb.XLength, 'Y': bb.YLength,
                        'Z': bb.ZLength}[key]
            if true_len > 1.0:
                half = true_len / 2.0
        except Exception:
            pass
        seen = set()
        ax = []
        for x, i in axis:
            if abs(x) >= half - 0.5:
                continue
            if round(x) in seen:
                continue
            seen.add(round(x))
            ax.append((x, i))

        ends = {0: None, 1: None}
        try:
            n_edges = len(view.getVisibleEdges())
        except Exception:
            n_edges = 0
        for i in range(1, n_edges + 1):
            try:
                e = view.getEdgeByIndex(i)
                if e.Curve.TypeId != 'Part::GeomLine' or e.Length < 2.0:
                    continue
                bb = e.BoundBox
                if bb.XLength > 1e-6:
                    continue
                x = bb.XMin
                if abs(abs(x) - half) < 0.75:
                    side = 0 if x < 0 else 1
                    if ends[side] is None or e.Length > ends[side][1]:
                        ends[side] = (i, e.Length)
            except Exception:
                continue

        scale = float(getattr(view, 'Scale', 1.0) or 1.0)
        y_ext = (max(ys) - min(ys)) / 2.0 * scale
        beam_top = vy + y_ext
        # Empirical TechDraw export offsets (verified by parsing the exported
        # SVG): the label is drawn at X + (half*scale + 17) and 11 mm above the
        # dimension line, while the line height is view.Y + Y - 10*scale.
        # X/Y are compensated so labels land where intended.
        cx = half * scale + 17.0
        cy = 11.0

        def place(name, typ, refs, lx, ly, expect):
            """Create a dimension whose *label* sits at page (lx, ly)."""
            try:
                lo = MARGIN + 6.0
                if ko and ko[0] - 2.0 <= vx <= ko[2] + 2.0:
                    lo = ko[3] + 6.0
                hi = page_h - MARGIN - 6.0
                ly = max(lo, min(float(ly), hi))
                lx = max(MARGIN + 6.0,
                         min(float(lx), page_w - MARGIN - 6.0))
                d = doc.addObject('TechDraw::DrawViewDimension', PAGE_PREFIX + name)
                d.Type = typ
                d.References2D = [(view, tuple(refs))]
                page.addView(d)
                d.X = float(lx) - cx
                d.Y = (ly - cy) - vy + 10.0 * scale
                pending.append((d, float(expect)))
            except Exception:
                pass

        row = [0]

        def next_row():
            r = row[0]
            row[0] += 1
            return beam_top + 12.0 + 6.0 * r

        if ends[0] and ends[1]:
            place('Dim_%s_L' % key, 'Distance',
                  ('Edge%d' % ends[0][0], 'Edge%d' % ends[1][0]),
                  vx, next_row(), 2.0 * half)

        if ends[0] and ends[1]:
            left = 'Edge%d' % ends[0][0]
            right = 'Edge%d' % ends[1][0]
            picked = []
            for h in holes_axis.get(key, []):
                try:
                    h = float(h)
                except Exception:
                    continue
                if h <= 0:
                    continue
                best = None
                for x, i in ax:
                    if i in [p[1] for p in picked]:
                        continue
                    dd = abs(x - (h - half))
                    if best is None or dd < best[0]:
                        best = (dd, x, i, h)
                if best is not None and best[0] < 1.0:
                    picked.append((best[1], best[2], best[3]))
            picked.sort(key=lambda t: t[2])
            if picked:
                # One chain row: end face -> nearest hole, consecutive hole
                # spacings, nearest hole -> end face. Everything else can be
                # derived from these.
                row_y = next_row()
                x1, i1, h1 = picked[0]
                place('Dim_%s_E1' % key, 'Distance', (left, 'Vertex%d' % i1),
                      vx + scale * (x1 - half) / 2.0, row_y, h1)
                for k in range(len(picked) - 1):
                    p1, p2 = picked[k], picked[k + 1]
                    place('Dim_%s_S%d' % (key, k + 1), 'DistanceX',
                          ('Vertex%d' % p1[1], 'Vertex%d' % p2[1]),
                          vx + scale * (p1[0] + p2[0]) / 2.0, row_y,
                          p2[2] - p1[2])
                x2, i2, h2 = picked[-1]
                place('Dim_%s_E2' % key, 'Distance', (right, 'Vertex%d' % i2),
                      vx + scale * (x2 + half) / 2.0, row_y, 2.0 * half - h2)

    if not pending:
        return 0
    try:
        doc.recompute()
    except Exception:
        pass
    kept = 0
    for d, expect in pending:
        try:
            val = float(d.getRawValue())
        except Exception:
            val = None
        if val is not None and abs(val - expect) < 0.5:
            kept += 1
        else:
            try:
                doc.removeObject(d.Name)
            except Exception:
                pass
    return kept
