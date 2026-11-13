"""Shared helpers: configuration loading and database connection."""
import json
import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def load_config(path=None):
    """Load config.json. Relative paths are resolved against the config file's folder,
    so every script works no matter where it is started from (e.g. Task Scheduler)."""
    path = Path(path or os.environ.get("GN_CONFIG") or BASE_DIR / "config.json").resolve()
    cfg = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent

    def fix(p):
        p = Path(p)
        return p if p.is_absolute() else base / p

    if cfg["database"]["type"] == "sqlite":
        cfg["database"]["path"] = fix(cfg["database"]["path"])
    b = cfg.setdefault("backup", {})
    b["dir"] = fix(b.get("dir", "backups"))
    b["secondary_dirs"] = [fix(p) for p in b.get("secondary_dirs", [])]
    b["key_file"] = fix(b.get("key_file", "backup.key"))
    b["log_file"] = fix(b.get("log_file", "logs/backup_system.log"))
    b.setdefault("retention_days", 30)
    b.setdefault("min_keep", 3)
    b.setdefault("compress", True)
    b.setdefault("encrypt", False)
    cfg.setdefault("alerts", {"on": "failure"})
    a = cfg.setdefault("app", {})
    a["secret_key_file"] = fix(a.get("secret_key_file", "instance/secret.key"))
    a.setdefault("session_hours", 8)
    cfg.setdefault("company", {"name": "Company", "address": "", "phone": "", "email": "", "gstin": "", "state": ""})
    cfg.setdefault("forecast", {})
    cfg["reports_dir"] = fix(cfg.get("reports_dir", "reports"))
    return cfg


def get_conn(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def fy_label(dt):
    """Indian financial year label, e.g. 2026-04-10 -> '2026-27', 2027-02-01 -> '2026-27'."""
    y = dt.year if dt.month >= 4 else dt.year - 1
    return f"{y}-{(y + 1) % 100:02d}"


def money(x):
    """Round to 2 decimals the way invoices expect (half-up on the float's decimal value)."""
    return round(x + 1e-9, 2)
