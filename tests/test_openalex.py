from paperarchive.sources.openalex import _reconstruct_abstract, _to_paper


def test_reconstruct_abstract_orders_words():
    inv = {"Venture": [0], "capital": [1], "matters": [2]}
    assert _reconstruct_abstract(inv) == "Venture capital matters"
    assert _reconstruct_abstract(None) is None
    assert _reconstruct_abstract({}) is None


def test_to_paper_maps_fields():
    w = {
        "id": "https://openalex.org/W1",
        "doi": "https://doi.org/10.1/ABC",
        "title": "Staged Financing",
        "publication_year": 2015,
        "authorships": [{"author": {"display_name": "Jane Doe"}}],
        "primary_location": {"source": {"display_name": "Journal of Finance"}},
        "cited_by_count": 42,
        "concepts": [{"display_name": "Venture capital"}],
        "abstract_inverted_index": {"We": [0], "study": [1]},
    }
    p = _to_paper(w)
    assert p.doi == "10.1/abc"
    assert p.title == "Staged Financing"
    assert p.year == 2015
    assert p.authors == ["Jane Doe"]
    assert p.venue == "Journal of Finance"
    assert p.cited_by == 42
    assert p.concepts == ["Venture capital"]
    assert p.abstract == "We study"
    assert p.url == "https://doi.org/10.1/abc"
    assert p.source == "openalex"


def test_to_paper_handles_missing_optional_fields():
    p = _to_paper({"display_name": "No DOI Paper"})
    assert p.title == "No DOI Paper"
    assert p.doi is None
    assert p.authors == []
    assert p.abstract is None
