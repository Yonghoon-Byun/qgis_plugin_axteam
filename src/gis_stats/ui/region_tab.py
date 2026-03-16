"""
Region Selection Tab - Card-based UI
"""

import os
import csv
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QFrame,
    QRadioButton,
    QButtonGroup,
)
from qgis.PyQt.QtCore import Qt, pyqtSignal


class RegionTab(QWidget):
    """Tab for region selection with display level."""

    # Signals
    region_changed = pyqtSignal(str, int)  # (region_code, display_level)

    def __init__(self, db_connection, parent=None):
        """Initialize the region tab."""
        super().__init__(parent)
        self.db = db_connection

        # Load region data
        self.region_data = self._load_region_data()

        self._setup_ui()
        self._initialize_data()

    def _load_region_data(self):
        """Load region data from CSV file."""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        csv_path = os.path.join(base_dir, "resources", "admin_regions.csv")

        if not os.path.exists(csv_path):
            csv_path = os.path.join(base_dir, "admin_regions.csv")

        if not os.path.exists(csv_path):
            print(f"Warning: admin_regions.csv not found")
            return []

        region_data = []
        try:
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    region_data.append({
                        "code": row["adm_cd"].strip(),
                        "name": row["adm_nm"].strip(),
                    })
        except Exception as e:
            print(f"Error loading region data: {e}")

        return region_data

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # Region selection card
        region_card = self._create_region_card()
        layout.addWidget(region_card)

        # Display level card
        level_card = self._create_display_level_card()
        layout.addWidget(level_card)

        # Notice for water supply statistics
        notice = self._create_notice()
        layout.addWidget(notice)

        layout.addStretch()
        self.setLayout(layout)

    def _create_region_card(self):
        """Create region selection card."""
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
        header = QLabel("지역 설정")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #374151; border: none;")
        layout.addWidget(header)

        # Sido row
        sido_layout = QHBoxLayout()
        sido_label = QLabel("시도")
        sido_label.setFixedWidth(50)
        sido_label.setStyleSheet("color: #6b7280; font-size: 14px; border: none;")
        self.cbx_sido = QComboBox()
        self.cbx_sido.currentIndexChanged.connect(self._on_sido_changed)
        sido_layout.addWidget(sido_label)
        sido_layout.addWidget(self.cbx_sido)
        layout.addLayout(sido_layout)

        # Sigungu row
        sigungu_layout = QHBoxLayout()
        sigungu_label = QLabel("시군구")
        sigungu_label.setFixedWidth(50)
        sigungu_label.setStyleSheet("color: #6b7280; font-size: 14px; border: none;")
        self.cbx_sigungu = QComboBox()
        self.cbx_sigungu.currentIndexChanged.connect(self._on_sigungu_changed)
        sigungu_layout.addWidget(sigungu_label)
        sigungu_layout.addWidget(self.cbx_sigungu)
        layout.addLayout(sigungu_layout)

        # Emd row
        emd_layout = QHBoxLayout()
        emd_label = QLabel("읍면동")
        emd_label.setFixedWidth(50)
        emd_label.setStyleSheet("color: #6b7280; font-size: 14px; border: none;")
        self.cbx_emd = QComboBox()
        self.cbx_emd.currentIndexChanged.connect(self._on_emd_changed)
        emd_layout.addWidget(emd_label)
        emd_layout.addWidget(self.cbx_emd)
        layout.addLayout(emd_layout)

        card.setLayout(layout)
        return card

    def _create_display_level_card(self):
        """Create display level selection card."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        # Card header
        header = QLabel("표시 레벨 (집계 단위)")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #374151; border: none;")
        layout.addWidget(header)

        # Radio buttons
        self.level_button_group = QButtonGroup(self)

        radio_style = """
            QRadioButton {
                spacing: 8px;
                font-size: 14px;
                color: #374151;
                padding: 6px 0;
                border: none;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton::indicator:checked {
                background-color: #1f2937;
                border: 2px solid #1f2937;
                border-radius: 8px;
            }
            QRadioButton::indicator:unchecked {
                background-color: white;
                border: 2px solid #d1d5db;
                border-radius: 8px;
            }
        """

        self.rb_sido = QRadioButton("시도 단위 (광역)")
        self.rb_sido.setStyleSheet(radio_style)
        self.rb_sigungu = QRadioButton("시군구 단위 (기초)")
        self.rb_sigungu.setStyleSheet(radio_style)
        self.rb_emd = QRadioButton("읍면동 단위 (세부)")
        self.rb_emd.setStyleSheet(radio_style)

        self.rb_emd.setChecked(True)

        self.level_button_group.addButton(self.rb_sido, 2)
        self.level_button_group.addButton(self.rb_sigungu, 5)
        self.level_button_group.addButton(self.rb_emd, 8)

        self.level_button_group.buttonClicked.connect(self._on_level_changed)

        layout.addWidget(self.rb_sido)
        layout.addWidget(self.rb_sigungu)
        layout.addWidget(self.rb_emd)

        card.setLayout(layout)
        return card

    def _create_notice(self):
        """Create notice for water supply statistics."""
        notice = QFrame()
        notice.setStyleSheet("""
            QFrame {
                background-color: #fef3c7;
                border: 1px solid #fcd34d;
                border-radius: 6px;
            }
        """)

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)

        # Info icon
        icon = QLabel("ℹ")
        icon.setStyleSheet("font-size: 13px; color: #92400e; border: none;")
        layout.addWidget(icon)

        # Notice text
        text = QLabel("상수도통계는 광역 및 기초 단위로만 제공됩니다")
        text.setStyleSheet("font-size: 13px; color: #92400e; border: none;")
        layout.addWidget(text)
        layout.addStretch()

        notice.setLayout(layout)
        return notice

    def _initialize_data(self):
        """Initialize combobox data."""
        self._load_sido()

    def _load_sido(self):
        """Load sido items."""
        self.cbx_sido.clear()
        self.cbx_sido.addItem("-- 전체 --", "")

        sido_list = [r for r in self.region_data if len(r["code"]) == 2]
        sido_list = sorted(sido_list, key=lambda x: x["name"])

        for sido in sido_list:
            self.cbx_sido.addItem(sido["name"], sido["code"])

    def _load_sigungu(self, sido_code):
        """Load sigungu items for selected sido."""
        self.cbx_sigungu.clear()
        self.cbx_sigungu.addItem("-- 전체 --", "")

        if not sido_code:
            return

        sigungu_list = [
            r for r in self.region_data
            if len(r["code"]) == 5 and r["code"].startswith(sido_code)
        ]
        sigungu_list = sorted(sigungu_list, key=lambda x: x["name"])

        for sigungu in sigungu_list:
            self.cbx_sigungu.addItem(sigungu["name"], sigungu["code"])

    def _load_emd(self, sigungu_code):
        """Load emd items for selected sigungu."""
        self.cbx_emd.clear()
        self.cbx_emd.addItem("-- 전체 --", "")

        if not sigungu_code:
            return

        emd_list = [
            r for r in self.region_data
            if len(r["code"]) == 8 and r["code"].startswith(sigungu_code)
        ]
        emd_list = sorted(emd_list, key=lambda x: x["name"])

        for emd in emd_list:
            self.cbx_emd.addItem(emd["name"], emd["code"])

    def _on_sido_changed(self, index):
        """Handle sido selection change."""
        self.cbx_sigungu.clear()
        self.cbx_emd.clear()

        sido_code = self.cbx_sido.currentData()
        if sido_code:
            self._load_sigungu(sido_code)

        self._emit_region_changed()

    def _on_sigungu_changed(self, index):
        """Handle sigungu selection change."""
        self.cbx_emd.clear()

        sigungu_code = self.cbx_sigungu.currentData()
        if sigungu_code:
            self._load_emd(sigungu_code)

        self._emit_region_changed()

    def _on_emd_changed(self, index):
        """Handle emd selection change."""
        self._emit_region_changed()

    def _on_level_changed(self, button):
        """Handle display level change."""
        self._emit_region_changed()

    def _emit_region_changed(self):
        """Emit region changed signal."""
        region_code = self.get_selected_region_code()
        display_level = self.get_display_level()
        self.region_changed.emit(region_code, display_level)

    def get_selected_region_code(self):
        """Get the most specific selected region code."""
        emd_code = self.cbx_emd.currentData()
        if emd_code:
            return emd_code

        sigungu_code = self.cbx_sigungu.currentData()
        if sigungu_code:
            return sigungu_code

        sido_code = self.cbx_sido.currentData()
        if sido_code:
            return sido_code

        return ""

    def get_selected_region_name(self):
        """Get the selected region name."""
        emd_code = self.cbx_emd.currentData()
        if emd_code:
            return self.cbx_emd.currentText()

        sigungu_code = self.cbx_sigungu.currentData()
        if sigungu_code:
            return self.cbx_sigungu.currentText()

        sido_code = self.cbx_sido.currentData()
        if sido_code:
            return self.cbx_sido.currentText()

        return "전체"

    def get_display_level(self):
        """Get selected display level."""
        return self.level_button_group.checkedId()
