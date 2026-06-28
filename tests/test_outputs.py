from pathlib import Path

from paperarchive.outputs import html_site, ris, telegram
from paperarchive.rank import ScoredPaper
from paperarchive.record import Entry
from paperarchive.sources.base import Paper
from paperarchive.summarize import KoreanSummary


def make_entry(title="Staged Financing", doi="10.1/a", rel=85):
    p = Paper(title=title, doi=doi, authors=["Jane Doe", "John Roe"], year=2015,
              venue="Journal of Finance", abstract="We study staging.",
              url=f"https://doi.org/{doi}", concepts=["Venture capital"], cited_by=10)
    s = ScoredPaper(paper=p, relevance=rel, reason="후속투자와 직결")
    summ = KoreanSummary(summary="단계적 투자를 분석한다.", key_result="We find staging matters.",
                         dependent_var="후속투자", independent_var="market traction",
                         method="패널 회귀", caveats="DiD: 평행추세 가정 검토")
    return Entry(scored=s, summary=summ)


def test_ris_contains_core_fields(tmp_path):
    out = ris.write_ris([make_entry()], tmp_path / "x.ris")
    txt = out.read_text(encoding="utf-8")
    assert "TY  - JOUR" in txt
    assert "AU  - Jane Doe" in txt
    assert "DO  - 10.1/a" in txt
    assert "ER  -" in txt
    assert "관련도 85" in txt


def test_telegram_message_and_empty():
    assert "없습니다" in telegram.build_message([], 8, None)
    msg = telegram.build_message([make_entry()], 8, "https://x.io")
    assert "Staged Financing" in msg
    assert "관련도 85" in msg
    assert "https://x.io" in msg


def test_telegram_truncates_long():
    entries = [make_entry(title="T" * 500, doi=f"10.1/{i}") for i in range(50)]
    msg = telegram.build_message(entries, 50, None)
    assert len(msg) <= telegram.MAX_LEN + 1


def test_html_merge_dedup_and_render(tmp_path: Path):
    site = tmp_path / "site"
    html_site.update_site(site, [make_entry()], "2026-06-27")
    # 같은 DOI 재처리 → 1편 유지(갱신)
    html_site.update_site(site, [make_entry(rel=90)], "2026-06-28")
    store = html_site.load_store(site)
    assert len(store) == 1
    assert store[0]["relevance"] == 90
    html = (site / "index.html").read_text(encoding="utf-8")
    assert "Paper Archive" in html
    assert "Staged Financing" in html
