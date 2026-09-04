"""
Tests for automatic id generation on the JSON import path (v3.0.10).

Before v3.0.10 the JSON importer minted only ``meta.id``, while every other
entry point -- ``MediaPlan.create()``, ``create_lineitem()`` and the Excel
importer -- minted ``campaign.id`` and line item ids as well. The result was
that the same plan imported as Excel succeeded and as JSON failed, on ids the
caller had no reason to invent. These tests pin the parity, and pin the other
half of the rule too: an id that *is* supplied is never touched.
"""
import json
import os
import tempfile

import pytest

from mediaplanpy.models import MediaPlan
from mediaplanpy.models.mediaplan_json import _ensure_entity_ids
from mediaplanpy.schema import get_current_version


def _plan_dict(**overrides):
    """A minimal, schema-valid plan with every id omitted."""
    plan = {
        "meta": {
            "schema_version": f"v{get_current_version()}",
            "created_by_name": "tester@example.com",
            "created_at": "2026-01-01T00:00:00Z",
            "name": "Import Test Plan",
        },
        "campaign": {
            "name": "Import Test Campaign",
            "start_date": "2026-01-01",
            "end_date": "2026-03-31",
            "budget_total": 50000,
        },
        "lineitems": [
            {"name": "Item A", "start_date": "2026-01-01", "end_date": "2026-02-01", "cost_total": 1000},
            {"name": "Item B", "start_date": "2026-02-01", "end_date": "2026-03-01", "cost_total": 2000},
        ],
    }
    plan.update(overrides)
    return plan


def _import(plan):
    """Import a plan dict through the real JSON file path."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_name = "plan.json"
        with open(os.path.join(tmp_dir, file_name), "w", encoding="utf-8") as handle:
            json.dump(plan, handle)
        return MediaPlan.import_from_json(file_path=tmp_dir, file_name=file_name)


# ---------------------------------------------------------------------------
# _ensure_entity_ids in isolation
# ---------------------------------------------------------------------------

def test_mints_all_three_kinds_of_id_when_absent():
    data = _plan_dict()

    _ensure_entity_ids(data)

    assert data["meta"]["id"].startswith("mediaplan_")
    assert data["campaign"]["id"].startswith("campaign_")
    assert all(item["id"].startswith("pli_") for item in data["lineitems"])


def test_minted_ids_are_unique_per_line_item():
    data = _plan_dict()

    _ensure_entity_ids(data)

    ids = [item["id"] for item in data["lineitems"]]
    assert len(set(ids)) == len(ids)


def test_supplied_ids_are_preserved_exactly():
    """
    The round-trip guarantee: export -> edit -> re-import must not silently
    re-identify a plan. This is what keeps the fix safe.
    """
    data = _plan_dict()
    data["meta"]["id"] = "mediaplan_keepme"
    data["campaign"]["id"] = "campaign_keepme"
    data["lineitems"][0]["id"] = "pli_keepme"

    _ensure_entity_ids(data)

    assert data["meta"]["id"] == "mediaplan_keepme"
    assert data["campaign"]["id"] == "campaign_keepme"
    assert data["lineitems"][0]["id"] == "pli_keepme"
    # The one that was missing still gets minted.
    assert data["lineitems"][1]["id"].startswith("pli_")


def test_empty_string_id_is_treated_as_missing():
    data = _plan_dict()
    data["campaign"]["id"] = ""

    _ensure_entity_ids(data)

    assert data["campaign"]["id"].startswith("campaign_")


def test_missing_campaign_block_is_left_alone():
    """
    A plan with no campaign at all is a schema violation, and the validator
    should say so. Inventing a campaign that holds nothing but an id would
    turn a clear error into a confusing one.
    """
    data = _plan_dict()
    del data["campaign"]

    _ensure_entity_ids(data)

    assert "campaign" not in data


def test_missing_lineitems_key_is_tolerated():
    data = _plan_dict()
    del data["lineitems"]

    _ensure_entity_ids(data)  # must not raise

    assert "lineitems" not in data


def test_empty_lineitems_list_is_tolerated():
    """A campaign-only plan -- the shape you get before any line items exist."""
    data = _plan_dict(lineitems=[])

    _ensure_entity_ids(data)

    assert data["lineitems"] == []
    assert data["campaign"]["id"].startswith("campaign_")


def test_legacy_alias_still_resolves():
    """_ensure_meta_id was the public-ish name before v3.0.10."""
    from mediaplanpy.models.mediaplan_json import _ensure_meta_id

    assert _ensure_meta_id is _ensure_entity_ids


# ---------------------------------------------------------------------------
# End to end, through import_from_json
# ---------------------------------------------------------------------------

def test_plan_with_no_ids_imports_successfully():
    """The regression: this raised for a missing campaign.id before v3.0.10."""
    media_plan = _import(_plan_dict())

    assert media_plan.meta.id.startswith("mediaplan_")
    assert media_plan.campaign.id.startswith("campaign_")
    assert len(media_plan.lineitems) == 2
    assert all(item.id.startswith("pli_") for item in media_plan.lineitems)


def test_import_preserves_supplied_ids():
    plan = _plan_dict()
    plan["meta"]["id"] = "mediaplan_fixed01"
    plan["campaign"]["id"] = "campaign_fixed01"
    plan["lineitems"][0]["id"] = "pli_fixed01"
    plan["lineitems"][1]["id"] = "pli_fixed02"

    media_plan = _import(plan)

    assert media_plan.meta.id == "mediaplan_fixed01"
    assert media_plan.campaign.id == "campaign_fixed01"
    assert [item.id for item in media_plan.lineitems] == ["pli_fixed01", "pli_fixed02"]


def test_generated_example_imports_without_modification():
    """
    Ties the two halves of this release together: the example the SDK hands an
    agent must be importable exactly as given, with nothing to fill in.
    """
    from mediaplanpy.schema import get_example

    example = json.loads(json.dumps(get_example(), default=str))
    media_plan = _import(example)

    assert media_plan.campaign.id
    assert len(media_plan.lineitems) >= 1


def test_example_stripped_of_every_id_still_imports():
    """The authoring case: an agent writes the content and omits all ids."""
    from mediaplanpy.schema import get_example

    example = json.loads(json.dumps(get_example(), default=str))
    example["meta"].pop("id", None)
    example["campaign"].pop("id", None)
    for item in example["lineitems"]:
        item.pop("id", None)

    media_plan = _import(example)

    assert media_plan.meta.id.startswith("mediaplan_")
    assert media_plan.campaign.id.startswith("campaign_")
    assert all(item.id.startswith("pli_") for item in media_plan.lineitems)
