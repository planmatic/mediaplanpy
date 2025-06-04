"""
Excel exporter for mediaplanpy.

This module provides functionality for exporting media plans to Excel format.
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
    Export a media plan to Excel format.
    [existing docstring...]
    """
    try:
        # Determine the path if not provided
        if not path:
            media_plan_id = media_plan.get("meta", {}).get("id", "media_plan")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"{media_plan_id}_{timestamp}.xlsx"

        # Get the schema version - UPDATE: use current schema version format
        schema_version = media_plan.get("meta", {}).get("schema_version", "1.0")

        # Validate schema version compatibility - UPDATE: only support current version
        if not _is_current_schema_version(schema_version):
            raise StorageError(f"Excel export only supports current schema version 1.0. Found: {schema_version}")

        # Create workbook - UPDATE: simplified, no template branching needed
        if template_path and os.path.exists(template_path):
            workbook = openpyxl.load_workbook(template_path)
        else:
            workbook = _create_default_workbook()

        # Populate the workbook - UPDATE: simplified, only v1.0 logic
        _populate_v1_workbook(workbook, media_plan, include_documentation)

        # Add validation and formatting
        _add_validation_and_formatting(workbook)

        # Save the workbook to the storage or local path
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


def _is_current_schema_version(version: str) -> bool:
    """
    Check if the schema version is the current supported version.

    Args:
        version: The schema version to check.

    Returns:
        True if the version is current and supported.
    """
    # Normalize version format (handle both "1.0" and "v1.0" for compatibility)
    normalized = version.replace("v", "") if version.startswith("v") else version
    return normalized == "1.0"


def _create_default_workbook() -> Workbook:
    """
    Create a default workbook with necessary sheets.

    Returns:
        A new Workbook with standard sheets.
    """
    workbook = Workbook()

    # Rename default sheet to "Metadata"
    metadata_sheet = workbook.active
    metadata_sheet.title = "Metadata"

    # Create other required sheets
    campaign_sheet = workbook.create_sheet("Campaign")
    lineitems_sheet = workbook.create_sheet("Line Items")
    documentation_sheet = workbook.create_sheet("Documentation")

    # Create basic styles
    _create_default_styles(workbook)

    return workbook


