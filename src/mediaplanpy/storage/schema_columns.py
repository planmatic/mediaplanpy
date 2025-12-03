"""
Shared schema definition for MediaPlan v3.0 Parquet and Database formats.

This module provides the canonical schema definition used by both
ParquetFormatHandler and DatabaseStorage to ensure consistency.

Single source of truth for:
- Column names (Parquet/Database)
- Python types
- Field descriptions
- JSON path mappings (hierarchical → flat)

JSON Path Notation:
- Scalar fields: "meta.id", "campaign.name"
- Array fields: "lineitems[].cost_total" (denormalized - one row per lineitem)
"""

from decimal import Decimal
from datetime import datetime, date
from typing import List, Tuple, Type, Dict
import pyarrow as pa


# =============================================================================
# v3.0 Schema Definition
# Format: (column_name, python_type, description, json_path)
# =============================================================================

MEDIAPLAN_SCHEMA_V3_0: List[Tuple[str, Type, str, str]] = [
    # -------------------------------------------------------------------------
    # Meta Fields (16 total: 11 v2.0 + 5 new v3.0)
    # -------------------------------------------------------------------------
    ("meta_id", str, "Unique identifier for the media plan", "meta.id"),
    ("meta_schema_version", str, "Schema version (e.g., '3.0')", "meta.schema_version"),
    ("meta_created_by", str, "Legacy field - email of creator", "meta.created_by"),
    ("meta_created_at", datetime, "Creation timestamp", "meta.created_at"),
    ("meta_name", str, "Name of the media plan", "meta.name"),
    ("meta_comments", str, "Additional comments", "meta.comments"),
    ("meta_created_by_id", str, "ID of the creator", "meta.created_by_id"),
    ("meta_created_by_name", str, "Name of the creator", "meta.created_by_name"),
    ("meta_is_current", bool, "Whether this is the current version", "meta.is_current"),
    ("meta_is_archived", bool, "Whether this plan is archived", "meta.is_archived"),
    ("meta_parent_id", str, "ID of parent plan if this is a version", "meta.parent_id"),
    # NEW v3.0 meta fields
    ("meta_dim_custom1", str, "Custom dimension 1 for meta", "meta.dim_custom1"),
    ("meta_dim_custom2", str, "Custom dimension 2 for meta", "meta.dim_custom2"),
    ("meta_dim_custom3", str, "Custom dimension 3 for meta", "meta.dim_custom3"),
    ("meta_dim_custom4", str, "Custom dimension 4 for meta", "meta.dim_custom4"),
    ("meta_dim_custom5", str, "Custom dimension 5 for meta", "meta.dim_custom5"),

    # -------------------------------------------------------------------------
    # Campaign Fields (33 total: 18 kept v2.0 + 15 new v3.0)
    # NOTE: 7 deprecated audience/location fields REMOVED in v3.0
    # -------------------------------------------------------------------------
    ("campaign_id", str, "Unique identifier for the campaign", "campaign.id"),
    ("campaign_name", str, "Name of the campaign", "campaign.name"),
    ("campaign_objective", str, "Campaign objective", "campaign.objective"),
    ("campaign_start_date", date, "Campaign start date", "campaign.start_date"),
    ("campaign_end_date", date, "Campaign end date", "campaign.end_date"),
    ("campaign_budget_total", Decimal, "Total campaign budget", "campaign.budget_total"),
    ("campaign_product_name", str, "Product name", "campaign.product_name"),
    ("campaign_product_description", str, "Product description", "campaign.product_description"),
    # v2.0 campaign fields (kept)
    ("campaign_budget_currency", str, "Currency for budget", "campaign.budget_currency"),
    ("campaign_agency_id", str, "Agency ID", "campaign.agency_id"),
    ("campaign_agency_name", str, "Agency name", "campaign.agency_name"),
    ("campaign_advertiser_id", str, "Advertiser ID", "campaign.advertiser_id"),
    ("campaign_advertiser_name", str, "Advertiser name", "campaign.advertiser_name"),
    ("campaign_product_id", str, "Product ID", "campaign.product_id"),
    ("campaign_campaign_type_id", str, "Campaign type ID", "campaign.campaign_type_id"),
    ("campaign_campaign_type_name", str, "Campaign type name", "campaign.campaign_type_name"),
    ("campaign_workflow_status_id", str, "Workflow status ID", "campaign.workflow_status_id"),
    ("campaign_workflow_status_name", str, "Workflow status name", "campaign.workflow_status_name"),
    # NEW v3.0 campaign fields - KPI tracking
    ("campaign_kpi_name1", str, "Name of KPI 1", "campaign.kpi_name1"),
    ("campaign_kpi_value1", Decimal, "Value for KPI 1", "campaign.kpi_value1"),
    ("campaign_kpi_name2", str, "Name of KPI 2", "campaign.kpi_name2"),
    ("campaign_kpi_value2", Decimal, "Value for KPI 2", "campaign.kpi_value2"),
    ("campaign_kpi_name3", str, "Name of KPI 3", "campaign.kpi_name3"),
    ("campaign_kpi_value3", Decimal, "Value for KPI 3", "campaign.kpi_value3"),
    ("campaign_kpi_name4", str, "Name of KPI 4", "campaign.kpi_name4"),
    ("campaign_kpi_value4", Decimal, "Value for KPI 4", "campaign.kpi_value4"),
    ("campaign_kpi_name5", str, "Name of KPI 5", "campaign.kpi_name5"),
    ("campaign_kpi_value5", Decimal, "Value for KPI 5", "campaign.kpi_value5"),
    # NEW v3.0 campaign fields - Custom dimensions
    ("campaign_dim_custom1", str, "Custom dimension 1 for campaign", "campaign.dim_custom1"),
    ("campaign_dim_custom2", str, "Custom dimension 2 for campaign", "campaign.dim_custom2"),
    ("campaign_dim_custom3", str, "Custom dimension 3 for campaign", "campaign.dim_custom3"),
    ("campaign_dim_custom4", str, "Custom dimension 4 for campaign", "campaign.dim_custom4"),
    ("campaign_dim_custom5", str, "Custom dimension 5 for campaign", "campaign.dim_custom5"),

    # -------------------------------------------------------------------------
    # LineItem Basic Fields
    # -------------------------------------------------------------------------
    ("lineitem_id", str, "Unique identifier for the line item", "lineitems[].id"),
    ("lineitem_name", str, "Name of the line item", "lineitems[].name"),
    ("lineitem_start_date", date, "Line item start date", "lineitems[].start_date"),
    ("lineitem_end_date", date, "Line item end date", "lineitems[].end_date"),
    ("lineitem_cost_total", Decimal, "Total cost for this line item", "lineitems[].cost_total"),

    # -------------------------------------------------------------------------
    # LineItem Categorization Fields
    # -------------------------------------------------------------------------
    ("lineitem_channel", str, "Media channel", "lineitems[].channel"),
    ("lineitem_channel_custom", str, "Custom channel value", "lineitems[].channel_custom"),
    ("lineitem_vehicle", str, "Media vehicle", "lineitems[].vehicle"),
    ("lineitem_vehicle_custom", str, "Custom vehicle value", "lineitems[].vehicle_custom"),
    ("lineitem_partner", str, "Partner/publisher", "lineitems[].partner"),
    ("lineitem_partner_custom", str, "Custom partner value", "lineitems[].partner_custom"),
    ("lineitem_media_product", str, "Media product", "lineitems[].media_product"),
    ("lineitem_media_product_custom", str, "Custom media product value", "lineitems[].media_product_custom"),
    ("lineitem_location_type", str, "Location type", "lineitems[].location_type"),
    ("lineitem_location_name", str, "Location name", "lineitems[].location_name"),
    ("lineitem_target_audience", str, "Target audience", "lineitems[].target_audience"),
    ("lineitem_adformat", str, "Ad format", "lineitems[].adformat"),
    ("lineitem_adformat_custom", str, "Custom ad format value", "lineitems[].adformat_custom"),
    ("lineitem_kpi", str, "KPI", "lineitems[].kpi"),
    ("lineitem_kpi_custom", str, "Custom KPI value", "lineitems[].kpi_custom"),
    # v2.0 line item fields (kept)
    ("lineitem_cost_currency", str, "Currency for costs", "lineitems[].cost_currency"),
    ("lineitem_dayparts", str, "Dayparts", "lineitems[].dayparts"),
    ("lineitem_dayparts_custom", str, "Custom dayparts value", "lineitems[].dayparts_custom"),
    ("lineitem_inventory", str, "Inventory type", "lineitems[].inventory"),
    ("lineitem_inventory_custom", str, "Custom inventory value", "lineitems[].inventory_custom"),

    # -------------------------------------------------------------------------
    # LineItem NEW v3.0 Fields
    # -------------------------------------------------------------------------
    # Buy information
    ("lineitem_kpi_value", Decimal, "Target value for the KPI", "lineitems[].kpi_value"),
    ("lineitem_buy_type", str, "Type of media buy (e.g., Programmatic)", "lineitems[].buy_type"),
    ("lineitem_buy_commitment", str, "Commitment level (e.g., Guaranteed)", "lineitems[].buy_commitment"),
    # Aggregation
    ("lineitem_is_aggregate", bool, "Whether this is an aggregate line item", "lineitems[].is_aggregate"),
    ("lineitem_aggregation_level", str, "Level at which metrics are aggregated", "lineitems[].aggregation_level"),
    # Multi-currency
    ("lineitem_cost_currency_exchange_rate", Decimal, "Exchange rate if costs in different currency", "lineitems[].cost_currency_exchange_rate"),
    # Budget constraints
    ("lineitem_cost_minimum", Decimal, "Minimum expected cost", "lineitems[].cost_minimum"),
    ("lineitem_cost_maximum", Decimal, "Maximum expected cost", "lineitems[].cost_maximum"),

    # -------------------------------------------------------------------------
    # LineItem Custom Dimensions (10)
    # -------------------------------------------------------------------------
    ("lineitem_dim_custom1", str, "Custom dimension 1", "lineitems[].dim_custom1"),
    ("lineitem_dim_custom2", str, "Custom dimension 2", "lineitems[].dim_custom2"),
    ("lineitem_dim_custom3", str, "Custom dimension 3", "lineitems[].dim_custom3"),
    ("lineitem_dim_custom4", str, "Custom dimension 4", "lineitems[].dim_custom4"),
    ("lineitem_dim_custom5", str, "Custom dimension 5", "lineitems[].dim_custom5"),
    ("lineitem_dim_custom6", str, "Custom dimension 6", "lineitems[].dim_custom6"),
    ("lineitem_dim_custom7", str, "Custom dimension 7", "lineitems[].dim_custom7"),
    ("lineitem_dim_custom8", str, "Custom dimension 8", "lineitems[].dim_custom8"),
    ("lineitem_dim_custom9", str, "Custom dimension 9", "lineitems[].dim_custom9"),
    ("lineitem_dim_custom10", str, "Custom dimension 10", "lineitems[].dim_custom10"),

    # -------------------------------------------------------------------------
    # LineItem Standard Cost Fields (5)
    # -------------------------------------------------------------------------
    ("lineitem_cost_media", Decimal, "Media cost", "lineitems[].cost_media"),
    ("lineitem_cost_buying", Decimal, "Buying cost", "lineitems[].cost_buying"),
    ("lineitem_cost_platform", Decimal, "Platform cost", "lineitems[].cost_platform"),
    ("lineitem_cost_data", Decimal, "Data cost", "lineitems[].cost_data"),
    ("lineitem_cost_creative", Decimal, "Creative cost", "lineitems[].cost_creative"),

    # -------------------------------------------------------------------------
    # LineItem Custom Cost Fields (10)
    # -------------------------------------------------------------------------
    ("lineitem_cost_custom1", Decimal, "Custom cost 1", "lineitems[].cost_custom1"),
    ("lineitem_cost_custom2", Decimal, "Custom cost 2", "lineitems[].cost_custom2"),
    ("lineitem_cost_custom3", Decimal, "Custom cost 3", "lineitems[].cost_custom3"),
    ("lineitem_cost_custom4", Decimal, "Custom cost 4", "lineitems[].cost_custom4"),
    ("lineitem_cost_custom5", Decimal, "Custom cost 5", "lineitems[].cost_custom5"),
    ("lineitem_cost_custom6", Decimal, "Custom cost 6", "lineitems[].cost_custom6"),
    ("lineitem_cost_custom7", Decimal, "Custom cost 7", "lineitems[].cost_custom7"),
    ("lineitem_cost_custom8", Decimal, "Custom cost 8", "lineitems[].cost_custom8"),
    ("lineitem_cost_custom9", Decimal, "Custom cost 9", "lineitems[].cost_custom9"),
    ("lineitem_cost_custom10", Decimal, "Custom cost 10", "lineitems[].cost_custom10"),

    # -------------------------------------------------------------------------
    # LineItem Standard Metrics - v1.0 (3)
    # -------------------------------------------------------------------------
    ("lineitem_metric_impressions", Decimal, "Number of impressions", "lineitems[].metric_impressions"),
    ("lineitem_metric_clicks", Decimal, "Number of clicks", "lineitems[].metric_clicks"),
    ("lineitem_metric_views", Decimal, "Number of views", "lineitems[].metric_views"),

    # -------------------------------------------------------------------------
    # LineItem Standard Metrics - v2.0 additions (15)
    # -------------------------------------------------------------------------
    ("lineitem_metric_engagements", Decimal, "Number of engagements", "lineitems[].metric_engagements"),
    ("lineitem_metric_followers", Decimal, "Number of followers gained", "lineitems[].metric_followers"),
    ("lineitem_metric_visits", Decimal, "Number of visits", "lineitems[].metric_visits"),
    ("lineitem_metric_leads", Decimal, "Number of leads", "lineitems[].metric_leads"),
    ("lineitem_metric_sales", Decimal, "Number of sales", "lineitems[].metric_sales"),
    ("lineitem_metric_add_to_cart", Decimal, "Number of add-to-cart actions", "lineitems[].metric_add_to_cart"),
    ("lineitem_metric_app_install", Decimal, "Number of app installs", "lineitems[].metric_app_install"),
    ("lineitem_metric_application_start", Decimal, "Number of application starts", "lineitems[].metric_application_start"),
    ("lineitem_metric_application_complete", Decimal, "Number of application completions", "lineitems[].metric_application_complete"),
    ("lineitem_metric_contact_us", Decimal, "Number of contact-us actions", "lineitems[].metric_contact_us"),
    ("lineitem_metric_download", Decimal, "Number of downloads", "lineitems[].metric_download"),
    ("lineitem_metric_signup", Decimal, "Number of signups", "lineitems[].metric_signup"),
    ("lineitem_metric_max_daily_spend", Decimal, "Maximum daily spend", "lineitems[].metric_max_daily_spend"),
    ("lineitem_metric_max_daily_impressions", Decimal, "Maximum daily impressions", "lineitems[].metric_max_daily_impressions"),
    ("lineitem_metric_audience_size", Decimal, "Audience size", "lineitems[].metric_audience_size"),

    # -------------------------------------------------------------------------
    # LineItem Standard Metrics - NEW v3.0 additions (10)
    # -------------------------------------------------------------------------
    ("lineitem_metric_view_starts", Decimal, "Number of video view starts", "lineitems[].metric_view_starts"),
    ("lineitem_metric_view_completions", Decimal, "Number of video view completions", "lineitems[].metric_view_completions"),
    ("lineitem_metric_reach", Decimal, "Total unique users reached", "lineitems[].metric_reach"),
    ("lineitem_metric_units", Decimal, "Number of units (generic counter)", "lineitems[].metric_units"),
    ("lineitem_metric_impression_share", Decimal, "Impression share (percentage)", "lineitems[].metric_impression_share"),
    ("lineitem_metric_page_views", Decimal, "Number of page views", "lineitems[].metric_page_views"),
    ("lineitem_metric_likes", Decimal, "Number of likes", "lineitems[].metric_likes"),
    ("lineitem_metric_shares", Decimal, "Number of shares", "lineitems[].metric_shares"),
    ("lineitem_metric_comments", Decimal, "Number of comments", "lineitems[].metric_comments"),
    ("lineitem_metric_conversions", Decimal, "Number of conversions", "lineitems[].metric_conversions"),

    # -------------------------------------------------------------------------
    # LineItem Custom Metrics (10)
    # -------------------------------------------------------------------------
    ("lineitem_metric_custom1", Decimal, "Custom metric 1", "lineitems[].metric_custom1"),
    ("lineitem_metric_custom2", Decimal, "Custom metric 2", "lineitems[].metric_custom2"),
    ("lineitem_metric_custom3", Decimal, "Custom metric 3", "lineitems[].metric_custom3"),
    ("lineitem_metric_custom4", Decimal, "Custom metric 4", "lineitems[].metric_custom4"),
    ("lineitem_metric_custom5", Decimal, "Custom metric 5", "lineitems[].metric_custom5"),
    ("lineitem_metric_custom6", Decimal, "Custom metric 6", "lineitems[].metric_custom6"),
    ("lineitem_metric_custom7", Decimal, "Custom metric 7", "lineitems[].metric_custom7"),
    ("lineitem_metric_custom8", Decimal, "Custom metric 8", "lineitems[].metric_custom8"),
    ("lineitem_metric_custom9", Decimal, "Custom metric 9", "lineitems[].metric_custom9"),
    ("lineitem_metric_custom10", Decimal, "Custom metric 10", "lineitems[].metric_custom10"),
]


