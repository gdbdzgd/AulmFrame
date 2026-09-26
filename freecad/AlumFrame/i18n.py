# -*- coding: utf-8 -*-
"""Minimal runtime i18n for the AlumFrame workbench.

Source strings are Chinese (the primary audience); an English table is
applied automatically whenever FreeCAD's UI language is not Chinese.

Usage:
    from .i18n import tr
    label = tr(u'新建框架')
"""

_CURRENT = None

# Chinese source -> English translation (UI strings only)
_EN = {
    # ---- workbench / commands ----
    u'铝型材框架': 'Aluminum Frame',
    u'快速生成铝型材框架、BOM 与加工图纸':
        'Quickly generate aluminum profile frames, BOM and shop drawings',
    u'新建框架': 'New Frame',
    u'打开生成器，创建新的铝型材框架':
        'Open the generator to create a new aluminum frame',
    u'编辑框架': 'Edit Frame',
    u'读取选中框架的参数并修改':
        'Load the parameters of the selected frame and modify them',
    u'导出 BOM (CSV)': 'Export BOM (CSV)',
    u'把当前框架的 BOM 表导出为 CSV（含打孔说明与五金）':
        'Export the current frame BOM to CSV (machining notes and hardware)',
    u'导出 BOM': 'Export BOM',
    u'AlumFrame: 未找到框架（请先在文档中生成框架）\n':
        'AlumFrame: no frame found (generate a frame in a document first)\n',
    u'AlumFrame: 未找到 BOM 表\n': 'AlumFrame: no BOM spreadsheet found\n',
    u'AlumFrame: BOM 已导出至 %s\n': 'AlumFrame: BOM exported to %s\n',
    u'AlumFrame: 导出失败: %s\n': 'AlumFrame: export failed: %s\n',
    u'生成 TechDraw 图纸': 'Create TechDraw Drawing',
    u'为当前框架重新生成加工图纸（每规格一行，含数量与打孔方式）':
        'Regenerate the shop drawing for the current frame '
        '(one row per profile, with quantity and machining)',
    u'AlumFrame: 图纸已生成\n': 'AlumFrame: drawing created\n',
    u'AlumFrame: 图纸生成失败: %s\n':
        'AlumFrame: drawing creation failed: %s\n',
    u'导出图纸 PDF': 'Export Drawing PDF',
    u'把当前框架的 A2 加工图纸导出为 PDF（含边框）':
        'Export the A2 shop drawing of the current frame to PDF (with border)',
    u'AlumFrame: 未找到框架\n': 'AlumFrame: no frame found\n',
    u'AlumFrame: 未找到图纸\n': 'AlumFrame: no drawing found\n',
    u'导出图纸': 'Export Drawing',
    u'AlumFrame: 图纸已导出 %s\n': 'AlumFrame: drawing exported to %s\n',
    u'AlumFrame: 图纸导出失败: %s\n':
        'AlumFrame: drawing export failed: %s\n',

    # ---- task panel ----
    u'铝型材框架生成器': 'Aluminum Frame Generator',
    u'<h3>铝型材框架生成器</h3>': '<h3>Aluminum Frame Generator</h3>',
    u'参数设置': 'Parameters',
    u'型材规格:': 'Profile:',
    u'长度 (X):': 'Length (X):',
    u'宽度 (Y):': 'Width (Y):',
    u'高度 (Z):': 'Height (Z):',
    u'Z层数:': 'Z layers:',
    u'第一尺寸(a)沿X': 'First size (a) along X',
    u'第二尺寸(b)沿X': 'Second size (b) along X',
    u'矩形立柱截面方向：哪个尺寸沿框架X轴':
        'Rectangular post orientation: which size runs along the frame X axis',
    u'立柱方向:': 'Post direction:',
    u'第二尺寸(b)竖直': 'Second size (b) vertical',
    u'第一尺寸(a)竖直': 'First size (a) vertical',
    u'矩形横梁截面方向：哪个尺寸竖直（X/Y梁共用）':
        'Rectangular beam orientation: which size is vertical '
        '(shared by X/Y beams)',
    u'横梁竖直:': 'Beam vertical:',
    u'连接方式：决定端面攻丝/侧孔/贯穿孔等加工':
        'Connection method: determines end tapping / side holes / '
        'through holes',
    u'连接方式:': 'Connection:',
    u'材料:': 'Material:',
    u'自动(推荐)': 'Auto (recommended)',
    u'连接孔直径；0=按型材推荐值。上限=型材宽度的一半':
        'Connection hole diameter; 0 = profile default. '
        'Limit = half of the profile width',
    u'开孔孔径:': 'Hole diameter:',
    u'开孔深度:': 'Hole depth:',
    u'孔位距端面距离；0=按推荐值':
        'Hole offset from the member end; 0 = recommended value',
    u'孔位距端:': 'Hole offset:',
    u'生成 TechDraw 图纸（每规格一页）':
        'Create TechDraw drawing (one page per profile)',
    u'出图:': 'Drawing:',
    u'生成 / 更新框架': 'Generate / Update Frame',
    u'按当前参数生成；编辑模式下就地重建当前文档的框架':
        'Generate with the current parameters; in edit mode rebuild the '
        'frame in place',
    u'读取选中参数': 'Load Selected',
    u'从选中的框架（或其子对象）读取参数':
        'Load parameters from the selected frame (or any child object)',
    u'新建 (重置)': 'New (Reset)',
    u'切换到新建模式：下次生成将创建新文档':
        'Switch to new mode: the next build creates a new document',
    u'导出BOM (CSV)': 'Export BOM (CSV)',
    u'导出物料清单到CSV文件':
        'Export the bill of materials to a CSV file',
    u'生成结果': 'Result',
    u'点击"生成 / 更新框架"开始': 'Click "Generate / Update Frame" to start',
    u'<small><i>提示：选中框架后点"读取选中参数"可编辑已有框架</i></small>':
        '<small><i>Tip: select a frame and click "Load Selected" to edit '
        'an existing frame</i></small>',
    u'<font color="#2a7"><b>编辑模式:</b> 更新文档「%s」中的框架</font>':
        '<font color="#2a7"><b>Edit mode:</b> update the frame in '
        'document "%s"</font>',
    u'<font color="#777"><b>新建模式:</b> 将生成新文档</font>':
        '<font color="#777"><b>New mode:</b> a new document will be '
        'created</font>',
    u'<font color="green">✓ 已读取选中框架参数</font>':
        '<font color="green">✓ Parameters loaded from the selected '
        'frame</font>',
    u'<font color="orange">未选中框架（请选中框架组或其任意子对象）</font>':
        '<font color="orange">No frame selected (select the frame group '
        'or any child object)</font>',
    u'已重置为新建模式，点击"生成 / 更新框架"创建新文档':
        'Reset to new mode; click "Generate / Update Frame" to create '
        'a new document',
    u'<b>✓ 框架已生成</b>': '<b>✓ Frame generated</b>',
    u'<b>BOM 汇总:</b>': '<b>BOM summary:</b>',
    u'  %s: 数量=%d, 总长=%.1fmm': '  %s: qty=%d, total length=%.1fmm',
    u'共 <b>%d</b> 项型材, Z层数: <b>%d</b>':
        '<b>%d</b> member entries, Z layers: <b>%d</b>',
    u'<font color="red">错误: %s</font>': '<font color="red">Error: %s</font>',
    u'<font color="orange">请先生成框架</font>':
        '<font color="orange">Generate a frame first</font>',
    u'保存BOM': 'Save BOM',
    u'<font color="green">✓ BOM已导出至: %s</font>':
        '<font color="green">✓ BOM exported to: %s</font>',
    u'<font color="red">导出错误: %s</font>':
        '<font color="red">Export error: %s</font>',

    # ---- member labels (used in summaries / drawings) ----
    u'X-横梁': 'X beam',
    u'Y-纵梁': 'Y beam',
    u'Z-立柱': 'Z post',

    # ---- connection methods (labels / descriptions / hardware) ----
    u'角码 + T型螺母（型材不打孔）':
        'Corner bracket + T-nut (no machining)',
    u'螺栓滑入槽内，配合 T 型螺母与角码，型材无需加工':
        'Bolts slide into the slot; bracket and T-nut fix the joint '
        'without machining',
    u'角码': 'Corner bracket',
    u'内六角螺栓': 'Socket head bolt',
    u'T型螺母': 'T-nut',
    u'端面攻丝 + 侧向贯穿（常用）': 'End tap + side through (common)',
    u'横梁端面中心孔攻丝，立柱侧壁钻贯穿孔，螺栓穿柱锁入梁端':
        'Tap the beam end centre hole, drill a through hole in the post '
        'wall, bolt through the post into the beam end',
    u'弹性垫圈': 'Spring washer',
    u'隐藏式连接件（侧面钻孔 + 端面攻丝）':
        'Hidden connector (side access + end tap)',
    u'连接件插入梁端并攻丝固定，梁侧面钻工艺孔拧紧':
        'The connector is inserted and tapped into the beam end; a side '
        'access hole is drilled to tighten it',
    u'隐藏式连接件': 'Hidden connector',
    u'紧定螺钉': 'Set screw',
    u'打孔攻丝（贯穿孔 + 螺母）': 'Through tap (through hole + nut)',
    u'横梁端部钻贯穿孔，螺栓穿柱与梁，槽内配螺母锁紧':
        'Drill a through hole in the beam end; the bolt passes through '
        'post and beam, locked with a nut in the slot',
    u'锚式连接件（槽内锚 + 侧向孔）':
        'Anchor connector (slot anchor + side hole)',
    u'梁槽内装入锚件，立柱侧壁钻孔后螺栓锁紧':
        'An anchor is inserted in the beam slot; a post wall hole and '
        'bolt lock it',
    u'锚式连接件': 'Anchor connector',
    u'直连接 / 连接棒（同轴对接）':
        'Straight joint / connector rod (coaxial butt)',
    u'同轴对接处两端攻丝，用连接棒连接（分段梁/柱时使用）':
        'Tap both ends of the coaxial butt joint and join with a '
        'connector rod (for segmented beams/posts)',
    u'连接棒': 'Connector rod',
    u'脚座/顶板（柱端攻丝）': 'Base / top plate (post end tap)',
    u'立柱上下端面中心孔攻丝，用于固定脚座与顶板':
        'Tap the centre holes of the post top/bottom ends for base and '
        'top plates',
    u'脚座/顶板': 'Base/top plate',

    # ---- BOM (spreadsheet cells, CSV) ----
    u'BOM 规格表': 'BOM specification',
    u'序号': '#',
    u'部件': 'Part',
    u'型材规格': 'Profile',
    u'长度(mm)': 'Length (mm)',
    u'数量': 'Qty',
    u'材料': 'Material',
    u'总长(mm)': 'Total (mm)',
    u'打孔说明': 'Machining note',
    u'合计': 'Total',
    u'外形尺寸': 'Outer size',
    u'Z层数: %d': 'Z layers: %d',
    u'连接方式': 'Connection',
    u'连接五金': 'Joint hardware',
    u'名称': 'Name',
    u'每根2处攻丝（沿梁轴），截面中心\n  端1: %s距端面%.0fmm 深%.0fmm  %s\n  端2: %s距端面%.0fmm 深%.0fmm  %s':
        '2 taps per member (along the axis), section center\n'
        '  end1: %s, %.0f mm from the end face, %.0f mm deep  %s\n'
        '  end2: %s, %.0f mm from the end face, %.0f mm deep  %s',
    u'底部': 'bottom',
    u'顶部': 'top',
    u'第%d层': 'layer %d',
    u'  %s: %s十字通孔 + %s攻丝 距底面%.0fmm/深%.0fmm  %s':
        '  %s: %s cross hole + %s tap, %.0f mm from the base, '
        '%.0f mm deep  %s',
    u'  %s: %s十字通孔  %s': '  %s: %s cross hole  %s',
    u'Z柱 %d层：每层%s十字通孔，顶底%s攻丝\n%s':
        'Z post, %d layers: %s cross hole per layer, top/bottom %s taps\n%s',

    # ---- machining notes (frame builder) ----
    u'端面攻丝【两端，每端1处，共2处/根】：%s 底孔Ø%g 深%.0f，'
    u'沿梁轴攻入截面中心（中心孔）':
        'End tap [both ends, 1 per end, 2 per member]: %s pilot '
        'Ø%g depth %.0f, tapped along the beam axis into the section '
        'center (center bore)',
    u'打孔【两端，每端1处】：距梁端%.0f，垂直于梁轴、水平方向，'
    u'Ø%g 贯通截面，配槽内螺母锁紧':
        'Drill [both ends, 1 per end]: %.0f from the beam end, '
        'perpendicular to the beam axis (horizontal), Ø%g through the '
        'section, locked with a nut in the slot',
    u'工艺孔【两端，每端1处】：距梁端%.0f，从顶面垂直向下、'
    u'Ø%.1f 深%.0f（只穿透顶面一层，通入槽内用于拧紧）':
        'Access hole [both ends, 1 per end]: %.0f from the beam end, '
        'downward from the top face, Ø%.1f depth %.0f (through the top '
        'wall only, into the slot for tightening)',
    u'锚孔【两端，每端1处】：距梁端%.0f，从顶面垂直向下、'
    u'Ø%g 深%.0f（只穿透顶面一层，槽内装锚件）':
        'Anchor hole [both ends, 1 per end]: %.0f from the beam end, '
        'downward from the top face, Ø%g depth %.0f (through the top '
        'wall only; the anchor sits in the slot)',
    u'打孔【每柱每层 2 处，X向+Y向各1】：沿梁轴方向水平贯穿，'
    u'Ø%g 间隙孔（螺栓通过）；层高 %s，共 %d 层':
        'Drill [2 per post per layer, 1 in X + 1 in Y]: horizontal '
        'through along the beam axis, Ø%g clearance hole (bolt '
        'passage); layer heights %s, %d layers',
    u'端面攻丝【两端，每端1处】：柱底沿 +Z 向上攻入、'
    u'柱顶沿 -Z 向下攻入，%s 底孔Ø%g 深%.0f':
        'End tap [both ends, 1 per end]: tapped upward along +Z from '
        'the post bottom and downward along -Z from the top, %s pilot '
        'Ø%g depth %.0f',
    u'、': ', ',

    # ---- drawing annotations / title block ----
    u'图纸': 'Drawing',
    u'型材加工图纸': 'Member machining drawing',
    u'铝型材加工图纸': 'ALUMINUM FRAME SHOP DRAWING',
    u'规格:': 'Profile:',
    u'比例:': 'Scale:',
    u'图号:': 'Sheet:',
    u'材料:': 'Material:',
    u'连接:': 'Connection:',
    u'部件: %s': 'Part: %s',
    u'规格: %s   长度: %.0f mm   数量: %d':
        'Profile: %s   Length: %.0f mm   Qty: %d',
    u'主视图比例 1:%.1f（各型材一致，便于比长短）':
        'Main view scale 1:%.1f (identical for all members for length '
        'comparison)',
    u'端面视图为细节，比例 1:%.1f': 'End view is a detail, scale 1:%.1f',
    u'打孔方式:': 'Machining:',
    u'无型材加工': 'No machining',

    # ---- profile display names (keys are kept in Chinese internally) ----
    u'20x20 方管': '20x20 Square',
    u'30x30 方管': '30x30 Square',
    u'40x40 方管': '40x40 Square',
    u'60x60 方管': '60x60 Square',
}


