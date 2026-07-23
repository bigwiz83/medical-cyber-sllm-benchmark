"""Pure, deterministic implementation of the frozen lexical retriever."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{1,}")


@dataclass(frozen=True, slots=True)
class CorpusDocument:
    corpus_object_id: str
    content: bytes


@dataclass(frozen=True, slots=True)
class RetrievedDocument:
    corpus_object_id: str
    content: str
    included_bytes: int
    lexical_score: int


def flatten_text(value: Any) -> str:
    """Match the recursive scalar projection used by the frozen runner."""

    if isinstance(value, Mapping):
        return " ".join(
            f"{key} {flatten_text(child)}"
            for key, child in sorted(value.items(), key=lambda item: str(item[0]))
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return " ".join(flatten_text(child) for child in value)
    if value is None:
        return "null"
    return str(value)


def terms(value: str) -> tuple[str, ...]:
    return tuple(token.casefold() for token in TOKEN_PATTERN.findall(value))


def utf8_prefix(data: bytes, limit: int) -> str:
    """Return the longest valid UTF-8 prefix no longer than ``limit`` bytes."""

    clipped = data[:limit]
    while clipped:
        try:
            return clipped.decode("utf-8")
        except UnicodeDecodeError as exc:
            clipped = clipped[: exc.start]
    raise ValueError("retrieved corpus object is not valid non-empty UTF-8")


def retrieve(
    input_artifacts: Sequence[Any],
    corpus: Sequence[CorpusDocument],
    *,
    top_k: int = 6,
    maximum_bytes_per_object: int = 5_000,
    maximum_total_bytes: int = 30_000,
) -> tuple[RetrievedDocument, ...]:
    """Rank and truncate corpus bytes using the study's fixed retrieval rule."""

    if top_k < 1 or maximum_bytes_per_object < 1 or maximum_total_bytes < 1:
        raise ValueError("retrieval limits must be positive")
    query_text = " ".join(flatten_text(payload) for payload in input_artifacts)
    query_terms = set(terms(query_text))
    ranked: list[tuple[int, str, CorpusDocument]] = []
    for document in corpus:
        content = utf8_prefix(document.content, maximum_bytes_per_object)
        document_terms = terms(content)
        score = sum(document_terms.count(term) for term in query_terms)
        ranked.append((-score, document.corpus_object_id, document))
    ranked.sort(key=lambda row: (row[0], row[1]))

    selected: list[RetrievedDocument] = []
    included_total = 0
    for negative_score, object_id, document in ranked:
        if len(selected) >= top_k:
            break
        remaining = maximum_total_bytes - included_total
        if remaining <= 0:
            break
        allowed = min(maximum_bytes_per_object, remaining, len(document.content))
        content = utf8_prefix(document.content, allowed)
        included_bytes = len(content.encode("utf-8"))
        selected.append(
            RetrievedDocument(
                corpus_object_id=object_id,
                content=content,
                included_bytes=included_bytes,
                lexical_score=-negative_score,
            )
        )
        included_total += included_bytes
    if len(selected) != top_k:
        raise ValueError("corpus cannot satisfy the frozen retrieval top-k")
    return tuple(selected)


__all__ = [
    "CorpusDocument",
    "RetrievedDocument",
    "flatten_text",
    "retrieve",
    "terms",
    "utf8_prefix",
]
