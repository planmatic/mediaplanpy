"""
Excel importer for mediaplanpy.

This module provides functionality for importing media plans from Excel format.
"""

import os
import logging
import uuid
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Union, Tuple
from decimal import Decimal

import openpyxl
from openpyxl import Workbook
from openpyxl.utils import get_column_letter, column_index_from_string

from mediaplanpy.exceptions import StorageError, ValidationError

logger = logging.getLogger("mediaplanpy.excel.importer")


def import_from_excel(file_path: str, **kwargs) -> Dict[str, Any]:
    """
    Import a media plan from an Excel file.

    Args:
        file_path: Path to the Excel file.
        **kwargs: Additional import options.

    Returns:
        The imported media plan data.

    Raises:
        StorageError: If the import fails.
        ValidationError: If the Excel file contains invalid data.
    """
    try:
        # Load the workbook
        workbook = openpyxl.load_workbook(file_path)

        # Determine schema version
        schema_version = _detect_schema_version(workbook)

        # Import based on schema version
        if schema_version.startswith("v0.0.0"):
            media_plan = _import_v0_media_plan(workbook)
        else:  # Default to v1.0.0
            media_plan = _import_v1_media_plan(workbook)

        logger.info(f"Media plan imported from Excel: {file_path}")
        return media_plan

    except Exception as e:
        raise StorageError(f"Failed to import media plan from Excel: {e}")


def update_from_excel(media_plan: Dict[str, Any], file_path: str, **kwargs) -> Dict[str, Any]:
    """
    Update a media plan from an Excel file.

    Args:
        media_plan: The existing media plan data to update.
        file_path: Path to the Excel file.
        **kwargs: Additional import options.

    Returns:
        The updated media plan data.

    Raises:
        StorageError: If the update fails.
        ValidationError: If the Excel file contains invalid data.
    """
    try:
        # Import the Excel file
        updated_plan = import_from_excel(file_path, **kwargs)

        # Keep original meta data, but update campaign and line items
        result = media_plan.copy()

        # Preserve original meta data except comments which may have been updated
        meta = result.get("meta", {})
        if "comments" in updated_plan.get("meta", {}):
            meta["comments"] = updated_plan["meta"]["comments"]

        # Update campaign and line items
        result["campaign"] = updated_plan["campaign"]
        result["lineitems"] = updated_plan["lineitems"]

        logger.info(f"Media plan updated from Excel: {file_path}")
        return result

    except Exception as e:
        raise StorageError(f"Failed to update media plan from Excel: {e}")


def _detect_schema_version(workbook: Workbook) -> str:
    """
    Detect the schema version from an Excel workbook.

    Args:
        workbook: The workbook to analyze.

    Returns:
        The detected schema version.
    """
    # Check if metadata sheet exists
    if "Metadata" in workbook.sheetnames:
        metadata_sheet = workbook["Metadata"]

        # Look for schema version in metadata sheet
        for row in range(1, 10):  # Check first few rows
            if metadata_sheet.cell(row=row, column=1).value == "Schema Version:":
                version = metadata_sheet.cell(row=row, column=2).value
                if version:
                    return version

    # Check line items sheet structure to infer version
    if "Line Items" in workbook.sheetnames:
        line_items_sheet = workbook["Line Items"]

        # Check header row
        headers = [cell.value for cell in line_items_sheet[1] if cell.value]

        # Check for v1.0.0 specific headers
        if "Name" in headers and "Cost Total" in headers:
            return "v1.0.0"
        elif "Budget" in headers and "Platform" in headers:
            return "v0.0.0"

    # Default to v1.0.0 if cannot determine
    logger.warning("Could not determine schema version from Excel, defaulting to v1.0.0")
    return "v1.0.0"


