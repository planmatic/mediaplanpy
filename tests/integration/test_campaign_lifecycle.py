"""
Integration tests for WorkspaceManager.archive_campaign()/restore_campaign()/
delete_campaign() (v3.0.11).

These operate on a real local-storage workspace rather than mocks, because the
behaviour under test is precisely how list_campaigns() responds to plan-level
archive state -- a campaign's "archived" state is derived from its plans, not
stored, so nothing meaningful is exercised without real query round-trips.
"""

import pytest
import os
import json
from datetime import date, datetime
from decimal import Decimal

from mediaplanpy.models import MediaPlan, Campaign, LineItem, Meta
from mediaplanpy.workspace import WorkspaceManager
from mediaplanpy.exceptions import CampaignNotFoundError


CAMPAIGN_A = "CAM_LIFECYCLE_A"
CAMPAIGN_B = "CAM_LIFECYCLE_B"


def _make_plan(plan_id, campaign_id, campaign_name, is_current=False, is_archived=False):
    """One saveable MediaPlan. Line item present so query rows are realistic."""
    return MediaPlan(
        meta=Meta(
            id=plan_id,
            schema_version="v3.0",
            name=f"Plan {plan_id}",
            created_by_name="Test User",
            created_at=datetime(2025, 1, 1, 0, 0, 0),
            is_current=is_current,
            is_archived=is_archived,
        ),
        campaign=Campaign(
            id=campaign_id,
            name=campaign_name,
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("50000"),
        ),
        lineitems=[
            LineItem(
                id=f"LI_{plan_id}",
                name=f"Line Item {plan_id}",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31),
                cost_total=Decimal("10000"),
                channel="display",
                vehicle="Programmatic",
                partner="DSP Partner",
            )
        ],
    )


@pytest.fixture
def workspace_with_campaigns(temp_dir):
    """
    A workspace holding two campaigns:
      CAMPAIGN_A -- three plans, one of them current
      CAMPAIGN_B -- one plan, current (the control: must never be touched)
    """
    config = {
        "workspace_id": "test_campaign_lifecycle",
        "workspace_name": "Test Campaign Lifecycle",
        "workspace_settings": {"schema_version": "3.0"},
        "storage": {"mode": "local", "local": {"base_path": temp_dir}},
        "database": {"enabled": False},
    }
    config_path = os.path.join(temp_dir, "workspace.json")
    with open(config_path, "w") as f:
        json.dump(config, f)
    os.makedirs(os.path.join(temp_dir, "mediaplans"), exist_ok=True)

    manager = WorkspaceManager(workspace_path=config_path)
    manager.load()

    for plan in (
        _make_plan("MP_A1", CAMPAIGN_A, "Campaign A", is_current=True),
        _make_plan("MP_A2", CAMPAIGN_A, "Campaign A"),
        _make_plan("MP_A3", CAMPAIGN_A, "Campaign A"),
        _make_plan("MP_B1", CAMPAIGN_B, "Campaign B", is_current=True),
    ):
        plan.save(manager)

    return manager


def _campaign_ids(manager, include_archived=False):
    rows = manager.list_campaigns(
        include_stats=False, include_archived=include_archived, return_dataframe=False
    )
    return {row["campaign_id"] for row in rows}


def _plan_row(manager, plan_id):
    rows = manager.list_mediaplans(
        filters={"meta_id": plan_id}, include_stats=False,
        include_archived=True, return_dataframe=False,
    )
    assert rows, f"plan {plan_id} not found"
    return rows[0]


# ---------------------------------------------------------------------------
# archive_campaign
# ---------------------------------------------------------------------------