def _create_default_styles(workbook: Workbook) -> None:
    """
    Create default named styles for the workbook.

    Args:
        workbook: The workbook to add styles to.
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


def _populate_metadata_sheet(sheet, media_plan: Dict[str, Any]) -> None:
    """
    Populate the metadata sheet with information about the media plan.

    Args:
        sheet: The worksheet to populate.
        media_plan: The media plan data.
    """
    meta = media_plan.get("meta", {})

    # Set column widths
    sheet.column_dimensions["A"].width = 20
    sheet.column_dimensions["B"].width = 50

    # Add title
    sheet['A1'] = "Media Plan Metadata"
    sheet['A1'].style = "header_style"
    sheet.merge_cells('A1:B1')

    # Add metadata fields
    row = 2
    sheet[f'A{row}'] = "Schema Version:"
    sheet[f'B{row}'] = "1.0"  # UPDATE: Always use current version

    row += 1
    sheet[f'A{row}'] = "Media Plan ID:"
    sheet[f'B{row}'] = meta.get("id", "")

    row += 1
    sheet[f'A{row}'] = "Media Plan Name:"
    sheet[f'B{row}'] = meta.get("name", "")

    row += 1
    sheet[f'A{row}'] = "Created By:"
    sheet[f'B{row}'] = meta.get("created_by", "")

    row += 1
    sheet[f'A{row}'] = "Created At:"
    sheet[f'B{row}'] = meta.get("created_at", "")

    row += 1
    sheet[f'A{row}'] = "Export Date:"
    sheet[f'B{row}'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if "comments" in meta:
        row += 1
        sheet[f'A{row}'] = "Comments:"
        sheet[f'B{row}'] = meta.get("comments", "")


def _populate_campaign_sheet(sheet, campaign: Dict[str, Any]) -> None:
    """
    Populate the campaign sheet with campaign information.

    Args:
        sheet: The worksheet to populate.
        campaign: The campaign data.
    """
    # Set column widths
    sheet.column_dimensions["A"].width = 25
    sheet.column_dimensions["B"].width = 50

    # Add title
    sheet['A1'] = "Campaign Information"
    sheet['A1'].style = "header_style"
    sheet.merge_cells('A1:B1')

    # Add campaign fields (v1.0 format only)
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

    # UPDATE: Use v1.0 budget structure only
    row += 1
    sheet[f'A{row}'] = "Budget Total:"
    sheet[f'B{row}'] = campaign.get("budget_total", 0)
    sheet[f'B{row}'].style = "currency_style"

    # UPDATE: Use v1.0 structured audience fields only
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


def _populate_lineitems_sheet(sheet, line_items: List[Dict[str, Any]]) -> None:
    """
    Populate the line items sheet with line item data.

    Args:
        sheet: The worksheet to populate.
        line_items: List of line item data.
    """
    # UPDATE: Remove v0.0.0 logic, only use v1.0 implementation

    # Define field order and header mapping based on v1.0 schema
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
    ]

    # Add custom dimension fields
    for i in range(1, 11):
        field_order.append((f"dim_custom{i}", f"Dim Custom {i}"))

    # Add cost breakdown fields
    field_order.extend([
        ("cost_media", "Cost Media"),
        ("cost_buying", "Cost Buying"),
        ("cost_platform", "Cost Platform"),
        ("cost_data", "Cost Data"),
        ("cost_creative", "Cost Creative"),
    ])

    # Add custom cost fields
    for i in range(1, 11):
        field_order.append((f"cost_custom{i}", f"Cost Custom {i}"))

    # Add metric fields
    field_order.extend([
        ("metric_impressions", "Impressions"),
        ("metric_clicks", "Clicks"),
        ("metric_views", "Views"),
    ])

    # Add custom metric fields
    for i in range(1, 11):
        field_order.append((f"metric_custom{i}", f"Metric Custom {i}"))

    # Determine which fields are actually present in any line item
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
        # Wider columns for certain fields
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


def _populate_documentation_sheet(sheet) -> None:
    """
    Populate the documentation sheet with helpful information.

    Args:
        sheet: The worksheet to populate.
    """
    # Set column widths
    sheet.column_dimensions["A"].width = 25
    sheet.column_dimensions["B"].width = 15
    sheet.column_dimensions["C"].width = 50
    sheet.column_dimensions["D"].width = 15

    # Add title
    sheet['A1'] = "Media Plan Excel Documentation"
    sheet['A1'].style = "header_style"
    sheet.merge_cells('A1:D1')

    # Add documentation content
    row = 2
    sheet[f'A{row}'] = "Schema Version:"
    sheet[f'B{row}'] = "1.0"  # UPDATE: Use current version

    row += 1
    sheet[f'A{row}'] = "Export Date:"
    sheet[f'B{row}'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row += 2
    sheet[f'A{row}'] = "Instructions:"
    sheet[f'B{row}'] = "This Excel file contains a media plan following the Media Plan Open Data Standard v1.0."
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

    # UPDATE: Only include v1.0 field documentation (remove v0.0.0 check)
    row += 2
    sheet[f'A{row}'] = "Line Items Column Reference"
    sheet[f'A{row}'].font = Font(bold=True, size=12)
    sheet.merge_cells(f'A{row}:D{row}')

    row += 1
    sheet[f'A{row}'] = "Column Name"
    sheet[f'B{row}'] = "Data Type"
    sheet[f'C{row}'] = "Description"
    sheet[f'D{row}'] = "Required"
    for col in ['A', 'B', 'C', 'D']:
        sheet[f'{col}{row}'].style = "header_style"

    # Define all fields with their properties (v1.0 only)
    fields_documentation = [
        # Required fields
        ("ID", "Text", "Unique identifier for the line item", "Yes"),
        ("Name", "Text", "Descriptive name for the line item", "Yes"),
        ("Start Date", "Date", "Start date of the line item (YYYY-MM-DD)", "Yes"),
        ("End Date", "Date", "End date of the line item (YYYY-MM-DD)", "Yes"),
        ("Cost Total", "Currency", "Total cost for the line item", "Yes"),

        # Channel-related fields
        ("Channel", "Text", "Primary channel category (e.g., Social, Search, Display, Video, Audio, TV, OOH, Print)", "No"),
        ("Channel Custom", "Text", "Custom channel label if standard category doesn't apply", "No"),
        ("Vehicle", "Text", "Vehicle or platform where ads will run (e.g., Facebook, Google, YouTube)", "No"),
        ("Vehicle Custom", "Text", "Custom vehicle label if standard name doesn't apply", "No"),
        ("Partner", "Text", "Partner or publisher (e.g., Meta, Google, Amazon)", "No"),
        ("Partner Custom", "Text", "Custom partner name if standard name doesn't apply", "No"),
        ("Media Product", "Text", "Media product offering (e.g., Feed Ads, Search Ads, Pre-roll)", "No"),
        ("Media Product Custom", "Text", "Custom media product if standard name doesn't apply", "No"),

        # Location fields
        ("Location Type", "Text", "Type of location targeting (Country or State)", "No"),
        ("Location Name", "Text", "Name of targeted location (e.g., US, NY, UK)", "No"),

        # Audience and format fields
        ("Target Audience", "Text", "Description of target audience", "No"),
        ("Ad Format", "Text", "Format of the advertisement (e.g., Banner, Video, Audio, Text)", "No"),
        ("Ad Format Custom", "Text", "Custom ad format if standard format doesn't apply", "No"),

        # KPI fields
        ("KPI", "Text", "Key Performance Indicator (e.g., CPM, CPC, CPA, CTR, CPV, CPL, ROAS)", "No"),
        ("KPI Custom", "Text", "Custom KPI if standard KPI doesn't apply", "No"),

        # Cost breakdown fields
        ("Cost Media", "Currency", "Cost of media placement", "No"),
        ("Cost Buying", "Currency", "Cost of buying or trading desk fees", "No"),
        ("Cost Platform", "Currency", "Cost of platform or tech fees", "No"),
        ("Cost Data", "Currency", "Cost of data", "No"),
        ("Cost Creative", "Currency", "Cost of creative production", "No"),

        # Metric fields
        ("Impressions", "Number", "Number of impressions", "No"),
        ("Clicks", "Number", "Number of clicks", "No"),
        ("Views", "Number", "Number of views (for video)", "No"),
    ]

    # Add custom dimension fields
    for i in range(1, 11):
        fields_documentation.append(
            (f"Dim Custom {i}", "Text", f"Custom dimension field {i} for additional categorization", "No")
        )

    # Add custom cost fields
    for i in range(1, 11):
        fields_documentation.append(
            (f"Cost Custom {i}", "Currency", f"Custom cost field {i} for additional cost tracking", "No")
        )

    # Add custom metric fields
    for i in range(1, 11):
        fields_documentation.append(
            (f"Metric Custom {i}", "Number", f"Custom metric field {i} for additional performance tracking", "No")
        )

    # Populate the field documentation
    for field_name, data_type, description, required in fields_documentation:
        row += 1
        sheet[f'A{row}'] = field_name
        sheet[f'B{row}'] = data_type
        sheet[f'C{row}'] = description
        sheet[f'D{row}'] = required

        # Apply alternating row colors for readability
        if row % 2 == 0:
            for col in ['A', 'B', 'C', 'D']:
                sheet[f'{col}{row}'].fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")

    # Add validation information
    row += 2
    sheet[f'A{row}'] = "Data Validation:"
    sheet[f'B{row}'] = "Some fields have data validation to ensure consistent data entry."
    sheet.merge_cells(f'B{row}:D{row}')

    row += 1
    sheet[f'B{row}'] = "- Channel: Dropdown list of standard channels"
    sheet.merge_cells(f'B{row}:D{row}')

    row += 1
    sheet[f'B{row}'] = "- KPI: Dropdown list of standard KPIs"
    sheet.merge_cells(f'B{row}:D{row}')

    row += 1
    sheet[f'B{row}'] = "- Location Type: Country or State"
    sheet.merge_cells(f'B{row}:D{row}')

    row += 1
    sheet[f'B{row}'] = "- Date fields: Must be in YYYY-MM-DD format"
    sheet.merge_cells(f'B{row}:D{row}')

    row += 2
    sheet[f'A{row}'] = "Custom Fields:"
    sheet[f'B{row}'] = "Custom fields allow for extensibility while maintaining standard structure."
    sheet.merge_cells(f'B{row}:D{row}')

    row += 1
    sheet[f'B{row}'] = "- Use 'Custom' fields when standard options don't fit your needs"
    sheet.merge_cells(f'B{row}:D{row}')

    row += 1
    sheet[f'B{row}'] = "- Dim Custom fields: For additional categorization dimensions"
    sheet.merge_cells(f'B{row}:D{row}')

    row += 1
    sheet[f'B{row}'] = "- Cost Custom fields: For tracking additional cost types"
    sheet.merge_cells(f'B{row}:D{row}')

    row += 1
    sheet[f'B{row}'] = "- Metric Custom fields: For tracking additional performance metrics"
    sheet.merge_cells(f'B{row}:D{row}')

    row += 2
    sheet[f'A{row}'] = "Support:"
    sheet[f'B{row}'] = "For more information, see: https://github.com/laurent-colard-l5i/mediaplanschema"
    sheet.merge_cells(f'B{row}:D{row}')

def _add_validation_and_formatting(workbook: Workbook) -> None:
    """
    Add data validation and formatting to the workbook.

    Args:
        workbook: The workbook to add validation to.
    """
    # UPDATE: Remove v0.0.0 logic, only use v1.0 validation
    line_items_sheet = workbook["Line Items"]

    # Channel validation
    channel_validation = DataValidation(
        type="list",
        formula1='"social,search,display,video,audio,tv,ooh,print,other"',
        allow_blank=True
    )
    line_items_sheet.add_data_validation(channel_validation)
    channel_validation.add(f'C2:C1000')  # Channel column

    # KPI validation
    kpi_validation = DataValidation(
        type="list",
        formula1='"CPM,CPC,CPA,CTR,CPV,CPI,ROAS,other"',
        allow_blank=True
    )
    line_items_sheet.add_data_validation(kpi_validation)
    kpi_validation.add(f'J2:J1000')  # KPI column

    # Location type validation
    location_validation = DataValidation(
        type="list",
        formula1='"Country,State"',
        allow_blank=True
    )
    line_items_sheet.add_data_validation(location_validation)
    location_validation.add(f'K2:K1000')  # Location type column


def _populate_v1_workbook(workbook: Workbook, media_plan: Dict[str, Any], include_documentation: bool) -> None:
    """
    Populate a workbook based on v1.0 schema.

    Args:
        workbook: The workbook to populate.
        media_plan: The media plan data.
        include_documentation: Whether to include a documentation sheet.
    """
    meta = media_plan.get("meta", {})
    campaign = media_plan.get("campaign", {})
    line_items = media_plan.get("lineitems", [])

    # Populate metadata sheet
    _populate_metadata_sheet(workbook["Metadata"], media_plan)

    # Populate campaign sheet
    _populate_campaign_sheet(workbook["Campaign"], campaign)

    # Populate line items sheet
    _populate_lineitems_sheet(workbook["Line Items"], line_items)

    # Populate documentation sheet if needed
    if include_documentation:
        _populate_documentation_sheet(workbook["Documentation"])
    elif "Documentation" in workbook.sheetnames:
        workbook.remove(workbook["Documentation"])