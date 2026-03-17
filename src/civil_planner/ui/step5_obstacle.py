# -*- coding: utf-8 -*-
"""
Step 6: 지장물 데이터 연동
로컬 셰이프 파일을 로드하고, 작업 범위에 맞게 전처리
"""

import os

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox, QFileDialog, QListWidget, QListWidgetItem,
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject, QgsVectorLayer

from .styles import CARD_STYLE, PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE
from ..core.preprocessor import Preprocessor
from ..core.style_manager import StyleManager


class Step5Obstacle(QWidget):
    """지장물 데이터 연동 페이지"""

    def __init__(self, iface, shared_data, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.shared_data = shared_data
        self.style_manager = StyleManager()
        self._file_paths = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        guide = QLabel(
            "발주처로부터 수령한 지장물 데이터(Shapefile)를 불러옵니다.\n"
            "작업 범위에 맞게 자동으로 클리핑 및 도형 수정을 수행합니다."
        )
        guide.setStyleSheet("font-size: 14px; color: #6b7280;")
        guide.setWordWrap(True)
        layout.addWidget(guide)

        # 파일 선택 카드
        file_card = QFrame()
        file_card.setStyleSheet(CARD_STYLE)
        fc_layout = QVBoxLayout()
        fc_layout.setContentsMargins(16, 12, 16, 12)
        fc_layout.setSpacing(8)

        fc_title = QLabel("지장물 파일 선택")
        fc_title.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #1f2937; border: none;"
        )
        fc_layout.addWidget(fc_title)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("파일 추가...")
        btn_add.setStyleSheet(SECONDARY_BUTTON_STYLE)
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self._add_files)
        btn_row.addWidget(btn_add)

        btn_clear = QPushButton("목록 초기화")
        btn_clear.setStyleSheet(SECONDARY_BUTTON_STYLE)
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.clicked.connect(self._clear_files)
        btn_row.addWidget(btn_clear)
        btn_row.addStretch()
        fc_layout.addLayout(btn_row)

        self.file_list = QListWidget()
        self.file_list.setStyleSheet(
            "border: 1px solid #e5e7eb; border-radius: 4px; "
            "background-color: #f9fafb; font-size: 13px;"
        )
        self.file_list.setMaximumHeight(200)
        fc_layout.addWidget(self.file_list)

        file_card.setLayout(fc_layout)
        layout.addWidget(file_card)

        # 로드 버튼
        self.btn_load = QPushButton("지장물 로드 및 전처리")
        self.btn_load.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.btn_load.setCursor(Qt.PointingHandCursor)
        self.btn_load.setFixedHeight(42)
        self.btn_load.clicked.connect(self._load_obstacles)
        layout.addWidget(self.btn_load)

        # 안내: 스타일 매칭
        hint_card = QFrame()
        hint_card.setStyleSheet(CARD_STYLE)
        hint_layout = QVBoxLayout()
        hint_layout.setContentsMargins(16, 12, 16, 12)

        hint_title = QLabel("스타일 자동 매칭 안내")
        hint_title.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #1f2937; border: none;"
        )
        hint_layout.addWidget(hint_title)

        hint_text = QLabel(
            "파일명에 다음 키워드가 포함되면 스타일이 자동 적용됩니다:\n"
            "가스, 고압전기, 광역상수, 난방, 전기_저압, 지방상수, 통신, 하수"
        )
        hint_text.setStyleSheet("font-size: 13px; color: #6b7280; border: none;")
        hint_text.setWordWrap(True)
        hint_layout.addWidget(hint_text)

        hint_card.setLayout(hint_layout)
        layout.addWidget(hint_card)

        # 상태
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 13px; color: #6b7280; padding: 4px;")
        layout.addWidget(self.status_label)

        layout.addStretch()
        self.setLayout(layout)

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "지장물 Shapefile 선택",
            "",
            "Shapefile (*.shp);;GeoPackage (*.gpkg);;All Files (*)",
        )
        for f in files:
            if f not in self._file_paths:
                self._file_paths.append(f)
                self.file_list.addItem(os.path.basename(f))

    def _clear_files(self):
        self._file_paths.clear()
        self.file_list.clear()

    def _load_obstacles(self):
        """지장물 파일 로드 + 전처리"""
        if not self._file_paths:
            QMessageBox.warning(self, "알림", "지장물 파일을 추가해주세요.")
            return

        boundary = self.shared_data.get("boundary_layer")
        if boundary is None:
            QMessageBox.warning(self, "알림", "작업 범위가 설정되지 않았습니다.")
            return

        # 지장물 그룹 생성
        root = QgsProject.instance().layerTreeRoot()
        obstacle_group = root.findGroup("지장물")
        if obstacle_group is None:
            obstacle_group = root.insertGroup(0, "지장물")

        loaded = []
        for filepath in self._file_paths:
            basename = os.path.splitext(os.path.basename(filepath))[0]

            layer = QgsVectorLayer(filepath, basename, "ogr")
            if not layer.isValid():
                self.status_label.setText(f"로드 실패: {basename}")
                self.status_label.setStyleSheet(
                    "font-size: 13px; color: #ef4444; padding: 4px;"
                )
                continue

            # 전처리 (클리핑 + 도형수정)
            processed = Preprocessor.preprocess_layer(layer, boundary)
            result_layer = processed if processed is not None else layer

            # 스타일 적용 (파일명 기반 매칭)
            self.style_manager.apply_style_to_layer(result_layer, basename)

            QgsProject.instance().addMapLayer(result_layer, False)
            obstacle_group.addLayer(result_layer)
            loaded.append(result_layer)

        self.shared_data["obstacle_layers"] = loaded
        self.status_label.setText(f"지장물 로드 완료: {len(loaded)}개 레이어")
        self.status_label.setStyleSheet(
            "font-size: 13px; color: #059669; padding: 4px; font-weight: 600;"
        )
        self.iface.mapCanvas().refresh()

    def on_enter(self):
        pass

    def execute_step(self):
        # 지장물은 선택사항이므로 항상 통과
        return True
