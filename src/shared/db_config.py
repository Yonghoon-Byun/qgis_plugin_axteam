# -*- coding: utf-8 -*-
"""
공통 DB 설정 로더
.env 파일에서 DB 접속 정보를 읽어옵니다.

사용법:
    from shared.db_config import get_db_config
    config = get_db_config()
    # config["host"], config["port"], config["database"], ...
"""

import os
from pathlib import Path


def _find_env_file():
    """프로젝트 루트의 .env 파일을 찾습니다."""
    # 1) 환경변수로 직접 지정된 경우
    env_path = os.environ.get("AXTEAM_ENV_FILE")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    # 2) 프로젝트 루트 (src/../.env)
    project_root = Path(__file__).resolve().parent.parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        return env_file

    # 3) QGIS 플러그인 폴더에서 실행될 때 (~/.qgis_axteam.env)
    home_env = Path.home() / ".qgis_axteam.env"
    if home_env.exists():
        return home_env

    return None


def _parse_env_file(filepath):
    """간단한 .env 파서 (python-dotenv 없이 동작)"""
    env = {}
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def get_db_config():
    """DB 접속 설정을 반환합니다.

    우선순위:
    1. 환경변수 (DB_HOST, DB_PORT, ...)
    2. .env 파일
    3. 기본값 (하드코딩 fallback)

    Returns:
        dict: DB 접속 정보
    """
    # .env 파일 로드
    env_file = _find_env_file()
    file_env = _parse_env_file(env_file) if env_file else {}

    def get(key, default=""):
        return os.environ.get(key) or file_env.get(key) or default

    return {
        "host": get("DB_HOST", "geo-spatial-hub.postgres.database.azure.com"),
        "port": get("DB_PORT", "6432"),
        "database": get("DB_NAME", "dde-water"),
        "schema": get("DB_SCHEMA", "public"),
        "user": get("DB_USER", ""),
        "password": get("DB_PASSWORD", ""),
        "geom_column": get("DB_GEOM_COLUMN", "geom"),
        "pk_column": get("DB_PK_COLUMN", "ufid"),
    }
