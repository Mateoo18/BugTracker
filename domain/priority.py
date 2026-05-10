from dataclasses import dataclass


@dataclass(frozen=True)
class PriorityInputs:
    severity: str
    impact: int
    similar_reports: int
    age_days: int
    module_importance: int


SEVERITY_WEIGHTS = {
    "critical": 45,
    "high": 32,
    "medium": 20,
    "low": 8,
}


def calculate_priority_score(inputs: PriorityInputs) -> int:
    score = SEVERITY_WEIGHTS.get(inputs.severity, 10)
    score += max(1, min(inputs.impact, 5)) * 7
    score += min(inputs.similar_reports, 20) * 2
    score += min(inputs.age_days, 30)
    score += max(1, min(inputs.module_importance, 5)) * 5
    return min(score, 100)


def map_score_to_priority(score: int) -> str:
    if score >= 85:
        return "P0"
    if score >= 65:
        return "P1"
    if score >= 40:
        return "P2"
    return "P3"