class TestArchiveCampaign:

    def test_archives_every_plan_and_hides_the_campaign(self, workspace_with_campaigns):
        manager = workspace_with_campaigns
        assert CAMPAIGN_A in _campaign_ids(manager)

        result = manager.archive_campaign(CAMPAIGN_A)

        assert result["success"] is True
        assert result["plans_total"] == 3
        assert set(result["plans_changed"]) == {"MP_A1", "MP_A2", "MP_A3"}
        assert result["plans_skipped"] == []
        assert result["plans_failed"] == []
        assert result["campaign_now_hidden"] is True

        # The campaign is gone from the default listing but still reachable.
        assert CAMPAIGN_A not in _campaign_ids(manager)
        assert CAMPAIGN_A in _campaign_ids(manager, include_archived=True)

    def test_current_plan_is_archived_but_stays_current(self, workspace_with_campaigns):
        """
        allow_current=True preserves is_current rather than clearing it, so a
        later restore reinstates the same plan with no re-election. This is the
        specific behaviour mediaplanpy 3.0.5 added for campaign cascades.
        """
        manager = workspace_with_campaigns
        manager.archive_campaign(CAMPAIGN_A)

        row = _plan_row(manager, "MP_A1")
        assert row["meta_is_archived"] is True
        assert row["meta_is_current"] is True

    def test_leaves_other_campaigns_untouched(self, workspace_with_campaigns):
        manager = workspace_with_campaigns
        manager.archive_campaign(CAMPAIGN_A)

        assert CAMPAIGN_B in _campaign_ids(manager)
        assert _plan_row(manager, "MP_B1")["meta_is_archived"] is not True

    def test_is_idempotent(self, workspace_with_campaigns):
        """Re-running after a partial failure must be safe, so a second call
        skips rather than erroring."""
        manager = workspace_with_campaigns
        manager.archive_campaign(CAMPAIGN_A)

        result = manager.archive_campaign(CAMPAIGN_A)

        assert result["success"] is True
        assert result["plans_changed"] == []
        assert len(result["plans_skipped"]) == 3
        assert all(s["reason"] == "already_archived" for s in result["plans_skipped"])

    def test_mixed_state_skips_only_the_archived_plan(self, workspace_with_campaigns):
        manager = workspace_with_campaigns
        MediaPlan.load(manager, media_plan_id="MP_A2").archive(manager)

        result = manager.archive_campaign(CAMPAIGN_A)

        assert result["success"] is True
        assert set(result["plans_changed"]) == {"MP_A1", "MP_A3"}
        assert [s["media_plan_id"] for s in result["plans_skipped"]] == ["MP_A2"]

    def test_unknown_campaign_raises(self, workspace_with_campaigns):
        with pytest.raises(CampaignNotFoundError):
            workspace_with_campaigns.archive_campaign("CAM_DOES_NOT_EXIST")

    def test_blank_campaign_id_raises(self, workspace_with_campaigns):
        with pytest.raises(CampaignNotFoundError):
            workspace_with_campaigns.archive_campaign("   ")

    def test_partial_failure_still_processes_the_other_plans(
        self, workspace_with_campaigns, monkeypatch
    ):
        """One plan failing must not strand the rest, and must be reported."""
        manager = workspace_with_campaigns
        real_archive = MediaPlan.archive

        def flaky_archive(self, workspace_manager, allow_current=False):
            if self.meta.id == "MP_A2":
                raise RuntimeError("simulated storage failure")
            return real_archive(self, workspace_manager, allow_current=allow_current)

        monkeypatch.setattr(MediaPlan, "archive", flaky_archive)
        result = manager.archive_campaign(CAMPAIGN_A)

        assert result["success"] is False
        assert set(result["plans_changed"]) == {"MP_A1", "MP_A3"}
        assert [f["media_plan_id"] for f in result["plans_failed"]] == ["MP_A2"]
        assert "simulated storage failure" in result["plans_failed"][0]["error"]
        # Not every plan is archived, so the campaign is still visible -- and the
        # result must not claim otherwise.
        assert result["campaign_now_hidden"] is False


# ---------------------------------------------------------------------------
# restore_campaign
# ---------------------------------------------------------------------------

class TestRestoreCampaign:

    def test_round_trip_restores_the_campaign_and_its_current_plan(
        self, workspace_with_campaigns
    ):
        manager = workspace_with_campaigns
        manager.archive_campaign(CAMPAIGN_A)

        result = manager.restore_campaign(CAMPAIGN_A)

        assert result["success"] is True
        assert set(result["plans_changed"]) == {"MP_A1", "MP_A2", "MP_A3"}
        assert result["campaign_now_visible"] is True
        assert CAMPAIGN_A in _campaign_ids(manager)

        row = _plan_row(manager, "MP_A1")
        assert row["meta_is_archived"] is not True
        assert row["meta_is_current"] is True   # no re-election needed

    def test_restores_plans_archived_individually_beforehand(
        self, workspace_with_campaigns
    ):
        """
        DEC-1, made explicit: restore un-archives EVERY archived plan, including
        one a user archived on its own before the campaign was archived. Nothing
        records why a plan was archived, so this loss is accepted and documented
        rather than silently unnoticed -- this test pins the behaviour so a future
        change to it is a deliberate one.
        """
        manager = workspace_with_campaigns
        MediaPlan.load(manager, media_plan_id="MP_A2").archive(manager)
        manager.archive_campaign(CAMPAIGN_A)

        result = manager.restore_campaign(CAMPAIGN_A)

        assert "MP_A2" in result["plans_changed"]
        assert _plan_row(manager, "MP_A2")["meta_is_archived"] is not True

    def test_skips_plans_that_are_not_archived(self, workspace_with_campaigns):
        manager = workspace_with_campaigns
        result = manager.restore_campaign(CAMPAIGN_A)

        assert result["success"] is True
        assert result["plans_changed"] == []
        assert len(result["plans_skipped"]) == 3
        assert all(s["reason"] == "not_archived" for s in result["plans_skipped"])

    def test_unknown_campaign_raises(self, workspace_with_campaigns):
        with pytest.raises(CampaignNotFoundError):
            workspace_with_campaigns.restore_campaign("CAM_DOES_NOT_EXIST")


