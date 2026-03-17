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


class BatchPreprocessTask(QgsTask):
    """QgsTask 기반 일괄 전처리 태스크

    여러 레이어를 하나의 태스크에서 **순차적으로** 처리합니다.
    processing.run()은 동시 실행 시 크래시하므로 반드시 순차 실행해야 합니다.

    사용 예:
        task = BatchPreprocessTask(layers_with_names, boundary_layer, style_callback)
        QgsApplication.taskManager().addTask(task)
    """

    def __init__(self, layers_with_names, boundary_layer, style_callback=None):
        """
        Args:
            layers_with_names: [(layer, name), ...] 전처리할 레이어 목록
            boundary_layer: 클리핑 범위 폴리곤 레이어
            style_callback: 완료 후 스타일 적용 콜백 (layer, name) → None
        """
        super().__init__("전처리 일괄 처리", QgsTask.CanCancel)
        self.layers_with_names = layers_with_names
        self.boundary_layer = boundary_layer
        self.style_callback = style_callback
        self.results = []  # [(layer, name, success), ...]

    def run(self):
        """백그라운드 스레드에서 실행 - 순차적으로 processing.run() 호출"""
        total = len(self.layers_with_names)

        for i, (layer, name) in enumerate(self.layers_with_names):
            if self.isCanceled():
                return False

            self.setProgress((i / total) * 100)

            QgsMessageLog.logMessage(
                f"전처리 중: {name} ({i + 1}/{total})",
                LOG_TAG, Qgis.Info,
            )

            try:
                result = Preprocessor.preprocess_layer(layer, self.boundary_layer)
                if result is not None:
                    self.results.append((result, name, True))
                else:
                    # 전처리 실패 시 레이어 제외 (범위 밖 데이터 방지)
                    QgsMessageLog.logMessage(
                        f"전처리 실패 (레이어 제외): {name}",
                        LOG_TAG, Qgis.Warning,
                    )
            except Exception as e:
                # 오류 발생 시 레이어 제외 (범위 밖 데이터 방지)
                QgsMessageLog.logMessage(
                    f"전처리 오류 (레이어 제외): {name} - {e}",
                    LOG_TAG, Qgis.Critical,
                )

        self.setProgress(100)
        return True

    def finished(self, success):
        """메인 스레드에서 호출 - 프로젝트에 레이어 일괄 추가"""
        for layer, name, preprocessed in self.results:
            if self.style_callback:
                self.style_callback(layer, name)
            QgsProject.instance().addMapLayer(layer)

            status = "완료" if preprocessed else "원본"
            QgsMessageLog.logMessage(
                f"레이어 추가 ({status}): {name}",
                LOG_TAG, Qgis.Success if preprocessed else Qgis.Warning,
            )
