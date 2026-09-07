# -*- coding: utf-8 -*-
"""AlumFrame workbench GUI initialization."""

import FreeCAD
import FreeCADGui
from FreeCADGui import Workbench
import os
import sys

def _add_alumframe_to_path():
    try:
        d = os.path.dirname(__file__)
        if d not in sys.path:
            sys.path.insert(0, d)
    except NameError:
        for p in [os.path.expanduser('~/.local/share/FreeCAD/v1-1/Mod'),
                  os.path.expanduser('~/.FreeCAD/Mod')]:
            if p not in sys.path:
                sys.path.insert(0, p)

_add_alumframe_to_path()


class NewFrameCommand:
    def GetResources(self):
        return {'MenuText': u'新建框架',
                'ToolTip': u'打开生成器，创建新的铝型材框架'}

    def Activated(self):
        try:
            from AlumFrame.Gui import open_task_panel
            open_task_panel(edit_selected=False)
        except Exception as e:
            FreeCAD.Console.PrintError(u'AlumFrame workbench: %s\n' % str(e))

    def IsActive(self):
        return True


class EditFrameCommand:
    def GetResources(self):
        return {'MenuText': u'编辑框架',
                'ToolTip': u'读取选中框架的参数并修改'}

    def Activated(self):
        try:
            from AlumFrame.Gui import open_task_panel
            open_task_panel(edit_selected=True)
        except Exception as e:
            FreeCAD.Console.PrintError(u'AlumFrame workbench: %s\n' % str(e))

    def IsActive(self):
        return True


class AlumFrameWorkbench(Workbench):
    def __init__(self):
        self.__class__.Icon = ":/icons/freecad.svg"
        self.__class__.MenuText = u'铝型材框架'
        self.__class__.ToolTip = u'快速生成铝型材框架并输出BOM'

    def Initialize(self):
        self.appendToolbar(u'铝型材框架', ['AlumFrame_NewFrame', 'AlumFrame_EditFrame'])

    def Activated(self):
        try:
            from AlumFrame.Gui import open_task_panel
            open_task_panel(edit_selected=True)
        except Exception as e:
            FreeCAD.Console.PrintError(u'AlumFrame workbench: %s\n' % str(e))

    def Deactivated(self):
        pass

    def GetClassName(self):
        return 'Gui::PythonWorkbench'


FreeCADGui.addCommand('AlumFrame_NewFrame', NewFrameCommand())
FreeCADGui.addCommand('AlumFrame_EditFrame', EditFrameCommand())
FreeCADGui.addWorkbench(AlumFrameWorkbench())
FreeCAD.Console.PrintMessage(u'AlumFrame workbench loaded successfully\n')