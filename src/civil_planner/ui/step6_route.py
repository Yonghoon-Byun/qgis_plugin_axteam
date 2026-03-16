# -*- coding: utf-8 -*-
"""
Step 6: 계획 노선(관로) 그리기
새 LineString 레이어 생성 + 편집 모드 활성화
"""

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox, QLineEdit, QComboBox,
)
from qgis.PyQt.QtCore import Qt
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsField, QgsFields,
    QgsWkbTypes, QgsVectorFileWriter,
)
from qgis.PyQt.QtCore import QVariant

from .styles import CARD_STYLE, PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE
from ..core.style_manager import StyleManager


class Step6Route(QWidget):
    """관로 LineString 레이어 생성 및 편집 페이지"""

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
            "관로 노선을 그리기 위한 새 레이어를 생성합니다.\n"
            "레이어 생성 후 편집 모드로 전환하여 지도에서 직접 관로를 그릴 수 있습니다."
        )
        guide.setStyleSheet("font-size: 14px; color: #6b7280;")
        guide.setWordWrap(True)
        layout.addWidget(guide)

        # 레이어 설정 카드
        card = QFrame()
        card.setStyleSheet(CARD_STYLE)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

        card_title = QLabel("관로 레이어 생성")
        card_title.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #1f2937; border: none;"
        )
        card_layout.addWidget(card_title)

        # 레이어 이름
        name_row = QHBoxLayout()
        name_label = QLabel("레이어 이름:")
        name_label.setStyleSheet("font-size: 14px; border: none; min-width: 90px;")
        name_row.addWidget(name_label)
        self.name_input = QLineEdit("계획 노선")
        name_row.addWidget(self.name_input)
        card_layout.addLayout(name_row)

        # 레이어 유형
        type_row = QHBoxLayout()
        type_label = QLabel("생성 방식:")
        type_label.setStyleSheet("font-size: 14px; border: none; min-width: 90px;")
        type_row.addWidget(type_label)
        self.type_combo = QComboBox()
        self.type_combo.addItem("메모리 레이어 (임시)", "memory")
        self.type_combo.addItem("Shapefile로 저장", "shp")
        type_row.addWidget(self.type_combo)
        card_layout.addLayout(type_row)

        # CRS 표시
        crs_row = QHBoxLayout()
        crs_label = QLabel("좌표계:")
        crs_label.setStyleSheet("font-size: 14px; border: none; min-width: 90px;")
        crs_row.addWidget(crs_label)
        self.crs_display = QLabel()
        self.crs_display.setStyleSheet("font-size: 14px; color: #6b7280; border: none;")
        crs_row.addWidget(self.crs_display)
        card_layout.addLayout(crs_row)

        card.setLayout(card_layout)
        layout.addWidget(card)

        # 생성 버튼
        self.btn_create = QPushButton("관로 레이어 생성")
        self.btn_create.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.btn_create.setCursor(Qt.PointingHandCursor)
        self.btn_create.setFixedHeight(42)
        self.btn_create.clicked.connect(self._create_route_layer)
        layout.addWidget(self.btn_create)

        # 편집 도구 카드
        edit_card = QFrame()
        edit_card.setStyleSheet(CARD_STYLE)
        edit_layout = QVBoxLayout()
        edit_layout.setContentsMargins(16, 12, 16, 12)
        edit_layout.setSpacing(8)

        edit_title = QLabel("편집 도구")
        edit_title.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #1f2937; border: none;"
        )
        edit_layout.addWidget(edit_title)

        btn_row = QHBoxLayout()
        self.btn_edit = QPushButton("편집 모드 시작")
        self.btn_edit.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.btn_edit.setCursor(Qt.PointingHandCursor)
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._toggle_editing)
        btn_row.addWidget(self.btn_edit)

        self.btn_snap = QPushButton("스냅 설정")
        self.btn_snap.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_snap.setCursor(Qt.PointingHandCursor)
        self.btn_snap.setEnabled(False)
        self.btn_snap.clicked.connect(self._configure_snapping)
        btn_row.addWidget(self.btn_snap)

        edit_layout.addLayout(btn_row)

        edit_desc = QLabel(
            "편집 모드 시작 후:\n"
            "- 도구모음에서 '라인 피처 추가'를 선택\n"
            "- 지도에서 클릭하여 관로 노선을 그립니다\n"
            "- 마우스 우클릭으로 피처 완성\n"
            "- 정점 편집 도구로 미세 조정"
        )
        edit_desc.setStyleSheet("font-size: 13px; color: #6b7280; border: none;")
        edit_desc.setWordWrap(True)
        edit_layout.addWidget(edit_desc)

        edit_card.setLayout(edit_layout)
        layout.addWidget(edit_card)

        # 상태
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 13px; color: #6b7280; padding: 4px;")
        layout.addWidget(self.status_label)

        layout.addStretch()
        self.setLayout(layout)

    def on_enter(self):
        """페이지 진입 시 CRS 표시 갱신"""
        crs = QgsProject.instance().crs()
        self.crs_display.setText(f"{crs.authid()} ({crs.description()})")

    def _create_route_layer(self):
        """관로 LineString 레이어 생성"""
        layer_name = self.name_input.text().strip()
        if not layer_name:
            QMessageBox.warning(self, "알림", "레이어 이름을 입력해주세요.")
            return

        crs = QgsProject.instance().crs()
        create_type = self.type_combo.currentData()

        if create_type == "memory":
            layer = self._create_memory_layer(layer_name, crs)
        else:
            layer = self._create_shp_layer(layer_name, crs)

        if layer is None or not layer.isValid():
            QMessageBox.critical(self, "오류", "레이어 생성에 실패했습니다.")
            return

        # 스타일 적용 (관로_계획)
        self.style_manager.apply_style_to_layer(layer, "계획 노선")

        # 프로젝트 최상단에 추가
        QgsProject.instance().addMapLayer(layer)
        root = QgsProject.instance().layerTreeRoot()
        tree_layer = root.findLayer(layer.id())
        if tree_layer:
            clone = tree_layer.clone()
            root.insertChildNode(0, clone)
            root.removeChildNode(tree_layer)

        self.shared_data["route_layer"] = layer
        self.btn_edit.setEnabled(True)
        self.btn_snap.setEnabled(True)

        self.status_label.setText(f"관로 레이어 생성 완료: {layer_name}")
        self.status_label.setStyleSheet(
            "font-size: 13px; color: #059669; padding: 4px; font-weight: 600;"
        )

    def _create_memory_layer(self, name, crs):
        """메모리 레이어 생성"""
        uri = (
            f"LineString?crs={crs.authid()}"
            f"&field=id:integer"
            f"&field=name:string(100)"
            f"&field=type:string(50)"
            f"&field=diameter:double"
            f"&field=material:string(50)"
            f"&field=memo:string(255)"
        )
        layer = QgsVectorLayer(uri, name, "memory")
        return layer if layer.isValid() else None

    def _create_shp_layer(self, name, crs):
        """Shapefile로 저장하는 레이어 생성"""
        from qgis.PyQt.QtWidgets import QFileDialog

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "관로 Shapefile 저장 위치",
            f"{name}.shp",
            "Shapefile (*.shp)",
        )
        if not filepath:
            return None

        fields = QgsFields()
        fields.append(QgsField("id", QVariant.Int))
        fields.append(QgsField("name", QVariant.String, len=100))
        fields.append(QgsField("type", QVariant.String, len=50))
        fields.append(QgsField("diameter", QVariant.Double))
        fields.append(QgsField("material", QVariant.String, len=50))
        fields.append(QgsField("memo", QVariant.String, len=255))

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "UTF-8"

        writer = QgsVectorFileWriter.create(
            filepath, fields, QgsWkbTypes.LineString, crs,
            QgsProject.instance().transformContext(), options,
        )

        if writer is None or writer.hasError() != QgsVectorFileWriter.NoError:
            return None

        del writer
        layer = QgsVectorLayer(filepath, name, "ogr")
        return layer if layer.isValid() else None

    def _toggle_editing(self):
        """편집 모드 토글"""
        layer = self.shared_data.get("route_layer")
        if layer is None:
            return

        # 활성 레이어 설정
        self.iface.setActiveLayer(layer)

        if layer.isEditable():
            layer.commitChanges()
            self.btn_edit.setText("편집 모드 시작")
            self.status_label.setText("편집 저장 완료")
        else:
            layer.startEditing()
            self.btn_edit.setText("편집 저장")
            self.status_label.setText(
                "편집 모드 활성화 - 도구모음에서 '라인 피처 추가' 선택"
            )

            # 다이얼로그 최소화
            parent_dialog = self.window()
            if parent_dialog:
                parent_dialog.showMinimized()

    def _configure_snapping(self):
        """스냅 설정"""
        from qgis.core import QgsSnappingConfig, QgsTolerance

        config = QgsProject.instance().snappingConfig()
        config.setEnabled(True)
        config.setMode(QgsSnappingConfig.AllLayers)
        config.setType(QgsSnappingConfig.VertexAndSegment)
        config.setTolerance(10)
        config.setUnits(QgsTolerance.Pixels)
        QgsProject.instance().setSnappingConfig(config)

        self.status_label.setText("스냅 설정 완료 (모든 레이어, 정점+세그먼트, 10px)")
        self.status_label.setStyleSheet(
            "font-size: 13px; color: #059669; padding: 4px; font-weight: 600;"
        )

    def execute_step(self):
        """완료 버튼 클릭 시"""
        layer = self.shared_data.get("route_layer")
        if layer and layer.isEditable():
            layer.commitChanges()
        return True
