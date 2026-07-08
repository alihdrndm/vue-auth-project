"""Every rule ID that fires on the corpus `fail` files and the samples is curated (section 7)."""

from pathlib import Path

import tests.tools  # noqa: F401 - puts backend/tools on the import path


def test_curated_rules_cover_every_rule_id_the_collector_finds(corpus: Path) -> None:
    from collect_rule_ids import SAMPLES_DIR, collect, curated_ids  # after tests.tools

    found = collect(corpus, SAMPLES_DIR)
    assert "XSD" in found
    assert "BR-DE-15" in found  # sample S05
    assert sorted(found - curated_ids()) == []
