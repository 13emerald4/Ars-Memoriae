"""Document upload -> cited deck generation -> references shown during review.

The load-bearing property here is that a citation can be trusted: a quote the
model did not actually copy out of the source must never reach the user as if
it had.
"""

from __future__ import annotations

import io

import pytest

from app.services.document_service import (
    DocumentError,
    extract_document,
    quote_is_grounded,
)

MARKDOWN = """# Monetary Policy

Central banks set the policy rate to steer short-term interest rates.

## Balance Sheet Recessions

When a credit bubble bursts, the private sector shifts from profit
maximization to debt minimization, and monetary policy loses traction.
"""


def _minimal_pdf(pages: list[str]) -> bytes:
    """A hand-rolled PDF with one text line per page.

    Synthesised here rather than shipped as a binary fixture, the same way
    test_apkg_import.py builds Anki collections — page numbers are the whole
    point of PDF citations, so they need a real multi-page file to assert on.
    """
    font_num = 3 + 2 * len(pages)
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        font_num: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(len(pages)))
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode()

    for i, text in enumerate(pages):
        page_num, content_num = 3 + 2 * i, 4 + 2 * i
        objects[page_num] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_num} 0 R "
            f"/Resources << /Font << /F1 {font_num} 0 R >> >> >>"
        ).encode()
        escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode()
        objects[content_num] = (
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )

    out = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode() + objects[num] + b"\nendobj\n"

    xref_at = len(out)
    highest = max(objects)
    out += f"xref\n0 {highest + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for num in range(1, highest + 1):
        out += f"{offsets.get(num, 0):010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {highest + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    return bytes(out)


