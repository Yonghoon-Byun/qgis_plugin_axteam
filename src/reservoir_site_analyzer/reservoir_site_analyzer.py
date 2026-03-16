# -*- coding: utf-8 -*-
"""
Reservoir Site Analyzer - Main Plugin Class
배수지(저수지) 설계를 위한 적합 부지 분석 플러그인
4단계 워크플로우: 지역선택 → 지형조건 → 소유주체 → 출력설정
"""

import os
import csv
import tempfile
from pathlib import Path

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QApplication
from qgis.core import (
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsProcessingFeedback,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeatureRequest,
    QgsGeometry,
    QgsRectangle,
    QgsDataSourceUri,
    Qgis
)

import processing

from .ui import MainDialog


# DB 연결 정보 (.env 기반 - pack_plugin.py 패키징 시 하드코딩으로 교체됨)
from .db_env import (DB_HOST, DB_PORT, DB_NAME, DB_SCHEMA,
                     DB_USER, DB_PASSWORD, DB_GEOM_COLUMN, DB_PK_COLUMN)

# DB 테이블 설정
DEM_TABLE = "korea_dem_90m"  # 래스터 DEM 테이블
BOUNDARY_TABLE = "sgis_hjd"  # 행정경계 테이블
BOUNDARY_GEOM_COLUMN = "geometry"  # 행정경계 geometry 컬럼명
OWNER_TABLE = "al_d400"  # 소유주체 테이블

# 소유주체 리스트 (하드코딩)
OWNER_LIST = [
    ("", "전체"),
    ("개인", "개인"),
    ("법인", "법인"),
    ("종중", "종중"),
    ("국유지", "국유지"),
    ("군유지", "군유지"),
    ("기타단체", "기타단체"),
    ("종교단체", "종교단체"),
    ("일본인, 창씨명등", "일본인, 창씨명등"),
    ("외국인, 외국공공기관", "외국인, 외국공공기관"),
    ("시, 도유지", "시, 도유지"),
    ("__OTHER__", "기타"),  # 리스트에 없는 항목
]

# 소유주체 칼럼명 매핑 (영문 → 한글)
OWNER_FIELD_MAPPING = {
    'a0': '고유번호',
    'a1': '법정동코드',
    'a2': '법정동명',
    'a3': '대장구분코드',
    'a4': '대장구분명',
    'a5': '지번',
    'a6': '지번지목부호',
    'a7': '소유구분코드',
    'a8': '소유구분명',
    'a9': '공유인수',
    'a10': '국가기관구분코드',
    'a11': '국가기관구분',
    'a12': '소유권변동원인코드',
    'a13': '소유권변동원인',
    'a14': '소유권변동일자',
    'a15': '지목코드',
    'a16': '지목',
    'a17': '라벨',
    'a18': '토지면적',
    'a19': '데이터기준일자',
    'a20': '시군구코드',
}


