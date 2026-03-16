"""
Database Connection Manager for PostgreSQL
"""

import psycopg2
from psycopg2 import sql
from qgis.core import QgsDataSourceUri, QgsVectorLayer
from qgis.PyQt.QtCore import QObject, pyqtSignal


class DBConnection(QObject):
    """PostgreSQL Database Connection Manager."""

    # Signals
    connection_error = pyqtSignal(str)
    query_error = pyqtSignal(str)

    # Default connection parameters (.env 기반 - pack_plugin.py 패키징 시 하드코딩으로 교체됨)
    from ..db_env import (DB_HOST, DB_PORT, DB_NAME, DB_SCHEMA,
                          DB_USER, DB_PASSWORD, DB_GEOM_COLUMN, DB_PK_COLUMN)
    DEFAULT_CONFIG = {
        "host": DB_HOST,
        "port": DB_PORT,
        "database": DB_NAME,
        "schema": DB_SCHEMA,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "geom_column": DB_GEOM_COLUMN,
        "pk_column": DB_PK_COLUMN,
    }

    def __init__(self, config=None, parent=None):
        """Initialize database connection.

        :param config: Database configuration dictionary (optional)
        :param parent: Parent QObject
        """
        super().__init__(parent)
        self.config = config or self.DEFAULT_CONFIG.copy()
        self._connection = None

    @property
    def connection(self):
        """Get or create database connection."""
        if self._connection is None or self._connection.closed:
            self._connection = self._create_connection()
        return self._connection

    def _create_connection(self):
        """Create a new database connection."""
        try:
            conn = psycopg2.connect(
                host=self.config["host"],
                port=self.config["port"],
                database=self.config["database"],
                user=self.config["user"],
                password=self.config["password"],
            )
            return conn
        except psycopg2.Error as e:
            self.connection_error.emit(f"DB 연결 실패: {str(e)}")
            return None

    def test_connection(self):
        """Test the database connection.

        :returns: True if connection is successful, False otherwise
        :rtype: bool
        """
        try:
            conn = self._create_connection()
            if conn:
                conn.close()
                return True
            return False
        except Exception as e:
            self.connection_error.emit(f"연결 테스트 실패: {str(e)}")
            return False

    def execute_query(self, query, params=None):
        """Execute a SELECT query and return results.

        :param query: SQL query string
        :param params: Query parameters (optional)
        :returns: List of dictionaries with query results
        :rtype: list
        """
        try:
            conn = self.connection
            if conn is None:
                return []

            with conn.cursor() as cursor:
                cursor.execute(query, params)
                columns = [desc[0] for desc in cursor.description]
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                return results

        except psycopg2.Error as e:
            self.query_error.emit(f"쿼리 실행 실패: {str(e)}")
            return []

    def get_available_years(self, table_name):
        """Get list of available years from a statistics table.

        :param table_name: Name of the statistics table
        :returns: List of available years
        :rtype: list
        """
        query = f"""
            SELECT DISTINCT year
            FROM {self.config['schema']}.{table_name}
            ORDER BY year
        """
        results = self.execute_query(query)
        return [r["year"] for r in results]

    def get_statistics_data(
        self, table_name, columns, region_code, years, display_level
    ):
        """Get aggregated statistics data.

        :param table_name: Name of the statistics table
        :param columns: List of column names to retrieve (will be aggregated with SUM)
        :param region_code: Region code prefix for filtering
        :param years: List of years to include
        :param display_level: Display level (2=sido, 5=sigungu, 8=emd)
        :returns: List of dictionaries with statistics data
        :rtype: list
        """
        # Build aggregation columns
        # Use CASE to safely convert to numeric, handling empty strings and non-numeric values
        agg_parts = []
        for col in columns:
            # Use regex to validate numeric format before conversion
            # This handles empty strings, NULL, and non-numeric text values safely
            agg_parts.append(
                f"SUM(CASE WHEN {col}::text ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN {col}::numeric ELSE NULL END) as {col}"
            )
        agg_columns = ", ".join(agg_parts)

        # Build year filter
        year_filter = ",".join([str(y) for y in years])

        # Query with grouping based on display level
        query = f"""
            SELECT
                LEFT(adm_cd, {display_level}) as adm_cd,
                year,
                {agg_columns}
            FROM {self.config['schema']}.{table_name}
            WHERE adm_cd LIKE %s
              AND year IN ({year_filter})
            GROUP BY LEFT(adm_cd, {display_level}), year
            ORDER BY adm_cd, year
        """

        return self.execute_query(query, (f"{region_code}%",))

    def get_boundaries_layer(self, region_code, display_level, layer_name="행정구역"):
        """Create a QGIS vector layer for administrative boundaries.

        :param region_code: Region code prefix for filtering
        :param display_level: Display level (2=sido, 5=sigungu, 8=emd)
        :param layer_name: Name for the layer
        :returns: QgsVectorLayer or None if failed
        :rtype: QgsVectorLayer
        """
        uri = QgsDataSourceUri()
        uri.setConnection(
            self.config["host"],
            self.config["port"],
            self.config["database"],
            self.config["user"],
            self.config["password"],
        )

        uri.setDataSource(
            self.config["schema"],
            "sgis_hjd",
            self.config["geom_column"],
            f"LENGTH(adm_cd) = {display_level} AND adm_cd LIKE '{region_code}%'",
            "adm_cd",  # primary key (unique administrative code)
        )

        layer = QgsVectorLayer(uri.uri(), layer_name, "postgres")

        if not layer.isValid():
            self.query_error.emit(f"레이어 생성 실패: {layer_name}")
            return None

        return layer

    def close(self):
        """Close the database connection."""
        if self._connection and not self._connection.closed:
            self._connection.close()
            self._connection = None
