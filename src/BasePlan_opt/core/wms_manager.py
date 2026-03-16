# -*- coding: utf-8 -*-
"""
WMS Manager for BasePlan QGIS Plugin - v7.1

v7.1 (2026-02-04): 초기화 후 재로드 실패 문제 해결
- _ensure_temp_dir() 추가: cleanup() 후 임시 디렉토리 재생성
- 타일 저장 전 임시 디렉토리 존재 확인

v7 (2026-02-04): 해안선 데이터 누락 문제 해결
- 타일 경계 부동소수점 오차 보정 (마지막 행/열 경계 정확히 맞춤)
- viewparams BBOX 좌표 floor/ceil 적용 (축소 → 확장)
- 타일 요청 재시도 로직 추가 (최대 3회, 지수 백오프)
- 병렬도 증가 (MAX_CONCURRENT 2 → 4)
- 최대 타일 수 증가 (MAX_TILES 16 → 25)

v5: 레이어 순서 자동 조정 (행정구역 최상단)
v3 Features:
- 타일 방식 로딩 (넓은 영역 고해상도 지원)
- 병렬 HTTP 요청 (ThreadPoolExecutor)
- VRT 합성 (메모리 효율적)
- 진행률 시그널
"""

import os
import math
import tempfile
import time
import requests
import hashlib
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.core import (
    QgsRasterLayer,
    QgsVectorLayer,
    QgsProject,
    QgsRectangle,
    QgsCoordinateReferenceSystem,
    QgsMessageLog,
    QgsLayerTreeLayer,
    Qgis
)

try:
    from osgeo import gdal
    HAS_GDAL = True
except ImportError:
    HAS_GDAL = False


