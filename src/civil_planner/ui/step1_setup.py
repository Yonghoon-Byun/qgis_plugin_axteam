# -*- coding: utf-8 -*-
"""
Step 1: 작업환경 설정 - 프로젝트 CRS를 EPSG:5186으로 설정
"""

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox,
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject, QgsCoordinateReferenceSystem

from .styles import CARD_STYLE, PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE


# 빠른 선택용 CRS 목록
CRS_PRESETS = [
    ("EPSG:5186", "Korea 2000 / Central Belt 2010", True),
    ("EPSG:5179", "Korea 2000 / Unified CS", False),
    ("EPSG:5174", "Korea 1985 / Central Belt", False),
    ("EPSG:4326", "WGS 84 (위경도)", False),
]


class Step1Setup(QWidget):
    """프로젝트 CRS 설정 페이지"""

    def __init__(self, iface, shared_data, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.shared_data = shared_data
        self.selected_crs = "EPSG:5186"
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 안내 텍스트
        guide = QLabel(
            "프로젝트의 좌표계(CRS)를 설정합니다.\n"
            "토목 설계 작업에는 EPSG:5186 (GRS80 중부원점)을 권장합니다."
        )
        guide.setStyleSheet("font-size: 14px; color: #6b7280; line-height: 1.5;")
        guide.setWordWrap(True)
        layout.addWidget(guide)

        # CRS 선택 카드
        card = QFrame()
        card.setStyleSheet(CARD_STYLE)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        card_title = QLabel("좌표계 선택")
        card_title.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #1f2937; border: none;"
        )
        card_layout.addWidget(card_title)

        self.crs_buttons = []
        for epsg, name, is_default in CRS_PRESETS:
            btn = QPushButton(f"{epsg}  -  {name}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setChecked(is_default)
            btn.clicked.connect(lambda checked, e=epsg: self._on_crs_selected(e))
            self.crs_buttons.append((btn, epsg))
            card_layout.addWidget(btn)

        card.setLayout(card_layout)
        layout.addWidget(card)

        # 현재 프로젝트 CRS 표시
        self.current_crs_label = QLabel()
        self.current_crs_label.setStyleSheet(
            "font-size: 13px; color: #6b7280; padding: 8px;"
        )
        layout.addWidget(self.current_crs_label)

        # 적용 버튼
        btn_apply = QPushButton("CRS 적용")
        btn_apply.setStyleSheet(PRIMARY_BUTTON_STYLE)
        btn_apply.setCursor(Qt.PointingHandCursor)
        btn_apply.setFixedHeight(40)
        btn_apply.clicked.connect(self._apply_crs)
        layout.addWidget(btn_apply)

        layout.addStretch()
        self.setLayout(layout)
        self._update_crs_display()
        self._update_button_styles()

    def _on_crs_selected(self, epsg):
        self.selected_crs = epsg
        # 라디오 버튼 효과
        for btn, e in self.crs_buttons:
            btn.setChecked(e == epsg)
        self._update_button_styles()

    def _update_button_styles(self):
        for btn, epsg in self.crs_buttons:
            if btn.isChecked():
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1f2937; color: white;
                        border: none; border-radius: 4px;
                        font-size: 14px; font-weight: 600;
                        padding: 10px 16px; text-align: left;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: white; color: #374151;
                        border: 1px solid #e5e7eb; border-radius: 4px;
                        font-size: 14px; font-weight: 500;
                        padding: 10px 16px; text-align: left;
                    }
                    QPushButton:hover {
                        background-color: #f9fafb; border-color: #9ca3af;
                    }
                """)

    def _update_crs_display(self):
        project = QgsProject.instance()
        crs = project.crs()
        if crs.isValid():
            self.current_crs_label.setText(
                f"현재 프로젝트 CRS: {crs.authid()} ({crs.description()})"
            )
        else:
            self.current_crs_label.setText("현재 프로젝트 CRS: 설정되지 않음")

    def _apply_crs(self):
        crs = QgsCoordinateReferenceSystem(self.selected_crs)
        if not crs.isValid():
            QMessageBox.warning(self, "오류", f"유효하지 않은 CRS: {self.selected_crs}")
            return

        QgsProject.instance().setCrs(crs)
        self._update_crs_display()
        QMessageBox.information(
            self, "완료",
            f"프로젝트 CRS가 {self.selected_crs}로 설정되었습니다."
        )

    def execute_step(self):
        """다음 버튼 클릭 시 호출"""
        project_crs = QgsProject.instance().crs()
        if not project_crs.isValid():
            QMessageBox.warning(self, "알림", "프로젝트 CRS를 먼저 설정해주세요.")
            return False
        return True
