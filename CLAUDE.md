# QGIS Plugin AXTeam - 작업 가이드

## [최우선 규칙] DB 정보 관리 정책

> **src/ 소스코드에는 절대 DB 접속 정보를 하드코딩하지 않는다.**

| 환경 | DB 정보 관리 방식 |
|------|------------------|
| **src/ (개발/레포지토리)** | `.env` 파일에서 읽음 (`db_env.py` → `.env` 로딩) |
| **plugins/*.zip (배포)** | `pack_plugin.py`가 `.env` 값을 하드코딩하여 `db_env.py`를 교체 |

**작업 흐름:**
1. DB 접속 정보 변경 → `.env` 파일만 수정
2. 소스 수정 후 패키징 요청 → `python scripts/pack_plugin.py <plugin>` 실행
3. pack_plugin.py가 자동으로 `.env`를 읽어 zip 내 `db_env.py`에 하드코딩

**DB를 사용하는 플러그인 (4개):**
- `gis_layer_loader` — `db_env.py` → `region_selector_dialog.py`에서 import
- `gis_stats` — `db_env.py` → `core/db_connection.py`에서 import
- `reservoir_site_analyzer` — `db_env.py` → `reservoir_site_analyzer.py`에서 import
- `civil_planner` — `db_env.py` → `core/layer_loader.py`에서 import

**절대 하지 말 것:**
- src/ 코드에 DB 호스트, 계정, 비밀번호를 직접 작성
- `.env` 파일을 git에 커밋 (`.gitignore`로 제외됨)

## [최우선 규칙] 작업 완료 시 zip 패키징 필수

> **플러그인 소스 수정 작업이 끝나면 반드시 zip 패키징까지 완료한다.**

- 소스 수정 후 `python scripts/pack_plugin.py <plugin>` 실행을 기본으로 수행
- 수정된 플러그인만 패키징 (전체가 아님)
- 사용자가 별도로 요청하지 않아도 자동으로 패키징
- 커밋/푸시와 패키징은 세트로 처리

## [최우선 규칙] DB 불변 원칙

> **DB(PostgreSQL/PostGIS)의 테이블, 함수, 스키마는 절대 수정하지 않는다.**

- DB 함수에서 에러가 발생하면 → **플러그인 코드에서 우회 처리**
- 예: `cadastral_filtered` 함수 GeometryCollection 에러 → `lsmd_cont_ldreg` 테이블 직접 공간 쿼리로 우회
- 예: DB 함수에 PK가 없음 → `ROW_NUMBER() OVER() AS _uid`로 순차 PK 생성
- DB에 ALTER, CREATE, DROP 등 DDL 실행 금지
- 모든 데이터 처리/변환은 플러그인(Python/QGIS API) 레벨에서 수행

---

## 프로젝트 개요
도화엔지니어링 수자원환경연구소의 QGIS 플러그인 6종을 관리하는 모노레포.
각 플러그인은 `src/` 디렉토리에서 소스를 수정하고, `plugins/`에 zip으로 패키징하여 배포한다.

## 디렉토리 구조
```
qgis_plugin_axteam/
├── CLAUDE.md          # 이 파일
├── .gitignore
├── .env               # DB 접속 정보 (git 추적 제외)
├── .env.example       # .env 템플릿 (git 추적)
├── plugins/           # 배포용 zip 파일 (git 추적 제외)
├── docs/              # 개발 문서
│   ├── civil_planner_개발계획서.md
│   └── civil_planner_개발계획서.pdf
├── src/               # 소스코드 작업 디렉토리 (git 추적)
│   ├── shared/        # 플러그인 공통 모듈
│   │   └── db_config.py   # .env 기반 DB 설정 로더
│   ├── BasePlan_opt/
│   ├── gis_layer_loader/
│   ├── gis_stats/
│   ├── gis_toolbox/
│   ├── reservoir_site_analyzer/
│   └── civil_planner/    # 토목 관로 설계 7단계 위자드
└── scripts/           # 관리 스크립트
    ├── pack_plugin.py
    └── deploy_plugin.py
```

## 플러그인 목록

| 플러그인 | 버전 | 설명 |
|---------|------|------|
| **BasePlan_opt** | 1.1.0 | 토목 기본계획 배경도 작성 (GeoServer WMS, PostGIS) |
| **gis_layer_loader** | 1.0 | 행정구역 계층선택 + WFS 동적 레이어 로딩 |
| **gis_stats** | 1.0.0 | 행정구역별 통계(인구/가구/주택) 시각화 (Quantile 분류) |
| **gis_toolbox** | 1.0.0 | GIS 유틸리티 모음 (좌표계/인코딩/레이어저장/지오메트리/레이어명) |
| **reservoir_site_analyzer** | 1.0.0 | 저수지(배수지) 후보 부지 분석 (DEM/경사/관리주체) |
| **civil_planner** | 1.0.6 | 토목 관로 설계 7단계 위자드 (UNION ALL 최적화) |

---

## civil_planner 상세

> 상세 개발계획서: `docs/civil_planner_개발계획서.md` 참조

### 7단계 위자드 워크플로우

```
[사전] Vworld 플러그인으로 배경지도 + 위치 이동 (별도 플러그인)
  ↓
1단계: 프로젝트 CRS 설정 (EPSG:5186 권장, OTF로 DB 5179와 호환)
  ↓
2단계: 사업지역 선택 (시도→시군구→읍면동 cascading, 지도 자동 zoom)
  ↓
3단계: 작업 범위 폴리곤 생성 (지도 드래그 or 기존 레이어 선택)
  ↓
4단계: 범위 기반 DB 데이터 로드 + 전처리
  - 범위 좌표 → DB CRS(5179) 변환
  - sgis_hjd 공간 인덱스로 읍면동 코드 자동 감지 (밀리초)
  - UNION ALL 통합 쿼리 (함수당 1회, 약 40배 성능 개선)
  - ROW_NUMBER() _uid로 PK 생성 (중복 방지)
  - BatchPreprocessTask로 순차 클리핑 + 도형수정 (크래시 방지)
  - clip 전 공간 인덱스 생성 (10배 속도 개선)
  - 스타일 자동 적용 (00_상하수도 태그)
  ↓
5단계: 레이어 그룹화 + 스타일 정리 + 배경 투명도
  ↓
6단계: 지장물 파일/폴더 일괄 로드 (하위 디렉토리별 서브그룹 자동 생성)
  ↓
7단계: 관로 LineString 레이어 생성 + 편집 모드 + 스냅 설정
```

### 핵심 구조

```
src/civil_planner/
├── plugin.py                    # QGIS 진입점
├── db_env.py                    # .env 기반 DB 설정
├── admin_regions.csv            # 행정구역 코드 (시도/시군구/읍면동)
├── core/
│   ├── layer_loader.py          # DB 레이어 로딩 (UNION ALL, 읍면동 감지)
│   ├── preprocessor.py          # 클리핑 + 도형수정 (BatchPreprocessTask)
│   └── style_manager.py         # XML 스타일 자동 적용
├── ui/
│   ├── wizard_dialog.py         # 7단계 위자드 메인 (자유 이동 + 초기화)
│   ├── step1_setup.py           # Step 1: CRS 설정
│   ├── step2_region.py          # Step 2: 사업지역 선택 (cascading combobox)
│   ├── step2_boundary.py        # Step 3: 범위 설정 (파일명 유지, 실제 Step 3)
│   ├── step3_load_data.py       # Step 4: 데이터 로드
│   ├── step4_organize.py        # Step 5: 정리 및 스타일
│   ├── step5_obstacle.py        # Step 6: 지장물 연동
│   ├── step6_route.py           # Step 7: 관로 설계
│   └── styles.py                # 공통 UI 스타일시트
└── styles/
    └── qgis_layer_style_library.xml  # 상하수도 스타일 23종
```

> **주의**: Step 2 삽입 시 기존 파일명은 유지함 (step2_boundary.py → 실제 Step 3 등)

### DB 레이어 목록 (16개, 전수 검증 완료)

**DB 함수 (13개)** — UNION ALL 통합 쿼리 + `ROW_NUMBER() OVER() AS _uid`:

| 레이어명 | DB 함수 | PK | geom |
|---------|--------|-----|------|
| 건축물정보 | building_info_filter | _uid | geom |
| 단지경계 | complex_outline_clip | _uid | geom |
| 단지시설용지 | complex_facility_site_clip | _uid | geom |
| 단지용도지역 | complex_landuse_clip | _uid | geom |
| 단지유치업종 | complex_industry_clip | _uid | geom |
| 도로경계선 | road_outline_clip | _uid | geom |
| 도로중심선 | road_center_clip | _uid | geom |
| 등고선 | contour_clip | _uid | geom |
| 터널 | tunnel_clip | _uid | geom |
| 토지소유정보 | land_owner_info | _uid | geom |
| 하천경계 | river_boundary_clip | _uid | geom |
| 하천중심선 | river_centerline_clip | _uid | geom |
| 호수 및 저수지 | reservoir_clip | _uid | geom |

**테이블 직접 쿼리 (3개)** — DB 함수 우회:

| 레이어명 | 테이블 | query_type | 이유 |
|---------|--------|------------|------|
| 연속지적도 | lsmd_cont_ldreg | spatial | cadastral_filtered 함수 GeometryCollection 에러 |
| 행정동 경계 | sgis_hjd | table | admin_boundary_by_level 함수 미존재 |
| DEM 90m | korea_dem_90m | raster | 래스터 테이블 |

### 스타일 자동 매칭 (qgis_layer_style_library.xml)

`00_상하수도` 태그 23개 심볼:
- 관로: `관로_계획`, `관로_기존`
- 지장물 8종: `지장물_가스`, `지장물_고압전기`, `지장물_광역상수` 등
- 지형지물 4종: `지형지물_건물`, `지형지물_도로`, `지형지물_지적`, `지형지물_하천`
- 경계 4종: `경계_도로`, `경계_리`, `경계_시군구`, `경계_읍면동`

### 기술적 결정 사항

| 결정 | 내용 | 이유 |
|------|------|------|
| CRS | 프로젝트 5186, DB 5179 (OTF) | DB 변환 리스크 방지 |
| 행정구역 감지 | 읍면동(8자리+) 우선 | 시군구 전체 로드 시 느림 |
| UNION ALL 통합 쿼리 | 읍면동별 개별 호출 → 함수당 1회 통합 | DB 호출 40배 감소, 성능 40배 개선 |
| ROW_NUMBER() _uid | DB 함수 결과에 순차 PK 생성 | rid 중복 시 QGIS 로드 실패 방지 |
| 공간 인덱스 | clip 전 createSpatialIndex() | clip 속도 10배 향상 |
| 전처리 | BatchPreprocessTask (순차) | processing.run() 병렬 실행 시 크래시 |
| DB 함수 호출 | gis_layer_loader와 동일 패턴 | 필터 없이 로드 → 후처리 클리핑 |
| 다이얼로그 | 상태 유지 + 초기화 버튼 | 닫았다 열어도 작업 유지 |
| 단계 이동 | 자유 이동 (잠금 없음) | 사용자 편의 |
| 지장물 폴더 로드 | os.walk() 재귀 탐색, 디렉토리→그룹 | 82개 파일 일괄 처리, 2초 내 완료 |

---

## DB 좌표계 현황 (EPSG:5179)

> **현재 DB 전체가 EPSG:5179로 저장**되어 있으며, 프로젝트 CRS(5186)와는 QGIS OTF로 자동 변환한다.
> 5179 ↔ 5186은 동일 datum(Korea 2000)이므로 변환 오차 없음 (부동소수점 정밀도 수준).

### DB SRID 분포

| SRID | 테이블 수 | 비고 |
|------|----------|------|
| 5179 | ~40개+ | sgis_hjd, lsmd_cont_ldreg, contour, n3a_*, mv_hjd_*, mv_road_37~39 등 |
| 0 (미설정) | ~25개 | mv_contour_11~36, mv_road_11~36 등 (원본 좌표계 확인 필요) |
| 5186 | 2개 | land_cover_yangju, soil |

### DB 함수 내 5179 하드코딩

모든 DB 함수(14개)의 결과 geometry에 `::geometry(MultiPolygon, 5179)` 형태로 SRID가 캐스팅되어 있음.
→ DB를 5186으로 변환하려면 함수 소스도 수정 필요.

### 플러그인별 5179 참조 현황

| 플러그인 | 5179 참조 위치 | 변환 시 수정 범위 |
|---------|---------------|-----------------|
| **civil_planner** | `DB_SRID = 5179`, transform_extent_to_db() | DB_SRID 변경 + transform 코드 정리 |
| **gis_layer_loader** | 없음 (DB 함수 결과를 OTF로 사용) | 영향 적음 |
| **gis_stats** | 없음 | 영향 없음 |
| **reservoir_site_analyzer** | `ST_MakeEnvelope(..., 5179)` 1곳, `crs=EPSG:5179` 2곳 | 하드코딩 3곳 수정 |
| **BasePlan_opt** | 프로젝트 CRS, WMS srsname, export bbox 등 **10곳+** | 전면 수정 (가장 큰 작업) |

### 5186 변환 판단 (미결정)

- **장점**: 프로젝트 CRS와 DB CRS 통일, transform 코드 제거 가능
- **단점**: DB 함수 14개 + 테이블 ~40개 수정, BasePlan_opt 전면 수정 필요
- **현행 유지 사유**: OTF 변환으로 실사용 문제 없음, 변환 리스크 대비 이점이 크지 않음

---

## 공통 기술 스택
- Python 3.12+ (QGIS 3.40 내장)
- PyQt5 (qgis.PyQt)
- QGIS API (qgis.core, qgis.gui)
- PostgreSQL/PostGIS (Azure: geo-spatial-hub.postgres.database.azure.com:6432/dde-water)
- GeoServer WMS/WFS

## 주요 명령어

### 플러그인 패키징 (src → zip)
```bash
python scripts/pack_plugin.py BasePlan_opt          # 특정 플러그인
python scripts/pack_plugin.py --all                  # 전체
```

### 개발용 배포 (src → QGIS 플러그인 폴더)
```bash
python scripts/deploy_plugin.py gis_stats            # 특정 플러그인
python scripts/deploy_plugin.py --all                 # 전체
python scripts/deploy_plugin.py --list                # QGIS 경로 확인
```

## 코딩 컨벤션

### 파일 인코딩
- 모든 Python 파일은 UTF-8
- `# -*- coding: utf-8 -*-` 헤더 사용

### QGIS 플러그인 구조 규칙
- 진입점: `__init__.py`의 `classFactory(iface)` 함수
- `metadata.txt`는 QGIS 플러그인 매니저가 읽는 메타데이터 (필수)
- UI 코드는 `ui/` 서브패키지에 분리
- 비즈니스 로직은 `core/` 서브패키지에 분리

### zip 패키징 주의사항
- **모든 플러그인**: zip 내에 동일 이름의 루트 폴더로 래핑 (QGIS zip 설치 규격)
- `__pycache__/`, `*.pyc` 파일은 zip에 포함하지 않음
- `pack_plugin.py` 패키징 시 `db_env.py`가 `.env` 값으로 자동 교체

### DB 접속 정보 (.env 관리)
- DB 접속 정보는 프로젝트 루트의 `.env` 파일로 관리 (git 추적 제외)
- `.env.example`을 복사하여 `.env`를 생성하고 실제 값 입력
- 각 플러그인의 `db_env.py`가 `.env`를 자동 로딩

**.env 변수 목록:**
| 변수 | 설명 | 기본값 |
|------|------|--------|
| `DB_HOST` | PostgreSQL 호스트 | geo-spatial-hub.postgres.database.azure.com |
| `DB_PORT` | 포트 | 6432 |
| `DB_NAME` | 데이터베이스명 | dde-water |
| `DB_SCHEMA` | 스키마 | public |
| `DB_USER` | 사용자명 | (없음) |
| `DB_PASSWORD` | 비밀번호 | (없음) |
| `DB_GEOM_COLUMN` | 기본 geometry 컬럼 | geom |
| `DB_PK_COLUMN` | 기본 PK 컬럼 | ufid |

### processing.run() 사용 주의사항
- **절대 병렬 실행 금지** — QGIS processing.run()은 동시 실행 시 access violation 크래시
- 반드시 `BatchPreprocessTask`처럼 **단일 QgsTask에서 순차 처리**
- 메인 스레드에서 직접 호출 시 UI 프리징 → QgsTask로 백그라운드 실행

## 작업 워크플로우
1. `src/<plugin_name>/` 에서 코드 수정
2. QGIS에서 테스트: `python scripts/deploy_plugin.py <plugin_name>`
3. 배포: `python scripts/pack_plugin.py <plugin_name>`
4. git commit & push

## 주의사항
- `plugins/*.zip` 파일은 `.gitignore`로 git 추적에서 제외됨
- `.env` 파일은 `.gitignore`로 git 추적에서 제외됨 (민감 정보 보호)
- `.env.example`은 git에 포함됨 (신규 개발자 가이드용)
- 소스 코드(`src/`)만 git으로 관리
- QGIS 재시작 또는 Plugin Reloader 플러그인으로 변경사항 반영
- DB 접속 정보를 소스코드에 하드코딩하지 말 것 → `.env` + `db_env.py` 사용
- DB 테이블/함수 수정 금지 → 플러그인 코드에서 우회 처리
