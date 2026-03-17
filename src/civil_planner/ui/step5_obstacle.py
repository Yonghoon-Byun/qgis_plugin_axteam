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
        self._folder_map = {}  # {folder_name: [shp_paths]}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        guide = QLabel(
            "발주처로부터 수령한 지장물 데이터(Shapefile)를 불러옵니다.\n"
            "폴더를 선택하면 하위 폴더별로 그룹이 자동 생성됩니다.\n"
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

        btn_add_folder = QPushButton("폴더 추가...")
        btn_add_folder.setStyleSheet(SECONDARY_BUTTON_STYLE)
        btn_add_folder.setCursor(Qt.PointingHandCursor)
        btn_add_folder.clicked.connect(self._add_folder)
        btn_row.addWidget(btn_add_folder)

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

    def _add_folder(self):
        """폴더 선택 → 하위 디렉토리별 SHP 파일 자동 탐색"""
        folder = QFileDialog.getExistingDirectory(
            self, "지장물 폴더 선택", ""
        )
        if not folder:
            return

        # 하위 디렉토리 스캔
        found_count = 0
        for entry in sorted(os.listdir(folder)):
            subdir = os.path.join(folder, entry)
            if not os.path.isdir(subdir):
                continue

            # 서브폴더 내 SHP 파일 수집
            shp_files = sorted([
                os.path.join(subdir, f)
                for f in os.listdir(subdir)
                if f.lower().endswith(".shp")
            ])
            if not shp_files:
                continue

            folder_name = entry  # 가스, 상수, 하수 등
            if folder_name not in self._folder_map:
                self._folder_map[folder_name] = []

            for shp in shp_files:
                if shp not in self._folder_map[folder_name]:
                    self._folder_map[folder_name].append(shp)
                    found_count += 1

            # 리스트 위젯에 표시
            self.file_list.addItem(f"\U0001f4c1 {folder_name}/ ({len(shp_files)}개 SHP)")

        if found_count == 0:
            QMessageBox.information(self, "알림", "선택한 폴더에 SHP 파일이 없습니다.")
        else:
            self.status_label.setText(f"폴더 추가 완료: {found_count}개 SHP 파일")
            self.status_label.setStyleSheet(
                "font-size: 13px; color: #059669; padding: 4px; font-weight: 600;"
            )

    def _clear_files(self):
        self._file_paths.clear()
        self._folder_map.clear()
        self.file_list.clear()

    def _load_obstacles(self):
        """지장물 파일 로드 + 전처리"""
        if not self._file_paths and not self._folder_map:
            QMessageBox.warning(self, "알림", "지장물 파일 또는 폴더를 추가해주세요.")
            return

        boundary = self.shared_data.get("boundary_layer")
        if boundary is None:
            QMessageBox.warning(self, "알림", "작업 범위가 설정되지 않았습니다.")
            return

        # 지장물 루트 그룹 생성
        root = QgsProject.instance().layerTreeRoot()
        obstacle_group = root.findGroup("지장물")
        if obstacle_group is None:
            obstacle_group = root.insertGroup(0, "지장물")

        loaded = []

        # 1) 폴더 기반 로드 (서브그룹별)
        for folder_name, shp_paths in sorted(self._folder_map.items()):
            # 서브그룹 생성
            sub_group = obstacle_group.findGroup(folder_name)
            if sub_group is None:
                sub_group = obstacle_group.addGroup(folder_name)

            for filepath in shp_paths:
                result = self._load_single_shp(filepath, boundary, sub_group)
                if result:
                    loaded.append(result)

        # 2) 개별 파일 로드 (루트 지장물 그룹에)
        for filepath in self._file_paths:
            result = self._load_single_shp(filepath, boundary, obstacle_group)
            if result:
                loaded.append(result)

        self.shared_data["obstacle_layers"] = loaded
        self.status_label.setText(f"지장물 로드 완료: {len(loaded)}개 레이어")
        self.status_label.setStyleSheet(
            "font-size: 13px; color: #059669; padding: 4px; font-weight: 600;"
        )
        self.iface.mapCanvas().refresh()

    def _load_single_shp(self, filepath, boundary, target_group):
        """단일 SHP 파일 로드 + 전처리 + 그룹에 추가

        Args:
            filepath: SHP 파일 경로
            boundary: 클리핑 범위 레이어
            target_group: 추가할 레이어 트리 그룹

        Returns:
            QgsVectorLayer or None
        """
        basename = os.path.splitext(os.path.basename(filepath))[0]

        layer = QgsVectorLayer(filepath, basename, "ogr")
        if not layer.isValid():
            self.status_label.setText(f"로드 실패: {basename}")
            self.status_label.setStyleSheet(
                "font-size: 13px; color: #ef4444; padding: 4px;"
            )
            return None

        # 전처리 (클리핑 + 도형수정)
        processed = Preprocessor.preprocess_layer(layer, boundary)
        if processed is None:
            return None

        # 스타일 적용 (파일명 기반 매칭)
        self.style_manager.apply_style_to_layer(processed, basename)

        QgsProject.instance().addMapLayer(processed, False)
        target_group.addLayer(processed)
        return processed

    def reset(self):
        """상태 초기화"""
        self._file_paths.clear()
        self._folder_map.clear()
        self.file_list.clear()
        self.status_label.setText("")

    def on_enter(self):
        pass

    def execute_step(self):
        # 지장물은 선택사항이므로 항상 통과
        return True
