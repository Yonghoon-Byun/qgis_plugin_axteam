# -*- coding: utf-8 -*-
"""
DB 접속 설정 (.env 기반)
개발 시 프로젝트 루트의 .env에서 읽고, 배포(zip) 시 pack_plugin.py가 하드코딩 버전으로 교체합니다.
"""
# === DB_ENV_START ===
import os
from pathlib import Path

def _load_env():
    env = {}
    for candidate in [
        Path(__file__).resolve().parents[2] / ".env",
        Path.home() / ".qgis_axteam.env",
    ]:
        if candidate.exists():
            with open(candidate, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        env[k.strip()] = v.strip()
            break
    return env

_env = _load_env()
def _get(key, default=""):
    return os.environ.get(key) or _env.get(key) or default

DB_HOST = _get("DB_HOST")
DB_PORT = _get("DB_PORT", "6432")
DB_NAME = _get("DB_NAME")
DB_SCHEMA = _get("DB_SCHEMA", "public")
DB_USER = _get("DB_USER")
DB_PASSWORD = _get("DB_PASSWORD")
DB_GEOM_COLUMN = _get("DB_GEOM_COLUMN", "geom")
DB_PK_COLUMN = _get("DB_PK_COLUMN", "ufid")
# === DB_ENV_END ===
