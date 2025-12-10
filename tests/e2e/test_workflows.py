"""
End-to-end workflow tests for MediaPlanPy v3.0.

Tests complete workflows that span multiple components:
- Create → Save → Load → Query → Export workflow
- Import → Validate → Save → Export workflow
- Workspace upgrade → Query workflow
- Multi-format persistence (JSON + Parquet + Excel)
"""

import pytest
import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal

from mediaplanpy.models import (
    MediaPlan, Campaign, LineItem, Meta,
    TargetAudience, TargetLocation, MetricFormula
)
from mediaplanpy.workspace import WorkspaceManager
from mediaplanpy.excel import export_to_excel, import_from_excel
from mediaplanpy.exceptions import MediaPlanError


class TestFullMediaPlanLifecycle:
    """Test complete media plan lifecycle from creation to querying."""

    def test_create_save_load_query_workflow(self, temp_dir):
        """Test full workflow: Create plan → Save to workspace → Load → Query."""
        # Step 1: Create v3.0 media plan
        meta = Meta(
            id="E2E_MP001",
            schema_version="v3.0",
            name="E2E Test Media Plan",
            created_by_name="E2E Test User",
            created_at=datetime(2025, 1, 1, 0, 0, 0)
        )

        target_audience = TargetAudience(
            name="Adults 25-54",
            description="Core demographic",
            demo_age_start=25,
            demo_age_end=54
        )

        campaign = Campaign(
            id="E2E_CAM001",
            name="E2E Test Campaign",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000"),
            target_audiences=[target_audience]
        )

        lineitem = LineItem(
            id="E2E_LI001",
            name="E2E Test Line Item",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            cost_total=Decimal("10000"),
            channel="display",
            vehicle="Programmatic",
            partner="DSP Partner",
            metric_impressions=Decimal("1000000")
        )

        mediaplan = MediaPlan(meta=meta, campaign=campaign, lineitems=[lineitem])

        # Step 2: Create workspace
        config = {
            "workspace_id": "e2e_test_workspace",
            "workspace_name": "E2E Test Workspace",
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

        # Create mediaplans subdirectory
        mediaplans_dir = os.path.join(temp_dir, "mediaplans")
        os.makedirs(mediaplans_dir, exist_ok=True)

        # Step 3: Save to workspace (creates JSON + Parquet)
        workspace_manager = WorkspaceManager(workspace_path=config_path)
        workspace_manager.load()

        save_path = "mediaplans/e2e_test_plan.json"
        mediaplan.save(workspace_manager, path=save_path)

        # Verify both files created
        json_file = os.path.join(temp_dir, save_path)
        parquet_file = os.path.join(temp_dir, "mediaplans/e2e_test_plan.parquet")

        assert os.path.exists(json_file)
        assert os.path.exists(parquet_file)

        # Step 4: Load from workspace
        loaded_plan = MediaPlan.load(workspace_manager, path=save_path)

        # Verify loaded plan matches original
        assert loaded_plan.meta.id == "E2E_MP001"
        assert loaded_plan.campaign.id == "E2E_CAM001"
        assert len(loaded_plan.lineitems) == 1
        assert loaded_plan.lineitems[0].id == "E2E_LI001"

        # Step 5: Query workspace
        # Query campaigns
        campaigns = workspace_manager.list_campaigns()
        assert len(campaigns) >= 1
        campaign_found = any(c.get("campaign_id") == "E2E_CAM001" for c in campaigns)
        assert campaign_found

        # Query line items
        lineitems = workspace_manager.list_lineitems()
        assert len(lineitems) >= 1
        lineitem_found = any(li.get("lineitem_id") == "E2E_LI001" for li in lineitems)
        assert lineitem_found

        # SQL query
        result = workspace_manager.sql_query(
            "SELECT * FROM {*} WHERE campaign_id = 'E2E_CAM001'"
        )
        assert result is not None

    def test_excel_import_validate_save_export_workflow(self, temp_dir):
        """Test workflow: Import Excel → Validate → Save → Export again."""
        from mediaplanpy.models import MediaPlan, Campaign, Meta

        # Step 1: Create initial media plan
        meta = Meta(
            id="EXCEL_MP001",
            schema_version="v3.0",
            name="Excel Test Plan",
            created_by_name="Test User",
            created_at=datetime(2025, 1, 1, 0, 0, 0)
        )

        campaign = Campaign(
            id="EXCEL_CAM001",
            name="Excel Test Campaign",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000")
        )

        mediaplan = MediaPlan(meta=meta, campaign=campaign, lineitems=[])
        plan_dict = mediaplan.to_dict()

        # Step 2: Export to Excel
        excel_path = os.path.join(temp_dir, "test_export.xlsx")
        export_to_excel(plan_dict, path=excel_path)

        assert os.path.exists(excel_path)

        # Step 3: Import from Excel
        imported_dict = import_from_excel(excel_path)

        # Step 4: Validate imported data
        assert imported_dict["meta"]["id"] == "EXCEL_MP001"
        assert imported_dict["campaign"]["id"] == "EXCEL_CAM001"

        # Step 5: Create MediaPlan object from imported data
        imported_plan = MediaPlan.from_dict(imported_dict)

        # Step 6: Save to workspace
        config = {
            "workspace_id": "excel_workflow_test",
            "workspace_name": "Excel Workflow Test",
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

        mediaplans_dir = os.path.join(temp_dir, "mediaplans")
        os.makedirs(mediaplans_dir, exist_ok=True)

        workspace_manager = WorkspaceManager(workspace_path=config_path)
        workspace_manager.load()

        imported_plan.save(workspace_manager, path="mediaplans/imported_plan.json")

        # Step 7: Export again to verify round-trip
        excel_path2 = os.path.join(temp_dir, "test_re_export.xlsx")
        export_to_excel(imported_plan.to_dict(), path=excel_path2)

        assert os.path.exists(excel_path2)

        # Step 8: Import again and verify consistency
        reimported_dict = import_from_excel(excel_path2)
        assert reimported_dict["meta"]["id"] == "EXCEL_MP001"


class TestWorkspaceUpgradeWorkflow:
    """Test workspace upgrade workflow."""

    def test_v2_workspace_upgrade_and_query(self, temp_dir):
        """Test upgrading v2.0 workspace to v3.0 and querying."""
        from mediaplanpy.workspace.upgrader import WorkspaceUpgrader

        # Step 1: Create v2.0 workspace
        config = {
            "workspace_id": "upgrade_test_ws",
            "workspace_name": "Upgrade Test Workspace",
            "workspace_settings": {
                "schema_version": "2.0"
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

        # Create mediaplans subdirectory
        mediaplans_dir = os.path.join(temp_dir, "mediaplans")
        os.makedirs(mediaplans_dir, exist_ok=True)

        # Step 2: Create v2.0 media plan file
        mediaplan_v2 = {
            "meta": {
                "id": "UPG_MP001",
                "schema_version": "v2.0",
                "name": "v2.0 Media Plan",
                "created_by_name": "Test User",
                "created_at": "2025-01-01T00:00:00Z"
            },
            "campaign": {
                "id": "UPG_CAM001",
                "name": "v2.0 Campaign",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000,
                # v2.0 deprecated fields
                "audience_name": "Adults 25-54",
                "audience_age_start": 25,
                "audience_age_end": 54
            },
            "lineitems": []
        }

        mediaplan_path = os.path.join(mediaplans_dir, "v2_plan.json")
        with open(mediaplan_path, 'w') as f:
            json.dump(mediaplan_v2, f)

        # Step 3: Load workspace in upgrade mode
        workspace_manager = WorkspaceManager(workspace_path=config_path)
        workspace_manager.load(upgrade_mode=True)

        # Step 4: Perform upgrade
        upgrader = WorkspaceUpgrader(workspace_manager)
        result = upgrader.upgrade(dry_run=False)

        # Verify upgrade succeeded
        assert result["workspace_updated"] is True
        assert result["json_files_migrated"] > 0

        # Step 5: Reload workspace in normal mode (should now work)
        workspace_manager = WorkspaceManager(workspace_path=config_path)
        workspace_manager.load()  # No upgrade_mode needed

        # Step 6: Verify workspace is now v3.0
        assert workspace_manager.config["workspace_settings"]["schema_version"] == "3.0"

        # Step 7: Verify migrated file
        with open(mediaplan_path, 'r') as f:
            migrated = json.load(f)

        assert migrated["meta"]["schema_version"] in ["3.0", "v3.0"]
        assert "target_audiences" in migrated["campaign"]
        assert "audience_name" not in migrated["campaign"]

        # Step 8: Query workspace (should work with migrated data)
        campaigns = workspace_manager.list_campaigns()
        assert len(campaigns) >= 1


class TestMultiFormatPersistence:
    """Test persistence across multiple formats."""

    def test_json_parquet_excel_consistency(self, temp_dir):
        """Test that data remains consistent across JSON, Parquet, and Excel formats."""
        from mediaplanpy.models import MediaPlan, Campaign, Meta, LineItem

        # Create test media plan
        meta = Meta(
            id="MULTI_MP001",
            schema_version="v3.0",
            name="Multi-Format Test",
            created_by_name="Test User",
            created_at=datetime(2025, 1, 1, 0, 0, 0),
            dim_custom1="Project: E2E"
        )

        campaign = Campaign(
            id="MULTI_CAM001",
            name="Multi-Format Campaign",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("150000"),
            kpi_name1="CPM",
            kpi_value1=Decimal("15.50")
        )

        lineitem = LineItem(
            id="MULTI_LI001",
            name="Multi-Format Line Item",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            cost_total=Decimal("25000"),
            channel="display",
            vehicle="Programmatic",
            partner="DSP Partner",
            metric_impressions=Decimal("1500000"),
            metric_clicks=Decimal("30000")
        )

        mediaplan = MediaPlan(meta=meta, campaign=campaign, lineitems=[lineitem])

        # Create workspace
        config = {
            "workspace_id": "multi_format_test",
            "workspace_name": "Multi-Format Test Workspace",
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

        mediaplans_dir = os.path.join(temp_dir, "mediaplans")
        os.makedirs(mediaplans_dir, exist_ok=True)

        workspace_manager = WorkspaceManager(workspace_path=config_path)
        workspace_manager.load()

        # Save to workspace (creates JSON + Parquet)
        mediaplan.save(workspace_manager, path="mediaplans/multi_format_plan.json")

        # Export to Excel
        excel_path = os.path.join(temp_dir, "multi_format_plan.xlsx")
        export_to_excel(mediaplan.to_dict(), path=excel_path)

        # Verify all formats exist
        json_path = os.path.join(temp_dir, "mediaplans/multi_format_plan.json")
        parquet_path = os.path.join(temp_dir, "mediaplans/multi_format_plan.parquet")

        assert os.path.exists(json_path)
        assert os.path.exists(parquet_path)
        assert os.path.exists(excel_path)

        # Load from JSON
        loaded_from_json = MediaPlan.load(workspace_manager, path="mediaplans/multi_format_plan.json")

        # Load from Excel
        excel_dict = import_from_excel(excel_path)
        loaded_from_excel = MediaPlan.from_dict(excel_dict)

        # Query from Parquet (via workspace)
        lineitems = workspace_manager.list_lineitems()
        lineitem_from_parquet = [li for li in lineitems if li.get("lineitem_id") == "MULTI_LI001"]

        # Verify consistency across all formats
        # JSON
        assert loaded_from_json.meta.id == "MULTI_MP001"
        assert loaded_from_json.campaign.budget_total == Decimal("150000")
        assert loaded_from_json.lineitems[0].cost_total == Decimal("25000")

        # Excel
        assert loaded_from_excel.meta.id == "MULTI_MP001"
        assert float(loaded_from_excel.campaign.budget_total) == 150000
        assert float(loaded_from_excel.lineitems[0].cost_total) == 25000

        # Parquet (via query)
        assert len(lineitem_from_parquet) == 1
        assert lineitem_from_parquet[0]["lineitem_id"] == "MULTI_LI001"


class TestComplexQueryWorkflow:
    """Test complex querying workflows."""

    def test_multi_plan_aggregation_workflow(self, temp_dir):
        """Test querying and aggregating across multiple media plans."""
        # Create workspace
        config = {
            "workspace_id": "complex_query_test",
            "workspace_name": "Complex Query Test",
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

        mediaplans_dir = os.path.join(temp_dir, "mediaplans")
        os.makedirs(mediaplans_dir, exist_ok=True)

        workspace_manager = WorkspaceManager(workspace_path=config_path)
        workspace_manager.load()

        # Create multiple media plans
        for i in range(1, 4):
            meta = Meta(
                id=f"QUERY_MP{i:03d}",
                schema_version="v3.0",
                name=f"Query Test Plan {i}",
                created_by_name="Test User",
                created_at=datetime(2025, 1, i, 0, 0, 0)
            )

            campaign = Campaign(
                id=f"QUERY_CAM{i:03d}",
                name=f"Query Campaign {i}",
                objective="awareness" if i % 2 == 1 else "conversion",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal(str(100000 * i))
            )

            lineitem = LineItem(
                id=f"QUERY_LI{i:03d}",
                name=f"Query Line Item {i}",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31),
                cost_total=Decimal(str(10000 * i)),
                channel="display",
                vehicle="Programmatic",
                partner="DSP Partner"
            )

            mediaplan = MediaPlan(meta=meta, campaign=campaign, lineitems=[lineitem])
            mediaplan.save(workspace_manager, path=f"mediaplans/query_plan_{i}.json")

        # Query all media plans
        all_mediaplans = workspace_manager.list_mediaplans()
        assert len(all_mediaplans) >= 3

        # Query campaigns by objective
        awareness_result = workspace_manager.sql_query(
            "SELECT * FROM {*} WHERE campaign_objective = 'awareness'"
        )
        assert awareness_result is not None

        # Query line items
        all_lineitems = workspace_manager.list_lineitems()
        assert len(all_lineitems) >= 3

        # Get as DataFrame for analysis
        df = workspace_manager.list_lineitems(return_dataframe=True)
        assert df is not None
        assert len(df) >= 3
        assert "lineitem_cost_total" in df.columns


class TestErrorRecoveryWorkflow:
    """Test error recovery in workflows."""

    def test_save_failure_recovery(self, temp_dir):
        """Test recovering from save failures."""
        from mediaplanpy.models import MediaPlan, Campaign, Meta

        # Create workspace
        config = {
            "workspace_id": "error_recovery_test",
            "workspace_name": "Error Recovery Test",
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

        workspace_manager = WorkspaceManager(workspace_path=config_path)
        workspace_manager.load()

        # Create media plan
        meta = Meta(
            id="ERR_MP001",
            schema_version="v3.0",
            name="Error Test Plan",
            created_by_name="Test User",
            created_at=datetime(2025, 1, 1, 0, 0, 0)
        )

        campaign = Campaign(
            id="ERR_CAM001",
            name="Error Test Campaign",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000")
        )

        mediaplan = MediaPlan(meta=meta, campaign=campaign, lineitems=[])

        # Try to save to invalid path (should fail gracefully)
        try:
            mediaplan.save(workspace_manager, path="/invalid/path/plan.json")
            assert False, "Should have raised an error"
        except Exception:
            # Error expected
            pass

        # Verify workspace is still operational
        mediaplans = workspace_manager.list_mediaplans()
        assert isinstance(mediaplans, list)

        # Now save to valid path (should succeed)
        mediaplans_dir = os.path.join(temp_dir, "mediaplans")
        os.makedirs(mediaplans_dir, exist_ok=True)

        mediaplan.save(workspace_manager, path="mediaplans/recovered_plan.json")

        # Verify save succeeded
        saved_plan = MediaPlan.load(workspace_manager, path="mediaplans/recovered_plan.json")
        assert saved_plan.meta.id == "ERR_MP001"
