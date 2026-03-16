# WMSPlanViewer Main Dialog

Refined brutalist UI for the WMS Plan Viewer QGIS plugin.

## Features

### 3-Level Cascading Region Selection
- **시도** (Province) → **시군구** (City/County) → **읍면동** (Town/District)
- Automatic hierarchical loading from CSV data
- Smart enable/disable of dependent dropdowns

### Workflow Buttons
Sequential workflow with clear visual hierarchy:
1. **행정구역 로드** - Load administrative boundary (Area A)
2. **박스 그리기** - Draw bounding box on map
3. **주변 영역 로드** - Load surrounding areas (Area B)
4. **완료** - Finalize and complete workflow

### Action Buttons
- **PDF 내보내기** - Export current view to PDF
- **프로젝트 저장** - Save QGIS project

### GeoServer Connection
- Dropdown selector for QGIS WMS connections
- Ready for integration with QGIS connection manager

### Status Bar
- Dynamic status messages with color-coded levels
- `info`, `success`, `warning`, `error` states

## Design Aesthetic

**Direction**: Refined Brutalist
- Dark navy header with bold white typography
- Clean geometric forms with 8px border radius
- Strategic use of electric blue (#2D5BFF) as accent color
- Generous padding and intentional spacing
- Strong typographic hierarchy with uppercase section labels
- Hover states that transform entire button appearance

## Usage

```python
from WMSPlanViewer.ui import WMSPlanDialog

# Create dialog
dialog = WMSPlanDialog(controller=my_controller)

# Connect signals
dialog.load_area_a_clicked.connect(on_load_area_a)
dialog.draw_box_clicked.connect(on_draw_box)
dialog.region_changed.connect(on_region_changed)

# Show dialog
dialog.show()

# Update status
dialog.set_status("Processing...", "info")
dialog.set_status("Complete!", "success")
```

## Signals

- `load_area_a_clicked()` - User clicked "행정구역 로드"
- `draw_box_clicked()` - User clicked "박스 그리기"
- `load_area_b_clicked()` - User clicked "주변 영역 로드"
- `finalize_clicked()` - User clicked "완료"
- `export_pdf_clicked()` - User clicked "PDF 내보내기"
- `save_project_clicked()` - User clicked "프로젝트 저장"
- `region_changed(str, str)` - Region selection changed (type, code)

## Methods

### `get_selected_region() -> Tuple[Optional[str], Optional[str]]`
Returns the most specific selected region as `(region_type, region_code)`.

Region types: `'sido'`, `'sigungu'`, `'emd'`

### `set_status(message: str, level: str = "info")`
Update status bar with colored message.

Levels: `'info'`, `'success'`, `'warning'`, `'error'`

## CSV Data Format

`admin_regions.csv` must contain:
- `adm_cd` - Administrative code
- `adm_nm` - Administrative name

Code lengths determine level:
- 2 digits = 시도
- 5 digits = 시군구
- 8 digits = 읍면동

## Testing

Run standalone test:
```bash
cd D:\DATA\연구원 연도별 업무사항\06_2026년 개발 자료\00_QGIS\00_플러그인\01_2_WMS(Back)
python test_dialog.py
```
