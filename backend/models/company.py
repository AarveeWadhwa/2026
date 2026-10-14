
"""Company profile schema and lightweight validation."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class CompanyProfile:
    company_name: str
    industry: str = ""
    services: list[str] = field(default_factory=list)
    location: str = ""
    annual_turnover_inr: float | None = None
    years_experience: float | None = None
    certifications: list[str] = field(default_factory=list)
    past_projects: list[str] = field(default_factory=list)
    available_documents: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompanyProfile":
        if not isinstance(data, dict):
            raise TypeError("Company profile must be a dictionary.")
        name = str(data.get("company_name", "")).strip()
        if not name:
            raise ValueError("company_name is required.")
        turnover = data.get("annual_turnover_inr")
        experience = data.get("years_experience")
        return cls(
            company_name=name,
            industry=str(data.get("industry", "")).strip(),
            services=_as_string_list(data.get("services", [])),
            location=str(data.get("location", "")).strip(),
            annual_turnover_inr=_optional_nonnegative_number(turnover, "annual_turnover_inr"),
            years_experience=_optional_nonnegative_number(experience, "years_experience"),
            certifications=_as_string_list(data.get("certifications", [])),
            past_projects=_as_string_list(data.get("past_projects", [])),
            available_documents=_as_string_list(data.get("available_documents", [])),
            keywords=_as_string_list(data.get("keywords", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, (list, tuple, set)):
        raise TypeError("Expected a string or list of strings.")
    return [str(item).strip() for item in value if str(item).strip()]


def _optional_nonnegative_number(value: Any, field_name: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric.") from exc
    if number < 0:
        raise ValueError(f"{field_name} cannot be negative.")
    return number
