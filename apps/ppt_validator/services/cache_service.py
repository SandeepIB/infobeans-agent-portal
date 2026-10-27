"""LLM cache service — SQLite/MySQL-backed, keyed on prompt + model + version hash."""
from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime, timedelta
from db.session import db, IS_MYSQL

TTL_HOURS = int(os.getenv("LLM_CACHE_TTL_HOURS", "24"))


class CacheService:

    def _key(self, provider: str, model: str, prompt_version_id: int | None, system: str, user: str) -> str:
        raw = f"{provider}|{model}|{prompt_version_id}|{system}|{user}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, provider: str, model: str, prompt_version_id: int | None, system: str, user: str) -> dict | None:
        key = self._key(provider, model, prompt_version_id, system, user)
        with db() as conn:
            row = conn.execute(
                "SELECT response_json, expires_at FROM llm_cache WHERE cache_key=?", (key,)
            ).fetchone()
            if not row:
                return None
            expires_at = row["expires_at"]
            if expires_at:
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at)
                if expires_at < datetime.utcnow():
                    return None
            conn.execute("UPDATE llm_cache SET hit_count = hit_count + 1 WHERE cache_key=?", (key,))
        return json.loads(row["response_json"])

    def set(self, provider: str, model: str, prompt_version_id: int | None, system: str, user: str,
            response: dict, input_tokens: int, output_tokens: int) -> None:
        key = self._key(provider, model, prompt_version_id, system, user)
        expires = (datetime.utcnow() + timedelta(hours=TTL_HOURS)).isoformat()
        resp_json = json.dumps(response)
        with db() as conn:
            if IS_MYSQL:
                conn.execute(
                    """INSERT INTO llm_cache
                       (cache_key, provider, model, prompt_version_id, response_json, input_tokens, output_tokens, expires_at)
                       VALUES (?,?,?,?,?,?,?,?)
                       ON DUPLICATE KEY UPDATE
                         response_json=VALUES(response_json), expires_at=VALUES(expires_at),
                         input_tokens=VALUES(input_tokens), output_tokens=VALUES(output_tokens), hit_count=0""",
                    (key, provider, model, prompt_version_id, resp_json, input_tokens, output_tokens, expires),
                )
            else:
                conn.execute(
                    """INSERT OR REPLACE INTO llm_cache
                       (cache_key, provider, model, prompt_version_id, response_json, input_tokens, output_tokens, expires_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (key, provider, model, prompt_version_id, resp_json, input_tokens, output_tokens, expires),
                )
