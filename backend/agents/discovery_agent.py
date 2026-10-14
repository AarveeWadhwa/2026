
"""Tender Discovery Agent: local-catalogue retrieval and explainable relevance ranking."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOGUE = ROOT / "data" / "sample_tenders" / "tenders.json"

STOP_WORDS = {
    "and", "the", "for", "with", "from", "that", "this", "into", "are",
    "is", "of", "to", "in", "a", "an", "by", "on", "or", "as", "at",
    "company", "services", "service", "work", "supply", "required"
}


def tokenize(value: str) -> set[str]:
    """Normalize text into useful matching terms."""
    return {
        token for token in re.findall(r"[a-zA-Z0-9]+", (value or "").lower())
        if len(token) > 1 and token not in STOP_WORDS
    }


class TenderDiscoveryAgent:
    """Searches tender records and explains why each record matched.

    This first version searches a local catalogue so the demo is repeatable.
    A public-portal adapter can populate the same record schema later.
    """

    def __init__(self, catalogue_path: str | Path = DEFAULT_CATALOGUE):
        self.catalogue_path = Path(catalogue_path)

    def load_tenders(self) -> list[dict[str, Any]]:
        if not self.catalogue_path.exists():
            raise FileNotFoundError(f"Tender catalogue not found: {self.catalogue_path}")
        with self.catalogue_path.open("r", encoding="utf-8") as handle:
            records = json.load(handle)
        if not isinstance(records, list):
            raise ValueError("Tender catalogue must contain a JSON list.")
        return records

    @staticmethod
    def _profile_text(profile: dict[str, Any]) -> str:
        fields: Iterable[str] = (
            str(profile.get("industry", "")),
            str(profile.get("services", "")),
            " ".join(profile.get("keywords", []) or []),
            " ".join(profile.get("past_projects", []) or []),
            str(profile.get("location", "")),
        )
        return " ".join(fields)

    def search(
        self,
        company_profile: dict[str, Any],
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Rank catalogue tenders by overlap with the company profile.

        The score is a transparent lexical relevance score, not an eligibility
        decision. Eligibility is checked by a separate agent.
        """
        profile_terms = tokenize(self._profile_text(company_profile))
        if not profile_terms:
            return []

        results: list[dict[str, Any]] = []
        for tender in self.load_tenders():
            searchable = " ".join([
                str(tender.get("title", "")),
                str(tender.get("description", "")),
                " ".join(tender.get("categories", []) or []),
                str(tender.get("location", "")),
                str(tender.get("organization", "")),
            ])
            tender_terms = tokenize(searchable)
            matched = sorted(profile_terms & tender_terms)
            # Explicit negative feedback lowers ranking without excluding opportunities.
            negative_terms = set()
            for keyword in company_profile.get("deprioritized_keywords", []) or []:
                negative_terms.update(tokenize(str(keyword)))
            matched_negative = sorted(negative_terms & tender_terms)
            # Coverage score is transparent; each negative match applies a capped penalty.
            base_score = len(matched) / max(len(profile_terms), 1) * 100
            penalty = min(30.0, 10.0 * len(matched_negative))
            score = round(max(0.0, base_score - penalty), 1)
            if score < min_score:
                continue
            result = dict(tender)
            result["relevance_score"] = score
            result["matched_terms"] = matched
            result["deprioritized_matches"] = matched_negative
            result["preference_penalty"] = penalty
            note = "Matched terms: " + (", ".join(matched) if matched else "none")
            if matched_negative:
                note += "; preference penalty for: " + ", ".join(matched_negative)
            result["discovery_note"] = note
            results.append(result)

        results.sort(key=lambda item: item["relevance_score"], reverse=True)
        return results[:max(0, limit)]


def demo() -> None:
    profile = {
        "industry": "IT and computer equipment",
        "services": "computer hardware networking and IT support",
        "keywords": ["laptop", "network", "software", "cybersecurity"],
        "location": "Maharashtra",
    }
    agent = TenderDiscoveryAgent()
    for item in agent.search(profile, limit=5):
        print(f'{item["relevance_score"]:>5}% | {item["title"]}')
        print(f'       {item["organization"]} | Deadline: {item.get("deadline", "Not listed")}')
        print(f'       {item["discovery_note"]}')


if __name__ == "__main__":
    demo()