class WMSManager(QObject):
    """Direct GetMap 방식 WMS 레이어 관리 - v7.1 초기화 후 재로드 수정"""

    # v3: 진행률 시그널
    progress_updated = pyqtSignal(int, int, str)  # current, total, message

    # 기본 설정
    DEFAULT_URL = 'http://10.0.0.22:8080/geoserver/gis_water/wms'
    CRS = 'EPSG:5179'

    # 타일 설정 (v7: 성능 개선)
    MAX_TILE_SIZE = 2000  # 타일당 최대 픽셀
    MAX_SINGLE_REQUEST = 2000  # 단일 요청 최대 픽셀 (이 초과시 타일 분할)
    MAX_CONCURRENT = 8  # v7.2: 동시 요청 수 (4 → 8, 속도 개선)
    TARGET_RESOLUTION = 2.0  # m/pixel (기본 해상도)
    MAX_TILES = 25  # v7: 최대 타일 수 (16 → 25)

    # 레이어 구성
    LAYERS = {
        'hjd': {
            'layer_a': 'hjd_mv_filter',       # MV 기반 (기존 hjd_emd_filter 유지, 새 레이어)
            'layer_b': 'hjd_bbox',
            'display_name_a': '행정구역_A',
            'display_name_b': '행정구역_B',
            'style_a': 'hjd_area_a',
            'style_b': 'hjd_area_b'
        },
        'contour': {
            'layer_a': 'contour_mv_filter',    # MV 기반 (기존 contour_filter 유지, 새 레이어)
            'layer_b': 'contour_bbox',
            'display_name_a': '등고선_A',
            'display_name_b': '등고선_B',
            'style_a': 'contour_area_a',
            'style_b': 'contour_area_b'
        },
        'road': {
            'layer_a': 'road_mv_filter',       # MV 기반 (기존 road_center_clipped 유지, 새 레이어)
            'layer_b': 'road_bbox',
            'display_name_a': '도로중심선_A',
            'display_name_b': '도로중심선_B',
            'style_a': 'road_area_a',
            'style_b': 'road_area_b'
        }
    }

    def __init__(self):
        """초기화"""
        super().__init__()
        self.base_url: str = self.DEFAULT_URL
        self.loaded_layers: Dict[str, QgsRasterLayer] = {}
        self.temp_files: list = []
        self.current_prov: Optional[str] = None  # 영역 B에서 MV 사용을 위해 저장
        # D: 드라이브 우선, 없으면 시스템 temp 폴백
        d_temp = Path('D:/Temp/baseplan')
        try:
            d_temp.mkdir(parents=True, exist_ok=True)
            self._base_temp = d_temp
        except Exception:
            self._base_temp = Path(tempfile.gettempdir()) / 'baseplan'
        self._base_temp.mkdir(parents=True, exist_ok=True)
        self.temp_dir = tempfile.mkdtemp(prefix='wms_v7_', dir=str(self._base_temp))

        # v8: HTTP 캐싱 (동일 URL 재요청 <1초)
        self.cache_dir = self._base_temp / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        self._log(f"HTTP cache dir: {self.cache_dir}")

    def set_url(self, url: str):
        """WMS URL 설정"""
        self.base_url = url

    def _needs_tiling(self, extent: QgsRectangle) -> bool:
        """
        v3: 타일 분할이 필요한지 판단

        Args:
            extent: 요청 범위

        Returns:
            True면 타일 분할 필요
        """
        required_width = extent.width() / self.TARGET_RESOLUTION
        required_height = extent.height() / self.TARGET_RESOLUTION

        return required_width > self.MAX_SINGLE_REQUEST or required_height > self.MAX_SINGLE_REQUEST

    def _calculate_tiles(self, bbox: QgsRectangle) -> List[QgsRectangle]:
        """
        v7: BBOX를 타일로 분할 (마지막 행/열 경계 보정)

        Args:
            bbox: 전체 범위

        Returns:
            타일 목록 (QgsRectangle)
        """
        width_m = bbox.width()
        height_m = bbox.height()

        # 적응형 해상도 계산 - MAX_TILES를 초과하지 않도록 조정
        resolution = self.TARGET_RESOLUTION
        max_tiles_per_side = int(math.sqrt(self.MAX_TILES))  # 5x5 = 25

        # 현재 해상도로 필요한 타일 수 계산
        total_width_px = width_m / resolution
        total_height_px = height_m / resolution
        n_cols = max(1, math.ceil(total_width_px / self.MAX_TILE_SIZE))
        n_rows = max(1, math.ceil(total_height_px / self.MAX_TILE_SIZE))

        # 타일 수가 너무 많으면 해상도 자동 조정
        while n_cols * n_rows > self.MAX_TILES:
            resolution *= 1.5  # 해상도 낮춤 (픽셀 크기 증가)
            total_width_px = width_m / resolution
            total_height_px = height_m / resolution
            n_cols = max(1, math.ceil(total_width_px / self.MAX_TILE_SIZE))
            n_rows = max(1, math.ceil(total_height_px / self.MAX_TILE_SIZE))

        if resolution != self.TARGET_RESOLUTION:
            self._log(f"Resolution adjusted: {self.TARGET_RESOLUTION}m -> {resolution:.1f}m (area too large)")

        self._log(f"Tile grid: {n_cols}x{n_rows} = {n_cols * n_rows} tiles (resolution: {resolution:.1f}m/px)")

        # v7: 타일 BBOX 생성 (마지막 행/열 경계 보정으로 데이터 누락 방지)
        tiles = []
        tile_width = width_m / n_cols
        tile_height = height_m / n_rows

        for row in range(n_rows):
            for col in range(n_cols):
                # v7: 마지막 행/열은 원래 bbox의 max 값 사용 (부동소수점 오차 방지)
                x_min = bbox.xMinimum() + col * tile_width
                y_min = bbox.yMinimum() + row * tile_height
                x_max = bbox.xMaximum() if col == n_cols - 1 else bbox.xMinimum() + (col + 1) * tile_width
                y_max = bbox.yMaximum() if row == n_rows - 1 else bbox.yMinimum() + (row + 1) * tile_height

                tile_bbox = QgsRectangle(x_min, y_min, x_max, y_max)
                tiles.append(tile_bbox)

        return tiles

    def _ensure_temp_dir(self):
        """
        v7.1: 임시 디렉토리 존재 확인 및 재생성
        cleanup() 후 재사용 시 필요
        """
        if not os.path.exists(self.temp_dir):
            try:
                os.makedirs(self.temp_dir, exist_ok=True)
                self._log(f"Temp dir recreated: {self.temp_dir}")
            except Exception as e:
                # 기존 경로 생성 실패 시 D:/Temp/baseplan에 새 경로 생성
                self._base_temp.mkdir(parents=True, exist_ok=True)
                self.temp_dir = tempfile.mkdtemp(prefix='wms_v7_', dir=str(self._base_temp))
                self._log(f"New temp dir created: {self.temp_dir}")

    def _get_cache_key(self, url: str) -> str:
        """v8: URL에서 캐시 키 생성 (MD5 해시)"""
        return hashlib.md5(url.encode()).hexdigest()

    def _get_cached_response(self, url: str) -> Optional[bytes]:
        """v8: 캐시에서 응답 조회"""
        try:
            cache_key = self._get_cache_key(url)
            cache_file = self.cache_dir / f"{cache_key}.png"
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    self._log(f"Cache HIT: {cache_key[:8]}...", level=Qgis.Info)
                    return f.read()
        except Exception as e:
            self._log(f"Cache read error: {str(e)}", level=Qgis.Warning)
        return None

    def _cache_response(self, url: str, content: bytes) -> bool:
        """v8: 응답을 캐시에 저장"""
        try:
            cache_key = self._get_cache_key(url)
            cache_file = self.cache_dir / f"{cache_key}.png"
            with open(cache_file, 'wb') as f:
                f.write(content)
            self._log(f"Cache WRITE: {cache_key[:8]}... ({len(content) / 1024:.1f}KB)")
            return True
        except Exception as e:
            self._log(f"Cache write error: {str(e)}", level=Qgis.Warning)
            return False

    def _fetch_single_tile(
        self,
        tile_bbox: QgsRectangle,
        tile_index: int,
        layer_name: str,
        style: str,
        viewparams: str,
        is_bbox_mode: bool = False,
        max_retries: int = 3,
        prov: Optional[str] = None
    ) -> Optional[Tuple[str, QgsRectangle]]:
        """
        v7: 단일 타일 HTTP 요청 (재시도 로직 추가)

        Args:
            tile_bbox: 타일 범위
            tile_index: 타일 인덱스
            layer_name: 레이어 이름
            style: 스타일
            viewparams: viewparams 문자열
            is_bbox_mode: True면 BBOX 모드 (영역 B)
            max_retries: 최대 재시도 횟수 (기본 3)

        Returns:
            (PNG 경로, bbox) 또는 None
        """
        # v7.1: 임시 디렉토리 존재 확인
        self._ensure_temp_dir()

        last_error = None
        for attempt in range(max_retries):
            try:
                # 타일 크기: MAX_TILE_SIZE로 고정 (해상도는 타일 분할에서 이미 조정됨)
                width = self.MAX_TILE_SIZE
                height = self.MAX_TILE_SIZE

                # URL 생성
                if is_bbox_mode:
                    # v7: floor/ceil 사용으로 BBOX 확장 (데이터 누락 방지)
                    minx = math.floor(tile_bbox.xMinimum())
                    miny = math.floor(tile_bbox.yMinimum())
                    maxx = math.ceil(tile_bbox.xMaximum())
                    maxy = math.ceil(tile_bbox.yMaximum())

                    # prov가 있으면 MV 사용 viewparams
                    if prov:
                        vp = f'prov:{prov};minx:{minx};miny:{miny};maxx:{maxx};maxy:{maxy}'
                    else:
                        vp = f'minx:{minx};miny:{miny};maxx:{maxx};maxy:{maxy}'

                    params = {
                        'SERVICE': 'WMS',
                        'VERSION': '1.1.0',
                        'REQUEST': 'GetMap',
                        'LAYERS': layer_name,
                        'STYLES': style,
                        'SRS': self.CRS,
                        'BBOX': f'{minx},{miny},{maxx},{maxy}',
                        'WIDTH': str(width),
                        'HEIGHT': str(height),
                        'FORMAT': 'image/png',
                        'TRANSPARENT': 'TRUE',
                        'viewparams': vp
                    }
                else:
                    params = {
                        'SERVICE': 'WMS',
                        'VERSION': '1.1.0',
                        'REQUEST': 'GetMap',
                        'LAYERS': layer_name,
                        'STYLES': style,
                        'SRS': self.CRS,
                        'BBOX': f'{tile_bbox.xMinimum()},{tile_bbox.yMinimum()},{tile_bbox.xMaximum()},{tile_bbox.yMaximum()}',
                        'WIDTH': str(width),
                        'HEIGHT': str(height),
                        'FORMAT': 'image/png',
                        'TRANSPARENT': 'TRUE',
                        'viewparams': viewparams
                    }

                url = f'{self.base_url}?{urlencode(params)}'

                # v8: 캐시 확인
                cached_content = self._get_cached_response(url)
                if cached_content:
                    response_content = cached_content
                else:
                    # HTTP 요청
                    response = requests.get(url, timeout=180)
                    response.raise_for_status()

                    # Content-Type 확인
                    content_type = response.headers.get('Content-Type', '')
                    if 'image' not in content_type.lower():
                        self._log(f"Tile {tile_index}: Expected image but got {content_type}", level=Qgis.Warning)
                        return None

                    response_content = response.content
                    # v8: 캐시에 저장
                    self._cache_response(url, response_content)

                # PNG 저장
                png_path = os.path.join(self.temp_dir, f'tile_{layer_name}_{tile_index}.png')
                pgw_path = os.path.join(self.temp_dir, f'tile_{layer_name}_{tile_index}.pgw')

                with open(png_path, 'wb') as f:
                    f.write(response_content)

                # World file 생성
                self._create_world_file(tile_bbox, width, height, pgw_path)

                self.temp_files.extend([png_path, pgw_path])

                return (png_path, tile_bbox)

            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    self._log(f"Tile {tile_index} timeout (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...", level=Qgis.Warning)
                    time.sleep(wait_time)
                else:
                    self._log(f"Tile {tile_index} timeout after {max_retries} attempts", level=Qgis.Warning)
                    return None
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    self._log(f"Tile {tile_index} connection error (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...", level=Qgis.Warning)
                    time.sleep(wait_time)
                else:
                    self._log(f"Tile {tile_index} connection failed after {max_retries} attempts: {str(e)}", level=Qgis.Warning)
                    return None
            except requests.exceptions.HTTPError as e:
                # 4xx/5xx 에러는 재시도 불필요
                self._log(f"Tile {tile_index} HTTP error: {str(e)}", level=Qgis.Warning)
                return None
            except Exception as e:
                # 기타 에러는 즉시 실패
                self._log(f"Tile {tile_index} unexpected error: {str(e)}", level=Qgis.Critical)
                return None

        return None

    def _fetch_tiles_parallel(
        self,
        tiles: List[QgsRectangle],
        layer_name: str,
        style: str,
        viewparams: str,
        is_bbox_mode: bool = False,
        prov: Optional[str] = None
    ) -> List[Tuple[str, QgsRectangle]]:
        """
        v3: 타일들을 병렬로 요청

        Args:
            tiles: 타일 BBOX 목록
            layer_name: 레이어 이름
            style: 스타일
            viewparams: viewparams 문자열
            is_bbox_mode: BBOX 모드 여부
            prov: 시도 코드 (영역 B MV 사용 시)

        Returns:
            [(PNG 경로, bbox), ...] 목록
        """
        results = []
        total = len(tiles)

        with ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT) as executor:
            futures = {
                executor.submit(
                    self._fetch_single_tile,
                    tile, idx, layer_name, style, viewparams, is_bbox_mode, 3, prov
                ): idx
                for idx, tile in enumerate(tiles)
            }

            completed = 0
            for future in as_completed(futures):
                completed += 1
                result = future.result()
                if result:
                    results.append(result)

                # 진행률 시그널
                self.progress_updated.emit(
                    completed,
                    total,
                    f"{layer_name}: {completed}/{total} 타일"
                )

        return results

    def _merge_tiles_to_vrt(self, tile_results: List[Tuple[str, QgsRectangle]], output_name: str) -> Optional[str]:
        """
        v3: 타일들을 GDAL VRT로 합성

        Args:
            tile_results: [(PNG 경로, bbox), ...] 목록
            output_name: 출력 VRT 이름

        Returns:
            VRT 파일 경로 또는 None
        """
        if not HAS_GDAL:
            self._log("GDAL not available, cannot create VRT", level=Qgis.Warning)
            return None

        if not tile_results:
            return None

        vrt_path = os.path.join(self.temp_dir, f'{output_name}.vrt')
        tile_paths = [r[0] for r in tile_results]

        try:
            vrt = gdal.BuildVRT(vrt_path, tile_paths)
            vrt = None  # 저장 및 핸들 해제

            self.temp_files.append(vrt_path)
            self._log(f"VRT created: {vrt_path} ({len(tile_paths)} tiles)")
            return vrt_path

        except Exception as e:
            self._log(f"VRT creation failed: {str(e)}", level=Qgis.Critical)
            return None

    def _build_getmap_url(
        self,
        layer: str,
        style: str,
        bbox: QgsRectangle,
        width: int,
        height: int,
        region_code: str
    ) -> str:
        """GetMap 요청 URL 생성 (영역 A)"""
        params = {
            'SERVICE': 'WMS',
            'VERSION': '1.1.0',
            'REQUEST': 'GetMap',
            'LAYERS': layer,
            'STYLES': style,
            'SRS': self.CRS,
            'BBOX': f'{bbox.xMinimum()},{bbox.yMinimum()},{bbox.xMaximum()},{bbox.yMaximum()}',
            'WIDTH': str(width),
            'HEIGHT': str(height),
            'FORMAT': 'image/png',
            'TRANSPARENT': 'TRUE',
            'viewparams': f'prov:{region_code[:2]};region:{region_code}'
        }

        url = f'{self.base_url}?{urlencode(params)}'
        self._log(f"GetMap URL: {url}")
        return url

    def _build_getmap_url_bbox(
        self,
        layer: str,
        style: str,
        bbox: QgsRectangle,
        width: int,
        height: int,
        prov: Optional[str] = None
    ) -> str:
        """v7: BBOX 기반 GetMap 요청 URL 생성 (영역 B) - floor/ceil 적용"""
        # v7: floor/ceil 사용으로 BBOX 확장 (데이터 누락 방지)
        minx = math.floor(bbox.xMinimum())
        miny = math.floor(bbox.yMinimum())
        maxx = math.ceil(bbox.xMaximum())
        maxy = math.ceil(bbox.yMaximum())

        # prov가 있으면 MV 사용 (contour_bbox, road_bbox)
        if prov:
            vp = f'prov:{prov};minx:{minx};miny:{miny};maxx:{maxx};maxy:{maxy}'
        else:
            vp = f'minx:{minx};miny:{miny};maxx:{maxx};maxy:{maxy}'

        params = {
            'SERVICE': 'WMS',
            'VERSION': '1.1.0',
            'REQUEST': 'GetMap',
            'LAYERS': layer,
            'STYLES': style,
            'SRS': self.CRS,
            'BBOX': f'{minx},{miny},{maxx},{maxy}',
            'WIDTH': str(width),
            'HEIGHT': str(height),
            'FORMAT': 'image/png',
            'TRANSPARENT': 'TRUE',
            'viewparams': vp
        }

        url = f'{self.base_url}?{urlencode(params)}'
        self._log(f"GetMap BBOX URL: {url}")
        return url

    def _create_world_file(
        self,
        bbox: QgsRectangle,
        width: int,
        height: int,
        pgw_path: str
    ):
        """World file (.pgw) 생성"""
        pixel_size_x = bbox.width() / width
        pixel_size_y = -bbox.height() / height

        top_left_x = bbox.xMinimum() + (pixel_size_x / 2.0)
        top_left_y = bbox.yMaximum() + (pixel_size_y / 2.0)

        with open(pgw_path, 'w') as f:
            f.write(f"{pixel_size_x}\n")
            f.write("0.0\n")
            f.write("0.0\n")
            f.write(f"{pixel_size_y}\n")
            f.write(f"{top_left_x}\n")
            f.write(f"{top_left_y}\n")

    def _fetch_and_load_layer(
        self,
        layer_name: str,
        style: str,
        bbox: QgsRectangle,
        region_code: str,
        display_name: str
    ) -> Optional[QgsRasterLayer]:
        """
        v3: GetMap으로 이미지 가져와서 래스터 레이어 로드
        타일 방식 자동 적용
        """
        # v7.1: 임시 디렉토리 존재 확인
        self._ensure_temp_dir()

        try:
            # 타일 분할 필요 여부 확인
            needs_tile = self._needs_tiling(bbox)
            self._log(f"Extent: {bbox.width():.0f}m x {bbox.height():.0f}m, needs_tiling={needs_tile}")

            if needs_tile:
                self._log(f"Using tile mode for {display_name}")
                return self._load_layer_tiled(
                    layer_name, style, bbox,
                    f'prov:{region_code[:2]};region:{region_code}',
                    display_name,
                    is_bbox_mode=False
                )

            # 단일 요청 모드 - TARGET_RESOLUTION 기반
            width = int(bbox.width() / self.TARGET_RESOLUTION)
            height = int(bbox.height() / self.TARGET_RESOLUTION)

            # 최대 크기 제한
            if width > self.MAX_SINGLE_REQUEST or height > self.MAX_SINGLE_REQUEST:
                scale = self.MAX_SINGLE_REQUEST / max(width, height)
                width = int(width * scale)
                height = int(height * scale)

            width = max(100, width)
            height = max(100, height)

            self._log(f"Image size: {width}x{height}")

            url = self._build_getmap_url(layer_name, style, bbox, width, height, region_code)

            # v8: 캐시 확인
            cached_content = self._get_cached_response(url)
            if cached_content:
                response_content = cached_content
            else:
                response = requests.get(url, timeout=180)
                response.raise_for_status()
                response_content = response.content
                # v8: 캐시에 저장
                self._cache_response(url, response_content)

            png_path = os.path.join(self.temp_dir, f'wms_{display_name}_{id(self)}.png')
            pgw_path = os.path.join(self.temp_dir, f'wms_{display_name}_{id(self)}.pgw')

            with open(png_path, 'wb') as f:
                f.write(response_content)

            self._create_world_file(bbox, width, height, pgw_path)
            self.temp_files.extend([png_path, pgw_path])

            layer = QgsRasterLayer(png_path, display_name, 'gdal')

            if layer.isValid():
                crs = QgsCoordinateReferenceSystem(self.CRS)
                layer.setCrs(crs)
                self._log(f"Layer loaded: {display_name}")
                return layer
            else:
                self._log(f"Layer load failed: {display_name}", level=Qgis.Warning)
                return None

        except Exception as e:
            self._log(f"Error loading {display_name}: {str(e)}", level=Qgis.Critical)
            return None

    def _load_layer_tiled(
        self,
        layer_name: str,
        style: str,
        bbox: QgsRectangle,
        viewparams: str,
        display_name: str,
        is_bbox_mode: bool = False,
        prov: Optional[str] = None
    ) -> Optional[QgsRasterLayer]:
        """
        v3: 타일 방식으로 레이어 로드

        Args:
            layer_name: GeoServer 레이어 이름
            style: 스타일
            bbox: 전체 범위
            viewparams: viewparams 문자열
            display_name: 표시 이름
            is_bbox_mode: BBOX 모드 여부

        Returns:
            QgsRasterLayer 또는 None
        """
        # 타일 분할
        tiles = self._calculate_tiles(bbox)
        self._log(f"Fetching {len(tiles)} tiles for {display_name}")

        # 병렬 요청
        tile_results = self._fetch_tiles_parallel(
            tiles, layer_name, style, viewparams, is_bbox_mode, prov
        )

        # 부분 타일 실패 경고
        if len(tile_results) < len(tiles):
            failed_count = len(tiles) - len(tile_results)
            self._log(
                f"Warning: {failed_count}/{len(tiles)} tiles failed for {display_name}",
                level=Qgis.Warning
            )

        if not tile_results:
            self._log(f"No tiles fetched for {display_name}", level=Qgis.Warning)
            return None

        # VRT 합성
        if HAS_GDAL and len(tile_results) > 1:
            vrt_path = self._merge_tiles_to_vrt(tile_results, f'{display_name}_{id(self)}')
            if vrt_path:
                layer = QgsRasterLayer(vrt_path, display_name, 'gdal')
                if layer.isValid():
                    crs = QgsCoordinateReferenceSystem(self.CRS)
                    layer.setCrs(crs)
                    return layer

        # VRT 실패 시 첫 번째 타일만 사용
        if tile_results:
            first_tile = tile_results[0][0]
            layer = QgsRasterLayer(first_tile, display_name, 'gdal')
            if layer.isValid():
                crs = QgsCoordinateReferenceSystem(self.CRS)
                layer.setCrs(crs)
                return layer

        return None

    def _fetch_and_load_layer_bbox(
        self,
        layer_name: str,
        style: str,
        bbox: QgsRectangle,
        display_name: str,
        prov: Optional[str] = None
    ) -> Optional[QgsRasterLayer]:
        """
        v3: BBOX 기반 GetMap으로 래스터 레이어 로드 (영역 B용)
        타일 방식 자동 적용
        """
        # v7.1: 임시 디렉토리 존재 확인
        self._ensure_temp_dir()

        try:
            # 타일 분할 필요 여부 확인
            if self._needs_tiling(bbox):
                self._log(f"Using tile mode for {display_name}")
                return self._load_layer_tiled(
                    layer_name, style, bbox,
                    '',  # viewparams는 타일별로 생성
                    display_name,
                    is_bbox_mode=True,
                    prov=prov
                )

            # 단일 요청 모드 - TARGET_RESOLUTION 기반
            width = int(bbox.width() / self.TARGET_RESOLUTION)
            height = int(bbox.height() / self.TARGET_RESOLUTION)

            # 최대 크기 제한
            if width > self.MAX_SINGLE_REQUEST or height > self.MAX_SINGLE_REQUEST:
                scale = self.MAX_SINGLE_REQUEST / max(width, height)
                width = int(width * scale)
                height = int(height * scale)

            width = max(100, width)
            height = max(100, height)

            self._log(f"Image size (BBOX): {width}x{height}, prov={prov}")

            url = self._build_getmap_url_bbox(layer_name, style, bbox, width, height, prov)

            # v8: 캐시 확인
            cached_content = self._get_cached_response(url)
            if cached_content:
                response_content = cached_content
            else:
                response = requests.get(url, timeout=180)
                response.raise_for_status()

                content_type = response.headers.get('Content-Type', '')
                if 'image' not in content_type.lower():
                    try:
                        error_text = response.text[:500]
                        self._log(f"GeoServer error: {error_text}", level=Qgis.Critical)
                    except:
                        pass
                    return None

                response_content = response.content
                # v8: 캐시에 저장
                self._cache_response(url, response_content)

            png_path = os.path.join(self.temp_dir, f'wms_{display_name}_{id(self)}.png')
            pgw_path = os.path.join(self.temp_dir, f'wms_{display_name}_{id(self)}.pgw')

            with open(png_path, 'wb') as f:
                f.write(response_content)

            self._create_world_file(bbox, width, height, pgw_path)
            self.temp_files.extend([png_path, pgw_path])

            layer = QgsRasterLayer(png_path, display_name, 'gdal')

            if layer.isValid():
                crs = QgsCoordinateReferenceSystem(self.CRS)
                layer.setCrs(crs)
                self._log(f"Layer loaded (BBOX): {display_name}")
                return layer
            else:
                self._log(f"Layer load failed: {display_name}", level=Qgis.Warning)
                return None

        except Exception as e:
            self._log(f"Error loading {display_name}: {str(e)}", level=Qgis.Critical)
            return None

    def load_area_a(
        self,
        region_code: str,
        bbox: QgsRectangle
    ) -> Dict[str, QgsRasterLayer]:
        """영역 A 레이어 로드 - 순서: 행정구역(상) → 등고선 → 도로(하)"""
        layers = {}
        project = QgsProject.instance()
        root = project.layerTreeRoot()

        self.current_prov = region_code[:2]  # 영역 B에서 재사용
        self._log(f"Loading Area A: region={region_code}, prov={self.current_prov}")
        start_time = time.time()

        # 레이어 추가 순서: road → contour → hjd (맨 위에 삽입되므로 역순)
        layer_order = ['road', 'contour', 'hjd']
        total_layers = len(layer_order)

        for idx, key in enumerate(layer_order):
            config = self.LAYERS[key]
            display_name = config['display_name_a']

            self.progress_updated.emit(idx + 1, total_layers, f"영역 A: {display_name}")

            self._remove_layer_by_name(display_name)

            layer = self._fetch_and_load_layer(
                layer_name=config['layer_a'],
                style=config['style_a'],
                bbox=bbox,
                region_code=region_code,
                display_name=display_name
            )

            if layer:
                # 레이어 등록 (트리에는 추가 안함)
                project.addMapLayer(layer, addToLegend=False)
                # 맨 위에 삽입 (역순이므로 결과: hjd → contour → road)
                tree_node = QgsLayerTreeLayer(layer)
                tree_node.setExpanded(False)
                root.insertChildNode(0, tree_node)
                layers[key] = layer
                self.loaded_layers[display_name] = layer

        elapsed = time.time() - start_time
        self._log(f"[V7 성능] Area A 로드 완료: {elapsed:.2f}초")

        return layers

    def load_area_b(
        self,
        bbox: QgsRectangle
    ) -> Dict[str, QgsRasterLayer]:
        """영역 B 레이어 로드 (A0 박스 BBOX 기반) - A 레이어 아래에 배치"""
        layers = {}
        project = QgsProject.instance()
        root = project.layerTreeRoot()

        self._log(f"Loading Area B (BBOX): {bbox.toString()}")
        start_time = time.time()

        # A 레이어 개수 확인 (B는 A 아래에 삽입)
        a_layer_count = 0
        for key in ['hjd', 'contour', 'road']:
            config = self.LAYERS[key]
            if project.mapLayersByName(config['display_name_a']):
                a_layer_count += 1

        # B 레이어 추가 순서: road → contour → hjd (A 아래에 역순 삽입)
        layer_order = ['road', 'contour', 'hjd']
        total_layers = len(layer_order)

        for idx, key in enumerate(layer_order):
            config = self.LAYERS[key]
            display_name = config['display_name_b']

            self.progress_updated.emit(idx + 1, total_layers, f"영역 B: {display_name}")

            self._remove_layer_by_name(display_name)

            layer = self._fetch_and_load_layer_bbox(
                layer_name=config['layer_b'],
                style=config['style_b'],
                bbox=bbox,
                display_name=display_name
            )

            if layer:
                # 레이어 등록 (트리에는 추가 안함)
                project.addMapLayer(layer, addToLegend=False)
                # A 레이어 바로 아래에 삽입 (인덱스 = A 레이어 개수)
                tree_node = QgsLayerTreeLayer(layer)
                tree_node.setExpanded(False)
                root.insertChildNode(a_layer_count, tree_node)
                layers[key] = layer
                self.loaded_layers[display_name] = layer

        elapsed = time.time() - start_time
        self._log(f"[V7 성능] Area B 로드 완료: {elapsed:.2f}초")

        return layers

    def get_region_extent(self, region_code: str) -> Optional[QgsRectangle]:
        """WFS로 행정구역 범위 조회"""
        try:
            wfs_url = self.base_url.replace('/wms', '/wfs')

            params = {
                'SERVICE': 'WFS',
                'VERSION': '2.0.0',
                'REQUEST': 'GetFeature',
                'TYPENAME': 'hjd_mv_filter',
                'outputFormat': 'application/json',
                'viewparams': f'prov:{region_code[:2]};region:{region_code}',
                'srsName': self.CRS
            }

            url = f'{wfs_url}?{urlencode(params)}'
            self._log(f"WFS GetFeature URL: {url}")

            response = requests.get(url, timeout=180)
            response.raise_for_status()

            data = response.json()
            features = data.get('features', [])

            if not features:
                self._log(f"No features found for region {region_code}", level=Qgis.Warning)
                return None

            self._log(f"WFS features loaded: {len(features)}")

            bounds = None
            for feature in features:
                geom = feature.get('geometry', {})
                geom_type = geom.get('type', '')
                coords = geom.get('coordinates', [])

                if geom_type == 'Polygon' and coords:
                    for ring in coords:
                        for coord in ring:
                            x, y = coord[0], coord[1]
                            if bounds is None:
                                bounds = [x, y, x, y]
                            else:
                                bounds[0] = min(bounds[0], x)
                                bounds[1] = min(bounds[1], y)
                                bounds[2] = max(bounds[2], x)
                                bounds[3] = max(bounds[3], y)
                elif geom_type == 'MultiPolygon' and coords:
                    for polygon in coords:
                        for ring in polygon:
                            for coord in ring:
                                x, y = coord[0], coord[1]
                                if bounds is None:
                                    bounds = [x, y, x, y]
                                else:
                                    bounds[0] = min(bounds[0], x)
                                    bounds[1] = min(bounds[1], y)
                                    bounds[2] = max(bounds[2], x)
                                    bounds[3] = max(bounds[3], y)

            if bounds:
                extent = QgsRectangle(bounds[0], bounds[1], bounds[2], bounds[3])
                self._log(f"Region extent: {extent.toString()}")
                return extent

            return None

        except Exception as e:
            self._log(f"Error getting region extent: {str(e)}", level=Qgis.Critical)
            return None

    def _reorder_layers(self):
        """
        v8: 레이어 순서 조정 - 영역 A가 B 위에, 행정구역이 최상단

        원하는 순서 (위→아래):
        1. 행정구역_A (최상단)
        2. 등고선_A
        3. 도로중심선_A
        4. 행정구역_B
        5. 등고선_B
        6. 도로중심선_B (최하단)
        """
        project = QgsProject.instance()
        root = project.layerTreeRoot()

        # 원하는 순서 (위에서 아래로)
        desired_order = [
            self.LAYERS['hjd']['display_name_a'],     # 1. 행정구역_A (최상단)
            self.LAYERS['contour']['display_name_a'], # 2. 등고선_A
            self.LAYERS['road']['display_name_a'],    # 3. 도로중심선_A
            self.LAYERS['hjd']['display_name_b'],     # 4. 행정구역_B
            self.LAYERS['contour']['display_name_b'], # 5. 등고선_B
            self.LAYERS['road']['display_name_b'],    # 6. 도로중심선_B (최하단)
        ]

        # 1단계: 존재하는 레이어와 노드 수집
        layers_to_move = []
        for layer_name in desired_order:
            map_layers = project.mapLayersByName(layer_name)
            for layer in map_layers:
                node = root.findLayer(layer.id())
                if node:
                    layers_to_move.append((layer_name, layer, node))

        if not layers_to_move:
            return

        # 2단계: 모든 노드를 루트에서 제거 (클론 저장)
        clones = []
        for layer_name, layer, node in layers_to_move:
            clone = node.clone()
            clones.append((layer_name, clone))
            root.removeChildNode(node)

        # 3단계: 역순으로 삽입 (맨 위에 삽입하므로)
        for layer_name, clone in reversed(clones):
            root.insertChildNode(0, clone)
            self._log(f"Layer reordered: {layer_name}")

    def _remove_layer_by_name(self, name: str):
        """이름으로 레이어 제거"""
        project = QgsProject.instance()
        layers = project.mapLayersByName(name)
        for layer in layers:
            project.removeMapLayer(layer.id())

    def clear_layers(self, area: str = 'both'):
        """레이어 제거"""
        for config in self.LAYERS.values():
            if area.upper() in ['A', 'BOTH']:
                self._remove_layer_by_name(config['display_name_a'])
            if area.upper() in ['B', 'BOTH']:
                self._remove_layer_by_name(config['display_name_b'])

    def cleanup(self):
        """리소스 정리"""
        self.clear_layers('both')

        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                self._log(f"Failed to remove {temp_file}: {str(e)}", level=Qgis.Warning)

        # 임시 디렉토리 삭제 시도
        try:
            if os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass

        self.temp_files.clear()
        self.loaded_layers.clear()

    def _log(self, message: str, level=Qgis.Info):
        """로그 메시지 출력"""
        QgsMessageLog.logMessage(message, 'BasePlan', level)
        print(f"[WMSManager] {message}")
