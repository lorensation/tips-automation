from app.services.bulk_segmenter import normalize_name, segment_bulk_text

FULL_TEXT = """Buenas, os paso todo:

ANDER GALDONA
1a: 2-1-3
2a: 4-5-1

[11:36] Jose Soto:
1) 5-2-8
2) 1-3-4

fernandez cuesta
2-1-3
4-5-6

JOSE MANUEL FERNANDEZ
1. DUKES. 1-3-2

Hipotour
1: 7-8-9

VILLAVERDE
1-2-3

Romera
3/4/5

Pedro Mercado
6-7-8
"""


def test_segments_all_specialists_with_aliases_accents_and_whatsapp() -> None:
    segmentation = segment_bulk_text(FULL_TEXT)

    names = [block.specialist_name for block in segmentation.blocks]
    assert names == [
        "ANDER GALDONA",
        "JOSÉ SOTO",
        "JAVIER FERNANDEZ-CUESTA",
        "JOSE MANUEL FERNÁNDEZ",
        "HIPOTOUR",
        "EMILIO VILLAVERDE",
        "ESTEBAN ROMERA",
        "PEDRO MERCADO",
    ]
    assert segmentation.missing_specialists == []
    assert segmentation.unassigned_preamble == "Buenas, os paso todo:"
    by_name = {block.specialist_name: block for block in segmentation.blocks}
    assert by_name["JOSÉ SOTO"].raw_block == "1) 5-2-8\n2) 1-3-4"
    assert by_name["ESTEBAN ROMERA"].raw_block == "3/4/5"


def test_fernandez_cuesta_not_confused_with_jose_manuel() -> None:
    segmentation = segment_bulk_text("FERNANDEZ CUESTA\n1-2-3\n\nJOSE MANUEL FERNANDEZ\n4-5-6\n")
    names = [block.specialist_name for block in segmentation.blocks]
    assert names == ["JAVIER FERNANDEZ-CUESTA", "JOSE MANUEL FERNÁNDEZ"]


def test_missing_specialists_reported() -> None:
    segmentation = segment_bulk_text("HIPOTOUR\n1-2-3\n")
    assert "EMILIO VILLAVERDE" in segmentation.missing_specialists
    assert len(segmentation.missing_specialists) == 7


def test_duplicated_specialist_blocks_are_merged() -> None:
    segmentation = segment_bulk_text("HIPOTOUR\n1-2-3\n\nHIPOTOUR\n4-5-6\n")
    assert segmentation.duplicated_specialists == ["HIPOTOUR"]
    assert len(segmentation.blocks) == 1
    assert segmentation.blocks[0].raw_block == "1-2-3\n\n4-5-6"


def test_pick_lines_are_never_headers() -> None:
    # "1-2-3" no debe interpretarse como cabecera aunque contenga texto corto.
    segmentation = segment_bulk_text("ANDER\n1-2-3\n2-3-4\n")
    assert len(segmentation.blocks) == 1
    assert segmentation.blocks[0].raw_block == "1-2-3\n2-3-4"


def test_normalize_name_strips_accents_and_punctuation() -> None:
    assert normalize_name("José  Soto.") == "JOSE SOTO"
    assert normalize_name("FERNÁNDEZ-CUESTA") == "FERNANDEZ CUESTA"
