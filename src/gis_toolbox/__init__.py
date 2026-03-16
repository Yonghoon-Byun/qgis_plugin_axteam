def classFactory(iface):
    from .gis_toolbox import GisToolbox
    return GisToolbox(iface)
