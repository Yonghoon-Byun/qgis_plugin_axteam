# -*- coding: utf-8 -*-
"""
전처리 엔진 - 레이어 클리핑 + 도형 수정 + 인코딩 설정
"""

from qgis.core import (
    QgsVectorLayer, QgsRasterLayer,
    QgsProcessingFeedback,
    QgsTask, QgsApplication, QgsProject,
    QgsMessageLog, Qgis,
)

LOG_TAG = "CivilPlanner"


class Preprocessor:
    """벡터/래스터 레이어 전처리"""

    @staticmethod
    def clip_vector(input_layer, boundary_layer, output_name=None):
        """벡터 레이어를 범위 레이어로 클리핑

        Args:
            input_layer: 입력 벡터 레이어
            boundary_layer: 클리핑 범위 폴리곤 레이어
            output_name: 출력 레이어 이름 (None이면 원래 이름 + '_clip')

        Returns:
            QgsVectorLayer: 클리핑된 메모리 레이어 또는 None
        """
        if not isinstance(input_layer, QgsVectorLayer):
            return None

        name = output_name or f"{input_layer.name()}_clip"

        try:
            import processing
            result = processing.run(
                "native:clip",
                {
                    "INPUT": input_layer,
                    "OVERLAY": boundary_layer,
                    "OUTPUT": "memory:" + name,
                },
                feedback=QgsProcessingFeedback(),
            )
            output = result["OUTPUT"]
            if isinstance(output, QgsVectorLayer) and output.featureCount() > 0:
                output.dataProvider().createSpatialIndex()
                return output
            return None
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Clip failed for {input_layer.name()}: {e}",
                LOG_TAG, Qgis.Warning,
            )
            return None

    @staticmethod
    def clip_raster(input_layer, boundary_layer, output_name=None):
        """래스터 레이어를 범위 레이어로 클리핑

        Args:
            input_layer: 입력 래스터 레이어
            boundary_layer: 클리핑 범위 폴리곤 레이어
            output_name: 출력 레이어 이름

        Returns:
            QgsRasterLayer 또는 None
        """
        if not isinstance(input_layer, QgsRasterLayer):
            return None

        try:
            import processing
            result = processing.run(
                "gdal:cliprasterbymasklayer",
                {
                    "INPUT": input_layer,
                    "MASK": boundary_layer,
                    "CROP_TO_CUTLINE": True,
                    "KEEP_RESOLUTION": True,
                    "NODATA": -9999,
                    "OUTPUT": "TEMPORARY_OUTPUT",
                },
                feedback=QgsProcessingFeedback(),
            )
            output_path = result["OUTPUT"]
            name = output_name or f"{input_layer.name()}_clip"
            clipped = QgsRasterLayer(output_path, name)
            if clipped.isValid():
                return clipped
            return None
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Raster clip failed for {input_layer.name()}: {e}",
                LOG_TAG, Qgis.Warning,
            )
            return None

    @staticmethod
    def fix_geometries(layer):
        """벡터 레이어의 도형 오류를 수정

        Args:
            layer: 입력 벡터 레이어

        Returns:
            QgsVectorLayer: 수정된 메모리 레이어 또는 None
        """
        if not isinstance(layer, QgsVectorLayer):
            return None

        try:
            import processing
            result = processing.run(
                "native:fixgeometries",
                {
                    "INPUT": layer,
                    "METHOD": 1,  # Structure method
                    "OUTPUT": "memory:" + layer.name(),
                },
                feedback=QgsProcessingFeedback(),
            )
            output = result["OUTPUT"]
            if isinstance(output, QgsVectorLayer) and output.isValid():
                output.dataProvider().createSpatialIndex()
                return output
            return None
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Fix geometry failed for {layer.name()}: {e}",
                LOG_TAG, Qgis.Warning,
            )
            return None

    @staticmethod
    def preprocess_layer(input_layer, boundary_layer, fix_geom=True):
        """클리핑 + 도형 수정을 한번에 수행

        Args:
            input_layer: 입력 레이어
            boundary_layer: 범위 레이어
            fix_geom: 도형 수정 여부

        Returns:
            레이어 또는 None
        """
        if isinstance(input_layer, QgsRasterLayer):
            return Preprocessor.clip_raster(input_layer, boundary_layer)

        # 벡터: 클리핑 → 도형 수정
        clipped = Preprocessor.clip_vector(input_layer, boundary_layer)
        if clipped is None:
            return None

        if fix_geom:
            fixed = Preprocessor.fix_geometries(clipped)
            if fixed is not None:
                return fixed

        return clipped


class PreprocessTask(QgsTask):
    """QgsTask 기반 백그라운드 전처리 태스크

    QGIS 내장 태스크 매니저에서 백그라운드로 실행되며,
    processing.run() 호출로 인한 메인 스레드 블로킹을 방지합니다.

    사용 예:
        task = PreprocessTask(input_layer, boundary_layer, "도로_전처리",
                              style_callback=apply_style)
        QgsApplication.taskManager().addTask(task)
    """

    def __init__(self, input_layer, boundary_layer, layer_name, style_callback=None):
        """
        Args:
            input_layer: 입력 레이어 (벡터 또는 래스터)
            boundary_layer: 클리핑 범위 폴리곤 레이어
            layer_name: 태스크 및 결과 레이어 표시 이름
            style_callback: 완료 후 스타일 적용 콜백 (layer, name) → None
                            메인 스레드(finished)에서 호출됨
        """
        super().__init__(f"전처리: {layer_name}", QgsTask.CanCancel)
        self.input_layer = input_layer
        self.boundary_layer = boundary_layer
        self.layer_name = layer_name
        self.style_callback = style_callback
        self.result_layer = None
        self.error_msg = None

    def run(self):
        """백그라운드 스레드에서 실행 - processing.run() 안전"""
        try:
            QgsMessageLog.logMessage(
                f"전처리 시작: {self.layer_name}",
                LOG_TAG, Qgis.Info,
            )
            self.result_layer = Preprocessor.preprocess_layer(
                self.input_layer, self.boundary_layer
            )
            return self.result_layer is not None
        except Exception as e:
            self.error_msg = str(e)
            QgsMessageLog.logMessage(
                f"전처리 오류 ({self.layer_name}): {e}",
                LOG_TAG, Qgis.Critical,
            )
            return False

    def finished(self, success):
        """메인 스레드에서 호출 - 프로젝트에 레이어 추가"""
        if success and self.result_layer is not None:
            if self.style_callback:
                self.style_callback(self.result_layer, self.layer_name)
            QgsProject.instance().addMapLayer(self.result_layer)
            QgsMessageLog.logMessage(
                f"전처리 완료: {self.layer_name}",
                LOG_TAG, Qgis.Success,
            )
        else:
            msg = self.error_msg or "결과 레이어 없음"
            QgsMessageLog.logMessage(
                f"전처리 실패 ({self.layer_name}): {msg}",
                LOG_TAG, Qgis.Warning,
            )
