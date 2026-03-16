"""
GIS Water Plugin - QGIS Plugin Entry Point

This module provides the classFactory function required by QGIS to load the plugin.
"""


def classFactory(iface):
    """
    Load GISLayerLoaderPlugin class from gis_layer_loader_plugin module.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .gis_layer_loader_plugin import GISLayerLoaderPlugin
    return GISLayerLoaderPlugin(iface)
