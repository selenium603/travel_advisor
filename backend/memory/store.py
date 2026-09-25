"""Atomic local store for short-term sessions and long-term preferences."""

import copy
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4

from backend.models.schemas import PreferenceUpdate, TravelFormDetails, TravelPlanParams


MEMORY_FILE = Path(__file__).resolve().parents[2] / "data" / "memory.json"
PREFERENCE_CATEGORIES = ("lodging", "food", "pace", "sights", "budget")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    def __init__(self, path: Path = MEMORY_FILE):
        self.path = path
        self._lock = RLock()
        if path.exists():
            with path.open(encoding="utf-8") as stream:
                self._data = json.load(stream)
        else:
            self._data = {"profile": {}, "changes": [], "sessions": {}}
        if not isinstance(self._data, dict):
            raise ValueError(f"Invalid memory store in {path}")
        for key, default in (("profile", {}), ("changes", []), ("sessions", {})):
            self._data.setdefault(key, default)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f"{self.path.name}.{uuid4().hex}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as stream:
                json.dump(self._data, stream, ensure_ascii=False, indent=2)
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)

    def profile(self) -> dict:
        with self._lock:
            return copy.deepcopy({
                "preferences": self._data["profile"],
                "changes": self._data["changes"][-20:],
            })

    def session(self, session_id: str) -> dict:
        with self._lock:
            return copy.deepcopy(self._data["sessions"].get(session_id, {}))

    def upsert_preference(
        self, update: PreferenceUpdate, source_kind: str, session_id: str | None = None
    ) -> dict:
        value = update.value.strip()
        if not value:
            raise ValueError("偏好内容不能为空")
        with self._lock:
            previous = self._data["profile"].get(update.category)
            if previous and previous["value"] == value:
                return copy.deepcopy(previous)
            current = {
                "value": value,
                "updated_at": _now(),
                "source": {
                    "kind": source_kind,
                    "quote": update.source_quote.strip(),
                    "session_id": session_id,
                },
            }
            self._data["profile"][update.category] = current
            self._data["changes"].append({
                "category": update.category,
                "old_value": previous["value"] if previous else None,
                "new_value": value,
                "updated_at": current["updated_at"],
                "source": current["source"],
            })
            self._data["changes"] = self._data["changes"][-100:]
            self._save()
            return copy.deepcopy(current)

    def delete_preference(self, category: str) -> bool:
        if category not in PREFERENCE_CATEGORIES:
            raise ValueError("未知偏好类别")
        with self._lock:
            previous = self._data["profile"].pop(category, None)
            if previous is None:
                return False
            # Deletion must also forget superseded values in the audit trail.
            self._data["changes"] = [
                change for change in self._data["changes"]
                if change["category"] != category
            ]
            self._save()
            return True

    def clear_session(self, session_id: str) -> bool:
        with self._lock:
            if self._data["sessions"].pop(session_id, None) is None:
                return False
            self._save()
            return True

    def _session(self, session_id: str) -> dict:
        sessions = self._data["sessions"]
        if session_id not in sessions:
            if len(sessions) >= 50:
                oldest = min(sessions, key=lambda key: sessions[key]["updated_at"])
                del sessions[oldest]
            sessions[session_id] = {
                "recent_messages": [], "current_plan_state": "idle",
                "current_plan": None, "updated_at": _now(),
            }
        return sessions[session_id]

    def record_request(
        self, session_id: str, message: str, form_details: TravelFormDetails | None
    ) -> None:
        with self._lock:
            session = self._session(session_id)
            session["recent_messages"].append({
                "role": "user", "content": message[:1200], "at": _now(),
            })
            session["recent_messages"] = session["recent_messages"][-8:]
            session["current_plan_state"] = "submitted"
            session["current_plan"] = (
                form_details.model_dump(mode="json") if form_details else None
            )
            session["updated_at"] = _now()
            self._save()

    def record_params(self, session_id: str, params: TravelPlanParams) -> None:
        with self._lock:
            session = self._session(session_id)
            session["current_plan"] = params.model_dump(mode="json")
            session["current_plan_state"] = "validated"
            session["updated_at"] = _now()
            self._save()

    def record_state(self, session_id: str, state: str) -> None:
        with self._lock:
            session = self._session(session_id)
            session["current_plan_state"] = state
            session["updated_at"] = _now()
            if state in {"completed", "failed"}:
                plan = session.get("current_plan") or {}
                destinations = "、".join(plan.get("destinations", []))
                trip_label = f"{destinations} {plan.get('departure_date', '')}".strip()
                session["recent_messages"].append({
                    "role": "assistant",
                    "content": (
                        f"已完成 {trip_label} 行程" if state == "completed" and trip_label
                        else "行程规划已完成" if state == "completed" else "行程规划失败"
                    ),
                    "at": session["updated_at"],
                })
                session["recent_messages"] = session["recent_messages"][-8:]
            self._save()

    def context(self, session_id: str | None) -> str:
        """Keep memory lower priority than the current request and explicit form."""
        with self._lock:
            profile = {
                key: entry["value"] for key, entry in self._data["profile"].items()
            }
            session = self._data["sessions"].get(session_id or "", {})
            context = {
                "long_term_preferences": profile,
                "recent_messages": session.get("recent_messages", [])[-4:],
                "current_plan_state": session.get("current_plan_state"),
                "current_plan": session.get("current_plan"),
            }
            return json.dumps(context, ensure_ascii=False)


memory_store = MemoryStore()
