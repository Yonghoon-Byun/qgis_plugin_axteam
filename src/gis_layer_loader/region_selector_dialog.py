# -*- coding: utf-8 -*-
"""
Region Selector Dialog with hierarchical selection and DB dynamic loading
Modern card-based UI design
"""

from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QWidget,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QGridLayout,
    QRadioButton,
    QButtonGroup,
    QDialogButtonBox,
)
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal
from qgis.PyQt.QtGui import QFont
from qgis.core import (
    QgsVectorLayer,
    QgsRasterLayer,
    QgsProject,
    QgsDataSourceUri,
    QgsMessageLog,
    Qgis,
)
import os
import csv
import psycopg2
from psycopg2 import sql


# Global stylesheet
DIALOG_STYLESHEET = """
* {
    font-family: 'Pretendard', 'Pretendard Variable', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
    font-weight: 500;
}
QDialog {
    background-color: #f9fafb;
}
QLabel {
    color: #374151;
    font-weight: 500;
}
QComboBox {
    border: 1px solid #d1d5db;
    border-radius: 4px;
    padding: 8px 12px;
    background-color: #f9fafb;
    font-size: 14px;
    color: #374151;
}
QComboBox:hover {
    border-color: #9ca3af;
    background-color: white;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    border: 1px solid #d1d5db;
    background-color: white;
    selection-background-color: #e5e7eb;
}
QLineEdit {
    border: 1px solid #d1d5db;
    border-radius: 4px;
    padding: 8px 12px;
    background-color: #f9fafb;
    font-size: 14px;
    color: #374151;
}
QLineEdit:hover {
    border-color: #9ca3af;
}
QLineEdit:focus {
    border-color: #6b7280;
    background-color: white;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical {
    background-color: #f3f4f6;
    width: 10px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background-color: #9ca3af;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #6b7280;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
QScrollBar:horizontal {
    background-color: #f3f4f6;
    height: 10px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background-color: #9ca3af;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #6b7280;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}
"""


