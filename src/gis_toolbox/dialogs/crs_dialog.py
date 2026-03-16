# -*- coding: utf-8 -*-
"""
CRS Dialog with modern card-based UI design
"""

from qgis.PyQt.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QRadioButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QLabel, QButtonGroup, QSizePolicy
)
from qgis.PyQt.QtCore import Qt
from qgis.gui import QgsProjectionSelectionWidget
from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsVectorLayer

from .base_dialog import BaseLayerDialog, LayerListItem


CRS_POPUP_STYLESHEET = """
    * {
        font-weight: bold;
    }
    QDialog {
        background-color: #f9fafb;
        color: #374151;
    }
    QWidget {
        color: #374151;
    }
    QLabel {
        color: #374151;
        background-color: transparent;
    }
    QFrame {
        color: #374151;
    }
    QTreeView, QTreeWidget {
        background-color: white;
        color: #374151;
        border: 1px solid #d1d5db;
        border-radius: 4px;
        selection-background-color: #dbeafe;
        selection-color: #1e40af;
    }
    QTreeView::item {
        color: #374151;
        padding: 4px;
    }
    QTreeView::item:selected {
        background-color: #dbeafe;
        color: #1e40af;
    }
    QLineEdit {
        background-color: white;
        color: #374151;
        border: 1px solid #d1d5db;
        border-radius: 4px;
        padding: 6px 10px;
    }
    QGroupBox {
        color: #374151;
        font-weight: bold;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        margin-top: 8px;
        padding-top: 12px;
        background-color: #f9fafb;
    }
    QGroupBox::title {
        color: #374151;
        background-color: transparent;
    }
    QPushButton {
        background-color: #f3f4f6;
        border: 1px solid #d1d5db;
        border-radius: 4px;
        color: #374151;
        padding: 6px 14px;
    }
    QPushButton:hover {
        background-color: #e5e7eb;
    }
    QTextEdit, QPlainTextEdit {
        background-color: white;
        color: #374151;
        border: 1px solid #d1d5db;
        border-radius: 4px;
    }
    QComboBox {
        background-color: white;
        color: #374151;
        border: 1px solid #d1d5db;
        border-radius: 4px;
        padding: 4px 8px;
    }
    QComboBox QAbstractItemView {
        background-color: white;
        color: #374151;
        selection-background-color: #dbeafe;
        selection-color: #1e40af;
    }
    QHeaderView::section {
        background-color: #f9fafb;
        color: #374151;
        border: none;
        border-bottom: 1px solid #e5e7eb;
        padding: 6px;
    }
    QTableView, QTableWidget {
        background-color: white;
        color: #374151;
        border: 1px solid #d1d5db;
    }
    QTabWidget::pane {
        border: 1px solid #d1d5db;
        background-color: #f9fafb;
    }
    QTabBar::tab {
        background-color: #e5e7eb;
        color: #374151;
        padding: 6px 12px;
        border: 1px solid #d1d5db;
    }
    QTabBar::tab:selected {
        background-color: white;
    }
"""


class CrsLayerListItem(LayerListItem):
    """Layer list item that also shows current CRS."""

    def __init__(self, layer_name, layer_id, crs_text, parent=None):
        self.crs_text = crs_text
        super().__init__(layer_name, layer_id, parent)

    def _setup_ui(self):
        self.setFixedHeight(30)
        self._update_container_style()

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(6)

        # Checkbox indicator
        self.check_indicator = QFrame()
        self.check_indicator.setFixedSize(14, 14)
        self._update_checkbox_style()
        layout.addWidget(self.check_indicator)

        # Layer type badge
        type_badge = QLabel("V")
        type_badge.setFixedSize(18, 18)
        type_badge.setStyleSheet("""
            background-color: #dbeafe;
            color: #1e40af;
            font-size: 10px;
            font-weight: bold;
            border-radius: 9px;
        """)
        type_badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(type_badge)

        # Layer name
        self.name_label = QLabel(self.layer_name)
        self.name_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #374151; background: transparent;")
        self.name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.name_label)

        # CRS badge
        self.crs_label = QLabel(self.crs_text)
        self.crs_label.setStyleSheet("""
            background-color: #f0fdf4;
            color: #166534;
            font-size: 11px;
            font-weight: bold;
            padding: 1px 6px;
            border-radius: 8px;
            border: 1px solid #bbf7d0;
        """)
        if not self.crs_text or self.crs_text == "없음":
            self.crs_label.setStyleSheet("""
                background-color: #fef2f2;
                color: #991b1b;
                font-size: 11px;
                font-weight: bold;
                padding: 1px 6px;
                border-radius: 8px;
                border: 1px solid #fecaca;
            """)
        layout.addWidget(self.crs_label)

        self.setLayout(layout)
        self.setCursor(Qt.PointingHandCursor)


