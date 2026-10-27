"""Rule service — fetches active rule sets from DB or YAML seeds."""
from __future__ import annotations
import json
from pathlib import Path
from db.session import db

SEED_DIR = Path(__file__).parent.parent / "rule_library"


class RuleService:

    def get_rules(self, domain: str) -> list[dict]:
        """Return active rules for a domain (e.g. 'branding', 'typography')."""
        rules = []
        with db() as conn:
            rows = conn.execute(
                """SELECT rv.rule_id, rv.rule_json
                   FROM rule_versions rv
                   WHERE rv.domain=? AND rv.is_active=1
                   ORDER BY rv.id DESC""",
                (domain,),
            ).fetchall()

        if rows:
            rules = [json.loads(r["rule_json"]) for r in rows]
        else:
            rules = self._load_seed(domain)

        # Merge rules.yaml definitions if present
        yaml_rules = self._load_yaml(domain)
        existing_types = {r.get("type") for r in rules}
        for yr in yaml_rules:
            if yr.get("type") not in existing_types:
                rules.append(yr)

        return rules

    def _load_seed(self, domain: str) -> list[dict]:
        seed = SEED_DIR / domain / "rules.json"
        if seed.exists():
            return json.loads(seed.read_text())
        return []

    def _load_yaml(self, domain: str) -> list[dict]:
        yaml_path = Path(__file__).parent.parent / "rules.yaml"
        if not yaml_path.exists():
            return []
        try:
            import yaml
            data = yaml.safe_load(yaml_path.read_text()) or {}
            theme = data.get("theme", {})
            results = []
            if domain == "branding":
                hr = theme.get("heading_rules", {})
                if "case" in hr:
                    results.append({"type": "heading_case", "value": str(hr["case"]), "rule_id": "yaml_heading_case"})
                if "eyebrow_case" in hr:
                    results.append({"type": "eyebrow_case", "value": str(hr["eyebrow_case"]), "rule_id": "yaml_eyebrow_case"})
                if "eyebrow_position" in hr:
                    results.append({"type": "eyebrow_position", "value": str(hr["eyebrow_position"]), "rule_id": "yaml_eyebrow_position"})

                # Load colors dynamically from YAML
                colors = theme.get("colors", {})
                for c_name, hex_val in colors.items():
                    results.append({"type": "allowed_color", "value": str(hex_val), "rule_id": f"yaml_color_{c_name}"})

                # Load placeholder patterns dynamically from YAML
                phs = data.get("placeholders", {}).get("forbidden_patterns", [])
                for ph in phs:
                    results.append({"type": "placeholder_pattern", "value": str(ph), "rule_id": "yaml_placeholder_pattern"})

                # Load brand spelling rules
                for fc in theme.get("brand_spelling", {}).get("forbidden_casing", []):
                    results.append({"type": "forbidden_brand_spelling", "value": str(fc), "rule_id": "yaml_brand_spelling"})

                # Load italic rules
                if "allowed_italic_only" in theme.get("fonts", {}):
                    results.append({"type": "allowed_italic_only", "value": str(theme["fonts"]["allowed_italic_only"]), "rule_id": "yaml_allowed_italic"})

                # Load source citation keywords dynamically from YAML
                cits = data.get("source_citations", {}).get("required_keywords", [])
                for cit in cits:
                    results.append({"type": "source_citation_keyword", "value": str(cit), "rule_id": "yaml_source_citation_keyword"})

            elif domain == "visual_quality":
                vq = data.get("visual_quality", {})
                for k, v in vq.items():
                    results.append({"type": k, "value": str(v), "rule_id": f"yaml_vq_{k}"})

            elif domain == "table_design":
                td = data.get("table_design", {})
                key_map = {
                    "max_columns_ideal":             "tbl_max_columns_ideal",
                    "max_columns_acceptable":        "tbl_max_columns_acceptable",
                    "check_column_alignment":        "tbl_check_column_alignment",
                    "check_border_minimalism":       "tbl_check_border_minimalism",
                    "check_font_consistency":        "tbl_check_font_consistency",
                    "check_number_format_consistency": "tbl_check_number_format_consistency",
                    "max_lines_per_cell":            "tbl_max_lines_per_cell",
                    "require_header_row":            "tbl_require_header_row",
                }
                for yaml_key, rule_type in key_map.items():
                    if yaml_key in td:
                        results.append({"type": rule_type, "value": str(td[yaml_key]), "rule_id": f"yaml_{rule_type}"})

            return results
        except Exception:
            return []

    def upsert_rule(self, domain: str, rule_id: str, rule_json: dict, created_by: str) -> None:
        with db() as conn:
            conn.execute("UPDATE rule_versions SET is_active=0 WHERE domain=? AND rule_id=?", (domain, rule_id))
            conn.execute(
                "INSERT INTO rule_versions (domain, rule_id, rule_json, created_by, is_active) VALUES (?,?,?,?,1)",
                (domain, rule_id, json.dumps(rule_json), created_by),
            )
