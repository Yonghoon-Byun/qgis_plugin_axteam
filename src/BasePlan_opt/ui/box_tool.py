# -*- coding: utf-8 -*-
"""
Box drawing map tool for WMSPlanViewer plugin v4.
A0 비율 고정 박스 그리기, 이동, 크기 조절 기능.

v4 변경:
- 항상 편집 가능 상태 (별도 편집 모드 불필요)
- 가로/세로 방향 전환 메서드 추가
- Delete 키로 박스 삭제
- 새 박스 그리기 모드 제거

v3 기능 유지:
- 8개 핸들 시스템 (코너 4개 + 변 4개)
- A0 비율 자동 유지하며 크기 조절
- 박스 외부 클릭해도 박스 유지
- 커서 변경 (핸들별)
"""

import math

from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtGui import QColor, QCursor
from qgis.core import QgsPointXY, QgsRectangle, QgsWkbTypes, QgsGeometry
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand


class BoxMapTool(QgsMapToolEmitPoint):
    """
    Map tool for drawing and editing A0 ratio bounding boxes.

    v3 Features:
    - 8 handles for resizing (4 corners + 4 edges)
    - A0 ratio (1.414:1) maintained during resize
    - Box persists when clicking outside
    - Cursor changes based on handle
    """

    # A0 landscape 비율 (가로:세로 = √2:1 ≈ 1.414:1)
    A0_RATIO = 1.41421356

    # Handle types
    HANDLE_NONE = 0
    HANDLE_CORNER_TL = 1  # Top-Left
    HANDLE_CORNER_TR = 2  # Top-Right
    HANDLE_CORNER_BL = 3  # Bottom-Left
    HANDLE_CORNER_BR = 4  # Bottom-Right
    HANDLE_EDGE_T = 5     # Top
    HANDLE_EDGE_B = 6     # Bottom
    HANDLE_EDGE_L = 7     # Left
    HANDLE_EDGE_R = 8     # Right
    HANDLE_MOVE = 9       # Inside (move)

    # Signals
    boxDrawn = pyqtSignal(QgsRectangle)
    boxModified = pyqtSignal(QgsRectangle)
    boxDeleted = pyqtSignal()  # v4: 박스 삭제 신호

    def __init__(self, canvas, controller=None):
        """
        Initialize the box map tool.

        Args:
            canvas: QgsMapCanvas instance
            controller: PlanMapController (for overlay access)
        """
        super().__init__(canvas)
        self.canvas = canvas
        self.controller = controller  # v4: 오버레이 접근용
        self.rubberBand = None
        self.handleBands = []  # 핸들 표시용 러버밴드
        self.startPoint = None
        self.endPoint = None
        self.is_editable = True
        self.current_bbox = None
        self.isDrawing = False
        self.draw_mode = False  # 새 박스 그리기 모드 (v4에서 미사용)

        # 핸들/이동 상태
        self.active_handle = self.HANDLE_NONE
        self.isMoving = False
        self.isResizing = False
        self.moveStartPoint = None
        self.resizeAnchor = None  # 크기 조절 시 고정점
        self.hasInitialBox = False

        # v4: 오버레이 드래그 상태
        self.dragging_overlay = None

        # v4.4: 박스 선택 상태 (핸들 표시 여부)
        self.is_box_selected = False

        # 핸들 크기 (픽셀)
        self.handle_size = 8

    def set_editable(self, editable):
        """
        Enable or disable editing of the box.
        잠금 시: 파란색 파선으로 표시 / 잠금 해제 시: 검정 실선으로 복원

        Args:
            editable (bool): True to enable editing, False to disable (lock)
        """
        self.is_editable = editable
        if self.rubberBand:
            if editable:
                # 잠금 해제: 검정 실선
                self.rubberBand.setStrokeColor(QColor(0, 0, 0, 255))
                self.rubberBand.setLineStyle(Qt.SolidLine)
            else:
                # 잠금: 파란색 파선
                self.rubberBand.setStrokeColor(QColor(37, 99, 235, 255))
                self.rubberBand.setLineStyle(Qt.DashLine)
        self._update_handles()

    def set_draw_mode(self, enabled):
        """
        v3: 새 박스 그리기 모드 설정

        Args:
            enabled (bool): True면 새 박스 그리기 모드
        """
        self.draw_mode = enabled
        if enabled:
            self.canvas.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.canvas.setCursor(Qt.CursorShape.ArrowCursor)

    def clear(self):
        """Remove the rubber band and handles from the canvas."""
        if self.rubberBand:
            self.canvas.scene().removeItem(self.rubberBand)
            self.rubberBand = None

        for hb in self.handleBands:
            self.canvas.scene().removeItem(hb)
        self.handleBands.clear()

        self.startPoint = None
        self.endPoint = None
        self.current_bbox = None
        self.isDrawing = False
        self.isMoving = False
        self.isResizing = False
        self.hasInitialBox = False
        self.draw_mode = False

    def get_bbox(self):
        """Get the current bounding box rectangle."""
        return self.current_bbox

    def set_initial_box(self, bbox: QgsRectangle):
        """
        v4: 초기 박스 설정 - 항상 편집 가능

        Args:
            bbox: 초기 박스 범위
        """
        if self.rubberBand:
            self.canvas.scene().removeItem(self.rubberBand)

        # 새 러버밴드 생성
        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setStrokeColor(QColor(0, 0, 0, 255))
        self.rubberBand.setFillColor(QColor(0, 0, 0, 0))
        self.rubberBand.setWidth(2)

        self.current_bbox = bbox
        self.hasInitialBox = True
        self.is_editable = True   # v4: 항상 편집 가능
        self.draw_mode = False    # v4: 그리기 모드 OFF
        self.is_box_selected = True  # v4.4: 초기 박스 설정 시 선택 상태
        self._drawBbox(bbox)
        self._update_handles()

        print(f"[BoxTool] Initial box set: {bbox}")

    def reset_to_extent(self, extent: QgsRectangle):
        """
        v3: 주어진 범위로 박스 초기화

        Args:
            extent: 초기화할 범위
        """
        initial_bbox = self._calculate_a0_from_extent(extent)
        self.set_initial_box(initial_bbox)
        self.boxModified.emit(initial_bbox)

    def _calculate_a0_from_extent(self, extent: QgsRectangle) -> QgsRectangle:
        """영역을 A0 비율로 확장"""
        center_x = extent.center().x()
        center_y = extent.center().y()

        extent_width = extent.width()
        extent_height = extent.height()

        current_ratio = extent_width / extent_height if extent_height > 0 else 1

        if current_ratio >= self.A0_RATIO:
            new_width = extent_width * 1.15
            new_height = new_width / self.A0_RATIO
        else:
            new_height = extent_height * 1.15
            new_width = new_height * self.A0_RATIO

        return QgsRectangle(
            center_x - new_width / 2,
            center_y - new_height / 2,
            center_x + new_width / 2,
            center_y + new_height / 2
        )

    def _drawBbox(self, bbox: QgsRectangle):
        """박스를 러버밴드에 그리기"""
        if not self.rubberBand:
            return

        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        self.rubberBand.addPoint(QgsPointXY(bbox.xMinimum(), bbox.yMinimum()), False)
        self.rubberBand.addPoint(QgsPointXY(bbox.xMaximum(), bbox.yMinimum()), False)
        self.rubberBand.addPoint(QgsPointXY(bbox.xMaximum(), bbox.yMaximum()), False)
        self.rubberBand.addPoint(QgsPointXY(bbox.xMinimum(), bbox.yMaximum()), True)
        self.rubberBand.show()

    def _update_handles(self):
        """v3: 핸들 위치 업데이트 (v4.4: 선택 시에만 표시)"""
        # 기존 핸들 제거
        for hb in self.handleBands:
            self.canvas.scene().removeItem(hb)
        self.handleBands.clear()

        # v4.4: 선택되지 않았으면 핸들 표시 안 함
        if not self.current_bbox or not self.is_editable or not self.is_box_selected:
            return

        # 8개 핸들 위치 계산
        bbox = self.current_bbox
        handle_positions = [
            (bbox.xMinimum(), bbox.yMaximum()),  # TL
            (bbox.xMaximum(), bbox.yMaximum()),  # TR
            (bbox.xMinimum(), bbox.yMinimum()),  # BL
            (bbox.xMaximum(), bbox.yMinimum()),  # BR
            (bbox.center().x(), bbox.yMaximum()),  # T
            (bbox.center().x(), bbox.yMinimum()),  # B
            (bbox.xMinimum(), bbox.center().y()),  # L
            (bbox.xMaximum(), bbox.center().y()),  # R
        ]

        # 핸들 러버밴드 생성
        for x, y in handle_positions:
            hb = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
            hb.setStrokeColor(QColor(0, 0, 0, 255))
            hb.setFillColor(QColor(255, 255, 255, 200))
            hb.setWidth(1)

            # 핸들 크기 (맵 좌표로 변환)
            pixel_size = self.canvas.mapUnitsPerPixel() * self.handle_size
            hb.addPoint(QgsPointXY(x - pixel_size, y - pixel_size), False)
            hb.addPoint(QgsPointXY(x + pixel_size, y - pixel_size), False)
            hb.addPoint(QgsPointXY(x + pixel_size, y + pixel_size), False)
            hb.addPoint(QgsPointXY(x - pixel_size, y + pixel_size), True)
            hb.show()

            self.handleBands.append(hb)

    def _detect_handle(self, point: QgsPointXY) -> int:
        """
        v3: 마우스 위치로 어떤 핸들인지 판별

        Args:
            point: 맵 좌표

        Returns:
            핸들 타입 (HANDLE_*)
        """
        if not self.current_bbox:
            return self.HANDLE_NONE

        bbox = self.current_bbox
        tolerance = self.canvas.mapUnitsPerPixel() * self.handle_size * 1.5

        # 코너 체크
        corners = [
            (bbox.xMinimum(), bbox.yMaximum(), self.HANDLE_CORNER_TL),
            (bbox.xMaximum(), bbox.yMaximum(), self.HANDLE_CORNER_TR),
            (bbox.xMinimum(), bbox.yMinimum(), self.HANDLE_CORNER_BL),
            (bbox.xMaximum(), bbox.yMinimum(), self.HANDLE_CORNER_BR),
        ]

        for x, y, handle_type in corners:
            if abs(point.x() - x) < tolerance and abs(point.y() - y) < tolerance:
                return handle_type

        # 변 체크
        edges = [
            (bbox.center().x(), bbox.yMaximum(), self.HANDLE_EDGE_T),
            (bbox.center().x(), bbox.yMinimum(), self.HANDLE_EDGE_B),
            (bbox.xMinimum(), bbox.center().y(), self.HANDLE_EDGE_L),
            (bbox.xMaximum(), bbox.center().y(), self.HANDLE_EDGE_R),
        ]

        for x, y, handle_type in edges:
            if abs(point.x() - x) < tolerance and abs(point.y() - y) < tolerance:
                return handle_type

        # 내부 체크
        if bbox.contains(point):
            return self.HANDLE_MOVE

        return self.HANDLE_NONE

    def _set_cursor_for_handle(self, handle: int):
        """v3: 핸들별 커서 변경"""
        cursors = {
            self.HANDLE_NONE: Qt.CursorShape.ArrowCursor,
            self.HANDLE_CORNER_TL: Qt.CursorShape.SizeFDiagCursor,
            self.HANDLE_CORNER_BR: Qt.CursorShape.SizeFDiagCursor,
            self.HANDLE_CORNER_TR: Qt.CursorShape.SizeBDiagCursor,
            self.HANDLE_CORNER_BL: Qt.CursorShape.SizeBDiagCursor,
            self.HANDLE_EDGE_T: Qt.CursorShape.SizeVerCursor,
            self.HANDLE_EDGE_B: Qt.CursorShape.SizeVerCursor,
            self.HANDLE_EDGE_L: Qt.CursorShape.SizeHorCursor,
            self.HANDLE_EDGE_R: Qt.CursorShape.SizeHorCursor,
            self.HANDLE_MOVE: Qt.CursorShape.SizeAllCursor,
        }

        cursor = cursors.get(handle, Qt.CursorShape.ArrowCursor)
        self.canvas.setCursor(cursor)

    def _get_resize_anchor(self, handle: int) -> QgsPointXY:
        """v3: 크기 조절 시 고정점 반환"""
        if not self.current_bbox:
            return None

        bbox = self.current_bbox
        anchors = {
            self.HANDLE_CORNER_TL: QgsPointXY(bbox.xMaximum(), bbox.yMinimum()),
            self.HANDLE_CORNER_TR: QgsPointXY(bbox.xMinimum(), bbox.yMinimum()),
            self.HANDLE_CORNER_BL: QgsPointXY(bbox.xMaximum(), bbox.yMaximum()),
            self.HANDLE_CORNER_BR: QgsPointXY(bbox.xMinimum(), bbox.yMaximum()),
            self.HANDLE_EDGE_T: QgsPointXY(bbox.center().x(), bbox.yMinimum()),
            self.HANDLE_EDGE_B: QgsPointXY(bbox.center().x(), bbox.yMaximum()),
            self.HANDLE_EDGE_L: QgsPointXY(bbox.xMaximum(), bbox.center().y()),
            self.HANDLE_EDGE_R: QgsPointXY(bbox.xMinimum(), bbox.center().y()),
        }

        return anchors.get(handle)

    def canvasPressEvent(self, event):
        """Handle mouse press event on canvas."""
        if not self.is_editable:
            return

        if event.button() == Qt.LeftButton:
            point = self.toMapCoordinates(event.pos())
            screen_point = event.pos()

            # v4: 오버레이 클릭 체크 (먼저)
            if self.controller:
                # 기존 선택 해제
                if self.controller.north_overlay:
                    self.controller.north_overlay.deselect()
                if self.controller.scale_overlay:
                    self.controller.scale_overlay.deselect()

                # 방위표 클릭 체크
                if self.controller.north_overlay:
                    from qgis.PyQt.QtCore import QPointF
                    if self.controller.north_overlay.contains_point(QPointF(screen_point.x(), screen_point.y())):
                        self.controller.north_overlay.start_drag(QPointF(screen_point.x(), screen_point.y()))
                        self.dragging_overlay = self.controller.north_overlay
                        return

                # 축적바 클릭 체크
                if self.controller.scale_overlay:
                    from qgis.PyQt.QtCore import QPointF
                    if self.controller.scale_overlay.contains_point(QPointF(screen_point.x(), screen_point.y())):
                        self.controller.scale_overlay.start_drag(QPointF(screen_point.x(), screen_point.y()))
                        self.dragging_overlay = self.controller.scale_overlay
                        return

            # 새 박스 그리기 모드 (v4에서는 사용 안 함)
            if self.draw_mode:
                self._start_drawing(point)
                return

            # 핸들 감지
            handle = self._detect_handle(point)

            if handle == self.HANDLE_MOVE:
                # v4.4: 박스 선택 및 이동 모드
                self.is_box_selected = True
                self._update_handles()
                self.isMoving = True
                self.moveStartPoint = point
                print(f"[BoxTool] Box selected, move mode started")

            elif handle != self.HANDLE_NONE:
                # v4.4: 핸들 클릭 시 선택 상태 유지
                self.is_box_selected = True
                self._update_handles()
                # 크기 조절 모드
                self.isResizing = True
                self.active_handle = handle
                self.resizeAnchor = self._get_resize_anchor(handle)
                print(f"[BoxTool] Resize mode started: handle={handle}")

            else:
                # v4.4: 박스 외부 클릭 시 - 선택 해제, 핸들 숨김
                if self.is_box_selected:
                    self.is_box_selected = False
                    self._update_handles()
                    print(f"[BoxTool] Box deselected")

    def _start_drawing(self, point: QgsPointXY):
        """새 박스 그리기 시작"""
        self.startPoint = point
        self.endPoint = self.startPoint
        self.isDrawing = True
        self.hasInitialBox = False

        if self.rubberBand:
            self.canvas.scene().removeItem(self.rubberBand)

        for hb in self.handleBands:
            self.canvas.scene().removeItem(hb)
        self.handleBands.clear()

        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setStrokeColor(QColor(0, 0, 0, 255))
        self.rubberBand.setFillColor(QColor(0, 0, 0, 0))
        self.rubberBand.setWidth(2)

    def canvasMoveEvent(self, event):
        """Handle mouse move event on canvas."""
        point = self.toMapCoordinates(event.pos())
        screen_point = event.pos()

        # v4: 오버레이 드래그
        if self.dragging_overlay:
            from qgis.PyQt.QtCore import QPointF
            self.dragging_overlay.update_drag(QPointF(screen_point.x(), screen_point.y()))
            self.canvas.refresh()
            return

        # 이동 모드
        if self.isMoving and self.moveStartPoint and self.current_bbox:
            dx = point.x() - self.moveStartPoint.x()
            dy = point.y() - self.moveStartPoint.y()

            new_bbox = QgsRectangle(
                self.current_bbox.xMinimum() + dx,
                self.current_bbox.yMinimum() + dy,
                self.current_bbox.xMaximum() + dx,
                self.current_bbox.yMaximum() + dy
            )
            self.current_bbox = new_bbox
            self.moveStartPoint = point
            self._drawBbox(new_bbox)
            self._update_handles()
            return

        # 크기 조절 모드
        if self.isResizing and self.resizeAnchor:
            new_bbox = self._resize_with_a0_ratio(self.active_handle, point)
            if new_bbox:
                self.current_bbox = new_bbox
                self._drawBbox(new_bbox)
                self._update_handles()
            return

        # 그리기 모드
        if self.isDrawing and self.startPoint:
            self.endPoint = point
            self._updateRubberBand()
            return

        # 호버 시 커서 변경
        if self.is_editable and self.current_bbox and not self.draw_mode:
            handle = self._detect_handle(point)
            self._set_cursor_for_handle(handle)

    def _is_horizontal(self) -> bool:
        """v4: 현재 박스가 가로 방향인지 확인"""
        if not self.current_bbox:
            return True
        return self.current_bbox.width() > self.current_bbox.height()

    def _resize_with_a0_ratio(self, handle: int, new_point: QgsPointXY) -> QgsRectangle:
        """
        v4: A0 비율 유지하며 크기 조절 (현재 방향 유지)

        Args:
            handle: 활성 핸들 타입
            new_point: 새 마우스 위치

        Returns:
            새 bbox (A0 비율 유지, 현재 방향 유지)
        """
        if not self.resizeAnchor:
            return None

        anchor = self.resizeAnchor
        is_horizontal = self._is_horizontal()

        # 코너 핸들: 대각선 방향으로 크기 조절
        if handle in [self.HANDLE_CORNER_TL, self.HANDLE_CORNER_TR,
                      self.HANDLE_CORNER_BL, self.HANDLE_CORNER_BR]:

            dx = abs(new_point.x() - anchor.x())
            dy = abs(new_point.y() - anchor.y())

            # v4: 현재 방향 유지하면서 A0 비율 계산
            if is_horizontal:
                # 가로 방향: 폭 > 높이
                if dx / self.A0_RATIO > dy:
                    new_width = dx
                    new_height = dx / self.A0_RATIO
                else:
                    new_height = dy
                    new_width = dy * self.A0_RATIO
            else:
                # 세로 방향: 높이 > 폭
                if dy / self.A0_RATIO > dx:
                    new_height = dy
                    new_width = dy / self.A0_RATIO
                else:
                    new_width = dx
                    new_height = dx * self.A0_RATIO

            # 방향 결정
            if handle == self.HANDLE_CORNER_TL:
                return QgsRectangle(
                    anchor.x() - new_width,
                    anchor.y(),
                    anchor.x(),
                    anchor.y() + new_height
                )
            elif handle == self.HANDLE_CORNER_TR:
                return QgsRectangle(
                    anchor.x(),
                    anchor.y(),
                    anchor.x() + new_width,
                    anchor.y() + new_height
                )
            elif handle == self.HANDLE_CORNER_BL:
                return QgsRectangle(
                    anchor.x() - new_width,
                    anchor.y() - new_height,
                    anchor.x(),
                    anchor.y()
                )
            elif handle == self.HANDLE_CORNER_BR:
                return QgsRectangle(
                    anchor.x(),
                    anchor.y() - new_height,
                    anchor.x() + new_width,
                    anchor.y()
                )

        # 변 핸들: 한 방향으로 크기 조절 (A0 비율 유지, 현재 방향 유지)
        elif handle in [self.HANDLE_EDGE_L, self.HANDLE_EDGE_R]:
            # 좌/우: 너비 변경 → 높이 자동 조절
            new_width = abs(new_point.x() - anchor.x())
            if is_horizontal:
                new_height = new_width / self.A0_RATIO  # 가로: 폭 > 높이
            else:
                new_height = new_width * self.A0_RATIO  # 세로: 높이 > 폭
            center_y = self.current_bbox.center().y()

            if handle == self.HANDLE_EDGE_L:
                return QgsRectangle(
                    anchor.x() - new_width,
                    center_y - new_height / 2,
                    anchor.x(),
                    center_y + new_height / 2
                )
            else:
                return QgsRectangle(
                    anchor.x(),
                    center_y - new_height / 2,
                    anchor.x() + new_width,
                    center_y + new_height / 2
                )

        elif handle in [self.HANDLE_EDGE_T, self.HANDLE_EDGE_B]:
            # 상/하: 높이 변경 → 너비 자동 조절
            new_height = abs(new_point.y() - anchor.y())
            if is_horizontal:
                new_width = new_height * self.A0_RATIO  # 가로: 폭 > 높이
            else:
                new_width = new_height / self.A0_RATIO  # 세로: 높이 > 폭
            center_x = self.current_bbox.center().x()

            if handle == self.HANDLE_EDGE_B:
                return QgsRectangle(
                    center_x - new_width / 2,
                    anchor.y() - new_height,
                    center_x + new_width / 2,
                    anchor.y()
                )
            else:
                return QgsRectangle(
                    center_x - new_width / 2,
                    anchor.y(),
                    center_x + new_width / 2,
                    anchor.y() + new_height
                )

        return None

    def canvasReleaseEvent(self, event):
        """Handle mouse release event on canvas."""
        if event.button() != Qt.LeftButton:
            return

        # v4: 오버레이 드래그 종료
        if self.dragging_overlay:
            self.dragging_overlay.end_drag()
            self.dragging_overlay = None
            self.canvas.refresh()
            return

        # 이동 완료
        if self.isMoving:
            self.isMoving = False
            self.moveStartPoint = None
            self._update_handles()
            self.boxModified.emit(self.current_bbox)
            print(f"[BoxTool] Box moved to: {self.current_bbox}")
            return

        # 크기 조절 완료
        if self.isResizing:
            self.isResizing = False
            self.active_handle = self.HANDLE_NONE
            self.resizeAnchor = None
            self._update_handles()
            self.boxModified.emit(self.current_bbox)
            print(f"[BoxTool] Box resized to: {self.current_bbox}")
            return

        # 그리기 완료
        if self.isDrawing:
            self.endPoint = self.toMapCoordinates(event.pos())
            self.isDrawing = False
            self.draw_mode = False

            if self.startPoint and self.endPoint:
                self.current_bbox = self._calculateA0Bbox(self.startPoint, self.endPoint)
                self._drawBbox(self.current_bbox)
                self._update_handles()
                self.hasInitialBox = True

                self.boxDrawn.emit(self.current_bbox)
                print(f"[BoxTool] Box drawn: {self.current_bbox}")

    def _calculateA0Bbox(self, start: QgsPointXY, end: QgsPointXY) -> QgsRectangle:
        """A0 landscape 비율로 박스 계산"""
        dx = end.x() - start.x()
        dy = end.y() - start.y()

        width = abs(dx)
        height = width / self.A0_RATIO

        sign_x = 1 if dx >= 0 else -1
        sign_y = 1 if dy >= 0 else -1

        adjusted_end = QgsPointXY(
            start.x() + (width * sign_x),
            start.y() + (height * sign_y)
        )

        return QgsRectangle(start, adjusted_end)

    def _updateRubberBand(self):
        """Update the rubber band geometry."""
        if not self.rubberBand or not self.startPoint or not self.endPoint:
            return

        rect = self._calculateA0Bbox(self.startPoint, self.endPoint)
        self._drawBbox(rect)

    def clear_box(self):
        """v4: 박스 삭제"""
        self.current_bbox = None
        if self.rubberBand:
            self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        self._clear_handles()
        self.canvas.refresh()

    def _clear_handles(self):
        """핸들 모두 제거"""
        for hb in self.handleBands:
            self.canvas.scene().removeItem(hb)
        self.handleBands.clear()

    def set_orientation(self, horizontal: bool):
        """
        v4: A0 박스 방향 전환 (가로/세로)

        Args:
            horizontal: True면 가로 (폭 > 높이), False면 세로 (높이 > 폭)
        """
        if not self.current_bbox:
            return

        center = self.current_bbox.center()
        current_area = self.current_bbox.width() * self.current_bbox.height()

        if horizontal:
            # 가로: 폭 > 높이 (폭 = 높이 * A0_RATIO)
            new_height = math.sqrt(current_area / self.A0_RATIO)
            new_width = new_height * self.A0_RATIO
        else:
            # 세로: 높이 > 폭 (높이 = 폭 * A0_RATIO)
            new_width = math.sqrt(current_area / self.A0_RATIO)
            new_height = new_width * self.A0_RATIO

        new_bbox = QgsRectangle(
            center.x() - new_width / 2,
            center.y() - new_height / 2,
            center.x() + new_width / 2,
            center.y() + new_height / 2
        )

        self.current_bbox = new_bbox
        self._drawBbox(new_bbox)
        self._update_handles()
        self.boxModified.emit(new_bbox)

    def keyPressEvent(self, event):
        """v4: 키보드 이벤트 처리 - Delete로 오버레이/박스 삭제"""
        if event.key() == Qt.Key_Delete:
            # 선택된 오버레이 먼저 삭제
            if self.controller:
                if self.controller.north_overlay and self.controller.north_overlay.is_selected:
                    self.controller.remove_overlay(self.controller.north_overlay)
                    print("[BoxTool] North arrow deleted via Delete key")
                    return
                if self.controller.scale_overlay and self.controller.scale_overlay.is_selected:
                    self.controller.remove_overlay(self.controller.scale_overlay)
                    print("[BoxTool] Scale bar deleted via Delete key")
                    return

            # 박스 삭제
            if self.current_bbox:
                self.clear_box()
                self.boxDeleted.emit()
                print("[BoxTool] Box deleted via Delete key")
        else:
            super().keyPressEvent(event)

    def deactivate(self):
        """Called when the map tool is deactivated."""
        super().deactivate()
        # 박스 유지, 핸들만 숨김
        for hb in self.handleBands:
            hb.hide()

    def activate(self):
        """Called when the map tool is activated."""
        super().activate()
        # 핸들 다시 표시
        self._update_handles()
        for hb in self.handleBands:
            hb.show()