class LayerListItem(QWidget):
    """Modern card-style layer list item with Add button"""

    def __init__(self, layer_info, callback, parent=None):
        super().__init__(parent)
        self.layer_info = layer_info
        self.layer_name = layer_info["name"]
        self.layer_type = layer_info.get("layer_type", "vector")
        self.callback = callback
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components for layer item"""
        self.setStyleSheet(
            """
            QWidget {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 4px;
            }
            QWidget:hover {
                border-color: #d1d5db;
                background-color: #fafafa;
            }
        """
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(8)

        # Layer type badge
        type_badge = QLabel("R" if self.layer_type == "raster" else "V")
        type_badge.setFixedSize(20, 20)
        if self.layer_type == "raster":
            type_badge.setStyleSheet(
                """
                background-color: #fef3c7;
                color: #92400e;
                font-size: 10px;
                font-weight: bold;
                border-radius: 10px;
                border: none;
            """
            )
        else:
            type_badge.setStyleSheet(
                """
                background-color: #dbeafe;
                color: #1e40af;
                font-size: 10px;
                font-weight: bold;
                border-radius: 10px;
                border: none;
            """
            )
        type_badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(type_badge)

        # Layer name label
        label = QLabel(self.layer_name)
        label.setStyleSheet(
            "font-size: 14px; font-weight: 600; color: #374151; border: none; background: transparent;"
        )
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(label)

        # Add button
        btn_add = QPushButton("+ 추가")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setFixedWidth(70)
        btn_add.setStyleSheet(
            """
            QPushButton {
                background-color: #1f2937;
                border: none;
                border-radius: 4px;
                color: white;
                font-size: 13px;
                font-weight: bold;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #374151;
            }
            QPushButton:pressed {
                background-color: #111827;
            }
        """
        )
        btn_add.clicked.connect(self._on_add_clicked)
        layout.addWidget(btn_add)

        self.setLayout(layout)

    def _on_add_clicked(self):
        """Handle Add button click"""
        if self.callback:
            self.callback(self.layer_info)


class DBLayerLoaderThread(QThread):
    """Worker thread for loading PostgreSQL DB layers without blocking UI"""

    # Signals
    progress_changed = pyqtSignal(int, str)  # (percentage, status_message)
    layer_loaded = pyqtSignal(
        object, str, int
    )  # (layer, full_layer_name, feature_count)
    error_occurred = pyqtSignal(str)  # (error_message)
    empty_result = pyqtSignal(str)  # (layer_name) - 쿼리 결과가 비었을 때

    def __init__(
        self,
        db_config,
        function_name,
        region_code,
        full_layer_name,
        layer_type="vector",
        extra_params=None,
        parent=None,
    ):
        super().__init__(parent)
        self.db_config = db_config
        self.function_name = function_name
        self.region_code = region_code
        self.full_layer_name = full_layer_name
        self.layer_type = layer_type
        self.extra_params = extra_params or {}
        self.layer = None

    def run(self):
        """Run the PostgreSQL DB layer loading in background thread"""
        try:
            self.progress_changed.emit(10, "DB 서버에 연결 중...")

            if self.layer_type == "raster":
                self._load_raster_layer()
            else:
                self._load_vector_layer()

        except Exception as e:
            self.error_occurred.emit(f"DB 레이어 로드 중 오류: {str(e)}")

    def _load_vector_layer(self):
        """Load vector layer from PostgreSQL with pre-check for empty results"""
        self.progress_changed.emit(30, "데이터 쿼리 중...")

        conn = None
        cursor = None

        try:
            # 1. Connect to database and check if data exists
            conn = psycopg2.connect(
                dbname=self.db_config["database"],
                host=self.db_config["host"],
                port=self.db_config["port"],
                user=self.db_config["user"],
                password=self.db_config["password"],
            )
            cursor = conn.cursor()

            # 2. Pre-check: count rows before loading layer
            # Build query based on whether extra_params has display_level
            if self.extra_params.get("display_level"):
                check_query = f"SELECT COUNT(*) FROM {self.db_config['schema']}.{self.function_name}('{self.region_code}', '{self.extra_params['display_level']}')"
            else:
                check_query = f"SELECT COUNT(*) FROM {self.db_config['schema']}.{self.function_name}('{self.region_code}')"

            QgsMessageLog.logMessage(
                f"[GIS Layer Loader] Pre-checking vector data: {check_query}",
                "GIS Layer Loader",
                Qgis.Info,
            )

            cursor.execute(check_query)
            row_count = cursor.fetchone()[0]

            if row_count == 0:
                QgsMessageLog.logMessage(
                    f"[GIS Layer Loader] No vector data for region {self.region_code}",
                    "GIS Layer Loader",
                    Qgis.Warning,
                )
                self.empty_result.emit(self.full_layer_name)
                return

            QgsMessageLog.logMessage(
                f"[GIS Layer Loader] Found {row_count} features, proceeding to load",
                "GIS Layer Loader",
                Qgis.Info,
            )

        except psycopg2.Error as e:
            error_msg = str(e)
            QgsMessageLog.logMessage(
                f"[GIS Layer Loader] Database pre-check error: {error_msg}",
                "GIS Layer Loader",
                Qgis.Critical,
            )
            self.error_occurred.emit(f"데이터 확인 중 오류 발생:\n\n{error_msg}")
            return
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        # 3. Now load the layer (we know it has data)
        self.progress_changed.emit(60, "피처 데이터 로딩 중...")

        uri = QgsDataSourceUri()
        uri.setConnection(
            self.db_config["host"],
            self.db_config["port"],
            self.db_config["database"],
            self.db_config["user"],
            self.db_config["password"],
        )

        # Build SQL query based on extra_params
        if self.extra_params.get("display_level"):
            sql = f"(SELECT * FROM {self.db_config['schema']}.{self.function_name}('{self.region_code}', '{self.extra_params['display_level']}'))"
        else:
            sql = f"(SELECT * FROM {self.db_config['schema']}.{self.function_name}('{self.region_code}'))"

        pk_col = "rid"
        uri.setDataSource("", sql, self.db_config["geom_column"], "", pk_col)

        # # Log connection URI (without password)
        # safe_uri = uri.uri().replace(
        #     f"password='{self.db_config['password']}'", "password='***'"
        # )
        # QgsMessageLog.logMessage(
        #     f"[GIS Layer Loader] Vector connection URI: {safe_uri}",
        #     "GIS Layer Loader",
        #     Qgis.Info,
        # )

        self.layer = QgsVectorLayer(uri.uri(), self.full_layer_name, "postgres")

        if not self.layer.isValid():
            error_msg = self.layer.error().message()
            QgsMessageLog.logMessage(
                f"[GIS Layer Loader] Vector layer load failed: {error_msg}",
                "GIS Layer Loader",
                Qgis.Critical,
            )
            self.error_occurred.emit(
                f"레이어를 로드할 수 없습니다.\n\nPostgreSQL 오류: {error_msg}"
            )
            return

        feature_count = self.layer.featureCount()
        QgsMessageLog.logMessage(
            f"[GIS Layer Loader] Vector layer loaded successfully: {feature_count} features",
            "GIS Layer Loader",
            Qgis.Success,
        )

        self.progress_changed.emit(90, "레이어 준비 중...")
        self.layer_loaded.emit(self.layer, self.full_layer_name, feature_count)
        self.progress_changed.emit(100, "완료!")

    def _load_raster_layer(self):
        """Load raster layer from PostgreSQL (PostGIS Raster) via temporary table"""
        self.progress_changed.emit(30, "래스터 데이터 쿼리 중...")

        temp_table = f"temp_raster_{self.region_code}"
        conn = None
        cursor = None

        try:
            # 1. Connect to database
            conn = psycopg2.connect(
                dbname=self.db_config["database"],
                host=self.db_config["host"],
                port=self.db_config["port"],
                user=self.db_config["user"],
                password=self.db_config["password"],
            )
            cursor = conn.cursor()

            QgsMessageLog.logMessage(
                f"[GIS Layer Loader] Creating temporary table: {temp_table}",
                "GIS Layer Loader",
                Qgis.Info,
            )

            self.progress_changed.emit(40, "임시 테이블 생성 중...")

            # 2. Create temporary table from function result
            cursor.execute(
                f"""
                DROP TABLE IF EXISTS {self.db_config['schema']}.{temp_table};
                CREATE TABLE {self.db_config['schema']}.{temp_table} AS
                SELECT * FROM {self.db_config['schema']}.{self.function_name}('{self.region_code}');
            """
            )
            conn.commit()

            # 3. Check if data exists
            cursor.execute(
                f"SELECT COUNT(*) FROM {self.db_config['schema']}.{temp_table}"
            )
            row_count = cursor.fetchone()[0]

            if row_count == 0:
                QgsMessageLog.logMessage(
                    f"[GIS Layer Loader] No raster data for region {self.region_code}",
                    "GIS Layer Loader",
                    Qgis.Warning,
                )
                cursor.execute(
                    f"DROP TABLE IF EXISTS {self.db_config['schema']}.{temp_table}"
                )
                conn.commit()
                self.empty_result.emit(self.full_layer_name)
                return

            self.progress_changed.emit(60, "GDAL로 래스터 로딩 중...")

            # 4. Build GDAL connection string for actual table
            direct_conn_str = (
                f"PG:dbname='{self.db_config['database']}' "
                f"host='{self.db_config['host']}' "
                f"port='{self.db_config['port']}' "
                f"user='{self.db_config['user']}' "
                f"password='{self.db_config['password']}' "
                f"mode=2 "
                f"schema='{self.db_config['schema']}' "
                f"table='{temp_table}' "
                f"column='{self.db_config['raster_column']}'"
            )

            # Log connection string (without password)
            safe_conn_str = direct_conn_str.replace(
                f"password='{self.db_config['password']}'", "password='***'"
            )
            QgsMessageLog.logMessage(
                f"[GIS Layer Loader] GDAL connection string: {safe_conn_str}",
                "GIS Layer Loader",
                Qgis.Info,
            )

            # 5. Load raster layer
            self.layer = QgsRasterLayer(direct_conn_str, self.full_layer_name, "gdal")

            if not self.layer.isValid():
                error_msg = self.layer.error().message()
                QgsMessageLog.logMessage(
                    f"[GIS Layer Loader] Raster layer load failed: {error_msg}",
                    "GIS Layer Loader",
                    Qgis.Critical,
                )
                # Clean up temp table
                cursor.execute(
                    f"DROP TABLE IF EXISTS {self.db_config['schema']}.{temp_table}"
                )
                conn.commit()

                # Check if error is due to empty result
                empty_patterns = [
                    "no rows",
                    "empty",
                    "0 rows",
                    "zero rows",
                    "no features",
                    "결과가 비어",
                ]

                is_empty_result = any(
                    pattern.lower() in error_msg.lower() for pattern in empty_patterns
                )

                if is_empty_result:
                    QgsMessageLog.logMessage(
                        f"[GIS Layer Loader] Empty raster result detected from error message",
                        "GIS Layer Loader",
                        Qgis.Warning,
                    )
                    self.empty_result.emit(self.full_layer_name)
                else:
                    self.error_occurred.emit(
                        f"래스터 레이어를 로드할 수 없습니다.\n\n"
                        f"GDAL 오류: {error_msg}\n\n"
                        f"가능한 원인:\n"
                        f"• PostGIS Raster 확장이 설치되지 않음\n"
                        f"• 래스터 컬럼명이 '{self.db_config['raster_column']}'이 아닐 수 있음"
                    )
                return

            # 6. Verify band count
            try:
                band_count = self.layer.bandCount()
                if band_count == 0:
                    QgsMessageLog.logMessage(
                        f"[GIS Layer Loader] Raster has zero bands",
                        "GIS Layer Loader",
                        Qgis.Warning,
                    )
                    cursor.execute(
                        f"DROP TABLE IF EXISTS {self.db_config['schema']}.{temp_table}"
                    )
                    conn.commit()
                    self.empty_result.emit(self.full_layer_name)
                    return

                QgsMessageLog.logMessage(
                    f"[GIS Layer Loader] Raster layer loaded successfully: {band_count} bands",
                    "GIS Layer Loader",
                    Qgis.Success,
                )

            except Exception as e:
                QgsMessageLog.logMessage(
                    f"[GIS Layer Loader] Error checking band count: {str(e)}",
                    "GIS Layer Loader",
                    Qgis.Critical,
                )
                cursor.execute(
                    f"DROP TABLE IF EXISTS {self.db_config['schema']}.{temp_table}"
                )
                conn.commit()
                self.error_occurred.emit(
                    f"래스터 밴드 정보를 가져올 수 없습니다.\n\n오류: {str(e)}"
                )
                return

            # 7. Clean up temporary table
            self.progress_changed.emit(90, "임시 테이블 정리 중...")
            cursor.execute(
                f"DROP TABLE IF EXISTS {self.db_config['schema']}.{temp_table}"
            )
            conn.commit()

            QgsMessageLog.logMessage(
                f"[GIS Layer Loader] Temporary table cleaned up: {temp_table}",
                "GIS Layer Loader",
                Qgis.Info,
            )

            # 8. Emit success
            self.progress_changed.emit(100, "완료!")
            self.layer_loaded.emit(self.layer, self.full_layer_name, band_count)

        except psycopg2.Error as e:
            error_msg = str(e)
            QgsMessageLog.logMessage(
                f"[GIS Layer Loader] Database error: {error_msg}",
                "GIS Layer Loader",
                Qgis.Critical,
            )
            self.error_occurred.emit(
                f"데이터베이스 오류가 발생했습니다.\n\n{error_msg}"
            )
        except Exception as e:
            error_msg = str(e)
            QgsMessageLog.logMessage(
                f"[GIS Layer Loader] Unexpected error: {error_msg}",
                "GIS Layer Loader",
                Qgis.Critical,
            )
            self.error_occurred.emit(f"예상치 못한 오류가 발생했습니다.\n\n{error_msg}")
        finally:
            # Clean up database connection
            if cursor:
                cursor.close()
            if conn:
                conn.close()


class RegionSelectorDialog(QDialog):
    """
    Modeless dialog for hierarchical region selection and DB layer loading
    Modern card-based UI design
    """

    # PostgreSQL DB Configuration (.env 기반 - pack_plugin.py 패키징 시 하드코딩으로 교체됨)
    from .db_env import (DB_HOST, DB_PORT, DB_NAME, DB_SCHEMA,
                         DB_USER, DB_PASSWORD, DB_GEOM_COLUMN,
                         DB_RASTER_COLUMN, DB_PK_COLUMN)

    # Available layers - 한글 가나다순, 영어순
    AVAILABLE_LAYERS = [
        {"name": "건축물정보", "function_name": "building_info_filter"},
        {"name": "단지경계", "function_name": "complex_outline_clip"},
        {"name": "단지시설용지", "function_name": "complex_facility_site_clip"},
        {"name": "단지용도지역", "function_name": "complex_landuse_clip"},
        {"name": "단지유치업종", "function_name": "complex_industry_clip"},
        {"name": "도로경계선", "function_name": "road_outline_clip"},
        {"name": "도로중심선", "function_name": "road_center_clip"},
        {"name": "등고선", "function_name": "contour_clip"},
        {"name": "연속지적도", "function_name": "cadastral_filtered"},
        {"name": "터널", "function_name": "tunnel_clip"},
        {"name": "토지소유정보", "function_name": "land_owner_info"},
        {"name": "하천경계", "function_name": "river_boundary_clip"},
        {"name": "하천중심선", "function_name": "river_centerline_clip"},
        {
            "name": "행정동 경계",
            "function_name": "admin_boundary_by_level",
            "layer_type": "vector",
            "geom_column": "geometry",
        },
        {"name": "호수 및 저수지", "function_name": "reservoir_clip"},
        {
            "name": "DEM 90m",
            "function_name": "dem_clip_by_region",
            "layer_type": "raster",
        },
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.region_data = self._load_region_data()
        self.loader_thread = None

        self.setWindowFlags(Qt.Window)
        self.setWindowTitle("지역별 GIS 데이터 로더")
        self.setMinimumSize(480, 700)
        self.resize(480, 750)
        self.setStyleSheet(DIALOG_STYLESHEET)

        self._setup_ui()
        self._initialize_region_data()

    def _load_region_data(self):
        """Load region data from CSV file"""
        csv_path = os.path.join(os.path.dirname(__file__), "admin_regions.csv")

        if not os.path.exists(csv_path):
            print(f"Error: CSV file not found at {csv_path}")
            return []

        region_data = []
        try:
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    region_data.append(
                        {"name": row["adm_nm"].strip(), "code": row["adm_cd"].strip()}
                    )
            print(f"Loaded {len(region_data)} regions from CSV file")
        except Exception as e:
            print(f"Error loading CSV file: {e}")

        return region_data

    def _setup_ui(self):
        """Setup main UI layout and components"""
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Content area
        content = QFrame()
        content.setStyleSheet("background-color: #f9fafb; border: none;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        # Region selection card
        region_card = self._create_region_card()
        content_layout.addWidget(region_card)

        # Layer list card
        layer_card = self._create_layer_card()
        content_layout.addWidget(layer_card, 1)

        content.setLayout(content_layout)
        layout.addWidget(content, 1)

        # Progress frame (hidden by default)
        self.progress_frame = self._create_progress_frame()
        layout.addWidget(self.progress_frame)

        # Footer
        footer = self._create_footer()
        layout.addWidget(footer)

        self.setLayout(layout)

    def _create_header(self):
        """Create header with title"""
        header = QFrame()
        header.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border-bottom: 1px solid #e5e7eb;
            }
        """
        )
        header.setFixedHeight(60)

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 0, 20, 0)

        # Title
        title = QLabel("지역별 GIS 데이터 로더")
        title.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #1f2937; border: none;"
        )
        layout.addWidget(title)

        layout.addStretch()

        header.setLayout(layout)
        return header

    def _create_region_card(self):
        """Create region selection card"""
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """
        )

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Card header
        header = QLabel("지역 선택")
        header.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #374151; border: none;"
        )
        layout.addWidget(header)

        # Description
        desc = QLabel("데이터를 불러올 지역을 선택하세요.")
        desc.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Region combos in grid
        grid = QGridLayout()
        grid.setSpacing(10)

        # Sido
        sido_label = QLabel("시도")
        sido_label.setFixedWidth(50)
        sido_label.setStyleSheet("color: #6b7280; font-size: 14px; border: none;")
        self.cbx_sido = QComboBox()
        self.cbx_sido.currentIndexChanged.connect(self._on_sido_changed)
        grid.addWidget(sido_label, 0, 0)
        grid.addWidget(self.cbx_sido, 0, 1)

        # Sigungu
        sigungu_label = QLabel("시군구")
        sigungu_label.setFixedWidth(50)
        sigungu_label.setStyleSheet("color: #6b7280; font-size: 14px; border: none;")
        self.cbx_sigungu = QComboBox()
        self.cbx_sigungu.currentIndexChanged.connect(self._on_sigungu_changed)
        grid.addWidget(sigungu_label, 1, 0)
        grid.addWidget(self.cbx_sigungu, 1, 1)

        # Emd
        emd_label = QLabel("읍면동")
        emd_label.setFixedWidth(50)
        emd_label.setStyleSheet("color: #6b7280; font-size: 14px; border: none;")
        self.cbx_emd = QComboBox()
        grid.addWidget(emd_label, 2, 0)
        grid.addWidget(self.cbx_emd, 2, 1)

        layout.addLayout(grid)

        # Info notice
        notice = self._create_info_notice()
        layout.addWidget(notice)

        card.setLayout(layout)
        return card

    def _create_info_notice(self):
        """Create info notice"""
        notice = QFrame()
        notice.setStyleSheet(
            """
            QFrame {
                background-color: #dbeafe;
                border: 1px solid #93c5fd;
                border-radius: 6px;
            }
        """
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)

        icon = QLabel("i")
        icon.setStyleSheet(
            """
            font-size: 13px;
            font-weight: bold;
            color: #1e40af;
            border: none;
            background-color: #93c5fd;
            border-radius: 8px;
            padding: 2px 6px;
        """
        )
        layout.addWidget(icon)

        text = QLabel("지역을 선택하면 해당 범위의 데이터만 DB에서 불러옵니다")
        text.setStyleSheet("font-size: 13px; color: #1e40af; border: none;")
        layout.addWidget(text)
        layout.addStretch()

        notice.setLayout(layout)
        return notice

    def _create_layer_card(self):
        """Create layer list card"""
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """
        )

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Card header with badge
        header_layout = QHBoxLayout()
        header = QLabel("레이어 목록")
        header.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #374151; border: none;"
        )
        header_layout.addWidget(header)

        # Legend
        legend_layout = QHBoxLayout()
        legend_layout.setSpacing(12)

        v_badge = QLabel("V 벡터")
        v_badge.setStyleSheet("font-size: 11px; color: #1e40af; border: none;")
        legend_layout.addWidget(v_badge)

        r_badge = QLabel("R 래스터")
        r_badge.setStyleSheet("font-size: 11px; color: #92400e; border: none;")
        legend_layout.addWidget(r_badge)

        header_layout.addStretch()
        header_layout.addLayout(legend_layout)
        layout.addLayout(header_layout)

        # Search box
        search_layout = QHBoxLayout()
        search_icon = QLabel("검색")
        search_icon.setFixedWidth(40)
        search_icon.setStyleSheet("color: #9ca3af; font-size: 13px; border: none;")
        self.txt_layer_search = QLineEdit()
        self.txt_layer_search.setPlaceholderText("레이어 이름으로 검색...")
        self.txt_layer_search.textChanged.connect(self._on_layer_search_changed)
        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.txt_layer_search)
        layout.addLayout(search_layout)

        # Scroll area for layer list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        # Container for layer items
        self.layer_container = QWidget()
        self.layer_container.setStyleSheet("background: transparent;")
        self.layer_container_layout = QVBoxLayout()
        self.layer_container_layout.setSpacing(4)
        self.layer_container_layout.setContentsMargins(0, 0, 0, 0)

        self.layer_item_widgets = []

        for layer_info in self.AVAILABLE_LAYERS:
            item_widget = LayerListItem(layer_info, self._on_layer_add_clicked)
            self.layer_container_layout.addWidget(item_widget)
            self.layer_item_widgets.append(
                {"widget": item_widget, "name": layer_info["name"]}
            )

        self.layer_container_layout.addStretch()
        self.layer_container.setLayout(self.layer_container_layout)
        scroll.setWidget(self.layer_container)

        layout.addWidget(scroll)
        card.setLayout(layout)
        return card

    def _create_progress_frame(self):
        """Create progress indicator frame"""
        frame = QFrame()
        frame.setStyleSheet(
            """
            QFrame {
                background-color: #fef3c7;
                border-top: 1px solid #fcd34d;
            }
        """
        )
        frame.setFixedHeight(50)
        frame.setVisible(False)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 8, 20, 8)

        self.lbl_status = QLabel("처리 중...")
        self.lbl_status.setStyleSheet("color: #92400e; font-size: 13px; border: none;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                background-color: #fde68a;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #f59e0b;
                border-radius: 3px;
            }
        """
        )
        layout.addWidget(self.progress_bar)

        frame.setLayout(layout)
        return frame

    def _create_footer(self):
        """Create footer with close button"""
        footer = QFrame()
        footer.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border-top: 1px solid #e5e7eb;
            }
        """
        )
        footer.setFixedHeight(60)

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 10, 20, 10)

        # Selected region display
        self.lbl_selected_region = QLabel("선택된 지역: 없음")
        self.lbl_selected_region.setStyleSheet(
            "color: #6b7280; font-size: 13px; border: none;"
        )
        layout.addWidget(self.lbl_selected_region)

        layout.addStretch()

        # Close button
        btn_close = QPushButton("닫기")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                color: #6b7280;
                font-size: 14px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #f3f4f6;
                border-color: #9ca3af;
            }
        """
        )
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        footer.setLayout(layout)
        return footer

    def _on_layer_search_changed(self, text):
        """Handle layer search text change"""
        search_text = text.lower().strip()

        for item_info in self.layer_item_widgets:
            widget = item_info["widget"]
            name = item_info["name"]

            if search_text == "" or search_text in name.lower():
                widget.setVisible(True)
            else:
                widget.setVisible(False)

    def _initialize_region_data(self):
        """Initialize region comboboxes with data"""
        self._load_sido()

    def _korean_english_sort_key(self, name):
        """
        Sort key function for Korean-English-Number ordering
        Returns tuple (priority, name) where:
        - 0: Korean (가-힣)
        - 1: English (a-z, A-Z)
        - 2: Numbers and others
        """
        if not name:
            return (2, name)
        first_char = name[0]
        if 0xAC00 <= ord(first_char) <= 0xD7A3:  # Korean
            return (0, name)
        elif first_char.isalpha():  # English
            return (1, name)
        else:  # Numbers and others
            return (2, name)

    def _load_sido(self):
        """Load sido items into combobox"""
        self.cbx_sido.clear()
        self.cbx_sido.addItem("-- 선택하세요 --", None)

        sido_list = [item for item in self.region_data if len(item["code"]) == 2]
        sido_list = sorted(
            sido_list, key=lambda x: self._korean_english_sort_key(x["name"])
        )

        for sido in sido_list:
            self.cbx_sido.addItem(sido["name"], sido["code"])

    def _load_sigungu(self, sido_code):
        """Load sigungu items filtered by sido code"""
        self.cbx_sigungu.clear()
        self.cbx_sigungu.addItem("-- 선택하세요 --", None)

        if not sido_code:
            return

        sigungu_list = [
            item
            for item in self.region_data
            if len(item["code"]) == 5 and item["code"].startswith(sido_code)
        ]
        sigungu_list = sorted(
            sigungu_list, key=lambda x: self._korean_english_sort_key(x["name"])
        )

        for sigungu in sigungu_list:
            self.cbx_sigungu.addItem(sigungu["name"], sigungu["code"])

    def _load_emd(self, sigungu_code):
        """Load emd items filtered by sigungu code"""
        self.cbx_emd.clear()
        self.cbx_emd.addItem("-- 선택하세요 --", None)

        if not sigungu_code:
            return

        emd_list = [
            item
            for item in self.region_data
            if len(item["code"]) == 8 and item["code"].startswith(sigungu_code)
        ]
        emd_list = sorted(
            emd_list, key=lambda x: self._korean_english_sort_key(x["name"])
        )

        for emd in emd_list:
            self.cbx_emd.addItem(emd["name"], emd["code"])

    def _on_sido_changed(self, index):
        """Handle sido selection change"""
        self.cbx_sigungu.clear()
        self.cbx_emd.clear()

        sido_code = self.cbx_sido.currentData()

        if sido_code:
            self._load_sigungu(sido_code)

        self._update_selected_region_label()

    def _on_sigungu_changed(self, index):
        """Handle sigungu selection change"""
        self.cbx_emd.clear()

        sigungu_code = self.cbx_sigungu.currentData()

        if sigungu_code:
            self._load_emd(sigungu_code)

        self._update_selected_region_label()

    def _update_selected_region_label(self):
        """Update the selected region label in footer"""
        region_code = self._get_selected_region_code()
        if region_code:
            region_name = self._get_region_name(region_code)
            self.lbl_selected_region.setText(f"선택된 지역: {region_name}")
            self.lbl_selected_region.setStyleSheet(
                "color: #059669; font-size: 13px; font-weight: bold; border: none;"
            )
        else:
            self.lbl_selected_region.setText("선택된 지역: 없음")
            self.lbl_selected_region.setStyleSheet(
                "color: #6b7280; font-size: 13px; border: none;"
            )

    def _get_selected_region_code(self):
        """Get the most specific selected region code"""
        emd_code = self.cbx_emd.currentData()
        if emd_code:
            return emd_code

        sigungu_code = self.cbx_sigungu.currentData()
        if sigungu_code:
            return sigungu_code

        sido_code = self.cbx_sido.currentData()
        return sido_code

    def _on_layer_add_clicked(self, layer_info):
        """Handle layer Add button click"""
        region_code = self._get_selected_region_code()

        if not region_code:
            QMessageBox.warning(
                self,
                "지역 선택 필요",
                "레이어를 추가하기 전에 지역을 선택해주세요.\n\n"
                "시도 → 시군구 → 읍면동 순서로 선택하세요.",
            )
            return

        layer_name = layer_info["name"]
        function_name = layer_info.get("function_name", "")
        layer_type = layer_info.get("layer_type", "vector")
        geom_column = layer_info.get("geom_column", None)

        if not function_name:
            QMessageBox.warning(
                self,
                "기능 미구현",
                f"'{layer_name}' 레이어는 아직 DB function이 구현되지 않았습니다.",
            )
            return

        # Handle admin_boundary_by_level layer with display level selection
        if function_name == "admin_boundary_by_level":
            display_level = self._select_admin_display_level()
            if not display_level:
                return  # User cancelled

            # Add level to layer name
            level_names = {"sido": "시도", "sigungu": "시군구", "emd": "읍면동"}
            layer_name = f"{layer_name} ({level_names[display_level]})"

            # Pass extra_params and geom_column to load function
            self._load_db_layer(
                layer_name,
                function_name,
                region_code,
                layer_type,
                extra_params={"display_level": display_level},
                geom_column=geom_column,
            )
        else:
            self._load_db_layer(
                layer_name,
                function_name,
                region_code,
                layer_type,
                geom_column=geom_column,
            )

    def _load_db_layer(
        self,
        layer_name,
        function_name,
        region_code,
        layer_type="vector",
        extra_params=None,
        geom_column=None,
    ):
        """Load PostgreSQL DB layer using background thread"""
        region_name = self._get_region_name(region_code)
        full_layer_name = f"{layer_name} ({region_name})"

        layer_type_text = "래스터" if layer_type == "raster" else "벡터"

        msg_box = QMessageBox(self)
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        msg_box.setFont(font)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("DB 레이어 로딩")
        msg_box.setText(f"'{layer_name}' {layer_type_text} 레이어를 불러옵니다.")
        msg_box.setInformativeText(
            f"지역: {region_name}\n"
            f"레이어 타입: {layer_type_text}\n\n"
            f"계속하시겠습니까?"
        )
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg_box.setDefaultButton(QMessageBox.Ok)

        if msg_box.exec_() == QMessageBox.Cancel:
            return

        self._show_progress()

        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.quit()
            self.loader_thread.wait()

        db_config = {
            "host": self.DB_HOST,
            "port": self.DB_PORT,
            "database": self.DB_NAME,
            "schema": self.DB_SCHEMA,
            "user": self.DB_USER,
            "password": self.DB_PASSWORD,
            "geom_column": geom_column if geom_column else self.DB_GEOM_COLUMN,
            "raster_column": self.DB_RASTER_COLUMN,
            "pk_column": self.DB_PK_COLUMN,
        }

        self.loader_thread = DBLayerLoaderThread(
            db_config,
            function_name,
            region_code,
            full_layer_name,
            layer_type,
            extra_params,
            self,
        )

        self.loader_thread.progress_changed.connect(self._update_progress)
        self.loader_thread.layer_loaded.connect(self._on_layer_loaded)
        self.loader_thread.error_occurred.connect(self._on_db_layer_error)
        self.loader_thread.empty_result.connect(self._on_empty_result)

        self.loader_thread.start()

    def _get_region_name(self, region_code):
        """Get region name from code"""
        for item in self.region_data:
            if item["code"] == region_code:
                return item["name"]
        return region_code

    def _update_progress(self, percentage, status_message):
        """Update progress bar and status label"""
        self.progress_bar.setValue(percentage)
        self.lbl_status.setText(status_message)

    def _show_progress(self):
        """Show progress frame"""
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("준비 중...")

    def _hide_progress(self):
        """Hide progress frame"""
        self.progress_frame.setVisible(False)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("대기 중...")

    def _on_layer_loaded(self, layer, full_layer_name, feature_count):
        """Handle successful layer loading"""
        try:
            if feature_count == 0:
                region_code = self._get_selected_region_code()
                region_name = self._get_region_name(region_code)
                QMessageBox.warning(
                    self,
                    "데이터 없음",
                    f"선택된 지역({region_name})에 해당하는 데이터가 없습니다.\n\n"
                    f"다른 지역을 선택하거나 데이터를 확인해주세요.",
                )
                self._hide_progress()
                return

            data_provider = layer.dataProvider()
            has_errors = False
            error_message = ""

            if data_provider:
                provider_error = data_provider.error()
                if provider_error and provider_error.message():
                    has_errors = True
                    error_message = provider_error.message()

            QgsProject.instance().addMapLayer(layer)
            self._hide_progress()

            region_code = self._get_selected_region_code()
            region_name = self._get_region_name(region_code)

            if has_errors:
                msg_box = QMessageBox(self)
                font = QFont()
                font.setPointSize(10)
                font.setBold(True)
                msg_box.setFont(font)
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("레이어 추가 완료 (경고)")
                msg_box.setText(
                    f"'{full_layer_name}' 레이어가 추가되었습니다.\n"
                    f"데이터 개수: {feature_count:,}개\n\n"
                    f"일부 데이터가 누락되었을 수 있습니다."
                )
                msg_box.exec_()
            else:
                msg_box = QMessageBox(self)
                font = QFont()
                font.setPointSize(10)
                font.setBold(True)
                msg_box.setFont(font)
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setWindowTitle("레이어 추가 완료")
                msg_box.setText(
                    f"'{full_layer_name}' 레이어가 추가되었습니다.\n\n"
                    f"데이터 개수: {feature_count:,}개\n"
                    f"지역: {region_name}"
                )
                msg_box.exec_()

        except Exception as e:
            self._hide_progress()
            QMessageBox.critical(
                self,
                "오류 발생",
                f"레이어 추가 중 오류가 발생했습니다:\n\n{str(e)}",
            )

    def _on_db_layer_error(self, error_message):
        """Handle DB layer loading error"""
        self._hide_progress()

        QMessageBox.critical(
            self,
            "DB 레이어 로드 실패",
            f"{error_message}\n\n"
            f"가능한 원인:\n"
            f"• PostgreSQL DB 서버 연결 실패\n"
            f"• 인증 실패 (사용자/비밀번호)\n"
            f"• Function이 존재하지 않음\n"
            f"• 네트워크 연결 문제",
        )

    def _on_empty_result(self, layer_name):
        """Handle empty query result"""
        self._hide_progress()

        region_code = self._get_selected_region_code()
        region_name = self._get_region_name(region_code)

        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("조회 결과 없음")
        msg_box.setText(
            f"'{layer_name}' 레이어 조회 결과가 없습니다.\n\n"
            f"선택 지역: {region_name}\n"
            f"지역 코드: {region_code}\n\n"
            f"선택한 지역에 해당 데이터가 존재하지 않습니다.\n"
            f"다른 지역을 선택하거나 데이터 범위를 확인해주세요."
        )
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        msg_box.setFont(font)
        msg_box.exec_()

    def _select_admin_display_level(self):
        """Show dialog to select administrative boundary display level"""
        dialog = QDialog(self)
        dialog.setWindowTitle("표시 레벨 선택")
        dialog.setMinimumWidth(300)

        layout = QVBoxLayout()

        # Description label
        label = QLabel("행정구역 집계 단위를 선택하세요:")
        layout.addWidget(label)

        # Radio button group
        button_group = QButtonGroup(dialog)

        rb_sido = QRadioButton("시도 (예: 서울특별시)")
        rb_sigungu = QRadioButton("시군구 (예: 종로구, 중구)")
        rb_emd = QRadioButton("읍면동 (예: 사직동, 청운동)")

        rb_sigungu.setChecked(True)  # Default value

        button_group.addButton(rb_sido, 1)
        button_group.addButton(rb_sigungu, 2)
        button_group.addButton(rb_emd, 3)

        layout.addWidget(rb_sido)
        layout.addWidget(rb_sigungu)
        layout.addWidget(rb_emd)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)

        if dialog.exec_() == QDialog.Accepted:
            button_id = button_group.checkedId()
            level_map = {1: "sido", 2: "sigungu", 3: "emd"}
            return level_map[button_id]
        return None
