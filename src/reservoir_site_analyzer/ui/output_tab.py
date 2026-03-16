# -*- coding: utf-8 -*-
"""
Output Settings Tab - Card-based UI
출력 설정 탭 (요약 정보 + 출력 레이어명)
"""

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QFrame,
)
from qgis.PyQt.QtCore import pyqtSignal
from qgis.gui import QgsMapLayerComboBox
from qgis.core import QgsMapLayerProxyModel


class OutputTab(QWidget):
    """Tab for output settings and analysis summary."""

    # Signals
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize the output tab."""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # Summary card
        summary_card = self._create_summary_card()
        layout.addWidget(summary_card)

        # Output settings card
        output_card = self._create_output_card()
        layout.addWidget(output_card)

        # Ready notice
        ready_card = self._create_ready_card()
        layout.addWidget(ready_card)

        layout.addStretch()
        self.setLayout(layout)

    def _create_summary_card(self):
        """Create analysis summary card."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Card header
        header = QLabel("분석 조건 요약")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #374151; border: none;")
        layout.addWidget(header)

        # Summary items container
        self.summary_container = QFrame()
        self.summary_container.setStyleSheet("border: none; background: transparent;")
        summary_layout = QVBoxLayout()
        summary_layout.setSpacing(12)
        summary_layout.setContentsMargins(0, 0, 0, 0)

        # Region row - Layer selector
        region_row = self._create_layer_selector_row(
            "선택 지역",
            QgsMapLayerProxyModel.PolygonLayer,
            "boundary_layer"
        )
        self.combo_boundary_layer = region_row.findChild(QgsMapLayerComboBox, "layer_combo")
        summary_layout.addWidget(region_row)

        # Terrain row - Polygon layer selector (filtered terrain result from step 2)
        terrain_row = self._create_layer_selector_row(
            "지형 조건",
            QgsMapLayerProxyModel.PolygonLayer,
            "terrain_layer"
        )
        self.combo_terrain_layer = terrain_row.findChild(QgsMapLayerComboBox, "layer_combo")
        summary_layout.addWidget(terrain_row)

        # Owner row - Vector layer selector
        owner_row = self._create_layer_selector_row(
            "소유주체",
            QgsMapLayerProxyModel.PolygonLayer,
            "owner_layer"
        )
        self.combo_owner_layer = owner_row.findChild(QgsMapLayerComboBox, "layer_combo")
        summary_layout.addWidget(owner_row)

        self.summary_container.setLayout(summary_layout)
        layout.addWidget(self.summary_container)

        card.setLayout(layout)
        return card

    def _create_summary_row(self, label_text, value_text):
        """Create a summary row with label and value."""
        row = QFrame()
        row.setStyleSheet("""
            QFrame {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 8px;
            }
        """)

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)

        label = QLabel(label_text)
        label.setStyleSheet("font-size: 13px; color: #6b7280; border: none; background: transparent;")
        label.setFixedWidth(70)
        layout.addWidget(label)

        value = QLabel(value_text)
        value.setObjectName("value_label")
        value.setStyleSheet("font-size: 13px; font-weight: bold; color: #374151; border: none; background: transparent;")
        layout.addWidget(value)
        layout.addStretch()

        row.setLayout(layout)
        return row

    def _create_layer_selector_row(self, label_text, layer_type, object_name):
        """Create a layer selector row with label and combo box.

        Args:
            label_text: Label text to display
            layer_type: QgsMapLayerProxyModel layer type filter
            object_name: Object name for the combo box
        """
        row = QFrame()
        row.setStyleSheet("""
            QFrame {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Label
        label = QLabel(label_text)
        label.setStyleSheet("font-size: 13px; font-weight: bold; color: #374151; border: none; background: transparent;")
        layout.addWidget(label)

        # Layer combo box
        combo = QgsMapLayerComboBox()
        combo.setObjectName("layer_combo")
        combo.setFilters(layer_type)
        combo.setAllowEmptyLayer(True)
        combo.setShowCrs(False)
        combo.setStyleSheet("""
            QgsMapLayerComboBox {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 6px 10px;
                background-color: white;
                font-size: 14px;
                color: #374151;
            }
            QgsMapLayerComboBox:hover {
                border-color: #9ca3af;
                background-color: #f9fafb;
            }
        """)
        combo.layerChanged.connect(lambda: self.settings_changed.emit())
        layout.addWidget(combo)

        row.setLayout(layout)
        return row

    def _create_output_card(self):
        """Create output settings card."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Card header
        header = QLabel("출력 설정")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #374151; border: none;")
        layout.addWidget(header)

        # Output layer name
        name_layout = QHBoxLayout()
        name_label = QLabel("레이어명")
        name_label.setFixedWidth(60)
        name_label.setStyleSheet("color: #6b7280; font-size: 14px; border: none;")
        self.txt_output_name = QLineEdit()
        self.txt_output_name.setText("4.적합부지_결과")
        self.txt_output_name.setPlaceholderText("출력 레이어 이름 입력")
        self.txt_output_name.textChanged.connect(lambda: self.settings_changed.emit())
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.txt_output_name)
        layout.addLayout(name_layout)

        card.setLayout(layout)
        return card

    def _create_ready_card(self):
        """Create analysis ready card."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #f0fdf4;
                border: 1px solid #86efac;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Header
        header_layout = QHBoxLayout()
        icon = QLabel("✓")
        icon.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #166534;
            border: none;
        """)
        header_layout.addWidget(icon)
        header = QLabel("분석 준비 완료")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #166534; border: none;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Description
        desc = QLabel("'분석 실행' 버튼을 클릭하면 선택한 조건에 맞는 적합 부지를 분석합니다.")
        desc.setStyleSheet("color: #166534; font-size: 13px; border: none;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Process steps
        steps = QLabel("분석 과정: 지형조건 결과 × 소유주체 필지 → 최종 적합 부지")
        steps.setStyleSheet("color: #15803d; font-size: 11px; border: none;")
        steps.setWordWrap(True)
        layout.addWidget(steps)

        card.setLayout(layout)
        return card

    def update_summary(self, region_name=None, elevation=None, slope=None, owner_label=None):
        """Update summary display with current values.

        Note: This method is kept for backward compatibility but does nothing
        since we now use layer selection combo boxes instead of summary labels.
        """
        # 레이어 선택 방식으로 변경되어 더 이상 요약 정보를 업데이트하지 않음
        pass

    def get_output_name(self):
        """Get output layer name."""
        name = self.txt_output_name.text().strip()
        return name if name else "4.적합부지_결과"

    def get_selected_boundary_layer(self):
        """Get selected boundary layer (선택 지역)."""
        return self.combo_boundary_layer.currentLayer()

    def get_selected_terrain_layer(self):
        """Get selected terrain/DEM layer (지형 조건)."""
        return self.combo_terrain_layer.currentLayer()

    def get_selected_owner_layer(self):
        """Get selected owner layer (소유주체)."""
        return self.combo_owner_layer.currentLayer()

    def set_selected_boundary_layer(self, layer):
        """Set boundary layer as default selection."""
        if layer:
            self.combo_boundary_layer.setLayer(layer)

    def set_selected_terrain_layer(self, layer):
        """Set terrain layer as default selection."""
        if layer:
            self.combo_terrain_layer.setLayer(layer)

    def set_selected_owner_layer(self, layer):
        """Set owner layer as default selection."""
        if layer:
            self.combo_owner_layer.setLayer(layer)
