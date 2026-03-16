# -*- coding: utf-8 -*-
"""
Owner Condition Tab - Card-based UI
소유주체 조건 탭 (3단계)
"""

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QGridLayout,
    QSizePolicy,
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.gui import QgsMapLayerComboBox
from qgis.core import QgsMapLayerProxyModel


class OwnerChipButton(QPushButton):
    """Chip-style toggle button for owner selection."""

    def __init__(self, text, data_value, parent=None):
        super().__init__(text, parent)
        self.data_value = data_value
        self._selected = False
        self.setCheckable(True)
        self.setChecked(False)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setMinimumHeight(32)
        self._update_style()
        self.toggled.connect(self._on_toggled)

    def _on_toggled(self, checked):
        self._selected = checked
        self._update_style()

    def _update_style(self):
        if self._selected:
            self.setStyleSheet(
                """
                QPushButton {
                    background-color: #1f2937;
                    border: none;
                    border-radius: 16px;
                    padding: 6px 14px;
                    font-size: 13px;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #374151;
                }
            """
            )
        else:
            self.setStyleSheet(
                """
                QPushButton {
                    background-color: white;
                    border: 1px solid #d1d5db;
                    border-radius: 16px;
                    padding: 6px 14px;
                    font-size: 13px;
                    color: #6b7280;
                }
                QPushButton:hover {
                    background-color: #f3f4f6;
                    border-color: #9ca3af;
                }
            """
            )

    def is_selected(self):
        return self._selected

    def set_selected(self, selected):
        self._selected = selected
        self.setChecked(selected)
        self._update_style()


