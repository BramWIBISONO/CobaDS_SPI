"""Embedded PostgreSQL for development and tests (pip package pgserver: no installer, no admin rights).
    .venv/Scripts/python scripts/devdb.py start   start or reuse the server, create database spi_web, write DATABASE_URL to .env
    .venv/Scripts/python scripts/devdb.py stop
Data directory: .devdb/ (git-ignored). Its Windows short (8.3) path is used because PostgreSQL tools dislike spaces in paths.
The database is created with psycopg: pgserver's psql() runs an unquoted shell command that breaks when the venv path has spaces.
pgserver's Windows build ships without PostgreSQL's time zone database, which Django needs (SET TIME ZONE 'UTC' on every
connection); the IANA files of the tzdata package (installed with Django on Windows) are copied into it once."""
import ctypes
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

import pgserver
import psycopg
import tzdata

ROOT = Path(__file__).resolve().parent.parent
PGDATA = ROOT / ".devdb"
ENV = ROOT / ".env"
DB = "spi_web"


def short_path(path):
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        return str(path)
    buf = ctypes.create_unicode_buffer(1024)
    n = ctypes.windll.kernel32.GetShortPathNameW(str(path), buf, 1024)
    return buf.value if n else str(path)


def ensure_timezone_data():
    target = Path(pgserver.__file__).resolve().parent / "pginstall" / "share" / "postgresql" / "timezone"
    if not (target / "UTC").exists():
        shutil.copytree(Path(tzdata.__file__).resolve().parent / "zoneinfo", target, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__init__.py", "__pycache__"))


def django_url(uri):
    """pgserver URI -> postgres://user@host:port/db (a socket directory becomes a percent-encoded host)"""
    u = urlparse(uri)
    host = u.hostname or parse_qs(u.query).get("host", [""])[0]
    if "/" in host or "\\" in host:
        host = quote(host, safe="")
    port = f":{u.port}" if u.port else ""
    return f"postgres://{u.username or 'postgres'}@{host}{port}{u.path}"


def write_env(url):
    text = ENV.read_text(encoding="utf-8") if ENV.exists() else ""
    line = f"DATABASE_URL={url}"
    if re.search(r"(?m)^DATABASE_URL=", text):
        text = re.sub(r"(?m)^DATABASE_URL=.*$", line, text)
    else:
        text = (text.rstrip("\n") + "\n" + line + "\n").lstrip("\n")
    ENV.write_text(text, encoding="utf-8")


def main(cmd):
    ensure_timezone_data()
    try:
        srv = pgserver.get_server(short_path(PGDATA), cleanup_mode="stop" if cmd == "stop" else None)
    except subprocess.TimeoutExpired:
        sys.exit("PostgreSQL masih memulihkan data (komputer mati tanpa 'devdb.py stop'). Tunggu +-1 menit, lalu jalankan lagi.")
    if cmd == "stop":
        srv.cleanup()
        print("PostgreSQL berhenti")
        return
    with psycopg.connect(srv.get_uri(), autocommit=True) as conn:
        if conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB,)).fetchone() is None:
            conn.execute(f'CREATE DATABASE "{DB}"')
    url = django_url(srv.get_uri(DB))
    write_env(url)
    print(url)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "start")
