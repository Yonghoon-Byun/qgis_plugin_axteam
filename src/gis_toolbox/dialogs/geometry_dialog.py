# -*- coding: utf-8 -*-
"""
Geometry Fix Dialog with modern card-based UI design
"""

from qgis.PyQt.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QRadioButton,
    QLabel, QCheckBox
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject, QgsVectorLayer
import processing

from .base_dialog import BaseLayerDialog


class GeometryDialog(BaseLayerDialog):
    """Dialog for batch geometry fixing with modern UI."""

    def __init__(self, iface, parent=None):
        super().__init__(iface, "도형 수정", parent)
        self.setup_geometry_options()

    def setup_geometry_options(self):
        """Setup geometry fix options in the options card."""
        # Card header
        header = QLabel("도형 수정 설정")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #374151; border: none;")
        self.options_layout.addWidget(header)

        # Description
        desc = QLabel("선택한 레이어들의 유효하지 않은 도형을 자동으로 수정합니다.")
        desc.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")
        desc.setWordWrap(True)
        self.options_layout.addWidget(desc)

        # Output mode frame
        mode_frame = QFrame()
        mode_frame.setObjectName("modeFrame")
        mode_frame.setStyleSheet("""
            QFrame#modeFrame {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
            }
        """)
        mode_layout = QVBoxLayout(mode_frame)
        mode_layout.setContentsMargins(12, 12, 12, 12)
        mode_layout.setSpacing(8)

        mode_label = QLabel("출력 방식")
        mode_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151; border: none;")
        mode_layout.addWidget(mode_label)

        self.radio_memory = QRadioButton("메모리 레이어로 생성 (원본 유지)")
        self.radio_memory.setStyleSheet("font-size: 14px; color: #374151;")
        self.radio_replace = QRadioButton("원본 레이어 대체")
        self.radio_replace.setStyleSheet("font-size: 14px; color: #374151;")
        self.radio_memory.setChecked(True)

        mode_layout.addWidget(self.radio_memory)
        mode_layout.addWidget(self.radio_replace)

        self.options_layout.addWidget(mode_frame)

        # Warning notice
        warning_frame = QFrame()
        warning_frame.setObjectName("warningFrame")
        warning_frame.setStyleSheet("""
            QFrame#warningFrame {
                background-color: #fef3c7;
                border: 1px solid #fcd34d;
                border-radius: 6px;
            }
        """)
        warning_layout = QHBoxLayout(warning_frame)
        warning_layout.setContentsMargins(12, 10, 12, 10)

        warning_icon = QLabel("⚠")
        warning_icon.setStyleSheet("font-size: 16px; border: none; background: transparent;")
        warning_layout.addWidget(warning_icon)

        warning_text = QLabel("원본 대체 선택 시 기존 레이어의 도형이 수정됩니다")
        warning_text.setStyleSheet("font-size: 13px; color: #92400e; border: none; background: transparent;")
        warning_layout.addWidget(warning_text)
        warning_layout.addStretch()

        self.options_layout.addWidget(warning_frame)

        # Additional options frame
        options_frame = QFrame()
        options_frame.setObjectName("optionsFrame")
        options_frame.setStyleSheet("""
            QFrame#optionsFrame {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
            }
        """)
        options_layout = QVBoxLayout(options_frame)
        options_layout.setContentsMargins(12, 12, 12, 12)
        options_layout.setSpacing(8)

        options_label = QLabel("추가 옵션")
        options_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151; border: none;")
        options_layout.addWidget(options_label)

        self.check_add_to_project = QCheckBox("수정된 레이어를 프로젝트에 추가")
        self.check_add_to_project.setStyleSheet("font-size: 14px; color: #374151;")
        self.check_add_to_project.setChecked(True)
        options_layout.addWidget(self.check_add_to_project)

        self.check_remove_original = QCheckBox("원본 레이어 제거 (메모리 레이어 생성 시)")
        self.check_remove_original.setStyleSheet("font-size: 14px; color: #374151;")
        self.check_remove_original.setChecked(False)
        options_layout.addWidget(self.check_remove_original)

        self.options_layout.addWidget(options_frame)

        # Info notice
        info_frame = QFrame()
        info_frame.setObjectName("infoFrame")
        info_frame.setStyleSheet("""
            QFrame#infoFrame {
                background-color: #dbeafe;
                border: 1px solid #93c5fd;
                border-radius: 6px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 12, 12, 12)
        info_layout.setSpacing(6)

        info_header = QLabel("수정되는 도형 오류")
        info_header.setStyleSheet("font-size: 13px; font-weight: bold; color: #1e40af; border: none; background: transparent;")
        info_layout.addWidget(info_header)

        fixes = [
            "• 자체 교차 폴리곤 수정",
            "• 중복 정점 제거",
            "• 링 방향 수정",
            "• 기타 도형 오류 수정"
        ]

        for fix in fixes:
            fix_label = QLabel(fix)
            fix_label.setStyleSheet("font-size: 12px; color: #1e40af; border: none; background: transparent; margin-left: 8px;")
            info_layout.addWidget(fix_label)

        self.options_layout.addWidget(info_frame)
        self.options_layout.addStretch()

    def execute(self):
        """Execute geometry fixing."""
        layers = self.get_selected_layers()
        if not layers:
            self.show_warning("선택된 레이어가 없습니다.")
            return

        self.start_progress(len(layers), "도형 수정 중...")

        success_count = 0
        errors = []
        results = []

        for i, layer in enumerate(layers):
            self.update_progress(i, f"수정 중: {layer.name()}")

            try:
                result = processing.run("native:fixgeometries", {
                    'INPUT': layer,
                    'OUTPUT': 'memory:'
                })

                output_layer = result['OUTPUT']

                if isinstance(output_layer, QgsVectorLayer) and output_layer.isValid():
                    new_name = f"{layer.name()}_fixed"
                    output_layer.setName(new_name)

                    if self.radio_replace.isChecked():
                        self.replace_layer_features(layer, output_layer)
                        results.append(f"✓ {layer.name()}: 원본 수정됨")
                    else:
                        if self.check_add_to_project.isChecked():
                            QgsProject.instance().addMapLayer(output_layer)
                            results.append(f"✓ {layer.name()} → {new_name}")

                        if self.check_remove_original.isChecked():
                            QgsProject.instance().removeMapLayer(layer.id())

                    success_count += 1
                else:
                    errors.append(f"{layer.name()}: 결과 레이어가 유효하지 않음")

            except Exception as e:
                errors.append(f"{layer.name()}: {str(e)}")

        self.finish_progress()

        message = f"{success_count}개 레이어의 도형이 수정되었습니다.\n\n"
        if results:
            message += "결과:\n" + "\n".join(results)
        if errors:
            message += f"\n\n오류:\n" + "\n".join(errors)

        self.show_info(message)
        self.load_layers()

    def replace_layer_features(self, target_layer, source_layer):
        """Replace features in target layer with features from source layer."""
        target_layer.startEditing()
        target_layer.dataProvider().truncate()
        features = list(source_layer.getFeatures())
        target_layer.dataProvider().addFeatures(features)
        target_layer.commitChanges()
        target_layer.triggerRepaint()
