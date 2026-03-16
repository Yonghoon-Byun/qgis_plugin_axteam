# -*- coding: utf-8 -*-
"""
Rename Dialog - Batch layer rename with modern card-based UI design
"""

from qgis.PyQt.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject

from .base_dialog import BaseLayerDialog


class RenameDialog(BaseLayerDialog):
    """Dialog for batch layer renaming with modern UI."""

    def __init__(self, iface, parent=None):
        super().__init__(iface, "레이어명 변경", parent)
        self.setup_rename_options()

    def setup_rename_options(self):
        """Setup rename-specific options in the options card."""
        # Card header
        header = QLabel("이름 변경 설정")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #374151; border: none;")
        self.options_layout.addWidget(header)

        # Description
        desc = QLabel("선택한 레이어들의 이름을 변경합니다. 접두사/접미사를 일괄 추가하거나 개별적으로 이름을 수정할 수 있습니다.")
        desc.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")
        desc.setWordWrap(True)
        self.options_layout.addWidget(desc)

        # Load button
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
        self.options_layout.addWidget(btn_load)

        # Prefix/Suffix batch controls
        batch_frame = QFrame()
        batch_frame.setObjectName("batchFrame")
        batch_frame.setStyleSheet("""
            QFrame#batchFrame {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
            }
        """)
        batch_layout = QVBoxLayout(batch_frame)
        batch_layout.setContentsMargins(12, 12, 12, 12)
        batch_layout.setSpacing(8)

        batch_label = QLabel("일괄 접두사/접미사 추가")
        batch_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151; border: none;")
        batch_layout.addWidget(batch_label)

        # Prefix row
        prefix_row = QHBoxLayout()
        prefix_row.setSpacing(8)
        prefix_label = QLabel("접두사")
        prefix_label.setStyleSheet("font-size: 13px; color: #374151; border: none;")
        prefix_label.setFixedWidth(45)
        prefix_row.addWidget(prefix_label)
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("예: NEW_")
        prefix_row.addWidget(self.prefix_edit)
        batch_layout.addLayout(prefix_row)

        # Suffix row
        suffix_row = QHBoxLayout()
        suffix_row.setSpacing(8)
        suffix_label = QLabel("접미사")
        suffix_label.setStyleSheet("font-size: 13px; color: #374151; border: none;")
        suffix_label.setFixedWidth(45)
        suffix_row.addWidget(suffix_label)
        self.suffix_edit = QLineEdit()
        self.suffix_edit.setPlaceholderText("예: _v2")
        suffix_row.addWidget(self.suffix_edit)
        batch_layout.addLayout(suffix_row)

        # Apply prefix/suffix button
        btn_apply = QPushButton("접두사/접미사 적용")
        btn_apply.setCursor(Qt.PointingHandCursor)
        btn_apply.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                color: #6b7280;
                font-size: 13px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #f3f4f6;
                border-color: #9ca3af;
            }
        """)
        btn_apply.clicked.connect(self.apply_prefix_suffix)
        batch_layout.addWidget(btn_apply)

        self.options_layout.addWidget(batch_frame)

        # Rename table
        table_label = QLabel("레이어별 이름 변경")
        table_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151; border: none;")
        self.options_layout.addWidget(table_label)

        self.rename_table = QTableWidget()
        self.rename_table.setColumnCount(2)
        self.rename_table.setHorizontalHeaderLabels(["현재 레이어명", "새 레이어명"])
        self.rename_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.rename_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.rename_table.setStyleSheet("""
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
        self.rename_table.setMinimumHeight(200)
        self.options_layout.addWidget(self.rename_table)

        self.options_layout.addStretch()

    def load_layers_to_table(self):
        """Load selected layers into the rename table."""
        layers = self.get_selected_layers()
        if not layers:
            self.show_warning("선택된 레이어가 없습니다.")
            return

        self.rename_table.setRowCount(len(layers))

        for row, layer in enumerate(layers):
            # Current layer name (read-only)
            name_item = QTableWidgetItem(layer.name())
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setData(Qt.UserRole, layer.id())
            self.rename_table.setItem(row, 0, name_item)

            # New layer name (editable QLineEdit)
            new_name_edit = QLineEdit(layer.name())
            self.rename_table.setCellWidget(row, 1, new_name_edit)

    def apply_prefix_suffix(self):
        """Apply prefix/suffix to all new name fields in the table."""
        if self.rename_table.rowCount() == 0:
            self.show_warning("테이블이 비어있습니다. 먼저 레이어를 불러와주세요.")
            return

        prefix = self.prefix_edit.text()
        suffix = self.suffix_edit.text()

        if not prefix and not suffix:
            self.show_warning("접두사 또는 접미사를 입력해주세요.")
            return

        for row in range(self.rename_table.rowCount()):
            edit_widget = self.rename_table.cellWidget(row, 1)
            if edit_widget:
                current = self.rename_table.item(row, 0).text()
                edit_widget.setText(f"{prefix}{current}{suffix}")

    def execute(self):
        """Execute layer renaming."""
        if self.rename_table.rowCount() == 0:
            self.show_warning("레이어 목록이 비어있습니다. 레이어를 선택 후 불러와주세요.")
            return

        project = QgsProject.instance()
        total = self.rename_table.rowCount()
        self.start_progress(total, "레이어명 변경 중...")

        success_count = 0
        error_layers = []

        for row in range(total):
            item = self.rename_table.item(row, 0)
            layer_id = item.data(Qt.UserRole)
            old_name = item.text()
            layer = project.mapLayer(layer_id)

            edit_widget = self.rename_table.cellWidget(row, 1)
            new_name = edit_widget.text().strip() if edit_widget else ""

            self.update_progress(row, f"처리 중: {old_name}")

            if not new_name:
                error_layers.append(f"{old_name} (새 이름이 비어있음)")
                continue

            if layer:
                try:
                    layer.setName(new_name)
                    success_count += 1
                except Exception as e:
                    error_layers.append(f"{old_name} ({str(e)})")
            else:
                error_layers.append(f"{old_name} (레이어를 찾을 수 없음)")

        self.finish_progress()

        message = f"{success_count}개 레이어의 이름이 변경되었습니다."
        if error_layers:
            message += f"\n\n실패한 레이어:\n" + "\n".join(error_layers)

        self.show_info(message)
        self.load_layers()
