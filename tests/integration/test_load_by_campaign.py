"""
Integration tests for MediaPlan.load() with campaign_id parameter.

Tests that loading by campaign_id correctly resolves to the current media plan
for that campaign via workspace.list_campaigns().
"""

import pytest
import os
import json
from datetime import date, datetime
from decimal import Decimal

from mediaplanpy.models import MediaPlan, Campaign, LineItem, Meta, TargetAudience
from mediaplanpy.workspace import WorkspaceManager
from mediaplanpy.exceptions import StorageError


@pytest.fixture
def workspace_with_campaign(temp_dir):
    """Create a workspace with a saved media plan for campaign_id lookup tests."""
    config = {
        "workspace_id": "test_load_by_campaign",
        "workspace_name": "Test Load by Campaign",
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

    # Create and save a media plan
    meta = Meta(
        id="MP_LOAD_001",
        schema_version="v3.0",
        name="Test Plan for Campaign Load",
        created_by_name="Test User",
        created_at=datetime(2025, 6, 1, 0, 0, 0),
        is_current=True
    )
    campaign = Campaign(
        id="CAM_LOAD_001",
        name="Campaign for Load Test",
        objective="awareness",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        budget_total=Decimal("50000")
    )
    lineitem = LineItem(
        id="LI_LOAD_001",
        name="Line Item for Load Test",
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


@pytest.fixture
def workspace_with_multiple_plans(temp_dir):
    """Create a workspace with multiple media plans for the same campaign."""
    config = {
        "workspace_id": "test_multi_plan",
        "workspace_name": "Test Multiple Plans",
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

    # Create an older, non-current plan
    meta_old = Meta(
        id="MP_OLD_001",
        schema_version="v3.0",
        name="Old Plan",
        created_by_name="Test User",
        created_at=datetime(2025, 1, 1, 0, 0, 0),
        is_current=False
    )
    campaign_old = Campaign(
        id="CAM_MULTI_001",
        name="Multi-Plan Campaign",
        objective="awareness",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 6, 30),
        budget_total=Decimal("30000")
    )
    lineitem_old = LineItem(
        id="LI_OLD_001",
        name="Old Line Item",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 3, 31),
        cost_total=Decimal("5000"),
        channel="display",
        vehicle="Programmatic",
        partner="DSP Partner"
    )
    old_plan = MediaPlan(meta=meta_old, campaign=campaign_old, lineitems=[lineitem_old])
    old_plan.save(workspace_manager)

    # Create a newer, current plan for the same campaign
    meta_current = Meta(
        id="MP_CURRENT_001",
        schema_version="v3.0",
        name="Current Plan",
        created_by_name="Test User",
        created_at=datetime(2025, 6, 1, 0, 0, 0),
        is_current=True
    )
    campaign_current = Campaign(
        id="CAM_MULTI_001",
        name="Multi-Plan Campaign",
        objective="awareness",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        budget_total=Decimal("60000")
    )
    lineitem_current = LineItem(
        id="LI_CURRENT_001",
        name="Current Line Item",
        start_date=date(2025, 4, 1),
        end_date=date(2025, 6, 30),
        cost_total=Decimal("15000"),
        channel="video",
        vehicle="CTV",
        partner="Streaming Partner"
    )
    current_plan = MediaPlan(meta=meta_current, campaign=campaign_current, lineitems=[lineitem_current])
    current_plan.save(workspace_manager)

    return workspace_manager, old_plan, current_plan


class TestLoadByCampaignId:
    """Test MediaPlan.load() with campaign_id parameter."""

    def test_load_by_campaign_id_resolves_to_current_plan(self, workspace_with_campaign):
        """Test that load(campaign_id=...) resolves to the current media plan."""
        workspace_manager, original_plan = workspace_with_campaign

        loaded = MediaPlan.load(workspace_manager, campaign_id="CAM_LOAD_001")

        assert loaded.meta.id == "MP_LOAD_001"
        assert loaded.campaign.id == "CAM_LOAD_001"
        assert loaded.campaign.name == "Campaign for Load Test"
        assert len(loaded.lineitems) == 1
        assert loaded.lineitems[0].id == "LI_LOAD_001"

    def test_load_by_campaign_id_picks_current_among_multiple(self, workspace_with_multiple_plans):
        """Test that load(campaign_id=...) picks the current plan when multiple exist."""
        workspace_manager, old_plan, current_plan = workspace_with_multiple_plans

        loaded = MediaPlan.load(workspace_manager, campaign_id="CAM_MULTI_001")

        # Should load the current plan, not the old one
        assert loaded.meta.id == "MP_CURRENT_001"
        assert loaded.meta.is_current is True
        assert loaded.campaign.id == "CAM_MULTI_001"
        assert loaded.lineitems[0].id == "LI_CURRENT_001"

    def test_load_by_campaign_id_not_found(self, workspace_with_campaign):
        """Test that load(campaign_id=...) raises StorageError for unknown campaign."""
        workspace_manager, _ = workspace_with_campaign

        with pytest.raises(StorageError, match="not found"):
            MediaPlan.load(workspace_manager, campaign_id="NONEXISTENT_CAM")

    def test_load_by_media_plan_id_still_works(self, workspace_with_campaign):
        """Test that load(media_plan_id=...) continues to work as before."""
        workspace_manager, original_plan = workspace_with_campaign

        loaded = MediaPlan.load(workspace_manager, media_plan_id="MP_LOAD_001")

        assert loaded.meta.id == "MP_LOAD_001"
        assert loaded.campaign.id == "CAM_LOAD_001"
