"""요약 생성 (LLM 미사용) — 간략 추출 + 비판적 읽기 보조.

LLM 없이 가능한 정직한 범위:
- summary: TLDR 우선, 없으면 결과/주장 문장 추출(없으면 첫 문장)
- key_result: "we find/show/..." 등 결과 단서 문장 추출
- dependent_var/independent_var/method: 키워드 사전 탐지
- caveats: 탐지된 방법에 대응하는 *일반* 점검 항목(논문별 실제 비평 아님)
"""
from __future__ import annotations

import re
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

# 방법/표본 단서 → 일반 유의점 (규칙 기반, 비판적 읽기 보조)
_CAVEAT_RULES = {
    "difference-in-differences": "DiD: 평행추세 가정 검토",
    "diff-in-diff": "DiD: 평행추세 가정 검토",
    "instrumental variable": "도구변수: 배제제약·약한도구 검토",
    "regression discontinuity": "RDD: 대역폭·경계조작 민감도",
    "machine learning": "예측≠인과 주의",
    "prediction": "예측≠인과 주의",
    "predict": "예측≠인과 주의",
    "random forest": "예측≠인과 주의",
    "neural": "예측≠인과 주의",
    "survey": "자기응답·표본 편의 가능",
    "self-reported": "자기응답 편의 가능",
    "questionnaire": "자기응답·표본 편의 가능",
    "propensity score": "매칭: 관측가능 변수에 한정",
    "cross-sectional": "횡단면: 상관≠인과",
    "correlation": "상관≠인과 주의",
}

_RESULT_CUES = [
    "we find", "we show", "we document", "we provide evidence", "we demonstrate",
    "we estimate", "results show", "results suggest", "results indicate",
    "find that", "show that", "evidence that", "our findings", "findings suggest",
]

KNOWN_FIELDS = {"summary", "key_result", "dependent_var", "independent_var",
                "method", "caveats"}


@dataclass
class KoreanSummary:
    summary: str = ""              # 1~2문장 간략 (원문 기반)
    key_result: str = ""          # 결과/주장 문장 추출(영문)
    dependent_var: str = ""       # 종속변수 후보(키워드)
    independent_var: str = ""     # 독립변수 후보(키워드)
    method: str = ""              # 방법론(키워드)
    caveats: str = ""             # 방법론 유의점(규칙 기반, 일반)


def _detect(text: str, terms: dict[str, str]) -> str:
    found: list[str] = []
    for needle, label in terms.items():
        if needle in text and label not in found:
            found.append(label)
    return ", ".join(found)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


def _extract_result(abstract: str) -> str:
    """결과 단서가 포함된 첫 문장을 추출(없으면 빈값)."""
    for sent in _sentences(abstract):
        low = sent.lower()
        if any(cue in low for cue in _RESULT_CUES):
            return sent[:300]
    return ""


def summarize(s: ScoredPaper, profile: dict | None = None) -> KoreanSummary:
    p = s.paper
    tldr = p.extra.get("tldr")
    abstract = p.abstract or ""
    key_result = _extract_result(abstract)

    if tldr:
        body = tldr
    elif key_result:
        body = key_result
    elif abstract:
        sents = _sentences(abstract)
        body = " ".join(sents[:2])[:300] + ("…" if len(abstract) > 300 else "")
    else:
        body = "(초록 없음 — DOI 링크에서 확인)"

    text = f" {(p.title or '').lower()} {abstract.lower()} {(tldr or '').lower()} "
    return KoreanSummary(
        summary=body,
        key_result=key_result,
        dependent_var=_detect(text, _DV_TERMS),
        independent_var=_detect(text, _IV_TERMS),
        method=_detect(text, _METHOD_TERMS),
        caveats=_detect(text, _CAVEAT_RULES),
    )
