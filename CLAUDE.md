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

**DB를 사용하는 플러그인 (3개):**
- `gis_layer_loader` — `db_env.py` → `region_selector_dialog.py`에서 import
- `gis_stats` — `db_env.py` → `core/db_connection.py`에서 import
- `reservoir_site_analyzer` — `db_env.py` → `reservoir_site_analyzer.py`에서 import

**절대 하지 말 것:**
- src/ 코드에 DB 호스트, 계정, 비밀번호를 직접 작성
- `.env` 파일을 git에 커밋 (`.gitignore`로 제외됨)

## [최우선 규칙] DB 불변 원칙

> **DB(PostgreSQL/PostGIS)의 테이블, 함수, 스키마는 절대 수정하지 않는다.**

- DB 함수에서 에러가 발생하면 → **플러그인 코드에서 우회 처리**
- 예: DB 함수가 GeometryCollection 반환 → 플러그인에서 원본 테이블 직접 공간 쿼리
- 예: DB 함수에 PK가 없음 → 플러그인 URI에서 rid 지정 또는 자동 감지
- DB에 ALTER, CREATE, DROP 등 DDL 실행 금지
- 모든 데이터 처리/변환은 플러그인(Python/QGIS API) 레벨에서 수행

---

## 프로젝트 개요
도화엔지니어링 수자원환경연구소의 QGIS 플러그인 5종을 관리하는 모노레포.
각 플러그인은 `src/` 디렉토리에서 소스를 수정하고, `plugins/`에 zip으로 패키징하여 배포한다.

## 디렉토리 구조
```
qgis_plugin_axteam/
├── CLAUDE.md          # 이 파일
├── .gitignore
├── .env               # DB 접속 정보 (git 추적 제외)
├── .env.example       # .env 템플릿 (git 추적)
├── plugins/           # 배포용 zip 파일 (git 추적 제외)
├── src/               # 소스코드 작업 디렉토리 (git 추적)
│   ├── shared/        # 플러그인 공통 모듈
│   │   └── db_config.py   # .env 기반 DB 설정 로더
│   ├── BasePlan_opt/
│   ├── gis_layer_loader/
│   ├── gis_stats/
│   ├── gis_toolbox/
│   ├── reservoir_site_analyzer/
│   └── civil_planner/    # 토목 관로 설계 위자드 (신규)
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
| **civil_planner** | 1.0.0 | 토목 관로 설계 6단계 위자드 (CRS→범위→데이터→스타일→지장물→관로) |

## 공통 기술 스택
- Python 3.12+ (QGIS 내장)
- PyQt5 (qgis.PyQt)
- QGIS API (qgis.core, qgis.gui)
- PostgreSQL/PostGIS (Azure 호스팅)
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
- **BasePlan_opt**: zip 내에 래핑 폴더 없이 파일이 직접 들어감
- **나머지 4개**: zip 내에 동일 이름의 폴더로 래핑됨 (예: `gis_stats/gis_stats_viewer.py`)
- `__pycache__/`, `*.pyc` 파일은 zip에 포함하지 않음

### DB 접속 정보 (.env 관리)
- DB 접속 정보는 프로젝트 루트의 `.env` 파일로 관리 (git 추적 제외)
- `.env.example`을 복사하여 `.env`를 생성하고 실제 값 입력
- 공통 로더: `src/shared/db_config.py`의 `get_db_config()` 사용

```python
from shared.db_config import get_db_config
config = get_db_config()
# config["host"], config["port"], config["database"],
# config["schema"], config["user"], config["password"],
# config["geom_column"], config["pk_column"]
```

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

**DB를 사용하는 플러그인 (하드코딩 → .env 전환 대상):**
- `gis_layer_loader` — `region_selector_dialog.py:617`
- `gis_stats` — `core/db_connection.py:19`
- `reservoir_site_analyzer` — `reservoir_site_analyzer.py:36`

> 주의: 현재 각 플러그인에 DB 정보가 하드코딩되어 있음. 수정 시 `shared/db_config.py`를 import하도록 전환 필요.

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
- DB 접속 정보를 소스코드에 하드코딩하지 말 것 → `.env` + `shared/db_config.py` 사용
