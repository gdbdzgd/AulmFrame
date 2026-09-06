# -*- coding: utf-8 -*-
"""AlumFrame workbench GUI initialization.

This workbench provides a complete task panel interface for generating
aluminum extrusion frames with real-time preview.
"""

import FreeCAD
import FreeCADGui


class AlumFrameWorkbench(FreeCADGui.Workbench):
    """Aluminum frame generator workbench."""

    def __init__(self):
        self.__class__.Icon = ''
        self.__class__.MenuText = u'铝型材框架'
        self.__class__.ToolTip = u'快速生成铝型材框架并输出BOM'

    def Initialize(self):
        """Initialize the workbench - called when user switches to this workbench."""
        # Import and show task panel immediately when workbench is activated
        try:
            from AlumFrame.Gui import AlumFrameTaskPanel
            panel = AlumFrameTaskPanel()
            FreeCADGui.Control.showDialog(panel)
        except Exception as e:
            FreeCAD.Console.PrintError(u'AlumFrame workbench init error: %s\n' % str(e))
            import traceback
            traceback.print_exc()

    def GetClassName(self):
        return 'Gui::PythonWorkbench'


class AlumFrameGenerateCommand:
    """Command to open/reopen the frame generator task panel."""

    def GetResources(self):
        return {
            'Pixmap': '',
            'MenuText': u'打开框架生成器',
            'ToolTip': u'打开铝型材框架生成器任务面板',
        }

    def Activated(self):
        try:
            from AlumFrame.Gui import AlumFrameTaskPanel
            panel = AlumFrameTaskPanel()
            FreeCADGui.Control.showDialog(panel)
        except Exception as e:
            FreeCAD.Console.PrintError(u'AlumFrame Activated error: %s\n' % str(e))
            import traceback
            traceback.print_exc()

    def IsActive(self):
        return True


FreeCADGui.addCommand('AlumFrame_OpenPanel', AlumFrameGenerateCommand())
FreeCADGui.addWorkbench(AlumFrameWorkbench())
FreeCAD.Console.PrintMessage(u'AlumFrame workbench loaded\n')
