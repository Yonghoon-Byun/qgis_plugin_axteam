# -*- coding: utf-8 -*-
"""
Main Controller for BasePlan Plugin v5.1 (Optimized)

토목 기본도면 작성 플러그인 메인 컨트롤러
- 대상영역/도면영역 로드
- 도면범위 설정 (가로도면/세로도면)
- 방위/축척 오버레이 지원
"""

import os

from qgis.core import (
    QgsProject, QgsRectangle, QgsCoordinateReferenceSystem, QgsPointXY,
    QgsRasterLayer, QgsMessageLog, Qgis
)
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QObject, QPointF
from qgis.PyQt.QtWidgets import QFileDialog

from ..core.wms_manager import WMSManager
from ..core.export_manager import ExportManager
from ..ui.main_dialog import WMSPlanDialog
from ..ui.box_tool import BoxMapTool
from ..ui.overlay_item import OverlayItem, ScaleBarItem


class PlanMapController(QObject):
    """Controller class that orchestrates the BasePlan workflow."""

    A0_RATIO = 1.41421356

    def __init__(self, iface: QgisInterface):
        """Initialize the controller with QGIS interface."""
        super().__init__()

        self.iface = iface
        self.canvas = iface.mapCanvas()

        # Initialize components
        self.wms_manager = WMSManager()
        self.export_manager = ExportManager()
        self.main_dialog = WMSPlanDialog()
        self.box_tool = BoxMapTool(self.canvas, controller=self)  # v4: controller 참조 전달

        # State management
        self.selected_admin = None
        self.current_bbox = None
        self.is_finalized = False
        self.area_a_extent = None
        self.area_a_loaded = False  # v4: 영역 A 로드 상태
        self.area_b_loaded = False  # v4: 영역 B 로드 상태

        # v4: 오버레이 상태
        self.north_overlay = None
        self.scale_overlay = None
        self.outer_gradient_layer = None  # v4.3: 외곽선 그라데이션 벡터 레이어

        # Connect signals
        self._connect_signals()

    def _connect_signals(self):
        """Connect signals between components."""
        # Dialog signals
        self.main_dialog.load_area_a_clicked.connect(self._on_load_area_a_clicked)
        self.main_dialog.horizontal_clicked.connect(self.set_box_horizontal)  # v4
        self.main_dialog.vertical_clicked.connect(self.set_box_vertical)      # v4
        self.main_dialog.reset_box_clicked.connect(self.reset_box)
        self.main_dialog.load_area_b_clicked.connect(self._on_load_area_b_clicked)
        self.main_dialog.finalize_clicked.connect(self.finalize)
        self.main_dialog.export_pdf_clicked.connect(self.export_pdf)
        self.main_dialog.export_image_clicked.connect(self.export_image)
        self.main_dialog.save_project_clicked.connect(self.save_project)
        self.main_dialog.add_north_clicked.connect(self.add_north_arrow)      # v4
        self.main_dialog.add_scale_clicked.connect(self.add_scale_bar)        # v4
        self.main_dialog.add_outer_clicked.connect(self.add_outer_gradient)   # v4.3
        self.main_dialog.full_reset_clicked.connect(self.full_reset)          # v4
        self.main_dialog.lock_box_clicked.connect(self._on_lock_box_clicked)  # 잠금
        self.main_dialog.open_layout_clicked.connect(self.open_in_layout)     # 조판

        # Box tool signals
        self.box_tool.boxDrawn.connect(self.on_box_drawn)
        self.box_tool.boxModified.connect(self.on_box_modified)
        self.box_tool.boxDeleted.connect(self.on_box_deleted)  # v4

        # WMS Manager 진행률 시그널
        self.wms_manager.progress_updated.connect(self._on_progress_updated)

    def _on_progress_updated(self, current: int, total: int, message: str):
        """v3: 진행률 업데이트 처리"""
        self.main_dialog.show_progress(current, total, message)

    def _setup_project_crs(self):
        """v4: 프로젝트 CRS를 EPSG:5179로 설정 및 확인"""
        project = QgsProject.instance()
        target_crs = QgsCoordinateReferenceSystem("EPSG:5179")

        if project.crs() != target_crs:
            project.setCrs(target_crs)
            print(f"[Controller] Project CRS set to EPSG:5179")
        else:
            print(f"[Controller] Project CRS already EPSG:5179")

    def _ensure_crs(self):
        """v4: 박스 조작 전 CRS 확인 및 재설정"""
        project = QgsProject.instance()
        target_crs = QgsCoordinateReferenceSystem("EPSG:5179")

        if project.crs() != target_crs:
            project.setCrs(target_crs)
            # 캔버스 범위를 영역 A로 다시 설정
            if self.area_a_extent:
                padded_extent = self.area_a_extent.buffered(self.area_a_extent.width() * 0.1)
                self.canvas.setExtent(padded_extent)
                self.canvas.refresh()
            print(f"[Controller] CRS restored to EPSG:5179")

    def show_dialog(self):
        """Show the main dialog window."""
        self.main_dialog.show()
        self.main_dialog.raise_()
        self.main_dialog.activateWindow()

    def _on_load_area_a_clicked(self):
        """Handle 'Load Area A' button click."""
        if self.area_a_loaded:
            self.main_dialog.set_status("대상영역이 이미 로드되어 있습니다", 'warning')
            return

        region_type, region_code = self.main_dialog.get_selected_region()

        if not region_code:
            self.main_dialog.set_status("행정구역을 선택하세요", 'error')
            return

        print(f"[Controller] Loading region: {region_type} = {region_code}")
        self.on_admin_selected(region_code)

    def _on_load_area_b_clicked(self):
        """Handle 'Load Area B' button click."""
        if self.area_b_loaded:
            self.main_dialog.set_status("도면영역이 이미 로드되어 있습니다", 'warning')
            return

        if self.current_bbox:
            self.load_area_b()
        else:
            self.main_dialog.set_status("먼저 도면범위를 설정하세요", 'error')

    def _on_lock_box_clicked(self, locked: bool):
        """도면 범위 잠금/해제 처리"""
        self.box_tool.set_editable(not locked)
        if locked:
            self.main_dialog.set_status("도면 범위 잠금 - 이동/크기조절 불가", 'info')
            print("[Controller] Box locked")
        else:
            self.main_dialog.set_status("도면 범위 잠금 해제", 'info')
            print("[Controller] Box unlocked")

    def on_admin_selected(self, adm_cd: str):
        """Handle administrative region selection."""
        self.selected_admin = adm_cd
        code_len = len(adm_cd)
        if code_len <= 2:
            self.main_dialog.set_status("시도 단위 로드 중... 데이터 크기가 크므로 수 분 소요될 수 있습니다", 'info')
        elif code_len <= 5:
            self.main_dialog.set_status("시군구 단위 로드 중... 처음 로드 시 수십 초 소요될 수 있습니다", 'info')
        else:
            self.main_dialog.set_status(f"읍면동 단위 로드 중... (코드: {adm_cd})", 'info')

        try:
            # v3: 프로젝트 CRS 설정
            self._setup_project_crs()

            # WFS로 행정구역 범위 조회
            extent = self.wms_manager.get_region_extent(adm_cd)

            if not extent:
                self.main_dialog.set_status(f"행정구역 범위 조회 실패: {adm_cd}", 'error')
                self.main_dialog.hide_progress()
                return

            self.area_a_extent = extent
            print(f"[Controller] Region extent: {extent.toString()}")

            # Direct GetMap으로 영역 A 레이어 로드
            layers_dict = self.wms_manager.load_area_a(adm_cd, extent)

            if layers_dict:
                # Zoom to extent
                padded_extent = extent.buffered(extent.width() * 0.1)
                self.canvas.setExtent(padded_extent)
                self.canvas.refresh()

                # Update dialog state
                self.area_a_loaded = True  # v4: 로드 상태 설정
                self.main_dialog.set_status(f'대상영역 로드 완료 - 가로도면/세로도면 버튼으로 범위 설정', 'success')
                self.main_dialog.enable_box_controls(True)  # 박스 버튼 그룹 활성화
                self.main_dialog.btn_load_area_a.setEnabled(False)  # v4: 버튼 비활성화
                # v4: 박스 없이 시작, 가로/세로 버튼으로 생성
                self.main_dialog.btn_load_area_b.setEnabled(False)
            else:
                self.main_dialog.set_status("대상영역 로드 실패 - QGIS 로그 확인", 'error')

            self.main_dialog.hide_progress()

        except Exception as e:
            self.main_dialog.set_status(f"오류: {str(e)}", 'error')
            self.main_dialog.hide_progress()
            print(f"[Controller] Exception: {str(e)}")

    def _create_initial_box(self):
        """v3: 영역 A 기반 초기 박스 생성"""
        if self.area_a_extent:
            initial_bbox = self._calculate_a0_bbox(self.area_a_extent)
            self.box_tool.set_initial_box(initial_bbox)
            self.current_bbox = initial_bbox

            # 맵 도구 활성화
            self.canvas.setMapTool(self.box_tool)

            self.main_dialog.set_status('박스 핸들로 크기 조절, 내부 드래그로 이동', 'info')

    def set_box_horizontal(self):
        """v4: 가로 A0 박스 생성 (대상영역 기준)"""
        if not self.area_a_extent:
            self.main_dialog.set_status('대상영역이 없습니다', 'error')
            return

        # v4: CRS 확인 (VWorld 등 다른 좌표계 레이어 추가 후에도 정상 동작)
        self._ensure_crs()

        new_bbox = self._calculate_a0_bbox_oriented(self.area_a_extent, horizontal=True)
        self.box_tool.set_initial_box(new_bbox)
        self.current_bbox = new_bbox
        self.canvas.setMapTool(self.box_tool)
        self.main_dialog.btn_load_area_b.setEnabled(True)
        self.main_dialog.set_status('가로도면 범위 생성됨', 'info')

    def set_box_vertical(self):
        """v4: 세로 A0 박스 생성 (대상영역 기준)"""
        if not self.area_a_extent:
            self.main_dialog.set_status('대상영역이 없습니다', 'error')
            return

        # v4: CRS 확인 (VWorld 등 다른 좌표계 레이어 추가 후에도 정상 동작)
        self._ensure_crs()

        new_bbox = self._calculate_a0_bbox_oriented(self.area_a_extent, horizontal=False)
        self.box_tool.set_initial_box(new_bbox)
        self.current_bbox = new_bbox
        self.canvas.setMapTool(self.box_tool)
        self.main_dialog.btn_load_area_b.setEnabled(True)
        self.main_dialog.set_status('세로도면 범위 생성됨', 'info')

    def on_box_deleted(self):
        """v4: 박스 삭제 처리"""
        self.current_bbox = None
        self.main_dialog.set_status('범위 삭제됨 - 가로도면/세로도면 버튼으로 다시 생성', 'info')
        self.main_dialog.btn_load_area_b.setEnabled(False)

    def reset_box(self):
        """v4: 박스 삭제 및 대상영역 상태로 복귀"""
        self.box_tool.clear()
        self.current_bbox = None
        self.area_b_loaded = False  # v4: 도면영역 상태 리셋
        self.main_dialog.btn_load_area_b.setEnabled(False)
        self.main_dialog.enable_overlay_controls(False)
        self.main_dialog.set_status('범위 삭제됨 - 가로도면/세로도면 버튼으로 다시 생성', 'info')

    def full_reset(self):
        """v4: 전체 초기화 - 모든 레이어 제거 및 처음 상태로 복귀"""
        # 1. 오버레이 제거
        if self.north_overlay:
            self.north_overlay.remove()
            self.north_overlay = None
        if self.scale_overlay:
            self.scale_overlay.remove()
            self.scale_overlay = None

        # v4.3: 외곽선 레이어 제거 (사용자가 이미 수동 삭제했을 경우 RuntimeError 방지)
        try:
            if self.outer_gradient_layer:
                QgsProject.instance().removeMapLayer(self.outer_gradient_layer.id())
        except RuntimeError:
            pass
        self.outer_gradient_layer = None

        # 2. 박스 제거
        self.box_tool.clear()
        self.current_bbox = None

        # 3. 맵 도구 해제
        if self.canvas.mapTool() == self.box_tool:
            self.canvas.unsetMapTool(self.box_tool)

        # 4. WMS 레이어 제거
        self.wms_manager.cleanup()

        # 5. 상태 변수 초기화
        self.selected_admin = None
        self.area_a_extent = None
        self.area_a_loaded = False
        self.area_b_loaded = False
        self.is_finalized = False

        # 6. UI 초기화
        self.main_dialog.reset_ui()

        self.main_dialog.set_status('전체 초기화 완료 - 처음부터 다시 시작하세요', 'success')
        print("[Controller] Full reset completed")

    def _calculate_a0_bbox(self, extent: QgsRectangle) -> QgsRectangle:
        """영역 A 범위를 A0 landscape(가로) 비율로 확장"""
        return self._calculate_a0_bbox_oriented(extent, horizontal=True)

    def _calculate_a0_bbox_oriented(self, extent: QgsRectangle, horizontal: bool = True) -> QgsRectangle:
        """
        v4: 영역 A 범위를 지정된 방향의 A0 비율로 확장

        Args:
            extent: 영역 A 범위
            horizontal: True면 가로(폭>높이), False면 세로(높이>폭)
        """
        center_x = extent.center().x()
        center_y = extent.center().y()

        extent_width = extent.width()
        extent_height = extent.height()

        if horizontal:
            # 가로 방향: 폭 > 높이 (폭 = 높이 * A0_RATIO)
            current_ratio = extent_width / extent_height if extent_height > 0 else 1
            if current_ratio >= self.A0_RATIO:
                new_width = extent_width * 1.15
                new_height = new_width / self.A0_RATIO
            else:
                new_height = extent_height * 1.15
                new_width = new_height * self.A0_RATIO
        else:
            # 세로 방향: 높이 > 폭 (높이 = 폭 * A0_RATIO)
            current_ratio = extent_height / extent_width if extent_width > 0 else 1
            if current_ratio >= self.A0_RATIO:
                new_height = extent_height * 1.15
                new_width = new_height / self.A0_RATIO
            else:
                new_width = extent_width * 1.15
                new_height = new_width * self.A0_RATIO

        return QgsRectangle(
            center_x - new_width / 2,
            center_y - new_height / 2,
            center_x + new_width / 2,
            center_y + new_height / 2
        )

    def on_box_drawn(self, bbox: QgsRectangle):
        """Handle box drawing completion."""
        self.current_bbox = bbox
        self.main_dialog.set_status('박스 그리기 완료 (A0 비율)', 'success')
        self.main_dialog.btn_load_area_b.setEnabled(True)

    def on_box_modified(self, bbox: QgsRectangle):
        """Handle box modification (move/resize)."""
        self.current_bbox = bbox
        self.main_dialog.set_status('박스 수정 완료', 'success')
        print(f"[Controller] Box modified: {bbox}")

    def add_north_arrow(self):
        """v9.2: 방위표 추가 (A0 박스 좌측 상단, position = 이미지 하단)"""
        if self.north_overlay:
            self.main_dialog.set_status('방위표가 이미 있습니다', 'warning')
            return

        image_path = os.path.join(os.path.dirname(__file__),
                                  '..', 'resources', 'north_arrow.png')

        if not os.path.exists(image_path):
            self.main_dialog.set_status('north_arrow.png 파일이 없습니다', 'error')
            return

        # v9.2: A0 박스 크기에 비례한 맵 단위 크기
        if self.current_bbox:
            # 방위표 크기: 박스 너비의 3% (맵 단위, 미터)
            width_map = self.current_bbox.width() * 0.03

            # 이미지 aspect ratio 계산 (height 미리 알기 위해)
            from qgis.PyQt.QtGui import QPixmap
            temp_pixmap = QPixmap(image_path)
            if temp_pixmap.width() > 0:
                aspect_ratio = temp_pixmap.height() / temp_pixmap.width()
            else:
                aspect_ratio = 1.0
            height_map = width_map * aspect_ratio

            # 박스 크기의 2% 오프셋 (이미지 상단이 여기에 위치)
            offset_x = self.current_bbox.width() * 0.02
            offset_y = self.current_bbox.height() * 0.02

            # position = 이미지 하단 (paint()가 position 위로 그리므로)
            # 이미지 상단 = yMax - offset, 이미지 하단 = yMax - offset - height
            position = QgsPointXY(
                self.current_bbox.xMinimum() + offset_x,
                self.current_bbox.yMaximum() - offset_y - height_map
            )
        else:
            width_map = 500.0  # 기본값 500m
            position = self.canvas.center()

        self.north_overlay = OverlayItem(self.canvas, image_path, position=position, width_map=width_map)
        self.canvas.scene().addItem(self.north_overlay)
        self.canvas.refresh()

        self.main_dialog.set_status('방위 추가됨 (드래그 이동, Delete 삭제)', 'success')

    def add_scale_bar(self):
        """v9: 축적바 추가 (방위표 아래, 맵 좌표 + 맵 단위 크기 + 고정 값 - 이미지처럼 박힘)"""
        if self.scale_overlay:
            self.main_dialog.set_status('축적바가 이미 있습니다', 'warning')
            return

        # v9.2: A0 박스 크기에 비례한 축적 계산 (항상 km 단위)
        if self.current_bbox:
            # 축적바 너비: 박스 너비의 약 5%를 기준으로 km 단위 nice value만 선택
            target_width = self.current_bbox.width() * 0.05
            # km 단위만 사용 (1km, 2km, 5km, 10km, 20km, 50km)
            nice_values_km = [1000, 2000, 5000, 10000, 20000, 50000]

            # target_width에 가장 가까운 nice value 선택 (최소 1km)
            bar_width_map = nice_values_km[0]  # 최소 1km
            for val in nice_values_km:
                if val <= target_width * 2.0:  # 여유있게 선택
                    bar_width_map = val
                else:
                    break

            # 축적 레이블 생성 (항상 km 단위)
            fixed_label = f"{bar_width_map // 1000}km"
        else:
            bar_width_map = 1000.0  # 기본값 1km
            fixed_label = "1km"

        # v9.3: 방위표 바로 아래에 배치
        # 방위표 position = 이미지 하단 (좌하단)
        # 축척바 position = 바 하단 (좌하단)
        # 축척바 상단이 방위표 하단 바로 아래에 오도록 배치
        if self.north_overlay and self.north_overlay.position:
            # 간격: 방위표 높이의 10% (0.5cm 상당의 작은 간격)
            north_height = self.north_overlay.get_height_map()
            gap_map = north_height * 0.1  # 방위표 높이의 10%

            # 축척바 전체 높이 (바 + 텍스트): bar_width의 약 17%
            scale_total_height = bar_width_map * 0.17

            # 축척바 position = 방위표 하단 - gap - 축척바 높이
            # 이렇게 하면 축척바 상단 = 방위표 하단 - gap (바로 아래!)
            position = QgsPointXY(
                self.north_overlay.position.x(),
                self.north_overlay.position.y() - gap_map - scale_total_height
            )
        else:
            # 방위표 없으면 A0 박스 좌측 상단
            if self.current_bbox:
                offset_x = self.current_bbox.width() * 0.02
                offset_y = self.current_bbox.height() * 0.05
                position = QgsPointXY(
                    self.current_bbox.xMinimum() + offset_x,
                    self.current_bbox.yMaximum() - offset_y
                )
            else:
                position = self.canvas.center()

        self.scale_overlay = ScaleBarItem(
            self.canvas,
            position=position,
            bar_width_map=bar_width_map,
            fixed_label=fixed_label,
            center_aligned=False
        )
        self.canvas.scene().addItem(self.scale_overlay)
        self.canvas.refresh()

        self.main_dialog.set_status(f'축척 추가됨 ({fixed_label} 고정, 드래그 이동)', 'success')

    def add_outer_gradient(self):
        """v4.3: 외곽 경계에 그라데이션 효과 추가 (WFS 벡터 + QML 스타일)"""
        try:
            layer_exists = bool(self.outer_gradient_layer)
        except RuntimeError:
            self.outer_gradient_layer = None
            layer_exists = False
        if layer_exists:
            self.main_dialog.set_status('경계선이 이미 있습니다', 'warning')
            return

        if not self.selected_admin:
            self.main_dialog.set_status('행정구역을 먼저 로드하세요', 'error')
            return

        self.main_dialog.set_status('경계선 로딩 중...', 'info')

        try:
            import processing
            from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry

            # 1. WFS로 벡터 데이터 로드
            wfs_url = self.wms_manager.base_url.replace('/wms', '/wfs')
            uri = (
                f"{wfs_url}?"
                f"service=WFS&version=2.0.0&request=GetFeature"
                f"&typename=hjd_emd_filter"
                f"&viewparams=REGION:{self.selected_admin}"
                f"&srsname=EPSG:5179"
            )

            wfs_layer = QgsVectorLayer(uri, "temp_hjd", "WFS")

            if not wfs_layer.isValid():
                self.main_dialog.set_status('WFS 레이어 로드 실패', 'error')
                return

            # 2. 폴리곤 병합 (dissolve)
            dissolved = processing.run("native:dissolve", {
                'INPUT': wfs_layer,
                'FIELD': [],
                'OUTPUT': 'memory:'
            })['OUTPUT']

            # 3. 외곽선 추출 (polygons to lines)
            outer_lines = processing.run("native:polygonstolines", {
                'INPUT': dissolved,
                'OUTPUT': 'memory:'
            })['OUTPUT']

            outer_lines.setName('행정구역_외곽선')

            # 4. QML 스타일 적용
            qml_path = os.path.join(os.path.dirname(__file__),
                                   '..', 'styles', 'hjd_outer_gradient.qml')

            if os.path.exists(qml_path):
                outer_lines.loadNamedStyle(qml_path)
            else:
                # QML 없으면 기본 스타일
                from qgis.core import QgsSimpleLineSymbolLayer, QgsSingleSymbolRenderer, QgsLineSymbol
                symbol = QgsLineSymbol.createSimple({
                    'color': '0,0,0,255',
                    'width': '1.0'
                })
                outer_lines.setRenderer(QgsSingleSymbolRenderer(symbol))

            # 5. 프로젝트에 추가
            QgsProject.instance().addMapLayer(outer_lines)
            self.outer_gradient_layer = outer_lines

            self.main_dialog.set_status('경계선 추가됨', 'success')
            print(f"[Controller] Outer gradient layer added")

        except Exception as e:
            self.main_dialog.set_status(f'경계선 추가 실패: {str(e)}', 'error')
            print(f"[Controller] Outer gradient error: {str(e)}")

    def remove_overlay(self, overlay):
        """v4: 오버레이 제거"""
        if overlay:
            overlay.remove()
            if overlay == self.north_overlay:
                self.north_overlay = None
                self.main_dialog.set_status('방위 삭제됨', 'info')
            elif overlay == self.scale_overlay:
                self.scale_overlay = None
                self.main_dialog.set_status('축척 삭제됨', 'info')

    def load_area_b(self):
        """도면영역 레이어 로드 (A0 박스 BBOX 기반)"""
        if not self.current_bbox:
            self.main_dialog.set_status("도면범위가 없습니다", 'error')
            return

        # v4: CRS 확인 (VWorld 등 다른 좌표계 레이어 추가 후에도 정상 동작)
        self._ensure_crs()

        self.main_dialog.set_status("도면영역 로딩 중...", 'info')

        try:
            print(f"[Controller] Area B (BBOX): {self.current_bbox.toString()}")

            layers_dict = self.wms_manager.load_area_b(self.current_bbox)

            if layers_dict:
                self.canvas.setExtent(self.current_bbox)
                self.canvas.refresh()

                self.area_b_loaded = True  # v4: 로드 상태 설정
                self.main_dialog.set_status(f'도면영역 로드 완료 - 도면요소 추가 가능', 'success')
                self.main_dialog.btn_finalize.setEnabled(True)
                self.main_dialog.btn_load_area_b.setEnabled(False)  # v4: 버튼 비활성화
                self.main_dialog.enable_overlay_controls(True)  # v4: 오버레이 버튼 활성화
                # v4: box_tool 활성화 유지 (오버레이 드래그 위해)
                self.canvas.setMapTool(self.box_tool)
            else:
                self.main_dialog.set_status("도면영역 로드 실패", 'error')

            self.main_dialog.hide_progress()

        except Exception as e:
            self.main_dialog.set_status(f"오류: {str(e)}", 'error')
            self.main_dialog.hide_progress()
            print(f"[Controller] Exception: {str(e)}")

    def finalize(self):
        """Lock box editing and finalize the workflow."""
        if not self.current_bbox:
            self.main_dialog.set_status("도면범위가 없습니다", 'error')
            return

        self.canvas.unsetMapTool(self.box_tool)
        self.box_tool.set_editable(False)

        self.is_finalized = True
        self.main_dialog.set_finalized(True)

    def export_pdf(self):
        """Trigger PDF export of the current map view."""
        if not self.is_finalized:
            self.main_dialog.set_status("먼저 작성완료 버튼을 눌러주세요", 'error')
            return

        bbox_tuple = (
            self.current_bbox.xMinimum(),
            self.current_bbox.yMinimum(),
            self.current_bbox.xMaximum(),
            self.current_bbox.yMaximum()
        )

        # v4.3: 오버레이 정보 전달
        self.export_manager.set_overlays(self.north_overlay, self.scale_overlay)
        # v4.4: A0 박스 정보 전달
        self.export_manager.set_a0_box(self.current_bbox)

        success, message = self.export_manager.export_to_pdf(bbox_tuple)

        if success:
            self.main_dialog.set_status("PDF 내보내기 완료", 'success')
        else:
            self.main_dialog.set_status(f"PDF 내보내기 실패: {message}", 'error')

    def export_image(self):
        """Trigger image export of the current map view."""
        if not self.is_finalized:
            self.main_dialog.set_status("먼저 작성완료 버튼을 눌러주세요", 'error')
            return

        bbox_tuple = (
            self.current_bbox.xMinimum(),
            self.current_bbox.yMinimum(),
            self.current_bbox.xMaximum(),
            self.current_bbox.yMaximum()
        )

        # v4.3: 오버레이 정보 전달 및 direct 방식 사용 (오버레이 렌더링 지원)
        self.export_manager.set_overlays(self.north_overlay, self.scale_overlay)
        # v4.4: A0 박스 정보 전달
        self.export_manager.set_a0_box(self.current_bbox)

        success, message = self.export_manager.export_to_image_direct(bbox_tuple)

        if success:
            self.main_dialog.set_status("이미지 내보내기 완료", 'success')
        else:
            self.main_dialog.set_status(f"이미지 내보내기 실패: {message}", 'error')

    def save_project(self):
        """Save the current QGIS project."""
        if not self.is_finalized:
            self.main_dialog.set_status("먼저 작성완료 버튼을 눌러주세요", 'error')
            return

        project_path, _ = QFileDialog.getSaveFileName(
            self.main_dialog,
            "QGIS 프로젝트 저장",
            "",
            "QGIS Project Files (*.qgs *.qgz)"
        )

        if project_path:
            success = QgsProject.instance().write(project_path)

            if success:
                self.main_dialog.set_status(f"프로젝트 저장 완료", 'success')
            else:
                self.main_dialog.set_status("프로젝트 저장 실패", 'error')

    def open_in_layout(self):
        """현재 A0 박스를 QGIS 조판관리자에 A0 크기로 자동 배치하여 열기"""
        if not self.current_bbox:
            self.main_dialog.set_status("도면 범위를 먼저 설정하세요", 'error')
            return

        try:
            from qgis.core import (
                QgsPrintLayout, QgsLayoutItemMap,
                QgsLayoutSize, QgsLayoutPoint, QgsUnitTypes,
                QgsCoordinateReferenceSystem
            )

            project = QgsProject.instance()
            manager = project.layoutManager()

            # 기존 동명 레이아웃 제거 후 재생성
            existing = manager.layoutByName("BasePlan")
            if existing:
                manager.removeLayout(existing)

            layout = QgsPrintLayout(project)
            layout.initializeDefaults()
            layout.setName("BasePlan")

            # A0 용지 크기: 가로(landscape) 1189×841mm, 세로(portrait) 841×1189mm
            bbox = self.current_bbox
            is_landscape = bbox.width() > bbox.height()
            if is_landscape:
                page_w, page_h = 1189.0, 841.0
            else:
                page_w, page_h = 841.0, 1189.0

            page_collection = layout.pageCollection()
            page = page_collection.pages()[0]
            page.setPageSize(
                QgsLayoutSize(page_w, page_h, QgsUnitTypes.LayoutMillimeters)
            )

            # 지도 항목: 여백 없이 전체 페이지 채우기
            map_item = QgsLayoutItemMap(layout)
            layout.addLayoutItem(map_item)
            map_item.attemptMove(
                QgsLayoutPoint(0, 0, QgsUnitTypes.LayoutMillimeters)
            )
            map_item.attemptResize(
                QgsLayoutSize(page_w, page_h, QgsUnitTypes.LayoutMillimeters)
            )

            # 현재 A0 박스 범위 → 지도 범위로 설정
            map_item.setExtent(bbox)
            map_item.setCrs(QgsCoordinateReferenceSystem("EPSG:5179"))

            # 레이아웃 등록 및 조판 디자이너 열기
            manager.addLayout(layout)
            designer = self.iface.openLayoutDesigner(layout)

            self.main_dialog.set_status(
                f"조판관리자 열림 - A0 {'가로' if is_landscape else '세로'} "
                f"({page_w:.0f}×{page_h:.0f}mm)", 'success'
            )
            print(f"[Controller] Layout opened: A0 {'landscape' if is_landscape else 'portrait'}, "
                  f"extent={bbox.toString()}")

        except Exception as e:
            self.main_dialog.set_status(f"조판 열기 실패: {str(e)}", 'error')
            print(f"[Controller] open_in_layout error: {str(e)}")

    def cleanup(self):
        """Cleanup resources when plugin is unloaded."""
        # v4: 오버레이 제거
        if self.north_overlay:
            self.north_overlay.remove()
            self.north_overlay = None
        if self.scale_overlay:
            self.scale_overlay.remove()
            self.scale_overlay = None

        # v4.3: 외곽선 레이어 제거
        if self.outer_gradient_layer:
            try:
                QgsProject.instance().removeMapLayer(self.outer_gradient_layer.id())
            except:
                pass
            self.outer_gradient_layer = None

        try:
            self.main_dialog.load_area_a_clicked.disconnect()
            self.main_dialog.horizontal_clicked.disconnect()
            self.main_dialog.vertical_clicked.disconnect()
            self.main_dialog.reset_box_clicked.disconnect()
            self.main_dialog.load_area_b_clicked.disconnect()
            self.main_dialog.finalize_clicked.disconnect()
            self.main_dialog.export_pdf_clicked.disconnect()
            self.main_dialog.export_image_clicked.disconnect()
            self.main_dialog.save_project_clicked.disconnect()
            self.main_dialog.add_north_clicked.disconnect()
            self.main_dialog.add_scale_clicked.disconnect()
            self.main_dialog.add_outer_clicked.disconnect()
            self.main_dialog.full_reset_clicked.disconnect()
            self.box_tool.boxDrawn.disconnect()
            self.box_tool.boxModified.disconnect()
            self.box_tool.boxDeleted.disconnect()
            self.wms_manager.progress_updated.disconnect()
        except:
            pass

        if self.canvas.mapTool() == self.box_tool:
            self.canvas.unsetMapTool(self.box_tool)

        if self.main_dialog:
            self.main_dialog.close()

        if self.wms_manager:
            self.wms_manager.cleanup()

        self.selected_admin = None
        self.current_bbox = None
        self.is_finalized = False
        self.area_a_extent = None
