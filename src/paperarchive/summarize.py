"""한국어 구조화 요약 생성 — 관련도 임계값 통과 논문 대상.

내용은 가공하지 않고 abstract에 근거해 요약한다(없는 내용 추론 금지).
필드: summary(요약), dependent_var, independent_var, method, korea_implication.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from .llm import complete_json
from .rank import ScoredPaper

log = logging.getLogger(__name__)


@dataclass
class KoreanSummary:
    summary: str = ""             # 3~4문장 한국어 요약
    dependent_var: str = ""       # 식별된 종속변수
    independent_var: str = ""     # 식별된 독립변수
    method: str = ""              # 데이터·방법론
    korea_implication: str = ""   # 한국 시장 적용 함의


_SYSTEM = (
    "당신은 창업금융 연구 논문을 한국어로 정확히 요약하는 연구 조교입니다. "
    "초록에 명시된 내용만 사용하고, 없는 결과를 지어내지 마세요."
)


def _prompt(profile: dict, s: ScoredPaper) -> str:
    p = s.paper
    return "\n".join([
        "다음 논문을 한국 기반 창업금융 연구자 관점에서 요약하세요.",
        f"제목: {p.title}",
        f"저널: {p.venue or 'NA'} ({p.year or 'NA'})",
        f"초록: {(p.abstract or '(초록 없음)')[:2500]}",
        "",
        "JSON 객체로만 답하세요:",
        json.dumps({
            "summary": "3~4문장 한국어 요약(연구질문·핵심결과 중심)",
            "dependent_var": "이 논문의 종속변수(없으면 빈 문자열)",
            "independent_var": "핵심 독립변수(market traction 관련 있으면 명시)",
            "method": "데이터·표본·분석방법 한 줄",
            "korea_implication": "한국 시장 적용/확장 시 시사점 한두 문장",
        }, ensure_ascii=False),
    ])


def summarize(s: ScoredPaper, profile: dict) -> KoreanSummary:
    model = profile.get("model", "claude-sonnet-4-6")
    try:
        data = complete_json(_prompt(profile, s), model=model, max_tokens=1200, system=_SYSTEM)
    except Exception as e:  # noqa: BLE001
        log.warning("요약 실패 (%s): %s", s.paper.title[:40], e)
        return KoreanSummary(summary="(요약 생성 실패)")
    return KoreanSummary(
        summary=data.get("summary", ""),
        dependent_var=data.get("dependent_var", ""),
        independent_var=data.get("independent_var", ""),
        method=data.get("method", ""),
        korea_implication=data.get("korea_implication", ""),
    )
