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
    Create styles for v2.0 Excel export including formula column styling.

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

    # Grey font style for formula columns
    grey_font_style = NamedStyle(name="grey_font_style")
    grey_font_style.font = Font(size=11, color="808080")  # Grey color
    grey_font_style.alignment = Alignment(vertical="center")
    workbook.add_named_style(grey_font_style)


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
    Populate the line items sheet with v2.0 schema data including dynamic calculated columns.

    Args:
        sheet: The worksheet to populate
        line_items: List of line item data
    """
    # Determine which fields are actually present in line items
    fields_present = set()
    for line_item in line_items:
        fields_present.update(line_item.keys())

    # Define base field order for v2.0 schema
    base_field_order = [
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

        # Dayparts and inventory fields
        ("dayparts", "Dayparts"),
        ("dayparts_custom", "Dayparts Custom"),
        ("inventory", "Inventory"),
        ("inventory_custom", "Inventory Custom"),
    ]

    # Add custom dimension fields
    for i in range(1, 11):
        base_field_order.append((f"dim_custom{i}", f"Dim Custom {i}"))

    # Cost fields - we'll insert calculated columns here
    cost_fields = [
        ("cost_currency", "Cost Currency"),
        ("cost_media", "Cost Media"),
        ("cost_buying", "Cost Buying"),
        ("cost_platform", "Cost Platform"),
        ("cost_data", "Cost Data"),
        ("cost_creative", "Cost Creative"),
    ]

    # Add custom cost fields
    for i in range(1, 11):
        cost_fields.append((f"cost_custom{i}", f"Cost Custom {i}"))

    # Performance metric fields - we'll insert calculated columns here
    performance_fields = [
        ("metric_impressions", "Impressions"),
        ("metric_clicks", "Clicks"),
        ("metric_views", "Views"),
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
    ]

    # Add custom metric fields
    for i in range(1, 11):
        performance_fields.append((f"metric_custom{i}", f"Metric Custom {i}"))

    # Determine which cost and performance metrics are present
    present_cost_fields = []
    present_performance_fields = []

    # Check cost fields (excluding cost_total and cost_currency which don't need calculated columns)
    for field_name, header_name in cost_fields:
        if field_name != "cost_currency" and (field_name in fields_present):
            present_cost_fields.append((field_name, header_name))

    # Check performance fields (excluding max daily fields and audience size which are limits, not performance)
    for field_name, header_name in performance_fields:
        if field_name in fields_present:
            present_performance_fields.append((field_name, header_name))

    # Build dynamic field order with calculated columns
    dynamic_field_order = []

    # Add base fields (up to custom dimensions)
    for field_name, header_name in base_field_order:
        if field_name in fields_present or field_name in {"id", "name", "start_date", "end_date", "cost_total"}:
            dynamic_field_order.append((field_name, header_name, "base"))

    # Add cost fields with calculated columns
    if "cost_currency" in fields_present:
        dynamic_field_order.append(("cost_currency", "Cost Currency", "base"))

    for field_name, header_name in present_cost_fields:
        # Add percentage column before actual cost column
        calc_field_name = f"{field_name}_pct"
        calc_header_name = f"{header_name} %"
        dynamic_field_order.append((calc_field_name, calc_header_name, "calculated"))

        # Add actual cost column
        dynamic_field_order.append((field_name, header_name, "formula"))

    # Add performance fields with calculated columns
    for field_name, header_name in present_performance_fields:
        # Add cost-per-unit column before actual metric column
        calc_field_name = f"{field_name}_cpu"

        # Special handling for impressions (CPM)
        if field_name == "metric_impressions":
            calc_header_name = "Cost per 1000 Impressions"
        else:
            # Convert metric_clicks -> Cost per Click, etc.
            metric_name = header_name  # Already clean (e.g., "Clicks")
            if metric_name.endswith('s') and metric_name not in ['Views', 'Sales']:
                metric_name = metric_name.rstrip('s')  # Remove plural 's'
            calc_header_name = f"Cost per {metric_name}"

        dynamic_field_order.append((calc_field_name, calc_header_name, "calculated"))

        # Add actual metric column
        dynamic_field_order.append((field_name, header_name, "formula"))

    # Add remaining metric fields that don't get calculated columns
    remaining_metrics = [
        ("metric_max_daily_spend", "Max Daily Spend"),
        ("metric_max_daily_impressions", "Max Daily Impressions"),
        ("metric_audience_size", "Audience Size"),
    ]

    for field_name, header_name in remaining_metrics:
        if field_name in fields_present:
            dynamic_field_order.append((field_name, header_name, "base"))

    # Set column widths based on field type
    for col_idx, (field_name, header_name, field_type) in enumerate(dynamic_field_order, 1):
        width = 15
        if field_name in ["name", "media_product", "media_product_custom", "target_audience"]:
            width = 25
        elif field_name in ["partner", "partner_custom", "vehicle", "vehicle_custom"]:
            width = 20
        elif field_type == "calculated":
            width = 18  # Slightly wider for calculated columns
        sheet.column_dimensions[get_column_letter(col_idx)].width = width

    # Add headers with appropriate styling
    for col_idx, (field_name, header_name, field_type) in enumerate(dynamic_field_order, 1):
        cell = sheet.cell(row=1, column=col_idx, value=header_name)
        cell.style = "header_style"

    # Add line item data with calculated values and formulas
    for row_idx, line_item in enumerate(line_items, 2):
        cost_total_col = None

        # First pass: populate base values and find cost_total column
        for col_idx, (field_name, header_name, field_type) in enumerate(dynamic_field_order, 1):
            if field_name == "cost_total":
                cost_total_col = col_idx

            if field_type == "base":
                value = line_item.get(field_name)
                if value is None:
                    continue

                # Apply appropriate formatting based on field type
                if field_name in ["start_date", "end_date"]:
                    cell = sheet.cell(row=row_idx, column=col_idx, value=value)
                    cell.style = "date_style"
                elif field_name.startswith("cost") or field_name.startswith("metric") or field_name == "cost_total":
                    cell = sheet.cell(row=row_idx, column=col_idx, value=value)
                    if field_name.startswith("cost"):
                        cell.style = "currency_style"
                else:
                    sheet.cell(row=row_idx, column=col_idx, value=value)

        # Second pass: populate calculated columns and formulas
        cost_total_value = line_item.get("cost_total", 0)
        cost_total_cell_ref = f"{get_column_letter(cost_total_col)}{row_idx}" if cost_total_col else "0"

        for col_idx, (field_name, header_name, field_type) in enumerate(dynamic_field_order, 1):
            if field_type == "calculated":
                if field_name.endswith("_pct"):
                    # Cost percentage calculation
                    base_field = field_name.replace("_pct", "")
                    cost_value = line_item.get(base_field, 0)

                    if cost_total_value and cost_total_value != 0:
                        percentage = (cost_value / cost_total_value)
                    else:
                        percentage = 0

                    cell = sheet.cell(row=row_idx, column=col_idx, value=percentage)
                    cell.number_format = '0.0%'  # Percentage format with 1 decimal place

                elif field_name.endswith("_cpu"):
                    # Cost-per-unit calculation
                    base_field = field_name.replace("_cpu", "")
                    metric_value = line_item.get(base_field, 0)

                    if metric_value and metric_value != 0:
                        if base_field == "metric_impressions":
                            # CPM calculation (cost per 1000 impressions)
                            cpu_value = (cost_total_value / metric_value) * 1000
                        else:
                            cpu_value = cost_total_value / metric_value
                    else:
                        cpu_value = 0

                    cell = sheet.cell(row=row_idx, column=col_idx, value=cpu_value)
                    cell.number_format = '$0.00'
                    # cell.style = "currency_style"

            elif field_type == "formula":
                if field_name.startswith("cost_") and field_name != "cost_total" and field_name != "cost_currency":
                    # Cost field formula: cost_total * percentage
                    pct_col_idx = None
                    for idx, (fname, _, ftype) in enumerate(dynamic_field_order, 1):
                        if fname == f"{field_name}_pct":
                            pct_col_idx = idx
                            break

                    if pct_col_idx:
                        pct_cell_ref = f"{get_column_letter(pct_col_idx)}{row_idx}"
                        formula = f"={cost_total_cell_ref}*{pct_cell_ref}"
                        cell = sheet.cell(row=row_idx, column=col_idx, value=formula)
                        cell.style = "currency_style"
                        # Apply grey font formatting for formula columns
                        cell.font = Font(color="808080")  # Grey color

                elif field_name.startswith("metric_"):
                    # Performance metric formula
                    cpu_col_idx = None
                    for idx, (fname, _, ftype) in enumerate(dynamic_field_order, 1):
                        if fname == f"{field_name}_cpu":
                            cpu_col_idx = idx
                            break

                    if cpu_col_idx:
                        cpu_cell_ref = f"{get_column_letter(cpu_col_idx)}{row_idx}"

                        if field_name == "metric_impressions":
                            # Special formula for impressions (divide by 1000 since CPU is per 1000)
                            formula = f"=IF({cpu_cell_ref}=0,0,{cost_total_cell_ref}/{cpu_cell_ref}*1000)"
                        else:
                            formula = f"=IF({cpu_cell_ref}=0,0,{cost_total_cell_ref}/{cpu_cell_ref})"

                        cell = sheet.cell(row=row_idx, column=col_idx, value=formula)
                        # Apply grey font formatting for formula columns
                        cell.font = Font(color="808080")  # Grey color

    logger.info(
        f"Created {len(dynamic_field_order)} columns with {len(present_cost_fields)} cost calculations and {len(present_performance_fields)} performance calculations")


def _populate_v2_dictionary_sheet(sheet, dictionary: Dict[str, Any]) -> None:
    """
    Populate the dictionary configuration sheet (NEW for v2.0) with enhanced column information.

    Args:
        sheet: The worksheet to populate
        dictionary: The dictionary configuration data
    """
    # Set column widths
    sheet.column_dimensions["A"].width = 20  # Field Name
    sheet.column_dimensions["B"].width = 15  # Field Type
    sheet.column_dimensions["C"].width = 20  # Column Name (NEW)
    sheet.column_dimensions["D"].width = 40  # Caption
    sheet.column_dimensions["E"].width = 15  # Status

    # Add title
    sheet['A1'] = "Custom Fields Configuration (v2.0)"
    sheet['A1'].style = "header_style"
    sheet.merge_cells('A1:E1')

    # Add headers
    row = 2
    sheet[f'A{row}'] = "Field Name"
    sheet[f'B{row}'] = "Field Type"
    sheet[f'C{row}'] = "Column Name"  # NEW COLUMN
    sheet[f'D{row}'] = "Caption"
    sheet[f'E{row}'] = "Status"

    for col in ['A', 'B', 'C', 'D', 'E']:
        sheet[f'{col}{row}'].style = "dict_header_style"

    # Add all possible custom fields with their current configuration
    row = 3

    # Custom dimensions
    custom_dimensions = dictionary.get("custom_dimensions", {})
    for i in range(1, 11):
        field_name = f"dim_custom{i}"
        config = custom_dimensions.get(field_name, {"status": "disabled", "caption": ""})
        column_name = f"Dim Custom {i}"  # This is what should appear in Line Items sheet

        sheet[f'A{row}'] = field_name
        sheet[f'B{row}'] = "Dimension"
        sheet[f'C{row}'] = column_name  # NEW: Show expected column header
        sheet[f'D{row}'] = config.get("caption", "")
        sheet[f'E{row}'] = config.get("status", "disabled")
        row += 1

    # Custom metrics
    custom_metrics = dictionary.get("custom_metrics", {})
    for i in range(1, 11):
        field_name = f"metric_custom{i}"
        config = custom_metrics.get(field_name, {"status": "disabled", "caption": ""})
        column_name = f"Metric Custom {i}"  # This is what should appear in Line Items sheet

        sheet[f'A{row}'] = field_name
        sheet[f'B{row}'] = "Metric"
        sheet[f'C{row}'] = column_name  # NEW: Show expected column header
        sheet[f'D{row}'] = config.get("caption", "")
        sheet[f'E{row}'] = config.get("status", "disabled")
        row += 1

    # Custom costs
    custom_costs = dictionary.get("custom_costs", {})
    for i in range(1, 11):
        field_name = f"cost_custom{i}"
        config = custom_costs.get(field_name, {"status": "disabled", "caption": ""})
        column_name = f"Cost Custom {i}"  # This is what should appear in Line Items sheet

        sheet[f'A{row}'] = field_name
        sheet[f'B{row}'] = "Cost"
        sheet[f'C{row}'] = column_name  # NEW: Show expected column header
        sheet[f'D{row}'] = config.get("caption", "")
        sheet[f'E{row}'] = config.get("status", "disabled")
        row += 1

    # Add instructions
    row += 2
    sheet[f'A{row}'] = "Instructions:"
    sheet[f'A{row}'].font = Font(bold=True)
    sheet.merge_cells(f'A{row}:E{row}')

    row += 1
    sheet[f'A{row}'] = "- Set Status to 'enabled' or 'disabled'"
    sheet.merge_cells(f'A{row}:E{row}')

    row += 1
    sheet[f'A{row}'] = "- Caption is required when Status is 'enabled'"
    sheet.merge_cells(f'A{row}:E{row}')

    row += 1
    sheet[f'A{row}'] = "- Caption should describe what the custom field represents"
    sheet.merge_cells(f'A{row}:E{row}')

    row += 1
    sheet[f'A{row}'] = "- Use the 'Column Name' exactly as shown when importing from Excel"
    sheet.merge_cells(f'A{row}:E{row}')


def _populate_v2_documentation_sheet(sheet) -> None:
    """
    Populate the documentation sheet with comprehensive v2.0 schema information.

    Args:
        sheet: The worksheet to populate
    """
    # Set column widths - updated for new Field Name column
    sheet.column_dimensions["A"].width = 25  # Column Name
    sheet.column_dimensions["B"].width = 20  # Field Name (NEW)
    sheet.column_dimensions["C"].width = 15  # Data Type
    sheet.column_dimensions["D"].width = 45  # Description (slightly reduced to fit)
    sheet.column_dimensions["E"].width = 12  # Required

    # Add title
    sheet['A1'] = "Media Plan Excel Documentation (v2.0)"
    sheet['A1'].style = "header_style"
    sheet.merge_cells('A1:E1')  # Updated merge range

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
    sheet.merge_cells(f'B{row}:E{row}')  # Updated merge range

    row += 1
    sheet[f'B{row}'] = "Use the tabs to navigate through different sections of the media plan."
    sheet.merge_cells(f'B{row}:E{row}')  # Updated merge range

    row += 2
    sheet[f'A{row}'] = "Sheets:"
    sheet[f'B{row}'] = "Metadata: Contains information about the media plan itself."
    sheet.merge_cells(f'B{row}:E{row}')  # Updated merge range

    row += 1
    sheet[f'B{row}'] = "Campaign: Contains campaign details and settings."
    sheet.merge_cells(f'B{row}:E{row}')  # Updated merge range

    row += 1
    sheet[f'B{row}'] = "Line Items: Contains all line items in the campaign."
    sheet.merge_cells(f'B{row}:E{row}')  # Updated merge range

    row += 1
    sheet[f'B{row}'] = "Dictionary: Configuration for custom fields (NEW in v2.0)."
    sheet.merge_cells(f'B{row}:E{row}')  # Updated merge range

    # Comprehensive field documentation header
    row += 2
    sheet[f'A{row}'] = "Supported Line Item Columns"
    sheet[f'A{row}'].font = Font(bold=True, size=12)
    sheet.merge_cells(f'A{row}:E{row}')  # Updated merge range

    row += 1
    sheet[f'A{row}'] = "Column Name"
    sheet[f'B{row}'] = "Field Name"  # NEW COLUMN
    sheet[f'C{row}'] = "Data Type"
    sheet[f'D{row}'] = "Description"
    sheet[f'E{row}'] = "Required"
    for col in ['A', 'B', 'C', 'D', 'E']:
        sheet[f'{col}{row}'].style = "header_style"

    # Comprehensive field documentation in schema order with field names
    all_fields_documentation = [
        # Required fields (in schema order)
        ("ID", "id", "Text", "Unique identifier for the line item", "Yes"),
        ("Name", "name", "Text", "Human-readable name for the line item", "Yes"),
        ("Start Date", "start_date", "Date", "Line item start date in YYYY-MM-DD format", "Yes"),
        ("End Date", "end_date", "Date", "Line item end date in YYYY-MM-DD format", "Yes"),
        ("Cost Total", "cost_total", "Number", "Total cost for the line item including all cost components", "Yes"),

        # Channel-related fields (in schema order)
        ("Channel", "channel", "Text", "Media channel for the line item (e.g., Digital, TV, Radio, Print)", "No"),
        ("Channel Custom", "channel_custom", "Text",
         "Custom channel specification when standard channel options don't apply", "No"),
        ("Vehicle", "vehicle", "Text", "Media vehicle or platform (e.g., Facebook, Google, CNN, Spotify)", "No"),
        ("Vehicle Custom", "vehicle_custom", "Text",
         "Custom vehicle specification when standard vehicle options don't apply", "No"),
        ("Partner", "partner", "Text", "Media partner or vendor handling the placement", "No"),
        ("Partner Custom", "partner_custom", "Text",
         "Custom partner specification when standard partner options don't apply", "No"),
        ("Media Product", "media_product", "Text", "Specific media product or ad unit being purchased", "No"),
        ("Media Product Custom", "media_product_custom", "Text",
         "Custom media product specification when standard options don't apply", "No"),

        # Location fields (in schema order)
        ("Location Type", "location_type", "Text",
         "Geographic scope type for the line item targeting (Country or State)", "No"),
        ("Location Name", "location_name", "Text", "Name of the geographic location being targeted", "No"),

        # Target/format fields (in schema order)
        ("Target Audience", "target_audience", "Text", "Description of the target audience for this line item", "No"),
        ("Ad Format", "adformat", "Text", "Creative format or ad type (e.g., Banner, Video, Native)", "No"),
        ("Ad Format Custom", "adformat_custom", "Text",
         "Custom ad format specification when standard formats don't apply", "No"),
        ("KPI", "kpi", "Text", "Primary key performance indicator for the line item", "No"),
        ("KPI Custom", "kpi_custom", "Text", "Custom KPI specification when standard KPIs don't apply", "No"),

        # Dayparts and inventory fields (NEW in v2.0, in schema order)
        ("Dayparts", "dayparts", "Text", "Time periods when the ad should run (e.g., Primetime, Morning, All Day)",
         "No"),
        (
        "Dayparts Custom", "dayparts_custom", "Text", "Custom daypart specification when standard dayparts don't apply",
        "No"),
        ("Inventory", "inventory", "Text", "Type of inventory or placement being purchased", "No"),
        ("Inventory Custom", "inventory_custom", "Text",
         "Custom inventory specification when standard inventory types don't apply", "No"),

        # Custom dimension fields (dim_custom1-10, in schema order)
        ("Dim Custom 1", "dim_custom1", "Text", "Custom dimension field 1 - configuration defined in dictionary schema",
         "No"),
        ("Dim Custom 2", "dim_custom2", "Text", "Custom dimension field 2 - configuration defined in dictionary schema",
         "No"),
        ("Dim Custom 3", "dim_custom3", "Text", "Custom dimension field 3 - configuration defined in dictionary schema",
         "No"),
        ("Dim Custom 4", "dim_custom4", "Text", "Custom dimension field 4 - configuration defined in dictionary schema",
         "No"),
        ("Dim Custom 5", "dim_custom5", "Text", "Custom dimension field 5 - configuration defined in dictionary schema",
         "No"),
        ("Dim Custom 6", "dim_custom6", "Text", "Custom dimension field 6 - configuration defined in dictionary schema",
         "No"),
        ("Dim Custom 7", "dim_custom7", "Text", "Custom dimension field 7 - configuration defined in dictionary schema",
         "No"),
        ("Dim Custom 8", "dim_custom8", "Text", "Custom dimension field 8 - configuration defined in dictionary schema",
         "No"),
        ("Dim Custom 9", "dim_custom9", "Text", "Custom dimension field 9 - configuration defined in dictionary schema",
         "No"),
        ("Dim Custom 10", "dim_custom10", "Text",
         "Custom dimension field 10 - configuration defined in dictionary schema", "No"),

        # Cost fields (in schema order, cost_currency is NEW in v2.0)
        ("Cost Currency", "cost_currency", "Text",
         "Currency code for all cost fields in this line item (e.g., USD, EUR, GBP)", "No"),
        ("Cost Media", "cost_media", "Number", "Media cost component (working media spend)", "No"),
        ("Cost Buying", "cost_buying", "Number", "Media buying/trading cost component", "No"),
        ("Cost Platform", "cost_platform", "Number", "Platform or technology cost component", "No"),
        ("Cost Data", "cost_data", "Number", "Data cost component (audience data, targeting data, etc.)", "No"),
        ("Cost Creative", "cost_creative", "Number", "Creative production and development cost component", "No"),

        # Custom cost fields (cost_custom1-10, in schema order)
        ("Cost Custom 1", "cost_custom1", "Number", "Custom cost field 1 - configuration defined in dictionary schema",
         "No"),
        ("Cost Custom 2", "cost_custom2", "Number", "Custom cost field 2 - configuration defined in dictionary schema",
         "No"),
        ("Cost Custom 3", "cost_custom3", "Number", "Custom cost field 3 - configuration defined in dictionary schema",
         "No"),
        ("Cost Custom 4", "cost_custom4", "Number", "Custom cost field 4 - configuration defined in dictionary schema",
         "No"),
        ("Cost Custom 5", "cost_custom5", "Number", "Custom cost field 5 - configuration defined in dictionary schema",
         "No"),
        ("Cost Custom 6", "cost_custom6", "Number", "Custom cost field 6 - configuration defined in dictionary schema",
         "No"),
        ("Cost Custom 7", "cost_custom7", "Number", "Custom cost field 7 - configuration defined in dictionary schema",
         "No"),
        ("Cost Custom 8", "cost_custom8", "Number", "Custom cost field 8 - configuration defined in dictionary schema",
         "No"),
        ("Cost Custom 9", "cost_custom9", "Number", "Custom cost field 9 - configuration defined in dictionary schema",
         "No"),
        ("Cost Custom 10", "cost_custom10", "Number",
         "Custom cost field 10 - configuration defined in dictionary schema", "No"),

        # Standard metric fields (in schema order)
        ("Impressions", "metric_impressions", "Number", "Number of ad impressions delivered or planned", "No"),
        ("Clicks", "metric_clicks", "Number", "Number of clicks on the ad", "No"),
        ("Views", "metric_views", "Number", "Number of video views or content views", "No"),
        ("Engagements", "metric_engagements", "Number", "Number of user engagements (likes, shares, comments, etc.)",
         "No"),
        ("Followers", "metric_followers", "Number", "Number of new followers gained", "No"),
        ("Visits", "metric_visits", "Number", "Number of website visits or page visits", "No"),
        ("Leads", "metric_leads", "Number", "Number of leads generated", "No"),
        ("Sales", "metric_sales", "Number", "Number of sales or purchases", "No"),
        ("Add to Cart", "metric_add_to_cart", "Number", "Number of add-to-cart actions", "No"),
        ("App Install", "metric_app_install", "Number", "Number of app installations", "No"),
        ("Application Start", "metric_application_start", "Number", "Number of application forms started", "No"),
        (
        "Application Complete", "metric_application_complete", "Number", "Number of application forms completed", "No"),
        ("Contact Us", "metric_contact_us", "Number", "Number of contact form submissions or contact actions", "No"),
        ("Download", "metric_download", "Number", "Number of downloads (files, apps, content)", "No"),
        ("Signup", "metric_signup", "Number", "Number of signups or registrations", "No"),
        ("Max Daily Spend", "metric_max_daily_spend", "Number", "Maximum daily spend limit for the line item", "No"),
        ("Max Daily Impressions", "metric_max_daily_impressions", "Number",
         "Maximum daily impressions limit for the line item", "No"),
        ("Audience Size", "metric_audience_size", "Number", "Size of the targetable audience for this line item", "No"),

        # Custom metric fields (metric_custom1-10, in schema order)
        ("Metric Custom 1", "metric_custom1", "Number",
         "Custom metric field 1 - configuration defined in dictionary schema", "No"),
        ("Metric Custom 2", "metric_custom2", "Number",
         "Custom metric field 2 - configuration defined in dictionary schema", "No"),
        ("Metric Custom 3", "metric_custom3", "Number",
         "Custom metric field 3 - configuration defined in dictionary schema", "No"),
        ("Metric Custom 4", "metric_custom4", "Number",
         "Custom metric field 4 - configuration defined in dictionary schema", "No"),
        ("Metric Custom 5", "metric_custom5", "Number",
         "Custom metric field 5 - configuration defined in dictionary schema", "No"),
        ("Metric Custom 6", "metric_custom6", "Number",
         "Custom metric field 6 - configuration defined in dictionary schema", "No"),
        ("Metric Custom 7", "metric_custom7", "Number",
         "Custom metric field 7 - configuration defined in dictionary schema", "No"),
        ("Metric Custom 8", "metric_custom8", "Number",
         "Custom metric field 8 - configuration defined in dictionary schema", "No"),
        ("Metric Custom 9", "metric_custom9", "Number",
         "Custom metric field 9 - configuration defined in dictionary schema", "No"),
        ("Metric Custom 10", "metric_custom10", "Number",
         "Custom metric field 10 - configuration defined in dictionary schema", "No"),
    ]

    # Populate the comprehensive field documentation
    for column_name, field_name, data_type, description, required in all_fields_documentation:
        row += 1
        sheet[f'A{row}'] = column_name
        sheet[f'B{row}'] = field_name  # NEW: Schema field name
        sheet[f'C{row}'] = data_type
        sheet[f'D{row}'] = description
        sheet[f'E{row}'] = required

        # Apply alternating row colors for readability
        if row % 2 == 0:
            for col in ['A', 'B', 'C', 'D', 'E']:
                sheet[f'{col}{row}'].fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")

    # Add additional v2.0 information
    row += 2
    sheet[f'A{row}'] = "Custom Fields:"
    sheet[
        f'B{row}'] = "v2.0 introduces 30 custom fields (10 dimensions, 10 metrics, 10 costs) that can be configured via the Dictionary sheet."
    sheet.merge_cells(f'B{row}:E{row}')  # Updated merge range

    row += 1
    sheet[f'B{row}'] = "- Use the Dictionary sheet to enable/disable custom fields and set their captions"
    sheet.merge_cells(f'B{row}:E{row}')  # Updated merge range

    row += 1
    sheet[f'B{row}'] = "- When enabled, custom fields appear as additional columns in the Line Items sheet"
    sheet.merge_cells(f'B{row}:E{row}')  # Updated merge range

    row += 1
    sheet[f'B{row}'] = "- Use the exact 'Column Name' from this table when importing data"
    sheet.merge_cells(f'B{row}:E{row}')  # Updated merge range

    row += 2
    sheet[f'A{row}'] = "Field Mapping:"
    sheet[
        f'B{row}'] = "The 'Field Name' column shows the underlying schema field name that corresponds to each Excel column."
    sheet.merge_cells(f'B{row}:E{row}')  # Updated merge range

    row += 1
    sheet[f'B{row}'] = "This mapping is useful for developers working with the MediaPlan schema programmatically."
    sheet.merge_cells(f'B{row}:E{row}')  # Updated merge range

    row += 2
    sheet[f'A{row}'] = "Support:"
    sheet[f'B{row}'] = "For more information, see: https://github.com/planmatic/mediaplanschema"
    sheet.merge_cells(f'B{row}:E{row}')  # Updated merge range


def _add_v2_validation_and_formatting(workbook: Workbook) -> None:
    """
    Add data validation and formatting for v2.0 Excel export.

    Args:
        workbook: The workbook to add validation to
    """
    line_items_sheet = workbook["Line Items"]
    dictionary_sheet = workbook["Dictionary"]

    # Channel validation (existing)
    # channel_validation = DataValidation(
    #     type="list",
    #     formula1='"social,search,display,video,audio,tv,ooh,print,other"',
    #     allow_blank=True
    # )
    # line_items_sheet.add_data_validation(channel_validation)
    # Find channel column dynamically
    # for col in range(1, line_items_sheet.max_column + 1):
    #     if line_items_sheet.cell(1, col).value == "Channel":
    #         channel_validation.add(f'{get_column_letter(col)}2:{get_column_letter(col)}1000')
    #         break

    # KPI validation (existing)
    # kpi_validation = DataValidation(
    #     type="list",
    #     formula1='"CPM,CPC,CPA,CTR,CPV,CPI,ROAS,other"',
    #     allow_blank=True
    # )
    # line_items_sheet.add_data_validation(kpi_validation)
    # Find KPI column dynamically
    # for col in range(1, line_items_sheet.max_column + 1):
    #     if line_items_sheet.cell(1, col).value == "KPI":
    #         kpi_validation.add(f'{get_column_letter(col)}2:{get_column_letter(col)}1000')
    #         break

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