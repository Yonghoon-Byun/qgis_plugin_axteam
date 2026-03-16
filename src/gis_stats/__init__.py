"""
GIS Stats Viewer - QGIS Plugin
행정구역별 경계에 통계정보를 조인하여 시각화하는 플러그인
"""


def classFactory(iface):
    """
    Load GisStatsViewer class from file gis_stats_viewer.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .gis_stats_viewer import GisStatsViewer
    return GisStatsViewer(iface)
