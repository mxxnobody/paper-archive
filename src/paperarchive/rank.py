"""관련도 랭킹 — 1차 키워드 스코어로 후보 축소, 2차 Claude 의미 랭킹.

- keyword_score / prefilter: 외부 의존 없는 순수 함수(테스트 가능).
- claude_rank: 후보를 배치로 묶어 Claude가 0~100 관련도 + 근거 산출.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from .llm import complete_json
from .sources.base import Paper

log = logging.getLogger(__name__)


@dataclass
class ScoredPaper:
    paper: Paper
    keyword_score: float = 0.0
    relevance: int = 0          # Claude 0~100
    reason: str = ""            # 한국어 관련도 근거
    is_canon: bool = False


def keyword_score(paper: Paper, keywords: list[str], allowlist: list[str]) -> float:
    """제목·abstract·concept의 키워드 매칭 + 저널 allowlist 가산점."""
    haystack = " ".join([
        paper.title or "",
        paper.abstract or "",
        " ".join(paper.concepts),
    ]).lower()
    score = sum(1.0 for kw in keywords if kw.lower() in haystack)
    venue = (paper.venue or "").lower()
    if allowlist and any(j.lower() in venue for j in allowlist):
        score += 2.0
    return score


def prefilter(
    papers: list[Paper], keywords: list[str], allowlist: list[str], top_n: int
) -> list[ScoredPaper]:
    """키워드 스코어 > 0인 논문을 점수순으로 정렬해 상위 top_n 반환."""
    scored = [
        ScoredPaper(paper=p, keyword_score=keyword_score(p, keywords, allowlist))
        for p in papers
    ]
    scored = [s for s in scored if s.keyword_score > 0]
    scored.sort(key=lambda s: (s.keyword_score, s.paper.cited_by), reverse=True)
    return scored[:top_n]


_RANK_SYSTEM = (
    "당신은 스타트업 모험자본·창업금융 분야의 연구 조교입니다. "
    "연구자의 프로필에 비추어 각 논문의 관련도를 0~100으로 냉정하게 평가합니다."
)


def _build_rank_prompt(profile: dict, batch: list[ScoredPaper]) -> str:
    lines = [
        "## 연구자 프로필",
        profile.get("researcher", ""),
        f"종속변수: {', '.join(profile.get('dependent_variables', []))}",
        f"독립변수: {', '.join(profile.get('independent_variables', []))}",
        "",
        "## 평가 기준",
        "- 종속변수(후속투자·단계적투자·투자규모·생존/exit)와의 관련성",
        "- 독립변수(특히 market traction)와의 관련성",
        "- 한국 시장 적용·확장 가능성",
        "- 방법론적 참고가치(ML 등)",
        "",
        "## 논문 목록",
    ]
    for i, s in enumerate(batch):
        abs = (s.paper.abstract or "")[:1200]
        lines.append(
            f"[{i}] 제목: {s.paper.title}\n"
            f"    저널: {s.paper.venue or 'NA'} ({s.paper.year or 'NA'})\n"
            f"    초록: {abs or '(없음)'}"
        )
    lines += [
        "",
        "각 논문에 대해 JSON 배열로만 답하세요. 형식:",
        '[{"index": 0, "relevance": 0-100, "reason": "한국어 한 문장 근거"}, ...]',
        "relevance는 위 기준에 부합할수록 높게. 무관하면 낮게.",
    ]
    return "\n".join(lines)


def claude_rank(
    candidates: list[ScoredPaper], profile: dict, batch_size: int = 12
) -> list[ScoredPaper]:
    """후보를 배치로 Claude에 보내 relevance/reason을 채워 반환(in-place 갱신)."""
    model = profile.get("model", "claude-sonnet-4-6")
    for start in range(0, len(candidates), batch_size):
        batch = candidates[start:start + batch_size]
        prompt = _build_rank_prompt(profile, batch)
        try:
            result = complete_json(prompt, model=model, max_tokens=2048, system=_RANK_SYSTEM)
        except (json.JSONDecodeError, Exception) as e:  # noqa: BLE001
            log.warning("랭킹 배치 실패(%d~): %s", start, e)
            continue
        for item in result:
            idx = item.get("index")
            if idx is None or idx >= len(batch):
                continue
            batch[idx].relevance = int(item.get("relevance", 0))
            batch[idx].reason = item.get("reason", "")
    candidates.sort(key=lambda s: s.relevance, reverse=True)
    return candidates
