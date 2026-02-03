"""Label cleaning: holdings re-derived from the letters, numbers checked, statuses linked, no leakage."""

from __future__ import annotations

from tariffcompass.search import corpus

NY_TEXT = (
    "CLA-2-96:OT:RR:NC:N4:422 Ms. A Example Co. RE: The tariff classification of stainless steel bottles from China "
    "Dear Ms. A: In your letter dated September 23, 2021, you requested a tariff classification ruling. "
    "The bottles are double-walled receptacles of stainless steel with a vacuum between the walls. Each holds 17 "
    "ounces. Heading 9617 provides for vacuum flasks. The applicable subheading for the stainless steel bottles will "
    "be 9617.00.1000, Harmonized Tariff Schedule of the United States (HTSUS), which provides for vacuum flasks."
)
HQ_REVOKES = (
    "OT:RR:CTF:CPMM H303684 CKG Ms. A RE: Revocation of NY N297758 and NY N111111; classification of insulated "
    "stainless steel beverage containers Dear Ms. A: We have reconsidered NY N297758, in which CBP classified "
    "tumblers in subheading 7323.93.0080. FACTS: The tumblers are double-walled stainless steel. ISSUE: Whether. "
    "HOLDING: Pursuant to GRIs 1 and 6, the stainless steel containers at issue are classified in heading 9617, "
    "specifically subheading 9617.00.10, HTSUS."
)
WRONG_LETTER = (
    "MAR-2 OT:RR:NC:N1:135 Mr. B RE: COUNTRY OF ORIGIN MARKING OF IMPORTED HEARING AIDS Dear Mr. B: This is in "
    "response to your letter requesting a ruling on marking hearing aids, made in Denmark and sold in boxes."
)


def row(rid, issued, code, text):
    return {"id": rid, "issued": issued, "code": code, "text": text}


def test_the_holding_gives_the_code_and_the_description_leaks_nothing():
    codes, sentence = corpus.holdings(NY_TEXT)
    assert codes == ["9617001000"] and "will be 9617.00.1000" in sentence
    d = corpus.describe(NY_TEXT, corpus.subject_of(NY_TEXT), "NY")
    assert d.startswith("stainless steel bottles.")
    assert "9617" not in d and "heading" not in d.lower() and "requested" not in d


def test_hq_holdings_are_read_from_the_holding_section():
    codes, _ = corpus.holdings(HQ_REVOKES)
    assert codes == ["96170010"]


def test_an_hq_letter_filed_under_an_ny_number_is_rekeyed_from_its_letterhead():
    out, rep = corpus.clean([row("NY N319947", "2021-07-07", "96170010", HQ_REVOKES)])
    ids = {r.id for r in out}
    assert "HQ H303684" in ids and "NY N319947" not in ids
    assert rep.rekeyed_from_letterhead == 1


def test_a_revocation_never_lands_on_a_different_letter_filed_under_that_number():
    out, rep = corpus.clean(
        [
            row("NY N297758", "2018-07-09", "85394080", WRONG_LETTER),
            row("NY N319947", "2021-07-07", "96170010", HQ_REVOKES),
        ]
    )
    by = {r.id: r for r in out}
    noted = by["NY N297758"]
    assert noted.noted and noted.status == "revoked" and noted.status_by == "HQ H303684"
    assert noted.text.startswith("The letter for NY N297758 is not in the corpus")
    moved = by["NY ?N297758"]
    assert "HEARING AIDS" in moved.subject and not moved.citable and moved.status == "in_force"
    assert by["NY N111111"].noted  # named but absent: noted, never invented
    assert rep.wrong_letter_under_number == 1


def test_labels_require_a_holding_that_agrees_with_the_stated_number():
    agree = row("NY N321134", "2021-12-03", "9617001000", NY_TEXT)
    disagree = row("NY N400000", "2021-12-04", "7323930080", NY_TEXT.replace("N4:422 Ms. A", "N4:422 Ms. C"))
    no_holding = row("NY N400001", "2021-12-05", "9617001000", WRONG_LETTER)
    out, rep = corpus.clean([agree, disagree, no_holding])
    by = {r.id: r for r in out}
    assert by["NY N321134"].labelled and by["NY N321134"].citable
    assert not by["NY N400000"].labelled and not by["NY N400000"].citable
    assert "holding_disagrees_with_mirror" in by["NY N400000"].flags
    assert not by["NY N400001"].labelled and by["NY N400001"].category == "Country of origin or marking"
    assert rep.labelled == 1 and rep.disagree_heading == 1 and rep.no_holding == 1


def test_snapshot_hash_is_order_independent():
    out, _ = corpus.clean([row("NY N321134", "2021-12-03", "9617001000", NY_TEXT)])
    assert corpus.snapshot_hash(out) == corpus.snapshot_hash(list(reversed(out)))
