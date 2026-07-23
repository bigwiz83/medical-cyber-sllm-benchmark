from medcyber_benchmark.retrieval import CorpusDocument, flatten_text, retrieve, terms


def test_flatten_and_terms_match_frozen_rules() -> None:
    value = {"z": ["CVE-2026-1234", None], "a": {"product": "PACS"}}
    assert flatten_text(value) == "a product PACS z CVE-2026-1234 null"
    assert terms(flatten_text(value)) == (
        "product",
        "pacs",
        "cve-2026-1234",
        "null",
    )


def test_retrieval_scores_multiplicity_and_breaks_ties_by_id() -> None:
    corpus = (
        CorpusDocument("obj_b", b"PACS PACS unrelated"),
        CorpusDocument("obj_c", b"PACS CVE-2026-1234"),
        CorpusDocument("obj_a", b"PACS CVE-2026-1234"),
    )
    selected = retrieve(
        ({"product": "PACS", "target": "CVE-2026-1234"},),
        corpus,
        top_k=3,
    )
    assert [(item.corpus_object_id, item.lexical_score) for item in selected] == [
        ("obj_a", 2),
        ("obj_b", 2),
        ("obj_c", 2),
    ]


def test_retrieval_uses_valid_utf8_prefix_and_total_budget() -> None:
    corpus = (
        CorpusDocument("obj_a", "PACS가".encode()),
        CorpusDocument("obj_b", b"PACS"),
    )
    selected = retrieve(
        ({"product": "PACS"},),
        corpus,
        top_k=2,
        maximum_bytes_per_object=6,
        maximum_total_bytes=10,
    )
    assert selected[0].content == "PACS"
    assert sum(item.included_bytes for item in selected) == 8
