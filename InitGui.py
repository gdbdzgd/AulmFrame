# -*- coding: utf-8 -*-
"""AlumFrame workbench GUI initialization.

All commands live in the workbench toolbar — no menu bar entries.
"""

import FreeCAD
from FreeCAD import Gui
from FreeCADGui import Workbench
import os

def _get_icon(name):
    """Find icon file robustly — handles missing __file__ in FreeCAD."""
    try:
        return os.path.join(os.path.dirname(__file__), 'icons', name)
    except NameError:
        pass
    # Fallback: search Mod directories
    for mod_dir in [FreeCAD.getUserModDir(),
                    os.path.expanduser('~/.local/share/FreeCAD/v1-1/Mod'),
                    os.path.expanduser('~/.FreeCAD/Mod')]:
        p = os.path.join(mod_dir, 'AlumFrame', 'icons', name)
        if os.path.exists(p):
            return p
    return name

_ICON_FRAME = _get_icon('frame_xpm.xpm')
_ICON_EDIT = _get_icon('edit_xpm.xpm')


def _open_panel(edit_selected=False):
    from AlumFrame.Gui import open_task_panel
    open_task_panel(edit_selected=edit_selected)


class NewFrameCommand:
    """Open the generator panel in new-frame mode."""

    def GetResources(self):
        return {
            'Pixmap': _ICON_FRAME,
            'MenuText': u'新建框架',
            'ToolTip': u'打开生成器，创建新的铝型材框架',
        }

    def Activated(self):
        _open_panel(edit_selected=False)

    def IsActive(self):
        return True


class EditFrameCommand:
    """Open the generator panel loading the selected/current frame."""

    def GetResources(self):
        return {
            'Pixmap': _ICON_EDIT,
            'MenuText': u'编辑框架',
            'ToolTip': u'读取选中（或当前文档）框架的参数并修改，就地重建',
        }

    def Activated(self):
        _open_panel(edit_selected=True)

    def IsActive(self):
        return True


class AlumFrameWorkbench(Workbench):
    """Aluminum frame generator workbench — commands live in the toolbar."""

    def __init__(self):
        self.__class__.Icon = _ICON_FRAME
        self.__class__.MenuText = u'铝型材框架'
        self.__class__.ToolTip = u'快速生成/编辑铝型材框架并输出BOM'

    def Initialize(self):
        # Toolbar only — no menu bar entries
        self.appendToolbar(u'铝型材框架', ['AlumFrame_NewFrame', 'AlumFrame_EditFrame'])

    def Activated(self):
        # Open the panel automatically for quick access
        try:
            _open_panel(edit_selected=True)
        except Exception as e:
            FreeCAD.Console.PrintError(u'AlumFrame workbench: %s\n' % str(e))

    def Deactivated(self):
        pass

    def GetClassName(self):
        return 'Gui::PythonWorkbench'


Gui.addCommand('AlumFrame_NewFrame', NewFrameCommand())
Gui.addCommand('AlumFrame_EditFrame', EditFrameCommand())
Gui.addWorkbench(AlumFrameWorkbench())
FreeCAD.Console.PrintMessage(u'AlumFrame workbench loaded\n')
