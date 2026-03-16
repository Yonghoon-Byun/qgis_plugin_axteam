from qgis.core import QgsProject, QgsVectorLayer


def get_all_vector_layers():
    """Get all vector layers from current project."""
    layers = []
    for layer in QgsProject.instance().mapLayers().values():
        if isinstance(layer, QgsVectorLayer):
            layers.append(layer)
    return layers


def get_shapefile_layers():
    """Get only shapefile layers."""
    layers = []
    for layer in QgsProject.instance().mapLayers().values():
        if isinstance(layer, QgsVectorLayer):
            provider = layer.dataProvider()
            if provider and provider.name() == 'ogr':
                uri = provider.dataSourceUri()
                if '.shp' in uri.lower():
                    layers.append(layer)
    return layers


def refresh_layer(layer):
    """Refresh a layer to show changes."""
    if layer:
        layer.reload()
        layer.triggerRepaint()


def is_memory_layer(layer):
    """Check if layer is a memory/scratch layer."""
    if not layer:
        return False
    provider = layer.dataProvider()
    if provider:
        return provider.name() == 'memory'
    return False


def get_layer_encoding(layer):
    """Get current encoding of a layer."""
    if layer and layer.dataProvider():
        return layer.dataProvider().encoding()
    return None
