"""
Export Manager for BasePlan QGIS Plugin
Handles exporting maps to PDF, images, and saving QGIS projects

v6 (2026-02-04): PDF 내보내기 멈춤 문제 해결
- QgsLayoutItemMap 사용으로 이중 렌더링 제거
- 적응형 DPI (큰 영역은 DPI 낮춤)
- 가시성 체크 추가
- QApplication.processEvents() 로 UI 응답성 유지

v5: 가로/세로 도면 방향 자동 감지
v4.3: 커스텀 방위표/축척바 오버레이 내보내기 지원
"""

from qgis.core import (
    QgsProject,
    QgsLayout,
    QgsLayoutExporter,
    QgsLayoutItemMap,
    QgsLayoutItemScaleBar,
    QgsLayoutItemPicture,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsRectangle,
    QgsCoordinateReferenceSystem,
    QgsUnitTypes,
    QgsPrintLayout,
    QgsReadWriteContext,
    QgsLayoutItemLabel,
    QgsMapSettings,
    QgsMapRendererCustomPainterJob,
    QgsMessageLog,
    Qgis
)
from qgis.PyQt.QtCore import QSize, QSizeF, QRectF, Qt
from qgis.PyQt.QtGui import QImage, QPainter, QColor, QPixmap, QFont, QPen, QBrush
from qgis.PyQt.QtWidgets import QFileDialog, QApplication
from typing import Tuple, Optional
import os


