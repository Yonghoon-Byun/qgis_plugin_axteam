# -*- coding: utf-8 -*-
"""
플러그인 배포(설치) 스크립트
src/ 의 플러그인을 QGIS 플러그인 디렉토리에 직접 복사합니다.
개발 중 빠른 테스트를 위해 사용합니다.

사용법:
    python scripts/deploy_plugin.py <plugin_name>    # 특정 플러그인 배포
    python scripts/deploy_plugin.py --all             # 전체 배포
    python scripts/deploy_plugin.py --list            # QGIS 플러그인 경로 확인
"""

import os
import sys
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"

# QGIS 플러그인 디렉토리 (Windows 기준)
QGIS_PLUGIN_DIR = Path(os.environ.get("APPDATA", "")) / "QGIS" / "QGIS3" / "profiles" / "default" / "python" / "plugins"

PLUGIN_NAMES = [
    "BasePlan_opt",
    "gis_layer_loader",
    "gis_stats",
    "gis_toolbox",
    "reservoir_site_analyzer",
    "civil_planner",
]

EXCLUDE = {"__pycache__", ".pyc", ".pyo"}


def deploy_plugin(plugin_name: str):
    if plugin_name not in PLUGIN_NAMES:
        print(f"[ERROR] Unknown plugin: {plugin_name}")
        return False

    src = SRC_DIR / plugin_name
    dest = QGIS_PLUGIN_DIR / plugin_name

    if not src.exists():
        print(f"[ERROR] Source not found: {src}")
        return False

    if not QGIS_PLUGIN_DIR.exists():
        print(f"[ERROR] QGIS plugin directory not found: {QGIS_PLUGIN_DIR}")
        print("  QGIS가 설치되어 있는지 확인하세요.")
        return False

    # Remove existing
    if dest.exists():
        shutil.rmtree(dest)

    # Copy with exclusions
    shutil.copytree(
        src, dest,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")
    )

    print(f"[OK] {plugin_name} -> {dest}")
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "--list":
        print(f"QGIS plugin dir: {QGIS_PLUGIN_DIR}")
        print(f"Exists: {QGIS_PLUGIN_DIR.exists()}")
        if QGIS_PLUGIN_DIR.exists():
            for d in sorted(QGIS_PLUGIN_DIR.iterdir()):
                if d.is_dir():
                    print(f"  {d.name}")
        sys.exit(0)

    if sys.argv[1] == "--all":
        results = [deploy_plugin(name) for name in PLUGIN_NAMES]
        sys.exit(0 if all(results) else 1)
    else:
        sys.exit(0 if deploy_plugin(sys.argv[1]) else 1)


if __name__ == "__main__":
    main()
