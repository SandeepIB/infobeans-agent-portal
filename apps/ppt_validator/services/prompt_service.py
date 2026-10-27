"""Prompt service — fetches active prompt versions from DB."""
from __future__ import annotations
import json
from pathlib import Path
from db.session import db

SEED_DIR = Path(__file__).parent.parent / "prompts"


class PromptService:

    def get_active(self, agent_id: str, profile_prompt_version_id: int | None = None) -> dict:
        """Return {system, user_template, version_id} for agent_id."""
        with db() as conn:
            if profile_prompt_version_id:
                row = conn.execute(
                    "SELECT id, system_prompt, user_template FROM prompt_versions WHERE id=?",
                    (profile_prompt_version_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    """SELECT pv.id, pv.system_prompt, pv.user_template
                       FROM prompt_activations pa
                       JOIN prompt_versions pv ON pv.id = pa.prompt_version_id
                       WHERE pa.agent_id=? AND pa.is_active=1
                       ORDER BY pa.activated_at DESC LIMIT 1""",
                    (agent_id,),
                ).fetchone()

        if row:
            return {"version_id": row["id"], "system": row["system_prompt"], "user_template": row["user_template"]}

        return self._load_seed(agent_id)

    def _load_seed(self, agent_id: str) -> dict:
        candidates = [
            SEED_DIR / agent_id / "v1.json",
            SEED_DIR / f"{agent_id}_agent" / "v1.json",
            SEED_DIR / agent_id.removesuffix("_agent") / "v1.json",
        ]
        for seed in candidates:
            if seed.exists():
                data = json.loads(seed.read_text())
                return {"version_id": None, "system": data["system"], "user_template": data["user_template"]}
        return {"version_id": None, "system": f"You are a PPT review agent: {agent_id}.", "user_template": "{context}"}

    def list_versions(self, agent_id: str) -> list[dict]:
        with db() as conn:
            rows = conn.execute(
                "SELECT id, version_tag, created_at FROM prompt_versions WHERE agent_id=? ORDER BY id DESC",
                (agent_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def create_version(self, agent_id: str, system: str, user_template: str, version_tag: str, created_by: str) -> int:
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO prompt_versions (agent_id, version_tag, system_prompt, user_template, created_by) VALUES (?,?,?,?,?)",
                (agent_id, version_tag, system, user_template, created_by),
            )
            return cur.lastrowid

    def activate(self, agent_id: str, version_id: int, activated_by: str) -> None:
        with db() as conn:
            conn.execute("UPDATE prompt_activations SET is_active=0 WHERE agent_id=?", (agent_id,))
            conn.execute(
                "INSERT INTO prompt_activations (agent_id, prompt_version_id, activated_by, is_active) VALUES (?,?,?,1)",
                (agent_id, version_id, activated_by),
            )
