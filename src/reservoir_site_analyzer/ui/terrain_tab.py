# -*- coding: utf-8 -*-
"""
Terrain Conditions Tab - Card-based UI
지형 조건 탭 (고도, 경사)
"""

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QDoubleSpinBox,
    QFrame,
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.gui import QgsMapLayerComboBox
from qgis.core import QgsMapLayerProxyModel


class TerrainTab(QWidget):
    """Tab for terrain condition settings."""

    # Signals
    terrain_changed = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize the terrain tab."""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # DEM layer selector card
        dem_card = self._create_dem_selector_card()
        layout.addWidget(dem_card)

        # Elevation card
        elevation_card = self._create_elevation_card()
        layout.addWidget(elevation_card)

        # Slope card
        slope_card = self._create_slope_card()
        layout.addWidget(slope_card)

        # Info notice
        notice = self._create_notice()
        layout.addWidget(notice)

        layout.addStretch()
        self.setLayout(layout)

    def _create_dem_selector_card(self):
        """Create DEM layer selector card."""
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
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Card header
        header = QLabel("DEM 레이어 선택")
        header.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #374151; border: none;"
        )
        layout.addWidget(header)

        # Description
        desc = QLabel("분석에 사용할 DEM 래스터 레이어를 선택하세요.")
        desc.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # DEM layer combo box
        self.combo_dem_layer = QgsMapLayerComboBox()
        self.combo_dem_layer.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.combo_dem_layer.setAllowEmptyLayer(True)
        self.combo_dem_layer.setShowCrs(True)
        self.combo_dem_layer.setStyleSheet(
            """
            QgsMapLayerComboBox {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 8px 12px;
                background-color: #f9fafb;
                font-size: 14px;
                color: #374151;
            }
            QgsMapLayerComboBox:hover {
                border-color: #9ca3af;
                background-color: white;
            }
        """
        )
        self.combo_dem_layer.layerChanged.connect(lambda: self.terrain_changed.emit())
        layout.addWidget(self.combo_dem_layer)

        card.setLayout(layout)
        return card

    def _create_elevation_card(self):
        """Create elevation range settings card."""
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

        # Card header with badge
        header_layout = QHBoxLayout()
        header = QLabel("고도 조건 검색")
        header.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #374151; border: none;"
        )
        header_layout.addWidget(header)

        self.elevation_badge = QLabel("60 ~ 200 m")
        self.elevation_badge.setStyleSheet(
            """
            background-color: #dcfce7;
            color: #166534;
            font-size: 12px;
            font-weight: bold;
            padding: 4px 10px;
            border-radius: 12px;
            border: none;
        """
        )
        header_layout.addWidget(self.elevation_badge)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Description
        desc = QLabel("배수지 부지선정을 위한 고도 범위 설정 (최소고도 ~ 최대고도)")
        desc.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # --- 고도 범위 (한 줄) ---
        range_spin_layout = QHBoxLayout()
        range_spin_layout.setSpacing(8)

        lbl_min = QLabel("최소")
        lbl_min.setStyleSheet("font-size: 13px; color: #4b5563; border: none;")
        range_spin_layout.addWidget(lbl_min)

        self.spin_elevation = QDoubleSpinBox()
        self.spin_elevation.setMinimum(0)
        self.spin_elevation.setMaximum(2000)
        self.spin_elevation.setValue(60)
        self.spin_elevation.setSuffix(" m")
        self.spin_elevation.setDecimals(0)
        self.spin_elevation.setStyleSheet(self._get_spinbox_style())
        self.spin_elevation.valueChanged.connect(self._on_elevation_changed)
        range_spin_layout.addWidget(self.spin_elevation)

        lbl_tilde = QLabel("~")
        lbl_tilde.setStyleSheet("font-size: 16px; font-weight: bold; color: #6b7280; border: none;")
        lbl_tilde.setAlignment(Qt.AlignCenter)
        lbl_tilde.setFixedWidth(20)
        range_spin_layout.addWidget(lbl_tilde)

        lbl_max = QLabel("최대")
        lbl_max.setStyleSheet("font-size: 13px; color: #4b5563; border: none;")
        range_spin_layout.addWidget(lbl_max)

        self.spin_elevation_max = QDoubleSpinBox()
        self.spin_elevation_max.setMinimum(0)
        self.spin_elevation_max.setMaximum(2000)
        self.spin_elevation_max.setValue(200)
        self.spin_elevation_max.setSuffix(" m")
        self.spin_elevation_max.setDecimals(0)
        self.spin_elevation_max.setStyleSheet(self._get_spinbox_style())
        self.spin_elevation_max.valueChanged.connect(self._on_elevation_max_changed)
        range_spin_layout.addWidget(self.spin_elevation_max)

        range_spin_layout.addStretch()
        layout.addLayout(range_spin_layout)

        card.setLayout(layout)
        return card

    def _create_slope_card(self):
        """Create slope settings card."""
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

        # Card header with badge
        header_layout = QHBoxLayout()
        header = QLabel("최대 경사")
        header.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #374151; border: none;"
        )
        header_layout.addWidget(header)

        self.slope_badge = QLabel("26 도")
        self.slope_badge.setStyleSheet(
            """
            background-color: #fef3c7;
            color: #92400e;
            font-size: 12px;
            font-weight: bold;
            padding: 4px 10px;
            border-radius: 12px;
            border: none;
        """
        )
        header_layout.addWidget(self.slope_badge)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Description
        desc = QLabel("최대 경사도 설정")
        desc.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Spinbox
        spin_layout = QHBoxLayout()
        self.spin_slope = QDoubleSpinBox()
        self.spin_slope.setMinimum(0)
        self.spin_slope.setMaximum(60)
        self.spin_slope.setValue(26)
        self.spin_slope.setSuffix(" 도")
        self.spin_slope.setDecimals(0)
        self.spin_slope.setStyleSheet(self._get_spinbox_style())
        self.spin_slope.valueChanged.connect(self._on_slope_changed)
        spin_layout.addWidget(self.spin_slope)
        spin_layout.addStretch()
        layout.addLayout(spin_layout)

        card.setLayout(layout)
        return card

    def _create_notice(self):
        """Create info notice."""
        notice = QFrame()
        notice.setStyleSheet(
            """
            QFrame {
                background-color: #f3f4f6;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
            }
        """
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)

        title = QLabel("권장 기준")
        title.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #374151; border: none;"
        )
        layout.addWidget(title)

        items = [
            "- 고도 범위: 급수 구역보다 높은 위치 (일반적으로 60m~200m)",
            "- 최대 경사: 26도 이하 (건설 가능 경사)",
        ]
        for item in items:
            label = QLabel(item)
            label.setStyleSheet("font-size: 12px; color: #6b7280; border: none;")
            layout.addWidget(label)

        notice.setLayout(layout)
        return notice

    def _get_spinbox_style(self):
        """Get spinbox stylesheet for elevation range inputs."""
        return """
            QDoubleSpinBox {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 6px 8px;
                background-color: #f9fafb;
                font-size: 14px;
                color: #374151;
                min-width: 80px;
            }
            QDoubleSpinBox:hover {
                border-color: #9ca3af;
                background-color: white;
            }
            QDoubleSpinBox:focus {
                border-color: #1f2937;
                background-color: white;
            }
        """

    def _update_elevation_badge(self):
        """Update elevation badge with current min~max range."""
        min_val = int(self.spin_elevation.value())
        max_val = int(self.spin_elevation_max.value())
        self.elevation_badge.setText(f"{min_val} ~ {max_val} m")

    def _on_elevation_changed(self, value):
        """Handle min elevation spinbox change."""
        # 최소가 최대보다 크면 최대를 조정
        if int(value) > int(self.spin_elevation_max.value()):
            self.spin_elevation_max.setValue(int(value))
        self._update_elevation_badge()
        self.terrain_changed.emit()

    def _on_elevation_max_changed(self, value):
        """Handle max elevation spinbox change."""
        # 최대가 최소보다 작으면 최소를 조정
        if int(value) < int(self.spin_elevation.value()):
            self.spin_elevation.setValue(int(value))
        self._update_elevation_badge()
        self.terrain_changed.emit()

    def _on_slope_changed(self, value):
        """Handle slope spinbox change."""
        self.slope_badge.setText(f"{int(value)} 도")
        self.terrain_changed.emit()

    def get_min_elevation(self):
        """Get minimum elevation value."""
        return int(self.spin_elevation.value())

    def get_max_elevation(self):
        """Get maximum elevation value."""
        return int(self.spin_elevation_max.value())

    def get_max_slope(self):
        """Get maximum slope value."""
        return int(self.spin_slope.value())

    def get_selected_dem_layer(self):
        """Get selected DEM raster layer."""
        return self.combo_dem_layer.currentLayer()

    def set_dem_layer(self, layer):
        """Set DEM layer as default selection."""
        if layer:
            self.combo_dem_layer.setLayer(layer)
