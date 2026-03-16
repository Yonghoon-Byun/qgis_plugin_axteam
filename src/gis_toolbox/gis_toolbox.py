from qgis.PyQt.QtWidgets import QAction, QToolButton, QMenu
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProject
import os

class GisToolbox:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.toolbar = None
        self.tool_button = None
        self.menu = None
        self.dialogs = {}

    def initGui(self):
        # Create toolbar
        self.toolbar = self.iface.addToolBar("GIS Toolbox")
        self.toolbar.setObjectName("GISToolbox")

        # Create tool button with dropdown
        self.tool_button = QToolButton()
        self.tool_button.setText("GIS Toolbox")
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        if os.path.exists(icon_path):
            self.tool_button.setIcon(QIcon(icon_path))
        self.tool_button.setPopupMode(QToolButton.InstantPopup)
        self.tool_button.setToolTip("GIS Toolbox")

        # Create menu
        self.menu = QMenu()

        # Add menu actions
        self.action_crs = self.menu.addAction("좌표계 정의")
        self.action_crs.triggered.connect(self.show_crs_dialog)

        self.action_encoding = self.menu.addAction("인코딩 변경")
        self.action_encoding.triggered.connect(self.show_encoding_dialog)

        self.action_saver = self.menu.addAction("레이어 저장")
        self.action_saver.triggered.connect(self.show_saver_dialog)

        self.action_geometry = self.menu.addAction("도형 수정")
        self.action_geometry.triggered.connect(self.show_geometry_dialog)

        self.action_rename = self.menu.addAction("레이어명 변경")
        self.action_rename.triggered.connect(self.show_rename_dialog)

        self.tool_button.setMenu(self.menu)
        self.toolbar.addWidget(self.tool_button)

    def unload(self):
        # Close any open dialogs
        for dialog in self.dialogs.values():
            if dialog:
                dialog.close()

        # Remove toolbar
        if self.toolbar:
            del self.toolbar

    def show_crs_dialog(self):
        from .dialogs.crs_dialog import CrsDialog
        if 'crs' not in self.dialogs or self.dialogs['crs'] is None:
            self.dialogs['crs'] = CrsDialog(self.iface)
        self.dialogs['crs'].show()
        self.dialogs['crs'].raise_()

    def show_encoding_dialog(self):
        from .dialogs.encoding_dialog import EncodingDialog
        if 'encoding' not in self.dialogs or self.dialogs['encoding'] is None:
            self.dialogs['encoding'] = EncodingDialog(self.iface)
        self.dialogs['encoding'].show()
        self.dialogs['encoding'].raise_()

    def show_saver_dialog(self):
        from .dialogs.saver_dialog import SaverDialog
        if 'saver' not in self.dialogs or self.dialogs['saver'] is None:
            self.dialogs['saver'] = SaverDialog(self.iface)
        self.dialogs['saver'].show()
        self.dialogs['saver'].raise_()

    def show_geometry_dialog(self):
        from .dialogs.geometry_dialog import GeometryDialog
        if 'geometry' not in self.dialogs or self.dialogs['geometry'] is None:
            self.dialogs['geometry'] = GeometryDialog(self.iface)
        self.dialogs['geometry'].show()
        self.dialogs['geometry'].raise_()

    def show_rename_dialog(self):
        from .dialogs.rename_dialog import RenameDialog
        if 'rename' not in self.dialogs or self.dialogs['rename'] is None:
            self.dialogs['rename'] = RenameDialog(self.iface)
        self.dialogs['rename'].show()
        self.dialogs['rename'].raise_()
