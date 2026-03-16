# -*- coding: utf-8 -*-
"""
Base dialog with modern card-based UI design
"""

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QFrame,
    QWidget, QMessageBox, QScrollArea, QSizePolicy,
    QProgressBar
)
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.core import QgsProject, QgsVectorLayer


# Global stylesheet for modern UI
DIALOG_STYLESHEET = """
QDialog, QDialog QWidget {
    font-family: 'Pretendard', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
    font-weight: bold;
}
QDialog {
    background-color: #f9fafb;
}
QLabel {
    color: #374151;
    font-weight: bold;
}
QComboBox {
    border: 1px solid #d1d5db;
    border-radius: 4px;
    padding: 8px 12px;
    background-color: #f9fafb;
    font-size: 14px;
    color: #374151;
}
QComboBox:hover {
    border-color: #9ca3af;
    background-color: white;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    border: 1px solid #d1d5db;
    background-color: white;
    selection-background-color: #e5e7eb;
}
QLineEdit {
    border: 1px solid #d1d5db;
    border-radius: 4px;
    padding: 8px 12px;
    background-color: #f9fafb;
    font-size: 14px;
    color: #374151;
}
QLineEdit:hover {
    border-color: #9ca3af;
}
QLineEdit:focus {
    border-color: #6b7280;
    background-color: white;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical {
    background-color: #f3f4f6;
    width: 10px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background-color: #9ca3af;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #6b7280;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QListWidget {
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    background-color: white;
    outline: none;
}
QListWidget::item {
    padding: 10px 12px;
    border-bottom: 1px solid #f3f4f6;
}
QListWidget::item:hover {
    background-color: #f9fafb;
}
QListWidget::item:selected {
    background-color: #eff6ff;
    color: #1e40af;
}
QRadioButton {
    font-size: 14px;
    color: #374151;
    spacing: 8px;
}
QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid #d1d5db;
    background-color: white;
}
QRadioButton::indicator:checked {
    border: 2px solid #2563eb;
    background-color: #2563eb;
}
QRadioButton::indicator:hover {
    border-color: #9ca3af;
}
QCheckBox {
    font-size: 14px;
    color: #374151;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #d1d5db;
    background-color: white;
}
QCheckBox::indicator:checked {
    border: 2px solid #2563eb;
    background-color: #2563eb;
}
QCheckBox::indicator:hover {
    border-color: #9ca3af;
}
"""