def _import_v0_media_plan(workbook: Workbook) -> Dict[str, Any]:
    """
    Import a v0.0.0 media plan from a workbook.

    Args:
        workbook: The workbook to import from.

    Returns:
        The imported media plan data in v0.0.0 format.
    """
    media_plan = {
        "meta": {},
        "campaign": {},
        "lineitems": []
    }

    # Import metadata
    if "Metadata" in workbook.sheetnames:
        metadata_sheet = workbook["Metadata"]
        for row in range(1, 20):  # Check first 20 rows
            key_cell = metadata_sheet.cell(row=row, column=1).value
            value_cell = metadata_sheet.cell(row=row, column=2).value

            if key_cell == "Schema Version:":
                media_plan["meta"]["schema_version"] = value_cell or "v0.0.0"
            elif key_cell == "Created By:":
                media_plan["meta"]["created_by"] = value_cell or ""
            elif key_cell == "Created At:":
                media_plan["meta"]["created_at"] = value_cell or datetime.now().isoformat()
            elif key_cell == "Comments:":
                media_plan["meta"]["comments"] = value_cell or ""

    # Ensure required meta fields
    if "schema_version" not in media_plan["meta"]:
        media_plan["meta"]["schema_version"] = "v0.0.0"
    if "created_by" not in media_plan["meta"]:
        media_plan["meta"]["created_by"] = "excel_import"
    if "created_at" not in media_plan["meta"]:
        media_plan["meta"]["created_at"] = datetime.now().isoformat()

    # Import campaign data
    if "Campaign" in workbook.sheetnames:
        campaign_sheet = workbook["Campaign"]
        campaign = media_plan["campaign"]

        for row in range(1, 30):  # Check first 30 rows
            key_cell = campaign_sheet.cell(row=row, column=1).value
            value_cell = campaign_sheet.cell(row=row, column=2).value

            if key_cell == "Campaign ID:":
                campaign["id"] = value_cell or f"campaign_{uuid.uuid4().hex[:8]}"
            elif key_cell == "Campaign Name:":
                campaign["name"] = value_cell or ""
            elif key_cell == "Objective:":
                campaign["objective"] = value_cell or ""
            elif key_cell == "Start Date:":
                # Handle date value
                if isinstance(value_cell, date):
                    campaign["start_date"] = value_cell.isoformat()
                else:
                    campaign["start_date"] = str(value_cell) if value_cell else ""
            elif key_cell == "End Date:":
                # Handle date value
                if isinstance(value_cell, date):
                    campaign["end_date"] = value_cell.isoformat()
                else:
                    campaign["end_date"] = str(value_cell) if value_cell else ""
            elif key_cell == "Budget Total:":
                # Create budget structure
                campaign["budget"] = {"total": float(value_cell) if value_cell else 0}
            elif key_cell == "Target Age Range:":
                if "target_audience" not in campaign:
                    campaign["target_audience"] = {}
                campaign["target_audience"]["age_range"] = value_cell or ""
            elif key_cell == "Target Location:":
                if "target_audience" not in campaign:
                    campaign["target_audience"] = {}
                campaign["target_audience"]["location"] = value_cell or ""
            elif key_cell == "Target Interests:":
                if "target_audience" not in campaign:
                    campaign["target_audience"] = {}
                if value_cell:
                    # Split comma-separated interests
                    campaign["target_audience"]["interests"] = [
                        interest.strip() for interest in str(value_cell).split(",")
                    ]
                else:
                    campaign["target_audience"]["interests"] = []

    # Ensure required campaign fields
    if "id" not in media_plan["campaign"]:
        media_plan["campaign"]["id"] = f"campaign_{uuid.uuid4().hex[:8]}"
    if "name" not in media_plan["campaign"]:
        media_plan["campaign"]["name"] = "Campaign from Excel"
    if "objective" not in media_plan["campaign"]:
        media_plan["campaign"]["objective"] = "Imported from Excel"
    if "start_date" not in media_plan["campaign"]:
        media_plan["campaign"]["start_date"] = datetime.now().strftime("%Y-%m-%d")
    if "end_date" not in media_plan["campaign"]:
        # Default to end of year
        end_date = datetime(datetime.now().year, 12, 31).strftime("%Y-%m-%d")
        media_plan["campaign"]["end_date"] = end_date
    if "budget" not in media_plan["campaign"]:
        media_plan["campaign"]["budget"] = {"total": 0}

    # Import line items
    if "Line Items" in workbook.sheetnames:
        line_items_sheet = workbook["Line Items"]

        # Get headers
        headers = [cell.value for cell in line_items_sheet[1] if cell.value]

        # Map column indices to headers
        header_indices = {}
        for col_idx, header in enumerate(headers, 1):
            header_indices[header] = col_idx

        # Process line items (skip header row)
        for row in range(2, line_items_sheet.max_row + 1):
            # Skip empty rows
            if all(cell.value is None for cell in line_items_sheet[row]):
                continue

            line_item = {}

            # Process standard fields
            if "ID" in header_indices:
                line_item["id"] = line_items_sheet.cell(row=row, column=header_indices[
                    "ID"]).value or f"li_{uuid.uuid4().hex[:8]}"

            if "Channel" in header_indices:
                line_item["channel"] = line_items_sheet.cell(row=row, column=header_indices["Channel"]).value or ""

            if "Platform" in header_indices:
                line_item["platform"] = line_items_sheet.cell(row=row, column=header_indices["Platform"]).value or ""

            if "Publisher" in header_indices:
                line_item["publisher"] = line_items_sheet.cell(row=row, column=header_indices["Publisher"]).value or ""

            if "Start Date" in header_indices:
                start_date_cell = line_items_sheet.cell(row=row, column=header_indices["Start Date"]).value
                if isinstance(start_date_cell, date):
                    line_item["start_date"] = start_date_cell.isoformat()
                else:
                    line_item["start_date"] = str(start_date_cell) if start_date_cell else ""

            if "End Date" in header_indices:
                end_date_cell = line_items_sheet.cell(row=row, column=header_indices["End Date"]).value
                if isinstance(end_date_cell, date):
                    line_item["end_date"] = end_date_cell.isoformat()
                else:
                    line_item["end_date"] = str(end_date_cell) if end_date_cell else ""

            if "Budget" in header_indices:
                budget_cell = line_items_sheet.cell(row=row, column=header_indices["Budget"]).value
                line_item["budget"] = float(budget_cell) if budget_cell else 0

            if "KPI" in header_indices:
                line_item["kpi"] = line_items_sheet.cell(row=row, column=header_indices["KPI"]).value or ""

            if "Creative IDs" in header_indices:
                creative_ids_cell = line_items_sheet.cell(row=row, column=header_indices["Creative IDs"]).value
                if creative_ids_cell:
                    line_item["creative_ids"] = [
                        id.strip() for id in str(creative_ids_cell).split(",")
                    ]
                else:
                    line_item["creative_ids"] = []

            # Add line item to list
            media_plan["lineitems"].append(line_item)

    return media_plan


