# WMSPlanViewer QGIS Plugin

WMS 기반 행정구역 도시계획 조회 플러그인

## 디렉토리 구조

```
WMSPlanViewer/
├── __init__.py           # 플러그인 진입점
├── metadata.txt          # QGIS 플러그인 메타데이터
├── plugin.py            # 메인 플러그인 클래스
├── resources.qrc        # Qt 리소스 파일
├── core/                # 핵심 비즈니스 로직
│   └── __init__.py
├── ui/                  # 사용자 인터페이스
│   └── __init__.py
└── data/                # 데이터 파일
    └── admin_regions.csv
```

## 설치 방법

1. WMSPlanViewer 폴더를 QGIS 플러그인 디렉토리에 복사
   - Windows: `%APPDATA%/QGIS/QGIS3/profiles/default/python/plugins/`
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - Mac: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`

2. QGIS를 재시작하거나 플러그인 관리자에서 플러그인 새로고침

3. 플러그인 관리자에서 "WMSPlanViewer" 활성화

## 사용 방법

1. QGIS 툴바에서 "WMS 도시계획 조회" 버튼 클릭
2. 행정구역 선택 후 도시계획 정보 조회

## 버전 정보

- Version: 1.0.0
- QGIS 최소 버전: 3.34