class LayerListItem(QWidget):
    """Modern layer list item with checkbox"""

    def __init__(self, layer_name, layer_id, parent=None):
        super().__init__(parent)
        self.layer_name = layer_name
        self.layer_id = layer_id
        self.checked = False
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedHeight(30)
        self._update_container_style()

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(6)

        # Modern checkbox indicator (circle style)
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

        self.setLayout(layout)
        self.setCursor(Qt.PointingHandCursor)

    def _update_container_style(self):
        if self.checked:
            self.setStyleSheet("""
                LayerListItem {
                    background-color: #eff6ff;
                    border: 1px solid #93c5fd;
                    border-radius: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                LayerListItem {
                    background-color: white;
                    border: 1px solid #e5e7eb;
                    border-radius: 6px;
                }
                LayerListItem:hover {
                    border-color: #d1d5db;
                    background-color: #fafafa;
                }
            """)

    def _update_checkbox_style(self):
        if self.checked:
            self.check_indicator.setStyleSheet("""
                QFrame {
                    background-color: #2563eb;
                    border: 2px solid #2563eb;
                    border-radius: 4px;
                }
            """)
        else:
            self.check_indicator.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 2px solid #d1d5db;
                    border-radius: 4px;
                }
            """)

    def mousePressEvent(self, event):
        self.toggle_check()
        super().mousePressEvent(event)

    def toggle_check(self):
        self.checked = not self.checked
        self._update_container_style()
        self._update_checkbox_style()

    def set_checked(self, checked):
        self.checked = checked
        self._update_container_style()
        self._update_checkbox_style()


class BaseLayerDialog(QDialog):
    """Base dialog with modern card-based UI and layer list."""

    def __init__(self, iface, title="GIS Toolbox", parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Window)
        self.setMinimumSize(550, 700)
        self.resize(550, 750)
        self.setStyleSheet(DIALOG_STYLESHEET)

        self.layer_items = []
        self.setup_ui()
        self.load_layers()

    def setup_ui(self):
        """Setup the modern UI layout."""
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #f9fafb; }")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content.setStyleSheet("background-color: #f9fafb;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        # Layer selection card
        layer_card = self._create_layer_card()
        content_layout.addWidget(layer_card)

        # Options card (to be extended by subclasses)
        self.options_card = self._create_options_card()
        content_layout.addWidget(self.options_card)

        content_layout.addStretch()
        content.setLayout(content_layout)
        scroll_area.setWidget(content)
        layout.addWidget(scroll_area, 1)

        # Footer
        footer = self._create_footer()
        layout.addWidget(footer)

        self.setLayout(layout)

    def _create_header(self):
        """Create header with title."""
        header = QFrame()
        header.setObjectName("headerFrame")
        header.setStyleSheet("""
            QFrame#headerFrame {
                background-color: white;
                border-bottom: 1px solid #e5e7eb;
            }
        """)
        header.setFixedHeight(60)

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel(self.windowTitle())
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1f2937; border: none;")
        layout.addWidget(title)
        layout.addStretch()

        header.setLayout(layout)
        return header

    def _create_layer_card(self):
        """Create layer selection card."""
        card = QFrame()
        card.setObjectName("layerCard")
        card.setStyleSheet("""
            QFrame#layerCard {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Card header with badge
        header_layout = QHBoxLayout()
        header = QLabel("레이어 선택")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #374151; border: none;")
        header_layout.addWidget(header)

        self.layer_count_badge = QLabel("0개")
        self.layer_count_badge.setStyleSheet("""
            background-color: #e5e7eb;
            color: #6b7280;
            font-size: 11px;
            font-weight: bold;
            padding: 2px 8px;
            border-radius: 10px;
            border: none;
        """)
        header_layout.addWidget(self.layer_count_badge)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Selection buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_select_all = QPushButton("전체 선택")
        self.btn_select_all.setCursor(Qt.PointingHandCursor)
        self.btn_select_all.setStyleSheet("""
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
        self.btn_select_all.clicked.connect(self.select_all)
        btn_layout.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("전체 해제")
        self.btn_deselect_all.setCursor(Qt.PointingHandCursor)
        self.btn_deselect_all.setStyleSheet("""
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
        self.btn_deselect_all.clicked.connect(self.deselect_all)
        btn_layout.addWidget(self.btn_deselect_all)

        self.btn_refresh = QPushButton("새로고침")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet("""
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
        self.btn_refresh.clicked.connect(self.load_layers)
        btn_layout.addWidget(self.btn_refresh)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Scroll area for layer list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setMinimumHeight(200)
        scroll.setMaximumHeight(350)

        self.layer_container = QWidget()
        self.layer_container.setStyleSheet("background: transparent;")
        self.layer_container_layout = QVBoxLayout()
        self.layer_container_layout.setSpacing(2)
        self.layer_container_layout.setContentsMargins(0, 0, 0, 0)
        self.layer_container_layout.addStretch()
        self.layer_container.setLayout(self.layer_container_layout)

        scroll.setWidget(self.layer_container)
        layout.addWidget(scroll)

        card.setLayout(layout)
        return card

    def _create_options_card(self):
        """Create options card. Override in subclasses."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame#optionsCard {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """)
        card.setObjectName("optionsCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.options_layout = QVBoxLayout()
        self.options_layout.setSpacing(10)
        self.options_layout.setContentsMargins(16, 16, 16, 16)

        card.setLayout(self.options_layout)
        return card

    def _create_footer(self):
        """Create footer with progress bar and action buttons."""
        footer = QFrame()
        footer.setObjectName("footerFrame")
        footer.setStyleSheet("""
            QFrame#footerFrame {
                background-color: white;
                border-top: 1px solid #e5e7eb;
            }
        """)

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #e5e7eb;
            }
            QProgressBar::chunk {
                background-color: #2563eb;
                border-radius: 0px;
            }
        """)
        outer_layout.addWidget(self.progress_bar)

        # Progress label
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #6b7280; font-size: 12px; border: none; padding: 2px 20px 0px 20px;")
        self.progress_label.setVisible(False)
        outer_layout.addWidget(self.progress_label)

        # Buttons row
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 10, 20, 12)

        # Selected count label
        self.lbl_selected = QLabel("선택된 레이어: 0개")
        self.lbl_selected.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")
        layout.addWidget(self.lbl_selected)

        layout.addStretch()

        # Close button
        btn_close = QPushButton("닫기")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                color: #6b7280;
                font-size: 14px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #f3f4f6;
                border-color: #9ca3af;
            }
        """)
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        # Execute button
        self.btn_execute = QPushButton("실행")
        self.btn_execute.setCursor(Qt.PointingHandCursor)
        self.btn_execute.setStyleSheet("""
            QPushButton {
                background-color: #1f2937;
                border: none;
                border-radius: 4px;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 24px;
            }
            QPushButton:hover {
                background-color: #374151;
            }
            QPushButton:pressed {
                background-color: #111827;
            }
        """)
        self.btn_execute.clicked.connect(self.execute)
        layout.addWidget(self.btn_execute)

        outer_layout.addLayout(layout)
        footer.setLayout(outer_layout)
        return footer

    def start_progress(self, total, label="처리 중..."):
        """Show and initialize progress bar."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_label.setText(label)
        self.progress_label.setVisible(True)
        self.btn_execute.setEnabled(False)

    def update_progress(self, value, label=None):
        """Update progress bar value and optional label."""
        self.progress_bar.setValue(value)
        if label:
            self.progress_label.setText(label)
        from qgis.PyQt.QtWidgets import QApplication
        QApplication.processEvents()

    def finish_progress(self):
        """Hide progress bar and re-enable execute button."""
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_label.setText("완료")
        self.btn_execute.setEnabled(True)
        QTimer.singleShot(2000, self._hide_progress)

    def _hide_progress(self):
        """Hide progress bar after delay."""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.progress_bar.setValue(0)

    def showEvent(self, event):
        """Auto-reload layers every time the dialog is shown."""
        super().showEvent(event)
        self.load_layers()

    def get_vector_layers(self):
        """Get all vector layers from project. Override to filter."""
        layers = []
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                layers.append(layer)
        return layers

    def load_layers(self):
        """Load layers into the container."""
        # Clear existing items
        for item in self.layer_items:
            item.setParent(None)
            item.deleteLater()
        self.layer_items.clear()

        # Remove stretch
        while self.layer_container_layout.count():
            item = self.layer_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        layers = self.get_vector_layers()

        for layer in layers:
            item = LayerListItem(layer.name(), layer.id())
            self.layer_container_layout.addWidget(item)
            self.layer_items.append(item)

        self.layer_container_layout.addStretch()

        # Update badge
        self.layer_count_badge.setText(f"{len(layers)}개")
        self._update_selected_count()

    def select_all(self):
        """Select all layers."""
        for item in self.layer_items:
            item.set_checked(True)
        self._update_selected_count()

    def deselect_all(self):
        """Deselect all layers."""
        for item in self.layer_items:
            item.set_checked(False)
        self._update_selected_count()

    def _update_selected_count(self):
        """Update selected layer count."""
        count = len(self.get_selected_layers())
        self.lbl_selected.setText(f"선택된 레이어: {count}개")
        if count > 0:
            self.lbl_selected.setStyleSheet("color: #059669; font-size: 13px; font-weight: bold; border: none;")
        else:
            self.lbl_selected.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")

    def get_selected_layers(self):
        """Get list of selected QgsVectorLayer objects."""
        selected = []
        project = QgsProject.instance()
        for item in self.layer_items:
            if item.checked:
                layer = project.mapLayer(item.layer_id)
                if layer:
                    selected.append(layer)
        return selected

    def execute(self):
        """Execute the operation. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement execute()")

    def show_info(self, message, title="정보"):
        """Show info message."""
        QMessageBox.information(self, title, message)

    def show_warning(self, message, title="경고"):
        """Show warning message."""
        QMessageBox.warning(self, title, message)

    def show_error(self, message, title="오류"):
        """Show error message."""
        QMessageBox.critical(self, title, message)
