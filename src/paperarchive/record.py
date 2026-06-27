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

    @staticmethod
    def from_dict(d: dict) -> "Entry":
        """site/data.json 의 dict를 Entry로 복원 (아카이브 재푸시용)."""
        from .sources.base import Paper
        p = Paper(
            title=d.get("title", ""), doi=d.get("doi"),
            authors=d.get("authors", []), year=d.get("year"),
            venue=d.get("venue"), abstract=d.get("abstract"),
            url=d.get("url"), concepts=d.get("concepts", []),
            cited_by=d.get("cited_by", 0) or 0,
        )
        s = ScoredPaper(paper=p, relevance=d.get("relevance", 0),
                        reason=d.get("reason", ""), is_canon=d.get("is_canon", False))
        summ = KoreanSummary(**d.get("summary", {}))
        return Entry(scored=s, summary=summ)

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