class TestExtraction:
    def test_markdown_segments_carry_their_heading_as_the_locator(self):
        title, segments = extract_document("notes.md", MARKDOWN.encode())
        assert title == "Monetary Policy"
        locators = {s.locator for s in segments}
        assert "Balance Sheet Recessions" in locators
        body = next(s for s in segments if s.locator == "Balance Sheet Recessions")
        assert "debt minimization" in body.text

    def test_plain_text_falls_back_to_numbered_parts(self):
        title, segments = extract_document("plain.txt", b"Just one paragraph of text.")
        assert title == "plain"
        assert segments[0].locator == "part 1"

    def test_html_is_stripped_to_readable_text(self):
        html = b"<html><head><title>On Memory</title></head><body><nav>menu</nav>"
        html += b"<article><p>Spacing beats massing.</p></article></body></html>"
        title, segments = extract_document("page.html", html)
        assert title == "On Memory"
        joined = " ".join(s.text for s in segments)
        assert "Spacing beats massing." in joined
        assert "menu" not in joined

    def test_pdf_pages_become_the_locator(self):
        """The headline case: a card cited to "p. 2" must point at page 2."""
        pdf = _minimal_pdf(["Alpha content on the first page.", "Beta content on the second."])
        title, segments = extract_document("textbook.pdf", pdf)
        assert title == "textbook"
        by_locator = {s.locator: s.text for s in segments}
        assert "Alpha" in by_locator["p. 1"]
        assert "Beta" in by_locator["p. 2"]

    async def test_pdf_upload_round_trips_page_locators(self, auth_client):
        pdf = _minimal_pdf(["First page material.", "Second page material."])
        resp = await auth_client.post(
            "/api/documents",
            files={"file": ("textbook.pdf", io.BytesIO(pdf), "application/pdf")},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["locators"] == ["p. 1", "p. 2"]

        extracts = (await auth_client.get(f"/api/sources/{body['source_id']}/extracts")).json()
        assert {e["locator"] for e in extracts} == {"p. 1", "p. 2"}

    def test_an_empty_upload_is_rejected_with_a_reason(self):
        with pytest.raises(DocumentError, match="empty"):
            extract_document("empty.txt", b"")

    def test_a_document_with_no_text_layer_says_so(self):
        with pytest.raises(DocumentError, match=r"no readable text|scanned"):
            extract_document("blank.txt", b"   \n\n   ")

    def test_unsupported_types_are_refused(self):
        with pytest.raises(DocumentError, match="unsupported"):
            extract_document("archive.zip", b"PK\x03\x04nonsense")


class TestQuoteGrounding:
    PASSAGE = "The private sector shifts from profit maximization to debt minimization."

    def test_a_verbatim_span_is_grounded(self):
        assert quote_is_grounded("from profit maximization to debt minimization", self.PASSAGE)

    def test_reflowed_whitespace_still_counts(self):
        assert quote_is_grounded("profit   maximization\n  to debt minimization", self.PASSAGE)

    def test_smart_quotes_and_dashes_are_normalized(self):
        passage = "Koo calls this a “balance sheet recession” — a debt-driven slump."
        assert quote_is_grounded('a "balance sheet recession" - a debt-driven slump', passage)

    def test_an_invented_quote_is_not_grounded(self):
        assert not quote_is_grounded(
            "The central bank raises rates to combat inflation.", self.PASSAGE
        )

    def test_a_trivially_short_quote_is_not_grounded(self):
        """Two words match almost anything; that isn't a citation."""
        assert not quote_is_grounded("the", self.PASSAGE)


async def _upload(client, name="notes.md", content: bytes = MARKDOWN.encode()):
    resp = await client.post(
        "/api/documents", files={"file": (name, io.BytesIO(content), "text/markdown")}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _queued_card(client, card_id: str) -> dict:
    """The composed session's entry for one card — not /queue/next, since a
    session can hold more than one item and the card under test need not be
    first in priority order."""
    session = (await client.get("/api/queue/session?preview=200")).json()
    item = next(
        (i for i in session["items"] if i["kind"] == "card" and i["id"] == card_id), None
    )
    assert item is not None, f"card {card_id} was not in the composed session"
    return item


class TestNeverSurfacedAsReading:
    """A document is uploaded to generate cards from, not to be read — its
    extracts must never compete with actual flashcards in the study queue."""

    async def test_a_document_upload_never_appears_as_reading_in_the_session(self, auth_client):
        body = await _upload(auth_client)
        session = (await auth_client.get("/api/queue/session?preview=200")).json()
        assert session["counts"]["ir"] == 0
        assert not any(i["kind"] == "extract" for i in session["items"])

        source = next(s for s in (await auth_client.get("/api/sources")).json()
                       if s["id"] == body["source_id"])
        assert source["for_reading"] is False

    async def test_a_pasted_article_still_surfaces_as_reading_as_before(self, auth_client):
        """The fix must not touch the original Incremental Reading path."""
        resp = await auth_client.post(
            "/api/sources", json={"title": "Pasted", "raw_text": MARKDOWN}
        )
        assert resp.status_code == 201, resp.text
        session = (await auth_client.get("/api/queue/session?preview=200")).json()
        assert session["counts"]["ir"] >= 1
        assert any(i["kind"] == "extract" for i in session["items"])


class TestUpload:
    async def test_upload_creates_a_source_with_located_extracts(self, auth_client):
        body = await _upload(auth_client)
        assert body["title"] == "Monetary Policy"
        assert body["segment_count"] >= 2
        assert "Balance Sheet Recessions" in body["locators"]

        extracts = (
            await auth_client.get(f"/api/sources/{body['source_id']}/extracts")
        ).json()
        assert len(extracts) == body["segment_count"]

    async def test_the_document_lands_in_the_knowledge_tree(self, auth_client):
        body = await _upload(auth_client)
        assert body["node_id"]
        tree = (await auth_client.get("/api/tree")).json()["nodes"]

        def find(nodes):
            for n in nodes:
                if n["id"] == body["node_id"]:
                    return n
                hit = find(n["children"])
                if hit:
                    return hit
            return None

        node = find(tree)
        assert node is not None
        assert node["kind"] == "source"
        assert len(node["children"]) == body["segment_count"]

    async def test_unsupported_upload_is_a_clean_415(self, auth_client):
        resp = await auth_client.post(
            "/api/documents", files={"file": ("thing.zip", io.BytesIO(b"PK"), "application/zip")}
        )
        assert resp.status_code == 415

    async def test_a_scanned_pdf_with_no_text_is_a_clean_422(self, auth_client):
        resp = await auth_client.post(
            "/api/documents", files={"file": ("scan.pdf", io.BytesIO(b"%PDF-1.4 broken"), "application/pdf")}
        )
        assert resp.status_code == 422
        assert "PDF" in resp.json()["detail"] or "text" in resp.json()["detail"]


class TestGeneration:
    async def test_generation_degrades_cleanly_without_consent(self, auth_client):
        """§4.3's promise applies here too: no key/consent is a stated
        fallback, not an error the UI has to special-case."""
        body = await _upload(auth_client)
        resp = await auth_client.post(
            f"/api/documents/{body['source_id']}/generate-deck", json={}
        )
        assert resp.status_code == 200, resp.text
        out = resp.json()
        assert out["degraded"] is True
        assert out["reason"] == "consent_not_given"
        assert out["cards"] == []
        assert out["sections_total"] >= 2


class TestAcceptAndReview:
    async def test_accepted_cards_keep_their_citation_and_show_it_in_review(self, auth_client):
        doc = await _upload(auth_client)
        extracts = (await auth_client.get(f"/api/sources/{doc['source_id']}/extracts")).json()
        cited = next(e for e in extracts if e["locator"] == "Balance Sheet Recessions")

        resp = await auth_client.post(
            f"/api/documents/{doc['source_id']}/accept-deck",
            json={
                "deck": "Macro",
                "cards": [
                    {
                        "kind": "qa",
                        "front": "What replaces profit maximization after a bubble bursts?",
                        "back": "Debt minimization.",
                        "quote": "shifts from profit",
                        "quote_verified": True,
                        "locator": cited["locator"],
                        "extract_id": cited["id"],
                    }
                ],
            },
        )
        assert resp.status_code == 201, resp.text
        out = resp.json()
        assert out["notes_created"] == 1
        assert out["references_created"] == 1

        cards = (await auth_client.get(f"/api/cards?deck_id={out['deck_id']}")).json()
        item = await _queued_card(auth_client, cards[0]["id"])
        refs = item["references"]
        assert len(refs) == 1
        assert refs[0]["quote"] == "shifts from profit"
        assert refs[0]["locator"] == cited["locator"]
        assert refs[0]["source_title"] == "Monetary Policy"
        # The full passage travels too, so the reader can widen the context.
        assert refs[0]["passage"] and "debt minimization" in refs[0]["passage"]

    async def test_an_unverified_quote_is_never_presented_as_one(self, auth_client):
        """A hallucinated citation must degrade to the real passage, not be
        shown as if the model had copied it."""
        doc = await _upload(auth_client)
        extracts = (await auth_client.get(f"/api/sources/{doc['source_id']}/extracts")).json()

        resp = await auth_client.post(
            f"/api/documents/{doc['source_id']}/accept-deck",
            json={
                "deck": "Macro unverified",
                "cards": [
                    {
                        "kind": "qa",
                        "front": "Q",
                        "back": "A",
                        "quote": "a sentence that is not in the document at all",
                        "quote_verified": False,
                        "extract_id": extracts[0]["id"],
                    }
                ],
            },
        )
        assert resp.status_code == 201, resp.text

        cards = (await auth_client.get(f"/api/cards?deck_id={resp.json()['deck_id']}")).json()
        item = await _queued_card(auth_client, cards[0]["id"])
        ref = item["references"][0]
        assert ref["quote"] == "", "an unverified quote must not be surfaced"
        assert ref["quote_verified"] is False
        assert ref["passage"], "but the real passage still is"

    async def test_a_citation_from_another_document_is_refused(self, auth_client):
        """extract_id is caller-supplied; it must be checked against the
        document being accepted into."""
        first = await _upload(auth_client, "first.md")
        second = await _upload(auth_client, "second.md", b"# Other\n\nUnrelated material here.")
        foreign = (await auth_client.get(f"/api/sources/{second['source_id']}/extracts")).json()[0]

        resp = await auth_client.post(
            f"/api/documents/{first['source_id']}/accept-deck",
            json={
                "deck": "Cross doc",
                "cards": [
                    {"kind": "qa", "front": "Q", "back": "A", "extract_id": foreign["id"]}
                ],
            },
        )
        assert resp.status_code == 201, resp.text
        assert any("did not belong" in w for w in resp.json()["warnings"])

    async def test_cards_without_citations_still_work(self, auth_client):
        """Not every accepted card needs a quote — the flow must not require
        one to produce a usable deck."""
        doc = await _upload(auth_client)
        resp = await auth_client.post(
            f"/api/documents/{doc['source_id']}/accept-deck",
            json={"deck": "Plain", "cards": [{"kind": "qa", "front": "Q", "back": "A"}]},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["cards_created"] == 1


class TestTenantIsolation:
    async def test_another_users_document_is_not_reachable(self, client):
        import uuid

        async def register() -> str:
            email = f"doc-{uuid.uuid4().hex[:8]}@example.com"
            resp = await client.post(
                "/api/auth/register", json={"email": email, "password": "hunter2hunter2"}
            )
            return resp.json()["access_token"]

        alice, bob = await register(), await register()

        client.headers["Authorization"] = f"Bearer {alice}"
        doc = await _upload(client)

        client.headers["Authorization"] = f"Bearer {bob}"
        assert (
            await client.post(f"/api/documents/{doc['source_id']}/generate-deck", json={})
        ).status_code == 404
        assert (
            await client.post(
                f"/api/documents/{doc['source_id']}/accept-deck",
                json={"deck": "stolen", "cards": [{"kind": "qa", "front": "Q", "back": "A"}]},
            )
        ).status_code == 404
