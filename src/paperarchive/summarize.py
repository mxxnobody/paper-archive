"""요약 생성 (LLM 미사용) — abstract/TLDR + 키워드 기반 DV/IV/방법 태깅.

LLM 없이 동작하도록 원문 abstract와 Semantic Scholar TLDR를 그대로 쓰고,
연구자 도메인에 맞춘 용어 사전으로 종속/독립변수·방법을 휴리스틱 추출한다.
요약 본문은 영어(원문 기반), 라벨은 한국어.
"""
from __future__ import annotations

from dataclasses import dataclass

from .rank import ScoredPaper

# 도메인 용어 사전 — 매칭되면 해당 변수/방법으로 표기 (소문자 부분일치)
_DV_TERMS = {
    "follow-on": "후속투자", "follow on": "후속투자", "followon": "후속투자",
    "staged financing": "단계적 투자", "staging": "단계적 투자",
    "valuation": "기업가치", "investment amount": "투자규모",
    "survival": "생존", "exit": "exit", "ipo": "IPO",
    "acquisition": "M&A", "merger": "M&A", "fundraising": "펀드레이징",
}
_IV_TERMS = {
    "traction": "market traction", "user growth": "사용자 성장",
    "startup growth": "스타트업 성장", "growth": "성장",
    "governance": "기업지배구조", "board": "이사회",
    "machine learning": "머신러닝", "deep learning": "딥러닝",
    " ml ": "머신러닝", "signal": "신호",
}
_METHOD_TERMS = {
    "difference-in-differences": "이중차분(DiD)", "diff-in-diff": "이중차분(DiD)",
    "regression discontinuity": "회귀불연속(RDD)",
    "instrumental variable": "도구변수(IV)",
    "machine learning": "머신러닝", "random forest": "머신러닝",
    "panel": "패널분석", "survival analysis": "생존분석",
    "matching": "매칭", "natural experiment": "자연실험",
    "regression": "회귀분석",
}


@dataclass
class KoreanSummary:
    summary: str = ""             # 원문 기반 요약(TLDR 우선, 없으면 abstract)
    dependent_var: str = ""       # 키워드로 탐지된 종속변수 후보
    independent_var: str = ""     # 키워드로 탐지된 독립변수 후보(traction 강조)
    method: str = ""              # 탐지된 방법론
    korea_implication: str = ""   # LLM 미사용 시 비움


def _detect(text: str, terms: dict[str, str]) -> str:
    found: list[str] = []
    for needle, label in terms.items():
        if needle in text and label not in found:
            found.append(label)
    return ", ".join(found)


def summarize(s: ScoredPaper, profile: dict | None = None) -> KoreanSummary:
    p = s.paper
    tldr = p.extra.get("tldr")
    abstract = p.abstract or ""
    if tldr:
        body = tldr
    elif abstract:
        body = abstract[:600] + ("…" if len(abstract) > 600 else "")
    else:
        body = "(초록 없음 — DOI 링크에서 확인)"

    text = f" {(p.title or '').lower()} {abstract.lower()} {(tldr or '').lower()} "
    return KoreanSummary(
        summary=body,
        dependent_var=_detect(text, _DV_TERMS),
        independent_var=_detect(text, _IV_TERMS),
        method=_detect(text, _METHOD_TERMS),
        korea_implication="",
    )
