"""FROZEN — Legacy validation runner."""
from validator.checks import check_fonts, check_slide_count, check_pagination, check_logo
from validator.models import ValidationResult
from validator.rules import load_rules


def validate(slides: list[dict], filename: str) -> ValidationResult:
    rules = load_rules()
    violations = []
    violations.extend(check_fonts(slides, rules))
    violations.extend(check_slide_count(len(slides), rules))
    violations.extend(check_pagination(slides, rules))
    violations.extend(check_logo(slides, rules))
    score = max(0, 100 - len(violations) * 10)
    return ValidationResult(filename=filename, score=score, violations=violations, passed=score >= 60)