def _import_v1_media_plan(workbook: Workbook) -> Dict[str, Any]:
    """
    Import a v1.0.0 media plan from a workbook.

    Args:
        workbook: The workbook to import from.

    Returns:
        The imported media plan data in v1.0.0 format.
    """
    media_plan = {
        "meta": {},
        "campaign": {},
        "lineitems": []
    }

    # Import metadata
    if "Metadata" in workbook.sheetnames:
        metadata_sheet = workbook["Metadata"]
        for row in range(1, 20):  # Check first 20 rows
            key_cell = metadata_sheet.cell(row=row, column=1).value
            value_cell = metadata_sheet.cell(row=row, column=2).value

            if key_cell == "Schema Version:":
                media_plan["meta"]["schema_version"] = value_cell or "v1.0.0"
            elif key_cell == "Media Plan ID:":
                media_plan["meta"]["id"] = value_cell or f"mediaplan_{uuid.uuid4().hex[:8]}"
            elif key_cell == "Media Plan Name:":
                media_plan["meta"]["name"] = value_cell or ""
            elif key_cell == "Created By:":
                media_plan["meta"]["created_by"] = value_cell or ""
            elif key_cell == "Created At:":
                media_plan["meta"]["created_at"] = value_cell or datetime.now().isoformat()
            elif key_cell == "Comments:":
                media_plan["meta"]["comments"] = value_cell or ""

    # Ensure required meta fields
    if "schema_version" not in media_plan["meta"]:
        media_plan["meta"]["schema_version"] = "v1.0.0"
    if "id" not in media_plan["meta"]:
        media_plan["meta"]["id"] = f"mediaplan_{uuid.uuid4().hex[:8]}"
    if "created_by" not in media_plan["meta"]:
        media_plan["meta"]["created_by"] = "excel_import"
    if "created_at" not in media_plan["meta"]:
        media_plan["meta"]["created_at"] = datetime.now().isoformat()

    # Import campaign data
    if "Campaign" in workbook.sheetnames:
        campaign_sheet = workbook["Campaign"]
        campaign = media_plan["campaign"]

        for row in range(1, 30):  # Check first 30 rows
            key_cell = campaign_sheet.cell(row=row, column=1).value
            value_cell = campaign_sheet.cell(row=row, column=2).value

            if key_cell == "Campaign ID:":
                campaign["id"] = value_cell or f"campaign_{uuid.uuid4().hex[:8]}"
            elif key_cell == "Campaign Name:":
                campaign["name"] = value_cell or ""
            elif key_cell == "Objective:":
                campaign["objective"] = value_cell or ""
            elif key_cell == "Start Date:":
                # Handle date value
                if isinstance(value_cell, date):
                    campaign["start_date"] = value_cell.isoformat()
                else:
                    campaign["start_date"] = str(value_cell) if value_cell else ""
            elif key_cell == "End Date:":
                # Handle date value
                if isinstance(value_cell, date):
                    campaign["end_date"] = value_cell.isoformat()
                else:
                    campaign["end_date"] = str(value_cell) if value_cell else ""
            elif key_cell == "Budget Total:":
                campaign["budget_total"] = float(value_cell) if value_cell else 0
            elif key_cell == "Audience Name:":
                campaign["audience_name"] = value_cell or ""
            elif key_cell == "Audience Age Start:":
                campaign["audience_age_start"] = int(value_cell) if value_cell else None
            elif key_cell == "Audience Age End:":
                campaign["audience_age_end"] = int(value_cell) if value_cell else None
            elif key_cell == "Audience Gender:":
                campaign["audience_gender"] = value_cell or ""
            elif key_cell == "Audience Interests:":
                if value_cell:
                    # Split comma-separated interests
                    campaign["audience_interests"] = [
                        interest.strip() for interest in str(value_cell).split(",")
                    ]
                else:
                    campaign["audience_interests"] = []
            elif key_cell == "Location Type:":
                campaign["location_type"] = value_cell or ""
            elif key_cell == "Locations:":
                if value_cell:
                    # Split comma-separated locations
                    campaign["locations"] = [
                        location.strip() for location in str(value_cell).split(",")
                    ]
                else:
                    campaign["locations"] = []

    # Ensure required campaign fields
    if "id" not in media_plan["campaign"]:
        media_plan["campaign"]["id"] = f"campaign_{uuid.uuid4().hex[:8]}"
    if "name" not in media_plan["campaign"]:
        media_plan["campaign"]["name"] = "Campaign from Excel"
    if "objective" not in media_plan["campaign"]:
        media_plan["campaign"]["objective"] = "Imported from Excel"
    if "start_date" not in media_plan["campaign"]:
        media_plan["campaign"]["start_date"] = datetime.now().strftime("%Y-%m-%d")
    if "end_date" not in media_plan["campaign"]:
        # Default to end of year
        end_date = datetime(datetime.now().year, 12, 31).strftime("%Y-%m-%d")
        media_plan["campaign"]["end_date"] = end_date
    if "budget_total" not in media_plan["campaign"]:
        media_plan["campaign"]["budget_total"] = 0

    # Import line items
    if "Line Items" in workbook.sheetnames:
        line_items_sheet = workbook["Line Items"]

        # Get headers
        headers = [cell.value for cell in line_items_sheet[1] if cell.value]

        # Map column indices to headers
        header_indices = {}
        for col_idx, header in enumerate(headers, 1):
            header_indices[header] = col_idx

        # Process line items (skip header row)
        for row in range(2, line_items_sheet.max_row + 1):
            # Skip empty rows
            if all(cell.value is None for cell in line_items_sheet[row]):
                continue

            line_item = {}

            # Process standard fields
            if "ID" in header_indices:
                line_item["id"] = line_items_sheet.cell(row=row, column=header_indices[
                    "ID"]).value or f"li_{uuid.uuid4().hex[:8]}"

            if "Name" in header_indices:
                line_item["name"] = line_items_sheet.cell(row=row, column=header_indices["Name"]).value or ""

            if "Channel" in header_indices:
                line_item["channel"] = line_items_sheet.cell(row=row, column=header_indices["Channel"]).value or ""

            if "Vehicle" in header_indices:
                line_item["vehicle"] = line_items_sheet.cell(row=row, column=header_indices["Vehicle"]).value or ""

            if "Partner" in header_indices:
                line_item["partner"] = line_items_sheet.cell(row=row, column=header_indices["Partner"]).value or ""

            if "Media Product" in header_indices:
                line_item["media_product"] = line_items_sheet.cell(row=row,
                                                                   column=header_indices["Media Product"]).value or ""

            if "Start Date" in header_indices:
                start_date_cell = line_items_sheet.cell(row=row, column=header_indices["Start Date"]).value
                if isinstance(start_date_cell, date):
                    line_item["start_date"] = start_date_cell.isoformat()
                else:
                    line_item["start_date"] = str(start_date_cell) if start_date_cell else ""

            if "End Date" in header_indices:
                end_date_cell = line_items_sheet.cell(row=row, column=header_indices["End Date"]).value
                if isinstance(end_date_cell, date):
                    line_item["end_date"] = end_date_cell.isoformat()
                else:
                    line_item["end_date"] = str(end_date_cell) if end_date_cell else ""

            if "Cost Total" in header_indices:
                cost_cell = line_items_sheet.cell(row=row, column=header_indices["Cost Total"]).value
                line_item["cost_total"] = float(cost_cell) if cost_cell else 0

            if "KPI" in header_indices:
                line_item["kpi"] = line_items_sheet.cell(row=row, column=header_indices["KPI"]).value or ""

            if "Location Type" in header_indices:
                line_item["location_type"] = line_items_sheet.cell(row=row,
                                                                   column=header_indices["Location Type"]).value or ""

            if "Location Name" in header_indices:
                line_item["location_name"] = line_items_sheet.cell(row=row,
                                                                   column=header_indices["Location Name"]).value or ""

            if "Target Audience" in header_indices:
                line_item["target_audience"] = line_items_sheet.cell(row=row, column=header_indices[
                    "Target Audience"]).value or ""

            if "Ad Format" in header_indices:
                line_item["adformat"] = line_items_sheet.cell(row=row, column=header_indices["Ad Format"]).value or ""

            # Metrics
            if "Impressions" in header_indices:
                impressions_cell = line_items_sheet.cell(row=row, column=header_indices["Impressions"]).value
                if impressions_cell:
                    line_item["metric_impressions"] = float(impressions_cell)

            if "Clicks" in header_indices:
                clicks_cell = line_items_sheet.cell(row=row, column=header_indices["Clicks"]).value
                if clicks_cell:
                    line_item["metric_clicks"] = float(clicks_cell)

            if "Views" in header_indices:
                views_cell = line_items_sheet.cell(row=row, column=header_indices["Views"]).value
                if views_cell:
                    line_item["metric_views"] = float(views_cell)

            # Add line item to list
            media_plan["lineitems"].append(line_item)

    return media_plan