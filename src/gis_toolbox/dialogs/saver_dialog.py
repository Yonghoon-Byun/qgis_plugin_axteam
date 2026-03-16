# -*- coding: utf-8 -*-
"""
Layer Saver Dialog with modern card-based UI design
"""

from qgis.PyQt.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QRadioButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QLabel, QLineEdit, QFileDialog,
    QComboBox
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.core import (QgsProject, QgsVectorLayer, QgsVectorFileWriter,
                       QgsCoordinateTransformContext)
import os

from .base_dialog import BaseLayerDialog


class SaverDialog(BaseLayerDialog):
    """Dialog for batch layer saving with modern UI."""

    def __init__(self, iface, parent=None):
        super().__init__(iface, "레이어 저장", parent)
        self.setup_saver_options()

    def get_vector_layers(self):
        """Get all vector layers including memory layers."""
        layers = []
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                layers.append(layer)
        return layers

    def setup_saver_options(self):
        """Setup saver-specific options in the options card."""
        # Card header
        header = QLabel("저장 설정")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #374151; border: none;")
        self.options_layout.addWidget(header)

        # Description
        desc = QLabel("선택한 레이어들을 파일로 저장합니다. 메모리 레이어도 저장할 수 있습니다.")
        desc.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")
        desc.setWordWrap(True)
        self.options_layout.addWidget(desc)

        # Mode selection frame
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

        self.radio_batch = QRadioButton("일괄 저장 (한 폴더에 레이어명으로 저장)")
        self.radio_batch.setStyleSheet("font-size: 14px; color: #374151;")
        self.radio_individual = QRadioButton("개별 저장 (레이어별 경로 지정)")
        self.radio_individual.setStyleSheet("font-size: 14px; color: #374151;")
        self.radio_batch.setChecked(True)
        self.radio_batch.toggled.connect(self.on_mode_changed)

        mode_layout.addWidget(self.radio_batch)
        mode_layout.addWidget(self.radio_individual)
        self.options_layout.addWidget(mode_frame)

        # Batch settings frame
        self.batch_frame = QFrame()
        self.batch_frame.setStyleSheet("border: none; background: transparent;")
        batch_layout = QVBoxLayout(self.batch_frame)
        batch_layout.setContentsMargins(0, 8, 0, 0)
        batch_layout.setSpacing(10)

        # Folder selector
        folder_label = QLabel("저장 폴더")
        folder_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151;")
        batch_layout.addWidget(folder_label)

        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("저장할 폴더를 선택하세요...")
        folder_row.addWidget(self.folder_edit)

        btn_browse = QPushButton("찾아보기...")
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                color: #374151;
                font-size: 13px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
        """)
        btn_browse.clicked.connect(self.browse_folder)
        folder_row.addWidget(btn_browse)
        batch_layout.addLayout(folder_row)

        # Format and encoding row
        options_row = QHBoxLayout()
        options_row.setSpacing(16)

        # Format
        format_box = QVBoxLayout()
        format_label = QLabel("출력 형식")
        format_label.setStyleSheet("font-size: 13px; color: #6b7280;")
        format_box.addWidget(format_label)

        self.format_combo = QComboBox()
        self.format_combo.addItem("Shapefile (.shp)", "ESRI Shapefile")
        self.format_combo.addItem("GeoPackage (.gpkg)", "GPKG")
        self.format_combo.addItem("GeoJSON (.geojson)", "GeoJSON")
        format_box.addWidget(self.format_combo)
        options_row.addLayout(format_box)

        # Encoding
        encoding_box = QVBoxLayout()
        encoding_label = QLabel("인코딩")
        encoding_label.setStyleSheet("font-size: 13px; color: #6b7280;")
        encoding_box.addWidget(encoding_label)

        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["UTF-8", "CP949", "EUC-KR", "System"])
        encoding_box.addWidget(self.encoding_combo)
        options_row.addLayout(encoding_box)

        options_row.addStretch()
        batch_layout.addLayout(options_row)

        self.options_layout.addWidget(self.batch_frame)

        # Individual settings frame
        self.individual_frame = QFrame()
        self.individual_frame.setStyleSheet("border: none; background: transparent;")
        self.individual_frame.setVisible(False)
        individual_layout = QVBoxLayout(self.individual_frame)
        individual_layout.setContentsMargins(0, 8, 0, 0)
        individual_layout.setSpacing(10)

        # Load button at top
        btn_load = QPushButton("선택된 레이어 불러오기")
        btn_load.setCursor(Qt.PointingHandCursor)
        btn_load.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                border: none;
                border-radius: 4px;
                color: white;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        btn_load.clicked.connect(self.load_layers_to_table)
        individual_layout.addWidget(btn_load)

        table_label = QLabel("레이어별 저장 경로")
        table_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151;")
        individual_layout.addWidget(table_label)

        self.path_table = QTableWidget()
        self.path_table.setColumnCount(4)
        self.path_table.setHorizontalHeaderLabels(["레이어명", "유형", "저장 경로", ""])
        self.path_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.path_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.path_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.path_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.path_table.setColumnWidth(0, 200)
        self.path_table.setColumnWidth(1, 100)
        self.path_table.setColumnWidth(3, 80)
        self.path_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #f9fafb;
                border: none;
                border-bottom: 1px solid #e5e7eb;
                padding: 8px;
                font-weight: bold;
                color: #374151;
            }
            QTableWidget::item {
                padding: 4px;
            }
        """)
        self.path_table.setMinimumHeight(200)
        individual_layout.addWidget(self.path_table)

        self.options_layout.addWidget(self.individual_frame)
        self.options_layout.addStretch()

    def browse_folder(self):
        """Browse for output folder."""
        folder = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if folder:
            self.folder_edit.setText(folder)

    def on_mode_changed(self, checked):
        """Handle mode change."""
        self.batch_frame.setVisible(self.radio_batch.isChecked())
        self.individual_frame.setVisible(self.radio_individual.isChecked())

    def load_layers_to_table(self):
        """Load selected layers into path table."""
        layers = self.get_selected_layers()

        if not layers:
            self.show_warning("선택된 레이어가 없습니다.")
            return

        self.path_table.setRowCount(len(layers))

        default_folder = self.folder_edit.text() or os.path.expanduser("~")
        ext = ".shp"

        for row, layer in enumerate(layers):
            # Layer name
            name_item = QTableWidgetItem(layer.name())
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setData(Qt.UserRole, layer.id())
            self.path_table.setItem(row, 0, name_item)

            # Layer type (memory or file)
            is_memory = layer.dataProvider().name() == 'memory' or not layer.source()
            type_text = "메모리" if is_memory else "파일"
            type_item = QTableWidgetItem(type_text)
            type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)
            if is_memory:
                type_item.setForeground(QColor("#d97706"))  # Amber color for memory layers
            self.path_table.setItem(row, 1, type_item)

            # Default path
            safe_name = self.sanitize_filename(layer.name())
            default_path = os.path.join(default_folder, f"{safe_name}{ext}")
            path_item = QTableWidgetItem(default_path)
            self.path_table.setItem(row, 2, path_item)

            # Browse button
            btn = QPushButton("찾아보기")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f3f4f6;
                    border: 1px solid #d1d5db;
                    border-radius: 4px;
                    color: #374151;
                    font-size: 12px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #e5e7eb;
                }
            """)
            btn.clicked.connect(lambda checked, r=row: self.browse_file(r))
            self.path_table.setCellWidget(row, 3, btn)

    def browse_file(self, row):
        """Browse for individual file path."""
        current_path = self.path_table.item(row, 2).text()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "저장 위치 선택",
            current_path,
            "Shapefile (*.shp);;GeoPackage (*.gpkg);;GeoJSON (*.geojson)"
        )
        if file_path:
            self.path_table.item(row, 2).setText(file_path)

    def sanitize_filename(self, name):
        """Remove invalid characters from filename."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name

    def get_extension(self, driver):
        """Get file extension for driver."""
        extensions = {
            "ESRI Shapefile": ".shp",
            "GPKG": ".gpkg",
            "GeoJSON": ".geojson"
        }
        return extensions.get(driver, ".shp")

    def execute(self):
        """Execute layer saving."""
        if self.radio_batch.isChecked():
            self.execute_batch()
        else:
            self.execute_individual()

    def execute_batch(self):
        """Save all selected layers to one folder."""
        layers = self.get_selected_layers()
        if not layers:
            self.show_warning("선택된 레이어가 없습니다.")
            return

        folder = self.folder_edit.text()
        if not folder or not os.path.isdir(folder):
            self.show_warning("유효한 저장 폴더를 선택해주세요.")
            return

        driver = self.format_combo.currentData()
        encoding = self.encoding_combo.currentText()
        ext = self.get_extension(driver)

        self.start_progress(len(layers), "레이어 저장 중...")

        success_count = 0
        errors = []

        for i, layer in enumerate(layers):
            self.update_progress(i, f"저장 중: {layer.name()}")

            safe_name = self.sanitize_filename(layer.name())
            output_path = os.path.join(folder, f"{safe_name}{ext}")

            try:
                options = QgsVectorFileWriter.SaveVectorOptions()
                options.driverName = driver
                options.fileEncoding = encoding

                error = QgsVectorFileWriter.writeAsVectorFormatV3(
                    layer, output_path,
                    QgsCoordinateTransformContext(), options
                )

                if error[0] == QgsVectorFileWriter.NoError:
                    success_count += 1
                else:
                    errors.append(f"{layer.name()}: {error[1]}")
            except Exception as e:
                errors.append(f"{layer.name()}: {str(e)}")

        self.finish_progress()

        message = f"{success_count}개 레이어가 저장되었습니다.\n저장 위치: {folder}"
        if errors:
            message += f"\n\n오류:\n" + "\n".join(errors)

        self.show_info(message)

    def execute_individual(self):
        """Save layers to individual paths."""
        if self.path_table.rowCount() == 0:
            self.show_warning("먼저 '선택된 레이어 불러오기' 버튼을 클릭해주세요.")
            return

        project = QgsProject.instance()
        encoding = self.encoding_combo.currentText()
        total = self.path_table.rowCount()

        self.start_progress(total, "레이어 개별 저장 중...")

        success_count = 0
        errors = []

        for row in range(total):
            layer_id = self.path_table.item(row, 0).data(Qt.UserRole)
            layer = project.mapLayer(layer_id)
            output_path = self.path_table.item(row, 2).text()

            if not layer or not output_path:
                continue

            self.update_progress(row, f"저장 중: {layer.name()}")

            ext = os.path.splitext(output_path)[1].lower()
            driver_map = {".shp": "ESRI Shapefile", ".gpkg": "GPKG", ".geojson": "GeoJSON"}
            driver = driver_map.get(ext, "ESRI Shapefile")

            try:
                options = QgsVectorFileWriter.SaveVectorOptions()
                options.driverName = driver
                options.fileEncoding = encoding

                error = QgsVectorFileWriter.writeAsVectorFormatV3(
                    layer, output_path,
                    QgsCoordinateTransformContext(), options
                )

                if error[0] == QgsVectorFileWriter.NoError:
                    success_count += 1
                else:
                    errors.append(f"{layer.name()}: {error[1]}")
            except Exception as e:
                errors.append(f"{layer.name()}: {str(e)}")

        self.finish_progress()

        message = f"{success_count}개 레이어가 저장되었습니다."
        if errors:
            message += f"\n\n오류:\n" + "\n".join(errors)

        self.show_info(message)
