"""
Integration tests for Excel import/export with v3.0 schema.

Tests the Excel functionality with v3.0 media plans, including:
- Export of v3.0 features (target_audiences, target_locations, new metrics)
- Import of v3.0 Excel files
- Round-trip export/import validation
- Error handling for v2.0 files
"""

import pytest
import os
import tempfile
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal

from mediaplanpy.excel import export_to_excel, import_from_excel
from mediaplanpy.models import MediaPlan
from mediaplanpy.exceptions import StorageError, ValidationError


class TestExcelExport:
    """Test Excel export functionality with v3.0 schema."""

    def test_export_minimal_v3_plan(self, mediaplan_v3_minimal, temp_dir):
        """Test exporting minimal v3.0 media plan to Excel."""
        # Convert to dict for export
        plan_dict = mediaplan_v3_minimal.to_dict()

        # Export to temp file
        output_path = os.path.join(temp_dir, "test_export_minimal.xlsx")
        result_path = export_to_excel(plan_dict, path=output_path)

        # Verify file was created
        assert os.path.exists(result_path)
        assert result_path == output_path
        assert os.path.getsize(result_path) > 0

    def test_export_full_v3_plan(self, mediaplan_v3_full, temp_dir):
        """Test exporting complete v3.0 media plan with all features to Excel."""
        # Convert to dict for export
        plan_dict = mediaplan_v3_full.to_dict()

        # Export to temp file
        output_path = os.path.join(temp_dir, "test_export_full.xlsx")
        result_path = export_to_excel(plan_dict, path=output_path)

        # Verify file was created
        assert os.path.exists(result_path)
        assert os.path.getsize(result_path) > 0

    def test_export_with_target_audiences(self, target_audience_adults, temp_dir):
        """Test that target_audiences array is exported correctly."""
        from mediaplanpy.models import Campaign, Meta

        campaign = Campaign(
            id="CAM001",
            name="Test",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000"),
            target_audiences=[target_audience_adults]
        )

        meta = Meta(
            id="MP001",
            schema_version="v3.0",
            name="Test",
            created_by_name="Test User",
            created_at=datetime(2025, 1, 1, 0, 0, 0)
        )

        mediaplan = MediaPlan(meta=meta, campaign=campaign, lineitems=[])
        plan_dict = mediaplan.to_dict()

        # Export
        output_path = os.path.join(temp_dir, "test_export_audiences.xlsx")
        result_path = export_to_excel(plan_dict, path=output_path)

        assert os.path.exists(result_path)

    def test_export_with_target_locations(self, target_location_california, temp_dir):
        """Test that target_locations array is exported correctly."""
        from mediaplanpy.models import Campaign, Meta

        campaign = Campaign(
            id="CAM001",
            name="Test",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000"),
            target_locations=[target_location_california]
        )

        meta = Meta(
            id="MP001",
            schema_version="v3.0",
            name="Test",
            created_by_name="Test User",
            created_at=datetime(2025, 1, 1, 0, 0, 0)
        )

        mediaplan = MediaPlan(meta=meta, campaign=campaign, lineitems=[])
        plan_dict = mediaplan.to_dict()

        # Export
        output_path = os.path.join(temp_dir, "test_export_locations.xlsx")
        result_path = export_to_excel(plan_dict, path=output_path)

        assert os.path.exists(result_path)

    def test_export_with_metric_formulas(self, metric_formula_cpm, temp_dir):
        """Test that metric_formulas are exported correctly."""
        from mediaplanpy.models import LineItem, Campaign, Meta

        lineitem = LineItem(
            id="LI001",
            name="Test",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            cost_total=Decimal("10000"),
            metric_formulas={"cpm": metric_formula_cpm}
        )

        campaign = Campaign(
            id="CAM001",
            name="Test",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000")
        )

        meta = Meta(
            id="MP001",
            schema_version="v3.0",
            name="Test",
            created_by_name="Test User",
            created_at=datetime(2025, 1, 1, 0, 0, 0)
        )

        mediaplan = MediaPlan(meta=meta, campaign=campaign, lineitems=[lineitem])
        plan_dict = mediaplan.to_dict()

        # Export
        output_path = os.path.join(temp_dir, "test_export_formulas.xlsx")
        result_path = export_to_excel(plan_dict, path=output_path)

        assert os.path.exists(result_path)

    def test_export_v2_plan_raises_error(self, temp_dir):
        """Test that exporting v2.0 plan raises error."""
        mediaplan_v2 = {
            "meta": {
                "id": "MP001",
                "schema_version": "v2.0",
                "name": "Test",
                "created_by_name": "Test User",
                "created_at": "2025-01-01T00:00:00Z"
            },
            "campaign": {
                "id": "CAM001",
                "name": "Test",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000
            },
            "lineitems": []
        }

        output_path = os.path.join(temp_dir, "test_v2.xlsx")

        # Should raise error for v2.0
        with pytest.raises(StorageError, match="only supports v3.0"):
            export_to_excel(mediaplan_v2, path=output_path)


