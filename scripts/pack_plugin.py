# -*- coding: utf-8 -*-
"""
플러그인 패키징 스크립트
src/ 의 플러그인 소스를 plugins/ 디렉토리에 zip으로 패키징합니다.
패키징 시 db_env.py는 .env의 실제 값이 하드코딩된 버전으로 교체됩니다.

사용법:
    python scripts/pack_plugin.py <plugin_name>    # 특정 플러그인만
    python scripts/pack_plugin.py --all             # 전체 플러그인
"""

import os
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
PLUGINS_DIR = REPO_ROOT / "plugins"
ENV_FILE = REPO_ROOT / ".env"

# 플러그인별 zip 내 최상위 폴더 이름 매핑
# BasePlan_opt는 zip 내에 폴더 없이 파일이 직접 들어감
PLUGIN_ZIP_CONFIG = {
    "BasePlan_opt": {"zip_name": "BasePlan_opt.zip", "wrap_folder": "BasePlan_opt"},
    "gis_layer_loader": {"zip_name": "gis_layer_loader.zip", "wrap_folder": "gis_layer_loader"},
    "gis_stats": {"zip_name": "gis_stats.zip", "wrap_folder": "gis_stats"},
    "gis_toolbox": {"zip_name": "gis_toolbox.zip", "wrap_folder": "gis_toolbox"},
    "reservoir_site_analyzer": {"zip_name": "reservoir_site_analyzer.zip", "wrap_folder": "reservoir_site_analyzer"},
    "civil_planner": {"zip_name": "civil_planner.zip", "wrap_folder": "civil_planner"},
}

# 플러그인별 db_env.py 의 기본값 오버라이드 (geom_column, pk_column 등 플러그인마다 다른 값)
DB_ENV_OVERRIDES = {
    "gis_layer_loader": {
        "DB_RASTER_COLUMN": "clipped_rast",
    },
    "gis_stats": {
        "DB_GEOM_COLUMN": "geometry",
        "DB_PK_COLUMN": "adm_cd",
    },
    "reservoir_site_analyzer": {},
    "civil_planner": {},
}

EXCLUDE_PATTERNS = {"__pycache__", ".pyc", ".pyo", ".git", ".DS_Store", "Thumbs.db"}


def parse_env_file():
    """프로젝트 루트의 .env 파일을 파싱합니다."""
    env = {}
    if not ENV_FILE.exists():
        print(f"[WARN] .env 파일이 없습니다: {ENV_FILE}")
        print("  .env.example을 복사하여 .env를 생성하세요.")
        return env

    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def generate_hardcoded_db_env(plugin_name: str, env: dict) -> str:
    """플러그인용 하드코딩 db_env.py 내용을 생성합니다."""
    overrides = DB_ENV_OVERRIDES.get(plugin_name, {})

    def val(key, default=""):
        # 오버라이드 > .env > 기본값
        if key in overrides:
            return overrides[key]
        return env.get(key, default)

    lines = [
        '# -*- coding: utf-8 -*-',
        '"""',
        'DB 접속 설정 (하드코딩 - pack_plugin.py에 의해 자동 생성)',
        '"""',
        f'DB_HOST = "{val("DB_HOST")}"',
        f'DB_PORT = "{val("DB_PORT", "6432")}"',
        f'DB_NAME = "{val("DB_NAME")}"',
        f'DB_SCHEMA = "{val("DB_SCHEMA", "public")}"',
        f'DB_USER = "{val("DB_USER")}"',
        f'DB_PASSWORD = "{val("DB_PASSWORD")}"',
        f'DB_GEOM_COLUMN = "{val("DB_GEOM_COLUMN", "geom")}"',
        f'DB_PK_COLUMN = "{val("DB_PK_COLUMN", "ufid")}"',
    ]

    # gis_layer_loader는 DB_RASTER_COLUMN도 필요
    if plugin_name == "gis_layer_loader":
        lines.append(f'DB_RASTER_COLUMN = "{val("DB_RASTER_COLUMN", "clipped_rast")}"')

    return "\n".join(lines) + "\n"


def should_exclude(path: str) -> bool:
    parts = Path(path).parts
    for part in parts:
        if part in EXCLUDE_PATTERNS or any(part.endswith(ext) for ext in [".pyc", ".pyo"]):
            return True
    return False


def pack_plugin(plugin_name: str, env: dict):
    if plugin_name not in PLUGIN_ZIP_CONFIG:
        print(f"[ERROR] Unknown plugin: {plugin_name}")
        print(f"  Available: {', '.join(PLUGIN_ZIP_CONFIG.keys())}")
        return False

    config = PLUGIN_ZIP_CONFIG[plugin_name]
    src_path = SRC_DIR / plugin_name
    zip_path = PLUGINS_DIR / config["zip_name"]
    wrap = config["wrap_folder"]

    if not src_path.exists():
        print(f"[ERROR] Source not found: {src_path}")
        return False

    # db_env.py 교체 대상인지 확인
    has_db_env = plugin_name in DB_ENV_OVERRIDES
    hardcoded_db_env = generate_hardcoded_db_env(plugin_name, env) if has_db_env else None

    PLUGINS_DIR.mkdir(exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_PATTERNS]

            for file in files:
                filepath = Path(root) / file
                if should_exclude(str(filepath)):
                    continue

                rel_path = filepath.relative_to(src_path)
                if wrap:
                    arcname = f"{wrap}/{rel_path}"
                else:
                    arcname = str(rel_path)

                # db_env.py → 하드코딩 버전으로 교체
                if file == "db_env.py" and has_db_env:
                    zf.writestr(arcname, hardcoded_db_env)
                    print(f"  [DB] db_env.py -> 하드코딩 버전으로 교체")
                else:
                    zf.write(filepath, arcname)

    print(f"[OK] {plugin_name} -> plugins/{config['zip_name']}")
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    env = parse_env_file()

    if sys.argv[1] == "--all":
        results = [pack_plugin(name, env) for name in PLUGIN_ZIP_CONFIG]
        sys.exit(0 if all(results) else 1)
    else:
        plugin_name = sys.argv[1]
        sys.exit(0 if pack_plugin(plugin_name, env) else 1)


if __name__ == "__main__":
    main()
