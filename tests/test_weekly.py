from paperarchive.pipeline import weekly_selection
from paperarchive.rank import ScoredPaper
from paperarchive.record import Entry
from paperarchive.sources.base import Paper
from paperarchive.summarize import KoreanSummary


def _entry(doi, rel):
    return Entry(scored=ScoredPaper(paper=Paper(title="T", doi=doi), relevance=rel),
                 summary=KoreanSummary())


def test_weekly_selection_caps_and_discards_excess():
    e = [_entry(f"10.1/{i}", 90 - i) for i in range(3)]   # 3 kept, relevance desc
    processed = {x.paper.key() for x in e} | {"doi:10.9/sub"}  # +1 sub-threshold candidate
    delivered, seen_add = weekly_selection(e, processed, weekly_max=2)

    assert [d.paper.doi for d in delivered] == ["10.1/0", "10.1/1"]   # top 2 delivered
    # 초과분(3등)도 seen 처리(폐기, 이월 없음)
    assert "doi:10.1/2" in seen_add
    assert seen_add == processed


def test_weekly_selection_no_overflow():
    e = [_entry("10.1/a", 85)]
    processed = {"doi:10.1/a"}
    delivered, seen_add = weekly_selection(e, processed, weekly_max=20)
    assert len(delivered) == 1
    assert seen_add == {"doi:10.1/a"}