class CrsDialog(BaseLayerDialog):
    """Dialog for batch CRS definition with modern UI."""

    def __init__(self, iface, parent=None):
        super().__init__(iface, "좌표계 정의", parent)
        self.setup_crs_options()

    def setup_crs_options(self):
        """Setup CRS-specific options in the options card."""
        # Card header
        header = QLabel("좌표계 설정")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #374151; border: none;")
        self.options_layout.addWidget(header)

        # Description
        desc = QLabel("선택한 레이어들의 좌표계를 정의합니다. (재투영이 아닌 좌표계 정의)")
        desc.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")
        desc.setWordWrap(True)
        self.options_layout.addWidget(desc)

        # Mode selection
        mode_frame = QFrame()
        mode_frame.setObjectName("modeFrame")
        mode_frame.setStyleSheet("""
            QFrame#modeFrame {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
            }
        """)
        mode_layout = QVBoxLayout(mode_frame)
        mode_layout.setContentsMargins(12, 12, 12, 12)
        mode_layout.setSpacing(8)

        self.radio_batch = QRadioButton("일괄 설정 (모든 레이어에 동일 좌표계 적용)")
        self.radio_batch.setStyleSheet("font-size: 14px; color: #374151;")
        self.radio_individual = QRadioButton("개별 설정 (레이어별 좌표계 지정)")
        self.radio_individual.setStyleSheet("font-size: 14px; color: #374151;")
        self.radio_batch.setChecked(True)
        self.radio_batch.toggled.connect(self.on_mode_changed)

        mode_layout.addWidget(self.radio_batch)
        mode_layout.addWidget(self.radio_individual)
        self.options_layout.addWidget(mode_frame)

        # Batch CRS selection
        self.batch_frame = QFrame()
        self.batch_frame.setStyleSheet("border: none; background: transparent;")
        batch_layout = QVBoxLayout(self.batch_frame)
        batch_layout.setContentsMargins(0, 8, 0, 0)
        batch_layout.setSpacing(10)

        crs_label = QLabel("대상 좌표계")
        crs_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151;")
        batch_layout.addWidget(crs_label)

        self.crs_widget = QgsProjectionSelectionWidget()
        self.crs_widget.setCrs(QgsCoordinateReferenceSystem("EPSG:5186"))
        batch_layout.addWidget(self.crs_widget)

        # Quick CRS buttons
        quick_label = QLabel("빠른 선택")
        quick_label.setStyleSheet("font-size: 13px; color: #6b7280;")
        batch_layout.addWidget(quick_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        crs_buttons = [
            ("EPSG:5186", "Korea 2000 중부"),
            ("EPSG:5179", "Korea 2000 통합"),
            ("EPSG:4326", "WGS84"),
            ("EPSG:5174", "Korea 1985 중부"),
        ]

        for epsg, tooltip in crs_buttons:
            btn = QPushButton(epsg)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f3f4f6;
                    border: 1px solid #d1d5db;
                    border-radius: 4px;
                    color: #374151;
                    font-size: 12px;
                    padding: 6px 10px;
                }
                QPushButton:hover {
                    background-color: #e5e7eb;
                    border-color: #9ca3af;
                }
            """)
            btn.clicked.connect(lambda checked, e=epsg: self.set_crs(e))
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        batch_layout.addLayout(btn_layout)

        self.options_layout.addWidget(self.batch_frame)

        # Individual CRS table
        self.individual_frame = QFrame()
        self.individual_frame.setStyleSheet("border: none; background: transparent;")
        self.individual_frame.setVisible(False)
        individual_layout = QVBoxLayout(self.individual_frame)
        individual_layout.setContentsMargins(0, 8, 0, 0)
        individual_layout.setSpacing(10)

        # Load button (unified style - above table)
        btn_load = QPushButton("선택된 레이어 불러오기")
        btn_load.setCursor(Qt.PointingHandCursor)
        btn_load.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                border: none;
                border-radius: 4px;
                color: white;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        btn_load.clicked.connect(self.load_layers_to_table)
        individual_layout.addWidget(btn_load)

        table_label = QLabel("레이어별 좌표계 설정")
        table_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151;")
        individual_layout.addWidget(table_label)

        self.crs_table = QTableWidget()
        self.crs_table.setColumnCount(3)
        self.crs_table.setHorizontalHeaderLabels(["레이어명", "현재 좌표계", "새 좌표계"])
        self.crs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.crs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.crs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.crs_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #f9fafb;
                border: none;
                border-bottom: 1px solid #e5e7eb;
                padding: 8px;
                font-weight: bold;
                color: #374151;
            }
        """)
        self.crs_table.setMinimumHeight(150)
        individual_layout.addWidget(self.crs_table)

        self.options_layout.addWidget(self.individual_frame)
        self.options_layout.addStretch()

    def showEvent(self, event):
        """Override to install event filter for CRS popup styling."""
        super().showEvent(event)
        from qgis.PyQt.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)

    def hideEvent(self, event):
        """Remove event filter when hidden."""
        super().hideEvent(event)
        from qgis.PyQt.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self)

    def eventFilter(self, obj, event):
        """Catch any dialog that opens (CRS selector popup) and apply light theme."""
        from qgis.PyQt.QtCore import QEvent
        from qgis.PyQt.QtWidgets import QDialog
        if event.type() == QEvent.Show and isinstance(obj, QDialog) and obj is not self:
            # Apply light theme to any popup dialog opened while this dialog is visible
            obj.setStyleSheet(CRS_POPUP_STYLESHEET)
        return super().eventFilter(obj, event)

    def load_layers(self):
        """Override to show CRS info in layer list."""
        for item in self.layer_items:
            item.setParent(None)
            item.deleteLater()
        self.layer_items.clear()

        while self.layer_container_layout.count():
            child = self.layer_container_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        layers = self.get_vector_layers()

        for layer in layers:
            crs_text = layer.crs().authid() if layer.crs().isValid() else "없음"
            item = CrsLayerListItem(layer.name(), layer.id(), crs_text)
            self.layer_container_layout.addWidget(item)
            self.layer_items.append(item)

        self.layer_container_layout.addStretch()
        self.layer_count_badge.setText(f"{len(layers)}개")
        self._update_selected_count()

    def set_crs(self, epsg_code):
        """Set CRS from EPSG code."""
        crs = QgsCoordinateReferenceSystem(epsg_code)
        self.crs_widget.setCrs(crs)

    def on_mode_changed(self, checked):
        """Handle mode change between batch and individual."""
        self.batch_frame.setVisible(self.radio_batch.isChecked())
        self.individual_frame.setVisible(self.radio_individual.isChecked())

    def load_layers_to_table(self):
        """Load selected layers into the CRS table."""
        layers = self.get_selected_layers()
        self.crs_table.setRowCount(len(layers))

        for row, layer in enumerate(layers):
            # Layer name
            name_item = QTableWidgetItem(layer.name())
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setData(Qt.UserRole, layer.id())
            self.crs_table.setItem(row, 0, name_item)

            # Current CRS
            current_crs = layer.crs().authid() if layer.crs().isValid() else "없음"
            current_item = QTableWidgetItem(current_crs)
            current_item.setFlags(current_item.flags() & ~Qt.ItemIsEditable)
            self.crs_table.setItem(row, 1, current_item)

            # New CRS widget
            new_crs_widget = QgsProjectionSelectionWidget()
            new_crs_widget.setCrs(self.crs_widget.crs())
            self.crs_table.setCellWidget(row, 2, new_crs_widget)

    def execute(self):
        """Execute CRS definition."""
        if self.radio_batch.isChecked():
            self.execute_batch()
        else:
            self.execute_individual()

    def execute_batch(self):
        """Apply same CRS to all selected layers."""
        layers = self.get_selected_layers()
        if not layers:
            self.show_warning("선택된 레이어가 없습니다.")
            return

        target_crs = self.crs_widget.crs()
        if not target_crs.isValid():
            self.show_warning("유효한 좌표계를 선택해주세요.")
            return

        self.start_progress(len(layers), "좌표계 정의 중...")

        success_count = 0
        for i, layer in enumerate(layers):
            self.update_progress(i, f"처리 중: {layer.name()}")
            try:
                layer.setCrs(target_crs)
                layer.triggerRepaint()
                success_count += 1
            except Exception as e:
                self.show_error(f"레이어 '{layer.name()}' 처리 중 오류: {str(e)}")

        self.finish_progress()
        self.show_info(f"{success_count}개 레이어의 좌표계가 {target_crs.authid()}로 정의되었습니다.")
        self.load_layers()

    def execute_individual(self):
        """Apply individual CRS to each layer."""
        if self.crs_table.rowCount() == 0:
            self.show_warning("먼저 '선택된 레이어 불러오기' 버튼을 클릭해주세요.")
            return

        project = QgsProject.instance()
        total = self.crs_table.rowCount()
        self.start_progress(total, "좌표계 개별 정의 중...")
        success_count = 0

        for row in range(total):
            layer_id = self.crs_table.item(row, 0).data(Qt.UserRole)
            layer = project.mapLayer(layer_id)
            self.update_progress(row, f"처리 중: {layer.name() if layer else ''}")

            if layer:
                crs_widget = self.crs_table.cellWidget(row, 2)
                if crs_widget:
                    new_crs = crs_widget.crs()
                    if new_crs.isValid():
                        layer.setCrs(new_crs)
                        layer.triggerRepaint()
                        success_count += 1

        self.finish_progress()
        self.show_info(f"{success_count}개 레이어의 좌표계가 정의되었습니다.")
        self.load_layers()
