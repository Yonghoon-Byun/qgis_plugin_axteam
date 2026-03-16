"""
Statistics Data Loader with LIKE-based aggregation
"""

from qgis.PyQt.QtCore import QObject, pyqtSignal, QThread


class StatisticsLoaderThread(QThread):
    """Worker thread for loading statistics data."""

    progress_changed = pyqtSignal(int, str)
    data_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, db_connection, config, parent=None):
        """Initialize the loader thread.

        :param db_connection: DBConnection instance
        :param config: Dictionary with loading configuration
        :param parent: Parent QObject
        """
        super().__init__(parent)
        self.db = db_connection
        self.config = config

    def run(self):
        """Run the statistics loading in background."""
        try:
            self.progress_changed.emit(10, "통계 테이블 연결 중...")

            region_code = self.config["region_code"]
            display_level = self.config["display_level"]
            years = self.config["years"]
            stat_configs = self.config["statistics"]  # List of {table, columns}

            all_data = {}

            total_tables = len(stat_configs)
            for idx, stat_config in enumerate(stat_configs):
                table_name = stat_config["table"]
                display_name = stat_config.get("display_name", table_name)
                columns = stat_config["columns"]

                progress = 10 + int((idx / total_tables) * 70)
                self.progress_changed.emit(
                    progress, f"{display_name} 데이터 로딩 중..."
                )

                data = self.db.get_statistics_data(
                    table_name, columns, region_code, years, display_level
                )

                all_data[table_name] = {
                    "columns": columns,
                    "data": data,
                }

            self.progress_changed.emit(90, "데이터 처리 완료...")
            self.data_loaded.emit(all_data)
            self.progress_changed.emit(100, "완료!")

        except Exception as e:
            self.error_occurred.emit(f"통계 로딩 실패: {str(e)}")


class StatisticsLoader(QObject):
    """Statistics data loader with aggregation support."""

    # Signals
    progress_changed = pyqtSignal(int, str)
    loading_finished = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    # Available statistics tables
    STATISTICS_TABLES = {
        "population": {
            "table": "sgis_population",
            "display_name": "인구통계",
            "columns": {
                "population": "인구수",
            },
        },
        "household": {
            "table": "sgis_gagu",
            "display_name": "가구통계",
            "columns": {
                "household_cnt": "가구수",
                "avg_family_member_cnt": "평균가구원수",
                "family_member_cnt": "총가구원수",
            },
        },
        "housing": {
            "table": "sgis_house",
            "display_name": "주택통계",
            "columns": {
                "house_cnt": "주택수",
            },
        },
        "water_supply": {
            "table": "fact_water_supply",
            "display_name": "상수도통계",
            "columns": {
                "m6_total_supply": "총급수량_m3",
                "m10_revenue_water": "유수수량_m3",
                "m34_daily_supply": "1인1일급수량",
                "m35_daily_usage": "1인1일사용량",
            },
        },
    }

    def __init__(self, db_connection, parent=None):
        """Initialize the statistics loader.

        :param db_connection: DBConnection instance
        :param parent: Parent QObject
        """
        super().__init__(parent)
        self.db = db_connection
        self._loader_thread = None
        self._loaded_data = {}

    def get_available_statistics(self):
        """Get list of available statistics.

        :returns: Dictionary of available statistics configurations
        :rtype: dict
        """
        return self.STATISTICS_TABLES

    def get_available_years(self, table_key):
        """Get available years for a statistics table.

        :param table_key: Key for the statistics table
        :returns: List of available years
        :rtype: list
        """
        if table_key not in self.STATISTICS_TABLES:
            return []

        table_name = self.STATISTICS_TABLES[table_key]["table"]
        return self.db.get_available_years(table_name)

    def load_statistics(self, region_code, display_level, years, selected_stats):
        """Load statistics data asynchronously.

        :param region_code: Region code prefix
        :param display_level: Display level (2, 5, or 8)
        :param years: List of years to load
        :param selected_stats: Dictionary of {stat_key: [column_names]}
        """
        # Build configuration for loader
        stat_configs = []
        for stat_key, columns in selected_stats.items():
            if stat_key in self.STATISTICS_TABLES:
                stat_configs.append({
                    "table": self.STATISTICS_TABLES[stat_key]["table"],
                    "display_name": self.STATISTICS_TABLES[stat_key]["display_name"],
                    "columns": columns,
                })

        if not stat_configs:
            self.error_occurred.emit("선택된 통계가 없습니다.")
            return

        config = {
            "region_code": region_code,
            "display_level": display_level,
            "years": years,
            "statistics": stat_configs,
        }

        # Stop existing thread if running
        if self._loader_thread and self._loader_thread.isRunning():
            self._loader_thread.quit()
            self._loader_thread.wait()

        # Create and start loader thread
        self._loader_thread = StatisticsLoaderThread(self.db, config, self)
        self._loader_thread.progress_changed.connect(self.progress_changed)
        self._loader_thread.data_loaded.connect(self._on_data_loaded)
        self._loader_thread.error_occurred.connect(self.error_occurred)
        self._loader_thread.start()

    def _on_data_loaded(self, data):
        """Handle loaded data."""
        self._loaded_data = data
        self.loading_finished.emit(data)

    def get_loaded_data(self):
        """Get the last loaded data.

        :returns: Dictionary of loaded statistics data
        :rtype: dict
        """
        return self._loaded_data

    def _get_column_display_name(self, column_name):
        """Get Korean display name for a database column.

        :param column_name: Database column name
        :returns: Korean display name
        :rtype: str
        """
        # Search all statistics tables for the column
        for stat_info in self.STATISTICS_TABLES.values():
            if column_name in stat_info["columns"]:
                return stat_info["columns"][column_name]
        # Return original name if not found
        return column_name

    def transform_data_for_join(self, data, year):
        """Transform loaded data into format suitable for joining.

        :param data: Loaded statistics data
        :param year: Year to filter
        :returns: Dictionary keyed by adm_cd with column values
        :rtype: dict
        """
        result = {}

        for table_name, table_data in data.items():
            for row in table_data["data"]:
                # Compare as integers to handle type mismatch (DB may return str or int)
                row_year = int(row.get("year", 0))
                if row_year != int(year):
                    continue

                adm_cd = row["adm_cd"]
                if adm_cd not in result:
                    result[adm_cd] = {}

                for col in table_data["columns"]:
                    if col in row:
                        # Use Korean display name for the field
                        display_name = self._get_column_display_name(col)
                        col_name = f"{display_name}_{year}"
                        result[adm_cd][col_name] = row[col]

        return result
