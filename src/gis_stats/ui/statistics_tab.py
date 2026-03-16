"""
Statistics Selection Tab - Card-based UI with Chip Buttons
"""

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QFrame,
    QPushButton,
    QSizePolicy,
    QScrollArea,
    QLineEdit,
)
from qgis.PyQt.QtCore import Qt, pyqtSignal


class ChipButton(QPushButton):
    """Chip-style toggle button for statistics selection."""

    def __init__(self, text, data_key, parent=None):
        super().__init__(text, parent)
        self.data_key = data_key
        self._selected = True
        self.setCheckable(True)
        self.setChecked(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setMinimumHeight(34)
        self._update_style()
        self.toggled.connect(self._on_toggled)

    def _on_toggled(self, checked):
        self._selected = checked
        self._update_style()

    def _update_style(self):
        if self._selected:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #1f2937;
                    border: none;
                    border-radius: 16px;
                    padding: 6px 14px;
                    font-size: 13px;
                    font-weight: 700;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #374151;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    border: 1px solid #d1d5db;
                    border-radius: 16px;
                    padding: 6px 14px;
                    font-size: 13px;
                    font-weight: 700;
                    color: #6b7280;
                }
                QPushButton:hover {
                    background-color: #f3f4f6;
                    border-color: #9ca3af;
                }
            """)

    def is_selected(self):
        return self._selected


class StatCategoryCard(QFrame):
    """Card widget for a statistics category."""

    selection_changed = pyqtSignal()

    def __init__(self, stat_key, stat_info, parent=None):
        super().__init__(parent)
        self.stat_key = stat_key
        self.stat_info = stat_info
        self.chip_buttons = []

        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(16, 12, 16, 12)

        # Header row with title, badge, and toggle
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Title
        title = QLabel(self.stat_info["display_name"])
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #374151; border: none;")
        header_layout.addWidget(title)

        # Badge
        count = len(self.stat_info["columns"])
        self.badge = QLabel(str(count))
        self.badge.setStyleSheet("""
            background-color: #e5e7eb;
            color: #374151;
            font-size: 11px;
            font-weight: bold;
            padding: 2px 8px;
            border-radius: 10px;
            border: none;
        """)
        self.badge.setFixedHeight(20)
        header_layout.addWidget(self.badge)

        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Chips container
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(6)

        for col_name, col_display in self.stat_info["columns"].items():
            chip = ChipButton(col_display, col_name)
            chip.toggled.connect(self._on_chip_toggled)
            self.chip_buttons.append(chip)
            chips_layout.addWidget(chip)

        chips_layout.addStretch()
        layout.addLayout(chips_layout)

        self.setLayout(layout)

    def _on_chip_toggled(self, checked):
        """Handle individual chip toggle."""
        self._update_badge()
        self.selection_changed.emit()

    def _update_badge(self):
        """Update badge count."""
        selected = sum(1 for chip in self.chip_buttons if chip.is_selected())
        self.badge.setText(str(selected))

    def get_selected_columns(self):
        """Get list of selected column keys."""
        return [chip.data_key for chip in self.chip_buttons if chip.is_selected()]

    def set_unavailable(self, is_unavailable, reason=""):
        """Set card as unavailable with reason.

        :param is_unavailable: True to disable, False to enable
        :param reason: Reason message to display
        """
        if is_unavailable:
            # Disable all chips
            for chip in self.chip_buttons:
                chip.setEnabled(False)
                chip.setChecked(False)

            # Add/update warning message
            if not hasattr(self, 'warning_label'):
                self.warning_label = QLabel()
                self.warning_label.setWordWrap(True)
                self.warning_label.setStyleSheet("""
                    background-color: #fef3c7;
                    border: 1px solid #fcd34d;
                    border-radius: 4px;
                    padding: 6px 10px;
                    font-size: 11px;
                    color: #92400e;
                """)
                self.layout().addWidget(self.warning_label)

            self.warning_label.setText(f"⚠ {reason}")
            self.warning_label.setVisible(True)

            # Gray out the card
            self.setStyleSheet("""
                QFrame {
                    background-color: #f9fafb;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    opacity: 0.6;
                }
            """)
        else:
            # Enable all chips
            for chip in self.chip_buttons:
                chip.setEnabled(True)
                chip.setChecked(True)

            # Hide warning
            if hasattr(self, 'warning_label'):
                self.warning_label.setVisible(False)

            # Restore normal style
            self.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                }
            """)

        self._update_badge()
        self.selection_changed.emit()