# ---------------------------------------------------------------------------
# delete_campaign
# ---------------------------------------------------------------------------

class TestDeleteCampaign:

    def test_dry_run_is_the_default_and_removes_nothing(self, workspace_with_campaigns):
        """
        The default differs from MediaPlan.delete()'s dry_run=False on purpose. If
        this ever flips, a caller who wrote delete_campaign(id) expecting a preview
        destroys the campaign instead -- hence a test on the default itself, not
        just on dry_run=True.
        """
        manager = workspace_with_campaigns

        result = manager.delete_campaign(CAMPAIGN_A)

        assert result["dry_run"] is True
        assert result["campaign_deleted"] is False
        assert result["files_deleted"] == 0
        assert result["files_found"] > 0
        assert CAMPAIGN_A in _campaign_ids(manager)

    def test_dry_run_lists_the_plans_it_would_delete(self, workspace_with_campaigns):
        """A preview reporting only a count is not reviewable."""
        result = workspace_with_campaigns.delete_campaign(CAMPAIGN_A)
        assert set(result["plans_to_delete"]) == {"MP_A1", "MP_A2", "MP_A3"}

    def test_real_delete_removes_the_campaign_entirely(self, workspace_with_campaigns):
        manager = workspace_with_campaigns

        result = manager.delete_campaign(CAMPAIGN_A, dry_run=False)

        assert result["success"] is True
        assert result["campaign_deleted"] is True
        assert set(result["plans_changed"]) == {"MP_A1", "MP_A2", "MP_A3"}
        assert result["files_deleted"] > 0

        # Gone from both listings -- a deleted campaign is not an archived one.
        assert CAMPAIGN_A not in _campaign_ids(manager)
        assert CAMPAIGN_A not in _campaign_ids(manager, include_archived=True)

    def test_deletes_archived_plans_too(self, workspace_with_campaigns):
        manager = workspace_with_campaigns
        manager.archive_campaign(CAMPAIGN_A)

        result = manager.delete_campaign(CAMPAIGN_A, dry_run=False)

        assert result["success"] is True
        assert CAMPAIGN_A not in _campaign_ids(manager, include_archived=True)

    def test_leaves_other_campaigns_untouched(self, workspace_with_campaigns):
        manager = workspace_with_campaigns
        manager.delete_campaign(CAMPAIGN_A, dry_run=False)

        assert CAMPAIGN_B in _campaign_ids(manager)

    def test_deletes_the_current_plan_without_an_override(self, workspace_with_campaigns):
        """
        There is deliberately no allow_current_plan_deletion here: a campaign
        cannot be deleted while keeping its current plan.
        """
        manager = workspace_with_campaigns
        result = manager.delete_campaign(CAMPAIGN_A, dry_run=False)
        assert "MP_A1" in result["plans_changed"]

    def test_unknown_campaign_raises(self, workspace_with_campaigns):
        with pytest.raises(CampaignNotFoundError):
            workspace_with_campaigns.delete_campaign("CAM_DOES_NOT_EXIST")

    def test_per_file_errors_count_as_failure_not_success(
        self, workspace_with_campaigns, monkeypatch
    ):
        """
        MediaPlan.delete() collects per-file errors into its result instead of
        raising, so a plan can report errors without an exception ever reaching
        the cascade. Those must not be counted as changed.
        """
        manager = workspace_with_campaigns
        real_delete = MediaPlan.delete

        def flaky_delete(self, workspace_manager, dry_run=False, include_database=True):
            result = real_delete(self, workspace_manager, dry_run=dry_run,
                                 include_database=include_database)
            if self.meta.id == "MP_A3":
                result["errors"].append("simulated per-file failure")
            return result

        monkeypatch.setattr(MediaPlan, "delete", flaky_delete)
        result = manager.delete_campaign(CAMPAIGN_A, dry_run=False)

        assert result["success"] is False
        assert "MP_A3" not in result["plans_changed"]
        assert [f["media_plan_id"] for f in result["plans_failed"]] == ["MP_A3"]
        assert result["campaign_deleted"] is False