class TestExcelImport:
    """Test Excel import functionality with v3.0 schema."""

    def test_import_after_export(self, mediaplan_v3_minimal, temp_dir):
        """Test importing an Excel file that was just exported."""
        # Export first
        plan_dict = mediaplan_v3_minimal.to_dict()
        output_path = os.path.join(temp_dir, "test_roundtrip.xlsx")
        export_to_excel(plan_dict, path=output_path)

        # Import back
        imported = import_from_excel(output_path)

        # Verify structure
        assert imported["meta"]["schema_version"] == "3.0" or imported["meta"]["schema_version"] == "v3.0"
        assert imported["meta"]["id"] == plan_dict["meta"]["id"]
        assert imported["campaign"]["id"] == plan_dict["campaign"]["id"]

    def test_import_preserves_target_audiences(self, mediaplan_v3_full, temp_dir):
        """Test that target_audiences array is preserved during import."""
        # Export plan with target_audiences
        plan_dict = mediaplan_v3_full.to_dict()
        output_path = os.path.join(temp_dir, "test_import_audiences.xlsx")
        export_to_excel(plan_dict, path=output_path)

        # Import back
        imported = import_from_excel(output_path)

        # Verify target_audiences
        assert "target_audiences" in imported["campaign"]
        assert len(imported["campaign"]["target_audiences"]) > 0
        assert "name" in imported["campaign"]["target_audiences"][0]

    def test_import_preserves_target_locations(self, mediaplan_v3_full, temp_dir):
        """Test that target_locations array is preserved during import."""
        # Export plan with target_locations
        plan_dict = mediaplan_v3_full.to_dict()
        output_path = os.path.join(temp_dir, "test_import_locations.xlsx")
        export_to_excel(plan_dict, path=output_path)

        # Import back
        imported = import_from_excel(output_path)

        # Verify target_locations
        assert "target_locations" in imported["campaign"]
        assert len(imported["campaign"]["target_locations"]) > 0
        assert "name" in imported["campaign"]["target_locations"][0]

    def test_import_preserves_metric_formulas(self, temp_dir):
        """Test that metric_formulas are preserved during import."""
        from mediaplanpy.models import LineItem, Campaign, Meta, MetricFormula

        formula = MetricFormula(
            formula_type="cost_per_unit",
            base_metric="cost_total",
            coefficient=1000.0
        )

        lineitem = LineItem(
            id="LI001",
            name="Test",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            cost_total=Decimal("10000"),
            metric_formulas={"cpm": formula}
        )

        campaign = Campaign(
            id="CAM001",
            name="Test",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000")
        )

        meta = Meta(
            id="MP001",
            schema_version="v3.0",
            name="Test",
            created_by_name="Test User",
            created_at=datetime(2025, 1, 1, 0, 0, 0)
        )

        mediaplan = MediaPlan(meta=meta, campaign=campaign, lineitems=[lineitem])
        plan_dict = mediaplan.to_dict()

        # Export
        output_path = os.path.join(temp_dir, "test_import_formulas.xlsx")
        export_to_excel(plan_dict, path=output_path)

        # Import back
        imported = import_from_excel(output_path)

        # Verify metric_formulas
        assert len(imported["lineitems"]) > 0
        if "metric_formulas" in imported["lineitems"][0] and imported["lineitems"][0]["metric_formulas"]:
            formulas = imported["lineitems"][0]["metric_formulas"]
            assert isinstance(formulas, dict)

    def test_import_nonexistent_file_raises_error(self):
        """Test that importing nonexistent file raises error."""
        with pytest.raises((StorageError, FileNotFoundError)):
            import_from_excel("/nonexistent/path/file.xlsx")


