"""Local storage for German Personal Tutor.

LocalStore speaks the small part of the Supabase client API the app uses
(table().select().eq().order().limit().execute(), insert, upsert, delete),
but keeps every table as a JSON file on this computer:

    data/<table>.json      e.g. data/exercise_attempts.json

So the app runs exactly the same in local mode and in cloud (Supabase) mode.
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()


class _Result:
    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data
        self.count = len(data)


class LocalStore:
    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    def table(self, name: str) -> "_Query":
        return _Query(self, name)

    # ---- files ----
    def _path(self, name: str) -> Path:
        return self.folder / f"{name}.json"

    def read(self, name: str) -> Dict[str, Any]:
        try:
            data = json.loads(self._path(name).read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("rows"), list):
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return {"next_id": 1, "rows": []}

    def write(self, name: str, data: Dict[str, Any]) -> None:
        path = self._path(name)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        os.replace(tmp, path)


class _Query:
    def __init__(self, store: LocalStore, name: str):
        self.store, self.name = store, name
        self.op = "select"
        self.columns: Optional[List[str]] = None
        self.filters: List[tuple] = []
        self.order_by: Optional[tuple] = None
        self.max_rows: Optional[int] = None
        self.payload: Any = None
        self.conflict = "id"

    # ---- builders (same names as the Supabase client) ----
    def select(self, columns: str = "*", **_):
        self.op = "select"
        cols = [c.strip() for c in columns.split(",") if c.strip()]
        self.columns = None if cols in ([], ["*"]) else cols
        return self

    def eq(self, column: str, value: Any):
        self.filters.append((column, value))
        return self

    def order(self, column: str, desc: bool = False, **_):
        self.order_by = (column, desc)
        return self

    def limit(self, n: int, **_):
        self.max_rows = int(n)
        return self

    def insert(self, rows: Any, **_):
        self.op, self.payload = "insert", rows
        return self

    def upsert(self, rows: Any, on_conflict: str = "id", **_):
        self.op, self.payload, self.conflict = "upsert", rows, on_conflict
        return self

    def update(self, values: Dict[str, Any], **_):
        self.op, self.payload = "update", values
        return self

    def delete(self, **_):
        self.op = "delete"
        return self

    # ---- run ----
    def _match(self, row: Dict[str, Any]) -> bool:
        return all(row.get(c) == v for c, v in self.filters)

    def execute(self) -> _Result:
        with _LOCK:
            table = self.store.read(self.name)
            rows = table["rows"]

            if self.op == "select":
                out = [r for r in rows if self._match(r)]
                if self.order_by:
                    col, desc = self.order_by
                    out.sort(key=lambda r: (r.get(col) is None, r.get(col) if r.get(col) is not None else ""),
                             reverse=desc)
                if self.max_rows is not None:
                    out = out[: self.max_rows]
                if self.columns:
                    out = [{c: r.get(c) for c in self.columns} for r in out]
                return _Result([dict(r) for r in out])

            changed: List[Dict[str, Any]] = []
            if self.op in ("insert", "upsert"):
                items = self.payload if isinstance(self.payload, list) else [self.payload]
                for item in items:
                    item = dict(item)
                    existing = None
                    if self.op == "upsert" and item.get(self.conflict) is not None:
                        existing = next((r for r in rows if r.get(self.conflict) == item[self.conflict]), None)
                    if existing is not None:
                        existing.update(item)
                        changed.append(existing)
                    else:
                        item.setdefault("id", table["next_id"])
                        table["next_id"] = max(table["next_id"], int(item["id"])) + 1
                        item.setdefault("created_at", datetime.now(timezone.utc).isoformat())
                        rows.append(item)
                        changed.append(item)
            elif self.op == "update":
                for r in rows:
                    if self._match(r):
                        r.update(self.payload)
                        changed.append(r)
            elif self.op == "delete":
                changed = [r for r in rows if self._match(r)]
                table["rows"] = [r for r in rows if not self._match(r)]

            self.store.write(self.name, table)
            return _Result([dict(r) for r in changed])
