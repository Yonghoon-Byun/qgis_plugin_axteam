# -*- coding: utf-8 -*-
"""
스타일 매니저 - qgis_layer_style_library.xml 기반 자동 스타일 적용
"""

import os
import xml.etree.ElementTree as ET
from qgis.core import QgsVectorLayer, QgsReadWriteContext
from qgis.PyQt.QtXml import QDomDocument


# 레이어 이름 → 스타일 심볼 이름 매핑 (00_상하수도 태그)
LAYER_STYLE_MAP = {
    # 지형지물
    "건축물정보": "지형지물_건물",
    "도로경계선": "지형지물_도로",
    "도로중심선": "실선_7_검정",
    "연속지적도": "지형지물_지적",
    "하천경계": "지형지물_하천",
    "하천중심선": "실선_4_하늘",
    "등고선": "등고선",
    "호수 및 저수지": "지형지물_하천",
    "터널": "실선_8_회색",
    # 경계
    "행정동 경계": "경계_읍면동",
    "경계_시군구": "경계_시군구",
    "경계_리": "경계_리",
    # 관로
    "관로_계획": "관로_계획",
    "관로_기존": "관로_기존",
    "계획 노선": "관로_계획",
    # 지장물
    "지장물_가스": "지장물_가스",
    "지장물_고압전기": "지장물_고압전기",
    "지장물_광역상수": "지장물_광역상수",
    "지장물_난방": "지장물_난방",
    "지장물_전기_저압": "지장물_전기_저압",
    "지장물_지방상수": "지장물_지방상수",
    "지장물_통신": "지장물_통신",
    "지장물_하수": "지장물_하수",
    # 단지 관련
    "단지경계": "빈_폴리곤_7_검정",
    "단지시설용지": "폴리곤_3_초록_투명",
    "단지용도지역": "폴리곤_4_하늘_투명",
    "단지유치업종": "폴리곤_2_노랑_투명",
    # 토지
    "토지소유정보": "지형지물_지적",
}


class StyleManager:
    """스타일 라이브러리 XML에서 심볼을 로드하고 레이어에 적용"""

    def __init__(self):
        self.style_xml_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "styles",
            "qgis_layer_style_library.xml",
        )
        self._symbol_cache = {}  # 심볼 이름 → QDomElement
        self._loaded = False

    def _ensure_loaded(self):
        """XML 파싱 (최초 1회)"""
        if self._loaded:
            return

        if not os.path.exists(self.style_xml_path):
            print(f"[StyleManager] Style XML not found: {self.style_xml_path}")
            return

        try:
            tree = ET.parse(self.style_xml_path)
            root = tree.getroot()
            symbols = root.find("symbols")
            if symbols is not None:
                for sym in symbols.findall("symbol"):
                    name = sym.get("name", "")
                    if name and not name.startswith("@"):
                        self._symbol_cache[name] = sym
            self._loaded = True
            print(f"[StyleManager] Loaded {len(self._symbol_cache)} symbols")
        except Exception as e:
            print(f"[StyleManager] Error loading XML: {e}")

    def apply_style_to_layer(self, layer, layer_name=None):
        """레이어에 스타일 라이브러리의 심볼을 적용

        Args:
            layer: QgsVectorLayer
            layer_name: 매핑에 사용할 이름 (없으면 layer.name() 사용)
        """
        if not isinstance(layer, QgsVectorLayer):
            return False

        name = layer_name or layer.name()

        # 매핑 테이블에서 심볼 이름 찾기
        symbol_name = LAYER_STYLE_MAP.get(name)
        if not symbol_name:
            # 부분 매칭 시도
            for key, val in LAYER_STYLE_MAP.items():
                if key in name or name in key:
                    symbol_name = val
                    break

        if not symbol_name:
            return False

        return self._apply_symbol_from_xml(layer, symbol_name)

    def _apply_symbol_from_xml(self, layer, symbol_name):
        """XML의 심볼을 QgsVectorLayer에 적용"""
        self._ensure_loaded()

        if symbol_name not in self._symbol_cache:
            print(f"[StyleManager] Symbol not found: {symbol_name}")
            return False

        try:
            # ElementTree → QDomDocument 변환
            sym_elem = self._symbol_cache[symbol_name]
            xml_str = ET.tostring(sym_elem, encoding="unicode")

            doc = QDomDocument()
            doc.setContent(xml_str)
            sym_node = doc.documentElement()

            context = QgsReadWriteContext()
            from qgis.core import QgsSymbolLayerUtils
            symbol = QgsSymbolLayerUtils.loadSymbol(sym_node, context)

            if symbol is not None:
                layer.renderer().setSymbol(symbol)
                layer.triggerRepaint()
                print(f"[StyleManager] Applied '{symbol_name}' to '{layer.name()}'")
                return True
            else:
                print(f"[StyleManager] Failed to create symbol: {symbol_name}")
                return False

        except Exception as e:
            print(f"[StyleManager] Error applying symbol '{symbol_name}': {e}")
            return False

    def get_available_symbols(self):
        """사용 가능한 심볼 이름 목록"""
        self._ensure_loaded()
        return list(self._symbol_cache.keys())