# =============================================================================
# Deprecated Fields (Removed in v3.0)
# =============================================================================

DEPRECATED_FIELDS_V3_0: List[Tuple[str, str]] = [
    # (field_name, reason_for_removal)
    ("campaign_audience_name", "Replaced by target_audiences array"),
    ("campaign_audience_age_start", "Replaced by target_audiences array"),
    ("campaign_audience_age_end", "Replaced by target_audiences array"),
    ("campaign_audience_gender", "Replaced by target_audiences array"),
    ("campaign_audience_interests", "Replaced by target_audiences array"),
    ("campaign_location_type", "Replaced by target_locations array"),
    ("campaign_locations", "Replaced by target_locations array"),
]


# =============================================================================
# Derived Properties (Auto-generated from schema)
# =============================================================================

def get_column_names() -> List[str]:
    """Get ordered list of column names."""
    return [col[0] for col in MEDIAPLAN_SCHEMA_V3_0]


def get_column_types() -> Dict[str, Type]:
    """Get dictionary mapping column names to Python types."""
    return {col[0]: col[1] for col in MEDIAPLAN_SCHEMA_V3_0}


def get_column_descriptions() -> Dict[str, str]:
    """Get dictionary mapping column names to descriptions."""
    return {col[0]: col[2] for col in MEDIAPLAN_SCHEMA_V3_0}


