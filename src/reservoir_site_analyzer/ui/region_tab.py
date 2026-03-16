# -*- coding: utf-8 -*-
"""
Region Selection Tab - Card-based UI
지역 선택 탭
"""

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QFrame,
)
from qgis.PyQt.QtCore import Qt, pyqtSignal


class RegionTab(QWidget):
    """Tab for region selection."""

    # Signals
    region_changed = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize the region tab."""
        super().__init__(parent)

        # Data storage
        self.sido_list = []
        self.sigungu_dict = {}
        self.eupmyeondong_dict = {}

        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # Region selection card
        region_card = self._create_region_card()
        layout.addWidget(region_card)

        # Help notice
        notice = self._create_notice()
        layout.addWidget(notice)

        layout.addStretch()
        self.setLayout(layout)

    def _create_region_card(self):
        """Create region selection card."""
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
        header = QLabel("지역 설정")
        header.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #374151; border: none;"
        )
        layout.addWidget(header)

        # Description
        desc = QLabel("분석할 지역을 선택하세요.")
        desc.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Sido row
        sido_layout = QHBoxLayout()
        sido_label = QLabel("시도")
        sido_label.setFixedWidth(60)
        sido_label.setStyleSheet("color: #6b7280; font-size: 14px; border: none;")
        self.cbx_sido = QComboBox()
        self.cbx_sido.currentIndexChanged.connect(self._on_sido_changed)
        sido_layout.addWidget(sido_label)
        sido_layout.addWidget(self.cbx_sido)
        layout.addLayout(sido_layout)

        # Sigungu row
        sigungu_layout = QHBoxLayout()
        sigungu_label = QLabel("시군구")
        sigungu_label.setFixedWidth(60)
        sigungu_label.setStyleSheet("color: #6b7280; font-size: 14px; border: none;")
        self.cbx_sigungu = QComboBox()
        self.cbx_sigungu.currentIndexChanged.connect(self._on_sigungu_changed)
        sigungu_layout.addWidget(sigungu_label)
        sigungu_layout.addWidget(self.cbx_sigungu)
        layout.addLayout(sigungu_layout)

        # Eupmyeondong row
        emd_layout = QHBoxLayout()
        emd_label = QLabel("읍면동")
        emd_label.setFixedWidth(60)
        emd_label.setStyleSheet("color: #6b7280; font-size: 14px; border: none;")
        self.cbx_eupmyeondong = QComboBox()
        self.cbx_eupmyeondong.currentIndexChanged.connect(self._on_emd_changed)
        emd_layout.addWidget(emd_label)
        emd_layout.addWidget(self.cbx_eupmyeondong)
        layout.addLayout(emd_layout)

        card.setLayout(layout)
        return card

    def _create_notice(self):
        """Create help notice."""
        notice = QFrame()
        notice.setStyleSheet(
            """
            QFrame {
                background-color: #dbeafe;
                border: 1px solid #93c5fd;
                border-radius: 6px;
            }
        """
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)

        # Info icon
        icon = QLabel("i")
        icon.setStyleSheet(
            """
            font-size: 13px;
            font-weight: bold;
            color: #1e40af;
            border: none;
            background-color: #93c5fd;
            border-radius: 8px;
            padding: 2px 6px;
        """
        )
        layout.addWidget(icon)

        # Notice text
        text = QLabel("행정경계는 DB에서 자동으로 로드됩니다")
        text.setStyleSheet("font-size: 13px; color: #1e40af; border: none;")
        layout.addWidget(text)
        layout.addStretch()

        notice.setLayout(layout)
        return notice

    def set_region_data(self, sido_list, sigungu_dict, eupmyeondong_dict):
        """Set region data and populate combos."""
        self.sido_list = sido_list
        self.sigungu_dict = sigungu_dict
        self.eupmyeondong_dict = eupmyeondong_dict
        self._populate_sido()

    def _populate_sido(self):
        """Populate sido combobox."""
        self.cbx_sido.clear()
        self.cbx_sido.addItem("-- 전체 --", "")

        for code, name in sorted(self.sido_list, key=lambda x: x[0]):
            self.cbx_sido.addItem(name, code)

    def _on_sido_changed(self, index):
        """Handle sido selection change."""
        self.cbx_sigungu.clear()
        self.cbx_sigungu.addItem("-- 전체 --", "")

        sido_code = self.cbx_sido.currentData()
        if sido_code and sido_code in self.sigungu_dict:
            for code, name in sorted(self.sigungu_dict[sido_code], key=lambda x: x[0]):
                self.cbx_sigungu.addItem(name, code)

        # Reset eupmyeondong
        self.cbx_eupmyeondong.clear()
        self.cbx_eupmyeondong.addItem("-- 전체 --", "")

        self.region_changed.emit()

    def _on_sigungu_changed(self, index):
        """Handle sigungu selection change."""
        self.cbx_eupmyeondong.clear()
        self.cbx_eupmyeondong.addItem("-- 전체 --", "")

        sigungu_code = self.cbx_sigungu.currentData()
        if sigungu_code and sigungu_code in self.eupmyeondong_dict:
            for code, name in sorted(
                self.eupmyeondong_dict[sigungu_code], key=lambda x: x[0]
            ):
                self.cbx_eupmyeondong.addItem(name, code)

        self.region_changed.emit()

    def _on_emd_changed(self, index):
        """Handle eupmyeondong selection change."""
        self.region_changed.emit()

    def get_selected_region_code(self):
        """Get the most specific selected region code."""
        emd_code = self.cbx_eupmyeondong.currentData()
        if emd_code:
            return emd_code

        sigungu_code = self.cbx_sigungu.currentData()
        if sigungu_code:
            return sigungu_code

        sido_code = self.cbx_sido.currentData()
        if sido_code:
            return sido_code

        return None

    def get_selected_region_name(self):
        """Get the selected region name."""
        emd_code = self.cbx_eupmyeondong.currentData()
        if emd_code:
            return self.cbx_eupmyeondong.currentText()

        sigungu_code = self.cbx_sigungu.currentData()
        if sigungu_code:
            return self.cbx_sigungu.currentText()

        sido_code = self.cbx_sido.currentData()
        if sido_code:
            return self.cbx_sido.currentText()

        return "전체"