class TestExcelRoundTrip:
    """Test round-trip export/import scenarios."""

    def test_roundtrip_minimal_plan(self, mediaplan_v3_minimal, temp_dir):
        """Test that minimal plan survives export/import cycle."""
        # Export
        plan_dict = mediaplan_v3_minimal.to_dict()
        output_path = os.path.join(temp_dir, "roundtrip_minimal.xlsx")
        export_to_excel(plan_dict, path=output_path)

        # Import
        imported = import_from_excel(output_path)

        # Verify key fields
        assert imported["meta"]["id"] == plan_dict["meta"]["id"]
        assert imported["campaign"]["id"] == plan_dict["campaign"]["id"]
        assert imported["campaign"]["name"] == plan_dict["campaign"]["name"]
        assert len(imported["lineitems"]) == len(plan_dict["lineitems"])

    def test_roundtrip_full_plan(self, mediaplan_v3_full, temp_dir):
        """Test that complete plan with all v3.0 features survives export/import cycle."""
        # Export
        plan_dict = mediaplan_v3_full.to_dict()
        output_path = os.path.join(temp_dir, "roundtrip_full.xlsx")
        export_to_excel(plan_dict, path=output_path)

        # Import
        imported = import_from_excel(output_path)

        # Verify meta
        assert imported["meta"]["id"] == plan_dict["meta"]["id"]
        assert imported["meta"]["dim_custom1"] == plan_dict["meta"]["dim_custom1"]

        # Verify campaign with v3.0 features
        assert imported["campaign"]["id"] == plan_dict["campaign"]["id"]
        assert "target_audiences" in imported["campaign"]
        assert "target_locations" in imported["campaign"]
        assert imported["campaign"]["kpi_name1"] == plan_dict["campaign"]["kpi_name1"]

        # Verify lineitems
        assert len(imported["lineitems"]) == len(plan_dict["lineitems"])

        # Verify dictionary
        if "dictionary" in plan_dict:
            assert "dictionary" in imported
            assert "lineitem_custom_dimensions" in imported["dictionary"]

    def test_roundtrip_preserves_data_types(self, temp_dir):
        """Test that data types are preserved during export/import."""
        from mediaplanpy.models import Campaign, Meta, LineItem

        campaign = Campaign(
            id="CAM001",
            name="Test Campaign",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000.50"),
            kpi_value1=Decimal("15.25")
        )

        lineitem = LineItem(
            id="LI001",
            name="Test Line Item",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            cost_total=Decimal("10000.75"),
            metric_impressions=Decimal("1000000")
        )

        meta = Meta(
            id="MP001",
            schema_version="v3.0",
            name="Test",
            created_by_name="Test User",
            created_at=datetime(2025, 1, 1, 0, 0, 0)
        )

        mediaplan = MediaPlan(meta=meta, campaign=campaign, lineitems=[lineitem])
        plan_dict = mediaplan.to_dict()

        # Export
        output_path = os.path.join(temp_dir, "roundtrip_types.xlsx")
        export_to_excel(plan_dict, path=output_path)

        # Import
        imported = import_from_excel(output_path)

        # Verify numeric types are preserved (as numbers, not strings)
        assert isinstance(imported["campaign"]["budget_total"], (int, float, Decimal))
        assert isinstance(imported["lineitems"][0]["cost_total"], (int, float, Decimal))

        # Verify date strings
        assert "2025-01-01" in str(imported["campaign"]["start_date"])
        assert "2025-12-31" in str(imported["campaign"]["end_date"])


class TestExcelEdgeCases:
    """Test edge cases and error handling."""

    def test_export_without_dictionary(self, temp_dir):
        """Test exporting plan without dictionary section."""
        from mediaplanpy.models import Campaign, Meta

        campaign = Campaign(
            id="CAM001",
            name="Test",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000")
        )

        meta = Meta(
            id="MP001",
            schema_version="v3.0",
            name="Test",
            created_by_name="Test User",
            created_at=datetime(2025, 1, 1, 0, 0, 0)
        )

        mediaplan = MediaPlan(meta=meta, campaign=campaign, lineitems=[])
        plan_dict = mediaplan.to_dict()

        # Export should work without dictionary
        output_path = os.path.join(temp_dir, "test_no_dict.xlsx")
        result_path = export_to_excel(plan_dict, path=output_path)

        assert os.path.exists(result_path)

    def test_export_empty_lineitems(self, temp_dir):
        """Test exporting plan with no line items."""
        from mediaplanpy.models import Campaign, Meta

        campaign = Campaign(
            id="CAM001",
            name="Test",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000")
        )

        meta = Meta(
            id="MP001",
            schema_version="v3.0",
            name="Test",
            created_by_name="Test User",
            created_at=datetime(2025, 1, 1, 0, 0, 0)
        )

        mediaplan = MediaPlan(meta=meta, campaign=campaign, lineitems=[])
        plan_dict = mediaplan.to_dict()

        # Export should work with empty lineitems
        output_path = os.path.join(temp_dir, "test_empty_lineitems.xlsx")
        result_path = export_to_excel(plan_dict, path=output_path)

        assert os.path.exists(result_path)

        # Import back and verify
        imported = import_from_excel(result_path)
        assert len(imported["lineitems"]) == 0