# =============================================================================
# Type Conversion Utilities
# =============================================================================

def python_type_to_pyarrow(py_type: Type) -> pa.DataType:
    """
    Convert Python type to PyArrow data type.

    Args:
        py_type: Python type (str, int, Decimal, datetime, date, bool)

    Returns:
        Corresponding PyArrow data type
    """
    mapping = {
        str: pa.string(),
        int: pa.int32(),
        Decimal: pa.float64(),  # Decimals stored as float64 in Parquet
        datetime: pa.timestamp('ns'),
        date: pa.date32(),
        bool: pa.bool_(),
    }
    return mapping.get(py_type, pa.string())


def python_type_to_sql(py_type: Type, is_primary_key: bool = False) -> str:
    """
    Convert Python type to PostgreSQL SQL data type.

    Args:
        py_type: Python type (str, int, Decimal, datetime, date, bool)
        is_primary_key: Whether this is a primary key field

    Returns:
        Corresponding SQL type string
    """
    mapping = {
        str: "VARCHAR(255)",
        int: "INTEGER",
        Decimal: "DECIMAL(20,4)",
        datetime: "TIMESTAMP",
        date: "DATE",
        bool: "BOOLEAN",
    }

    sql_type = mapping.get(py_type, "TEXT")

    # Add NOT NULL for primary keys
    if is_primary_key:
        sql_type += " NOT NULL"

    return sql_type


