# -*- coding: utf-8 -*-
"""AlumFrame workbench GUI initialization."""

import FreeCAD
import FreeCADGui


class AlumFrameWorkbench(FreeCADGui.Workbench):
    """Aluminum frame generator workbench."""

    def __init__(self):
        self.__class__.Icon = ''
        self.__class__.MenuText = u'铝型材框架'
        self.__class__.ToolTip = u'快速生成铝型材框架并输出BOM'

    def Initialize(self):
        self.appendToolbar(u'铝型材框架', ['AlumFrame_Generate'])
        self.appendMenu(u'铝型材框架', ['AlumFrame_Generate'])

    def GetClassName(self):
        return 'Gui::PythonWorkbench'


class AlumFrameGenerateCommand:
    """Command to open the frame generator dialog."""

    def GetResources(self):
        return {
            'Pixmap': '',
            'MenuText': u'生成铝型材框架',
            'ToolTip': u'打开铝型材框架生成器对话框',
        }

    def Activated(self):
        try:
            from AlumFrame.Gui import AlumFrameDialog
            dlg = AlumFrameDialog()
            dlg.exec()
        except Exception as e:
            FreeCAD.Console.PrintError(u'AlumFrame Activated error: %s\n' % str(e))
            import traceback
            traceback.print_exc()

    def IsActive(self):
        return True


FreeCADGui.addCommand('AlumFrame_Generate', AlumFrameGenerateCommand())
FreeCADGui.addWorkbench(AlumFrameWorkbench())
FreeCAD.Console.PrintMessage(u'AlumFrame workbench loaded\n')