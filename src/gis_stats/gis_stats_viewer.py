"""
GIS Stats Viewer - Main Plugin Class
"""

import os
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProject

from .ui.main_dialog import MainDialog


class GisStatsViewer:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = "GIS Stats Viewer"
        self.toolbar = self.iface.addToolBar("GIS Stats Viewer")
        self.toolbar.setObjectName("GisStatsViewerToolbar")

        # Dialog instance (for modeless behavior)
        self.dialog = None

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
    ):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action.
        :param text: Text that should be shown in menu items for this action.
        :param callback: Function to be called when the action is triggered.
        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :param parent: Parent widget for the new action. Defaults None.
        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.
        :returns: The action that was created.
        :rtype: QAction
        """
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        self.add_action(
            icon_path,
            text="통계정보 뷰어",
            callback=self.run,
            parent=self.iface.mainWindow(),
            status_tip="행정구역별 통계정보 조인 및 시각화",
        )

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)

        # Remove the toolbar
        del self.toolbar

        # Close dialog if open
        if self.dialog:
            self.dialog.close()
            self.dialog = None

    def run(self):
        """Run method that performs all the real work."""
        # Create dialog if not exists or was closed
        if self.dialog is None:
            self.dialog = MainDialog(self.iface, parent=self.iface.mainWindow())
            # Connect to destroyed signal to clean up reference
            self.dialog.destroyed.connect(self._on_dialog_destroyed)

        # Show the dialog (modeless)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def _on_dialog_destroyed(self):
        """Handle dialog destroyed signal."""
        self.dialog = None
