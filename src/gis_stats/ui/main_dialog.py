"""
Main Dialog - Wizard-style UI with Stepper Navigation
"""

from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QPushButton,
    QProgressBar,
    QLabel,
    QFrame,
    QMessageBox,
    QSizePolicy,
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject

from .region_tab import RegionTab
from .statistics_tab import StatisticsTab
from .styling_tab import StylingTab
from ..core.db_connection import DBConnection
from ..core.statistics_loader import StatisticsLoader
from ..core.layer_joiner import LayerJoiner
from ..core.style_manager import StyleManager


# Global stylesheet for the dialog
DIALOG_STYLESHEET = """
* {
    font-family: 'Pretendard', 'Pretendard Variable', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
    font-weight: 500;
}
QDialog {
    background-color: #f9fafb;
}
QLabel {
    color: #374151;
    font-weight: 500;
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
QSpinBox, QDoubleSpinBox {
    border: 1px solid #d1d5db;
    border-radius: 4px;
    padding: 8px 12px;
    background-color: #f9fafb;
    font-size: 14px;
    color: #374151;
}
QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #9ca3af;
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
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
QScrollBar:horizontal {
    background-color: #f3f4f6;
    height: 10px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background-color: #9ca3af;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #6b7280;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}
"""


class StepperButton(QPushButton):
    """Stepper navigation button."""

    def __init__(self, text, step_index, parent=None):
        super().__init__(text, parent)
        self.step_index = step_index
        self._active = False
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self._update_style()

    def set_active(self, active):
        self._active = active
        self.setChecked(active)
        self._update_style()

    def _update_style(self):
        if self._active:
            self.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    border: 1px solid #d1d5db;
                    border-radius: 20px;
                    padding: 8px 20px;
                    font-size: 13px;
                    font-weight: bold;
                    color: #1f2937;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    padding: 8px 20px;
                    font-size: 13px;
                    color: #9ca3af;
                }
                QPushButton:hover {
                    color: #6b7280;
                }
            """)


class MainDialog(QDialog):
    """Main dialog with wizard-style tabbed interface."""

    def __init__(self, iface, parent=None):
        """Initialize the main dialog."""
        super().__init__(parent)
        self.iface = iface

        # Set window properties
        self.setWindowTitle("GIS Stats Viewer")
        self.setWindowFlags(Qt.Window)
        self.setMinimumSize(560, 750)
        self.resize(560, 750)
        self.setStyleSheet(DIALOG_STYLESHEET)

        # Initialize core components
        self.db = DBConnection()
        self.stats_loader = StatisticsLoader(self.db)
        self.layer_joiner = LayerJoiner()
        self.style_manager = StyleManager()

        # State
        self._current_step = 0
        self._current_layer = None
        self._loaded_statistics = {}

        # Setup UI
        self._setup_ui()
        self._connect_signals()
        self._update_step(0)

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Stepper navigation
        stepper = self._create_stepper()
        layout.addWidget(stepper)

        # Content area
        content_frame = QFrame()
        content_frame.setStyleSheet("background-color: #f9fafb;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(16, 16, 16, 16)

        self.stacked_widget = QStackedWidget()

        # Create tabs
        self.region_tab = RegionTab(self.db, self)
        self.statistics_tab = StatisticsTab(self.stats_loader, self)
        self.styling_tab = StylingTab(self.style_manager, self)

        self.stacked_widget.addWidget(self.region_tab)
        self.stacked_widget.addWidget(self.statistics_tab)
        self.stacked_widget.addWidget(self.styling_tab)

        content_layout.addWidget(self.stacked_widget)
        content_frame.setLayout(content_layout)
        layout.addWidget(content_frame, 1)

        # Progress bar (hidden by default)
        self.progress_frame = self._create_progress_frame()
        layout.addWidget(self.progress_frame)

        # Summary bar
        self.summary_bar = self._create_summary_bar()
        layout.addWidget(self.summary_bar)

        # Footer buttons
        footer = self._create_footer()
        layout.addWidget(footer)

        self.setLayout(layout)

    def _create_header(self):
        """Create header with title."""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: white;
                border-bottom: 1px solid #e5e7eb;
            }
        """)
        header.setFixedHeight(60)

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 0, 20, 0)

        # Title
        title = QLabel("GIS기반 통계조회")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1f2937;")
        layout.addWidget(title)
        layout.addStretch()

        header.setLayout(layout)
        return header

    def _create_stepper(self):
        """Create stepper navigation."""
        stepper = QFrame()
        stepper.setStyleSheet("""
            QFrame {
                background-color: white;
                border-bottom: 1px solid #e5e7eb;
            }
        """)
        stepper.setFixedHeight(50)

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(0)

        self.step_buttons = []

        steps = [
            ("지역 선택", 0),
            ("통계자료 선택", 1),
            ("색상 매핑", 2),
        ]

        layout.addStretch()
        for text, index in steps:
            btn = StepperButton(text, index)
            btn.clicked.connect(lambda checked, idx=index: self._on_step_clicked(idx))
            self.step_buttons.append(btn)
            layout.addWidget(btn)
        layout.addStretch()

        stepper.setLayout(layout)
        return stepper

    def _create_progress_frame(self):
        """Create progress indicator frame."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #fef3c7;
                border-top: 1px solid #fcd34d;
            }
        """)
        frame.setFixedHeight(50)
        frame.setVisible(False)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 8, 20, 8)

        self.lbl_status = QLabel("처리 중...")
        self.lbl_status.setStyleSheet("color: #92400e; font-size: 13px;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #fde68a;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #f59e0b;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        frame.setLayout(layout)
        return frame

    def _create_summary_bar(self):
        """Create summary bar."""
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background-color: white;
                border-top: 1px solid #e5e7eb;
            }
        """)
        bar.setFixedHeight(36)

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 0, 20, 0)

        self.lbl_region_summary = QLabel("* 지역 미선택")
        self.lbl_region_summary.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(self.lbl_region_summary)

        separator = QLabel("|")
        separator.setStyleSheet("color: #d1d5db;")
        layout.addWidget(separator)

        self.lbl_stats_summary = QLabel("* 통계 미선택")
        self.lbl_stats_summary.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(self.lbl_stats_summary)

        layout.addStretch()

        self.lbl_year_summary = QLabel("2024")
        self.lbl_year_summary.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(self.lbl_year_summary)

        bar.setLayout(layout)
        return bar

    def _create_footer(self):
        """Create footer with action buttons."""
        footer = QFrame()
        footer.setStyleSheet("""
            QFrame {
                background-color: white;
                border-top: 1px solid #e5e7eb;
            }
        """)
        footer.setFixedHeight(60)

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 10, 20, 10)

        # Previous button
        self.btn_prev = QPushButton("< 이전")
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #6b7280;
                font-size: 14px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                color: #374151;
            }
            QPushButton:disabled {
                color: #d1d5db;
            }
        """)
        self.btn_prev.clicked.connect(self._on_prev_clicked)
        layout.addWidget(self.btn_prev)

        layout.addStretch()

        # Main action button
        self.btn_action = QPushButton("다음 단계 >")
        self.btn_action.setCursor(Qt.PointingHandCursor)
        self.btn_action.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #9ca3af;
            }
        """)
        self.btn_action.clicked.connect(self._on_action_clicked)
        layout.addWidget(self.btn_action)

        # Close button
        self.btn_close = QPushButton("닫기")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                color: #6b7280;
                font-size: 14px;
                padding: 10px 16px;
            }
            QPushButton:hover {
                background-color: #f3f4f6;
                border-color: #9ca3af;
            }
        """)
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_close)

        footer.setLayout(layout)
        return footer

    def _connect_signals(self):
        """Connect signals between components."""
        # Database signals
        self.db.query_error.connect(self._on_error)

        # Statistics loader signals
        self.stats_loader.progress_changed.connect(self._update_progress)
        self.stats_loader.loading_finished.connect(self._on_statistics_loaded)
        self.stats_loader.error_occurred.connect(self._on_error)

        # Layer joiner signals
        self.layer_joiner.progress_changed.connect(self._update_progress)
        self.layer_joiner.join_finished.connect(self._on_join_finished)
        self.layer_joiner.error_occurred.connect(self._on_error)

        # Style manager signals
        self.style_manager.style_applied.connect(self._on_style_applied)
        self.style_manager.error_occurred.connect(self._on_error)

        # Region tab signals
        self.region_tab.region_changed.connect(self._on_region_changed)

        # Statistics tab signals
        self.statistics_tab.selection_changed.connect(self._update_summary)

        # Styling tab signals
        self.styling_tab.style_requested.connect(self._apply_style)

    def _update_step(self, step):
        """Update UI for current step."""
        self._current_step = step
        self.stacked_widget.setCurrentIndex(step)

        # Update stepper buttons
        for i, btn in enumerate(self.step_buttons):
            btn.set_active(i == step)

        # Update footer buttons
        self.btn_prev.setVisible(step > 0)

        if step == 0:
            self.btn_action.setText("다음 단계 >")
        elif step == 1:
            self.btn_action.setText("데이터 로드 >")
        else:
            self.btn_action.setText("색상 적용 >")

        self._update_summary()

    def _on_step_clicked(self, step):
        """Handle stepper button click."""
        self._update_step(step)

    def _on_prev_clicked(self):
        """Handle previous button click."""
        if self._current_step > 0:
            self._update_step(self._current_step - 1)

    def _on_action_clicked(self):
        """Handle main action button click."""
        if self._current_step == 0:
            # Next step
            self._update_step(1)
        elif self._current_step == 1:
            # Load data
            self._on_load_clicked()
        else:
            # Apply style
            self._on_apply_style_clicked()

    def _on_region_changed(self, region_code, display_level):
        """Handle region selection change."""
        self.statistics_tab.set_region_info(region_code, display_level)
        self._update_summary()

    def _update_summary(self):
        """Update summary bar."""
        # Region summary
        region_name = self.region_tab.get_selected_region_name()
        if region_name:
            self.lbl_region_summary.setText(f"* {region_name}")
        else:
            self.lbl_region_summary.setText("* 지역 미선택")

        # Statistics summary
        stats = self.statistics_tab.get_selected_statistics()
        total_cols = sum(len(cols) for cols in stats.values())
        if total_cols > 0:
            # Get first stat name
            first_stat = list(stats.keys())[0] if stats else ""
            stat_names = {"pop": "인구수", "hh": "가구수", "hu": "주택수"}
            first_name = stat_names.get(first_stat, "통계")
            if total_cols > 1:
                self.lbl_stats_summary.setText(f"* {first_name} 외 {total_cols - 1}종")
            else:
                self.lbl_stats_summary.setText(f"* {first_name}")
        else:
            self.lbl_stats_summary.setText("* 통계 미선택")

        # Year summary
        years = self.statistics_tab.get_selected_years()
        if years:
            if len(years) == 1:
                self.lbl_year_summary.setText(f"{years[0]}")
            else:
                self.lbl_year_summary.setText(f"{min(years)}~{max(years)}")

    def _on_load_clicked(self):
        """Handle load button click."""
        region_code = self.region_tab.get_selected_region_code()
        display_level = self.region_tab.get_display_level()

        # Truncate to display_level so that e.g. sigungu code "11135"
        # becomes sido code "11" when aggregating at sido level.
        region_code = region_code[:display_level]

        if not region_code:
            QMessageBox.warning(self, "지역 선택 필요", "지역을 먼저 선택해주세요.")
            self._update_step(0)
            return

        selected_stats = self.statistics_tab.get_selected_statistics()
        selected_years = self.statistics_tab.get_selected_years()

        if not selected_stats:
            QMessageBox.warning(self, "통계 선택 필요", "통계 항목을 선택해주세요.")
            return

        if not selected_years:
            QMessageBox.warning(self, "연도 선택 필요", "연도를 선택해주세요.")
            return

        self._show_progress()

        self._region_code = region_code
        self._display_level = display_level
        self._selected_years = selected_years

        self.stats_loader.load_statistics(
            region_code, display_level, selected_years, selected_stats
        )

    def _on_statistics_loaded(self, data):
        """Handle statistics data loaded."""
        self._loaded_statistics = data

        total_rows = 0
        for table_name, table_data in data.items():
            total_rows += len(table_data.get("data", []))

        if total_rows == 0:
            self._hide_progress()
            QMessageBox.warning(
                self,
                "데이터 없음",
                f"선택한 조건에 해당하는 통계 데이터가 없습니다.",
            )
            return

        self._update_progress(50, "경계 레이어 로딩 중...")

        region_name = self.region_tab.get_selected_region_name()
        min_year = min(self._selected_years)
        max_year = max(self._selected_years)
        year_str = f"{min_year}" if min_year == max_year else f"{min_year}~{max_year}"
        layer_name = f"통계_{region_name}_{year_str}"

        boundary_layer = self.db.get_boundaries_layer(
            self._region_code, self._display_level, layer_name
        )

        if not boundary_layer:
            self._hide_progress()
            QMessageBox.critical(self, "오류", "경계 레이어를 불러올 수 없습니다.")
            return

        self._update_progress(70, "통계 데이터 조인 중...")

        join_data = {}
        for year in self._selected_years:
            year_data = self.stats_loader.transform_data_for_join(data, year)
            for adm_cd, stats in year_data.items():
                if adm_cd not in join_data:
                    join_data[adm_cd] = {}
                join_data[adm_cd].update(stats)

        if not join_data:
            self._hide_progress()
            QMessageBox.warning(self, "조인 데이터 없음", "조인할 데이터가 없습니다.")
            return

        self.layer_joiner.join_statistics_to_boundaries(
            boundary_layer, join_data, "adm_cd", layer_name
        )

    def _on_join_finished(self, layer):
        """Handle join operation finished."""
        self._current_layer = layer

        self.layer_joiner.add_layer_to_project(layer)
        self._hide_progress()

        self.styling_tab.set_layer(layer)
        self._update_step(2)

        QMessageBox.information(
            self,
            "완료",
            f"통계 레이어가 생성되었습니다.\n피처 수: {layer.featureCount():,}개",
        )

    def _on_apply_style_clicked(self):
        """Handle apply style button click."""
        self.styling_tab._on_apply_clicked()

    def _apply_style(self, field_name, num_classes, color_ramp):
        """Apply style to current layer."""
        # Get layer from styling tab
        layer = self.styling_tab._layer

        if not layer:
            QMessageBox.warning(self, "레이어 없음", "레이어를 선택해주세요.")
            return

        self._current_layer = layer

        success = self.style_manager.apply_graduated_style(
            layer, field_name, num_classes, color_ramp, "quantile"
        )

        if success:
            self.style_manager.create_legend_labels(layer, field_name, "{:,.0f}")
            self.style_manager.apply_labels(
                layer, field_name, font_family="굴림", font_size=9, buffer_size=0.8
            )
            QMessageBox.information(self, "완료", "색상이 적용되었습니다.")

    def _on_style_applied(self):
        """Handle style applied successfully."""
        self.iface.mapCanvas().refresh()

    def _on_error(self, message):
        """Handle error from components."""
        self._hide_progress()
        QMessageBox.critical(self, "오류", message)

    def _update_progress(self, value, message):
        """Update progress bar and status."""
        self.progress_bar.setValue(value)
        self.lbl_status.setText(message)

    def _show_progress(self):
        """Show progress frame."""
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("준비 중...")
        self.btn_action.setEnabled(False)

    def _hide_progress(self):
        """Hide progress frame."""
        self.progress_frame.setVisible(False)
        self.btn_action.setEnabled(True)

    def closeEvent(self, event):
        """Handle dialog close event."""
        self.db.close()
        super().closeEvent(event)
