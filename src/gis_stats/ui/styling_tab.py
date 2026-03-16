"""
Styling Tab - Color mapping with layer selection and preview
"""

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QSpinBox,
    QPushButton,
    QFrame,
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor, QPainter, QLinearGradient
from qgis.core import QgsProject, QgsVectorLayer


class ColorPreviewBar(QFrame):
    """Widget to preview color gradient."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)
        self.setStyleSheet("border: 1px solid #d1d5db; border-radius: 4px;")
        self._colors = []
        self._set_grayscale()

    def _set_grayscale(self):
        """Set default grayscale colors."""
        self._colors = [
            QColor(240, 240, 240),
            QColor(200, 200, 200),
            QColor(160, 160, 160),
            QColor(120, 120, 120),
            QColor(80, 80, 80),
        ]
        self.update()

    def set_colors(self, colors):
        """Set colors for the preview bar."""
        self._colors = colors
        self.update()

    def paintEvent(self, event):
        """Paint the color gradient."""
        super().paintEvent(event)
        if not self._colors:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width() - 2
        height = self.height() - 2
        segment_width = width // len(self._colors)

        for i, color in enumerate(self._colors):
            x = 1 + i * segment_width
            w = (
                segment_width
                if i < len(self._colors) - 1
                else width - i * segment_width
            )
            painter.fillRect(x, 1, w, height, color)

        painter.end()


class StylingTab(QWidget):
    """Tab for color mapping and styling."""

    # Signals
    style_requested = pyqtSignal(str, int, str)  # (field_name, num_classes, color_ramp)

    # Color ramp definitions
    COLOR_RAMPS = {
        "greys": (
            "무채색계열",
            [
                QColor(247, 247, 247),
                QColor(204, 204, 204),
                QColor(150, 150, 150),
                QColor(99, 99, 99),
                QColor(37, 37, 37),
            ],
        ),
        "blues": (
            "파랑계열",
            [
                QColor(239, 243, 255),
                QColor(189, 215, 231),
                QColor(107, 174, 214),
                QColor(49, 130, 189),
                QColor(8, 81, 156),
            ],
        ),
        "greens": (
            "초록계열",
            [
                QColor(237, 248, 233),
                QColor(186, 228, 179),
                QColor(116, 196, 118),
                QColor(49, 163, 84),
                QColor(0, 109, 44),
            ],
        ),
        "reds": (
            "빨강계열",
            [
                QColor(254, 229, 217),
                QColor(252, 174, 145),
                QColor(251, 106, 74),
                QColor(222, 45, 38),
                QColor(165, 15, 21),
            ],
        ),
        "oranges": (
            "주황계열",
            [
                QColor(254, 237, 222),
                QColor(253, 190, 133),
                QColor(253, 141, 60),
                QColor(230, 85, 13),
                QColor(166, 54, 3),
            ],
        ),
        "purples": (
            "보라계열",
            [
                QColor(242, 240, 247),
                QColor(203, 201, 226),
                QColor(158, 154, 200),
                QColor(117, 107, 177),
                QColor(84, 39, 143),
            ],
        ),
    }

    def __init__(self, style_manager, parent=None):
        """Initialize the styling tab."""
        super().__init__(parent)
        self.style_manager = style_manager
        self._layer = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # Layer and column card
        layer_card = self._create_layer_card()
        layout.addWidget(layer_card)

        # Classification card
        class_card = self._create_classification_card()
        layout.addWidget(class_card)

        layout.addStretch()
        self.setLayout(layout)

    def _create_layer_card(self):
        """Create layer and column selection card."""
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """
        )

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Card header
        header = QLabel("레이어 및 컬럼")
        header.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #374151; border: none;"
        )
        layout.addWidget(header)

        # Layer row
        layer_layout = QHBoxLayout()
        layer_label = QLabel("레이어")
        layer_label.setFixedWidth(40)
        layer_label.setStyleSheet("color: #6b7280; font-size: 14px; border: none;")

        self.cbx_layer = QComboBox()
        self.cbx_layer.currentIndexChanged.connect(self._on_layer_changed)

        self.btn_refresh = QPushButton()
        self.btn_refresh.setFixedSize(32, 32)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet(
            """
            QPushButton {
                background-color: #f3f4f6;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
        """
        )
        self.btn_refresh.setText("↻")
        self.btn_refresh.clicked.connect(lambda: self.refresh_layers())

        layer_layout.addWidget(layer_label)
        layer_layout.addWidget(self.cbx_layer)
        layer_layout.addWidget(self.btn_refresh)
        layout.addLayout(layer_layout)

        # Column row
        column_layout = QHBoxLayout()
        column_label = QLabel("컬럼")
        column_label.setFixedWidth(40)
        column_label.setStyleSheet("color: #6b7280; font-size: 14px; border: none;")

        self.cbx_column = QComboBox()

        column_layout.addWidget(column_label)
        column_layout.addWidget(self.cbx_column)
        layout.addLayout(column_layout)

        card.setLayout(layout)
        return card

    def _create_classification_card(self):
        """Create classification settings card."""
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """
        )

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Card header
        header = QLabel("분류 및 색상")
        header.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #374151; border: none;"
        )
        layout.addWidget(header)

        # Row with class count and color ramp
        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(16)

        # Class count
        count_layout = QVBoxLayout()
        count_label = QLabel("분류 개수")
        count_label.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")
        count_layout.addWidget(count_label)

        self.spn_classes = QSpinBox()
        self.spn_classes.setMinimum(3)
        self.spn_classes.setMaximum(10)
        self.spn_classes.setValue(5)
        self.spn_classes.setStyleSheet(
            """
            QSpinBox {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 8px 12px;
                background-color: #f9fafb;
                font-size: 14px;
                color: #374151;
            }
            QSpinBox:hover {
                border-color: #9ca3af;
            }
        """
        )
        self.spn_classes.setFixedWidth(80)
        count_layout.addWidget(self.spn_classes)
        settings_layout.addLayout(count_layout)

        # Color ramp
        ramp_layout = QVBoxLayout()
        ramp_label = QLabel("색상 테마")
        ramp_label.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")
        ramp_layout.addWidget(ramp_label)

        self.cbx_color_ramp = QComboBox()
        ramp_layout.addWidget(self.cbx_color_ramp)
        settings_layout.addLayout(ramp_layout)

        settings_layout.addStretch()
        layout.addLayout(settings_layout)

        # Preview section
        preview_label = QLabel("분류 방식: 분위수")
        preview_label.setStyleSheet("color: #9ca3af; font-size: 13px; border: none;")
        layout.addWidget(preview_label)

        # Color preview bar - MUST be created before _populate_color_ramps()
        self.color_preview = ColorPreviewBar()
        layout.addWidget(self.color_preview)

        # Populate color ramps after preview bar is created
        self._populate_color_ramps()
        self.cbx_color_ramp.currentIndexChanged.connect(self._on_color_ramp_changed)

        card.setLayout(layout)
        return card

    def _populate_color_ramps(self):
        """Populate color ramp combobox."""
        for ramp_key, (ramp_name, colors) in self.COLOR_RAMPS.items():
            self.cbx_color_ramp.addItem(ramp_name, ramp_key)

        # Set default to grayscale
        self.cbx_color_ramp.setCurrentIndex(0)
        self._update_color_preview()

    def _on_color_ramp_changed(self, index):
        """Handle color ramp selection change."""
        self._update_color_preview()

    def _update_color_preview(self):
        """Update the color preview bar."""
        ramp_key = self.cbx_color_ramp.currentData()
        if ramp_key and ramp_key in self.COLOR_RAMPS:
            _, colors = self.COLOR_RAMPS[ramp_key]
            self.color_preview.set_colors(colors)

    def set_layer(self, layer):
        """Set the layer to style."""
        self._layer = layer
        self.refresh_layers(select_layer=layer)

        if layer and layer.isValid():
            self._populate_columns()

    def refresh_layers(self, select_layer=None):
        """Refresh the layer combo box with all vector layers."""
        self.cbx_layer.blockSignals(True)
        self.cbx_layer.clear()

        self.cbx_layer.addItem("-- 레이어를 선택하세요 --", None)

        project = QgsProject.instance()
        layers = project.mapLayers().values()

        select_index = 0
        for layer in layers:
            if isinstance(layer, QgsVectorLayer):
                self.cbx_layer.addItem(layer.name(), layer.id())
                if select_layer and layer.id() == select_layer.id():
                    select_index = self.cbx_layer.count() - 1

        self.cbx_layer.blockSignals(False)

        if select_index > 0:
            self.cbx_layer.setCurrentIndex(select_index)

    def _on_layer_changed(self, index):
        """Handle layer selection change."""
        layer_id = self.cbx_layer.currentData()

        if layer_id:
            project = QgsProject.instance()
            layer = project.mapLayer(layer_id)
            if layer and isinstance(layer, QgsVectorLayer):
                self._layer = layer
                self._populate_columns()
                return

        self._layer = None
        self.cbx_column.clear()

    def _populate_columns(self):
        """Populate column combobox with numeric fields."""
        self.cbx_column.clear()

        if not self._layer:
            return

        numeric_fields = self.style_manager.get_numeric_fields(self._layer)

        # Filter to show only statistics columns (those with year suffix)
        stat_fields = [f for f in numeric_fields if "_20" in f]

        for field_name in stat_fields:
            self.cbx_column.addItem(field_name, field_name)

        # Also add original numeric fields if no stat fields found
        if not stat_fields:
            for field_name in numeric_fields:
                if field_name not in ["adm_cd"]:
                    self.cbx_column.addItem(field_name, field_name)

    def _on_apply_clicked(self):
        """Handle apply button click."""
        if not self._layer:
            return

        field_name = self.cbx_column.currentData()
        if not field_name:
            return

        num_classes = self.spn_classes.value()
        color_ramp = self.cbx_color_ramp.currentData()

        self.style_requested.emit(field_name, num_classes, color_ramp)

    def get_selected_field(self):
        """Get selected field name."""
        return self.cbx_column.currentData()
