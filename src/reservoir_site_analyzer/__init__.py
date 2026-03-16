# -*- coding: utf-8 -*-
"""
Reservoir Site Analyzer - QGIS Plugin
배수지(저수지) 설계를 위한 적합 부지 분석 플러그인

Author: GIS Water Team
"""


def classFactory(iface):
    """QGIS Plugin 로드 함수

    Args:
        iface: QgisInterface 인스턴스

    Returns:
        ReservoirSiteAnalyzer: 플러그인 인스턴스
    """
    from .reservoir_site_analyzer import ReservoirSiteAnalyzer
    return ReservoirSiteAnalyzer(iface)
