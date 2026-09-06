# -*- coding: utf-8 -*-
"""
AlumFrame GUI — Task panel for the aluminum frame generator.
Provides a dialog to select profile, dimensions, and generate frame.
"""

try:
    from PySide import QtWidgets, QtCore
except ImportError:
    try:
        from PySide2 import QtWidgets, QtCore
    except ImportError:
        try:
            from PySide6 import QtWidgets, QtCore
        except ImportError:
            QtWidgets = None
            QtCore = None

from . import AlumFrame


class AlumFrameDialog(QtWidgets.QDialog):
    """Main dialog for generating aluminum frames."""

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