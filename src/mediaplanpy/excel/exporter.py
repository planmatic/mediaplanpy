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

    Args:
        media_plan: The media plan data to export.
        path: The path where to save the Excel file. If None, a default path is generated.
        template_path: Optional path to an Excel template file.
        include_documentation: Whether to include a documentation sheet.
        workspace_manager: Optional WorkspaceManager for saving to workspace storage.
        **kwargs: Additional export options.

    Returns:
        The path to the saved Excel file.

    Raises:
        StorageError: If the export fails.
    """
    try:
        # Determine the path if not provided
        if not path:
            # Generate default path based on media plan ID
            media_plan_id = media_plan.get("meta", {}).get("id", "media_plan")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"{media_plan_id}_{timestamp}.xlsx"

        # Get the schema version
        schema_version = media_plan.get("meta", {}).get("schema_version", "v1.0.0")

        # Create a new workbook, optionally based on a template
        if template_path and os.path.exists(template_path):
            workbook = openpyxl.load_workbook(template_path)
        else:
            workbook = _create_default_workbook(schema_version)

        # Populate the workbook based on schema version
        if schema_version.startswith("v0.0.0"):
            _populate_v0_workbook(workbook, media_plan, include_documentation)
        else:  # Default to v1.0.0
            _populate_v1_workbook(workbook, media_plan, include_documentation)

        # Add validation and formatting
        _add_validation_and_formatting(workbook, schema_version)

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


def _create_default_workbook(schema_version: str) -> Workbook:
    """
    Create a default workbook with necessary sheets.

    Args:
        schema_version: The schema version to use.

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

    # Add documentation sheet if needed
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


