"""출력 채널 공용 레코드 — 랭킹+요약이 끝난 한 논문의 최종 형태."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .rank import ScoredPaper
from .summarize import KoreanSummary


@dataclass
class Entry:
    scored: ScoredPaper
    summary: KoreanSummary

    @property
    def paper(self):
        return self.scored.paper

    def to_dict(self) -> dict:
        p = self.paper
        return {
            "title": p.title,
            "doi": p.doi,
            "authors": p.authors,
            "year": p.year,
            "venue": p.venue,
            "url": p.url,
            "abstract": p.abstract,
            "cited_by": p.cited_by,
            "concepts": p.concepts,
            "relevance": self.scored.relevance,
            "reason": self.scored.reason,
            "is_canon": self.scored.is_canon,
            "summary": asdict(self.summary),
        }
