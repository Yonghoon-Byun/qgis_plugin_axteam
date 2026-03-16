# -*- coding: utf-8 -*-
"""
BasePlan QGIS Plugin
토목 기본도면 작성 플러그인
"""


def classFactory(iface):
    """Load BasePlan class from file plugin.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .plugin import BasePlan
    return BasePlan(iface)
