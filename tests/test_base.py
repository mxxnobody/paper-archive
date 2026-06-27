from paperarchive.sources.base import Paper, dedup, normalize_doi, normalize_title


def test_normalize_doi_strips_url_and_lowercases():
    assert normalize_doi("https://doi.org/10.1016/J.X") == "10.1016/j.x"
    assert normalize_doi("doi:10.1/AB") == "10.1/ab"
    assert normalize_doi(None) is None
    assert normalize_doi("  ") is None


def test_normalize_title():
    assert normalize_title("Venture Capital: A Survey!") == "venturecapitalasurvey"


def test_dedup_by_doi_merges_missing_fields():
    a = Paper(title="X", doi="10.1/a", source="openalex")
    b = Paper(title="X", doi="10.1/a", abstract="abs", cited_by=5, source="semanticscholar",
              extra={"tldr": "t"})
    out = dedup([a, b])
    assert len(out) == 1
    assert out[0].abstract == "abs"
    assert out[0].cited_by == 5
    assert out[0].extra["tldr"] == "t"


def test_dedup_by_title_when_no_doi():
    a = Paper(title="Same Title Here")
    b = Paper(title="same title  here!")
    assert len(dedup([a, b])) == 1


def test_key_prefers_doi():
    assert Paper(title="T", doi="10.1/x").key() == "doi:10.1/x"
    assert Paper(title="T").key().startswith("title:")