def map_language(name):
    """Map a FreeCAD locale name/code (e.g. 'Chinese (Simplified)', 'zh-CN')
    to 'zh' or 'en'.  Returns None when the name is empty/unknown."""
    if not name:
        return None
    low = str(name).lower()
    if low.startswith('chinese') or low.startswith('zh'):
        return 'zh'
    return 'en'


def _detect_language():
    """Follow FreeCAD's effective language setting.

    Order:
      1. ``FreeCADGui.getLocale()`` - the resolved UI language. This honours
         the Language preference *and* its fallback to the system locale;
      2. the ``Language`` preference (headless / early startup);
      3. the Qt system locale (no FreeCAD available, e.g. unit tests);
      4. Chinese (source language) as the last resort.
    """
    # 1. resolved GUI locale
    try:
        import FreeCADGui
        name = FreeCADGui.getLocale() or ''
        if name:
            try:
                code = FreeCADGui.supportedLocales().get(name)
            except Exception:
                code = None
            return map_language(code or name)
    except Exception:
        pass
    # 2. preference (works headless as well)
    name = ''
    try:
        import FreeCAD
        name = FreeCAD.ParamGet(
            'User parameter:BaseApp/Preferences/General'
        ).GetString('Language')
    except Exception:
        name = ''
    if name:
        return map_language(name)
    # 3. system locale
    for mod in ('PySide6', 'PySide2', 'PySide'):
        try:
            QtCore = __import__(mod + '.QtCore', fromlist=['QtCore'])
            loc = map_language(QtCore.QLocale.system().name())
            if loc:
                return loc
        except Exception:
            continue
    # 4. source language
    return 'zh'


def current_language():
    """Return 'zh' or 'en' following FreeCAD's UI language setting."""
    global _CURRENT
    if _CURRENT is None:
        _CURRENT = _detect_language()
    return _CURRENT


def set_language(lang):
    """Force a language ('zh'/'en') or reset auto-detection (None)."""
    global _CURRENT
    _CURRENT = None if lang is None else str(lang)


def tr(text):
    """Translate a Chinese UI string to the current UI language."""
    if current_language() == 'en':
        return _EN.get(text, text)
    return text
