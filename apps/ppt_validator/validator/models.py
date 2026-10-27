"""FROZEN — Legacy data models."""
from dataclasses import dataclass, field


@dataclass
class Violation:
    rule: str
    slide: int
    message: str
    severity: str = "MEDIUM"
    auto_fixable: bool = False


@dataclass
class ValidationResult:
    filename: str
    score: int
    violations: list[Violation] = field(default_factory=list)
    passed: bool = True
