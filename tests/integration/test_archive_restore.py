"""
Integration tests for MediaPlan.archive()/restore()/set_as_current() with the
allow_current override (v3.0.5).

Archiving a campaign is implemented client-side as a loop over the campaign's
plans, including the current one. archive(allow_current=True) unblocks that
loop by allowing the current plan to be archived while preserving is_current,
so restore() reinstates it as current with no re-election step.
"""

import pytest
import os
import json
from datetime import date, datetime
from decimal import Decimal

from mediaplanpy.models import MediaPlan, Campaign, LineItem, Meta
from mediaplanpy.workspace import WorkspaceManager
from mediaplanpy.exceptions import ValidationError, StorageError
from mediaplanpy.schema import SchemaValidator


@pytest.fixture
def workspace_with_current_plan(temp_dir):
    """Create a workspace with a single current media plan for a campaign."""
    config = {
        "workspace_id": "test_archive_restore",
        "workspace_name": "Test Archive Restore",
        "workspace_settings": {
            "schema_version": "3.0"
        },
        "storage": {
            "mode": "local",
            "local": {
                "base_path": temp_dir
            }
        },
        "database": {
            "enabled": False
        }
    }

    config_path = os.path.join(temp_dir, "workspace.json")
    with open(config_path, 'w') as f:
        json.dump(config, f)

    os.makedirs(os.path.join(temp_dir, "mediaplans"), exist_ok=True)

    workspace_manager = WorkspaceManager(workspace_path=config_path)
    workspace_manager.load()

    meta = Meta(
        id="MP_ARCH_001",
        schema_version="v3.0",
        name="Plan to Archive",
        created_by_name="Test User",
        created_at=datetime(2025, 1, 1, 0, 0, 0),
        is_current=True
    )
    campaign = Campaign(
        id="CAM_ARCH_001",
        name="Campaign for Archive Test",
        objective="awareness",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        budget_total=Decimal("50000")
    )
    lineitem = LineItem(
        id="LI_ARCH_001",
        name="Line Item for Archive Test",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 3, 31),
        cost_total=Decimal("10000"),
        channel="display",
        vehicle="Programmatic",
        partner="DSP Partner"
    )

    mediaplan = MediaPlan(meta=meta, campaign=campaign, lineitems=[lineitem])
    mediaplan.save(workspace_manager)

    return workspace_manager, mediaplan