class StatisticsTab(QWidget):
    """Tab for statistics and year selection."""

    # Signals
    selection_changed = pyqtSignal()

    # Year range
    MIN_YEAR = 2015
    MAX_YEAR = 2024

    def __init__(self, stats_loader, parent=None):
        """Initialize the statistics tab."""
        super().__init__(parent)
        self.stats_loader = stats_loader

        # State
        self._region_code = ""
        self._display_level = 8

        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # Year selection card
        year_card = self._create_year_card()
        layout.addWidget(year_card)

        # Statistics category label
        stats_label = QLabel("통계 항목 선택")
        stats_label.setStyleSheet("font-size: 14px; color: #6b7280; margin-top: 4px;")
        layout.addWidget(stats_label)

        # Search box for filtering statistics
        search_layout = QHBoxLayout()
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("font-size: 14px; border: none;")
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("통계 항목 검색...")
        self.txt_search.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.txt_search)
        layout.addLayout(search_layout)

        # Scroll area for statistics cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        # Container widget for cards
        cards_container = QWidget()
        cards_container.setStyleSheet("background: transparent;")
        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(12)
        cards_layout.setContentsMargins(0, 0, 0, 0)

        # Statistics cards
        self.stat_cards = {}
        available_stats = self.stats_loader.get_available_statistics()

        for stat_key, stat_info in available_stats.items():
            card = StatCategoryCard(stat_key, stat_info)
            card.selection_changed.connect(self._on_card_selection_changed)
            self.stat_cards[stat_key] = card
            cards_layout.addWidget(card)

        cards_layout.addStretch()
        cards_container.setLayout(cards_layout)
        scroll.setWidget(cards_container)
        layout.addWidget(scroll, 1)  # Add with stretch factor
        self.setLayout(layout)

    def _create_year_card(self):
        """Create year selection card."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """)

        layout = QHBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)

        # Title
        title = QLabel("연도 설정")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #374151; border: none;")
        layout.addWidget(title)

        layout.addStretch()

        # Year badge
        self.year_badge = QLabel("2024년 (1개년)")
        self.year_badge.setStyleSheet("""
            background-color: #dbeafe;
            color: #1e40af;
            font-size: 11px;
            padding: 4px 10px;
            border-radius: 12px;
            border: none;
        """)
        layout.addWidget(self.year_badge)

        card.setLayout(layout)

        # Second row for year inputs
        card_layout = QVBoxLayout()
        card_layout.setSpacing(0)
        card_layout.setContentsMargins(0, 0, 0, 0)

        # Header part
        header_widget = QWidget()
        header_widget.setLayout(layout)
        card_layout.addWidget(header_widget)

        # Input row
        input_frame = QFrame()
        input_frame.setStyleSheet("border: none; background: transparent;")
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(16, 0, 16, 12)

        self.cbx_start_year = QComboBox()
        for year in range(self.MIN_YEAR, self.MAX_YEAR + 1):
            self.cbx_start_year.addItem(str(year), year)
        self.cbx_start_year.setCurrentIndex(self.cbx_start_year.count() - 1)  # Select last year
        self.cbx_start_year.currentIndexChanged.connect(self._on_year_changed)

        tilde = QLabel("~")
        tilde.setStyleSheet("color: #9ca3af; font-size: 14px; border: none;")
        tilde.setAlignment(Qt.AlignCenter)
        tilde.setFixedWidth(30)

        self.cbx_end_year = QComboBox()
        for year in range(self.MIN_YEAR, self.MAX_YEAR + 1):
            self.cbx_end_year.addItem(str(year), year)
        self.cbx_end_year.setCurrentIndex(self.cbx_end_year.count() - 1)  # Select last year
        self.cbx_end_year.currentIndexChanged.connect(self._on_year_changed)

        input_layout.addWidget(self.cbx_start_year)
        input_layout.addWidget(tilde)
        input_layout.addWidget(self.cbx_end_year)
        input_layout.addStretch()

        input_frame.setLayout(input_layout)
        card_layout.addWidget(input_frame)

        # Create actual card widget
        actual_card = QFrame()
        actual_card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """)
        actual_card.setLayout(card_layout)

        return actual_card

    def _on_year_changed(self, index):
        """Handle year selection change."""
        # Ensure start <= end
        start_year = self.cbx_start_year.currentData()
        end_year = self.cbx_end_year.currentData()

        if start_year and end_year and start_year > end_year:
            if self.sender() == self.cbx_start_year:
                # Find index for start year in end year combobox
                idx = self.cbx_end_year.findData(start_year)
                if idx >= 0:
                    self.cbx_end_year.setCurrentIndex(idx)
            else:
                # Find index for end year in start year combobox
                idx = self.cbx_start_year.findData(end_year)
                if idx >= 0:
                    self.cbx_start_year.setCurrentIndex(idx)

        self._update_year_badge()
        self.selection_changed.emit()

    def _update_year_badge(self):
        """Update year badge text."""
        years = self.get_selected_years()
        if len(years) == 1:
            self.year_badge.setText(f"{years[0]}년 (1개년)")
        else:
            self.year_badge.setText(f"{min(years)}~{max(years)}년 ({len(years)}개년)")

    def _on_card_selection_changed(self):
        """Handle card selection change."""
        self.selection_changed.emit()

    def _on_search_changed(self, text):
        """Filter statistics cards based on search text."""
        search_text = text.lower().strip()

        for stat_key, card in self.stat_cards.items():
            stat_name = card.stat_info["display_name"].lower()

            # Also check column names
            column_names = " ".join(card.stat_info["columns"].values()).lower()

            if search_text == "" or search_text in stat_name or search_text in column_names:
                card.setVisible(True)
            else:
                card.setVisible(False)

    def set_region_info(self, region_code, display_level):
        """Set region information and update availability of statistics cards."""
        self._region_code = region_code
        self._display_level = display_level

        # Water supply statistics are only available for 시도(2) and 시군구(5) levels
        if "water_supply" in self.stat_cards:
            water_card = self.stat_cards["water_supply"]
            if display_level == 8:  # 읍면동 level
                water_card.set_unavailable(True, "읍면동 단위에서는 데이터가 제공되지 않습니다")
            else:
                water_card.set_unavailable(False)

    def get_selected_years(self):
        """Get list of selected years."""
        start = self.cbx_start_year.currentData()
        end = self.cbx_end_year.currentData()
        if start and end:
            return list(range(start, end + 1))
        return []

    def get_selected_statistics(self):
        """Get selected statistics configuration."""
        result = {}

        for stat_key, card in self.stat_cards.items():
            selected_columns = card.get_selected_columns()
            if selected_columns:
                result[stat_key] = selected_columns

        return result
