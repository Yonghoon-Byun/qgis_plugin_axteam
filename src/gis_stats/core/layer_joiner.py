"""
Layer Joiner - Join statistics to administrative boundaries
"""

from qgis.PyQt.QtCore import QObject, pyqtSignal, QThread, QMetaType
from qgis.core import (
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsProject,
    QgsMemoryProviderUtils,
    QgsFields,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem,
)


class LayerJoinerThread(QThread):
    """Worker thread for joining layers."""

    progress_changed = pyqtSignal(int, str)
    layer_created = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    # Fields to exclude from the result layer
    EXCLUDED_FIELDS = {"addr_en", "x", "y"}

    # Define field order priority (higher number = earlier in list)
    FIELD_ORDER = {
        "인구수": 9,
        "가구수": 8,
        "평균가구원수": 7,
        "총가구원수": 6,
        "주택수": 5,
        "총급수량_m3": 4,
        "유수수량_m3": 3,
        "1인1일급수량": 2,
        "1인1일사용량": 1,
    }

    def __init__(self, boundary_layer, statistics_data, join_field, layer_name=None, parent=None):
        """Initialize the joiner thread.

        :param boundary_layer: QgsVectorLayer with boundaries
        :param statistics_data: Dictionary of statistics keyed by adm_cd
        :param join_field: Field name to join on
        :param layer_name: Name for the result layer
        :param parent: Parent QObject
        """
        super().__init__(parent)
        self.boundary_layer = boundary_layer
        self.statistics_data = statistics_data
        self.join_field = join_field
        self.layer_name = layer_name or "통계_조인_결과"

    def _get_field_sort_key(self, field_name):
        """Get sort key for field name based on priority order.

        :param field_name: Field name (e.g., "인구수_2024")
        :returns: Tuple (priority, year, field_base_name) for sorting
        :rtype: tuple
        """
        # Extract base name (remove year suffix)
        parts = field_name.rsplit("_", 1)
        if len(parts) == 2:
            base_name = parts[0]
            try:
                year = int(parts[1])
            except ValueError:
                year = 0
        else:
            base_name = field_name
            year = 0

        # Get priority (higher = earlier)
        priority = self.FIELD_ORDER.get(base_name, 0)

        # Return tuple for sorting: (priority DESC, year ASC, base_name)
        return (-priority, year, base_name)

    def run(self):
        """Run the join operation."""
        try:
            self.progress_changed.emit(10, "레이어 구조 분석 중...")

            # Get original fields
            original_fields = self.boundary_layer.fields()

            # Determine new fields from statistics data
            new_field_names = set()
            for adm_cd, stats in self.statistics_data.items():
                new_field_names.update(stats.keys())

            # Sort fields by custom priority order
            new_field_names = sorted(new_field_names, key=self._get_field_sort_key)

            # Create fields for new layer (excluding specified fields)
            fields = QgsFields()
            for field in original_fields:
                if field.name() not in self.EXCLUDED_FIELDS:
                    fields.append(field)

            for field_name in new_field_names:
                field = QgsField(field_name, QMetaType.Type.Double, "double")
                fields.append(field)

            self.progress_changed.emit(30, "메모리 레이어 생성 중...")

            # Create memory layer
            crs = self.boundary_layer.crs()
            geom_type = self.boundary_layer.wkbType()

            mem_layer = QgsMemoryProviderUtils.createMemoryLayer(
                self.layer_name,
                fields,
                geom_type,
                crs,
            )

            if not mem_layer.isValid():
                self.error_occurred.emit("메모리 레이어 생성 실패")
                return

            self.progress_changed.emit(50, "피처 복사 및 통계 조인 중...")

            # Copy features and join statistics
            mem_layer.startEditing()

            total_features = self.boundary_layer.featureCount()
            for idx, feature in enumerate(self.boundary_layer.getFeatures()):
                new_feature = QgsFeature(fields)
                new_feature.setGeometry(feature.geometry())

                # Copy original attributes (excluding specified fields)
                for field in original_fields:
                    if field.name() not in self.EXCLUDED_FIELDS:
                        new_feature[field.name()] = feature[field.name()]

                # Join statistics
                adm_cd = feature[self.join_field]
                if adm_cd in self.statistics_data:
                    stats = self.statistics_data[adm_cd]
                    for field_name in new_field_names:
                        if field_name in stats:
                            value = stats[field_name]
                            # Handle empty strings and None values for Double fields
                            if value is None or value == '':
                                new_feature[field_name] = None
                            else:
                                try:
                                    new_feature[field_name] = float(value)
                                except (ValueError, TypeError):
                                    new_feature[field_name] = None

                mem_layer.addFeature(new_feature)

                # Update progress
                if idx % 100 == 0:
                    progress = 50 + int((idx / total_features) * 40)
                    self.progress_changed.emit(progress, f"피처 처리 중... ({idx}/{total_features})")

            mem_layer.commitChanges()

            self.progress_changed.emit(95, "레이어 완료...")
            self.layer_created.emit(mem_layer)
            self.progress_changed.emit(100, "완료!")

        except Exception as e:
            self.error_occurred.emit(f"조인 실패: {str(e)}")


class LayerJoiner(QObject):
    """Join statistics data to boundary layers."""

    # Signals
    progress_changed = pyqtSignal(int, str)
    join_finished = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        """Initialize the layer joiner.

        :param parent: Parent QObject
        """
        super().__init__(parent)
        self._joiner_thread = None
        self._result_layer = None

    def join_statistics_to_boundaries(
        self, boundary_layer, statistics_data, join_field="adm_cd", layer_name=None
    ):
        """Join statistics data to boundary layer.

        :param boundary_layer: QgsVectorLayer with boundaries
        :param statistics_data: Dictionary of statistics keyed by adm_cd
        :param join_field: Field name to join on (default: adm_cd)
        :param layer_name: Name for the result layer
        """
        if not boundary_layer or not boundary_layer.isValid():
            self.error_occurred.emit("유효하지 않은 경계 레이어입니다.")
            return

        if not statistics_data:
            self.error_occurred.emit("통계 데이터가 없습니다.")
            return

        # Stop existing thread if running
        if self._joiner_thread and self._joiner_thread.isRunning():
            self._joiner_thread.quit()
            self._joiner_thread.wait()

        # Create and start joiner thread
        self._joiner_thread = LayerJoinerThread(
            boundary_layer, statistics_data, join_field, layer_name, self
        )
        self._joiner_thread.progress_changed.connect(self.progress_changed)
        self._joiner_thread.layer_created.connect(self._on_layer_created)
        self._joiner_thread.error_occurred.connect(self.error_occurred)
        self._joiner_thread.start()

    def _on_layer_created(self, layer):
        """Handle layer creation completion."""
        self._result_layer = layer
        self.join_finished.emit(layer)

    def get_result_layer(self):
        """Get the result layer from the last join operation.

        :returns: QgsVectorLayer or None
        :rtype: QgsVectorLayer
        """
        return self._result_layer

    def add_layer_to_project(self, layer=None, group_name=None):
        """Add layer to QGIS project.

        :param layer: Layer to add (uses result layer if None)
        :param group_name: Optional group name to add layer to
        :returns: True if successful
        :rtype: bool
        """
        layer = layer or self._result_layer
        if not layer or not layer.isValid():
            return False

        project = QgsProject.instance()

        if group_name:
            root = project.layerTreeRoot()
            group = root.findGroup(group_name)
            if not group:
                group = root.addGroup(group_name)
            project.addMapLayer(layer, False)
            group.addLayer(layer)
        else:
            project.addMapLayer(layer)

        return True