class TestArchiveAllowCurrent:
    """Test archive()'s allow_current override."""

    def test_archive_current_plan_default_raises(self, workspace_with_current_plan):
        """archive() with no override still raises for a current plan (unchanged)."""
        workspace_manager, plan = workspace_with_current_plan

        with pytest.raises(ValidationError, match="it is marked as current"):
            plan.archive(workspace_manager)

        # Nothing should have changed
        assert plan.meta.is_archived is not True

    def test_archive_current_plan_with_allow_current_succeeds(self, workspace_with_current_plan):
        """archive(allow_current=True) archives a current plan, preserving is_current."""
        workspace_manager, plan = workspace_with_current_plan

        plan.archive(workspace_manager, allow_current=True)

        assert plan.meta.is_archived is True
        assert plan.meta.is_current is True

        # Persisted state matches
        reloaded = MediaPlan.load(workspace_manager, media_plan_id="MP_ARCH_001")
        assert reloaded.meta.is_archived is True
        assert reloaded.meta.is_current is True

    def test_archive_non_current_plan_allow_current_identical_to_default(self, temp_dir, workspace_with_current_plan):
        """archive(allow_current=True) on a non-current plan behaves like archive()."""
        workspace_manager, _ = workspace_with_current_plan

        meta = Meta(
            id="MP_ARCH_002",
            schema_version="v3.0",
            name="Non-current plan",
            created_by_name="Test User",
            created_at=datetime(2025, 1, 1, 0, 0, 0),
            is_current=False
        )
        campaign = Campaign(
            id="CAM_ARCH_001",
            name="Campaign for Archive Test",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("50000")
        )
        lineitem = LineItem(
            id="LI_ARCH_002",
            name="Line Item",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            cost_total=Decimal("5000"),
            channel="display",
            vehicle="Programmatic",
            partner="DSP Partner"
        )
        plan = MediaPlan(meta=meta, campaign=campaign, lineitems=[lineitem])
        plan.save(workspace_manager)

        plan.archive(workspace_manager, allow_current=True)

        assert plan.meta.is_archived is True
        assert plan.meta.is_current is False

    def test_restore_reinstates_current_with_no_reelection(self, workspace_with_current_plan):
        """Round-trip archive(allow_current=True) -> restore() keeps is_current, no re-election."""
        workspace_manager, plan = workspace_with_current_plan

        plan.archive(workspace_manager, allow_current=True)
        assert plan.meta.is_current is True
        assert plan.meta.is_archived is True

        plan.restore(workspace_manager)

        assert plan.meta.is_archived is False
        assert plan.meta.is_current is True

        reloaded = MediaPlan.load(workspace_manager, media_plan_id="MP_ARCH_001")
        assert reloaded.meta.is_current is True
        assert reloaded.meta.is_archived is False

    def test_load_by_campaign_id_resolves_archived_current_plan(self, workspace_with_current_plan):
        """
        MediaPlan.load(campaign_id=...) still resolves the current plan of a campaign
        whose current (and only) plan has been archived via allow_current=True.

        This behavior is load-bearing for the campaign-archive-cascade UI flow, which
        must be able to view/restore an archived campaign by campaign_id. Pinned here
        so a future change to list_campaigns()/load() doesn't silently break it.
        """
        workspace_manager, plan = workspace_with_current_plan

        plan.archive(workspace_manager, allow_current=True)

        loaded = MediaPlan.load(workspace_manager, campaign_id="CAM_ARCH_001")

        assert loaded.meta.id == "MP_ARCH_001"
        assert loaded.meta.is_current is True
        assert loaded.meta.is_archived is True

    def test_set_as_current_still_refuses_archived_plan(self, workspace_with_current_plan):
        """set_as_current() keeps refusing an archived plan (unchanged guard)."""
        workspace_manager, plan = workspace_with_current_plan

        plan.archive(workspace_manager, allow_current=True)

        with pytest.raises(ValidationError, match="Cannot set archived media plan"):
            plan.set_as_current(workspace_manager)

    def test_current_and_archived_passes_model_and_schema_validation(self):
        """A plan with is_current=True, is_archived=True passes both validators."""
        meta = Meta(
            id="MP_VALID_001",
            schema_version="v3.0",
            name="Plan",
            created_by_name="Test User",
            created_at=datetime(2025, 1, 1, 0, 0, 0),
            is_current=True,
            is_archived=True
        )
        assert meta.validate_model() == []

        validator = SchemaValidator()
        errors = validator._validate_meta_v2_consistency({
            "id": "MP_VALID_001",
            "is_current": True,
            "is_archived": True
        })
        assert errors == []

    def test_current_and_archived_survives_save_load_save_cycle(self, temp_dir):
        """A plan with is_current=True, is_archived=True round-trips through storage."""
        config = {
            "workspace_id": "test_archive_roundtrip",
            "workspace_name": "Test Archive Roundtrip",
            "workspace_settings": {"schema_version": "3.0"},
            "storage": {"mode": "local", "local": {"base_path": temp_dir}},
            "database": {"enabled": False}
        }
        config_path = os.path.join(temp_dir, "workspace.json")
        with open(config_path, 'w') as f:
            json.dump(config, f)
        os.makedirs(os.path.join(temp_dir, "mediaplans"), exist_ok=True)

        workspace_manager = WorkspaceManager(workspace_path=config_path)
        workspace_manager.load()

        meta = Meta(
            id="MP_ROUNDTRIP_001",
            schema_version="v3.0",
            name="Plan",
            created_by_name="Test User",
            created_at=datetime(2025, 1, 1, 0, 0, 0),
            is_current=True,
            is_archived=True
        )
        campaign = Campaign(
            id="CAM_ROUNDTRIP_001",
            name="Campaign",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("50000")
        )
        lineitem = LineItem(
            id="LI_ROUNDTRIP_001",
            name="Line Item",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            cost_total=Decimal("10000"),
            channel="display",
            vehicle="Programmatic",
            partner="DSP Partner"
        )
        plan = MediaPlan(meta=meta, campaign=campaign, lineitems=[lineitem])
        plan.save(workspace_manager)

        loaded = MediaPlan.load(workspace_manager, media_plan_id="MP_ROUNDTRIP_001")
        assert loaded.meta.is_current is True
        assert loaded.meta.is_archived is True

        # Save again to confirm the round-tripped state still saves cleanly
        loaded.save(workspace_manager, overwrite=True)
        assert loaded.validate_against_schema() == []
