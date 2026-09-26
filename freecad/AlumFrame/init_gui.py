# -*- coding: utf-8 -*-
"""AlumFrame workbench GUI initialization (GUI mode only).

Loaded by FreeCAD as ``freecad.AlumFrame.init_gui``; no sys.path changes.
"""

import os

import FreeCAD
import FreeCADGui
from FreeCADGui import Workbench

from .i18n import tr


class NewFrameCommand:
    def GetResources(self):
        return {'MenuText': tr(u'新建框架'),
                'ToolTip': tr(u'打开生成器，创建新的铝型材框架')}

    def Activated(self):
        try:
            from .gui import open_task_panel
            open_task_panel(edit_selected=False)
        except Exception as e:
            FreeCAD.Console.PrintError(u'AlumFrame workbench: %s\n' % str(e))

    def IsActive(self):
        return True


class EditFrameCommand:
    def GetResources(self):
        return {'MenuText': tr(u'编辑框架'),
                'ToolTip': tr(u'读取选中框架的参数并修改')}

    def Activated(self):
        try:
            from .gui import open_task_panel
            open_task_panel(edit_selected=True)
        except Exception as e:
            FreeCAD.Console.PrintError(u'AlumFrame workbench: %s\n' % str(e))

    def IsActive(self):
        return True


class ExportBomCommand:
    def GetResources(self):
        return {'MenuText': tr(u'导出 BOM (CSV)'),
                'ToolTip': tr(u'把当前框架的 BOM 表导出为 CSV（含打孔说明与五金）')}

    def Activated(self):
        try:
            from .gui import active_frame
            frame = active_frame()
            if frame is None:
                FreeCAD.Console.PrintWarning(
                    tr(u'AlumFrame: 未找到框架（请先在文档中生成框架）\n'))
                return
            doc = frame.Document
            bom = doc.getObject('BOM')
            if bom is None:
                FreeCAD.Console.PrintWarning(tr(u'AlumFrame: 未找到 BOM 表\n'))
                return
            from .gui import QtWidgets
            filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
                None, tr(u'导出 BOM'), 'bom.csv', 'CSV Files (*.csv)')
            if not filepath:
                return
            from .bom import export_bom_sheet_csv
            export_bom_sheet_csv(bom, filepath)
            FreeCAD.Console.PrintMessage(
                tr(u'AlumFrame: BOM 已导出至 %s\n') % filepath)
        except Exception as e:
            FreeCAD.Console.PrintError(tr(u'AlumFrame: 导出失败: %s\n') % str(e))

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None


class DrawingsCommand:
    def GetResources(self):
        return {'MenuText': tr(u'生成 TechDraw 图纸'),
                'ToolTip': tr(u'为当前框架重新生成加工图纸（每规格一行，含数量与打孔方式）')}

    def Activated(self):
        try:
            from .gui import active_frame
            frame = active_frame()
            if frame is None:
                FreeCAD.Console.PrintWarning(
                    tr(u'AlumFrame: 未找到框架（请先在文档中生成框架）\n'))
                return
            from .techdraw_bom import create_drawings_for_frame
            create_drawings_for_frame(frame.Document, frame)
            FreeCAD.Console.PrintMessage(tr(u'AlumFrame: 图纸已生成\n'))
        except Exception as e:
            FreeCAD.Console.PrintError(tr(u'AlumFrame: 图纸生成失败: %s\n') % str(e))

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None


class ExportDrawingsCommand:
    def GetResources(self):
        return {'MenuText': tr(u'导出图纸 PDF'),
                'ToolTip': tr(u'把当前框架的 A2 加工图纸导出为 PDF（含边框）')}

    def Activated(self):
        try:
            from .gui import active_frame, QtWidgets
            frame = active_frame()
            if frame is None:
                FreeCAD.Console.PrintWarning(tr(u'AlumFrame: 未找到框架\n'))
                return
            page = frame.Document.getObject('TD_Page_Specs')
            if page is None:
                FreeCAD.Console.PrintWarning(tr(u'AlumFrame: 未找到图纸\n'))
                return
            filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
                None, tr(u'导出图纸'), 'alumframe_drawing.pdf', 'PDF Files (*.pdf)')
            if not filepath:
                return
            from .techdraw_bom import export_page_pdf
            out = export_page_pdf(page, filepath)
            FreeCAD.Console.PrintMessage(tr(u'AlumFrame: 图纸已导出 %s\n') % out)
        except Exception as e:
            FreeCAD.Console.PrintError(tr(u'AlumFrame: 图纸导出失败: %s\n') % str(e))

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None


class AlumFrameWorkbench(Workbench):
    def __init__(self):
        self.__class__.Icon = os.path.join(
            os.path.dirname(__file__), 'icons', 'frame_xpm.xpm')
        self.__class__.MenuText = tr(u'铝型材框架')
        self.__class__.ToolTip = tr(u'快速生成铝型材框架、BOM 与加工图纸')

    def Initialize(self):
        cmds = ['AlumFrame_NewFrame', 'AlumFrame_EditFrame',
                'AlumFrame_ExportBom', 'AlumFrame_Drawings',
                'AlumFrame_ExportDrawings']
        self.appendToolbar(tr(u'铝型材框架'), cmds)
        self.appendMenu(tr(u'铝型材框架'), cmds)

    def Activated(self):
        # Don't force the task panel open (it may already be open); the user
        # can use the toolbar / menu buttons.
        pass

    def Deactivated(self):
        pass

    def GetClassName(self):
        return 'Gui::PythonWorkbench'


FreeCADGui.addCommand('AlumFrame_NewFrame', NewFrameCommand())
FreeCADGui.addCommand('AlumFrame_EditFrame', EditFrameCommand())
FreeCADGui.addCommand('AlumFrame_ExportBom', ExportBomCommand())
FreeCADGui.addCommand('AlumFrame_Drawings', DrawingsCommand())
FreeCADGui.addCommand('AlumFrame_ExportDrawings', ExportDrawingsCommand())
FreeCADGui.addWorkbench(AlumFrameWorkbench())
FreeCAD.Console.PrintMessage(u'AlumFrame workbench loaded successfully\n')
