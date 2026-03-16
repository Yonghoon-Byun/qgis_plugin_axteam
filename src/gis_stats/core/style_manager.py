"""
Style Manager - Quantile classification and color mapping
"""

from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import (
    QgsVectorLayer,
    QgsGraduatedSymbolRenderer,
    QgsClassificationQuantile,
    QgsClassificationEqualInterval,
    QgsClassificationJenks,
    QgsRendererRange,
    QgsSymbol,
    QgsFillSymbol,
    QgsStyle,
    QgsGradientColorRamp,
    QgsPalLayerSettings,
    QgsTextFormat,
    QgsTextBufferSettings,
    QgsVectorLayerSimpleLabeling,
    QgsUnitTypes,
)


class StyleManager(QObject):
    """Manage layer styling with classification methods."""

    # Signals
    style_applied = pyqtSignal()
    error_occurred = pyqtSignal(str)

    # Available color ramps (start_color, end_color)
    COLOR_RAMPS = {
        "blues": (QColor(239, 243, 255), QColor(8, 81, 156)),
        "greens": (QColor(237, 248, 233), QColor(0, 109, 44)),
        "reds": (QColor(254, 229, 217), QColor(165, 15, 21)),
        "oranges": (QColor(254, 237, 222), QColor(166, 54, 3)),
        "purples": (QColor(242, 240, 247), QColor(84, 39, 143)),
        "greys": (QColor(247, 247, 247), QColor(37, 37, 37)),
        "blue_green": (QColor(237, 248, 251), QColor(0, 68, 27)),
        "yellow_red": (QColor(255, 255, 178), QColor(189, 0, 38)),
    }

    # Classification methods
    CLASSIFICATION_METHODS = {
        "quantile": QgsClassificationQuantile,
        "equal_interval": QgsClassificationEqualInterval,
        "jenks": QgsClassificationJenks,
    }

    def __init__(self, parent=None):
        """Initialize the style manager.

        :param parent: Parent QObject
        """
        super().__init__(parent)

    def get_numeric_fields(self, layer):
        """Get list of numeric fields from a layer.

        :param layer: QgsVectorLayer
        :returns: List of field names
        :rtype: list
        """
        if not layer or not layer.isValid():
            return []

        numeric_types = [
            "Integer", "Integer64", "Real", "Double",
            2, 4, 6,  # QVariant types
        ]

        numeric_fields = []
        for field in layer.fields():
            if field.typeName() in numeric_types or field.type() in numeric_types:
                numeric_fields.append(field.name())

        return numeric_fields

    def get_available_color_ramps(self):
        """Get list of available color ramp names.

        :returns: List of color ramp names
        :rtype: list
        """
        return list(self.COLOR_RAMPS.keys())

    def get_available_classification_methods(self):
        """Get list of available classification methods.

        :returns: Dictionary of method key -> display name
        :rtype: dict
        """
        return {
            "quantile": "분위수 (Quantile)",
            "equal_interval": "등간격 (Equal Interval)",
            "jenks": "자연분류 (Natural Breaks)",
        }

    def apply_graduated_style(
        self,
        layer,
        field_name,
        num_classes=5,
        color_ramp="blues",
        classification_method="quantile",
    ):
        """Apply graduated (classified) style to a layer.

        :param layer: QgsVectorLayer to style
        :param field_name: Field name to classify on
        :param num_classes: Number of classes (default: 5)
        :param color_ramp: Color ramp name (default: blues)
        :param classification_method: Classification method (default: quantile)
        :returns: True if successful
        :rtype: bool
        """
        if not layer or not layer.isValid():
            self.error_occurred.emit("유효하지 않은 레이어입니다.")
            return False

        if field_name not in [f.name() for f in layer.fields()]:
            self.error_occurred.emit(f"필드를 찾을 수 없습니다: {field_name}")
            return False

        try:
            # Create graduated renderer
            renderer = QgsGraduatedSymbolRenderer(field_name)

            # Set classification method
            if classification_method in self.CLASSIFICATION_METHODS:
                method_class = self.CLASSIFICATION_METHODS[classification_method]
                renderer.setClassificationMethod(method_class())
            else:
                renderer.setClassificationMethod(QgsClassificationQuantile())

            # Create color ramp
            if color_ramp in self.COLOR_RAMPS:
                start_color, end_color = self.COLOR_RAMPS[color_ramp]
            else:
                start_color, end_color = self.COLOR_RAMPS["blues"]

            gradient_ramp = QgsGradientColorRamp(start_color, end_color)

            # Update classes
            renderer.updateClasses(layer, num_classes)
            renderer.updateColorRamp(gradient_ramp)

            # Set thicker outline for all ranges
            for range_item in renderer.ranges():
                symbol = range_item.symbol()
                if symbol:
                    # Set outline width to 0.5mm (thicker than default 0.26mm)
                    symbol.symbolLayer(0).setStrokeWidth(0.5)
                    # Set outline color to dark gray
                    symbol.symbolLayer(0).setStrokeColor(QColor(80, 80, 80))

            # Apply renderer to layer
            layer.setRenderer(renderer)
            layer.triggerRepaint()

            self.style_applied.emit()
            return True

        except Exception as e:
            self.error_occurred.emit(f"스타일 적용 실패: {str(e)}")
            return False

    def apply_labels(
        self,
        layer,
        field_name,
        font_family="굴림",
        font_size=9,
        buffer_size=0.8,
    ):
        """Apply labels to a layer with thousand separator formatting.

        :param layer: QgsVectorLayer to label
        :param field_name: Field name to use for labels
        :param font_family: Font family name (default: 굴림)
        :param font_size: Font size in points (default: 9)
        :param buffer_size: Text buffer size in mm (default: 0.8)
        :returns: True if successful
        :rtype: bool
        """
        if not layer or not layer.isValid():
            self.error_occurred.emit("유효하지 않은 레이어입니다.")
            return False

        try:
            # Create text format
            text_format = QgsTextFormat()

            # Set font
            font = QFont(font_family, font_size)
            text_format.setFont(font)
            text_format.setSize(font_size)
            text_format.setSizeUnit(QgsUnitTypes.RenderPoints)

            # Set buffer
            buffer_settings = QgsTextBufferSettings()
            buffer_settings.setEnabled(True)
            buffer_settings.setSize(buffer_size)
            buffer_settings.setSizeUnit(QgsUnitTypes.RenderMillimeters)
            buffer_settings.setColor(QColor(255, 255, 255))
            text_format.setBuffer(buffer_settings)

            # Create label settings with formatting
            label_settings = QgsPalLayerSettings()
            # Use QGIS expression to format with thousand separators
            label_settings.fieldName = f"format_number(\"{field_name}\", 0)"
            label_settings.isExpression = True
            label_settings.setFormat(text_format)

            # Enable labels
            labeling = QgsVectorLayerSimpleLabeling(label_settings)
            layer.setLabeling(labeling)
            layer.setLabelsEnabled(True)
            layer.triggerRepaint()

            return True

        except Exception as e:
            self.error_occurred.emit(f"라벨 적용 실패: {str(e)}")
            return False

    def create_legend_labels(self, layer, field_name, format_string="{:.0f}"):
        """Create formatted legend labels for the current renderer.

        :param layer: QgsVectorLayer
        :param field_name: Field name being classified
        :param format_string: Format string for numbers
        :returns: True if successful
        :rtype: bool
        """
        if not layer or not layer.isValid():
            return False

        renderer = layer.renderer()
        if not isinstance(renderer, QgsGraduatedSymbolRenderer):
            return False

        try:
            ranges = renderer.ranges()
            for i, range_item in enumerate(ranges):
                lower = range_item.lowerValue()
                upper = range_item.upperValue()
                label = f"{format_string.format(lower)} - {format_string.format(upper)}"
                renderer.updateRangeLabel(i, label)

            layer.triggerRepaint()
            return True

        except Exception as e:
            self.error_occurred.emit(f"범례 생성 실패: {str(e)}")
            return False

    def reset_style(self, layer):
        """Reset layer to default single symbol style.

        :param layer: QgsVectorLayer
        :returns: True if successful
        :rtype: bool
        """
        if not layer or not layer.isValid():
            return False

        try:
            symbol = QgsFillSymbol.createSimple({
                "color": "180,180,180,255",
                "outline_color": "0,0,0,255",
                "outline_width": "0.26",
            })
            layer.renderer().setSymbol(symbol)
            layer.triggerRepaint()
            return True

        except Exception as e:
            self.error_occurred.emit(f"스타일 초기화 실패: {str(e)}")
            return False
