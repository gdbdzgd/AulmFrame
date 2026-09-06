# -*- coding: utf-8 -*-
"""AlumFrame GUI — Task panel for the aluminum frame generator.

Two modes:
- New frame: generate into a new document
- Edit frame: load parameters from the selected/current frame and rebuild in place
"""

try:
    from PySide import QtWidgets, QtCore, QtGui
except ImportError:
    try:
        from PySide2 import QtWidgets, QtCore, QtGui
    except ImportError:
        try:
            from PySide6 import QtWidgets, QtCore, QtGui
        except ImportError:
            QtWidgets = None
            QtCore = None
            QtGui = None

import FreeCAD
import FreeCADGui

from .config import PROFILES
from . import make_frame, get_bom_summary, export_bom_csv
from .frame_builder import FrameBuilder


class AlumFrameTaskPanel:
    """Task panel for aluminum frame generator (appears in left sidebar)."""

    def __init__(self, edit_selected=False):
        if QtWidgets is None:
            raise RuntimeError('PySide/PySide2/PySide6 not available')

        self.form = QtWidgets.QWidget()
        self.form.setWindowTitle(u'铝型材框架生成器')
        self._target_doc_name = None
        self._last_beams = None
        self._build_ui()
        self._load_from_context(prefer_selection=edit_selected)

    # ========== UI ==========
    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self.form)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QtWidgets.QLabel(u'<h3>铝型材框架生成器</h3>')
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)

        # Mode / target status
        self.target_label = QtWidgets.QLabel(u'')
        self.target_label.setWordWrap(True)
        layout.addWidget(self.target_label)

        # Parameters group
        params_group = QtWidgets.QGroupBox(u'参数设置')
        params_layout = QtWidgets.QFormLayout(params_group)
        params_layout.setSpacing(5)

        self.profile_combo = QtWidgets.QComboBox()
        for k in sorted(PROFILES.keys()):
            # Round profiles are not supported yet - only offer square/rect
            if PROFILES[k]['type'] != 'round':
                self.profile_combo.addItem(k)
        idx = self.profile_combo.findText(u'40x40 方管')
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)
        params_layout.addRow(u'型材规格:', self.profile_combo)

        self.length_spin = QtWidgets.QDoubleSpinBox()
        self.length_spin.setRange(100, 20000)
        self.length_spin.setValue(600)
        self.length_spin.setSuffix(' mm')
        params_layout.addRow(u'长度 (X):', self.length_spin)

        self.width_spin = QtWidgets.QDoubleSpinBox()
        self.width_spin.setRange(100, 20000)
        self.width_spin.setValue(400)
        self.width_spin.setSuffix(' mm')
        params_layout.addRow(u'宽度 (Y):', self.width_spin)

        self.height_spin = QtWidgets.QDoubleSpinBox()
        self.height_spin.setRange(100, 20000)
        self.height_spin.setValue(500)
        self.height_spin.setSuffix(' mm')
        params_layout.addRow(u'高度 (Z):', self.height_spin)

        self.z_layers_spin = QtWidgets.QSpinBox()
        self.z_layers_spin.setRange(1, 20)
        self.z_layers_spin.setValue(1)
        params_layout.addRow(u'Z层数:', self.z_layers_spin)

        self.material_edit = QtWidgets.QLineEdit('Aluminum 6061')
        params_layout.addRow(u'材料:', self.material_edit)

        layout.addWidget(params_group)

        # Action buttons
        row1 = QtWidgets.QHBoxLayout()
        self.gen_btn = QtWidgets.QPushButton(u'生成 / 更新框架')
        self.gen_btn.setToolTip(u'按当前参数生成；编辑模式下就地重建当前文档的框架')
        self.gen_btn.clicked.connect(self._generate)
        self.load_btn = QtWidgets.QPushButton(u'读取选中参数')
        self.load_btn.setToolTip(u'从选中的框架（或其子对象）读取参数')
        self.load_btn.clicked.connect(self._load_selected)
        row1.addWidget(self.gen_btn)
        row1.addWidget(self.load_btn)
        layout.addLayout(row1)

        row2 = QtWidgets.QHBoxLayout()
        self.new_btn = QtWidgets.QPushButton(u'新建 (重置)')
        self.new_btn.setToolTip(u'切换到新建模式：下次生成将创建新文档')
        self.new_btn.clicked.connect(self._reset_new)
        self.bom_btn = QtWidgets.QPushButton(u'导出BOM (CSV)')
        self.bom_btn.setToolTip(u'导出物料清单到CSV文件')
        self.bom_btn.clicked.connect(self._export_bom)
        row2.addWidget(self.new_btn)
        row2.addWidget(self.bom_btn)
        layout.addLayout(row2)

        # Result area
        result_group = QtWidgets.QGroupBox(u'生成结果')
        result_layout = QtWidgets.QVBoxLayout(result_group)
        self.result_label = QtWidgets.QLabel(u'点击"生成 / 更新框架"开始')
        self.result_label.setWordWrap(True)
        self.result_label.setMinimumHeight(80)
        result_layout.addWidget(self.result_label)
        layout.addWidget(result_group)

        help_label = QtWidgets.QLabel(
            u'<small><i>提示：选中框架后点"读取选中参数"可编辑已有框架</i></small>'
        )
        help_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(help_label)

        layout.addStretch()

    # ========== Helpers ==========
    def _read_params(self):
        return {
            'profile': self.profile_combo.currentText(),
            'length': self.length_spin.value(),
            'width': self.width_spin.value(),
            'height': self.height_spin.value(),
            'z_layers': self.z_layers_spin.value(),
            'material': self.material_edit.text() or 'Aluminum 6061',
        }

    def _apply_params(self, p):
        idx = self.profile_combo.findText(p.get('profile', ''))
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)
        self.length_spin.setValue(p.get('length', 600))
        self.width_spin.setValue(p.get('width', 400))
        self.height_spin.setValue(p.get('height', 500))
        self.z_layers_spin.setValue(max(1, p.get('z_layers', 1)))
        self.material_edit.setText(p.get('material', 'Aluminum 6061'))

    def _update_target_label(self):
        if self._target_doc_name:
            try:
                doc = FreeCAD.getDocument(self._target_doc_name)
                label = doc.Label
            except Exception:
                label = self._target_doc_name
            self.target_label.setText(
                u'<font color="#2a7"><b>编辑模式:</b> 更新文档「%s」中的框架</font>' % label)
        else:
            self.target_label.setText(
                u'<font color="#777"><b>新建模式:</b> 将生成新文档</font>')

    def _set_target(self, frame_group):
        if frame_group is not None and frame_group.Document is not None:
            self._target_doc_name = frame_group.Document.Name
        else:
            self._target_doc_name = None
        self._update_target_label()

    # ========== Actions ==========
    def _load_from_context(self, prefer_selection=True):
        """Load parameters from selection or the active document's frame."""
        frame = None
        if prefer_selection:
            for obj in FreeCADGui.Selection.getSelection():
                frame = FrameBuilder.find_frame_group(obj=obj)
                if frame is not None:
                    break
        if frame is None:
            frame = FrameBuilder.find_frame_group(doc=FreeCAD.ActiveDocument)
        if frame is not None:
            self._apply_params(FrameBuilder.get_frame_params(frame))
            self._set_target(frame)
        else:
            self._set_target(None)

    def _load_selected(self):
        for obj in FreeCADGui.Selection.getSelection():
            frame = FrameBuilder.find_frame_group(obj=obj)
            if frame is not None:
                self._apply_params(FrameBuilder.get_frame_params(frame))
                self._set_target(frame)
                self.result_label.setText(u'<font color="green">✓ 已读取选中框架参数</font>')
                return
        self.result_label.setText(
            u'<font color="orange">未选中框架（请选中框架组或其任意子对象）</font>')

    def _reset_new(self):
        self._set_target(None)
        self.result_label.setText(u'已重置为新建模式，点击"生成 / 更新框架"创建新文档')

    def _generate(self):
        p = self._read_params()
        doc = None
        if self._target_doc_name:
            try:
                doc = FreeCAD.getDocument(self._target_doc_name)
            except Exception:
                doc = None
        try:
            doc, beams = make_frame(
                p['profile'], p['length'], p['width'], p['height'],
                p['material'], p['z_layers'], doc=doc)
            self._target_doc_name = doc.Name
            self._last_beams = beams
            self._update_target_label()

            summary = get_bom_summary(beams)
            lines = [u'<b>✓ 框架已生成</b>', u'<hr>', u'<b>BOM 汇总:</b>']
            for k, v in sorted(summary.items()):
                lines.append(u'  %s: 数量=%d, 总长=%.1fmm' % (k, v['qty'], v['length']))
            lines.append(u'<hr>')
            lines.append(u'共 <b>%d</b> 项型材, Z层数: <b>%d</b>' % (len(beams), p['z_layers']))
            self.result_label.setText('<br>'.join(lines))

            FreeCADGui.activeDocument().activeView().viewIsometric()
            FreeCADGui.SendMsgToActiveView("ViewFit")
        except Exception as e:
            self.result_label.setText(u'<font color="red">错误: %s</font>' % str(e))

    def _export_bom(self):
        if self._last_beams is None:
            self.result_label.setText(u'<font color="orange">请先生成框架</font>')
            return
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.form, u'保存BOM', 'bom.csv', 'CSV Files (*.csv)')
        if filepath:
            try:
                export_bom_csv(self._last_beams, filepath,
                               self.material_edit.text() or 'Aluminum 6061')
                self.result_label.setText(
                    u'<font color="green">✓ BOM已导出至: %s</font>' % filepath)
            except Exception as e:
                self.result_label.setText(u'<font color="red">导出错误: %s</font>' % str(e))

    # ========== Task panel protocol ==========
    def getStandardButtons(self):
        return QtWidgets.QDialogButtonBox.Close

    def reject(self):
        FreeCADGui.Control.closeDialog()


def open_task_panel(edit_selected=False):
    """Open the frame generator task panel."""
    panel = AlumFrameTaskPanel(edit_selected=edit_selected)
    FreeCADGui.Control.showDialog(panel)
    return panel
