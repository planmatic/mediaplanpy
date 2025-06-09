"""
Excel exporter for mediaplanpy - Updated for v2.0 Schema Support Only.

This module provides functionality for exporting media plans to Excel format,
supporting only v2.0 schema with all new fields and dictionary configuration.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
from decimal import Decimal

import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment, NamedStyle
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.cell import Cell

from mediaplanpy.exceptions import StorageError
from mediaplanpy.workspace import WorkspaceManager

logger = logging.getLogger("mediaplanpy.excel.exporter")


def export_to_excel(media_plan: Dict[str, Any], path: Optional[str] = None,
                    template_path: Optional[str] = None,
                    include_documentation: bool = True,
                    workspace_manager: Optional[WorkspaceManager] = None,
                    **kwargs) -> str:
    """
    Export a media plan to Excel format using v2.0 schema.

    Args:
        media_plan: The media plan data to export (must be v2.0 schema)
        path: Optional path for the output file
        template_path: Optional path to an Excel template file
        include_documentation: Whether to include a documentation sheet
        workspace_manager: Optional WorkspaceManager for workspace storage
        **kwargs: Additional export options

    Returns:
        The path to the exported Excel file

    Raises:
        StorageError: If export fails or schema version is not v2.0
    """
    try:
        # Determine the path if not provided
        if not path:
            media_plan_id = media_plan.get("meta", {}).get("id", "media_plan")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"{media_plan_id}_{timestamp}.xlsx"

        # Validate schema version - only v2.0 supported
        schema_version = media_plan.get("meta", {}).get("schema_version", "unknown")
        if not _is_v2_schema_version(schema_version):
            raise StorageError(f"Excel export only supports v2.0 schema. Found: {schema_version}")

        # Create workbook
        if template_path and os.path.exists(template_path):
            workbook = openpyxl.load_workbook(template_path)
        else:
            workbook = _create_v2_workbook()

        # Populate the workbook with v2.0 data
        _populate_v2_workbook(workbook, media_plan, include_documentation)

        # Add validation and formatting
        _add_v2_validation_and_formatting(workbook)

        # Save the workbook
        if workspace_manager is not None:
            # Make sure workspace is loaded
            if not workspace_manager.is_loaded:
                workspace_manager.load()

            # Get storage backend
            storage_backend = workspace_manager.get_storage_backend()

            # Save to a temporary file first
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                tmp_path = tmp.name
                workbook.save(tmp_path)

            # Read the content
            with open(tmp_path, 'rb') as f:
                content = f.read()

            # Write to storage backend
            storage_backend.write_file(path, content)

            # Clean up temp file
            os.unlink(tmp_path)

            logger.info(f"Media plan exported to Excel in workspace storage: {path}")
        else:
            # Save locally
            workbook.save(path)
            logger.info(f"Media plan exported to Excel at: {path}")

        return path

    except Exception as e:
        raise StorageError(f"Failed to export media plan to Excel: {e}")


def _is_v2_schema_version(version: str) -> bool:
    """
    Check if the schema version is v2.0.

    Args:
        version: The schema version to check

    Returns:
        True if the version is v2.0, False otherwise
    """
    if not version:
        return False

    # Normalize version format (handle both "2.0" and "v2.0")
    normalized = version.replace("v", "") if version.startswith("v") else version
    return normalized == "2.0"


def _create_v2_workbook() -> Workbook:
    """
    Create a default workbook with v2.0 schema sheets.

    Returns:
        A new Workbook with v2.0 schema sheets
    """
    workbook = Workbook()

    # Rename default sheet to "Metadata"
    metadata_sheet = workbook.active
    metadata_sheet.title = "Metadata"

    # Create other required sheets for v2.0
    campaign_sheet = workbook.create_sheet("Campaign")
    lineitems_sheet = workbook.create_sheet("Line Items")
    dictionary_sheet = workbook.create_sheet("Dictionary")  # NEW for v2.0
    documentation_sheet = workbook.create_sheet("Documentation")

    # Create v2.0 styles
    _create_v2_styles(workbook)

    return workbook


def _create_v2_styles(workbook: Workbook) -> None:
    """
    Create styles for v2.0 Excel export.

    Args:
        workbook: The workbook to add styles to
    """
    # Header style
    header_style = NamedStyle(name="header_style")
    header_style.font = Font(bold=True, size=12, color="FFFFFF")
    header_style.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_style.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    workbook.add_named_style(header_style)

    # Data style
    data_style = NamedStyle(name="data_style")
    data_style.font = Font(size=11)
    data_style.alignment = Alignment(vertical="center")
    workbook.add_named_style(data_style)

    # Currency style
    currency_style = NamedStyle(name="currency_style")
    currency_style.font = Font(size=11)
    currency_style.number_format = "$#,##0.00"
    currency_style.alignment = Alignment(horizontal="right", vertical="center")
    workbook.add_named_style(currency_style)

    # Date style
    date_style = NamedStyle(name="date_style")
    date_style.font = Font(size=11)
    date_style.number_format = "YYYY-MM-DD"
    date_style.alignment = Alignment(horizontal="center", vertical="center")
    workbook.add_named_style(date_style)

    # Dictionary header style (for custom fields configuration)
    dict_header_style = NamedStyle(name="dict_header_style")
    dict_header_style.font = Font(bold=True, size=11, color="FFFFFF")
    dict_header_style.fill = PatternFill(start_color="5B9BD5", end_color="5B9BD5", fill_type="solid")
    dict_header_style.alignment = Alignment(horizontal="center", vertical="center")
    workbook.add_named_style(dict_header_style)


def _populate_v2_workbook(workbook: Workbook, media_plan: Dict[str, Any], include_documentation: bool) -> None:
    """
    Populate a workbook with v2.0 schema data.

    Args:
        workbook: The workbook to populate
        media_plan: The media plan data (v2.0 schema)
        include_documentation: Whether to include a documentation sheet
    """
    meta = media_plan.get("meta", {})
    campaign = media_plan.get("campaign", {})
    line_items = media_plan.get("lineitems", [])
    dictionary = media_plan.get("dictionary", {})  # NEW for v2.0

    # Populate all sheets
    _populate_v2_metadata_sheet(workbook["Metadata"], media_plan)
    _populate_v2_campaign_sheet(workbook["Campaign"], campaign)
    _populate_v2_lineitems_sheet(workbook["Line Items"], line_items)
    _populate_v2_dictionary_sheet(workbook["Dictionary"], dictionary)  # NEW for v2.0

    # Populate documentation sheet if needed
    if include_documentation:
        _populate_v2_documentation_sheet(workbook["Documentation"])
    elif "Documentation" in workbook.sheetnames:
        workbook.remove(workbook["Documentation"])


def _populate_v2_metadata_sheet(sheet, media_plan: Dict[str, Any]) -> None:
    """
    Populate the metadata sheet with v2.0 schema information.

    Args:
        sheet: The worksheet to populate
        media_plan: The media plan data
    """
    meta = media_plan.get("meta", {})

    # Set column widths
    sheet.column_dimensions["A"].width = 20
    sheet.column_dimensions["B"].width = 50

    # Add title
    sheet['A1'] = "Media Plan Metadata (v2.0)"
    sheet['A1'].style = "header_style"
    sheet.merge_cells('A1:B1')

    # Add v2.0 metadata fields
    row = 2
    sheet[f'A{row}'] = "Schema Version:"
    sheet[f'B{row}'] = "2.0"

    row += 1
    sheet[f'A{row}'] = "Media Plan ID:"
    sheet[f'B{row}'] = meta.get("id", "")

    row += 1
    sheet[f'A{row}'] = "Media Plan Name:"
    sheet[f'B{row}'] = meta.get("name", "")

    # v2.0: created_by_name is required
    row += 1
    sheet[f'A{row}'] = "Created By Name:"
    sheet[f'B{row}'] = meta.get("created_by_name", "")

    # v2.0: created_by_id is optional
    row += 1
    sheet[f'A{row}'] = "Created By ID:"
    sheet[f'B{row}'] = meta.get("created_by_id", "")

    row += 1
    sheet[f'A{row}'] = "Created At:"
    sheet[f'B{row}'] = meta.get("created_at", "")

    # v2.0: New status fields
    row += 1
    sheet[f'A{row}'] = "Is Current:"
    sheet[f'B{row}'] = meta.get("is_current", "")

    row += 1
    sheet[f'A{row}'] = "Is Archived:"
    sheet[f'B{row}'] = meta.get("is_archived", "")

    row += 1
    sheet[f'A{row}'] = "Parent ID:"
    sheet[f'B{row}'] = meta.get("parent_id", "")

    row += 1
    sheet[f'A{row}'] = "Export Date:"
    sheet[f'B{row}'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if "comments" in meta:
        row += 1
        sheet[f'A{row}'] = "Comments:"
        sheet[f'B{row}'] = meta.get("comments", "")


def _populate_v2_campaign_sheet(sheet, campaign: Dict[str, Any]) -> None:
    """
    Populate the campaign sheet with v2.0 schema information.

    Args:
        sheet: The worksheet to populate
        campaign: The campaign data
    """
    # Set column widths
    sheet.column_dimensions["A"].width = 25
    sheet.column_dimensions["B"].width = 50

    # Add title
    sheet['A1'] = "Campaign Information (v2.0)"
    sheet['A1'].style = "header_style"
    sheet.merge_cells('A1:B1')

    # Add campaign fields (existing + new v2.0 fields)
    row = 2
    sheet[f'A{row}'] = "Campaign ID:"
    sheet[f'B{row}'] = campaign.get("id", "")

    row += 1
    sheet[f'A{row}'] = "Campaign Name:"
    sheet[f'B{row}'] = campaign.get("name", "")

    row += 1
    sheet[f'A{row}'] = "Objective:"
    sheet[f'B{row}'] = campaign.get("objective", "")

    row += 1
    sheet[f'A{row}'] = "Start Date:"
    sheet[f'B{row}'] = campaign.get("start_date", "")
    sheet[f'B{row}'].style = "date_style"

    row += 1
    sheet[f'A{row}'] = "End Date:"
    sheet[f'B{row}'] = campaign.get("end_date", "")
    sheet[f'B{row}'].style = "date_style"

    row += 1
    sheet[f'A{row}'] = "Budget Total:"
    sheet[f'B{row}'] = campaign.get("budget_total", 0)
    sheet[f'B{row}'].style = "currency_style"

    # NEW v2.0: Budget currency
    row += 1
    sheet[f'A{row}'] = "Budget Currency:"
    sheet[f'B{row}'] = campaign.get("budget_currency", "")

    # NEW v2.0: Agency fields
    row += 1
    sheet[f'A{row}'] = "Agency ID:"
    sheet[f'B{row}'] = campaign.get("agency_id", "")

    row += 1
    sheet[f'A{row}'] = "Agency Name:"
    sheet[f'B{row}'] = campaign.get("agency_name", "")

    # NEW v2.0: Advertiser fields
    row += 1
    sheet[f'A{row}'] = "Advertiser ID:"
    sheet[f'B{row}'] = campaign.get("advertiser_id", "")

    row += 1
    sheet[f'A{row}'] = "Advertiser Name:"
    sheet[f'B{row}'] = campaign.get("advertiser_name", "")

    # Product fields (existing + new v2.0 product_id)
    row += 1
    sheet[f'A{row}'] = "Product ID:"
    sheet[f'B{row}'] = campaign.get("product_id", "")

    row += 1
    sheet[f'A{row}'] = "Product Name:"
    sheet[f'B{row}'] = campaign.get("product_name", "")

    row += 1
    sheet[f'A{row}'] = "Product Description:"
    sheet[f'B{row}'] = campaign.get("product_description", "")

    # NEW v2.0: Campaign type fields
    row += 1
    sheet[f'A{row}'] = "Campaign Type ID:"
    sheet[f'B{row}'] = campaign.get("campaign_type_id", "")

    row += 1
    sheet[f'A{row}'] = "Campaign Type Name:"
    sheet[f'B{row}'] = campaign.get("campaign_type_name", "")

    # NEW v2.0: Workflow status fields
    row += 1
    sheet[f'A{row}'] = "Workflow Status ID:"
    sheet[f'B{row}'] = campaign.get("workflow_status_id", "")

    row += 1
    sheet[f'A{row}'] = "Workflow Status Name:"
    sheet[f'B{row}'] = campaign.get("workflow_status_name", "")

    # Existing audience fields
    row += 1
    sheet[f'A{row}'] = "Audience Name:"
    sheet[f'B{row}'] = campaign.get("audience_name", "")

    row += 1
    sheet[f'A{row}'] = "Audience Age Start:"
    sheet[f'B{row}'] = campaign.get("audience_age_start", "")

    row += 1
    sheet[f'A{row}'] = "Audience Age End:"
    sheet[f'B{row}'] = campaign.get("audience_age_end", "")

    row += 1
    sheet[f'A{row}'] = "Audience Gender:"
    sheet[f'B{row}'] = campaign.get("audience_gender", "")

    row += 1
    sheet[f'A{row}'] = "Audience Interests:"
    interests = campaign.get("audience_interests", [])
    sheet[f'B{row}'] = ", ".join(interests) if interests else ""

    row += 1
    sheet[f'A{row}'] = "Location Type:"
    sheet[f'B{row}'] = campaign.get("location_type", "")

    row += 1
    sheet[f'A{row}'] = "Locations:"
    locations = campaign.get("locations", [])
    sheet[f'B{row}'] = ", ".join(locations) if locations else ""


def _populate_v2_lineitems_sheet(sheet, line_items: List[Dict[str, Any]]) -> None:
    """
    Populate the line items sheet with v2.0 schema data.

    Args:
        sheet: The worksheet to populate
        line_items: List of line item data
    """
    # Define field order for v2.0 schema (with all new fields)
    field_order = [
        # Required fields
        ("id", "ID"),
        ("name", "Name"),
        ("start_date", "Start Date"),
        ("end_date", "End Date"),
        ("cost_total", "Cost Total"),

        # Channel-related fields
        ("channel", "Channel"),
        ("channel_custom", "Channel Custom"),
        ("vehicle", "Vehicle"),
        ("vehicle_custom", "Vehicle Custom"),
        ("partner", "Partner"),
        ("partner_custom", "Partner Custom"),
        ("media_product", "Media Product"),
        ("media_product_custom", "Media Product Custom"),

        # Location fields
        ("location_type", "Location Type"),
        ("location_name", "Location Name"),

        # Target/format fields
        ("target_audience", "Target Audience"),
        ("adformat", "Ad Format"),
        ("adformat_custom", "Ad Format Custom"),

        # KPI fields
        ("kpi", "KPI"),
        ("kpi_custom", "KPI Custom"),

        # NEW v2.0: Dayparts and inventory fields
        ("dayparts", "Dayparts"),
        ("dayparts_custom", "Dayparts Custom"),
        ("inventory", "Inventory"),
        ("inventory_custom", "Inventory Custom"),
    ]

    # Add custom dimension fields
    for i in range(1, 11):
        field_order.append((f"dim_custom{i}", f"Dim Custom {i}"))

    # Cost fields (including new v2.0 cost_currency)
    cost_fields = [
        ("cost_currency", "Cost Currency"),  # NEW v2.0
        ("cost_media", "Cost Media"),
        ("cost_buying", "Cost Buying"),
        ("cost_platform", "Cost Platform"),
        ("cost_data", "Cost Data"),
        ("cost_creative", "Cost Creative"),
    ]
    field_order.extend(cost_fields)

    # Add custom cost fields
    for i in range(1, 11):
        field_order.append((f"cost_custom{i}", f"Cost Custom {i}"))

    # Metric fields - existing 3 + NEW 17 v2.0 standard metrics in schema order
    metric_fields = [
        # Existing 3 metrics
        ("metric_impressions", "Impressions"),
        ("metric_clicks", "Clicks"),
        ("metric_views", "Views"),

        # NEW v2.0: 17 new standard metrics in schema order
        ("metric_engagements", "Engagements"),
        ("metric_followers", "Followers"),
        ("metric_visits", "Visits"),
        ("metric_leads", "Leads"),
        ("metric_sales", "Sales"),
        ("metric_add_to_cart", "Add to Cart"),
        ("metric_app_install", "App Install"),
        ("metric_application_start", "Application Start"),
        ("metric_application_complete", "Application Complete"),
        ("metric_contact_us", "Contact Us"),
        ("metric_download", "Download"),
        ("metric_signup", "Signup"),
        ("metric_max_daily_spend", "Max Daily Spend"),
        ("metric_max_daily_impressions", "Max Daily Impressions"),
        ("metric_audience_size", "Audience Size"),
    ]
    field_order.extend(metric_fields)

    # Add custom metric fields
    for i in range(1, 11):
        field_order.append((f"metric_custom{i}", f"Metric Custom {i}"))

    # Determine which fields are actually present in line items
    fields_present = set()
    for line_item in line_items:
        fields_present.update(line_item.keys())

    # Filter field order to only include present fields (always include required fields)
    required_fields = {"id", "name", "start_date", "end_date", "cost_total"}
    active_fields = []
    for field_name, header_name in field_order:
        if field_name in required_fields or field_name in fields_present:
            active_fields.append((field_name, header_name))

    # Set column widths
    for col_idx in range(1, len(active_fields) + 1):
        width = 15
        field_name = active_fields[col_idx - 1][0]
        if field_name in ["name", "media_product", "media_product_custom", "target_audience"]:
            width = 25
        elif field_name in ["partner", "partner_custom", "vehicle", "vehicle_custom"]:
            width = 20
        sheet.column_dimensions[get_column_letter(col_idx)].width = width

    # Add headers
    for col_idx, (field_name, header_name) in enumerate(active_fields, 1):
        cell = sheet.cell(row=1, column=col_idx, value=header_name)
        cell.style = "header_style"

    # Add line item data
    for row_idx, line_item in enumerate(line_items, 2):
        for col_idx, (field_name, header_name) in enumerate(active_fields, 1):
            value = line_item.get(field_name)

            # Skip None values
            if value is None:
                continue

            # Apply appropriate formatting based on field type
            if field_name in ["start_date", "end_date"]:
                cell = sheet.cell(row=row_idx, column=col_idx, value=value)
                cell.style = "date_style"
            elif field_name.startswith("cost") or field_name.startswith("metric") or field_name == "cost_total":
                # Numeric fields
                cell = sheet.cell(row=row_idx, column=col_idx, value=value)
                if field_name.startswith("cost"):
                    cell.style = "currency_style"
                # Metrics remain as regular numbers
            else:
                # String fields
                sheet.cell(row=row_idx, column=col_idx, value=value)


def _populate_v2_dictionary_sheet(sheet, dictionary: Dict[str, Any]) -> None:
    """
    Populate the dictionary configuration sheet (NEW for v2.0).

    Args:
        sheet: The worksheet to populate
        dictionary: The dictionary configuration data
    """
    # Set column widths
    sheet.column_dimensions["A"].width = 20
    sheet.column_dimensions["B"].width = 15
    sheet.column_dimensions["C"].width = 40
    sheet.column_dimensions["D"].width = 15

    # Add title
    sheet['A1'] = "Custom Fields Configuration (v2.0)"
    sheet['A1'].style = "header_style"
    sheet.merge_cells('A1:D1')

    # Add headers
    row = 2
    sheet[f'A{row}'] = "Field Name"
    sheet[f'B{row}'] = "Field Type"
    sheet[f'C{row}'] = "Caption"
    sheet[f'D{row}'] = "Status"

    for col in ['A', 'B', 'C', 'D']:
        sheet[f'{col}{row}'].style = "dict_header_style"

    # Add all possible custom fields with their current configuration
    row = 3

    # Custom dimensions
    custom_dimensions = dictionary.get("custom_dimensions", {})
    for i in range(1, 11):
        field_name = f"dim_custom{i}"
        config = custom_dimensions.get(field_name, {"status": "disabled", "caption": ""})

        sheet[f'A{row}'] = field_name
        sheet[f'B{row}'] = "Dimension"
        sheet[f'C{row}'] = config.get("caption", "")
        sheet[f'D{row}'] = config.get("status", "disabled")
        row += 1

    # Custom metrics
    custom_metrics = dictionary.get("custom_metrics", {})
    for i in range(1, 11):
        field_name = f"metric_custom{i}"
        config = custom_metrics.get(field_name, {"status": "disabled", "caption": ""})

        sheet[f'A{row}'] = field_name
        sheet[f'B{row}'] = "Metric"
        sheet[f'C{row}'] = config.get("caption", "")
        sheet[f'D{row}'] = config.get("status", "disabled")
        row += 1

    # Custom costs
    custom_costs = dictionary.get("custom_costs", {})
    for i in range(1, 11):
        field_name = f"cost_custom{i}"
        config = custom_costs.get(field_name, {"status": "disabled", "caption": ""})

        sheet[f'A{row}'] = field_name
        sheet[f'B{row}'] = "Cost"
        sheet[f'C{row}'] = config.get("caption", "")
        sheet[f'D{row}'] = config.get("status", "disabled")
        row += 1

    # Add instructions
    row += 2
    sheet[f'A{row}'] = "Instructions:"
    sheet[f'A{row}'].font = Font(bold=True)
    sheet.merge_cells(f'A{row}:D{row}')

    row += 1
    sheet[f'A{row}'] = "- Set Status to 'enabled' or 'disabled'"
    sheet.merge_cells(f'A{row}:D{row}')

    row += 1
    sheet[f'A{row}'] = "- Caption is required when Status is 'enabled'"
    sheet.merge_cells(f'A{row}:D{row}')

    row += 1
    sheet[f'A{row}'] = "- Caption should describe what the custom field represents"
    sheet.merge_cells(f'A{row}:D{row}')


def _populate_v2_documentation_sheet(sheet) -> None:
    """
    Populate the documentation sheet with v2.0 schema information.

    Args:
        sheet: The worksheet to populate
    """
    # Set column widths
    sheet.column_dimensions["A"].width = 25
    sheet.column_dimensions["B"].width = 15
    sheet.column_dimensions["C"].width = 50
    sheet.column_dimensions["D"].width = 15

    # Add title
    sheet['A1'] = "Media Plan Excel Documentation (v2.0)"
    sheet['A1'].style = "header_style"
    sheet.merge_cells('A1:D1')

    # Add documentation content
    row = 2
    sheet[f'A{row}'] = "Schema Version:"
    sheet[f'B{row}'] = "2.0"

    row += 1
    sheet[f'A{row}'] = "Export Date:"
    sheet[f'B{row}'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row += 2
    sheet[f'A{row}'] = "Instructions:"
    sheet[f'B{row}'] = "This Excel file contains a media plan following the Media Plan Open Data Standard v2.0."
    sheet.merge_cells(f'B{row}:D{row}')

    row += 1
    sheet[f'B{row}'] = "Use the tabs to navigate through different sections of the media plan."
    sheet.merge_cells(f'B{row}:D{row}')

    row += 2
    sheet[f'A{row}'] = "Sheets:"
    sheet[f'B{row}'] = "Metadata: Contains information about the media plan itself."
    sheet.merge_cells(f'B{row}:D{row}')

    row += 1
    sheet[f'B{row}'] = "Campaign: Contains campaign details and settings."
    sheet.merge_cells(f'B{row}:D{row}')

    row += 1
    sheet[f'B{row}'] = "Line Items: Contains all line items in the campaign."
    sheet.merge_cells(f'B{row}:D{row}')

    row += 1
    sheet[f'B{row}'] = "Dictionary: Configuration for custom fields (NEW in v2.0)."
    sheet.merge_cells(f'B{row}:D{row}')

    # v2.0 field documentation
    row += 2
    sheet[f'A{row}'] = "v2.0 New Features"
    sheet[f'A{row}'].font = Font(bold=True, size=12)
    sheet.merge_cells(f'A{row}:D{row}')

    row += 1
    sheet[f'A{row}'] = "Column Name"
    sheet[f'B{row}'] = "Data Type"
    sheet[f'C{row}'] = "Description"
    sheet[f'D{row}'] = "Required"
    for col in ['A', 'B', 'C', 'D']:
        sheet[f'{col}{row}'].style = "header_style"

    # Define v2.0 new fields documentation
    v2_fields_documentation = [
        # Campaign new fields
        ("Budget Currency", "Text", "Currency code for campaign budget (e.g., USD, EUR)", "No"),
        ("Agency ID", "Text", "Unique identifier for the agency", "No"),
        ("Agency Name", "Text", "Name of the agency managing the campaign", "No"),
        ("Advertiser ID", "Text", "Unique identifier for the advertiser/client", "No"),
        ("Advertiser Name", "Text", "Name of the advertiser/client organization", "No"),
        ("Product ID", "Text", "Unique identifier for the product being advertised", "No"),
        ("Campaign Type ID", "Text", "Unique identifier for campaign type classification", "No"),
        ("Campaign Type Name", "Text", "Campaign type (e.g., Brand Awareness, Performance)", "No"),
        ("Workflow Status ID", "Text", "Unique identifier for workflow status", "No"),
        ("Workflow Status Name", "Text", "Workflow status (e.g., Draft, Approved, Live)", "No"),

        # Line item new fields
        ("Cost Currency", "Text", "Currency code for line item costs", "No"),
        ("Dayparts", "Text", "Time periods for ad delivery (e.g., Primetime, Morning)", "No"),
        ("Dayparts Custom", "Text", "Custom daypart specification", "No"),
        ("Inventory", "Text", "Type of inventory (e.g., Premium, Remnant)", "No"),
        ("Inventory Custom", "Text", "Custom inventory specification", "No"),

        # New standard metrics (17 new ones)
        ("Engagements", "Number", "User engagements (likes, shares, comments)", "No"),
        ("Followers", "Number", "New followers gained", "No"),
        ("Visits", "Number", "Website visits or page visits", "No"),
        ("Leads", "Number", "Leads generated", "No"),
        ("Sales", "Number", "Sales or purchases", "No"),
        ("Add to Cart", "Number", "Add-to-cart actions", "No"),
        ("App Install", "Number", "App installations", "No"),
        ("Application Start", "Number", "Application forms started", "No"),
        ("Application Complete", "Number", "Application forms completed", "No"),
        ("Contact Us", "Number", "Contact form submissions", "No"),
        ("Download", "Number", "Downloads (files, apps, content)", "No"),
        ("Signup", "Number", "Signups or registrations", "No"),
        ("Max Daily Spend", "Number", "Maximum daily spend limit", "No"),
        ("Max Daily Impressions", "Number", "Maximum daily impressions limit", "No"),
        ("Audience Size", "Number", "Size of targetable audience", "No"),
    ]

    # Populate the field documentation
    for field_name, data_type, description, required in v2_fields_documentation:
        row += 1
        sheet[f'A{row}'] = field_name
        sheet[f'B{row}'] = data_type
        sheet[f'C{row}'] = description
        sheet[f'D{row}'] = required

        # Apply alternating row colors for readability
        if row % 2 == 0:
            for col in ['A', 'B', 'C', 'D']:
                sheet[f'{col}{row}'].fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")

    # Add additional v2.0 information
    row += 2
    sheet[f'A{row}'] = "Dictionary Configuration:"
    sheet[f'B{row}'] = "v2.0 introduces custom field configuration via the Dictionary sheet."
    sheet.merge_cells(f'B{row}:D{row}')

    row += 1
    sheet[f'B{row}'] = "- Configure which custom fields are enabled/disabled"
    sheet.merge_cells(f'B{row}:D{row}')

    row += 1
    sheet[f'B{row}'] = "- Add captions to describe what each custom field represents"
    sheet.merge_cells(f'B{row}:D{row}')

    row += 2
    sheet[f'A{row}'] = "Support:"
    sheet[f'B{row}'] = "For more information, see: https://github.com/laurent-colard-l5i/mediaplanschema"
    sheet.merge_cells(f'B{row}:D{row}')


def _add_v2_validation_and_formatting(workbook: Workbook) -> None:
    """
    Add data validation and formatting for v2.0 Excel export.

    Args:
        workbook: The workbook to add validation to
    """
    line_items_sheet = workbook["Line Items"]
    dictionary_sheet = workbook["Dictionary"]

    # Channel validation (existing)
    channel_validation = DataValidation(
        type="list",
        formula1='"social,search,display,video,audio,tv,ooh,print,other"',
        allow_blank=True
    )
    line_items_sheet.add_data_validation(channel_validation)
    # Find channel column dynamically
    for col in range(1, line_items_sheet.max_column + 1):
        if line_items_sheet.cell(1, col).value == "Channel":
            channel_validation.add(f'{get_column_letter(col)}2:{get_column_letter(col)}1000')
            break

    # KPI validation (existing)
    kpi_validation = DataValidation(
        type="list",
        formula1='"CPM,CPC,CPA,CTR,CPV,CPI,ROAS,other"',
        allow_blank=True
    )
    line_items_sheet.add_data_validation(kpi_validation)
    # Find KPI column dynamically
    for col in range(1, line_items_sheet.max_column + 1):
        if line_items_sheet.cell(1, col).value == "KPI":
            kpi_validation.add(f'{get_column_letter(col)}2:{get_column_letter(col)}1000')
            break

    # Location type validation (existing)
    location_validation = DataValidation(
        type="list",
        formula1='"Country,State"',
        allow_blank=True
    )
    line_items_sheet.add_data_validation(location_validation)
    # Find Location Type column dynamically
    for col in range(1, line_items_sheet.max_column + 1):
        if line_items_sheet.cell(1, col).value == "Location Type":
            location_validation.add(f'{get_column_letter(col)}2:{get_column_letter(col)}1000')
            break

    # NEW v2.0: Dictionary Status validation
    status_validation = DataValidation(
        type="list",
        formula1='"enabled,disabled"',
        allow_blank=False
    )
    dictionary_sheet.add_data_validation(status_validation)
    status_validation.add('D3:D32')  # Status column for all 30 custom fields