class OwnerTab(QWidget):
    """Tab for owner condition filtering (Step 3)."""

    # Signals
    owner_changed = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize the owner tab."""
        super().__init__(parent)

        # Data
        self.owner_list = []
        self.owner_chips = []

        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # Boundary layer selector card
        boundary_card = self._create_boundary_selector_card()
        layout.addWidget(boundary_card)

        # Owner filtering card
        self.owner_card = self._create_owner_card()
        layout.addWidget(self.owner_card)

        # Info card
        info_card = self._create_info_card()
        layout.addWidget(info_card)

        layout.addStretch()
        self.setLayout(layout)

    def _create_boundary_selector_card(self):
        """Create boundary layer selector card."""
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
        header = QLabel("지역경계 레이어 선택")
        header.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #374151; border: none;"
        )
        layout.addWidget(header)

        # Description
        desc = QLabel("소유주체 분석에 사용할 지역경계 벡터 레이어를 선택하세요.")
        desc.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Boundary layer combo box
        self.combo_boundary_layer = QgsMapLayerComboBox()
        self.combo_boundary_layer.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.combo_boundary_layer.setAllowEmptyLayer(True)
        self.combo_boundary_layer.setShowCrs(True)
        self.combo_boundary_layer.setStyleSheet(
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
        self.combo_boundary_layer.layerChanged.connect(
            lambda: self.owner_changed.emit()
        )
        layout.addWidget(self.combo_boundary_layer)

        card.setLayout(layout)
        return card

    def _create_owner_card(self):
        """Create owner filtering card."""
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

        self.owner_card_layout = QVBoxLayout()
        self.owner_card_layout.setSpacing(12)
        self.owner_card_layout.setContentsMargins(16, 16, 16, 16)

        # Card header with badge
        header_layout = QHBoxLayout()
        header = QLabel("소유주체 조건")
        header.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #374151; border: none;"
        )
        header_layout.addWidget(header)

        self.owner_badge = QLabel("0개 선택")
        self.owner_badge.setStyleSheet(
            """
            background-color: #e5e7eb;
            color: #374151;
            font-size: 11px;
            font-weight: bold;
            padding: 2px 8px;
            border-radius: 10px;
            border: none;
        """
        )
        self.owner_badge.setFixedHeight(20)
        header_layout.addWidget(self.owner_badge)
        header_layout.addStretch()

        # Select all / Deselect all buttons
        self.btn_select_all = QPushButton("전체선택")
        self.btn_select_all.setCursor(Qt.PointingHandCursor)
        self.btn_select_all.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: none;
                color: #3b82f6;
                font-size: 13px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                color: #1d4ed8;
                text-decoration: underline;
            }
        """
        )
        self.btn_select_all.clicked.connect(self._select_all)
        header_layout.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("전체해제")
        self.btn_deselect_all.setCursor(Qt.PointingHandCursor)
        self.btn_deselect_all.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: none;
                color: #6b7280;
                font-size: 13px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                color: #374151;
                text-decoration: underline;
            }
        """
        )
        self.btn_deselect_all.clicked.connect(self._deselect_all)
        header_layout.addWidget(self.btn_deselect_all)

        self.owner_card_layout.addLayout(header_layout)

        # Description
        desc = QLabel(
            "분석에 포함할 소유주체를 선택하세요. 선택하지 않으면 전체를 대상으로 분석합니다."
        )
        desc.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")
        desc.setWordWrap(True)
        self.owner_card_layout.addWidget(desc)

        # Chips container (will be populated later)
        self.chips_container = QFrame()
        self.chips_container.setStyleSheet("border: none; background: transparent;")
        self.chips_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.chips_layout = QGridLayout()
        self.chips_layout.setSpacing(8)
        self.chips_layout.setContentsMargins(0, 0, 0, 0)
        self.chips_container.setLayout(self.chips_layout)
        self.owner_card_layout.addWidget(self.chips_container)

        card.setLayout(self.owner_card_layout)
        return card

    def _create_info_card(self):
        """Create info card."""
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background-color: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 8px;
            }
        """
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Header
        header_layout = QHBoxLayout()
        icon = QLabel("ℹ")
        icon.setStyleSheet(
            """
            font-size: 14px;
            font-weight: bold;
            color: #1e40af;
            border: none;
        """
        )
        header_layout.addWidget(icon)
        header = QLabel("소유주체 필터링 안내")
        header.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #1e40af; border: none;"
        )
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Description
        desc = QLabel(
            "'다음 단계' 버튼을 클릭하면 선택한 지역경계 내의 소유주체 필지를 불러옵니다."
        )
        desc.setStyleSheet("color: #1e40af; font-size: 13px; border: none;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        card.setLayout(layout)
        return card

    def set_owner_list(self, owner_list):
        """Set owner list and populate chips."""
        self.owner_list = owner_list
        self._populate_owner_chips()

    def _populate_owner_chips(self):
        """Populate owner chips."""
        # Clear existing chips
        for chip in self.owner_chips:
            chip.deleteLater()
        self.owner_chips.clear()

        # Clear layout
        while self.chips_layout.count():
            item = self.chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add new chips (skip empty value which is "전체")
        row = 0
        col = 0
        max_cols = 3

        for value, label in self.owner_list:
            if not value:  # Skip "전체" option
                continue

            chip = OwnerChipButton(label, value)
            chip.toggled.connect(self._on_chip_toggled)
            self.owner_chips.append(chip)
            self.chips_layout.addWidget(chip, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # Update layout
        self.chips_container.adjustSize()
        self.owner_card.adjustSize()
        self._update_badge()

    def _on_chip_toggled(self, checked):
        """Handle chip toggle."""
        self._update_badge()
        self.owner_changed.emit()

    def _update_badge(self):
        """Update badge count."""
        selected = sum(1 for chip in self.owner_chips if chip.is_selected())
        if selected == 0:
            self.owner_badge.setText("미선택 (전체)")
            self.owner_badge.setStyleSheet(
                """
                background-color: #dbeafe;
                color: #1e40af;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 8px;
                border-radius: 10px;
                border: none;
            """
            )
        else:
            self.owner_badge.setText(f"{selected}개 선택")
            self.owner_badge.setStyleSheet(
                """
                background-color: #dcfce7;
                color: #166534;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 8px;
                border-radius: 10px;
                border: none;
            """
            )

    def _select_all(self):
        """Select all owner chips."""
        for chip in self.owner_chips:
            chip.set_selected(True)
        self._update_badge()
        self.owner_changed.emit()

    def _deselect_all(self):
        """Deselect all owner chips."""
        for chip in self.owner_chips:
            chip.set_selected(False)
        self._update_badge()
        self.owner_changed.emit()

    def get_owner_values(self):
        """Get list of selected owner values."""
        return [chip.data_value for chip in self.owner_chips if chip.is_selected()]

    def get_owner_labels(self):
        """Get list of selected owner labels."""
        return [chip.text() for chip in self.owner_chips if chip.is_selected()]

    def get_owner_label(self):
        """Get selected owner labels as string."""
        labels = self.get_owner_labels()
        if not labels:
            return "전체"
        elif len(labels) <= 2:
            return ", ".join(labels)
        else:
            return f"{labels[0]} 외 {len(labels)-1}개"

    def get_selected_boundary_layer(self):
        """Get selected boundary vector layer."""
        return self.combo_boundary_layer.currentLayer()

    def set_boundary_layer(self, layer):
        """Set boundary layer as default selection."""
        if layer:
            self.combo_boundary_layer.setLayer(layer)
