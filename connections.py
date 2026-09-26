# -*- coding: utf-8 -*-
"""
Connection methods for aluminum T-slot frames.

Each method declares the machining it needs on the members and the hardware
it consumes. Hole positions themselves are computed by the frame builder in
each base object's local frame (the base is shared by symmetric array copies,
so both ends / every post get the same pattern).

Methods:
  bracket     角码 + T 型螺母   -> no profile machining
  end_tap     端面攻丝          -> beam end taps + post side through holes
  hidden      隐藏式连接件      -> beam end tap + side access hole + post through
  through_tap 打孔攻丝          -> beam end through hole + post through
  anchor      锚式连接件        -> beam slot anchor hole + post through
  straight    直连接/连接棒     -> collinear butt joint (segmented members)
  base_plate  脚座/顶板         -> post bottom/top end taps
"""

METHODS = {
    'bracket': {
        'label': u'角码 + T型螺母（型材不打孔）',
        'desc': u'螺栓滑入槽内，配合 T 型螺母与角码，型材无需加工',
        'hardware': [(u'角码', 1), (u'内六角螺栓', 2), (u'T型螺母', 2)],
        'params': {},
        'joint_based': True,
        'machining': 'none',
    },
    'end_tap': {
        'label': u'端面攻丝 + 侧向贯穿（常用）',
        'desc': u'横梁端面中心孔攻丝，立柱侧壁钻贯穿孔，螺栓穿柱锁入梁端',
        'hardware': [(u'内六角螺栓', 1), (u'弹性垫圈', 1)],
        'params': {},
        'joint_based': True,
        'machining': 'end_tap+post_through',
    },
    'hidden': {
        'label': u'隐藏式连接件（侧面钻孔 + 端面攻丝）',
        'desc': u'连接件插入梁端并攻丝固定，梁侧面钻工艺孔拧紧',
        'hardware': [(u'隐藏式连接件', 1), (u'紧定螺钉', 1)],
        'params': {'side_offset': 18.0, 'access_d': 6.8},
        'joint_based': True,
        'machining': 'end_tap+side_access+post_through',
    },
    'through_tap': {
        'label': u'打孔攻丝（贯穿孔 + 螺母）',
        'desc': u'横梁端部钻贯穿孔，螺栓穿柱与梁，槽内配螺母锁紧',
        'hardware': [(u'内六角螺栓', 1), (u'T型螺母', 1)],
        'params': {},
        'joint_based': True,
        'machining': 'end_through+post_through',
    },
    'anchor': {
        'label': u'锚式连接件（槽内锚 + 侧向孔）',
        'desc': u'梁槽内装入锚件，立柱侧壁钻孔后螺栓锁紧',
        'hardware': [(u'锚式连接件', 1), (u'内六角螺栓', 1)],
        'params': {'anchor_offset': 15.0},
        'joint_based': True,
        'machining': 'anchor_hole+post_through',
    },
    'straight': {
        'label': u'直连接 / 连接棒（同轴对接）',
        'desc': u'同轴对接处两端攻丝，用连接棒连接（分段梁/柱时使用）',
        'hardware': [(u'连接棒', 1)],
        'params': {},
        'joint_based': False,
        'machining': 'end_tap',
    },
    'base_plate': {
        'label': u'脚座/顶板（柱端攻丝）',
        'desc': u'立柱上下端面中心孔攻丝，用于固定脚座与顶板',
        'hardware': [(u'脚座/顶板', 1), (u'内六角螺栓', 1)],
        'params': {},
        'joint_based': False,
        'machining': 'post_end_tap',
    },
}

METHOD_ORDER = ['bracket', 'end_tap', 'hidden', 'through_tap', 'anchor',
                'straight', 'base_plate']


def method_label(method):
    return METHODS.get(method, {}).get('label', method)


def joint_hardware(method):
    """Return hardware [(name, qty)] consumed by ONE joint (or member end)."""
    return list(METHODS.get(method, {}).get('hardware', []))


def method_params(method):
    return dict(METHODS.get(method, {}).get('params', {}))
