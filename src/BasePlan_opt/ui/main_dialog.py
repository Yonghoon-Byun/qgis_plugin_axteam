# -*- coding: utf-8 -*-
"""
BasePlan - Main Dialog v6
토목 기본도면 작성 플러그인 메인 다이얼로그
Modern card-based UI design
"""

import os
import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
        QLabel, QFrame, QWidget, QLineEdit, QSizePolicy,
        QProgressBar, QScrollArea, QGridLayout, QCheckBox
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QFont, QIcon
except ImportError:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
        QLabel, QFrame, QWidget, QLineEdit, QSizePolicy,
        QProgressBar, QScrollArea, QGridLayout, QCheckBox
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QFont, QIcon


# Global stylesheet - Modern design
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
    combobox-popup: 0;
}
QComboBox:hover {
    border-color: #9ca3af;
    background-color: white;
}
QComboBox:disabled {
    background-color: #f3f4f6;
    color: #9ca3af;
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
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
QProgressBar {
    background-color: #fde68a;
    border: none;
    border-radius: 3px;
}
QProgressBar::chunk {
    background-color: #f59e0b;
    border-radius: 3px;
}
"""


class WMSPlanDialog(QDialog):
    """Main dialog for BasePlan plugin - Modern card-based UI"""

    # Signals
    load_area_a_clicked = pyqtSignal()
    horizontal_clicked = pyqtSignal()
    vertical_clicked = pyqtSignal()
    reset_box_clicked = pyqtSignal()
    lock_box_clicked = pyqtSignal(bool)
    load_area_b_clicked = pyqtSignal()
    finalize_clicked = pyqtSignal()
    export_pdf_clicked = pyqtSignal()
    export_image_clicked = pyqtSignal()
    save_project_clicked = pyqtSignal()
    open_layout_clicked = pyqtSignal()
    region_changed = pyqtSignal(str, str)
    add_north_clicked = pyqtSignal()
    add_scale_clicked = pyqtSignal()
    add_outer_clicked = pyqtSignal()
    full_reset_clicked = pyqtSignal()

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.admin_data = {}
        self.hierarchy = {}

        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle("BasePlan - 기본도면 작성")

        # 아이콘 설정
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.is_box_locked = False  # 도면 잠금 상태

        self.setMinimumSize(420, 750)
        self.resize(440, 800)
        self.setStyleSheet(DIALOG_STYLESHEET)

        self._setup_ui()
        self.load_admin_data()

    def _setup_ui(self):
        """Setup main UI layout and components"""
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        content = QFrame()
        content.setStyleSheet("background-color: #f9fafb; border: none;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        # Region selection card
        region_card = self._create_region_card()
        content_layout.addWidget(region_card)

        # Workflow card
        workflow_card = self._create_workflow_card()
        content_layout.addWidget(workflow_card)

        # Export card
        export_card = self._create_export_card()
        content_layout.addWidget(export_card)

        # Reset button
        self.btn_full_reset = self._create_reset_button()
        content_layout.addWidget(self.btn_full_reset)

        content_layout.addStretch()
        content.setLayout(content_layout)
        scroll.setWidget(content)

        layout.addWidget(scroll, 1)

        # Progress frame (hidden by default)
        self.progress_frame = self._create_progress_frame()
        layout.addWidget(self.progress_frame)

        # Footer with status
        footer = self._create_footer()
        layout.addWidget(footer)

        self.setLayout(layout)

    def _create_header(self):
        """Create header with title"""
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
        title = QLabel("BasePlan")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1f2937; border: none;")
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("기본도면 작성")
        subtitle.setStyleSheet("font-size: 13px; color: #6b7280; border: none; margin-left: 8px;")
        layout.addWidget(subtitle)

        layout.addStretch()

        # CRS badge (minimal, fixed size)
        self.crs_label = QLabel("EPSG:5179")
        self.crs_label.setStyleSheet("""
            font-size: 10px;
            color: #1e40af;
            background-color: #dbeafe;
            border: none;
            border-radius: 2px;
            padding: 1px 3px;
        """)
        self.crs_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.crs_label)

        header.setLayout(layout)
        return header

    def _create_region_card(self):
        """Create region selection card"""
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
        header = QLabel("행정구역 선택")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #374151; border: none;")
        layout.addWidget(header)

        # Description
        desc = QLabel("대상영역을 로드할 행정구역을 선택하세요")
        desc.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Region combos in grid
        grid = QGridLayout()
        grid.setSpacing(10)

        # Sido
        sido_label = QLabel("시도")
        sido_label.setFixedWidth(50)
        sido_label.setStyleSheet("color: #6b7280; font-size: 14px; border: none;")
        self.sido_combo = QComboBox()
        self.sido_combo.addItem("-- 선택하세요 --", "")
        self.sido_combo.setMaxVisibleItems(20)
        self.sido_combo.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.sido_combo.currentIndexChanged.connect(self._on_sido_changed)
        grid.addWidget(sido_label, 0, 0)
        grid.addWidget(self.sido_combo, 0, 1)

        # Sigungu
        sigungu_label = QLabel("시군구")
        sigungu_label.setFixedWidth(50)
        sigungu_label.setStyleSheet("color: #6b7280; font-size: 14px; border: none;")
        self.sigungu_combo = QComboBox()
        self.sigungu_combo.addItem("-- 선택하세요 --", "")
        self.sigungu_combo.setEnabled(False)
        self.sigungu_combo.setMaxVisibleItems(20)
        self.sigungu_combo.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.sigungu_combo.currentIndexChanged.connect(self._on_sigungu_changed)
        grid.addWidget(sigungu_label, 1, 0)
        grid.addWidget(self.sigungu_combo, 1, 1)

        # Emd
        emd_label = QLabel("읍면동")
        emd_label.setFixedWidth(50)
        emd_label.setStyleSheet("color: #6b7280; font-size: 14px; border: none;")
        self.emd_combo = QComboBox()
        self.emd_combo.addItem("-- 선택하세요 --", "")
        self.emd_combo.setEnabled(False)
        self.emd_combo.setMaxVisibleItems(20)
        self.emd_combo.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.emd_combo.currentIndexChanged.connect(self._on_emd_changed)
        grid.addWidget(emd_label, 2, 0)
        grid.addWidget(self.emd_combo, 2, 1)

        layout.addLayout(grid)

        # Info notice
        notice = self._create_info_notice()
        layout.addWidget(notice)

        card.setLayout(layout)
        return card

    def _create_info_notice(self):
        """Create info notice"""
        notice = QFrame()
        notice.setStyleSheet("""
            QFrame {
                background-color: #dbeafe;
                border: 1px solid #93c5fd;
                border-radius: 6px;
            }
        """)

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)

        icon = QLabel("i")
        icon.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            color: #1e40af;
            border: none;
            background-color: #93c5fd;
            border-radius: 8px;
            padding: 2px 6px;
        """)
        layout.addWidget(icon)

        text = QLabel("세부 지역을 선택할수록 로딩이 빨라집니다")
        text.setStyleSheet("font-size: 13px; color: #1e40af; border: none;")
        layout.addWidget(text)
        layout.addStretch()

        notice.setLayout(layout)
        return notice

    def _create_workflow_card(self):
        """Create workflow card"""
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
        header = QLabel("작업 순서")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #374151; border: none;")
        layout.addWidget(header)

        # Step 1: Load Area A
        step1_layout = QVBoxLayout()
        step1_layout.setSpacing(6)

        step1_label = QLabel("1. 대상영역 로드")
        step1_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #374151; border: none;")
        step1_layout.addWidget(step1_label)

        self.btn_load_area_a = self._create_primary_button("대상영역 로드")
        self.btn_load_area_a.clicked.connect(self.load_area_a_clicked.emit)
        step1_layout.addWidget(self.btn_load_area_a)

        layout.addLayout(step1_layout)

        # Divider
        layout.addWidget(self._create_divider())

        # Step 2: Box settings
        step2_layout = QVBoxLayout()
        step2_layout.setSpacing(6)

        step2_label = QLabel("2. 도면범위 설정")
        step2_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #374151; border: none;")
        step2_layout.addWidget(step2_label)

        box_btn_layout = QHBoxLayout()
        box_btn_layout.setSpacing(8)

        self.btn_horizontal = self._create_secondary_button("가로도면")
        self.btn_horizontal.setEnabled(False)
        self.btn_horizontal.clicked.connect(self.horizontal_clicked.emit)
        self.btn_horizontal.setToolTip("가로 방향 도면 (Landscape)")
        box_btn_layout.addWidget(self.btn_horizontal)

        self.btn_vertical = self._create_secondary_button("세로도면")
        self.btn_vertical.setEnabled(False)
        self.btn_vertical.clicked.connect(self.vertical_clicked.emit)
        self.btn_vertical.setToolTip("세로 방향 도면 (Portrait)")
        box_btn_layout.addWidget(self.btn_vertical)

        self.btn_reset_box = self._create_secondary_button("초기화")
        self.btn_reset_box.setEnabled(False)
        self.btn_reset_box.clicked.connect(self.reset_box_clicked.emit)
        self.btn_reset_box.setToolTip("도면 범위를 삭제하고 다시 설정")
        box_btn_layout.addWidget(self.btn_reset_box)

        step2_layout.addLayout(box_btn_layout)

        # 잠금 버튼
        self.btn_lock_box = self._create_lock_button()
        self.btn_lock_box.setEnabled(False)
        self.btn_lock_box.clicked.connect(self._on_lock_box_clicked)
        step2_layout.addWidget(self.btn_lock_box)

        layout.addLayout(step2_layout)

        # Divider
        layout.addWidget(self._create_divider())

        # Step 3: Load Area B
        step3_layout = QVBoxLayout()
        step3_layout.setSpacing(6)

        step3_label = QLabel("3. 도면영역 로드")
        step3_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #374151; border: none;")
        step3_layout.addWidget(step3_label)

        self.btn_load_area_b = self._create_primary_button("도면영역 로드")
        self.btn_load_area_b.setEnabled(False)
        self.btn_load_area_b.clicked.connect(self.load_area_b_clicked.emit)
        step3_layout.addWidget(self.btn_load_area_b)

        layout.addLayout(step3_layout)

        # Divider
        layout.addWidget(self._create_divider())

        # Overlay elements
        overlay_layout = QVBoxLayout()
        overlay_layout.setSpacing(6)

        overlay_label = QLabel("도면 요소")
        overlay_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #374151; border: none;")
        overlay_layout.addWidget(overlay_label)

        # v9.2: 방위/축척은 내보내기 시 자동 추가됨 (안내 문구)
        overlay_info = QLabel("※ 방위표/축척바는 PDF/이미지 내보내기 시 자동 추가됩니다")
        overlay_info.setStyleSheet("font-size: 11px; color: #6b7280; border: none; padding: 4px 0;")
        overlay_layout.addWidget(overlay_info)

        overlay_btn_layout = QHBoxLayout()
        overlay_btn_layout.setSpacing(8)

        # v9.2: 방위/축척 버튼 숨김 (내보내기 전용)
        self.btn_add_north = self._create_chip_button("방위")
        self.btn_add_north.setEnabled(False)
        self.btn_add_north.clicked.connect(self.add_north_clicked.emit)
        self.btn_add_north.setToolTip("방위표 추가 (드래그 이동, Delete 삭제)")
        self.btn_add_north.setVisible(False)  # 숨김
        overlay_btn_layout.addWidget(self.btn_add_north)

        self.btn_add_scale = self._create_chip_button("축척")
        self.btn_add_scale.setEnabled(False)
        self.btn_add_scale.clicked.connect(self.add_scale_clicked.emit)
        self.btn_add_scale.setToolTip("축척바 추가 (드래그 이동, Delete 삭제)")
        self.btn_add_scale.setVisible(False)  # 숨김
        overlay_btn_layout.addWidget(self.btn_add_scale)

        self.btn_add_outer = self._create_chip_button("경계선")
        self.btn_add_outer.setEnabled(False)
        self.btn_add_outer.clicked.connect(self.add_outer_clicked.emit)
        self.btn_add_outer.setToolTip("행정구역 경계선 그라데이션")
        overlay_btn_layout.addWidget(self.btn_add_outer)

        overlay_btn_layout.addStretch()
        overlay_layout.addLayout(overlay_btn_layout)
        layout.addLayout(overlay_layout)

        # Divider
        layout.addWidget(self._create_divider())

        # Step 4: Finalize
        step4_layout = QVBoxLayout()
        step4_layout.setSpacing(6)

        step4_label = QLabel("4. 작성완료")
        step4_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #374151; border: none;")
        step4_layout.addWidget(step4_label)

        self.btn_finalize = self._create_action_button("작성완료")
        self.btn_finalize.setEnabled(False)
        self.btn_finalize.clicked.connect(self.finalize_clicked.emit)
        step4_layout.addWidget(self.btn_finalize)

        layout.addLayout(step4_layout)

        card.setLayout(layout)
        return card

    def _create_export_card(self):
        """Create export card"""
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
        header = QLabel("내보내기")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #374151; border: none;")
        layout.addWidget(header)

        # Export buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_export_pdf = self._create_secondary_button("PDF")
        self.btn_export_pdf.setEnabled(False)
        self.btn_export_pdf.clicked.connect(self.export_pdf_clicked.emit)
        btn_layout.addWidget(self.btn_export_pdf)

        self.btn_export_image = self._create_secondary_button("이미지")
        self.btn_export_image.setEnabled(False)
        self.btn_export_image.clicked.connect(self.export_image_clicked.emit)
        btn_layout.addWidget(self.btn_export_image)

        self.btn_save_project = self._create_secondary_button("프로젝트 저장")
        self.btn_save_project.setEnabled(False)
        self.btn_save_project.clicked.connect(self.save_project_clicked.emit)
        btn_layout.addWidget(self.btn_save_project)

        layout.addLayout(btn_layout)

        # 조판으로 이동 버튼 (전체 너비)
        self.btn_open_layout = self._create_layout_button()
        self.btn_open_layout.setEnabled(False)
        self.btn_open_layout.clicked.connect(self.open_layout_clicked.emit)
        layout.addWidget(self.btn_open_layout)

        card.setLayout(layout)
        return card

    def _create_progress_frame(self):
        """Create progress indicator frame"""
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

        self.progress_status_label = QLabel("처리 중...")
        self.progress_status_label.setStyleSheet("color: #92400e; font-size: 13px; border: none;")
        layout.addWidget(self.progress_status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        frame.setLayout(layout)
        return frame

    def _create_footer(self):
        """Create footer with status"""
        footer = QFrame()
        footer.setStyleSheet("""
            QFrame {
                background-color: white;
                border-top: 1px solid #e5e7eb;
            }
        """)
        footer.setFixedHeight(50)

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 10, 20, 10)

        # Status label
        self.status_label = QLabel("준비")
        self.status_label.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        footer.setLayout(layout)
        return footer

    def _create_reset_button(self):
        """Create full reset button"""
        btn = QPushButton("전체 초기화")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.full_reset_clicked.emit)
        btn.setToolTip("모든 레이어와 설정을 초기화하고 처음부터 다시 시작")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 6px;
                color: #dc2626;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 16px;
            }
            QPushButton:hover {
                background-color: #fee2e2;
                border-color: #f87171;
            }
            QPushButton:pressed {
                background-color: #fecaca;
            }
        """)
        return btn

    def _create_primary_button(self, text):
        """Create primary action button"""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                color: #374151;
                font-size: 14px;
                font-weight: 500;
                padding: 10px 16px;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
                border-color: #9ca3af;
            }
            QPushButton:pressed {
                background-color: #d1d5db;
            }
            QPushButton:disabled {
                background-color: #f9fafb;
                color: #9ca3af;
                border-color: #e5e7eb;
            }
        """)
        return btn

    def _create_secondary_button(self, text):
        """Create secondary button"""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                color: #374151;
                font-size: 14px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #f9fafb;
                border-color: #9ca3af;
            }
            QPushButton:pressed {
                background-color: #f3f4f6;
            }
            QPushButton:disabled {
                background-color: #f9fafb;
                color: #9ca3af;
                border-color: #e5e7eb;
            }
        """)
        return btn

    def _create_action_button(self, text):
        """Create main action button (dark style)"""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #1f2937;
                border: none;
                border-radius: 6px;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 16px;
            }
            QPushButton:hover {
                background-color: #374151;
            }
            QPushButton:pressed {
                background-color: #111827;
            }
            QPushButton:disabled {
                background-color: #9ca3af;
                color: #f3f4f6;
            }
        """)
        return btn

    def _create_chip_button(self, text):
        """Create chip-style button"""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
                color: #374151;
                font-size: 13px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
                border-color: #d1d5db;
            }
            QPushButton:pressed {
                background-color: #d1d5db;
            }
            QPushButton:disabled {
                background-color: #f9fafb;
                color: #9ca3af;
                border-color: #e5e7eb;
            }
        """)
        return btn

    def _create_layout_button(self):
        """Create 'Open in Layout' button"""
        btn = QPushButton("조판으로 이동 (A0 자동 배치)")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip("현재 도면 범위를 A0 크기로 조판관리자에 자동 배치하여 엽니다")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #f0fdf4;
                border: 1px solid #86efac;
                border-radius: 6px;
                color: #15803d;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 16px;
            }
            QPushButton:hover {
                background-color: #dcfce7;
                border-color: #4ade80;
            }
            QPushButton:pressed {
                background-color: #bbf7d0;
            }
            QPushButton:disabled {
                background-color: #f9fafb;
                color: #9ca3af;
                border-color: #e5e7eb;
            }
        """)
        return btn

    def _lock_btn_style(self, locked: bool) -> str:
        """Return stylesheet for lock button based on lock state"""
        if locked:
            return """
                QPushButton {
                    background-color: #eff6ff;
                    border: 1px solid #2563eb;
                    border-radius: 4px;
                    color: #1d4ed8;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 8px 12px;
                }
                QPushButton:hover {
                    background-color: #dbeafe;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: white;
                    border: 1px solid #d1d5db;
                    border-radius: 4px;
                    color: #374151;
                    font-size: 14px;
                    padding: 8px 12px;
                }
                QPushButton:hover {
                    background-color: #f9fafb;
                    border-color: #9ca3af;
                }
                QPushButton:disabled {
                    background-color: #f9fafb;
                    color: #9ca3af;
                    border-color: #e5e7eb;
                }
            """

    def _create_lock_button(self):
        """Create lock/unlock toggle button for box"""
        btn = QPushButton("잠금")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip("도면 범위를 고정하여 실수로 이동/크기조절되지 않도록 잠금")
        btn.setStyleSheet(self._lock_btn_style(False))
        return btn

    def _on_lock_box_clicked(self):
        """Toggle box lock state"""
        self.is_box_locked = not self.is_box_locked
        if self.is_box_locked:
            self.btn_lock_box.setText("잠금 해제")
            self.btn_lock_box.setStyleSheet(self._lock_btn_style(True))
            self.btn_horizontal.setEnabled(False)
            self.btn_vertical.setEnabled(False)
            self.btn_reset_box.setEnabled(False)
        else:
            self.btn_lock_box.setText("잠금")
            self.btn_lock_box.setStyleSheet(self._lock_btn_style(False))
            self.btn_horizontal.setEnabled(True)
            self.btn_vertical.setEnabled(True)
            self.btn_reset_box.setEnabled(True)
        self.lock_box_clicked.emit(self.is_box_locked)

    def _create_divider(self):
        """Create horizontal divider"""
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #e5e7eb; border: none;")
        return divider

    # ===== Data loading methods =====

    def load_admin_data(self):
        """Load administrative region data from CSV"""
        csv_path = Path(__file__).parent.parent / "data" / "admin_regions.csv"

        if not csv_path.exists():
            csv_path = Path(__file__).parent.parent.parent / "admin_regions.csv"

        if not csv_path.exists():
            self.set_status("CSV 파일 없음", "warning")
            return

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = row['adm_cd'].strip()
                    name = row['adm_nm'].strip()
                    self.admin_data[code] = name

            self._build_hierarchy()
            self._populate_sido()
            self.set_status(f"{len(self.admin_data)}개 행정구역 로드 완료")

        except Exception as e:
            self.set_status(f"CSV 로드 실패: {str(e)}", "error")

    def _build_hierarchy(self):
        """Build hierarchical structure from flat data"""
        self.hierarchy = {
            'sido': {},
            'sigungu': {},
            'emd': {}
        }

        for code, name in self.admin_data.items():
            if len(code) == 2:
                self.hierarchy['sido'][code] = name
            elif len(code) == 5:
                sido_code = code[:2]
                if sido_code not in self.hierarchy['sigungu']:
                    self.hierarchy['sigungu'][sido_code] = {}
                self.hierarchy['sigungu'][sido_code][code] = name
            elif len(code) == 8:
                sigungu_code = code[:5]
                if sigungu_code not in self.hierarchy['emd']:
                    self.hierarchy['emd'][sigungu_code] = {}
                self.hierarchy['emd'][sigungu_code][code] = name

    def _populate_sido(self):
        """Populate sido combo box"""
        self.sido_combo.clear()
        self.sido_combo.addItem("-- 선택하세요 --", "")

        for code, name in sorted(self.hierarchy['sido'].items()):
            self.sido_combo.addItem(name, code)

    # ===== Event handlers =====

    def _on_sido_changed(self, index):
        """Handle sido selection change"""
        self.sigungu_combo.clear()
        self.sigungu_combo.addItem("-- 선택하세요 --", "")
        self.sigungu_combo.setEnabled(False)

        self.emd_combo.clear()
        self.emd_combo.addItem("-- 선택하세요 --", "")
        self.emd_combo.setEnabled(False)

        sido_code = self.sido_combo.currentData()
        if not sido_code:
            return

        if sido_code in self.hierarchy['sigungu']:
            for code, name in sorted(self.hierarchy['sigungu'][sido_code].items()):
                self.sigungu_combo.addItem(name, code)
            self.sigungu_combo.setEnabled(True)

        self.region_changed.emit('sido', sido_code)

    def _on_sigungu_changed(self, index):
        """Handle sigungu selection change"""
        self.emd_combo.clear()
        self.emd_combo.addItem("-- 선택하세요 --", "")
        self.emd_combo.setEnabled(False)

        sigungu_code = self.sigungu_combo.currentData()
        if not sigungu_code:
            return

        if sigungu_code in self.hierarchy['emd']:
            for code, name in sorted(self.hierarchy['emd'][sigungu_code].items()):
                self.emd_combo.addItem(name, code)
            self.emd_combo.setEnabled(True)

        self.region_changed.emit('sigungu', sigungu_code)

    def _on_emd_changed(self, index):
        """Handle emd selection change"""
        emd_code = self.emd_combo.currentData()
        if emd_code:
            self.region_changed.emit('emd', emd_code)

    # ===== Public API methods =====

    def get_selected_region(self) -> Tuple[Optional[str], Optional[str]]:
        """Get the currently selected region at the most specific level."""
        emd_code = self.emd_combo.currentData()
        if emd_code:
            return ('emd', emd_code)

        sigungu_code = self.sigungu_combo.currentData()
        if sigungu_code:
            return ('sigungu', sigungu_code)

        sido_code = self.sido_combo.currentData()
        if sido_code:
            return ('sido', sido_code)

        return (None, None)

    def enable_box_controls(self, enabled: bool):
        """Enable/disable box control buttons"""
        if not enabled:
            # 비활성화 시 잠금 상태도 초기화
            self.is_box_locked = False
            self.btn_lock_box.setText("잠금")
            self.btn_lock_box.setStyleSheet(self._lock_btn_style(False))
        # 잠금 상태가 아닐 때만 가로/세로/초기화 버튼 활성화
        if not self.is_box_locked:
            self.btn_horizontal.setEnabled(enabled)
            self.btn_vertical.setEnabled(enabled)
            self.btn_reset_box.setEnabled(enabled)
        self.btn_lock_box.setEnabled(enabled)

    def enable_overlay_controls(self, enabled: bool):
        """Enable/disable overlay element buttons"""
        self.btn_add_north.setEnabled(enabled)
        self.btn_add_scale.setEnabled(enabled)
        self.btn_add_outer.setEnabled(enabled)

    def set_finalized(self, finalized: bool):
        """Update UI state when workflow is finalized"""
        if finalized:
            self.set_status('도면 작성 완료! 내보내기 가능', 'success')
            self.btn_export_pdf.setEnabled(True)
            self.btn_export_image.setEnabled(True)
            self.btn_save_project.setEnabled(True)
            self.btn_open_layout.setEnabled(True)
            self.btn_load_area_a.setEnabled(False)
            self.enable_box_controls(False)
            self.enable_overlay_controls(False)
            self.btn_load_area_b.setEnabled(False)
            self.btn_finalize.setEnabled(False)

    def reset_ui(self):
        """Reset entire UI to initial state"""
        self.btn_load_area_a.setEnabled(True)
        self.enable_box_controls(False)
        self.enable_overlay_controls(False)
        self.btn_load_area_b.setEnabled(False)
        self.btn_finalize.setEnabled(False)
        self.btn_export_pdf.setEnabled(False)
        self.btn_export_image.setEnabled(False)
        self.btn_save_project.setEnabled(False)
        self.btn_open_layout.setEnabled(False)
        self.set_status('준비 - 행정구역을 선택하고 대상영역을 로드하세요', 'info')

    def show_progress(self, current: int, total: int, message: str = ""):
        """Show progress indicator"""
        self.progress_frame.setVisible(True)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        if message:
            self.progress_status_label.setText(message)
        else:
            self.progress_status_label.setText(f"처리 중... {current} / {total}")

    def hide_progress(self):
        """Hide progress indicator"""
        self.progress_frame.setVisible(False)

    def set_status(self, message: str, level: str = "info"):
        """Set status message with color coding"""
        self.status_label.setText(message)

        styles = {
            'info': "color: #6b7280;",
            'success': "color: #059669; font-weight: bold;",
            'warning': "color: #d97706;",
            'error': "color: #dc2626; font-weight: bold;"
        }

        style = styles.get(level, styles['info'])
        self.status_label.setStyleSheet(f"{style} font-size: 13px; border: none;")

    def reset_workflow(self):
        """Reset UI to initial state"""
        self.btn_load_area_a.setEnabled(True)
        self.enable_box_controls(False)
        self.enable_overlay_controls(False)
        self.btn_load_area_b.setEnabled(False)
        self.btn_finalize.setEnabled(False)
        self.btn_export_pdf.setEnabled(False)
        self.btn_export_image.setEnabled(False)
        self.btn_save_project.setEnabled(False)
        self.btn_open_layout.setEnabled(False)
        self.hide_progress()
        self.set_status('행정구역을 선택하세요', 'info')


# Standalone test
if __name__ == '__main__':
    import sys
    try:
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dialog = WMSPlanDialog()
    dialog.show()
    sys.exit(app.exec() if hasattr(app, 'exec') else app.exec_())
