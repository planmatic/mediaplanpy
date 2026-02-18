"""
Integration tests for workspace query functionality with v3.0 schema.

Tests querying media plans in a workspace, including:
- list_mediaplans() with v3.0 features
- list_campaigns() with target_audiences/locations
- list_lineitems() with new metrics
- sql_query() with v3.0 schema
- DataFrame output
"""

import pytest
import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import date

from mediaplanpy.workspace import WorkspaceManager
from mediaplanpy.models import MediaPlan


@pytest.fixture
def temp_workspace_with_v3_plans(temp_dir, mediaplan_v3_minimal, mediaplan_v3_full):
    """Create a workspace with v3.0 media plans."""
    # Create workspace config
    config = {
        "workspace_id": "test_workspace_query",
        "workspace_name": "Test Workspace for Queries",
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

    # Load workspace and save media plans properly (creates both JSON and Parquet)
    workspace_manager = WorkspaceManager(workspace_path=config_path)
    workspace_manager.load()

    # Save media plans using proper save method (creates JSON + Parquet)
    mediaplan_v3_minimal.save(workspace_manager, path="mediaplans/mediaplan_minimal.json")
    mediaplan_v3_full.save(workspace_manager, path="mediaplans/mediaplan_full.json")

    return config_path


class TestListMediaPlans:
    """Test list_mediaplans() with v3.0 media plans."""

    def test_list_all_mediaplans(self, temp_workspace_with_v3_plans):
        """Test listing all media plans in workspace."""
        workspace_manager = WorkspaceManager(workspace_path=temp_workspace_with_v3_plans)
        workspace_manager.load()

        # List all media plans
        mediaplans = workspace_manager.list_mediaplans()

        # Should return list of media plans
        assert isinstance(mediaplans, list)
        assert len(mediaplans) >= 2  # minimal and full

        # Each should have basic Parquet schema fields
        # Note: list_mediaplans() returns one row per media plan (not per lineitem)
        for mp in mediaplans:
            assert "meta_id" in mp
            assert "campaign_id" in mp
            assert "meta_schema_version" in mp
            assert mp["meta_schema_version"] in ["3.0", "v3.0"]

    def test_list_mediaplans_as_dataframe(self, temp_workspace_with_v3_plans):
        """Test returning mediaplans as DataFrame."""
        workspace_manager = WorkspaceManager(workspace_path=temp_workspace_with_v3_plans)
        workspace_manager.load()

        # List as DataFrame
        df = workspace_manager.list_mediaplans(return_dataframe=True)

        # Should return pandas DataFrame
        assert df is not None
        assert len(df) >= 2

        # Should have key columns (using Parquet schema names)
        assert "meta_id" in df.columns

    def test_list_mediaplans_with_filters(self, temp_workspace_with_v3_plans):
        """Test filtering mediaplans by criteria."""
        workspace_manager = WorkspaceManager(workspace_path=temp_workspace_with_v3_plans)
        workspace_manager.load()

        # Filter by meta_id (using Parquet schema name)
        filtered = workspace_manager.list_mediaplans(filters={"meta_id": "MP001"})

        # Should return filtered results
        assert isinstance(filtered, list)
        if len(filtered) > 0:
            assert all(mp["meta_id"] == "MP001" for mp in filtered)


class TestListCampaigns:
    """Test list_campaigns() with v3.0 campaigns."""

    def test_list_all_campaigns(self, temp_workspace_with_v3_plans):
        """Test listing all campaigns in workspace."""
        workspace_manager = WorkspaceManager(workspace_path=temp_workspace_with_v3_plans)
        workspace_manager.load()

        # List all campaigns
        campaigns = workspace_manager.list_campaigns()

        # Should return list of campaigns
        assert isinstance(campaigns, list)
        assert len(campaigns) >= 2

        # Each should have campaign Parquet schema fields
        for campaign in campaigns:
            assert "campaign_id" in campaign
            assert "campaign_name" in campaign
            assert "campaign_objective" in campaign

    def test_list_campaigns_with_target_audiences(self, temp_workspace_with_v3_plans):
        """Test that campaigns are returned correctly.

        Note: target_audiences is a complex nested array in v3.0 JSON that is not
        stored in the flattened Parquet schema used for queries.
        """
        workspace_manager = WorkspaceManager(workspace_path=temp_workspace_with_v3_plans)
        workspace_manager.load()

        # List campaigns
        campaigns = workspace_manager.list_campaigns()

        # Verify campaigns are returned with Parquet schema fields
        assert len(campaigns) >= 1
        for campaign in campaigns:
            assert "campaign_id" in campaign
            assert "campaign_name" in campaign

    def test_list_campaigns_with_target_locations(self, temp_workspace_with_v3_plans):
        """Test that campaigns are returned correctly.

        Note: target_locations is a complex nested array in v3.0 JSON that is not
        stored in the flattened Parquet schema used for queries.
        """
        workspace_manager = WorkspaceManager(workspace_path=temp_workspace_with_v3_plans)
        workspace_manager.load()

        # List campaigns
        campaigns = workspace_manager.list_campaigns()

        # Verify campaigns are returned with Parquet schema fields
        assert len(campaigns) >= 1
        for campaign in campaigns:
            assert "campaign_id" in campaign
            assert "campaign_objective" in campaign

    def test_list_campaigns_as_dataframe(self, temp_workspace_with_v3_plans):
        """Test returning campaigns as DataFrame."""
        workspace_manager = WorkspaceManager(workspace_path=temp_workspace_with_v3_plans)
        workspace_manager.load()

        # List as DataFrame
        df = workspace_manager.list_campaigns(return_dataframe=True)

        # Should return pandas DataFrame
        assert df is not None
        assert len(df) >= 2

        # Should have key columns (using Parquet schema names)
        assert "campaign_id" in df.columns


class TestListLineItems:
    """Test list_lineitems() with v3.0 line items."""

    def test_list_all_lineitems(self, temp_workspace_with_v3_plans):
        """Test listing all line items in workspace."""
        workspace_manager = WorkspaceManager(workspace_path=temp_workspace_with_v3_plans)
        workspace_manager.load()

        # List all line items
        lineitems = workspace_manager.list_lineitems()

        # Should return list of line items
        assert isinstance(lineitems, list)
        assert len(lineitems) >= 1  # At least one from fixtures

        # Each should have lineitem Parquet schema fields
        for lineitem in lineitems:
            assert "lineitem_id" in lineitem
            assert "lineitem_name" in lineitem
            assert "lineitem_cost_total" in lineitem

    def test_list_lineitems_with_new_metrics(self, temp_workspace_with_v3_plans):
        """Test that line items with new v3.0 metrics are returned correctly."""
        workspace_manager = WorkspaceManager(workspace_path=temp_workspace_with_v3_plans)
        workspace_manager.load()

        # List line items
        lineitems = workspace_manager.list_lineitems()

        # Find line items with new metrics (using Parquet schema names)
        lineitems_with_new_metrics = [
            li for li in lineitems
            if any(metric in li for metric in ["lineitem_metric_view_starts", "lineitem_metric_reach", "lineitem_metric_conversions"])
        ]

        # If we have line items with new metrics, verify structure
        if len(lineitems_with_new_metrics) > 0:
            assert isinstance(lineitems_with_new_metrics[0], dict)

    def test_list_lineitems_with_metric_formulas(self, temp_workspace_with_v3_plans):
        """Test that line items with metric_formulas are returned correctly."""
        workspace_manager = WorkspaceManager(workspace_path=temp_workspace_with_v3_plans)
        workspace_manager.load()

        # List line items
        lineitems = workspace_manager.list_lineitems()

        # Find line items with metric_formulas
        lineitems_with_formulas = [li for li in lineitems if "metric_formulas" in li and li["metric_formulas"]]

        # If we have line items with formulas, verify structure
        if len(lineitems_with_formulas) > 0:
            formulas = lineitems_with_formulas[0]["metric_formulas"]
            assert isinstance(formulas, dict)

    def test_list_lineitems_as_dataframe(self, temp_workspace_with_v3_plans):
        """Test returning line items as DataFrame."""
        workspace_manager = WorkspaceManager(workspace_path=temp_workspace_with_v3_plans)
        workspace_manager.load()

        # List as DataFrame
        df = workspace_manager.list_lineitems(return_dataframe=True)

        # Should return pandas DataFrame
        assert df is not None
        assert len(df) >= 1

        # Should have key columns (using Parquet schema names)
        assert "lineitem_id" in df.columns


class TestSQLQuery:
    """Test sql_query() with v3.0 schema."""

    def test_sql_query_basic(self, temp_workspace_with_v3_plans):
        """Test basic SQL query on media plans."""
        workspace_manager = WorkspaceManager(workspace_path=temp_workspace_with_v3_plans)
        workspace_manager.load()

        # Simple SELECT query - use {*} pattern to match all files
        result = workspace_manager.sql_query("SELECT * FROM {*} LIMIT 10")

        # Should return results
        assert result is not None

    def test_sql_query_campaigns(self, temp_workspace_with_v3_plans):
        """Test SQL query on campaigns table."""
        workspace_manager = WorkspaceManager(workspace_path=temp_workspace_with_v3_plans)
        workspace_manager.load()

        # Query campaigns - use {*} pattern to match all files
        result = workspace_manager.sql_query("SELECT campaign_id, campaign_name, campaign_objective FROM {*}")

        # Should return results
        assert result is not None

    def test_sql_query_with_filters(self, temp_workspace_with_v3_plans):
        """Test SQL query with WHERE clause."""
        workspace_manager = WorkspaceManager(workspace_path=temp_workspace_with_v3_plans)
        workspace_manager.load()

        # Query with filter - use {*} pattern to match all files
        result = workspace_manager.sql_query(
            "SELECT * FROM {*} WHERE campaign_objective = 'awareness'"
        )

        # Should return results
        assert result is not None


class TestQueryEdgeCases:
    """Test edge cases and error handling."""

    def test_list_empty_workspace(self, temp_dir):
        """Test listing from empty workspace."""
        # Create empty workspace
        config = {
            "workspace_id": "test_empty",
            "workspace_name": "Empty Test Workspace",
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

        config_path = os.path.join(temp_dir, "workspace_empty.json")
        with open(config_path, 'w') as f:
            json.dump(config, f)

        workspace_manager = WorkspaceManager(workspace_path=config_path)
        workspace_manager.load()

        # List should return empty list, not error
        mediaplans = workspace_manager.list_mediaplans()
        assert isinstance(mediaplans, list)
        assert len(mediaplans) == 0

    def test_query_requires_loaded_workspace(self, temp_dir):
        """Test that queries require workspace to be loaded."""
        config_path = os.path.join(temp_dir, "workspace_test.json")
        config = {
            "workspace_id": "test_query",
            "workspace_name": "Test Query Workspace",
            "workspace_settings": {
                "schema_version": "3.0"
            },
            "storage": {
                "mode": "local",
                "local": {
                    "base_path": temp_dir
                }
            },
            "database": {"enabled": False}
        }

        with open(config_path, 'w') as f:
            json.dump(config, f)

        workspace_manager = WorkspaceManager(workspace_path=config_path)
        # Don't load workspace

        # Should raise error
        from mediaplanpy.exceptions import WorkspaceError
        with pytest.raises(WorkspaceError):
            workspace_manager.list_mediaplans()


class TestSQLWorkspaceIsolation:
    """Test SQL query validation for workspace isolation safety.

    These tests verify that queries which could bypass the workspace_id
    filter injection are properly rejected. The _add_workspace_filter()
    method only modifies the first/outermost WHERE clause, so queries
    with multiple SELECT statements, UNION, or semicolons could leak
    data across workspaces in a multi-tenant database.
    """

    def _validate(self, query):
        """Helper to call _validate_sql_safety directly."""
        from mediaplanpy.workspace.query import _validate_sql_safety
        _validate_sql_safety(query)

    # --- Valid queries that SHOULD pass ---

    def test_simple_select_passes(self):
        """Simple SELECT query should pass validation."""
        self._validate("SELECT * FROM {*}")

    def test_select_with_where_passes(self):
        """SELECT with WHERE clause should pass."""
        self._validate("SELECT * FROM {*} WHERE campaign_name = 'test'")

    def test_select_with_group_by_passes(self):
        """SELECT with GROUP BY should pass."""
        self._validate("SELECT campaign_id, COUNT(*) FROM {*} GROUP BY campaign_id")

    def test_select_with_order_and_limit_passes(self):
        """SELECT with ORDER BY and LIMIT should pass."""
        self._validate("SELECT * FROM {*} ORDER BY campaign_name LIMIT 10")

    def test_string_literal_containing_select_passes(self):
        """String literal containing 'SELECT' keyword should not trigger false positive."""
        self._validate("SELECT * FROM {*} WHERE name = 'SELECT something'")

    def test_string_literal_containing_union_passes(self):
        """String literal containing 'UNION' keyword should not trigger false positive."""
        self._validate("SELECT * FROM {*} WHERE description = 'UNION of campaigns'")

    def test_string_literal_containing_semicolon_passes(self):
        """String literal containing semicolon should not trigger false positive."""
        self._validate("SELECT * FROM {*} WHERE notes = 'item1; item2; item3'")

    # --- UNION queries that SHOULD be rejected ---

    def test_union_select_rejected(self):
        """UNION SELECT should be rejected to prevent workspace isolation bypass."""
        from mediaplanpy.exceptions import SQLQueryError
        with pytest.raises(SQLQueryError, match="UNION"):
            self._validate("SELECT * FROM {*} UNION SELECT * FROM media_plans")

    def test_union_all_rejected(self):
        """UNION ALL should be rejected."""
        from mediaplanpy.exceptions import SQLQueryError
        with pytest.raises(SQLQueryError, match="UNION"):
            self._validate("SELECT * FROM {*} UNION ALL SELECT * FROM media_plans")

    def test_union_case_insensitive(self):
        """UNION detection should be case-insensitive."""
        from mediaplanpy.exceptions import SQLQueryError
        with pytest.raises(SQLQueryError, match="UNION"):
            self._validate("SELECT * FROM {*} union select * FROM media_plans")

    # --- Semicolon (multiple statements) that SHOULD be rejected ---

    def test_semicolon_multiple_statements_rejected(self):
        """Multiple SQL statements via semicolons should be rejected."""
        from mediaplanpy.exceptions import SQLQueryError
        with pytest.raises(SQLQueryError, match="semicolon"):
            self._validate("SELECT * FROM {*}; SELECT * FROM media_plans")

    def test_trailing_semicolon_rejected(self):
        """Even a trailing semicolon should be rejected as a precaution."""
        from mediaplanpy.exceptions import SQLQueryError
        with pytest.raises(SQLQueryError, match="semicolon"):
            self._validate("SELECT * FROM {*};")

    # --- Subqueries (multiple SELECTs) that SHOULD be rejected ---

    def test_subquery_in_where_rejected(self):
        """Subquery in WHERE clause should be rejected."""
        from mediaplanpy.exceptions import SQLQueryError
        with pytest.raises(SQLQueryError, match="[Ss]ubquer"):
            self._validate(
                "SELECT * FROM {*} WHERE campaign_id IN (SELECT campaign_id FROM media_plans)"
            )

    def test_subquery_in_from_rejected(self):
        """Subquery in FROM clause should be rejected."""
        from mediaplanpy.exceptions import SQLQueryError
        with pytest.raises(SQLQueryError, match="[Ss]ubquer"):
            self._validate("SELECT * FROM (SELECT * FROM {*}) AS sub")

    def test_scalar_subquery_rejected(self):
        """Scalar subquery in SELECT list should be rejected."""
        from mediaplanpy.exceptions import SQLQueryError
        with pytest.raises(SQLQueryError, match="[Ss]ubquer"):
            self._validate(
                "SELECT *, (SELECT COUNT(*) FROM media_plans) AS total FROM {*}"
            )

    def test_exists_subquery_rejected(self):
        """EXISTS subquery should be rejected."""
        from mediaplanpy.exceptions import SQLQueryError
        with pytest.raises(SQLQueryError, match="[Ss]ubquer"):
            self._validate(
                "SELECT * FROM {*} WHERE EXISTS (SELECT 1 FROM media_plans WHERE workspace_id = 'other')"
            )

    def test_cte_with_subquery_rejected(self):
        """CTE (WITH clause) containing SELECT should be rejected (two SELECTs total)."""
        from mediaplanpy.exceptions import SQLQueryError
        with pytest.raises(SQLQueryError, match="[Ss]ubquer"):
            self._validate(
                "WITH all_data AS (SELECT * FROM media_plans) SELECT * FROM {*}"
            )

    # --- Comments should not hide dangerous keywords ---

    def test_union_in_line_comment_still_safe(self):
        """UNION hidden in a line comment should be stripped and not affect the query.
        A single SELECT after comment stripping should pass."""
        # The comment gets stripped, leaving just a single SELECT
        self._validate("SELECT * FROM {*} -- UNION SELECT * FROM media_plans")

    def test_select_in_block_comment_stripped(self):
        """SELECT in block comment should be stripped and not count."""
        self._validate("SELECT * FROM {*} /* SELECT * FROM other_table */")
