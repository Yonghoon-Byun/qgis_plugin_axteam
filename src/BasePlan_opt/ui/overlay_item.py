# -*- coding: utf-8 -*-
"""
이동 가능한 이미지/축적 오버레이 아이템 v9.1

방위표: A0 박스 내부에 "이미지처럼 박힌" 상태
축적: 방위표 아래에 "이미지처럼 박힌" 상태

v9.1: 맵 좌표 저장 + 화면 좌표 렌더링
    - 위치: 맵 좌표 (QgsPointXY) 저장
    - 크기: 맵 단위 (미터) 저장
    - paint()에서 toCanvasCoordinates()로 화면 좌표 변환 후 그리기
    - 축척바 값: 생성 시 고정 (확대/축소해도 변하지 않음)
"""

from qgis.PyQt.QtCore import Qt, QRectF, QPointF
from qgis.PyQt.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QFont, QImage
from qgis.gui import QgsMapCanvasItem
from qgis.core import QgsPointXY


class OverlayItem(QgsMapCanvasItem):
    """A0 박스 내부에 이미지처럼 박힌 오버레이 (맵 좌표 저장, 화면 좌표 렌더링)"""

    def __init__(self, canvas, image_path: str, position: QgsPointXY = None, width_map: float = 500.0):
        """
        Args:
            canvas: QgsMapCanvas
            image_path: 이미지 파일 경로
            position: 맵 좌표 위치 (QgsPointXY) - A0 박스 내부 좌표
            width_map: 이미지 너비 (맵 단위, 미터) - 확대하면 커보임
        """
        super().__init__(canvas)
        self.canvas = canvas
        self.pixmap = QPixmap(image_path)
        self.position = position  # 맵 좌표 (A0 박스 기준)
        self.width_map = width_map  # 맵 단위 너비 (미터)
        self.is_dragging = False
        self.drag_offset = QPointF(0, 0)
        self.is_selected = False
        self.setZValue(1000)

        # 종횡비 계산
        if self.pixmap.width() > 0:
            self.aspect_ratio = self.pixmap.height() / self.pixmap.width()
        else:
            self.aspect_ratio = 1.0

        # 높이 계산 (맵 단위)
        self.height_map = self.width_map * self.aspect_ratio

    def paint(self, painter, option, widget):
        if not self.pixmap or not self.position:
            return

        # 맵 좌표 → 화면 좌표 변환
        screen_pos = self.toCanvasCoordinates(self.position)

        # 맵 단위 크기 → 픽셀 크기 변환
        mupp = self.canvas.mapUnitsPerPixel()
        if mupp > 0:
            pixel_width = int(self.width_map / mupp)
            pixel_height = int(self.height_map / mupp)
        else:
            pixel_width = 80
            pixel_height = int(80 * self.aspect_ratio)

        # 최소 크기 보장
        pixel_width = max(10, pixel_width)
        pixel_height = max(10, pixel_height)

        # 화면 좌표에서 그리기 (Y축: 맵은 위로 증가, 화면은 아래로 증가)
        x = int(screen_pos.x())
        y = int(screen_pos.y()) - pixel_height  # position이 좌하단이므로 위로 올림

        # painter 변환 초기화 (화면 좌표로 직접 그리기)
        painter.save()
        painter.resetTransform()

        # 이미지 스케일 및 그리기
        scaled_pixmap = self.pixmap.scaled(
            pixel_width, pixel_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        painter.drawPixmap(x, y, scaled_pixmap)

        # 선택 시 테두리 표시
        if self.is_selected:
            pen_width = max(1, int(pixel_width * 0.02))
            painter.setPen(QPen(QColor(0, 120, 215), pen_width, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            margin = max(2, int(pixel_width * 0.02))
            painter.drawRect(x - margin, y - margin,
                             pixel_width + margin * 2, pixel_height + margin * 2)

        painter.restore()

    def boundingRect(self):
        # 넓은 범위 반환 (항상 다시 그리기 보장)
        return QRectF(-1e10, -1e10, 2e10, 2e10)

    def get_width_map(self) -> float:
        """맵 단위 너비 반환"""
        return self.width_map

    def get_height_map(self) -> float:
        """맵 단위 높이 반환"""
        return self.height_map

    # PDF 내보내기 호환용 (레거시)
    def get_pixel_width(self) -> int:
        """화면 픽셀 너비 (현재 줌 레벨 기준)"""
        mupp = self.canvas.mapUnitsPerPixel()
        if mupp > 0:
            return int(self.width_map / mupp)
        return 80

    def get_pixel_height(self) -> int:
        """화면 픽셀 높이 (현재 줌 레벨 기준)"""
        mupp = self.canvas.mapUnitsPerPixel()
        if mupp > 0:
            return int(self.height_map / mupp)
        return int(80 * self.aspect_ratio)

    def contains_point(self, screen_point: QPointF) -> bool:
        """화면 좌표가 아이템 영역 내에 있는지 확인"""
        if not self.position:
            return False
        # 화면 좌표 → 맵 좌표 변환
        map_point = self.toMapCoordinates(screen_point.toPoint())
        x = self.position.x()
        y = self.position.y()
        rect = QRectF(x, y - self.height_map, self.width_map, self.height_map)
        return rect.contains(QPointF(map_point.x(), map_point.y()))

    def start_drag(self, screen_point: QPointF):
        self.is_dragging = True
        self.is_selected = True
        if self.position:
            map_point = self.toMapCoordinates(screen_point.toPoint())
            self.drag_offset = QPointF(map_point.x() - self.position.x(),
                                       map_point.y() - self.position.y())
        self.update()

    def update_drag(self, screen_point: QPointF):
        if self.is_dragging:
            map_point = self.toMapCoordinates(screen_point.toPoint())
            new_x = map_point.x() - self.drag_offset.x()
            new_y = map_point.y() - self.drag_offset.y()
            self.position = QgsPointXY(new_x, new_y)
            self.update()

    def end_drag(self):
        self.is_dragging = False

    def deselect(self):
        self.is_selected = False
        self.update()

    def remove(self):
        self.canvas.scene().removeItem(self)


class ScaleBarItem(QgsMapCanvasItem):
    """A0 박스 내부에 이미지처럼 박힌 축적바 (맵 좌표 저장, 화면 좌표 렌더링, 고정 값)"""

    def __init__(self, canvas, position: QgsPointXY = None, bar_width_map: float = 1000.0,
                 fixed_label: str = "1km", center_aligned: bool = False):
        """
        Args:
            canvas: QgsMapCanvas
            position: 맵 좌표 위치 (QgsPointXY)
            bar_width_map: 축적바 너비 (맵 단위, 미터) - 고정됨
            fixed_label: 축적 표시 텍스트 (고정) - 예: "1km", "500m"
            center_aligned: 중앙 정렬 여부
        """
        super().__init__(canvas)
        self.canvas = canvas
        self.position = position  # 맵 좌표
        self.bar_width_map = bar_width_map  # 맵 단위 너비 (미터) - 고정!
        self.fixed_label = fixed_label  # 축척 텍스트 - 고정!
        self.center_aligned = center_aligned
        self.is_dragging = False
        self.drag_offset = QPointF(0, 0)
        self.is_selected = False
        self.setZValue(1000)

        # 축적바 높이 비율 (너비 대비)
        self.height_ratio = 0.05  # 너비의 5%
        # 폰트 크기 비율 (너비 대비)
        self.font_ratio = 0.12  # 너비의 12%

    def paint(self, painter, option, widget):
        if not self.position:
            return

        # 맵 좌표 → 화면 좌표 변환
        screen_pos = self.toCanvasCoordinates(self.position)

        # 맵 단위 크기 → 픽셀 크기 변환
        mupp = self.canvas.mapUnitsPerPixel()
        if mupp > 0:
            pixel_width = int(self.bar_width_map / mupp)
        else:
            pixel_width = 200

        # 최소/최대 크기 제한
        pixel_width = max(50, min(pixel_width, 2000))

        # 픽셀 기반 치수 계산
        pixel_height = max(5, int(pixel_width * self.height_ratio))
        font_pixel = max(8, int(pixel_width * self.font_ratio))
        pen_width = max(1, int(pixel_width * 0.01))

        # 화면 좌표 계산
        x = int(screen_pos.x())
        y = int(screen_pos.y())

        if self.center_aligned:
            x = x - pixel_width // 2

        # painter 변환 초기화 (화면 좌표로 직접 그리기)
        painter.save()
        painter.resetTransform()

        segment_width = pixel_width // 2

        # 축적바 그리기 (2세그먼트: 흰-검)
        painter.setPen(QPen(QColor(0, 0, 0), pen_width))
        for i in range(2):
            seg_x = x + i * segment_width
            if i % 2 == 0:
                painter.setBrush(QBrush(QColor(255, 255, 255)))
            else:
                painter.setBrush(QBrush(QColor(0, 0, 0)))
            # 화면 좌표: Y축 아래로 증가, 바를 position 위에 그림
            painter.drawRect(seg_x, y - pixel_height, segment_width, pixel_height)

        # 텍스트 그리기
        painter.setPen(QPen(QColor(0, 0, 0)))
        font = QFont()
        font.setPixelSize(font_pixel)
        font.setBold(True)
        painter.setFont(font)

        # "0" 텍스트 (좌측, 바 아래)
        text_y = y + font_pixel + 3
        painter.drawText(x, text_y, "0")

        # 고정된 축적 레이블 (우측 끝에 맞춤, 단위 포함)
        from qgis.PyQt.QtCore import QRect
        from qgis.PyQt.QtGui import QFontMetrics
        fm = QFontMetrics(font)
        label_width = fm.horizontalAdvance(self.fixed_label)
        painter.drawText(x + pixel_width - label_width, text_y, self.fixed_label)

        # 선택 시 테두리
        if self.is_selected:
            painter.setPen(QPen(QColor(0, 120, 215), pen_width * 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            margin = max(3, int(pixel_width * 0.03))
            total_height = pixel_height + font_pixel + 5
            painter.drawRect(x - margin, y - pixel_height - margin,
                             pixel_width + margin * 2, total_height + margin * 2)

        painter.restore()

    def boundingRect(self):
        # 넓은 범위 반환 (항상 다시 그리기 보장)
        return QRectF(-1e10, -1e10, 2e10, 2e10)

    def contains_point(self, screen_point: QPointF) -> bool:
        """화면 좌표가 아이템 영역 내에 있는지 확인"""
        if not self.position:
            return False

        # 화면 좌표 기반 히트 테스트
        screen_pos = self.toCanvasCoordinates(self.position)
        mupp = self.canvas.mapUnitsPerPixel()
        if mupp > 0:
            pixel_width = int(self.bar_width_map / mupp)
        else:
            pixel_width = 200

        pixel_width = max(50, min(pixel_width, 2000))
        pixel_height = max(5, int(pixel_width * self.height_ratio))
        font_pixel = max(8, int(pixel_width * self.font_ratio))

        x = int(screen_pos.x())
        y = int(screen_pos.y())

        if self.center_aligned:
            x = x - pixel_width // 2

        # 히트 영역 (바 + 텍스트)
        total_height = pixel_height + font_pixel + 10
        margin = pixel_width * 0.1
        rect = QRectF(x - margin, y - pixel_height - margin,
                      pixel_width + margin * 2, total_height + margin * 2)
        return rect.contains(screen_point)

    def start_drag(self, screen_point: QPointF):
        self.is_dragging = True
        self.is_selected = True
        if self.position:
            map_point = self.toMapCoordinates(screen_point.toPoint())
            self.drag_offset = QPointF(map_point.x() - self.position.x(),
                                       map_point.y() - self.position.y())
        self.update()

    def update_drag(self, screen_point: QPointF):
        if self.is_dragging:
            map_point = self.toMapCoordinates(screen_point.toPoint())
            new_x = map_point.x() - self.drag_offset.x()
            new_y = map_point.y() - self.drag_offset.y()
            self.position = QgsPointXY(new_x, new_y)
            self.update()

    def end_drag(self):
        self.is_dragging = False

    def deselect(self):
        self.is_selected = False
        self.update()

    def remove(self):
        self.canvas.scene().removeItem(self)