class ExportManager:
    """Manages export operations for the BasePlan plugin - v6 UI 응답성 개선"""

    # Constants
    CRS = 'EPSG:5179'
    DEFAULT_DPI = 300
    # A0 용지 크기 (mm)
    A0_LONG_MM = 1189   # 긴 변
    A0_SHORT_MM = 841   # 짧은 변

    def __init__(self):
        """Initialize Export Manager"""
        self.project = QgsProject.instance()
        # v4.3: 오버레이 참조 (controller에서 설정)
        self.north_overlay = None
        self.scale_overlay = None
        # v4.4: A0 박스 참조
        self.a0_box = None

    def set_overlays(self, north_overlay, scale_overlay):
        """v4.3: 오버레이 참조 설정"""
        self.north_overlay = north_overlay
        self.scale_overlay = scale_overlay

    def set_a0_box(self, bbox: QgsRectangle):
        """v4.4: A0 박스 참조 설정"""
        self.a0_box = bbox

    def _is_portrait(self, bbox: Tuple[float, float, float, float]) -> bool:
        """v5: 박스가 세로 방향인지 확인"""
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        return height > width

    def _get_page_size_mm(self, bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
        """v5: 박스 방향에 따른 A0 용지 크기 반환 (width_mm, height_mm)"""
        if self._is_portrait(bbox):
            # 세로 도면: 폭 < 높이
            return (self.A0_SHORT_MM, self.A0_LONG_MM)
        else:
            # 가로 도면: 폭 > 높이
            return (self.A0_LONG_MM, self.A0_SHORT_MM)

    def _get_image_size_px(self, bbox: Tuple[float, float, float, float], dpi: int = 300) -> Tuple[int, int]:
        """v5: 박스 방향에 따른 이미지 픽셀 크기 반환"""
        width_mm, height_mm = self._get_page_size_mm(bbox)
        width_px = int(width_mm / 25.4 * dpi)
        height_px = int(height_mm / 25.4 * dpi)
        return (width_px, height_px)

    def _log(self, message: str, level=Qgis.Info):
        """로그 메시지 출력"""
        QgsMessageLog.logMessage(message, 'BasePlan', level)
        print(f"[ExportManager] {message}")

    def _get_visible_layers(self):
        """v6: 실제로 보이는 레이어만 반환"""
        root = self.project.layerTreeRoot()
        visible_layers = []
        for layer in self.project.mapLayers().values():
            if layer.isValid():
                node = root.findLayer(layer.id())
                if node and node.isVisible():
                    visible_layers.append(layer)
        return visible_layers

    def _calculate_adaptive_dpi(self, bbox: Tuple[float, float, float, float]) -> int:
        """v6: 영역 크기에 따른 적응형 DPI 계산"""
        width_m = bbox[2] - bbox[0]
        height_m = bbox[3] - bbox[1]
        area_km2 = (width_m * height_m) / 1_000_000

        # 영역 크기에 따른 DPI 조정
        if area_km2 > 100:  # 100km² 이상
            return 150
        elif area_km2 > 50:  # 50km² 이상
            return 200
        elif area_km2 > 20:  # 20km² 이상
            return 250
        else:
            return self.DEFAULT_DPI  # 300 DPI

    def export_to_pdf(
        self,
        bbox: Tuple[float, float, float, float],
        output_path: Optional[str] = None,
        include_scale_bar: bool = False,
        include_north_arrow: bool = False
    ) -> Tuple[bool, str]:
        """
        v6: Export map to PDF (QgsLayoutItemMap 직접 사용, UI 응답성 개선)

        Args:
            bbox: Bounding box (minx, miny, maxx, maxy) in EPSG:5179
            output_path: Path to save PDF file (prompts if None)

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Prompt for output path if not provided
            if not output_path:
                output_path, _ = QFileDialog.getSaveFileName(
                    None,
                    "Export to PDF",
                    "",
                    "PDF Files (*.pdf)"
                )
                if not output_path:
                    return False, "Export cancelled by user"

            # Ensure .pdf extension
            if not output_path.lower().endswith('.pdf'):
                output_path += '.pdf'

            # v6: UI 응답성 유지
            QApplication.processEvents()

            # v5: 박스 방향에 따른 용지 크기 자동 결정
            page_width_mm, page_height_mm = self._get_page_size_mm(bbox)

            # v6: 적응형 DPI
            adaptive_dpi = self._calculate_adaptive_dpi(bbox)
            self._log(f"PDF - {'세로도면' if self._is_portrait(bbox) else '가로도면'}: {page_width_mm}x{page_height_mm}mm, DPI: {adaptive_dpi}")

            # v6: QgsLayoutItemMap 직접 사용 (이중 렌더링 제거)
            layout = QgsPrintLayout(self.project)
            layout.initializeDefaults()
            layout.setName("BasePlan Export Layout")

            # 용지 크기 설정
            page = layout.pageCollection().page(0)
            page.setPageSize(QgsLayoutSize(
                page_width_mm,
                page_height_mm,
                QgsUnitTypes.LayoutMillimeters
            ))

            QApplication.processEvents()

            # 맵 아이템 생성
            map_item = QgsLayoutItemMap(layout)
            map_item.attemptMove(QgsLayoutPoint(0, 0, QgsUnitTypes.LayoutMillimeters))
            map_item.attemptResize(QgsLayoutSize(page_width_mm, page_height_mm, QgsUnitTypes.LayoutMillimeters))

            # 맵 범위 설정
            extent = QgsRectangle(bbox[0], bbox[1], bbox[2], bbox[3])
            map_item.setExtent(extent)

            # CRS 설정
            crs = QgsCoordinateReferenceSystem(self.CRS)
            map_item.setCrs(crs)

            # v6: 가시 레이어만 설정
            visible_layers = self._get_visible_layers()
            map_item.setLayers(visible_layers)

            layout.addLayoutItem(map_item)

            QApplication.processEvents()

            # v6: 오버레이 (방위표, 축척바)를 레이아웃 아이템으로 추가
            self._add_layout_overlays(layout, map_item, extent, page_width_mm, page_height_mm)

            QApplication.processEvents()

            # PDF 내보내기
            exporter = QgsLayoutExporter(layout)
            export_settings = QgsLayoutExporter.PdfExportSettings()
            export_settings.dpi = adaptive_dpi

            self._log(f"Exporting PDF to: {output_path}")
            result = exporter.exportToPdf(output_path, export_settings)

            if result == QgsLayoutExporter.Success:
                self._log(f"PDF export success: {output_path}")
                return True, f"Successfully exported to {output_path}"
            else:
                error_messages = {
                    QgsLayoutExporter.FileError: "File error - check permissions and path",
                    QgsLayoutExporter.PrintError: "Print/rendering error",
                    QgsLayoutExporter.MemoryError: "Insufficient memory",
                    QgsLayoutExporter.IteratorError: "Iterator error",
                    QgsLayoutExporter.SvgLayerError: "SVG layer error",
                    QgsLayoutExporter.Canceled: "Export cancelled"
                }
                error_msg = error_messages.get(result, f"Unknown error (code: {result})")
                self._log(f"PDF export failed: {error_msg}", level=Qgis.Critical)
                return False, f"PDF export failed: {error_msg}"

        except Exception as e:
            self._log(f"PDF export error: {str(e)}", level=Qgis.Critical)
            return False, f"PDF export error: {str(e)}"

    def _add_layout_overlays(self, layout, map_item, extent, page_width_mm, page_height_mm):
        """v6.1: 레이아웃에 방위표/축척바 추가 (크기 증가)"""
        if not self.a0_box:
            return

        # A0 박스의 레이아웃 내 위치 계산
        box_x_ratio = (self.a0_box.xMinimum() - extent.xMinimum()) / extent.width()
        box_y_ratio = (extent.yMaximum() - self.a0_box.yMaximum()) / extent.height()
        box_width_ratio = self.a0_box.width() / extent.width()
        box_height_ratio = self.a0_box.height() / extent.height()

        box_x_mm = box_x_ratio * page_width_mm
        box_y_mm = box_y_ratio * page_height_mm
        box_width_mm = box_width_ratio * page_width_mm
        box_height_mm = box_height_ratio * page_height_mm

        margin_mm = box_width_mm * 0.03  # 3% 마진 (증가)

        # 방위표 추가
        north_image_path = os.path.join(
            os.path.dirname(__file__), '..', 'resources', 'north_arrow.png'
        )
        if os.path.exists(north_image_path):
            north_width_mm = box_width_mm * 0.12  # 박스 너비의 12% (6% → 12% 증가)
            north_width_mm = max(30, min(north_width_mm, 120))  # 30~120mm 범위 (확대)

            north_item = QgsLayoutItemPicture(layout)
            north_item.setPicturePath(north_image_path)
            north_item.attemptMove(QgsLayoutPoint(
                box_x_mm + margin_mm,
                box_y_mm + margin_mm,
                QgsUnitTypes.LayoutMillimeters
            ))
            north_item.attemptResize(QgsLayoutSize(
                north_width_mm,
                north_width_mm * 1.5,  # 종횡비 약 1:1.5
                QgsUnitTypes.LayoutMillimeters
            ))
            layout.addLayoutItem(north_item)

            # v6.3: 축척바 기능 임시 비활성화
            # TODO: 축척바 위치/크기 문제 해결 후 다시 활성화
            # scale_bar = QgsLayoutItemScaleBar(layout)
            # scale_bar.setLinkedMap(map_item)
            # ...
            pass

    def _map_to_layout_coords(self, map_point, extent, layout_width_mm, layout_height_mm):
        """v4.3: 맵 좌표를 레이아웃 좌표(mm)로 변환"""
        # X: 왼쪽 = 0, 오른쪽 = layout_width
        x_ratio = (map_point.x() - extent.xMinimum()) / extent.width()
        x_mm = x_ratio * layout_width_mm

        # Y: 위쪽 = 0 (맵에서는 yMaximum), 아래쪽 = layout_height
        y_ratio = (extent.yMaximum() - map_point.y()) / extent.height()
        y_mm = y_ratio * layout_height_mm

        return (x_mm, y_mm)

    def export_to_image(
        self,
        bbox: Tuple[float, float, float, float],
        output_path: Optional[str] = None,
        format: str = 'PNG',
        dpi: int = 300
    ) -> Tuple[bool, str]:
        """
        Export map to image file

        Args:
            bbox: Bounding box (minx, miny, maxx, maxy) in EPSG:5179
            output_path: Path to save image file (prompts if None)
            format: Image format ('PNG' or 'JPEG')
            dpi: Output DPI (default: 300 for print quality)

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Validate format
            format = format.upper()
            if format not in ['PNG', 'JPEG', 'JPG']:
                return False, f"Unsupported format: {format}. Use PNG or JPEG."

            # Normalize JPEG format
            if format == 'JPG':
                format = 'JPEG'

            # Prompt for output path if not provided
            if not output_path:
                file_filter = f"{format} Files (*.{format.lower()})"
                output_path, _ = QFileDialog.getSaveFileName(
                    None,
                    f"Export to {format}",
                    "",
                    file_filter
                )
                if not output_path:
                    return False, "Export cancelled by user"

            # Ensure correct extension
            ext = f'.{format.lower()}'
            if format == 'JPEG':
                ext = '.jpg'  # Use .jpg for JPEG files
            if not output_path.lower().endswith(ext):
                output_path += ext

            # v5: 박스 방향에 따른 용지 크기 결정
            page_width_mm, page_height_mm = self._get_page_size_mm(bbox)

            print(f"[ExportManager] Image - {'세로도면' if self._is_portrait(bbox) else '가로도면'}: {page_width_mm}x{page_height_mm}mm")

            # Create layout for high-quality export
            layout = QgsPrintLayout(self.project)
            layout.initializeDefaults()
            layout.setName("BasePlan Image Export")

            # v5: 박스 방향에 따른 용지 크기 설정
            page = layout.pageCollection().page(0)
            page.setPageSize(QgsLayoutSize(
                page_width_mm,
                page_height_mm,
                QgsUnitTypes.LayoutMillimeters
            ))

            # Create map item
            map_item = QgsLayoutItemMap(layout)
            map_item.attemptMove(
                QgsLayoutPoint(0, 0, QgsUnitTypes.LayoutMillimeters)
            )
            map_item.attemptResize(
                QgsLayoutSize(
                    page_width_mm,
                    page_height_mm,
                    QgsUnitTypes.LayoutMillimeters
                )
            )

            # Set map extent
            extent = QgsRectangle(bbox[0], bbox[1], bbox[2], bbox[3])
            map_item.setExtent(extent)

            # Set CRS
            crs = QgsCoordinateReferenceSystem(self.CRS)
            map_item.setCrs(crs)

            # Add map item to layout
            layout.addLayoutItem(map_item)

            # Export to image
            exporter = QgsLayoutExporter(layout)
            image_settings = QgsLayoutExporter.ImageExportSettings()
            image_settings.dpi = dpi

            if format == 'PNG':
                result = exporter.exportToImage(output_path, image_settings)
            else:  # JPEG
                # For JPEG, we need to export to temporary PNG first, then convert
                # Or use exportToImage which handles the format
                result = exporter.exportToImage(output_path, image_settings)

            if result == QgsLayoutExporter.Success:
                return True, f"Successfully exported to {output_path}"
            else:
                error_messages = {
                    QgsLayoutExporter.FileError: "File error - check permissions and path",
                    QgsLayoutExporter.PrintError: "Print/rendering error",
                    QgsLayoutExporter.MemoryError: "Insufficient memory",
                    QgsLayoutExporter.IteratorError: "Iterator error",
                    QgsLayoutExporter.SvgLayerError: "SVG layer error",
                    QgsLayoutExporter.Canceled: "Export cancelled"
                }
                error_msg = error_messages.get(result, f"Unknown error (code: {result})")
                return False, f"Image export failed: {error_msg}"

        except Exception as e:
            return False, f"Image export error: {str(e)}"

    def save_project(self, output_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Save current project as QGIS project file

        Args:
            output_path: Path to save project file (prompts if None)

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Prompt for output path if not provided
            if not output_path:
                output_path, _ = QFileDialog.getSaveFileName(
                    None,
                    "Save QGIS Project",
                    "",
                    "QGIS Project Files (*.qgs *.qgz);;QGIS Project (*.qgs);;Compressed QGIS Project (*.qgz)"
                )
                if not output_path:
                    return False, "Save cancelled by user"

            # Ensure proper extension
            if not (output_path.lower().endswith('.qgs') or output_path.lower().endswith('.qgz')):
                output_path += '.qgz'  # Default to compressed format

            # Save project
            success = self.project.write(output_path)

            if success:
                return True, f"Successfully saved project to {output_path}"
            else:
                return False, "Failed to save project. Check file permissions and path."

        except Exception as e:
            return False, f"Project save error: {str(e)}"

    def export_to_image_direct(
        self,
        bbox: Tuple[float, float, float, float],
        output_path: Optional[str] = None,
        format: str = 'PNG',
        width: int = None,  # v5: None이면 자동 계산
        height: int = None  # v5: None이면 자동 계산
    ) -> Tuple[bool, str]:
        """
        v6: Export map to image (UI 응답성 개선, 가시 레이어만 사용)

        Args:
            bbox: Bounding box (minx, miny, maxx, maxy) in EPSG:5179
            output_path: Path to save image file (prompts if None)
            format: Image format ('PNG' or 'JPEG')
            width: Image width in pixels (None for auto)
            height: Image height in pixels (None for auto)

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Validate format
            format = format.upper()
            if format not in ['PNG', 'JPEG', 'JPG']:
                return False, f"Unsupported format: {format}. Use PNG or JPEG."

            # Normalize format
            if format == 'JPG':
                format = 'JPEG'

            # Prompt for output path if not provided
            if not output_path:
                file_filter = f"{format} Files (*.{format.lower()})"
                output_path, _ = QFileDialog.getSaveFileName(
                    None,
                    f"Export to {format}",
                    "",
                    file_filter
                )
                if not output_path:
                    return False, "Export cancelled by user"

            # Ensure correct extension
            ext = f'.{format.lower()}'
            if format == 'JPEG':
                ext = '.jpg'
            if not output_path.lower().endswith(ext):
                output_path += ext

            # v6: UI 응답성 유지
            QApplication.processEvents()

            # v6: 적응형 DPI
            adaptive_dpi = self._calculate_adaptive_dpi(bbox)

            # v5: 박스 방향에 따른 이미지 크기 자동 계산
            if width is None or height is None:
                width, height = self._get_image_size_px(bbox, adaptive_dpi)

            self._log(f"Direct Image - {'세로도면' if self._is_portrait(bbox) else '가로도면'}: {width}x{height}px, DPI: {adaptive_dpi}")

            # Create map settings
            settings = QgsMapSettings()
            extent = QgsRectangle(bbox[0], bbox[1], bbox[2], bbox[3])
            settings.setExtent(extent)
            settings.setOutputSize(QSize(width, height))
            crs = QgsCoordinateReferenceSystem(self.CRS)
            settings.setDestinationCrs(crs)
            settings.setBackgroundColor(QColor(255, 255, 255))

            # v6: 가시 레이어만 사용
            visible_layers = self._get_visible_layers()
            settings.setLayers(visible_layers)

            QApplication.processEvents()

            # Create image
            image = QImage(QSize(width, height), QImage.Format_ARGB32)
            image.fill(QColor(255, 255, 255).rgb())

            # Create painter
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Render map
            self._log("Rendering map...")
            job = QgsMapRendererCustomPainterJob(settings, painter)
            job.start()
            job.waitForFinished()

            QApplication.processEvents()

            # v4.3: 오버레이 렌더링
            self._render_overlays(painter, extent, width, height)

            painter.end()

            QApplication.processEvents()

            # Save image
            self._log(f"Saving image to: {output_path}")
            quality = 95 if format == 'JPEG' else -1
            success = image.save(output_path, format, quality)

            if success:
                self._log(f"Image export success: {output_path}")
                return True, f"Successfully exported to {output_path}"
            else:
                self._log("Image save failed", level=Qgis.Critical)
                return False, "Failed to save image. Check file permissions and path."

        except Exception as e:
            self._log(f"Image export error: {str(e)}", level=Qgis.Critical)
            return False, f"Direct image export error: {str(e)}"

    def _render_overlays(self, painter: QPainter, extent: QgsRectangle, img_width: int, img_height: int):
        """v6.1: 오버레이 자동 렌더링 (A0 박스 기준, 크기 증가)"""

        # 맵 좌표 → 이미지 좌표 변환 함수
        def map_to_pixel(map_x, map_y):
            px = (map_x - extent.xMinimum()) / extent.width() * img_width
            py = (extent.yMaximum() - map_y) / extent.height() * img_height
            return int(px), int(py)

        # A0 박스가 없으면 오버레이 없음
        if not self.a0_box:
            return

        # A0 박스 좌표 → 픽셀 좌표
        box_x1, box_y1 = map_to_pixel(self.a0_box.xMinimum(), self.a0_box.yMaximum())  # 좌상단
        box_x2, box_y2 = map_to_pixel(self.a0_box.xMaximum(), self.a0_box.yMinimum())  # 우하단
        box_width_px = box_x2 - box_x1
        box_height_px = box_y2 - box_y1

        # v6.1: 크기 증가
        # 방위표: 박스 좌측 상단, 박스 너비의 12% (6% → 12%)
        north_width_px = int(box_width_px * 0.12)
        north_width_px = max(80, min(north_width_px, 400))  # 80~400px 범위 (확대)
        margin_px = int(box_width_px * 0.03)  # 3% 마진 (증가)

        north_x = box_x1 + margin_px
        north_y = box_y1 + margin_px

        # 방위표 이미지 로드 및 렌더링
        north_image_path = os.path.join(
            os.path.dirname(__file__), '..', 'resources', 'north_arrow.png'
        )
        north_height_px = 0
        if os.path.exists(north_image_path):
            pixmap = QPixmap(north_image_path)
            if not pixmap.isNull():
                # 종횡비 유지
                aspect = pixmap.height() / pixmap.width() if pixmap.width() > 0 else 1.0
                north_height_px = int(north_width_px * aspect)

                scaled_pixmap = pixmap.scaled(
                    north_width_px, north_height_px,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                painter.drawPixmap(north_x, north_y, scaled_pixmap)

        # v6.3: 축척바 기능 임시 비활성화
        # TODO: 축척바 위치/크기 문제 해결 후 다시 활성화

        # A0 박스 테두리 렌더링
        painter.setPen(QPen(QColor(0, 0, 0), 3))  # 테두리 두께 증가
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(box_x1, box_y1, box_width_px, box_height_px)

    @staticmethod
    def get_file_dialog_path(
        dialog_title: str = "Select File",
        file_filter: str = "All Files (*.*)",
        default_path: str = ""
    ) -> Optional[str]:
        """
        Show file dialog and return selected path

        Args:
            dialog_title: Dialog window title
            file_filter: File filter string
            default_path: Default directory/file path

        Returns:
            Selected file path or None if cancelled
        """
        path, _ = QFileDialog.getSaveFileName(
            None,
            dialog_title,
            default_path,
            file_filter
        )
        return path if path else None
