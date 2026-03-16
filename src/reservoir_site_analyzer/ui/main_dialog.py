# -*- coding: utf-8 -*-
"""
Main Dialog - Wizard-style UI with 4-Step Stepper Navigation
배수지 적합 부지 분석 메인 다이얼로그 (4단계 워크플로우)
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
    QSizePolicy,
)
from qgis.PyQt.QtCore import Qt, pyqtSignal

from .region_tab import RegionTab
from .terrain_tab import TerrainTab
from .owner_tab import OwnerTab
from .output_tab import OutputTab


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
                    padding: 8px 16px;
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
                    padding: 8px 16px;
                    font-size: 13px;
                    color: #9ca3af;
                }
                QPushButton:hover {
                    color: #6b7280;
                }
            """)


class MainDialog(QDialog):
    """Main dialog with wizard-style 4-step tabbed interface."""

    # Signals for step completion
    step1_completed = pyqtSignal(str)  # region_code
    step2_completed = pyqtSignal(int, int, int)  # min_elevation, max_elevation, max_slope
    step3_completed = pyqtSignal(list)  # owner_values
    analysis_requested = pyqtSignal(dict)  # Emits analysis parameters

    def __init__(self, parent=None):
        """Initialize the main dialog."""
        super().__init__(parent)

        # Set window properties
        self.setWindowTitle("배수지 적합 부지 분석")
        self.setWindowFlags(Qt.Window)
        self.setMinimumSize(520, 750)
        self.resize(520, 800)
        self.setStyleSheet(DIALOG_STYLESHEET)

        # State
        self._current_step = 0

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

        # Stepper navigation (4 steps)
        stepper = self._create_stepper()
        layout.addWidget(stepper)

        # Content area
        content_frame = QFrame()
        content_frame.setStyleSheet("background-color: #f9fafb;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(16, 16, 16, 16)

        self.stacked_widget = QStackedWidget()

        # Create tabs (4 tabs)
        self.region_tab = RegionTab(self)
        self.terrain_tab = TerrainTab(self)
        self.owner_tab = OwnerTab(self)
        self.output_tab = OutputTab(self)

        self.stacked_widget.addWidget(self.region_tab)      # Index 0
        self.stacked_widget.addWidget(self.terrain_tab)     # Index 1
        self.stacked_widget.addWidget(self.owner_tab)       # Index 2
        self.stacked_widget.addWidget(self.output_tab)      # Index 3

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
        title = QLabel("배수지 적합 부지 분석")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1f2937;")
        layout.addWidget(title)
        layout.addStretch()

        header.setLayout(layout)
        return header

    def _create_stepper(self):
        """Create 4-step stepper navigation."""
        stepper = QFrame()
        stepper.setStyleSheet("""
            QFrame {
                background-color: white;
                border-bottom: 1px solid #e5e7eb;
            }
        """)
        stepper.setFixedHeight(50)

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(0)

        self.step_buttons = []

        # 4 steps
        steps = [
            ("1. 지역 선택", 0),
            ("2. 지형 조건", 1),
            ("3. 소유주체", 2),
            ("4. 출력 설정", 3),
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

        self.lbl_region_summary = QLabel("지역: 미선택")
        self.lbl_region_summary.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(self.lbl_region_summary)

        separator1 = QLabel("|")
        separator1.setStyleSheet("color: #d1d5db;")
        layout.addWidget(separator1)

        self.lbl_terrain_summary = QLabel("고도 60~200m / 경사 26도")
        self.lbl_terrain_summary.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(self.lbl_terrain_summary)

        separator2 = QLabel("|")
        separator2.setStyleSheet("color: #d1d5db;")
        layout.addWidget(separator2)

        self.lbl_owner_summary = QLabel("소유주체: 전체")
        self.lbl_owner_summary.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(self.lbl_owner_summary)

        layout.addStretch()

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
        self.btn_close.clicked.connect(self.reject)
        layout.addWidget(self.btn_close)

        footer.setLayout(layout)
        return footer

    def _connect_signals(self):
        """Connect signals between components."""
        # Region tab signals
        self.region_tab.region_changed.connect(self._on_region_changed)

        # Terrain tab signals
        self.terrain_tab.terrain_changed.connect(self._on_terrain_changed)

        # Owner tab signals
        self.owner_tab.owner_changed.connect(self._on_owner_changed)

    def _update_step(self, step):
        """Update UI for current step."""
        self._current_step = step
        self.stacked_widget.setCurrentIndex(step)

        # Update stepper buttons
        for i, btn in enumerate(self.step_buttons):
            btn.set_active(i == step)

        # Update footer buttons
        self.btn_prev.setVisible(step > 0)

        # Update action button text based on step
        if step == 0:
            self.btn_action.setText("다음 단계 >")
        elif step == 1:
            self.btn_action.setText("다음 단계 >")
        elif step == 2:
            self.btn_action.setText("다음 단계 >")
        else:  # step == 3
            self.btn_action.setText("분석 실행")

        self._update_summary()

        # Update output tab summary when reaching step 3
        if step == 3:
            self._update_output_summary()

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
            # Step 1 완료 - 지역 선택
            region_code = self.region_tab.get_selected_region_code()
            self.step1_completed.emit(region_code)
            self._update_step(1)
        elif self._current_step == 1:
            # Step 2 완료 - 지형 조건
            min_elevation = self.terrain_tab.get_min_elevation()
            max_elevation = self.terrain_tab.get_max_elevation()
            slope = self.terrain_tab.get_max_slope()
            self.step2_completed.emit(min_elevation, max_elevation, slope)
            self._update_step(2)
        elif self._current_step == 2:
            # Step 3 완료 - 소유주체 조건
            owner_values = self.owner_tab.get_owner_values()
            self.step3_completed.emit(owner_values)
            self._update_step(3)
        else:  # step == 3
            # Step 4 - 분석 실행
            self._run_analysis()

    def _on_region_changed(self):
        """Handle region selection change."""
        self._update_summary()

    def _on_terrain_changed(self):
        """Handle terrain settings change."""
        self._update_summary()

    def _on_owner_changed(self):
        """Handle owner selection change."""
        self._update_summary()

    def _update_summary(self):
        """Update summary bar."""
        # Region summary
        region_name = self.region_tab.get_selected_region_name()
        if region_name and region_name != "전체":
            self.lbl_region_summary.setText(f"지역: {region_name}")
        else:
            self.lbl_region_summary.setText("지역: 미선택")

        # Terrain summary
        min_elev = self.terrain_tab.get_min_elevation()
        max_elev = self.terrain_tab.get_max_elevation()
        slope = self.terrain_tab.get_max_slope()
        self.lbl_terrain_summary.setText(f"고도 {min_elev}~{max_elev}m / 경사 {slope}도")

        # Owner summary
        owner_label = self.owner_tab.get_owner_label()
        self.lbl_owner_summary.setText(f"소유주체: {owner_label}")

    def _update_output_summary(self):
        """Update output tab summary with current selections."""
        region_name = self.region_tab.get_selected_region_name()
        min_elevation = self.terrain_tab.get_min_elevation()
        max_elevation = self.terrain_tab.get_max_elevation()
        slope = self.terrain_tab.get_max_slope()
        owner_label = self.owner_tab.get_owner_label()

        self.output_tab.update_summary(
            region_name=region_name,
            elevation=min_elevation,
            slope=slope,
            owner_label=owner_label
        )

    def _run_analysis(self):
        """Run the analysis."""
        params = self.get_analysis_params()
        self.analysis_requested.emit(params)

    def get_analysis_params(self):
        """Get all analysis parameters."""
        return {
            'region_code': self.region_tab.get_selected_region_code(),
            'region_name': self.region_tab.get_selected_region_name(),
            'min_elevation': self.terrain_tab.get_min_elevation(),
            'max_elevation': self.terrain_tab.get_max_elevation(),
            'max_slope': self.terrain_tab.get_max_slope(),
            'owner_values': self.owner_tab.get_owner_values(),
            'owner_label': self.owner_tab.get_owner_label(),
            'output_name': self.output_tab.get_output_name(),
            # Layer selections from output tab (intermediate results)
            'selected_boundary_layer': self.output_tab.get_selected_boundary_layer(),
            'selected_terrain_layer': self.output_tab.get_selected_terrain_layer(),
            'selected_owner_layer': self.output_tab.get_selected_owner_layer(),
            # Source layer selections from step tabs
            'selected_dem_layer': self.terrain_tab.get_selected_dem_layer(),
            'selected_owner_boundary_layer': self.owner_tab.get_selected_boundary_layer(),
        }

    def update_progress(self, value, message):
        """Update progress bar and status."""
        self.progress_bar.setValue(value)
        self.lbl_status.setText(message)

    def show_progress(self):
        """Show progress frame."""
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("준비 중...")
        self.btn_action.setEnabled(False)

    def hide_progress(self):
        """Hide progress frame."""
        self.progress_frame.setVisible(False)
        self.btn_action.setEnabled(True)

    def set_region_data(self, sido_list, sigungu_dict, eupmyeondong_dict):
        """Set region data for the region tab."""
        self.region_tab.set_region_data(sido_list, sigungu_dict, eupmyeondong_dict)

    def set_owner_list(self, owner_list):
        """Set owner list for the owner tab."""
        self.owner_tab.set_owner_list(owner_list)
