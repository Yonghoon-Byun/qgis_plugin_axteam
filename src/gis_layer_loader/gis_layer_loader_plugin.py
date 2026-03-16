"""
GIS Layer Loader Plugin - Main Plugin Class
"""

import os
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QCoreApplication

from .region_selector_dialog import RegionSelectorDialog


class GISLayerLoaderPlugin:
    """QGIS Plugin Implementation for GIS Layer Loader"""

    def __init__(self, iface):
        """
        Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        # Dialog instance (will be created when action is triggered)
        self.dialog = None

        # Plugin action
        self.action = None

    def tr(self, message):
        """Get the translation for a string using Qt translation API"""
        return QCoreApplication.translate('GISLayerLoaderPlugin', message)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI"""

        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        icon = QIcon(icon_path)

        # Create action that will start plugin configuration
        self.action = QAction(
            icon,
            self.tr('GIS Layer Loader'),
            self.iface.mainWindow()
        )

        # Connect the action to the run method
        self.action.triggered.connect(self.run)

        # Add toolbar button
        self.iface.addToolBarIcon(self.action)

        # Add menu item
        self.iface.addPluginToMenu(
            self.tr('&GIS Layer Loader'),
            self.action
        )

    def unload(self):
        """Remove the plugin menu item and icon from QGIS GUI"""

        # Remove the plugin menu item and icon
        self.iface.removePluginMenu(
            self.tr('&GIS Layer Loader'),
            self.action
        )
        self.iface.removeToolBarIcon(self.action)

        # Close dialog if it exists
        if self.dialog:
            self.dialog.close()
            self.dialog = None

    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog if it doesn't exist
        if self.dialog is None:
            self.dialog = RegionSelectorDialog(self.iface.mainWindow())

        # Show the dialog (modeless)
        self.dialog.show()

        # Bring it to the front
        self.dialog.raise_()
        self.dialog.activateWindow()
