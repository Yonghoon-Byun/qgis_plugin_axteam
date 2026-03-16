# -*- coding: utf-8 -*-
"""
Step 3: 현황 데이터 로드 및 전처리
2단계 범위 폴리곤의 extent → DB 공간 쿼리 → 클리핑 → 도형 수정
"""

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox, QCheckBox, QScrollArea, QProgressBar,
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer

from .styles import CARD_STYLE, PRIMARY_BUTTON_STYLE
from ..core.layer_loader import (
    AVAILABLE_LAYERS, LayerLoaderThread, transform_extent_to_db,
    detect_sigungu_code, detect_region_code,
)
from ..core.preprocessor import PreprocessTask
from ..core.style_manager import StyleManager


class Step3LoadData(QWidget):
    """데이터 로드 및 전처리 페이지 (범위 기반 공간 쿼리)"""

    def __init__(self, iface, shared_data, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.shared_data = shared_data
        self.loader_thread = None
        self.style_manager = StyleManager()
        self._loaded_raw_layers = []
        self._pending_tasks = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 안내
        guide = QLabel(
            "2단계에서 설정한 작업 범위를 기준으로\n"
            "DB에서 해당 영역의 현황 데이터를 자동으로 조회합니다."
        )
        guide.setStyleSheet("font-size: 14px; color: #6b7280;")
        guide.setWordWrap(True)
        layout.addWidget(guide)

        # 범위 정보 카드
        boundary_card = QFrame()
        boundary_card.setStyleSheet(CARD_STYLE)
        bc_layout = QVBoxLayout()
        bc_layout.setContentsMargins(16, 12, 16, 12)
        bc_layout.setSpacing(6)

        bc_title = QLabel("작업 범위")
        bc_title.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #1f2937; border: none;"
        )
        bc_layout.addWidget(bc_title)

        self.boundary_info = QLabel("범위가 설정되지 않았습니다.")
        self.boundary_info.setStyleSheet(
            "font-size: 13px; color: #6b7280; border: none;"
        )
        self.boundary_info.setWordWrap(True)
        bc_layout.addWidget(self.boundary_info)

        boundary_card.setLayout(bc_layout)
        layout.addWidget(boundary_card)

        # 레이어 선택 카드
        layer_card = self._create_layer_card()
        layout.addWidget(layer_card, 1)

        # 진행률
        self.progress_frame = QFrame()
        self.progress_frame.setVisible(False)
        progress_layout = QVBoxLayout()
        progress_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        progress_layout.addWidget(self.progress_bar)
        self.progress_label = QLabel()
        self.progress_label.setStyleSheet("font-size: 12px; color: #6b7280;")
        progress_layout.addWidget(self.progress_label)
        self.progress_frame.setLayout(progress_layout)
        layout.addWidget(self.progress_frame)

        # 로드 버튼
        self.btn_load = QPushButton("데이터 로드 및 전처리")
        self.btn_load.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.btn_load.setCursor(Qt.PointingHandCursor)
        self.btn_load.setFixedHeight(42)
        self.btn_load.clicked.connect(self._start_loading)
        layout.addWidget(self.btn_load)

        # 상태
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 13px; color: #6b7280; padding: 4px;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def _create_layer_card(self):
        card = QFrame()
        card.setStyleSheet(CARD_STYLE)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("로드할 레이어")
        title.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #1f2937; border: none;"
        )
        header.addWidget(title)
        header.addStretch()

        btn_all = QPushButton("전체선택")
        btn_all.setStyleSheet(
            "font-size: 12px; color: #6b7280; border: none; background: transparent;"
        )
        btn_all.setCursor(Qt.PointingHandCursor)
        btn_all.clicked.connect(self._select_all)
        header.addWidget(btn_all)

        btn_none = QPushButton("전체해제")
        btn_none.setStyleSheet(
            "font-size: 12px; color: #6b7280; border: none; background: transparent;"
        )
        btn_none.setCursor(Qt.PointingHandCursor)
        btn_none.clicked.connect(self._deselect_all)
        header.addWidget(btn_none)

        card_layout.addLayout(header)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(4)

        self.layer_checkboxes = []
        for layer_info in AVAILABLE_LAYERS:
            ltype = layer_info.get("layer_type", "vector")
            badge = "[R]" if ltype == "raster" else "[V]"
            cb = QCheckBox(f"{badge} {layer_info['name']}")
            cb.setChecked(True)
            cb.layer_info = layer_info
            self.layer_checkboxes.append(cb)
            scroll_layout.addWidget(cb)

        scroll_layout.addStretch()
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        card_layout.addWidget(scroll, 1)

        card.setLayout(card_layout)
        return card

    def _select_all(self):
        for cb in self.layer_checkboxes:
            cb.setChecked(True)

    def _deselect_all(self):
        for cb in self.layer_checkboxes:
            cb.setChecked(False)

    def on_enter(self):
        """페이지 진입 시 범위 정보 표시"""
        boundary = self.shared_data.get("boundary_layer")
        if boundary is not None:
            ext = boundary.extent()
            self.boundary_info.setText(
                f"레이어: {boundary.name()}\n"
                f"범위: {ext.width():.0f} x {ext.height():.0f} m\n"
                f"좌표: ({ext.xMinimum():.1f}, {ext.yMinimum():.1f}) ~ "
                f"({ext.xMaximum():.1f}, {ext.yMaximum():.1f})"
            )
            self.boundary_info.setStyleSheet(
                "font-size: 13px; color: #059669; border: none; font-weight: 600;"
            )
        else:
            self.boundary_info.setText("범위가 설정되지 않았습니다.")
            self.boundary_info.setStyleSheet(
                "font-size: 13px; color: #ef4444; border: none;"
            )

    def _start_loading(self):
        """범위 기반 데이터 로드 시작"""
        boundary = self.shared_data.get("boundary_layer")
        if boundary is None:
            QMessageBox.warning(self, "알림", "2단계에서 작업 범위를 먼저 설정해주세요.")
            return

        selected = [cb.layer_info for cb in self.layer_checkboxes if cb.isChecked()]
        if not selected:
            QMessageBox.warning(self, "알림", "로드할 레이어를 선택해주세요.")
            return

        # 범위를 DB CRS(5179)로 변환
        project_crs = QgsProject.instance().crs()
        extent = boundary.extent()
        extent_5179 = transform_extent_to_db(extent, project_crs)

        # 메인 스레드에서 행정구역 코드 감지 (스레드 안전)
        self.status_label.setText("행정구역 자동 감지 중...")
        region_code = detect_sigungu_code(extent_5179) or detect_region_code(extent_5179)
        if region_code is None:
            QMessageBox.warning(
                self, "알림",
                "범위에 해당하는 행정구역을 찾을 수 없습니다.\nDB 연결을 확인해주세요.",
            )
            return

        self.boundary_info.setText(
            self.boundary_info.text() + f"\n감지된 행정구역 코드: {region_code}"
        )

        self.btn_load.setEnabled(False)
        self.progress_frame.setVisible(True)
        self._loaded_raw_layers = []
        self._pending_tasks = 0

        self._cleanup_thread()
        self.loader_thread = LayerLoaderThread(selected, region_code)
        self.loader_thread.progress_changed.connect(self._on_progress)
        self.loader_thread.uri_ready.connect(self._on_uri_ready)
        self.loader_thread.error_occurred.connect(self._on_error)
        self.loader_thread.all_completed.connect(self._on_all_completed)
        self.loader_thread.start()

    def _cleanup_thread(self):
        """스레드 정리"""
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.cancel()
            self.loader_thread.wait(5000)

    def _on_progress(self, pct, msg):
        self.progress_bar.setValue(pct)
        self.progress_label.setText(msg)

    def _on_uri_ready(self, uri_str, name, layer_type, provider):
        """URI 수신 → 메인 스레드에서 레이어 생성 → QgsTask로 비동기 전처리"""
        # 취소된 스레드의 잔여 시그널 무시
        if self.loader_thread and self.loader_thread._is_cancelled:
            return

        if layer_type == "raster":
            layer = QgsRasterLayer(uri_str, name, provider)
        else:
            layer = QgsVectorLayer(uri_str, name, provider)

        if not layer.isValid():
            self.status_label.setText(f"로드 실패: {name}")
            self.status_label.setStyleSheet("font-size: 13px; color: #ef4444; padding: 4px;")
            return

        boundary = self.shared_data.get("boundary_layer")
        if boundary is None or not boundary.isValid():
            # 범위 레이어가 삭제된 경우 원본 그대로 추가
            QgsProject.instance().addMapLayer(layer)
            self._loaded_raw_layers.append(layer)
            return

        # QgsTask로 비동기 전처리 (UI 프리징 방지)
        self._pending_tasks += 1
        task = PreprocessTask(
            layer, boundary, name,
            style_callback=self._apply_style_callback,
        )
        task.taskCompleted.connect(lambda: self._on_task_finished(task, name, True))
        task.taskTerminated.connect(lambda: self._on_task_finished(task, name, False))

        from qgis.core import QgsApplication
        QgsApplication.taskManager().addTask(task)
        self.status_label.setText(f"전처리 중: {name}")

    def _apply_style_callback(self, layer, name):
        """PreprocessTask.finished()에서 호출되는 스타일 콜백"""
        self.style_manager.apply_style_to_layer(layer, name)

    def _on_task_finished(self, task, name, success):
        """PreprocessTask 완료 시 호출"""
        self._pending_tasks -= 1
        if success and task.result_layer:
            self._loaded_raw_layers.append(task.result_layer)
            self.status_label.setText(f"전처리 완료: {name}")
            self.status_label.setStyleSheet("font-size: 13px; color: #059669; padding: 4px;")
        else:
            self.status_label.setText(f"전처리 실패: {name}")
            self.status_label.setStyleSheet("font-size: 13px; color: #ef4444; padding: 4px;")

        # 모든 태스크 완료 시
        if self._pending_tasks <= 0:
            self.shared_data["loaded_layers"] = self._loaded_raw_layers
            count = len(self._loaded_raw_layers)
            self.status_label.setText(f"전체 완료: {count}개 레이어 로드 및 전처리됨")
            self.status_label.setStyleSheet(
                "font-size: 13px; color: #059669; padding: 4px; font-weight: 600;"
            )
            self.iface.mapCanvas().refresh()

    def _on_error(self, msg):
        self.status_label.setText(f"오류: {msg}")
        self.status_label.setStyleSheet("font-size: 13px; color: #ef4444; padding: 4px;")

    def _on_all_completed(self):
        """URI 준비 스레드 완료 (전처리 태스크는 아직 실행 중일 수 있음)"""
        self.btn_load.setEnabled(True)
        self.progress_frame.setVisible(False)
        if self._pending_tasks > 0:
            self.status_label.setText(f"전처리 진행 중... ({self._pending_tasks}개 남음)")
        else:
            self.shared_data["loaded_layers"] = self._loaded_raw_layers
            count = len(self._loaded_raw_layers)
            self.status_label.setText(f"전체 완료: {count}개 레이어")

    def execute_step(self):
        if not self.shared_data.get("loaded_layers"):
            QMessageBox.warning(self, "알림", "데이터를 먼저 로드해주세요.")
            return False
        return True
