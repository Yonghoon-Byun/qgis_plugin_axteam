# -*- coding: utf-8 -*-
"""
레이어 로더 - PostGIS DB에서 범위(bbox) 기반으로 레이어를 로드

동작 방식:
1. 범위 폴리곤의 extent → DB CRS(5179) 변환
2. sgis_hjd 테이블에서 해당 범위와 겹치는 행정구역 코드 자동 감지
3. 기존 DB 함수(function_name)를 감지된 행정구역 코드로 호출
4. 결과를 범위로 추가 클리핑
"""

import re

from qgis.PyQt.QtCore import QThread, pyqtSignal
from qgis.core import (
    QgsVectorLayer, QgsRasterLayer, QgsProject,
    QgsDataSourceUri, QgsRectangle,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsMessageLog, Qgis,
)

from ..db_env import (
    DB_HOST, DB_PORT, DB_NAME, DB_SCHEMA,
    DB_USER, DB_PASSWORD, DB_GEOM_COLUMN,
)

# DB 저장 좌표계
DB_SRID = 5179

# 레이어 목록: gis_layer_loader의 DB 함수와 동일
AVAILABLE_LAYERS = [
    {"name": "건축물정보", "function_name": "building_info_filter", "geom_column": "geom", "layer_type": "vector"},
    {"name": "단지경계", "function_name": "complex_outline_clip", "geom_column": "geom", "layer_type": "vector"},
    {"name": "단지시설용지", "function_name": "complex_facility_site_clip", "geom_column": "geom", "layer_type": "vector"},
    {"name": "단지용도지역", "function_name": "complex_landuse_clip", "geom_column": "geom", "layer_type": "vector"},
    {"name": "단지유치업종", "function_name": "complex_industry_clip", "geom_column": "geom", "layer_type": "vector"},
    {"name": "도로경계선", "function_name": "road_outline_clip", "geom_column": "geom", "layer_type": "vector"},
    {"name": "도로중심선", "function_name": "road_center_clip", "geom_column": "geom", "layer_type": "vector"},
    {"name": "등고선", "function_name": "contour_clip", "geom_column": "geom", "layer_type": "vector"},
    {
        "name": "연속지적도",
        "function_name": "lsmd_cont_ldreg",
        "geom_column": "geom",
        "layer_type": "vector",
        "query_type": "spatial",  # 테이블 직접 공간쿼리
        "pk_column": "ufid",
    },
    {"name": "터널", "function_name": "tunnel_clip", "geom_column": "geom", "layer_type": "vector"},
    {"name": "토지소유정보", "function_name": "land_owner_info", "geom_column": "geom", "layer_type": "vector"},
    {"name": "하천경계", "function_name": "river_boundary_clip", "geom_column": "geom", "layer_type": "vector"},
    {"name": "하천중심선", "function_name": "river_centerline_clip", "geom_column": "geom", "layer_type": "vector"},
    {
        "name": "행정동 경계",
        "function_name": "sgis_hjd",
        "geom_column": "geometry",
        "layer_type": "vector",
        "query_type": "table",
        "pk_column": "adm_cd",
    },
    {"name": "호수 및 저수지", "function_name": "reservoir_clip", "geom_column": "geom", "layer_type": "vector"},
    {"name": "DEM 90m", "function_name": "korea_dem_90m", "layer_type": "raster"},
]


def transform_extent_to_db(extent, project_crs):
    """프로젝트 CRS의 extent를 DB CRS(5179)로 변환"""
    db_crs = QgsCoordinateReferenceSystem(f"EPSG:{DB_SRID}")
    if project_crs.authid() == db_crs.authid():
        return extent
    transform = QgsCoordinateTransform(project_crs, db_crs, QgsProject.instance())
    return transform.transformBoundingBox(extent)


