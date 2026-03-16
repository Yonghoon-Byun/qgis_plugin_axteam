# -*- coding: utf-8 -*-
"""
Reservoir Site Analyzer - Dialog Class
배수지(저수지) 설계를 위한 적합 부지 분석 다이얼로그
"""

import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog

# UI 파일 로드
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'reservoir_site_analyzer_dialog.ui'))


class ReservoirSiteAnalyzerDialog(QDialog, FORM_CLASS):
    """배수지 적합 부지 분석 다이얼로그 클래스"""

    def __init__(self, parent=None):
        """다이얼로그 초기화

        Args:
            parent: 부모 위젯
        """
        super(ReservoirSiteAnalyzerDialog, self).__init__(parent)
        self.setupUi(self)