def _populate_metadata_sheet(sheet, media_plan: Dict[str, Any], schema_version: str) -> None:
    """
    Populate the metadata sheet with information about the media plan.

    Args:
        sheet: The worksheet to populate.
        media_plan: The media plan data.
        schema_version: The schema version being used.
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
    sheet[f'B{row}'] = schema_version

    row += 1
    sheet[f'A{row}'] = "Media Plan ID:"
    sheet[f'B{row}'] = meta.get("id", "")

    # In v1.0.0, we have a name field
    if "name" in meta:
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


def _populate_campaign_sheet(sheet, campaign: Dict[str, Any], schema_version: str) -> None:
    """
    Populate the campaign sheet with campaign information.

    Args:
        sheet: The worksheet to populate.
        campaign: The campaign data.
        schema_version: The schema version being used.
    """
    # Set column widths
    sheet.column_dimensions["A"].width = 25
    sheet.column_dimensions["B"].width = 50

    # Add title
    sheet['A1'] = "Campaign Information"
    sheet['A1'].style = "header_style"
    sheet.merge_cells('A1:B1')

    # Add campaign fields
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

    # Handle budget differences between v0.0.0 and v1.0.0
    row += 1
    sheet[f'A{row}'] = "Budget Total:"
    if schema_version.startswith("v0.0.0"):
        budget = campaign.get("budget", {})
        sheet[f'B{row}'] = budget.get("total", 0)
    else:
        sheet[f'B{row}'] = campaign.get("budget_total", 0)
    sheet[f'B{row}'].style = "currency_style"

    # Handle target audience differences between v0.0.0 and v1.0.0
    row += 1
    if schema_version.startswith("v0.0.0"):
        target_audience = campaign.get("target_audience", {})

        sheet[f'A{row}'] = "Target Age Range:"
        sheet[f'B{row}'] = target_audience.get("age_range", "")

        row += 1
        sheet[f'A{row}'] = "Target Location:"
        sheet[f'B{row}'] = target_audience.get("location", "")

        row += 1
        sheet[f'A{row}'] = "Target Interests:"
        interests = target_audience.get("interests", [])
        sheet[f'B{row}'] = ", ".join(interests) if interests else ""
    else:
        # v1.0.0 structured audience fields
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


def _populate_lineitems_sheet(sheet, line_items: List[Dict[str, Any]], schema_version: str) -> None:
    """
    Populate the line items sheet with line item data.

    Args:
        sheet: The worksheet to populate.
        line_items: List of line item data.
        schema_version: The schema version being used.
    """
    if schema_version.startswith("v0.0.0"):
        # Keep existing v0.0.0 implementation
        headers = [
            "ID", "Channel", "Platform", "Publisher", "Start Date", "End Date",
            "Budget", "KPI", "Creative IDs"
        ]

        # Set column widths
        for col_idx, header in enumerate(headers, 1):
            sheet.column_dimensions[get_column_letter(col_idx)].width = 15

        # Add headers
        for col_idx, header in enumerate(headers, 1):
            cell = sheet.cell(row=1, column=col_idx, value=header)
            cell.style = "header_style"

        # Add line item data
        for row_idx, line_item in enumerate(line_items, 2):
            col_idx = 1
            sheet.cell(row=row_idx, column=col_idx, value=line_item.get("id", ""))
            col_idx += 1

            sheet.cell(row=row_idx, column=col_idx, value=line_item.get("channel", ""))
            col_idx += 1

            sheet.cell(row=row_idx, column=col_idx, value=line_item.get("platform", ""))
            col_idx += 1

            sheet.cell(row=row_idx, column=col_idx, value=line_item.get("publisher", ""))
            col_idx += 1

            start_date_cell = sheet.cell(row=row_idx, column=col_idx, value=line_item.get("start_date", ""))
            start_date_cell.style = "date_style"
            col_idx += 1

            end_date_cell = sheet.cell(row=row_idx, column=col_idx, value=line_item.get("end_date", ""))
            end_date_cell.style = "date_style"
            col_idx += 1

            budget_cell = sheet.cell(row=row_idx, column=col_idx, value=line_item.get("budget", 0))
            budget_cell.style = "currency_style"
            col_idx += 1

            sheet.cell(row=row_idx, column=col_idx, value=line_item.get("kpi", ""))
            col_idx += 1

            creative_ids = line_item.get("creative_ids", [])
            if isinstance(creative_ids, list):
                creative_ids_str = ", ".join(creative_ids)
            else:
                creative_ids_str = str(creative_ids) if creative_ids else ""
            sheet.cell(row=row_idx, column=col_idx, value=creative_ids_str)

    else:
        # v1.0.0 implementation with dynamic field detection

        # Define field order and header mapping based on schema
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

        # Add a totals row if there are cost fields
        cost_fields = [field for field, _ in active_fields if field.startswith("cost")]
        if cost_fields and len(line_items) > 0:
            totals_row = len(line_items) + 2

            # Add "Total" label
            total_cell = sheet.cell(row=totals_row, column=1, value="Total")
            total_cell.font = Font(bold=True)

            # Calculate and add totals for cost fields
            for col_idx, (field_name, _) in enumerate(active_fields, 1):
                if field_name in cost_fields:
                    total = sum(item.get(field_name, 0) or 0 for item in line_items)
                    total_cell = sheet.cell(row=totals_row, column=col_idx, value=total)
                    total_cell.style = "currency_style"
                    total_cell.font = Font(bold=True)


def _populate_documentation_sheet(sheet, schema_version: str) -> None:
    """
    Populate the documentation sheet with helpful information.

    Args:
        sheet: The worksheet to populate.
        schema_version: The schema version being used.
    """
    # Set column widths
    sheet.column_dimensions["A"].width = 20
    sheet.column_dimensions["B"].width = 50

    # Add title
    sheet['A1'] = "Media Plan Excel Documentation"
    sheet['A1'].style = "header_style"
    sheet.merge_cells('A1:B1')

    # Add documentation content
    row = 2
    sheet[f'A{row}'] = "Schema Version:"
    sheet[f'B{row}'] = schema_version

    row += 1
    sheet[f'A{row}'] = "Export Date:"
    sheet[f'B{row}'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row += 2
    sheet[f'A{row}'] = "Instructions:"
    sheet[f'B{row}'] = "This Excel file contains a media plan following the Media Plan Open Data Standard."

    row += 1
    sheet[f'B{row}'] = "Use the tabs to navigate through different sections of the media plan."

    row += 2
    sheet[f'A{row}'] = "Sheets:"
    sheet[f'B{row}'] = "Metadata: Contains information about the media plan itself."

    row += 1
    sheet[f'B{row}'] = "Campaign: Contains campaign details and settings."

    row += 1
    sheet[f'B{row}'] = "Line Items: Contains all line items in the campaign."

    row += 2
    sheet[f'A{row}'] = "Validation:"
    sheet[f'B{row}'] = "Some fields have data validation to ensure consistent data entry."

    row += 2
    sheet[f'A{row}'] = "Support:"
    sheet[f'B{row}'] = "For more information, see: https://github.com/laurent-colard-l5i/mediaplanschema"


def _add_validation_and_formatting(workbook: Workbook, schema_version: str) -> None:
    """
    Add data validation and formatting to the workbook.

    Args:
        workbook: The workbook to add validation to.
        schema_version: The schema version being used.
    """
    # Example: Add validation for channels in Line Items sheet
    line_items_sheet = workbook["Line Items"]

    if schema_version.startswith("v0.0.0"):
        # v0.0.0 validation
        # Channel validation
        channel_validation = DataValidation(
            type="list",
            formula1='"social,search,display,video,audio,tv,ooh,print,other"',
            allow_blank=True
        )
        line_items_sheet.add_data_validation(channel_validation)

        # Apply to channel column (col B)
        channel_col = 2
        channel_validation.add(f'B2:B1000')

        # KPI validation
        kpi_validation = DataValidation(
            type="list",
            formula1='"CPM,CPC,CPA,CTR,CPV,CPI,ROAS,other"',
            allow_blank=True
        )
        line_items_sheet.add_data_validation(kpi_validation)

        # Apply to KPI column (col G)
        kpi_col = 8
        kpi_validation.add(f'H2:H1000')

    else:
        # v1.0.0 validation
        # Channel validation
        channel_validation = DataValidation(
            type="list",
            formula1='"social,search,display,video,audio,tv,ooh,print,other"',
            allow_blank=True
        )
        line_items_sheet.add_data_validation(channel_validation)

        # Apply to channel column (col C)
        channel_validation.add(f'C2:C1000')

        # KPI validation
        kpi_validation = DataValidation(
            type="list",
            formula1='"CPM,CPC,CPA,CTR,CPV,CPI,ROAS,other"',
            allow_blank=True
        )
        line_items_sheet.add_data_validation(kpi_validation)

        # Apply to KPI column (col J)
        kpi_validation.add(f'J2:J1000')

        # Location type validation
        location_validation = DataValidation(
            type="list",
            formula1='"Country,State"',
            allow_blank=True
        )
        line_items_sheet.add_data_validation(location_validation)

        # Apply to location type column (col K)
        location_validation.add(f'K2:K1000')


def _populate_v0_workbook(workbook: Workbook, media_plan: Dict[str, Any], include_documentation: bool) -> None:
    """
    Populate a workbook based on v0.0.0 schema.

    Args:
        workbook: The workbook to populate.
        media_plan: The media plan data.
        include_documentation: Whether to include a documentation sheet.
    """
    meta = media_plan.get("meta", {})
    campaign = media_plan.get("campaign", {})
    line_items = media_plan.get("lineitems", [])

    # Populate metadata sheet
    _populate_metadata_sheet(workbook["Metadata"], media_plan, "v0.0.0")

    # Populate campaign sheet
    _populate_campaign_sheet(workbook["Campaign"], campaign, "v0.0.0")

    # Populate line items sheet
    _populate_lineitems_sheet(workbook["Line Items"], line_items, "v0.0.0")

    # Populate documentation sheet if needed
    if include_documentation:
        _populate_documentation_sheet(workbook["Documentation"], "v0.0.0")
    elif "Documentation" in workbook.sheetnames:
        workbook.remove(workbook["Documentation"])


def _populate_v1_workbook(workbook: Workbook, media_plan: Dict[str, Any], include_documentation: bool) -> None:
    """
    Populate a workbook based on v1.0.0 schema.

    Args:
        workbook: The workbook to populate.
        media_plan: The media plan data.
        include_documentation: Whether to include a documentation sheet.
    """
    meta = media_plan.get("meta", {})
    campaign = media_plan.get("campaign", {})
    line_items = media_plan.get("lineitems", [])

    # Populate metadata sheet
    _populate_metadata_sheet(workbook["Metadata"], media_plan, "v1.0.0")

    # Populate campaign sheet
    _populate_campaign_sheet(workbook["Campaign"], campaign, "v1.0.0")

    # Populate line items sheet
    _populate_lineitems_sheet(workbook["Line Items"], line_items, "v1.0.0")

    # Populate documentation sheet if needed
    if include_documentation:
        _populate_documentation_sheet(workbook["Documentation"], "v1.0.0")
    elif "Documentation" in workbook.sheetnames:
        workbook.remove(workbook["Documentation"])