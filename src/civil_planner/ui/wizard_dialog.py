# -*- coding: utf-8 -*-
"""
Civil Planner - 메인 위자드 다이얼로그
QStackedWidget 기반 6단계 위자드
"""

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QFrame, QStackedWidget, QSizePolicy,
)
from qgis.PyQt.QtCore import Qt

from .styles import (
    DIALOG_STYLESHEET, PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE,
    STEP_ACTIVE_STYLE, STEP_INACTIVE_STYLE, STEP_DONE_STYLE,
)
from .step1_setup import Step1Setup
from .step2_boundary import Step2Boundary
from .step3_load_data import Step3LoadData
from .step4_organize import Step4Organize
from .step5_obstacle import Step5Obstacle
from .step6_route import Step6Route


STEP_TITLES = [
    "작업환경 설정",
    "범위 설정",
    "데이터 로드",
    "정리 및 스타일",
    "지장물 연동",
    "관로 설계",
]


class CivilPlannerWizard(QDialog):
    """6단계 위자드 메인 다이얼로그"""

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.current_step = 0
        self.completed_steps = set()

        # 각 단계에서 공유하는 데이터
        self.shared_data = {
            "boundary_layer": None,     # 2단계에서 생성된 범위 레이어
            "loaded_layers": [],        # 3단계에서 로드된 레이어 목록
            "obstacle_layers": [],      # 5단계에서 로드된 지장물 레이어 목록
            "route_layer": None,        # 6단계에서 생성된 관로 레이어
        }

        self.setWindowFlags(Qt.Window)
        self.setWindowTitle("Civil Planner - 토목 관로 설계")
        self.setMinimumSize(560, 720)
        self.resize(560, 750)
        self.setStyleSheet(DIALOG_STYLESHEET)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # 헤더
        header = self._create_header()
        layout.addWidget(header)

        # 단계 표시 바
        self.step_bar = self._create_step_bar()
        layout.addWidget(self.step_bar)

        # 콘텐츠 (QStackedWidget)
        self.stack = QStackedWidget()
        self.step_pages = [
            Step1Setup(self.iface, self.shared_data),
            Step2Boundary(self.iface, self.shared_data),
            Step3LoadData(self.iface, self.shared_data),
            Step4Organize(self.iface, self.shared_data),
            Step5Obstacle(self.iface, self.shared_data),
            Step6Route(self.iface, self.shared_data),
        ]
        for page in self.step_pages:
            self.stack.addWidget(page)

        content_frame = QFrame()
        content_frame.setStyleSheet("background-color: #f9fafb; border: none;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self.stack)
        content_frame.setLayout(content_layout)
        layout.addWidget(content_frame, 1)

        # 하단 네비게이션
        nav = self._create_navigation()
        layout.addWidget(nav)

        self.setLayout(layout)
        self._update_ui()

    def _create_header(self):
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet(
            "background-color: #1f2937; border: none;"
        )
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("Civil Planner")
        title.setStyleSheet(
            "color: white; font-size: 18px; font-weight: bold; border: none;"
        )
        layout.addWidget(title)
        layout.addStretch()

        subtitle = QLabel("토목 관로 설계 워크플로우")
        subtitle.setStyleSheet(
            "color: #9ca3af; font-size: 13px; border: none;"
        )
        layout.addWidget(subtitle)

        header.setLayout(layout)
        return header

    def _create_step_bar(self):
        bar = QFrame()
        bar.setFixedHeight(48)
        bar.setStyleSheet(
            "background-color: white; border-bottom: 1px solid #e5e7eb;"
        )
        self.step_bar_layout = QHBoxLayout()
        self.step_bar_layout.setContentsMargins(16, 8, 16, 8)
        self.step_bar_layout.setSpacing(6)

        self.step_labels = []
        for i, title in enumerate(STEP_TITLES):
            lbl = QLabel(f" {i + 1}. {title} ")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setCursor(Qt.PointingHandCursor)
            lbl.mousePressEvent = lambda event, idx=i: self._on_step_clicked(idx)
            self.step_labels.append(lbl)
            self.step_bar_layout.addWidget(lbl)

        self.step_bar_layout.addStretch()
        bar.setLayout(self.step_bar_layout)
        return bar

    def _create_navigation(self):
        nav = QFrame()
        nav.setFixedHeight(64)
        nav.setStyleSheet(
            "background-color: white; border-top: 1px solid #e5e7eb;"
        )
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 12, 20, 12)

        # 이전 버튼
        self.btn_prev = QPushButton("이전")
        self.btn_prev.setFixedWidth(100)
        self.btn_prev.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.clicked.connect(self._go_prev)
        layout.addWidget(self.btn_prev)

        layout.addStretch()

        # 현재 단계 레이블
        self.step_info_label = QLabel()
        self.step_info_label.setStyleSheet(
            "color: #6b7280; font-size: 13px; border: none;"
        )
        layout.addWidget(self.step_info_label)

        layout.addStretch()

        # 다음/완료 버튼
        self.btn_next = QPushButton("다음")
        self.btn_next.setFixedWidth(100)
        self.btn_next.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.clicked.connect(self._go_next)
        layout.addWidget(self.btn_next)

        nav.setLayout(layout)
        return nav

    def _on_step_clicked(self, idx):
        """단계 표시 바 클릭 시 자유롭게 이동"""
        if 0 <= idx < len(self.step_pages):
            self.current_step = idx
            self._update_ui()
            page = self.step_pages[self.current_step]
            if hasattr(page, "on_enter"):
                page.on_enter()

    def _go_prev(self):
        if self.current_step > 0:
            self.current_step -= 1
            self._update_ui()
            page = self.step_pages[self.current_step]
            if hasattr(page, "on_enter"):
                page.on_enter()

    def _go_next(self):
        self.completed_steps.add(self.current_step)

        last_step = len(self.step_pages) - 1
        if self.current_step < last_step:
            self.current_step += 1
            self._update_ui()
            # 다음 페이지 진입 시 갱신
            next_page = self.step_pages[self.current_step]
            if hasattr(next_page, "on_enter"):
                next_page.on_enter()
        else:
            # 마지막 단계 완료
            self.completed_steps.add(last_step)
            self._update_ui()

    def _update_ui(self):
        """UI 상태 갱신"""
        self.stack.setCurrentIndex(self.current_step)

        # 단계 바 스타일 업데이트
        for i, lbl in enumerate(self.step_labels):
            if i in self.completed_steps and i != self.current_step:
                lbl.setStyleSheet(STEP_DONE_STYLE)
            elif i == self.current_step:
                lbl.setStyleSheet(STEP_ACTIVE_STYLE)
            else:
                lbl.setStyleSheet(STEP_INACTIVE_STYLE)

        # 네비게이션 버튼
        self.btn_prev.setEnabled(self.current_step > 0)
        last_step = len(self.step_pages) - 1
        if self.current_step == last_step:
            self.btn_next.setText("완료")
        else:
            self.btn_next.setText("다음")

        self.step_info_label.setText(
            f"{self.current_step + 1} / 6  {STEP_TITLES[self.current_step]}"
        )
