# -*- coding: utf-8 -*-
"""
Civil Planner - QGIS Plugin
토목 관로 설계 워크플로우 플러그인
"""


def classFactory(iface):
    """QGIS Plugin 로드 함수

    Args:
        iface: QgisInterface 인스턴스

    Returns:
        CivilPlanner: 플러그인 인스턴스
    """
    from .plugin import CivilPlanner
    return CivilPlanner(iface)
