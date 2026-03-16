# -*- coding: utf-8 -*-
"""
Civil Planner Plugin - QGIS 진입점
"""

import os.path
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .ui.wizard_dialog import CivilPlannerWizard


class CivilPlanner:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = "&Civil Planner"
        self.toolbar = self.iface.addToolBar("Civil Planner")
        self.toolbar.setObjectName("CivilPlanner")
        self.dialog = None

    def add_action(self, icon_path, text, callback, parent=None):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent or self.iface.mainWindow())
        action.triggered.connect(callback)
        self.toolbar.addAction(action)
        self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        self.add_action(
            icon_path,
            "Civil Planner",
            self.run,
        )

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)
        if self.toolbar:
            self.toolbar.deleteLater()
            self.toolbar = None
        if self.dialog:
            self.dialog.close()
            self.dialog = None

    def run(self):
        # 다이얼로그 재사용 (작업 상태 유지)
        if self.dialog is None:
            self.dialog = CivilPlannerWizard(self.iface)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
