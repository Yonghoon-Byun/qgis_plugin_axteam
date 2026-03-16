# -*- coding: utf-8 -*-
"""
Step 4: 레이어 병합 및 스타일 정리
로드된 레이어를 그룹화하고 스타일을 일괄 적용
"""

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox, QCheckBox, QScrollArea, QSpinBox,
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer

from .styles import CARD_STYLE, PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE
from ..core.style_manager import StyleManager

# 레이어 그룹 분류
LAYER_GROUPS = {
    "현황_경계": ["행정동 경계"],
    "현황_지형": ["등고선", "DEM 90m"],
    "현황_도로": ["도로경계선", "도로중심선", "터널"],
    "현황_수계": ["하천경계", "하천중심선", "호수 및 저수지"],
    "현황_건물": ["건축물정보"],
    "현황_토지": ["연속지적도", "토지소유정보"],
    "현황_단지": ["단지경계", "단지시설용지", "단지용도지역", "단지유치업종"],
}


class Step4Organize(QWidget):
    """레이어 정리 및 스타일 적용 페이지"""

    def __init__(self, iface, shared_data, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.shared_data = shared_data
        self.style_manager = StyleManager()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        guide = QLabel(
            "로드된 레이어를 그룹별로 정리하고 스타일을 적용합니다.\n"
            "배경지도(Vworld) 투명도도 조절할 수 있습니다."
        )
        guide.setStyleSheet("font-size: 14px; color: #6b7280;")
        guide.setWordWrap(True)
        layout.addWidget(guide)

        # 그룹화 카드
        group_card = QFrame()
        group_card.setStyleSheet(CARD_STYLE)
        gc_layout = QVBoxLayout()
        gc_layout.setContentsMargins(16, 12, 16, 12)
        gc_layout.setSpacing(8)

        gc_title = QLabel("레이어 그룹화")
        gc_title.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #1f2937; border: none;"
        )
        gc_layout.addWidget(gc_title)

        gc_desc = QLabel(
            "로드된 레이어를 용도별 그룹(현황_도로, 현황_수계 등)으로 자동 분류합니다."
        )
        gc_desc.setStyleSheet("font-size: 13px; color: #6b7280; border: none;")
        gc_desc.setWordWrap(True)
        gc_layout.addWidget(gc_desc)

        btn_group = QPushButton("레이어 그룹화 실행")
        btn_group.setStyleSheet(PRIMARY_BUTTON_STYLE)
        btn_group.setCursor(Qt.PointingHandCursor)
        btn_group.setFixedHeight(38)
        btn_group.clicked.connect(self._execute_grouping)
        gc_layout.addWidget(btn_group)

        group_card.setLayout(gc_layout)
        layout.addWidget(group_card)

        # 스타일 카드
        style_card = QFrame()
        style_card.setStyleSheet(CARD_STYLE)
        sc_layout = QVBoxLayout()
        sc_layout.setContentsMargins(16, 12, 16, 12)
        sc_layout.setSpacing(8)

        sc_title = QLabel("스타일 적용")
        sc_title.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #1f2937; border: none;"
        )
        sc_layout.addWidget(sc_title)

        sc_desc = QLabel(
            "상하수도 스타일 라이브러리(00_상하수도)를 기반으로 자동 매칭합니다."
        )
        sc_desc.setStyleSheet("font-size: 13px; color: #6b7280; border: none;")
        sc_desc.setWordWrap(True)
        sc_layout.addWidget(sc_desc)

        btn_style = QPushButton("스타일 일괄 적용")
        btn_style.setStyleSheet(PRIMARY_BUTTON_STYLE)
        btn_style.setCursor(Qt.PointingHandCursor)
        btn_style.setFixedHeight(38)
        btn_style.clicked.connect(self._apply_styles)
        sc_layout.addWidget(btn_style)

        style_card.setLayout(sc_layout)
        layout.addWidget(style_card)

        # 배경지도 투명도 카드
        bg_card = QFrame()
        bg_card.setStyleSheet(CARD_STYLE)
        bg_layout = QHBoxLayout()
        bg_layout.setContentsMargins(16, 12, 16, 12)

        bg_label = QLabel("배경지도(래스터) 투명도:")
        bg_label.setStyleSheet(
            "font-size: 14px; color: #374151; border: none;"
        )
        bg_layout.addWidget(bg_label)

        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setValue(60)
        self.opacity_spin.setSuffix("%")
        bg_layout.addWidget(self.opacity_spin)

        btn_opacity = QPushButton("적용")
        btn_opacity.setStyleSheet(SECONDARY_BUTTON_STYLE)
        btn_opacity.setCursor(Qt.PointingHandCursor)
        btn_opacity.setFixedWidth(60)
        btn_opacity.clicked.connect(self._apply_opacity)
        bg_layout.addWidget(btn_opacity)

        bg_card.setLayout(bg_layout)
        layout.addWidget(bg_card)

        # 상태
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 13px; color: #6b7280; padding: 4px;")
        layout.addWidget(self.status_label)

        layout.addStretch()
        self.setLayout(layout)

    def _execute_grouping(self):
        """레이어를 그룹별로 분류"""
        root = QgsProject.instance().layerTreeRoot()
        loaded = self.shared_data.get("loaded_layers", [])

        if not loaded:
            QMessageBox.warning(self, "알림", "로드된 레이어가 없습니다.")
            return

        grouped_count = 0
        for group_name, layer_names in LAYER_GROUPS.items():
            group_node = None

            for layer in loaded:
                if layer.name() in layer_names or any(
                    ln in layer.name() for ln in layer_names
                ):
                    # 그룹 노드 생성 (없으면)
                    if group_node is None:
                        existing = root.findGroup(group_name)
                        group_node = existing or root.insertGroup(0, group_name)

                    # 레이어를 그룹으로 이동
                    tree_layer = root.findLayer(layer.id())
                    if tree_layer:
                        clone = tree_layer.clone()
                        group_node.addChildNode(clone)
                        root.removeChildNode(tree_layer)
                        grouped_count += 1

        self.status_label.setText(f"그룹화 완료: {grouped_count}개 레이어 분류됨")
        self.status_label.setStyleSheet(
            "font-size: 13px; color: #059669; padding: 4px; font-weight: 600;"
        )

    def _apply_styles(self):
        """모든 로드된 레이어에 스타일 적용"""
        loaded = self.shared_data.get("loaded_layers", [])
        if not loaded:
            QMessageBox.warning(self, "알림", "로드된 레이어가 없습니다.")
            return

        applied = 0
        for layer in loaded:
            if isinstance(layer, QgsVectorLayer):
                if self.style_manager.apply_style_to_layer(layer):
                    applied += 1

        self.iface.mapCanvas().refresh()
        self.status_label.setText(f"스타일 적용 완료: {applied}/{len(loaded)}개 레이어")
        self.status_label.setStyleSheet(
            "font-size: 13px; color: #059669; padding: 4px; font-weight: 600;"
        )

    def _apply_opacity(self):
        """래스터 레이어 투명도 조절"""
        opacity = self.opacity_spin.value() / 100.0
        count = 0
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsRasterLayer):
                layer.setOpacity(opacity)
                layer.triggerRepaint()
                count += 1

        self.status_label.setText(f"투명도 {self.opacity_spin.value()}% 적용: {count}개 래스터 레이어")

    def on_enter(self):
        pass

    def execute_step(self):
        return True