def get_pyarrow_schema() -> pa.Schema:
    """
    Generate PyArrow schema for Parquet files from canonical definition.

    Returns:
        PyArrow schema with all v3.0 fields
    """
    fields = []
    for col_name, py_type, _ in MEDIAPLAN_SCHEMA_V3_0:
        pa_type = python_type_to_pyarrow(py_type)
        fields.append(pa.field(col_name, pa_type))
    return pa.schema(fields)


def get_database_schema(include_workspace_fields: bool = True) -> List[Tuple[str, str]]:
    """
    Generate PostgreSQL schema from canonical definition.

    Args:
        include_workspace_fields: Whether to include workspace_id and workspace_name

    Returns:
        List of (column_name, sql_type) tuples
    """
    schema = []

    # Add workspace fields if requested (database-specific)
    if include_workspace_fields:
        schema.extend([
            ('workspace_id', 'VARCHAR(255) NOT NULL'),
            ('workspace_name', 'VARCHAR(255) NOT NULL'),
        ])

    # Add media plan fields
    for col_name, py_type, _ in MEDIAPLAN_SCHEMA_V3_0:
        # Primary keys get NOT NULL constraint
        is_pk = col_name in ['meta_id', 'campaign_id', 'lineitem_id']
        sql_type = python_type_to_sql(py_type, is_primary_key=is_pk)
        schema.append((col_name, sql_type))

    return schema


# =============================================================================
# Schema Validation
# =============================================================================

def validate_schema() -> None:
    """
    Validate schema definition for completeness and correctness.

    Raises:
        ValueError: If schema has issues
    """
    # Check for duplicate column names
    column_names = get_column_names()
    duplicates = [name for name in set(column_names) if column_names.count(name) > 1]
    if duplicates:
        raise ValueError(f"Duplicate column names found: {duplicates}")

    # Check that all types are valid
    valid_types = {str, int, Decimal, datetime, date, bool}
    for col_name, py_type, _ in MEDIAPLAN_SCHEMA_V3_0:
        if py_type not in valid_types:
            raise ValueError(f"Invalid type {py_type} for column {col_name}")

    print(f"✅ Schema validation passed: {len(column_names)} columns defined")


# Run validation on import
validate_schema()
