# -*- coding: utf-8 -*-
"""AlumFrame GUI — Task panel for the aluminum frame generator.

Provides a FreeCAD task panel interface for generating aluminum frames.
The panel appears in the left sidebar when the workbench is activated.
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
from . import AlumFrame


class AlumFrameTaskPanel:
    """Task panel for aluminum frame generator (appears in left sidebar)."""

    def __init__(self):
        if QtWidgets is None:
            raise RuntimeError('PySide/PySide2/PySide6 not available')
        
        self.form = QtWidgets.QWidget()
        self.form.setWindowTitle(u'铝型材框架生成器')
        self._build_ui()
        self._last_boms = None

    def _build_ui(self):
        """Build the task panel UI."""
        layout = QtWidgets.QVBoxLayout(self.form)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title = QtWidgets.QLabel(u'<h3>铝型材框架生成器</h3>')
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)

        # Parameters group
        params_group = QtWidgets.QGroupBox(u'参数设置')
        params_layout = QtWidgets.QFormLayout(params_group)
        params_layout.setSpacing(5)

        # Profile combo
        self.profile_combo = QtWidgets.QComboBox()
        keys = sorted(AlumFrame.PROFILES.keys())
        for k in keys:
            self.profile_combo.addItem(k)
        idx = self.profile_combo.findText('40x40 方管')
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)
        params_layout.addRow(u'型材规格:', self.profile_combo)

        # Length (X)
        self.length_spin = QtWidgets.QDoubleSpinBox()
        self.length_spin.setRange(10, 20000)
        self.length_spin.setValue(600)
        self.length_spin.setSuffix(' mm')
        params_layout.addRow(u'长度 (X):', self.length_spin)

        # Width (Y)
        self.width_spin = QtWidgets.QDoubleSpinBox()
        self.width_spin.setRange(10, 20000)
        self.width_spin.setValue(400)
        self.width_spin.setSuffix(' mm')
        params_layout.addRow(u'宽度 (Y):', self.width_spin)

        # Height (Z)
        self.height_spin = QtWidgets.QDoubleSpinBox()
        self.height_spin.setRange(10, 20000)
        self.height_spin.setValue(500)
        self.height_spin.setSuffix(' mm')
        params_layout.addRow(u'高度 (Z):', self.height_spin)

        # Z layers
        self.z_layers_spin = QtWidgets.QSpinBox()
        self.z_layers_spin.setRange(1, 20)
        self.z_layers_spin.setValue(1)
        params_layout.addRow(u'Z层数:', self.z_layers_spin)

        # Material
        self.material_edit = QtWidgets.QLineEdit('Aluminum 6061')
        params_layout.addRow(u'材料:', self.material_edit)

        layout.addWidget(params_group)

        # Action buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.gen_btn = QtWidgets.QPushButton(u'生成框架')
        self.gen_btn.setToolTip(u'根据当前参数生成框架')
        self.gen_btn.clicked.connect(self._generate)
        
        self.preview_btn = QtWidgets.QPushButton(u'预览')
        self.preview_btn.setToolTip(u'预览框架（暂不支持）')
        self.preview_btn.setEnabled(False)
        
        btn_layout.addWidget(self.gen_btn)
        btn_layout.addWidget(self.preview_btn)
        layout.addLayout(btn_layout)

        # Export button
        self.bom_btn = QtWidgets.QPushButton(u'导出BOM (CSV)')
        self.bom_btn.setToolTip(u'导出物料清单到CSV文件')
        self.bom_btn.clicked.connect(self._export_bom)
        layout.addWidget(self.bom_btn)

        # Result area
        result_group = QtWidgets.QGroupBox(u'生成结果')
        result_layout = QtWidgets.QVBoxLayout(result_group)
        self.result_label = QtWidgets.QLabel(u'点击"生成框架"开始')
        self.result_label.setWordWrap(True)
        self.result_label.setMinimumHeight(80)
        result_layout.addWidget(self.result_label)
        layout.addWidget(result_group)

        # Help text
        help_label = QtWidgets.QLabel(
            u'<small><i>提示：切换出此工作台可关闭面板</i></small>'
        )
        help_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(help_label)

        layout.addStretch()

    def _generate(self):
        """Generate the frame with current parameters."""
        profile = self.profile_combo.currentText()
        length = self.length_spin.value()
        width = self.width_spin.value()
        height = self.height_spin.value()
        z_layers = self.z_layers_spin.value()
        material = self.material_edit.text() or 'Aluminum 6061'

        try:
            doc, beams, boms = AlumFrame.make_frame(profile, length, width, height, material, z_layers)
            self._last_boms = boms
            summary = AlumFrame.get_bom_summary(boms)
            lines = [u'<b>✓ 框架已生成</b>']
            lines.append(u'<hr>')
            lines.append(u'<b>BOM 汇总:</b>')
            for k, v in sorted(summary.items()):
                lines.append(u'  %s: 数量=%d, 总长=%.1fmm' % (k, v['qty'], v['length']))
            lines.append(u'<hr>')
            lines.append(u'共 <b>%d</b> 根型材' % len(beams))
            lines.append(u'Z层数: <b>%d</b>' % z_layers)
            self.result_label.setText('<br>'.join(lines))
            
            # Switch to 3D view to show the result
            FreeCADGui.activeDocument().activeView().viewIsometric()
            FreeCADGui.SendMsgToActiveView("ViewFit")
        except Exception as e:
            self.result_label.setText(u'<font color="red">错误: %s</font>' % str(e))

    def _export_bom(self):
        """Export BOM to CSV file."""
        if self._last_boms is None:
            self.result_label.setText(u'<font color="orange">请先生成框架</font>')
            return
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.form, u'保存BOM', 'bom.csv', 'CSV Files (*.csv)')
        if filepath:
            try:
                AlumFrame.export_bom_csv(self._last_boms, filepath,
                                         self.material_edit.text() or 'Aluminum 6061')
                self.result_label.setText(u'<font color="green">✓ BOM已导出至: %s</font>' % filepath)
            except Exception as e:
                self.result_label.setText(u'<font color="red">导出错误: %s</font>' % str(e))

    def getStandardButtons(self):
        """Return standard buttons for task panel (Close button)."""
        return QtWidgets.QDialogButtonBox.Close

    def reject(self):
        """Handle panel close."""
        FreeCADGui.Control.closeDialog()


# Keep backward compatibility - AlumFrameDialog for direct use
class AlumFrameDialog(QtWidgets.QDialog):
    """Standalone dialog for generating aluminum frames (for backward compatibility)."""

    def __init__(self, parent=None):
        if QtWidgets is None:
            raise RuntimeError('PySide/PySide2/PySide6 not available')
        super(AlumFrameDialog, self).__init__(parent)
        self.setWindowTitle(u'铝型材框架生成器')
        self.setMinimumWidth(340)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QFormLayout(self)

        # Profile combo
        self.profile_combo = QtWidgets.QComboBox()
        keys = sorted(AlumFrame.PROFILES.keys())
        for k in keys:
            self.profile_combo.addItem(k)
        idx = self.profile_combo.findText('40x40 方管')
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)
        layout.addRow(u'型材规格:', self.profile_combo)

        # Length (X)
        self.length_spin = QtWidgets.QDoubleSpinBox()
        self.length_spin.setRange(10, 20000)
        self.length_spin.setValue(600)
        self.length_spin.setSuffix(' mm')
        layout.addRow(u'长度 (X):', self.length_spin)

        # Width (Y)
        self.width_spin = QtWidgets.QDoubleSpinBox()
        self.width_spin.setRange(10, 20000)
        self.width_spin.setValue(400)
        self.width_spin.setSuffix(' mm')
        layout.addRow(u'宽度 (Y):', self.width_spin)

        # Height (Z)
        self.height_spin = QtWidgets.QDoubleSpinBox()
        self.height_spin.setRange(10, 20000)
        self.height_spin.setValue(500)
        self.height_spin.setSuffix(' mm')
        layout.addRow(u'高度 (Z):', self.height_spin)

        # Z layers
        self.z_layers_spin = QtWidgets.QSpinBox()
        self.z_layers_spin.setRange(1, 20)
        self.z_layers_spin.setValue(1)
        layout.addRow(u'Z层数:', self.z_layers_spin)

        # Material
        self.material_edit = QtWidgets.QLineEdit('Aluminum 6061')
        layout.addRow(u'材料:', self.material_edit)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.gen_btn = QtWidgets.QPushButton(u'生成框架')
        self.gen_btn.clicked.connect(self._generate)
        self.bom_btn = QtWidgets.QPushButton(u'导出BOM(CSV)')
        self.bom_btn.clicked.connect(self._export_bom)
        btn_layout.addWidget(self.gen_btn)
        btn_layout.addWidget(self.bom_btn)
        layout.addRow(btn_layout)

        # Result label
        self.result_label = QtWidgets.QLabel('')
        self.result_label.setWordWrap(True)
        layout.addRow(self.result_label)

        self._last_boms = None

    def _generate(self):
        profile = self.profile_combo.currentText()
        length = self.length_spin.value()
        width = self.width_spin.value()
        height = self.height_spin.value()
        z_layers = self.z_layers_spin.value()
        material = self.material_edit.text() or 'Aluminum 6061'

        try:
            doc, beams, boms = AlumFrame.make_frame(profile, length, width, height, material, z_layers)
            self._last_boms = boms
            summary = AlumFrame.get_bom_summary(boms)
            lines = [u'✓ 框架已生成\n', u'BOM 汇总:']
            for k, v in sorted(summary.items()):
                lines.append(u'  %s: 数量=%d, 总长=%.1fmm' % (k, v['qty'], v['length']))
            lines.append(u'\n共 %d 根型材' % len(beams))
            lines.append(u'  Z层数: %d' % z_layers)
            self.result_label.setText('\n'.join(lines))
        except Exception as e:
            self.result_label.setText(u'错误: %s' % str(e))

    def _export_bom(self):
        if self._last_boms is None:
            self.result_label.setText(u'请先生成框架')
            return
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, u'保存BOM', 'bom.csv', 'CSV Files (*.csv)')
        if filepath:
            try:
                AlumFrame.export_bom_csv(self._last_boms, filepath,
                                         self.material_edit.text() or 'Aluminum 6061')
                self.result_label.setText(u'BOM已导出至: %s' % filepath)
            except Exception as e:
                self.result_label.setText(u'导出错误: %s' % str(e))