class ReservoirSiteAnalyzer:
    """배수지 적합 부지 분석 QGIS 플러그인"""

    def __init__(self, iface):
        """플러그인 초기화

        Args:
            iface: QgisInterface 인스턴스
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.dlg = None
        self.actions = []
        self.menu = '배수지 적합 부지 분석'
        self.toolbar = self.iface.addToolBar('ReservoirSiteAnalyzer')
        self.toolbar.setObjectName('ReservoirSiteAnalyzer')

        # 행정구역 데이터 저장
        self.admin_regions = {}
        self.sido_list = []
        self.sigungu_dict = {}
        self.eupmyeondong_dict = {}

        # 단계별 중간 결과 저장
        self._step_results = {
            'boundary_layer': None,
            'fixed_boundary': None,
            'dem_layer': None,
            'clipped_dem': None,
            'terrain_layer': None,
            'owner_layer': None,
        }
        self._current_params = {}

    def tr(self, message):
        """번역 함수"""
        return QCoreApplication.translate('ReservoirSiteAnalyzer', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        """툴바와 메뉴에 액션 추가"""
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)
        if whats_this is not None:
            action.setWhatsThis(whats_this)
        if add_to_toolbar:
            self.toolbar.addAction(action)
        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)
        return action

    def initGui(self):
        """플러그인 GUI 초기화"""
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.add_action(
            icon_path,
            text=self.tr('배수지 적합 부지 분석'),
            callback=self.run,
            parent=self.iface.mainWindow()
        )

    def unload(self):
        """플러그인 언로드"""
        for action in self.actions:
            self.iface.removePluginMenu(self.tr('배수지 적합 부지 분석'), action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def load_admin_regions(self):
        """admin_regions.csv에서 행정구역 데이터 로드"""
        csv_path = os.path.join(self.plugin_dir, 'admin_regions.csv')

        if not os.path.exists(csv_path):
            QMessageBox.warning(
                self.dlg,
                '오류',
                f'행정구역 파일을 찾을 수 없습니다:\n{csv_path}'
            )
            return False

        self.admin_regions = {}
        self.sido_list = []
        self.sigungu_dict = {}
        self.eupmyeondong_dict = {}

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = row['adm_cd'].strip()
                    name = row['adm_nm'].strip()
                    self.admin_regions[code] = name

                    code_len = len(code)

                    if code_len == 2:
                        # 시도 레벨
                        self.sido_list.append((code, name))
                    elif code_len == 5:
                        # 시군구 레벨
                        sido_code = code[:2]
                        if sido_code not in self.sigungu_dict:
                            self.sigungu_dict[sido_code] = []
                        self.sigungu_dict[sido_code].append((code, name))
                    elif code_len >= 8:
                        # 읍면동 레벨 (8자리 이상)
                        sigungu_code = code[:5]
                        if sigungu_code not in self.eupmyeondong_dict:
                            self.eupmyeondong_dict[sigungu_code] = []
                        self.eupmyeondong_dict[sigungu_code].append((code, name))

            return True

        except Exception as e:
            QMessageBox.warning(
                self.dlg,
                '오류',
                f'행정구역 파일 로드 실패:\n{str(e)}'
            )
            return False


    def get_vector_uri(self, table_name, geom_column=None):
        """벡터 레이어용 PostgreSQL URI 생성"""
        geom_col = geom_column or DB_GEOM_COLUMN
        uri = QgsDataSourceUri()
        uri.setConnection(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, QgsDataSourceUri.SslRequire)
        uri.setDataSource(DB_SCHEMA, table_name, geom_col)
        return uri.uri()

    def get_raster_uri(self, table_name):
        """래스터 레이어용 PostgreSQL URI 생성"""
        # PostGIS Raster 형식
        uri = (
            f"PG:dbname='{DB_NAME}' "
            f"host='{DB_HOST}' "
            f"port='{DB_PORT}' "
            f"user='{DB_USER}' "
            f"password='{DB_PASSWORD}' "
            f"sslmode=require "
            f"schema='{DB_SCHEMA}' "
            f"table='{table_name}' "
            f"mode=2"
        )
        return uri

    def load_dem_layer(self):
        """DB에서 DEM 래스터 레이어 로드"""
        uri = self.get_raster_uri(DEM_TABLE)
        dem_layer = QgsRasterLayer(uri, "DEM", "gdal")

        if not dem_layer.isValid():
            raise Exception(f"DEM 레이어를 로드할 수 없습니다: {DEM_TABLE}")

        return dem_layer

    def load_boundary_layer(self, where_clause=None):
        """DB에서 행정경계 벡터 레이어 로드"""
        # URI 문자열로 직접 연결 (Azure PostgreSQL 호환)
        uri_str = (
            f"dbname='{DB_NAME}' "
            f"host='{DB_HOST}' "
            f"port='{DB_PORT}' "
            f"user='{DB_USER}' "
            f"password='{DB_PASSWORD}' "
            f"sslmode=require "
            f"key='adm_cd' "
            f"table=\"{DB_SCHEMA}\".\"{BOUNDARY_TABLE}\" ({BOUNDARY_GEOM_COLUMN})"
        )

        if where_clause:
            uri_str += f" sql={where_clause}"

        boundary_layer = QgsVectorLayer(uri_str, "행정경계", "postgres")

        if not boundary_layer.isValid():
            error_msg = ""
            if boundary_layer.dataProvider():
                error_msg = boundary_layer.dataProvider().error().message()
            raise Exception(f"행정경계 레이어를 로드할 수 없습니다: {BOUNDARY_TABLE}\n연결 정보: {DB_HOST}:{DB_PORT}/{DB_NAME}\n오류: {error_msg}")

        return boundary_layer

    def load_owner_layer_bbox(self, extent):
        """DB에서 소유주체 레이어 로드 (bbox 필터 + ST_MakeValid만 적용, a8 필터 없음)

        Args:
            extent: 공간 필터용 사각 범위
        """
        # bbox 필터 + ST_MakeValid + ST_CollectionExtract (Polygon만 추출)
        xmin, ymin, xmax, ymax = extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()

        sql_query = (
            f"SELECT {DB_PK_COLUMN}, a8, "
            f"ST_CollectionExtract(ST_MakeValid({DB_GEOM_COLUMN}), 3) as {DB_GEOM_COLUMN} "
            f"FROM {DB_SCHEMA}.{OWNER_TABLE} "
            f"WHERE {DB_GEOM_COLUMN} && ST_MakeEnvelope({xmin}, {ymin}, {xmax}, {ymax}, 5179)"
        )

        # URI 생성 (SQL 서브쿼리 사용)
        uri_str = (
            f"dbname='{DB_NAME}' "
            f"host='{DB_HOST}' "
            f"port='{DB_PORT}' "
            f"user='{DB_USER}' "
            f"password='{DB_PASSWORD}' "
            f"sslmode=require "
            f"key='{DB_PK_COLUMN}' "
            f"table=\"({sql_query})\" ({DB_GEOM_COLUMN})"
        )

        db_owner_layer = QgsVectorLayer(uri_str, "소유주체_db", "postgres")

        if not db_owner_layer.isValid():
            error_msg = db_owner_layer.dataProvider().error().message() if db_owner_layer.dataProvider() else "Unknown error"
            raise Exception(f"소유주체 레이어를 로드할 수 없습니다: {OWNER_TABLE}\nSQL 오류: {error_msg}")

        # 결과를 메모리 레이어로 복사하여 반환
        mem_owner_layer = QgsVectorLayer(
            f"Polygon?crs=EPSG:5179",
            "owner_bbox",
            "memory"
        )
        provider = mem_owner_layer.dataProvider()
        provider.addAttributes(db_owner_layer.fields())
        mem_owner_layer.updateFields()
        provider.addFeatures(list(db_owner_layer.getFeatures()))
        mem_owner_layer.updateExtents()

        return mem_owner_layer

    def load_owner_layer_filtered(self, adm_cd, owner_values=None):
        """DB에서 소유주체 레이어 로드 (ST_Intersects + a8 필터)

        Args:
            adm_cd: 행정동 코드
            owner_values: 소유주체 값 리스트 (None이면 전체)
        Returns:
            필터링된 소유주체 메모리 레이어
        """
        # a8 필터 조건 생성
        a8_filter = ""
        if owner_values:
            has_other = "__OTHER__" in owner_values
            normal_values = [v for v in owner_values if v != "__OTHER__"]

            conditions = []
            if normal_values:
                if len(normal_values) == 1:
                    conditions.append(f"al.a8 = '{normal_values[0]}'")
                else:
                    values_str = "', '".join(normal_values)
                    conditions.append(f"al.a8 IN ('{values_str}')")

            if has_other:
                known_owners = [o[0] for o in OWNER_LIST if o[0] and o[0] != "__OTHER__"]
                other_conditions = ["al.a8 IS NOT NULL", "al.a8 != ''"]
                other_conditions += [f"al.a8 != '{owner}'" for owner in known_owners]
                other_filter = "(" + " AND ".join(other_conditions) + ")"
                conditions.append(other_filter)

            if conditions:
                a8_filter = " AND (" + " OR ".join(conditions) + ")"

        # 최적화된 쿼리: 필요한 칼럼만 SELECT, && 연산자로 1차 필터링
        # a0~a20 칼럼과 ufid(기본키) 선택
        selected_columns = ', '.join([f'al.{DB_PK_COLUMN}'] + [f'al.a{i}' for i in range(21)])

        sql_query = (
            f"SELECT {selected_columns}, "
            f"ST_CollectionExtract(ST_MakeValid(al.{DB_GEOM_COLUMN}), 3) as geom_clean "
            f"FROM {DB_SCHEMA}.{OWNER_TABLE} AS al "
            f"JOIN {DB_SCHEMA}.{BOUNDARY_TABLE} AS hjd "
            f"ON al.{DB_GEOM_COLUMN} && hjd.{BOUNDARY_GEOM_COLUMN} "  # bbox 연산자로 1차 필터링
            f"AND ST_Intersects(al.{DB_GEOM_COLUMN}, hjd.{BOUNDARY_GEOM_COLUMN}) "  # 정확한 교집합
            f"WHERE hjd.adm_cd = '{adm_cd}'"
            f"{a8_filter}"
        )

        # URI 생성 (SQL 서브쿼리 사용, geom_clean을 geometry 칼럼으로 사용)
        uri_str = (
            f"dbname='{DB_NAME}' "
            f"host='{DB_HOST}' "
            f"port='{DB_PORT}' "
            f"user='{DB_USER}' "
            f"password='{DB_PASSWORD}' "
            f"sslmode=require "
            f"key='{DB_PK_COLUMN}' "
            f"table=\"({sql_query})\" (geom_clean)"
        )

        db_owner_layer = QgsVectorLayer(uri_str, "소유주체_filtered", "postgres")

        if not db_owner_layer.isValid():
            error_msg = db_owner_layer.dataProvider().error().message() if db_owner_layer.dataProvider() else "Unknown error"
            raise Exception(f"소유주체 레이어를 로드할 수 없습니다.\nSQL 오류: {error_msg}")

        # 메모리 레이어 생성 (한글 필드명 사용)
        from qgis.core import QgsField, QgsFields
        from qgis.PyQt.QtCore import QVariant

        mem_layer = QgsVectorLayer(
            f"Polygon?crs=EPSG:5179",
            "소유주체_한글필드",
            "memory"
        )
        mem_provider = mem_layer.dataProvider()

        # 한글 필드명으로 필드 추가
        new_fields = QgsFields()
        for field in db_owner_layer.fields():
            field_name = field.name().lower()
            if field_name in OWNER_FIELD_MAPPING:
                korean_name = OWNER_FIELD_MAPPING[field_name]
                new_field = QgsField(korean_name, field.type())
                new_fields.append(new_field)
            elif field_name not in ['geom_clean']:  # geometry 필드 제외
                new_fields.append(field)

        mem_provider.addAttributes(new_fields)
        mem_layer.updateFields()

        # 피처 복사
        features = []
        for src_feature in db_owner_layer.getFeatures():
            new_feature = src_feature
            features.append(new_feature)

        mem_provider.addFeatures(features)
        mem_layer.updateExtents()

        return mem_layer

    def build_owner_filter_expression(self, owner_values):
        """소유주체 필터 표현식 생성 (QGIS 표현식 형식)

        Args:
            owner_values: 단일 값(str) 또는 값 리스트(list)
        Returns:
            QGIS 표현식 문자열
        """
        if isinstance(owner_values, str):
            owner_values = [owner_values]

        conditions = []
        has_other = "__OTHER__" in owner_values
        normal_values = [v for v in owner_values if v != "__OTHER__"]

        if normal_values:
            if len(normal_values) == 1:
                conditions.append(f"\"a8\" = '{normal_values[0]}'")
            else:
                values_str = "', '".join(normal_values)
                conditions.append(f"\"a8\" IN ('{values_str}')")

        if has_other:
            known_owners = [o[0] for o in OWNER_LIST if o[0] and o[0] != "__OTHER__"]
            other_conditions = ["\"a8\" IS NOT NULL", "\"a8\" != ''"]
            other_conditions += [f"\"a8\" != '{owner}'" for owner in known_owners]
            other_filter = "(" + " AND ".join(other_conditions) + ")"
            conditions.append(other_filter)

        if not conditions:
            return "1=1"

        return " OR ".join(conditions)


    def run(self):
        """플러그인 실행"""
        # 중간 결과 초기화
        self._step_results = {
            'boundary_layer': None,
            'fixed_boundary': None,
            'dem_layer': None,
            'clipped_dem': None,
            'terrain_layer': None,
            'owner_layer': None,
        }
        self._current_params = {}

        if self.dlg is None:
            self.dlg = MainDialog(self.iface.mainWindow())

            # 단계별 시그널 연결
            self.dlg.step1_completed.connect(self.run_step1_load_boundary_dem)
            self.dlg.step2_completed.connect(self.run_step2_terrain_filter)
            self.dlg.step3_completed.connect(self.run_step3_owner_filter)
            self.dlg.analysis_requested.connect(self.run_step4_final_analysis)
        else:
            # 다이얼로그가 이미 존재하면 UI 상태 초기화
            # 첫 번째 스텝으로 리셋
            self.dlg._update_step(0)
            # DEM 레이어 선택 초기화 (이전 클리핑 결과가 남아있지 않도록)
            self.dlg.terrain_tab.combo_dem_layer.setLayer(None)
            # 소유주체 탭의 지역경계 레이어 초기화
            self.dlg.owner_tab.combo_boundary_layer.setLayer(None)
            # 소유주체 칩 선택 해제
            self.dlg.owner_tab._deselect_all()
            # 출력 탭의 레이어 선택도 초기화
            self.dlg.output_tab.combo_boundary_layer.setLayer(None)
            self.dlg.output_tab.combo_terrain_layer.setLayer(None)
            self.dlg.output_tab.combo_owner_layer.setLayer(None)

        # 데이터 로드
        if self.load_admin_regions():
            self.dlg.set_region_data(
                self.sido_list,
                self.sigungu_dict,
                self.eupmyeondong_dict
            )

        # 소유주체 리스트 설정
        self.dlg.set_owner_list(OWNER_LIST)

        # 다이얼로그 표시
        self.dlg.show()
        self.dlg.exec_()

    def run_step1_load_boundary_dem(self, region_code):
        """1단계: 지역경계 및 DEM 로드

        Args:
            region_code: 선택된 행정구역 코드
        """
        self._current_params['region_code'] = region_code

        # 선택된 지역명 가져오기
        region_name = self.dlg.region_tab.get_selected_region_name()
        if not region_name or region_name == "전체":
            region_name = "전국"
        self._current_params['region_name'] = region_name

        self.dlg.show_progress()
        self.dlg.update_progress(0, '1단계: 지역경계 로드 중...')
        QApplication.processEvents()

        try:
            feedback = QgsProcessingFeedback()

            # 1. 행정경계 레이어 로드
            where_clause = None
            if region_code:
                where_clause = f"adm_cd = '{region_code}'"

            boundary_layer = self.load_boundary_layer(where_clause)

            if boundary_layer.featureCount() == 0:
                QMessageBox.warning(self.dlg, '오류', '선택한 지역의 행정경계를 찾을 수 없습니다.')
                self.dlg.hide_progress()
                return

            self._step_results['boundary_layer'] = boundary_layer

            # 지역 경계 레이어를 프로젝트에 추가
            self.dlg.update_progress(20, '선택지역 경계 추가 중...')
            QApplication.processEvents()

            boundary_layer_copy = QgsVectorLayer(
                f"Polygon?crs={boundary_layer.crs().authid()}",
                f"0.지역경계_{region_name}",
                "memory"
            )
            boundary_provider = boundary_layer_copy.dataProvider()
            boundary_provider.addAttributes(boundary_layer.fields())
            boundary_layer_copy.updateFields()
            boundary_provider.addFeatures(list(boundary_layer.getFeatures()))
            boundary_layer_copy.updateExtents()
            QgsProject.instance().addMapLayer(boundary_layer_copy)
            # 소유주체 탭의 지역경계 레이어 콤보박스에 자동 설정
            self.dlg.owner_tab.set_boundary_layer(boundary_layer_copy)
            # 출력설정 탭의 선택지역 콤보박스에 자동 설정
            self.dlg.output_tab.set_selected_boundary_layer(boundary_layer_copy)

            # 2. DEM 레이어 로드
            self.dlg.update_progress(40, 'DEM 로드 중...')
            QApplication.processEvents()

            # Check if user selected a DEM layer in terrain tab
            selected_dem = self.dlg.terrain_tab.get_selected_dem_layer()
            if selected_dem:
                dem_layer = selected_dem
                self.iface.messageBar().pushMessage(
                    "정보",
                    f"선택된 DEM 레이어 사용: {dem_layer.name()}",
                    level=Qgis.Info,
                    duration=3
                )
            else:
                dem_layer = self.load_dem_layer()

            self._step_results['dem_layer'] = dem_layer

            # 3. 행정경계 geometry 수정 (buffer 0)
            self.dlg.update_progress(60, '행정경계 geometry 수정 중...')
            QApplication.processEvents()

            fix_result = processing.run(
                "native:buffer",
                {
                    'INPUT': boundary_layer,
                    'DISTANCE': 0,
                    'SEGMENTS': 5,
                    'END_CAP_STYLE': 0,
                    'JOIN_STYLE': 0,
                    'MITER_LIMIT': 2,
                    'DISSOLVE': True,
                    'OUTPUT': 'TEMPORARY_OUTPUT'
                },
                feedback=feedback
            )
            self._step_results['fixed_boundary'] = fix_result['OUTPUT']

            # 4. DEM을 행정경계로 클리핑
            self.dlg.update_progress(80, 'DEM 클리핑 중...')
            QApplication.processEvents()

            clip_result = processing.run(
                "gdal:cliprasterbymasklayer",
                {
                    'INPUT': dem_layer,
                    'MASK': self._step_results['fixed_boundary'],
                    'SOURCE_CRS': None,
                    'TARGET_CRS': None,
                    'NODATA': -9999,
                    'ALPHA_BAND': False,
                    'CROP_TO_CUTLINE': True,
                    'KEEP_RESOLUTION': True,
                    'SET_RESOLUTION': False,
                    'X_RESOLUTION': None,
                    'Y_RESOLUTION': None,
                    'MULTITHREADING': False,
                    'OPTIONS': '',
                    'DATA_TYPE': 0,
                    'EXTRA': '',
                    'OUTPUT': 'TEMPORARY_OUTPUT'
                },
                feedback=feedback
            )
            self._step_results['clipped_dem'] = clip_result['OUTPUT']

            # 클리핑된 DEM을 프로젝트에 추가
            clipped_dem_layer = QgsRasterLayer(clip_result['OUTPUT'], f"1.DEM_{region_name}")
            if clipped_dem_layer.isValid():
                QgsProject.instance().addMapLayer(clipped_dem_layer)
                # 지형조건 탭의 DEM 레이어 콤보박스에 자동 설정
                self.dlg.terrain_tab.set_dem_layer(clipped_dem_layer)

            self.dlg.update_progress(100, '1단계 완료!')
            QApplication.processEvents()

            self.iface.messageBar().pushMessage(
                "1단계 완료",
                "지역경계 및 DEM 로드 완료",
                level=Qgis.Success,
                duration=3
            )

            self.dlg.hide_progress()

        except Exception as e:
            self.dlg.hide_progress()
            QMessageBox.critical(
                self.dlg,
                '오류',
                f'1단계 처리 중 오류가 발생했습니다:\n{str(e)}'
            )

    def run_step2_terrain_filter(self, min_elevation, max_elevation, max_slope):
        """2단계: 지형 조건 필터링 (고도/경사)

        Args:
            min_elevation: 최소 고도 (m)
            max_elevation: 최대 고도 (m)
            max_slope: 최대 경사 (도)
        """
        self._current_params['min_elevation'] = min_elevation
        self._current_params['max_elevation'] = max_elevation
        self._current_params['max_slope'] = max_slope

        if not self._step_results.get('clipped_dem'):
            QMessageBox.warning(self.dlg, '오류', '먼저 1단계를 완료해주세요.')
            return

        self.dlg.show_progress()
        self.dlg.update_progress(0, '2단계: 경사 계산 중...')
        QApplication.processEvents()

        try:
            feedback = QgsProcessingFeedback()
            clipped_dem = self._step_results['clipped_dem']

            # 1. 경사 계산
            self.dlg.update_progress(20, '경사 계산 중...')
            QApplication.processEvents()

            slope_result = processing.run(
                "native:slope",
                {
                    'INPUT': clipped_dem,
                    'Z_FACTOR': 1.0,
                    'OUTPUT': 'TEMPORARY_OUTPUT'
                },
                feedback=feedback
            )
            slope_raster = slope_result['OUTPUT']

            # 2. 래스터 계산기 - 고도 및 경사 조건 적용
            self.dlg.update_progress(40, '고도/경사 조건 필터링 중...')
            QApplication.processEvents()

            formula = f"(A >= {min_elevation}) * (A <= {max_elevation}) * (B <= {max_slope})"

            calc_result = processing.run(
                "gdal:rastercalculator",
                {
                    'INPUT_A': clipped_dem,
                    'BAND_A': 1,
                    'INPUT_B': slope_raster,
                    'BAND_B': 1,
                    'FORMULA': formula,
                    'NO_DATA': -9999,
                    'RTYPE': 5,
                    'OUTPUT': 'TEMPORARY_OUTPUT'
                },
                feedback=feedback
            )
            filtered_raster = calc_result['OUTPUT']

            # 3. 폴리곤화
            self.dlg.update_progress(60, '폴리곤 변환 중...')
            QApplication.processEvents()

            polygonize_result = processing.run(
                "gdal:polygonize",
                {
                    'INPUT': filtered_raster,
                    'BAND': 1,
                    'FIELD': 'DN',
                    'EIGHT_CONNECTEDNESS': True,
                    'EXTRA': '',
                    'OUTPUT': 'TEMPORARY_OUTPUT'
                },
                feedback=feedback
            )
            polygon_output = polygonize_result['OUTPUT']

            # 3.5. 도형 수정 (fix geometries)
            self.dlg.update_progress(70, '도형 유효성 검사 및 수정 중...')
            QApplication.processEvents()

            fix_geometries_result = processing.run(
                "native:fixgeometries",
                {
                    'INPUT': polygon_output,
                    'METHOD': 1,  # Structure method
                    'OUTPUT': 'TEMPORARY_OUTPUT'
                },
                feedback=feedback
            )
            polygon_output = fix_geometries_result['OUTPUT']

            # 4. DN = 1 인 피처만 추출 (processing 알고리즘 사용)
            self.dlg.update_progress(80, '조건 만족 영역 추출 중...')
            QApplication.processEvents()

            extract_result = processing.run(
                "native:extractbyexpression",
                {
                    'INPUT': polygon_output,
                    'EXPRESSION': '"DN" = 1',
                    'OUTPUT': 'TEMPORARY_OUTPUT'
                },
                feedback=feedback
            )
            terrain_layer = extract_result['OUTPUT']

            self._step_results['terrain_layer'] = terrain_layer

            # 평균 고도 계산 (zonal statistics)
            self.dlg.update_progress(85, '평균 고도 계산 중...')
            QApplication.processEvents()

            zonal_result = processing.run(
                "native:zonalstatisticsfb",
                {
                    'INPUT': terrain_layer,
                    'INPUT_RASTER': clipped_dem,
                    'RASTER_BAND': 1,
                    'COLUMN_PREFIX': '_',
                    'STATISTICS': [2],  # 2 = mean (평균)
                    'OUTPUT': 'TEMPORARY_OUTPUT'
                },
                feedback=feedback
            )

            # 결과 레이어에서 평균 고도 필드만 추출
            zonal_layer = zonal_result['OUTPUT']
            if isinstance(zonal_layer, str):
                zonal_layer = QgsVectorLayer(zonal_layer, "zonal_temp", "ogr")

            # 지형조건 필터링 결과 레이어를 프로젝트에 추가
            region_name = self._current_params.get('region_name', '전국')
            terrain_output_layer = QgsVectorLayer(
                f"Polygon?crs={terrain_layer.crs().authid()}",
                f"2.지형조건_{region_name}",
                "memory"
            )
            terrain_output_provider = terrain_output_layer.dataProvider()

            # 기존 필드 + 평균고도 필드 추가
            from qgis.core import QgsField
            from qgis.PyQt.QtCore import QVariant

            fields = list(terrain_layer.fields())
            fields.append(QgsField("평균고도", QVariant.Double, "double", 10, 2))
            terrain_output_provider.addAttributes(fields)
            terrain_output_layer.updateFields()

            # 피처 복사 및 평균 고도 값 추가
            features_with_elevation = []
            for terrain_feat, zonal_feat in zip(terrain_layer.getFeatures(), zonal_layer.getFeatures()):
                new_feat = terrain_feat
                # zonal statistics 결과에서 평균값 가져오기
                mean_value = zonal_feat['_mean'] if '_mean' in zonal_feat.fields().names() else None
                attrs = terrain_feat.attributes()
                attrs.append(round(mean_value, 2) if mean_value is not None else None)
                new_feat.setAttributes(attrs)
                features_with_elevation.append(new_feat)

            terrain_output_provider.addFeatures(features_with_elevation)
            terrain_output_layer.updateExtents()
            QgsProject.instance().addMapLayer(terrain_output_layer)
            # 출력설정 탭의 지형조건 콤보박스에 자동 설정
            self.dlg.output_tab.set_selected_terrain_layer(terrain_output_layer)

            self.dlg.update_progress(100, '2단계 완료!')
            QApplication.processEvents()

            feature_count = terrain_layer.featureCount()
            self.iface.messageBar().pushMessage(
                "2단계 완료",
                f"지형조건 필터링 완료 - {feature_count}개 영역 추출",
                level=Qgis.Success,
                duration=3
            )

            self.dlg.hide_progress()

        except Exception as e:
            self.dlg.hide_progress()
            QMessageBox.critical(
                self.dlg,
                '오류',
                f'2단계 처리 중 오류가 발생했습니다:\n{str(e)}'
            )

    def run_step3_owner_filter(self, owner_values):
        """3단계: 소유주체 필터링

        Args:
            owner_values: 선택된 소유주체 값 리스트
        """
        self._current_params['owner_values'] = owner_values

        region_code = self._current_params.get('region_code')
        if not region_code:
            QMessageBox.warning(self.dlg, '오류', '먼저 1단계를 완료해주세요.')
            return

        # 소유주체 미선택 시 필터링 없이 통과
        if not owner_values:
            self._step_results['owner_layer'] = None
            self.iface.messageBar().pushMessage(
                "3단계 완료",
                "소유주체 필터링 없이 진행 (전체)",
                level=Qgis.Info,
                duration=3
            )
            return

        self.dlg.show_progress()
        self.dlg.update_progress(0, '3단계: 소유주체 레이어 로드 중...')
        QApplication.processEvents()

        try:
            # DB에서 ST_Intersects + a8 필터로 직접 조회
            self.dlg.update_progress(10, 'DB 연결 중...')
            QApplication.processEvents()

            self.dlg.update_progress(30, '공간 필터링 중 (시간이 걸릴 수 있습니다)...')
            QApplication.processEvents()

            owner_layer = self.load_owner_layer_filtered(region_code, owner_values)

            owner_count = owner_layer.featureCount()
            self.dlg.update_progress(60, f'소유주체 필지 {owner_count}개 추출됨')
            QApplication.processEvents()

            self.dlg.update_progress(70, '필드명 한글 변환 중...')
            QApplication.processEvents()

            if owner_count == 0:
                QMessageBox.information(
                    self.dlg,
                    '결과',
                    '선택한 지역 내에 해당 소유주체 필지가 없습니다.'
                )
                self.dlg.hide_progress()
                return

            self._step_results['owner_layer'] = owner_layer

            # 소유주체 레이어를 프로젝트에 추가
            owner_label = self.dlg.owner_tab.get_owner_label()
            owner_mem_layer = QgsVectorLayer(
                f"Polygon?crs=EPSG:5179",
                f"3.소유주체_{owner_label}",
                "memory"
            )
            owner_provider = owner_mem_layer.dataProvider()
            owner_provider.addAttributes(owner_layer.fields())
            owner_mem_layer.updateFields()
            owner_provider.addFeatures(list(owner_layer.getFeatures()))
            owner_mem_layer.updateExtents()
            QgsProject.instance().addMapLayer(owner_mem_layer)
            # 출력설정 탭의 소유주체 콤보박스에 자동 설정
            self.dlg.output_tab.set_selected_owner_layer(owner_mem_layer)

            self.dlg.update_progress(100, '3단계 완료!')
            QApplication.processEvents()

            self.iface.messageBar().pushMessage(
                "3단계 완료",
                f"소유주체 필터링 완료 - {owner_count}개 필지 추출",
                level=Qgis.Success,
                duration=3
            )

            self.dlg.hide_progress()

        except Exception as e:
            self.dlg.hide_progress()
            QMessageBox.critical(
                self.dlg,
                '오류',
                f'3단계 처리 중 오류가 발생했습니다:\n{str(e)}'
            )

    def run_step4_final_analysis(self, params):
        """4단계: 최종 분석 (지형조건 × 소유주체 교집합)

        Args:
            params: 분석 파라미터 딕셔너리
        """
        # Check if layers are selected from output tab (allows skipping steps 1-3)
        selected_terrain = params.get('selected_terrain_layer')
        selected_owner = params.get('selected_owner_layer')

        # Use selected layers if available, otherwise use step results
        terrain_layer = selected_terrain if selected_terrain else self._step_results.get('terrain_layer')
        owner_layer = selected_owner if selected_owner else self._step_results.get('owner_layer')
        output_name = params.get('output_name', '4.적합부지_결과')

        # Validate terrain layer
        if terrain_layer and not terrain_layer.isValid():
            QMessageBox.warning(
                self.dlg,
                '오류',
                f'선택한 지형조건 레이어({terrain_layer.name()})가 유효하지 않습니다.\n다시 선택해주세요.'
            )
            return

        # Validate owner layer
        if owner_layer and not owner_layer.isValid():
            QMessageBox.warning(
                self.dlg,
                '오류',
                f'선택한 소유주체 레이어({owner_layer.name()})가 유효하지 않습니다.\n다시 선택해주세요.'
            )
            return

        if not terrain_layer:
            QMessageBox.warning(
                self.dlg,
                '오류',
                '지형 조건 레이어를 선택하거나 2단계를 완료해주세요.\n\n'
                '출력설정 탭에서 기존 레이어를 선택하거나,\n'
                '2단계(지형 조건)를 먼저 실행해주세요.'
            )
            return

        self.dlg.show_progress()
        self.dlg.update_progress(0, '4단계: 최종 분석 시작...')
        QApplication.processEvents()

        try:
            feedback = QgsProcessingFeedback()

            # 소유주체 필터링이 없는 경우 지형조건 결과를 최종 결과로 사용
            if not owner_layer:
                self.dlg.update_progress(50, '최종 결과 생성 중...')
                QApplication.processEvents()

                result_layer = terrain_layer
            else:
                # 지형조건 결과와 소유주체 교집합
                self.dlg.update_progress(20, '지형 도형 수정 중...')
                QApplication.processEvents()

                # terrain_layer의 무결하지 않은 도형 수정
                fix_terrain_result = processing.run(
                    "native:fixgeometries",
                    {
                        'INPUT': terrain_layer,
                        'METHOD': 1,  # Structure method
                        'OUTPUT': 'TEMPORARY_OUTPUT'
                    },
                    feedback=feedback
                )
                terrain_layer_fixed = fix_terrain_result['OUTPUT']

                self.dlg.update_progress(50, '소유주체 교집합 분석 중...')
                QApplication.processEvents()

                # 공간 인덱스 생성 (intersection 성능 향상)
                if hasattr(owner_layer, 'dataProvider'):
                    owner_layer.dataProvider().createSpatialIndex()

                # 소유주체 필드명 결정 (한글 또는 영문)
                owner_field_name = '소유구분명' if '소유구분명' in [f.name() for f in owner_layer.fields()] else 'a8'

                intersect_result = processing.run(
                    "native:intersection",
                    {
                        'INPUT': terrain_layer_fixed,
                        'OVERLAY': owner_layer,
                        'INPUT_FIELDS': [],
                        'OVERLAY_FIELDS': [owner_field_name],
                        'OVERLAY_FIELDS_PREFIX': '',
                        'OUTPUT': 'TEMPORARY_OUTPUT'
                    },
                    feedback=feedback
                )

                # intersect_result['OUTPUT']은 이미 QgsVectorLayer 객체일 수 있음
                output_result = intersect_result['OUTPUT']
                if isinstance(output_result, QgsVectorLayer):
                    result_layer = output_result
                else:
                    result_layer = QgsVectorLayer(
                        output_result,
                        output_name,
                        "ogr"
                    )

            # 결과 레이어 추가
            self.dlg.update_progress(90, '결과 레이어 생성 중...')
            QApplication.processEvents()

            if result_layer.featureCount() > 0:
                final_layer = QgsVectorLayer(
                    f"Polygon?crs={result_layer.crs().authid()}",
                    output_name,
                    "memory"
                )
                final_provider = final_layer.dataProvider()
                final_provider.addAttributes(result_layer.fields())
                final_layer.updateFields()
                final_provider.addFeatures(list(result_layer.getFeatures()))
                final_layer.updateExtents()

                QgsProject.instance().addMapLayer(final_layer)

                self.dlg.update_progress(100, '완료!')
                QApplication.processEvents()

                self.iface.messageBar().pushMessage(
                    "분석 완료",
                    f"적합 부지 {final_layer.featureCount()}개 발견",
                    level=Qgis.Success,
                    duration=5
                )
            else:
                self.dlg.update_progress(100, '완료!')
                QApplication.processEvents()

                QMessageBox.information(
                    self.dlg,
                    '결과',
                    '조건에 맞는 적합 부지를 찾지 못했습니다.'
                )

            self.dlg.hide_progress()
            self.dlg.accept()

        except Exception as e:
            self.dlg.hide_progress()
            QMessageBox.critical(
                self.dlg,
                '오류',
                f'최종 분석 중 오류가 발생했습니다:\n{str(e)}'
            )

    # 기존 run_analysis_with_params 유지 (하위 호환성)
    def run_analysis_with_params(self, params):
        """새 UI에서 전달받은 파라미터로 분석 실행 (하위 호환용)"""
        self.run_step4_final_analysis(params)
