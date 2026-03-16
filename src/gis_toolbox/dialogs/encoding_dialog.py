# -*- coding: utf-8 -*-
"""
Encoding Dialog with modern card-based UI design
"""

from qgis.PyQt.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QComboBox, QRadioButton,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject

from .base_dialog import BaseLayerDialog


class EncodingDialog(BaseLayerDialog):
    """Dialog for batch encoding change with modern UI."""

    ENCODINGS = [
        ("UTF-8", "UTF-8"),
        ("System", "System"),
        ("CP949", "CP949"),
        ("EUC-KR", "EUC-KR"),
        ("ISO-8859-1", "ISO-8859-1"),
        ("Windows-1252", "Windows-1252"),
    ]

    def __init__(self, iface, parent=None):
        super().__init__(iface, "인코딩 변경", parent)
        self.setup_encoding_options()

    def setup_encoding_options(self):
        """Setup encoding-specific options in the options card."""
        # Card header
        header = QLabel("인코딩 설정")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #374151; border: none;")
        self.options_layout.addWidget(header)

        # Description
        desc = QLabel("선택한 레이어들의 문자 인코딩을 변경합니다. 한글이 깨지는 경우 CP949 또는 EUC-KR을 시도해보세요.")
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

        self.radio_batch = QRadioButton("일괄 설정 (모든 레이어에 동일 인코딩 적용)")
        self.radio_batch.setStyleSheet("font-size: 14px; color: #374151;")
        self.radio_individual = QRadioButton("개별 설정 (레이어별 인코딩 지정)")
        self.radio_individual.setStyleSheet("font-size: 14px; color: #374151;")
        self.radio_batch.setChecked(True)
        self.radio_batch.toggled.connect(self.on_mode_changed)

        mode_layout.addWidget(self.radio_batch)
        mode_layout.addWidget(self.radio_individual)
        self.options_layout.addWidget(mode_frame)

        # Batch encoding selection
        self.batch_frame = QFrame()
        self.batch_frame.setStyleSheet("border: none; background: transparent;")
        batch_layout = QVBoxLayout(self.batch_frame)
        batch_layout.setContentsMargins(0, 8, 0, 0)
        batch_layout.setSpacing(10)

        enc_label = QLabel("대상 인코딩")
        enc_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151;")
        batch_layout.addWidget(enc_label)

        self.encoding_combo = QComboBox()
        self.encoding_combo.setMinimumWidth(150)
        for display_name, value in self.ENCODINGS:
            self.encoding_combo.addItem(display_name, value)
        self.encoding_combo.setCurrentIndex(0)
        batch_layout.addWidget(self.encoding_combo)

        # Info notice
        info_frame = QFrame()
        info_frame.setObjectName("infoFrame")
        info_frame.setStyleSheet("""
            QFrame#infoFrame {
                background-color: #dbeafe;
                border: 1px solid #93c5fd;
                border-radius: 6px;
            }
        """)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 10, 12, 10)

        icon = QLabel("i")
        icon.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            color: #1e40af;
            background-color: #93c5fd;
            border-radius: 8px;
            padding: 2px 6px;
            border: none;
        """)
        icon.setFixedSize(20, 20)
        icon.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(icon)

        info_text = QLabel("인코딩 변경 후 레이어가 자동으로 새로고침됩니다")
        info_text.setStyleSheet("font-size: 13px; color: #1e40af; border: none; background: transparent;")
        info_layout.addWidget(info_text)
        info_layout.addStretch()

        batch_layout.addWidget(info_frame)
        self.options_layout.addWidget(self.batch_frame)

        # Individual encoding table
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

        table_label = QLabel("레이어별 인코딩 설정")
        table_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151;")
        individual_layout.addWidget(table_label)

        self.encoding_table = QTableWidget()
        self.encoding_table.setColumnCount(3)
        self.encoding_table.setHorizontalHeaderLabels(["레이어명", "현재 인코딩", "새 인코딩"])
        self.encoding_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.encoding_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.encoding_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.encoding_table.setStyleSheet("""
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
        self.encoding_table.setMinimumHeight(150)
        individual_layout.addWidget(self.encoding_table)

        self.options_layout.addWidget(self.individual_frame)
        self.options_layout.addStretch()

    def on_mode_changed(self, checked):
        """Handle mode change between batch and individual."""
        if hasattr(self, 'batch_frame'):
            self.batch_frame.setVisible(self.radio_batch.isChecked())
        if hasattr(self, 'individual_frame'):
            self.individual_frame.setVisible(self.radio_individual.isChecked())

    def load_layers(self):
        """Override to update encoding info after loading."""
        super().load_layers()
        # Auto-populate individual table if in individual mode
        if hasattr(self, 'radio_individual') and self.radio_individual.isChecked():
            self.load_layers_to_table()

    def load_layers_to_table(self):
        """Load selected layers into the encoding table."""
        if not hasattr(self, 'encoding_table'):
            return

        layers = self.get_selected_layers()
        self.encoding_table.setRowCount(len(layers))

        for row, layer in enumerate(layers):
            # Layer name
            name_item = QTableWidgetItem(layer.name())
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setData(Qt.UserRole, layer.id())
            self.encoding_table.setItem(row, 0, name_item)

            # Current encoding
            encoding = "알 수 없음"
            if layer.dataProvider():
                enc = layer.dataProvider().encoding()
                if enc:
                    encoding = enc

            current_item = QTableWidgetItem(encoding)
            current_item.setFlags(current_item.flags() & ~Qt.ItemIsEditable)
            self.encoding_table.setItem(row, 1, current_item)

            # New encoding dropdown
            new_encoding_combo = QComboBox()
            for display_name, value in self.ENCODINGS:
                new_encoding_combo.addItem(display_name, value)
            new_encoding_combo.setCurrentIndex(0)
            self.encoding_table.setCellWidget(row, 2, new_encoding_combo)

    def execute(self):
        """Execute encoding change."""
        if hasattr(self, 'radio_batch') and self.radio_batch.isChecked():
            self.execute_batch()
        else:
            self.execute_individual()

    def execute_batch(self):
        """Apply same encoding to all selected layers."""
        layers = self.get_selected_layers()
        if not layers:
            self.show_warning("선택된 레이어가 없습니다.")
            return

        target_encoding = self.encoding_combo.currentData()
        self.start_progress(len(layers), "인코딩 변경 중...")

        success_count = 0
        error_layers = []

        for i, layer in enumerate(layers):
            self.update_progress(i, f"처리 중: {layer.name()}")
            try:
                provider = layer.dataProvider()
                if provider:
                    provider.setEncoding(target_encoding)
                    layer.reload()
                    layer.triggerRepaint()
                    success_count += 1
                else:
                    error_layers.append(layer.name())
            except Exception as e:
                error_layers.append(f"{layer.name()} ({str(e)})")

        self.finish_progress()

        message = f"{success_count}개 레이어의 인코딩이 {target_encoding}(으)로 변경되었습니다."
        if error_layers:
            message += f"\n\n실패한 레이어:\n" + "\n".join(error_layers)

        self.show_info(message)
        self.load_layers()

    def execute_individual(self):
        """Apply individual encoding to each layer."""
        if not hasattr(self, 'encoding_table') or self.encoding_table.rowCount() == 0:
            self.show_warning("레이어 목록이 비어있습니다. 레이어를 선택해주세요.")
            return

        project = QgsProject.instance()
        total = self.encoding_table.rowCount()
        self.start_progress(total, "인코딩 개별 변경 중...")
        success_count = 0
        error_layers = []

        for row in range(total):
            layer_id = self.encoding_table.item(row, 0).data(Qt.UserRole)
            layer = project.mapLayer(layer_id)
            self.update_progress(row, f"처리 중: {layer.name() if layer else ''}")

            if layer:
                encoding_combo = self.encoding_table.cellWidget(row, 2)
                if encoding_combo:
                    target_encoding = encoding_combo.currentData()
                    try:
                        provider = layer.dataProvider()
                        if provider:
                            provider.setEncoding(target_encoding)
                            layer.reload()
                            layer.triggerRepaint()
                            success_count += 1
                        else:
                            error_layers.append(layer.name())
                    except Exception as e:
                        error_layers.append(f"{layer.name()} ({str(e)})")

        self.finish_progress()

        message = f"{success_count}개 레이어의 인코딩이 변경되었습니다."
        if error_layers:
            message += f"\n\n실패한 레이어:\n" + "\n".join(error_layers)

        self.show_info(message)
        self.load_layers()
