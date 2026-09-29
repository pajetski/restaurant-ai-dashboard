"""File-backed persistence: state, audit log, vendor history, upload queue."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from .manager import RestaurantManager

VENDOR_HISTORY_COLUMNS = ["time", "vendor", "item", "price"]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class Store:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_path = self.data_dir / "data.json"
        self.audit_path = self.data_dir / "audit_log.jsonl"
        self.vendor_history_path = self.data_dir / "vendor_price_history.csv"
        self.upload_dir = self.data_dir / "uploads"
        self.upload_queue_path = self.data_dir / "upload_queue.jsonl"

    # --- state ---
    def load(self) -> RestaurantManager:
        if self.data_path.exists():
            return RestaurantManager.from_dict(json.loads(self.data_path.read_text(encoding="utf-8")))
        return RestaurantManager.sample()

    def save(self, m: RestaurantManager) -> None:
        """Atomic write so a crash mid-save can't corrupt data.json."""
        fd, tmp = tempfile.mkstemp(dir=self.data_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(m.to_dict(), f, indent=2)
            os.replace(tmp, self.data_path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        self.log("save_data", {"path": str(self.data_path)})

    def reset(self) -> RestaurantManager:
        self.data_path.unlink(missing_ok=True)
        self.log("reset_sample", {})
        return self.load()

    # --- audit ---
    def log(self, action: str, payload: Dict[str, Any]) -> None:
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"time": now_iso(), "action": action, "payload": payload}) + "\n")

    def load_audit(self, limit: int = 200) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        if self.audit_path.exists():
            for line in self.audit_path.read_text(encoding="utf-8").splitlines():
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
        if not rows:
            return pd.DataFrame(columns=["time", "action", "payload"])
        return pd.DataFrame(rows).sort_values("time", ascending=False).head(limit)

    # --- vendor history ---
    def append_vendor_history(self, vendor: str, item: str, price: float) -> None:
        new = not self.vendor_history_path.exists()
        with self.vendor_history_path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(VENDOR_HISTORY_COLUMNS)
            w.writerow([now_iso(), vendor, item, f"{price:.4f}"])

    def load_vendor_history(self) -> pd.DataFrame:
        if not self.vendor_history_path.exists():
            return pd.DataFrame(columns=VENDOR_HISTORY_COLUMNS)
        try:
            return pd.read_csv(self.vendor_history_path)
        except (pd.errors.ParserError, pd.errors.EmptyDataError):
            return pd.DataFrame(columns=VENDOR_HISTORY_COLUMNS)

    # --- uploads ---
    def save_upload(self, filename: str, content: bytes, label: str) -> Path:
        self.upload_dir.mkdir(exist_ok=True)
        digest = sha256_bytes(content)
        safe_name = Path(filename).name  # strip any client-supplied path components
        path = self.upload_dir / f"{digest[:16]}_{safe_name}"
        path.write_bytes(content)
        with self.upload_queue_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "time": now_iso(), "filename": safe_name, "stored_as": str(path),
                "sha256": digest, "size_bytes": len(content), "label": label,
            }) + "\n")
        return path

    # --- export ---
    def export_zip(self, m: RestaurantManager) -> bytes:
        def read(p: Path, default: str = "") -> str:
            return p.read_text(encoding="utf-8") if p.exists() else default

        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("data.json", json.dumps(m.to_dict(), indent=2))
            z.writestr("audit_log.jsonl", read(self.audit_path))
            z.writestr("vendor_price_history.csv", read(self.vendor_history_path, ",".join(VENDOR_HISTORY_COLUMNS) + "\n"))
            out = io.StringIO()
            w = csv.writer(out)
            w.writerow(["time", "platform", "item", "qty"])
            for o in m.orders:
                w.writerow([o.get("time"), o.get("platform"), o.get("item"), o.get("qty")])
            z.writestr("orders.csv", out.getvalue())
            z.writestr("upload_queue.jsonl", read(self.upload_queue_path))
        return mem.getvalue()