def detect_region_code(extent_5179):
    """범위와 겹치는 행정구역 코드를 sgis_hjd에서 자동 감지

    sgis_hjd 테이블에서 범위와 교차하는 시도(2자리) 코드를 찾습니다.
    메인 스레드에서 호출해야 합니다.

    Args:
        extent_5179: QgsRectangle (EPSG:5179)

    Returns:
        str: 시도 코드 (예: "11") 또는 None
    """
    xmin = extent_5179.xMinimum()
    ymin = extent_5179.yMinimum()
    xmax = extent_5179.xMaximum()
    ymax = extent_5179.yMaximum()

    # sgis_hjd에서 범위와 교차하는 가장 넓은(시도급) 행정구역 찾기
    sql_filter = (
        f"ST_Intersects(geometry, "
        f"ST_MakeEnvelope({xmin}, {ymin}, {xmax}, {ymax}, {DB_SRID})) "
        f"AND LENGTH(adm_cd) = 2"
    )

    uri = QgsDataSourceUri()
    uri.setConnection(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
    uri.setDataSource(DB_SCHEMA, "sgis_hjd", "geometry", sql_filter, "adm_cd")

    layer = QgsVectorLayer(uri.uri(), "_region_detect", "postgres")
    if not layer.isValid() or layer.featureCount() <= 0:
        return None

    # 첫 번째 시도 코드 반환
    for feat in layer.getFeatures():
        return feat["adm_cd"]

    return None


def detect_emd_codes(extent_5179):
    """범위와 겹치는 읍면동(8자리+) 코드를 모두 감지

    가장 세밀한 단위로 감지하여 DB 함수 호출 시 소량 데이터만 반환되도록 합니다.
    메인 스레드에서 호출해야 합니다.

    Args:
        extent_5179: QgsRectangle (EPSG:5179)

    Returns:
        list[str]: 읍면동 코드 리스트 (예: ["31240101", "31240102"]) 또는 빈 리스트
    """
    xmin = extent_5179.xMinimum()
    ymin = extent_5179.yMinimum()
    xmax = extent_5179.xMaximum()
    ymax = extent_5179.yMaximum()

    sql_filter = (
        f"ST_Intersects(geometry, "
        f"ST_MakeEnvelope({xmin}, {ymin}, {xmax}, {ymax}, {DB_SRID})) "
        f"AND LENGTH(adm_cd) >= 8"
    )

    uri = QgsDataSourceUri()
    uri.setConnection(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
    uri.setDataSource(DB_SCHEMA, "sgis_hjd", "geometry", sql_filter, "adm_cd")

    layer = QgsVectorLayer(uri.uri(), "_emd_detect", "postgres")
    if not layer.isValid() or layer.featureCount() <= 0:
        return []

    return [feat["adm_cd"] for feat in layer.getFeatures()]


def detect_sigungu_code(extent_5179):
    """범위와 겹치는 시군구(5자리) 코드를 감지 (폴백용)
    메인 스레드에서 호출해야 합니다.
    """
    xmin = extent_5179.xMinimum()
    ymin = extent_5179.yMinimum()
    xmax = extent_5179.xMaximum()
    ymax = extent_5179.yMaximum()

    sql_filter = (
        f"ST_Intersects(geometry, "
        f"ST_MakeEnvelope({xmin}, {ymin}, {xmax}, {ymax}, {DB_SRID})) "
        f"AND LENGTH(adm_cd) = 5"
    )

    uri = QgsDataSourceUri()
    uri.setConnection(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
    uri.setDataSource(DB_SCHEMA, "sgis_hjd", "geometry", sql_filter, "adm_cd")

    layer = QgsVectorLayer(uri.uri(), "_sigungu_detect", "postgres")
    if not layer.isValid() or layer.featureCount() <= 0:
        return None

    codes = [feat["adm_cd"] for feat in layer.getFeatures()]
    if len(codes) == 1:
        return codes[0]
    return codes[0][:2]


def build_function_uri(function_name, region_code, layer_info=None, extent_5179=None):
    """DB 함수 또는 테이블 기반 레이어 URI 생성

    Args:
        function_name: DB 함수 이름 또는 테이블 이름
        region_code: 행정구역 코드 (자동 감지된 값)
        layer_info: 레이어 추가 정보 (query_type, pk_column 등)
        extent_5179: QgsRectangle (EPSG:5179 기준 bbox, 공간 필터용)

    Returns:
        QgsDataSourceUri
    """
    if not re.match(r'^[0-9]+$', region_code):
        raise ValueError(f"Invalid region code: {region_code}")

    uri = QgsDataSourceUri()
    uri.setConnection(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)

    geom_col = DB_GEOM_COLUMN
    if layer_info and "geom_column" in layer_info:
        geom_col = layer_info["geom_column"]

    query_type = layer_info.get("query_type", "function") if layer_info else "function"
    pk_col = layer_info.get("pk_column", "") if layer_info else ""

    if query_type == "spatial":
        # 테이블 직접 공간쿼리 (bbox 기반)
        if extent_5179 is not None:
            xmin = extent_5179.xMinimum()
            ymin = extent_5179.yMinimum()
            xmax = extent_5179.xMaximum()
            ymax = extent_5179.yMaximum()
            sql_filter = (
                f"ST_Intersects({geom_col}, "
                f"ST_MakeEnvelope({xmin}, {ymin}, {xmax}, {ymax}, {DB_SRID}))"
            )
        else:
            sql_filter = (
                f"ST_Intersects({geom_col}, "
                f"(SELECT geometry FROM {DB_SCHEMA}.sgis_hjd "
                f"WHERE adm_cd = '{region_code}' LIMIT 1))"
            )
        uri.setDataSource(DB_SCHEMA, function_name, geom_col, sql_filter, pk_col)
    elif query_type == "table":
        # 테이블 직접 조회 + region_code 필터
        sql_filter = f"adm_cd LIKE '{region_code}%'"
        uri.setDataSource(DB_SCHEMA, function_name, geom_col, sql_filter, pk_col)
    else:
        # DB 함수 서브쿼리 방식 (gis_layer_loader와 동일)
        # 필터 없이 로드 → PreprocessTask에서 클리핑
        table = f"(SELECT * FROM {DB_SCHEMA}.{function_name}('{region_code}'))"
        uri.setDataSource("", table, geom_col, "", pk_col or "rid")

    return uri


def build_union_uri(function_name, region_codes, layer_info=None, extent_5179=None):
    """여러 읍면동 코드를 UNION ALL로 합쳐 하나의 URI 생성

    DB 함수를 읍면동별로 개별 호출하는 대신, UNION ALL로 통합하여
    1회 쿼리로 모든 데이터를 가져온다. (640회 → 16회로 감소)

    Args:
        function_name: DB 함수 이름 또는 테이블 이름
        region_codes: 행정구역 코드 리스트 (예: ["31240101", "31240102"])
        layer_info: 레이어 추가 정보 (query_type, pk_column 등)
        extent_5179: QgsRectangle (EPSG:5179 기준 bbox)

    Returns:
        QgsDataSourceUri
    """
    # Validate all region codes
    for code in region_codes:
        if not re.match(r'^[0-9]+$', code):
            raise ValueError(f"Invalid region code: {code}")

    uri = QgsDataSourceUri()
    uri.setConnection(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)

    geom_col = DB_GEOM_COLUMN
    if layer_info and "geom_column" in layer_info:
        geom_col = layer_info["geom_column"]

    query_type = layer_info.get("query_type", "function") if layer_info else "function"
    pk_col = layer_info.get("pk_column", "") if layer_info else ""

    if query_type == "spatial":
        # 테이블 직접 공간쿼리 — extent 기반 (이미 1회 호출)
        if extent_5179 is not None:
            xmin = extent_5179.xMinimum()
            ymin = extent_5179.yMinimum()
            xmax = extent_5179.xMaximum()
            ymax = extent_5179.yMaximum()
            sql_filter = (
                f"ST_Intersects({geom_col}, "
                f"ST_MakeEnvelope({xmin}, {ymin}, {xmax}, {ymax}, {DB_SRID}))"
            )
        else:
            # 여러 행정구역 geometry의 union으로 공간 필터
            code_list = ", ".join(f"'{c}'" for c in region_codes)
            sql_filter = (
                f"ST_Intersects({geom_col}, "
                f"(SELECT ST_Union(geometry) FROM {DB_SCHEMA}.sgis_hjd "
                f"WHERE adm_cd IN ({code_list})))"
            )
        uri.setDataSource(DB_SCHEMA, function_name, geom_col, sql_filter, pk_col)
    elif query_type == "table":
        # 테이블 직접 조회 — OR 조건으로 통합
        if len(region_codes) == 1:
            sql_filter = f"adm_cd LIKE '{region_codes[0]}%'"
        else:
            conditions = [f"adm_cd LIKE '{code}%'" for code in region_codes]
            sql_filter = f"({' OR '.join(conditions)})"
        uri.setDataSource(DB_SCHEMA, function_name, geom_col, sql_filter, pk_col)
    else:
        # DB 함수 — UNION ALL로 통합
        subqueries = [
            f"SELECT * FROM {DB_SCHEMA}.{function_name}('{code}')"
            for code in region_codes
        ]
        table = f"({' UNION ALL '.join(subqueries)})"
        uri.setDataSource("", table, geom_col, "", pk_col or "rid")

    return uri


class LayerLoaderThread(QThread):
    """비동기 레이어 URI 준비 스레드

    동작:
    1. 외부에서 미리 감지된 region_code를 받아 사용
    2. 기존 DB 함수를 감지된 코드로 호출하는 URI 생성
    3. 메인 스레드로 URI 전달 → 레이어 생성 + 클리핑

    주의: region_code 감지(detect_sigungu_code / detect_region_code)는
    반드시 메인 스레드에서 수행한 뒤 생성자에 전달해야 합니다.
    """

    progress_changed = pyqtSignal(int, str)
    uri_ready = pyqtSignal(str, str, str, str)  # (uri_str, name, layer_type, provider)
    error_occurred = pyqtSignal(str)
    all_completed = pyqtSignal()

    def __init__(self, layers_to_load, region_codes, extent_5179=None, parent=None):
        """
        Args:
            layers_to_load: AVAILABLE_LAYERS 중 선택된 항목 리스트
            region_codes: 읍면동 코드 리스트 (예: ["31240101", "31240102"])
            extent_5179: QgsRectangle (EPSG:5179, spatial 쿼리용)
        """
        super().__init__(parent)
        self.layers_to_load = layers_to_load
        self.region_codes = region_codes  # 여러 읍면동 코드
        self.extent_5179 = extent_5179
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        total = len(self.layers_to_load)
        region_codes = self.region_codes

        if not region_codes:
            self.error_occurred.emit("범위에 해당하는 행정구역을 찾을 수 없습니다.")
            self.all_completed.emit()
            return

        # 각 레이어 × 각 읍면동 코드로 URI 생성
        for i, layer_info in enumerate(self.layers_to_load):
            if self._is_cancelled:
                break

            name = layer_info["name"]
            func = layer_info["function_name"]
            ltype = layer_info.get("layer_type", "vector")

            pct = int(((i + 1) / total) * 100)
            self.progress_changed.emit(pct, f"준비 중: {name} ({i + 1}/{total})")

            try:
                if ltype == "raster":
                    uri_str = self._build_raster_uri(func)
                    self.uri_ready.emit(uri_str, name, "raster", "gdal")
                else:
                    # UNION ALL 통합 쿼리 — 레이어당 1회 호출 (읍면동 N개 통합)
                    uri = build_union_uri(func, region_codes, layer_info, self.extent_5179)
                    self.uri_ready.emit(uri.uri(), name, "vector", "postgres")
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"LayerLoaderThread - {name}: {str(e)}",
                    "CivilPlanner",
                    Qgis.Warning,
                )
                self.error_occurred.emit(f"{name}: {str(e)}")

        self.progress_changed.emit(100, "완료")
        self.all_completed.emit()

    def _build_raster_uri(self, table_name):
        """래스터 URI 문자열 생성"""
        return (
            f"PG: dbname='{DB_NAME}' "
            f"host='{DB_HOST}' "
            f"port='{DB_PORT}' "
            f"user='{DB_USER}' "
            f"password='{DB_PASSWORD}' "
            f"schema='{DB_SCHEMA}' "
            f"table='{table_name}' "
            f"mode=2"
        )
