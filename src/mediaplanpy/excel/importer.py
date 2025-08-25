"""
Excel importer for mediaplanpy - Updated for v2.0 Schema Support Only.

This module provides functionality for importing media plans from Excel format,
supporting only v2.0 schema with all new fields and dictionary configuration.
"""

import os
import logging
import uuid
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Union, Tuple
from decimal import Decimal
import copy

import openpyxl
from openpyxl import Workbook
from openpyxl.utils import get_column_letter, column_index_from_string

from mediaplanpy.exceptions import StorageError, ValidationError

logger = logging.getLogger("mediaplanpy.excel.importer")


def import_from_excel(file_path: str, **kwargs) -> Dict[str, Any]:
    """
    Import a media plan from an Excel file using v2.0 schema with enhanced data validation.

    Args:
        file_path: Path to the Excel file
        **kwargs: Additional import options

    Returns:
        The imported media plan data in v2.0 schema format

    Raises:
        StorageError: If the import fails
        ValidationError: If the Excel file contains invalid data or wrong schema version
    """
    try:
        # Load the workbook
        workbook = openpyxl.load_workbook(file_path, data_only=True)

        # Detect and validate schema version
        schema_version = _detect_schema_version(workbook)
        if not _is_v2_schema_version(schema_version):
            raise ValidationError(
                f"Excel import only supports v2.0 schema. Found: {schema_version}. "
                f"Please use a v2.0 compatible Excel file."
            )

        # Import v2.0 media plan
        media_plan = _import_v2_media_plan(workbook)

        # NEW: Perform data integrity validations
        _validate_import_data_integrity(media_plan)

        # Sanitize the data to avoid validation issues
        sanitized_media_plan = _sanitize_v2_media_plan_data(media_plan)

        logger.info(f"Media plan imported from Excel (v2.0): {file_path}")
        return sanitized_media_plan

    except ValidationError:
        # Re-raise validation errors as-is to preserve detailed messages
        raise
    except Exception as e:
        raise StorageError(f"Failed to import media plan from Excel: {e}")


def _validate_import_data_integrity(media_plan: Dict[str, Any]) -> None:
    """
    Validate data integrity of imported media plan data.

    Args:
        media_plan: The imported media plan data to validate

    Raises:
        ValidationError: If validation fails with detailed error messages
    """
    validation_errors = []

    # Validate Line Item ID uniqueness
    lineitem_errors = _validate_lineitem_id_uniqueness(media_plan.get("lineitems", []))
    validation_errors.extend(lineitem_errors)

    # Validate Dictionary caption uniqueness
    dictionary_errors = _validate_dictionary_caption_uniqueness(media_plan.get("dictionary", {}))
    validation_errors.extend(dictionary_errors)

    # If any validation errors found, raise ValidationError
    if validation_errors:
        error_message = "Data integrity validation failed:\n\n" + "\n".join(validation_errors)
        raise ValidationError(error_message)


def _validate_lineitem_id_uniqueness(lineitems: List[Dict[str, Any]]) -> List[str]:
    """
    Validate that all non-empty Line Item IDs are unique.

    Args:
        lineitems: List of line item dictionaries

    Returns:
        List of validation error messages (empty if no errors)
    """
    errors = []

    if not lineitems:
        return errors

    # Collect non-empty IDs with their row numbers (Excel row = list index + 2 for header)
    id_to_rows = {}

    for idx, lineitem in enumerate(lineitems):
        line_id = lineitem.get("id")
        excel_row = idx + 2  # +2 because Excel has header row and is 1-indexed

        # Only check non-empty IDs (empty/None IDs will get auto-generated)
        if line_id and str(line_id).strip():
            clean_id = str(line_id).strip()

            if clean_id not in id_to_rows:
                id_to_rows[clean_id] = []
            id_to_rows[clean_id].append(excel_row)

    # Find duplicates
    duplicates = {id_val: rows for id_val, rows in id_to_rows.items() if len(rows) > 1}

    if duplicates:
        errors.append("❌ Line Item ID Uniqueness Validation Failed:")
        errors.append("   The following Line Item IDs appear multiple times:")

        for duplicate_id, rows in duplicates.items():
            row_list = ", ".join(f"row {row}" for row in sorted(rows))
            errors.append(f"   • ID '{duplicate_id}' found in: {row_list}")

        errors.append("")
        errors.append("   💡 Solution: Ensure each Line Item has a unique ID, or leave ID blank for auto-generation.")

    return errors


def _validate_dictionary_caption_uniqueness(dictionary: Dict[str, Any]) -> List[str]:
    """
    Validate that custom field captions are unique across ALL custom field types.

    Args:
        dictionary: Dictionary configuration data

    Returns:
        List of validation error messages (empty if no errors)
    """
    errors = []

    if not dictionary:
        return errors

    # Define section information for clear error messages
    sections = {
        "custom_dimensions": {
            "name": "Custom Dimensions",
            "field_prefix": "dim_custom"
        },
        "custom_metrics": {
            "name": "Custom Metrics",
            "field_prefix": "metric_custom"
        },
        "custom_costs": {
            "name": "Custom Costs",
            "field_prefix": "cost_custom"
        }
    }

    # Collect ALL captions from ALL sections (global uniqueness check)
    caption_to_fields = {}

    for section_key, section_info in sections.items():
        section_data = dictionary.get(section_key, {})

        if not section_data:
            continue

        for field_name, config in section_data.items():
            if not isinstance(config, dict):
                continue

            status = config.get("status", "").lower()
            caption = config.get("caption", "").strip()

            # Only check enabled fields with non-empty captions
            if status == "enabled" and caption:
                if caption not in caption_to_fields:
                    caption_to_fields[caption] = []

                # Store field name with section information for better error reporting
                field_info = {
                    "field_name": field_name,
                    "section": section_info["name"]
                }
                caption_to_fields[caption].append(field_info)

    # Find captions used by multiple fields (across ALL sections)
    duplicates = {caption: fields for caption, fields in caption_to_fields.items() if len(fields) > 1}

    if duplicates:
        errors.append("❌ Dictionary Caption Uniqueness Validation Failed:")
        errors.append("   The following captions are used by multiple custom fields:")
        errors.append("")

        for duplicate_caption, field_infos in duplicates.items():
            errors.append(f"   Caption '{duplicate_caption}' is used by:")

            # Group by section for cleaner display
            by_section = {}
            for field_info in field_infos:
                section = field_info["section"]
                if section not in by_section:
                    by_section[section] = []
                by_section[section].append(field_info["field_name"])

            # Display grouped by section
            for section, field_names in by_section.items():
                field_list = ", ".join(sorted(field_names))
                errors.append(f"      • {section}: {field_list}")

            errors.append("")  # Add blank line between different caption conflicts

        errors.append("   💡 Solution: Each custom field must have a unique caption across ALL custom field types.")
        errors.append("      Captions must be unique globally - not just within dimensions, metrics, or costs.")

    return errors


def update_from_excel(media_plan: Dict[str, Any], file_path: str, **kwargs) -> Dict[str, Any]:
    """
    Update a media plan from an Excel file using v2.0 schema with enhanced data validation.

    Args:
        media_plan: The existing media plan data to update
        file_path: Path to the Excel file
        **kwargs: Additional import options

    Returns:
        The updated media plan data in v2.0 schema format

    Raises:
        StorageError: If the update fails
        ValidationError: If the Excel file contains invalid data
    """
    try:
        # Import the Excel file (this will include our new validations)
        updated_plan = import_from_excel(file_path, **kwargs)

        # Keep original meta data, but update relevant fields
        result = media_plan.copy()

        # Preserve original meta ID and timestamps, but update other meta fields
        original_meta = result.get("meta", {})
        updated_meta = updated_plan.get("meta", {})

        # Keep original ID and timestamps
        updated_meta["id"] = original_meta.get("id", updated_meta.get("id"))
        updated_meta["created_at"] = original_meta.get("created_at", updated_meta.get("created_at"))

        # Update meta with new values from Excel
        result["meta"] = updated_meta

        # Update campaign and line items
        result["campaign"] = updated_plan["campaign"]
        result["lineitems"] = updated_plan["lineitems"]

        # Update dictionary if present
        if "dictionary" in updated_plan:
            result["dictionary"] = updated_plan["dictionary"]

        logger.info(f"Media plan updated from Excel (v2.0): {file_path}")
        return result

    except ValidationError:
        # Re-raise validation errors as-is to preserve detailed messages
        raise
    except Exception as e:
        raise StorageError(f"Failed to update media plan from Excel: {e}")


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


def _detect_schema_version(workbook: Workbook) -> str:
    """
    Detect the schema version from an Excel workbook.

    Args:
        workbook: The workbook to analyze

    Returns:
        The detected schema version
    """
    # Check if metadata sheet exists
    if "Metadata" in workbook.sheetnames:
        metadata_sheet = workbook["Metadata"]

        # Look for schema version in metadata sheet
        for row in range(1, 10):  # Check first few rows
            if metadata_sheet.cell(row=row, column=1).value == "Schema Version:":
                version = metadata_sheet.cell(row=row, column=2).value
                if version:
                    # Normalize version format
                    return version.replace("v", "") if version.startswith("v") else version

    # Check for v2.0 specific features (Dictionary sheet)
    if "Dictionary" in workbook.sheetnames:
        logger.info("Found Dictionary sheet - assuming v2.0 schema")
        return "2.0"

    # Check line items sheet structure to infer version
    if "Line Items" in workbook.sheetnames:
        line_items_sheet = workbook["Line Items"]

        # Get headers
        headers = [cell.value for cell in line_items_sheet[1] if cell.value]

        # Check for v2.0 specific headers
        v2_headers = {"Cost Currency", "Dayparts", "Inventory", "Engagements", "Followers", "Visits"}
        if any(header in headers for header in v2_headers):
            logger.info("Found v2.0 specific headers - assuming v2.0 schema")
            return "2.0"

        # Check for basic required headers
        if "Name" in headers and "Cost Total" in headers:
            logger.warning("Excel file appears to be from an older schema version")
            return "unknown"

    # Default to unknown if cannot determine
    logger.warning("Could not determine schema version from Excel, assuming unknown")
    return "unknown"


def _import_v2_media_plan(workbook: Workbook) -> Dict[str, Any]:
    """
    Import a v2.0 media plan from a workbook.

    Args:
        workbook: The workbook to import from

    Returns:
        The imported media plan data in v2.0 format
    """
    media_plan = {
        "meta": {},
        "campaign": {},
        "lineitems": [],
        "dictionary": {}  # NEW for v2.0
    }

    # Import metadata with v2.0 fields
    if "Metadata" in workbook.sheetnames:
        metadata_sheet = workbook["Metadata"]
        meta = _import_v2_metadata(metadata_sheet)
        media_plan["meta"] = meta

    # Import campaign with v2.0 fields
    if "Campaign" in workbook.sheetnames:
        campaign_sheet = workbook["Campaign"]
        campaign = _import_v2_campaign(campaign_sheet)
        media_plan["campaign"] = campaign

    # Import line items with v2.0 fields
    if "Line Items" in workbook.sheetnames:
        line_items_sheet = workbook["Line Items"]
        lineitems = _import_v2_lineitems(line_items_sheet)
        media_plan["lineitems"] = lineitems

    # Import dictionary configuration (NEW for v2.0, optional)
    if "Dictionary" in workbook.sheetnames:
        dictionary_sheet = workbook["Dictionary"]
        dictionary = _import_v2_dictionary(dictionary_sheet)
        if dictionary:  # Only include if not empty
            media_plan["dictionary"] = dictionary

    # Ensure required meta fields with v2.0 format
    _ensure_v2_meta_fields(media_plan["meta"])

    # Ensure required campaign fields
    _ensure_v2_campaign_fields(media_plan["campaign"])

    return media_plan


def _import_v2_metadata(metadata_sheet) -> Dict[str, Any]:
    """
    Import metadata section with v2.0 fields.

    Args:
        metadata_sheet: The metadata worksheet

    Returns:
        Dictionary containing metadata
    """
    meta = {}

    for row in range(1, 20):  # Check first 20 rows
        key_cell = metadata_sheet.cell(row=row, column=1).value
        value_cell = metadata_sheet.cell(row=row, column=2).value

        if key_cell == "Schema Version:":
            meta["schema_version"] = "2.0"  # Force v2.0
        elif key_cell == "Media Plan ID:":
            meta["id"] = value_cell or f"mediaplan_{uuid.uuid4().hex[:8]}"
        elif key_cell == "Media Plan Name:":
            meta["name"] = value_cell or ""
        elif key_cell == "Created By Name:":  # v2.0 required field
            meta["created_by_name"] = value_cell or ""
        elif key_cell == "Created By ID:":  # v2.0 optional field
            meta["created_by_id"] = value_cell or None
        elif key_cell == "Created At:":
            meta["created_at"] = value_cell or datetime.now().isoformat()
        elif key_cell == "Is Current:":  # v2.0 field
            if value_cell is not None:
                meta["is_current"] = str(value_cell).lower() in ['true', 'yes', '1']
        elif key_cell == "Is Archived:":  # v2.0 field
            if value_cell is not None:
                meta["is_archived"] = str(value_cell).lower() in ['true', 'yes', '1']
        elif key_cell == "Parent ID:":  # v2.0 field
            meta["parent_id"] = value_cell or None
        elif key_cell == "Comments:":
            meta["comments"] = value_cell or ""

    return meta


def _import_v2_campaign(campaign_sheet) -> Dict[str, Any]:
    """
    Import campaign section with v2.0 fields.

    Args:
        campaign_sheet: The campaign worksheet

    Returns:
        Dictionary containing campaign data
    """
    campaign = {}

    for row in range(1, 50):  # Check more rows for v2.0 fields
        key_cell = campaign_sheet.cell(row=row, column=1).value
        value_cell = campaign_sheet.cell(row=row, column=2).value

        if key_cell == "Campaign ID:":
            campaign["id"] = value_cell or f"campaign_{uuid.uuid4().hex[:8]}"
        elif key_cell == "Campaign Name:":
            campaign["name"] = value_cell or ""
        elif key_cell == "Objective:":
            campaign["objective"] = value_cell or ""
        elif key_cell == "Start Date:":
            if isinstance(value_cell, date):
                campaign["start_date"] = value_cell.isoformat()
            else:
                campaign["start_date"] = str(value_cell) if value_cell else ""
        elif key_cell == "End Date:":
            if isinstance(value_cell, date):
                campaign["end_date"] = value_cell.isoformat()
            else:
                campaign["end_date"] = str(value_cell) if value_cell else ""
        elif key_cell == "Budget Total:":
            campaign["budget_total"] = float(value_cell) if value_cell else 0

        # NEW v2.0 budget field
        elif key_cell == "Budget Currency:":
            if value_cell and str(value_cell).strip():
                campaign["budget_currency"] = str(value_cell).strip()

        # NEW v2.0 agency fields
        elif key_cell == "Agency ID:":
            if value_cell and str(value_cell).strip():
                campaign["agency_id"] = str(value_cell).strip()
        elif key_cell == "Agency Name:":
            if value_cell and str(value_cell).strip():
                campaign["agency_name"] = str(value_cell).strip()

        # NEW v2.0 advertiser fields
        elif key_cell == "Advertiser ID:":
            if value_cell and str(value_cell).strip():
                campaign["advertiser_id"] = str(value_cell).strip()
        elif key_cell == "Advertiser Name:":
            if value_cell and str(value_cell).strip():
                campaign["advertiser_name"] = str(value_cell).strip()

        # Product fields (existing + new v2.0 product_id)
        elif key_cell == "Product ID:":
            if value_cell and str(value_cell).strip():
                campaign["product_id"] = str(value_cell).strip()
        elif key_cell == "Product Name:":
            if value_cell and str(value_cell).strip():
                campaign["product_name"] = str(value_cell).strip()
        elif key_cell == "Product Description:":
            if value_cell and str(value_cell).strip():
                campaign["product_description"] = str(value_cell).strip()

        # NEW v2.0 campaign type fields
        elif key_cell == "Campaign Type ID:":
            if value_cell and str(value_cell).strip():
                campaign["campaign_type_id"] = str(value_cell).strip()
        elif key_cell == "Campaign Type Name:":
            if value_cell and str(value_cell).strip():
                campaign["campaign_type_name"] = str(value_cell).strip()

        # NEW v2.0 workflow status fields
        elif key_cell == "Workflow Status ID:":
            if value_cell and str(value_cell).strip():
                campaign["workflow_status_id"] = str(value_cell).strip()
        elif key_cell == "Workflow Status Name:":
            if value_cell and str(value_cell).strip():
                campaign["workflow_status_name"] = str(value_cell).strip()

        # Existing audience fields
        elif key_cell == "Audience Name:":
            campaign["audience_name"] = value_cell or ""
        elif key_cell == "Audience Age Start:":
            campaign["audience_age_start"] = int(value_cell) if value_cell else None
        elif key_cell == "Audience Age End:":
            campaign["audience_age_end"] = int(value_cell) if value_cell else None
        elif key_cell == "Audience Gender:":
            if value_cell and str(value_cell).strip():
                campaign["audience_gender"] = str(value_cell).strip()
        elif key_cell == "Audience Interests:":
            if value_cell:
                campaign["audience_interests"] = [
                    interest.strip() for interest in str(value_cell).split(",")
                ]
            else:
                campaign["audience_interests"] = []
        elif key_cell == "Location Type:":
            if value_cell and str(value_cell).strip():
                campaign["location_type"] = str(value_cell).strip()
        elif key_cell == "Locations:":
            if value_cell:
                campaign["locations"] = [
                    location.strip() for location in str(value_cell).split(",")
                ]
            else:
                campaign["locations"] = []

    return campaign


def _import_v2_lineitems(line_items_sheet) -> List[Dict[str, Any]]:
    """
    Import line items section with v2.0 fields, skipping calculated columns.

    Args:
        line_items_sheet: The line items worksheet

    Returns:
        List of line item dictionaries
    """
    # Get headers
    headers = [cell.value for cell in line_items_sheet[1] if cell.value]

    # Create comprehensive field mapping for v2.0 - ONLY original schema fields
    field_mapping = {
        # Required fields
        "ID": "id",
        "Name": "name",
        "Start Date": "start_date",
        "End Date": "end_date",
        "Cost Total": "cost_total",

        # Channel-related fields
        "Channel": "channel",
        "Channel Custom": "channel_custom",
        "Vehicle": "vehicle",
        "Vehicle Custom": "vehicle_custom",
        "Partner": "partner",
        "Partner Custom": "partner_custom",
        "Media Product": "media_product",
        "Media Product Custom": "media_product_custom",

        # Location fields
        "Location Type": "location_type",
        "Location Name": "location_name",

        # Audience and format fields
        "Target Audience": "target_audience",
        "Ad Format": "adformat",
        "Ad Format Custom": "adformat_custom",

        # KPI fields
        "KPI": "kpi",
        "KPI Custom": "kpi_custom",

        # Dayparts and inventory fields
        "Dayparts": "dayparts",
        "Dayparts Custom": "dayparts_custom",
        "Inventory": "inventory",
        "Inventory Custom": "inventory_custom",

        # Cost fields (including cost_currency)
        "Cost Currency": "cost_currency",
        "Cost Media": "cost_media",
        "Cost Buying": "cost_buying",
        "Cost Platform": "cost_platform",
        "Cost Data": "cost_data",
        "Cost Creative": "cost_creative",

        # Metric fields - existing 3 + NEW 17 v2.0 standard metrics
        "Impressions": "metric_impressions",
        "Clicks": "metric_clicks",
        "Views": "metric_views",
        # NEW v2.0 standard metrics
        "Engagements": "metric_engagements",
        "Followers": "metric_followers",
        "Visits": "metric_visits",
        "Leads": "metric_leads",
        "Sales": "metric_sales",
        "Add to Cart": "metric_add_to_cart",
        "App Install": "metric_app_install",
        "Application Start": "metric_application_start",
        "Application Complete": "metric_application_complete",
        "Contact Us": "metric_contact_us",
        "Download": "metric_download",
        "Signup": "metric_signup",
        "Max Daily Spend": "metric_max_daily_spend",
        "Max Daily Impressions": "metric_max_daily_impressions",
        "Audience Size": "metric_audience_size",
    }

    # Add custom dimension fields
    for i in range(1, 11):
        field_mapping[f"Dim Custom {i}"] = f"dim_custom{i}"
        field_mapping[f"Dim Custom{i}"] = f"dim_custom{i}"  # Alternative format

    # Add custom cost fields
    for i in range(1, 11):
        field_mapping[f"Cost Custom {i}"] = f"cost_custom{i}"
        field_mapping[f"Cost Custom{i}"] = f"cost_custom{i}"  # Alternative format

    # Add custom metric fields
    for i in range(1, 11):
        field_mapping[f"Metric Custom {i}"] = f"metric_custom{i}"
        field_mapping[f"Metric Custom{i}"] = f"metric_custom{i}"  # Alternative format

    # NEW: Identify and skip calculated columns
    calculated_column_patterns = [
        " %",  # Cost allocation percentages (e.g., "Cost Media %")
        "Cost per ",  # Cost-per-unit columns (e.g., "Cost per Click", "Cost per 1000 Impressions")
    ]

    def is_calculated_column(header_name: str) -> bool:
        """Check if a header represents a calculated column that should be skipped."""
        if not header_name:
            return False

        for pattern in calculated_column_patterns:
            if pattern in header_name:
                return True
        return False

    # Map column indices to field names (skipping calculated columns)
    header_to_field = {}
    skipped_columns = []

    for col_idx, header in enumerate(headers, 1):
        if is_calculated_column(header):
            skipped_columns.append(header)
            continue

        if header in field_mapping:
            header_to_field[col_idx] = field_mapping[header]

    # Log information about skipped columns
    if skipped_columns:
        logger.info(
            f"Skipping {len(skipped_columns)} calculated columns during import: {', '.join(skipped_columns[:5])}")
        if len(skipped_columns) > 5:
            logger.info(f"... and {len(skipped_columns) - 5} more calculated columns")

    # NEW: Helper function to handle Excel errors and convert to appropriate values
    def clean_excel_value(cell_value, field_name: str):
        """
        Clean Excel cell values, converting errors to appropriate defaults.

        Args:
            cell_value: The raw cell value from Excel
            field_name: The schema field name for context

        Returns:
            Cleaned value appropriate for the field type
        """
        # Handle Excel errors (like #DIV/0!, #VALUE!, #REF!, etc.)
        if isinstance(cell_value, str) and cell_value.startswith('#'):
            logger.debug(f"Converting Excel error '{cell_value}' to 0 for field '{field_name}'")
            if field_name.startswith(("cost_", "metric_")) or field_name == "cost_total":
                return 0  # Numeric fields get 0
            else:
                return ""  # String fields get empty string

        # Handle None values
        if cell_value is None:
            return None

        # Return the value as-is for further processing
        return cell_value

    # Process line items (skip header row)
    lineitems = []
    for row in range(2, line_items_sheet.max_row + 1):
        # Skip empty rows
        if all(cell.value is None for cell in line_items_sheet[row]):
            continue

        line_item = {}

        # Process all mapped fields (skipping calculated columns)
        for col_idx, field_name in header_to_field.items():
            cell_value = line_items_sheet.cell(row=row, column=col_idx).value

            # Clean the cell value (handle Excel errors)
            cleaned_value = clean_excel_value(cell_value, field_name)

            if cleaned_value is not None:
                # Handle different field types
                if field_name in ["id", "name"] and not cleaned_value:
                    # Generate ID if missing
                    if field_name == "id":
                        line_item[field_name] = f"li_{uuid.uuid4().hex[:8]}"
                    continue

                elif field_name in ["start_date", "end_date"]:
                    # Handle date fields
                    if isinstance(cleaned_value, date):
                        line_item[field_name] = cleaned_value.isoformat()
                    else:
                        line_item[field_name] = str(cleaned_value) if cleaned_value else ""

                elif field_name.startswith(("cost_", "metric_")) or field_name == "cost_total":
                    # Handle numeric fields
                    try:
                        line_item[field_name] = float(cleaned_value)
                    except (ValueError, TypeError):
                        # Skip invalid numeric values or set to 0
                        if field_name == "cost_total":
                            line_item[field_name] = 0  # cost_total is required
                        # Skip other invalid numeric values

                elif field_name == "location_type":
                    # Handle enum field with validation
                    if cleaned_value and str(cleaned_value).strip():
                        line_item[field_name] = str(cleaned_value).strip()

                else:
                    # Handle string fields
                    if str(cleaned_value).strip():
                        line_item[field_name] = str(cleaned_value).strip()

        # Ensure required fields have defaults
        if "id" not in line_item:
            line_item["id"] = f"li_{uuid.uuid4().hex[:8]}"
        if "name" not in line_item:
            line_item["name"] = line_item.get("id", "")
        if "start_date" not in line_item:
            line_item["start_date"] = "2025-01-01"  # Default start date
        if "end_date" not in line_item:
            line_item["end_date"] = "2025-12-31"  # Default end date
        if "cost_total" not in line_item:
            line_item["cost_total"] = 0

        # Add line item to list
        lineitems.append(line_item)

    logger.info(f"Imported {len(lineitems)} line items, skipped {len(skipped_columns)} calculated columns")
    return lineitems


def _import_v2_dictionary(dictionary_sheet) -> Dict[str, Any]:
    """
    Import dictionary configuration (NEW for v2.0).

    Args:
        dictionary_sheet: The dictionary worksheet

    Returns:
        Dictionary containing custom field configuration
    """
    dictionary = {
        "custom_dimensions": {},
        "custom_metrics": {},
        "custom_costs": {}
    }

    # Find the headers
    field_name_col = None
    field_type_col = None
    caption_col = None
    status_col = None

    # Look for header row
    for row in range(1, 5):  # Check first few rows
        for col in range(1, 10):
            cell_value = dictionary_sheet.cell(row=row, column=col).value
            if cell_value == "Field Name":
                field_name_col = col
            elif cell_value == "Field Type":
                field_type_col = col
            elif cell_value == "Caption":
                caption_col = col
            elif cell_value == "Status":
                status_col = col

        # If we found all headers, this is the header row
        if all(col is not None for col in [field_name_col, field_type_col, caption_col, status_col]):
            break

    if not all(col is not None for col in [field_name_col, field_type_col, caption_col, status_col]):
        logger.warning("Could not find dictionary headers, returning empty dictionary")
        return {}

    # Process data rows
    for row in range(3, dictionary_sheet.max_row + 1):  # Start from row 3 (after headers)
        field_name = dictionary_sheet.cell(row=row, column=field_name_col).value
        field_type = dictionary_sheet.cell(row=row, column=field_type_col).value
        caption = dictionary_sheet.cell(row=row, column=caption_col).value
        status = dictionary_sheet.cell(row=row, column=status_col).value

        if not field_name or not field_type or not status:
            continue  # Skip incomplete rows

        # Normalize values
        field_name = str(field_name).strip()
        field_type = str(field_type).strip().lower()
        status = str(status).strip().lower()
        caption = str(caption).strip() if caption else ""

        # Validate status
        if status not in ["enabled", "disabled"]:
            continue  # Skip invalid status

        # Create field configuration
        config = {
            "status": status,
            "caption": caption
        }

        # Add to appropriate section based on field type
        if field_type == "dimension" and field_name.startswith("dim_custom"):
            dictionary["custom_dimensions"][field_name] = config
        elif field_type == "metric" and field_name.startswith("metric_custom"):
            dictionary["custom_metrics"][field_name] = config
        elif field_type == "cost" and field_name.startswith("cost_custom"):
            dictionary["custom_costs"][field_name] = config

    # Remove empty sections
    dictionary = {k: v for k, v in dictionary.items() if v}

    return dictionary


def _ensure_v2_meta_fields(meta: Dict[str, Any]) -> None:
    """
    Ensure required v2.0 meta fields are present with defaults.

    Args:
        meta: The meta dictionary to update
    """
    # v2.0: schema_version is required
    if "schema_version" not in meta:
        meta["schema_version"] = "2.0"

    # v2.0: id is required
    if "id" not in meta:
        meta["id"] = f"mediaplan_{uuid.uuid4().hex[:8]}"

    # v2.0: created_by_name is required (vs optional created_by in v1.0)
    if "created_by_name" not in meta:
        meta["created_by_name"] = meta.get("created_by", "Excel Import User")

    # v2.0: created_at is required
    if "created_at" not in meta:
        meta["created_at"] = datetime.now().isoformat()


def _ensure_v2_campaign_fields(campaign: Dict[str, Any]) -> None:
    """
    Ensure required campaign fields are present with defaults.

    Args:
        campaign: The campaign dictionary to update
    """
    # Required campaign fields (same in v1.0 and v2.0)
    if "id" not in campaign:
        campaign["id"] = f"campaign_{uuid.uuid4().hex[:8]}"
    if "name" not in campaign:
        campaign["name"] = "Campaign from Excel"
    if "objective" not in campaign:
        campaign["objective"] = "Imported from Excel"
    if "start_date" not in campaign:
        campaign["start_date"] = "2025-01-01"
    if "end_date" not in campaign:
        campaign["end_date"] = "2025-12-31"
    if "budget_total" not in campaign:
        campaign["budget_total"] = 100000


def _sanitize_v2_media_plan_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize media plan data to avoid common validation errors for v2.0.

    Args:
        data: The media plan data to sanitize

    Returns:
        Sanitized media plan data
    """
    # Deep copy to avoid modifying the original
    sanitized = copy.deepcopy(data)

    # Handle campaign fields
    if "campaign" in sanitized:
        campaign = sanitized["campaign"]

        # Convert empty strings to None for enum fields
        if "audience_gender" in campaign and (campaign["audience_gender"] == "" or campaign["audience_gender"] is None):
            campaign["audience_gender"] = "Any"  # Default valid value

        if "location_type" in campaign and (campaign["location_type"] == "" or campaign["location_type"] is None):
            campaign["location_type"] = "Country"  # Default to Country

    # Handle lineitems
    if "lineitems" in sanitized:
        for line_item in sanitized["lineitems"]:
            # Handle location_type field
            if "location_type" in line_item and (line_item["location_type"] == "" or line_item["location_type"] is None):
                line_item["location_type"] = "Country"  # Default to Country

    # Handle dictionary (NEW for v2.0)
    if "dictionary" in sanitized:
        dictionary = sanitized["dictionary"]

        # Validate and clean dictionary configuration
        for section_name in ["custom_dimensions", "custom_metrics", "custom_costs"]:
            if section_name in dictionary:
                section = dictionary[section_name]
                cleaned_section = {}

                for field_name, config in section.items():
                    if isinstance(config, dict) and "status" in config:
                        # Ensure status is valid
                        if config["status"] in ["enabled", "disabled"]:
                            cleaned_config = {
                                "status": config["status"],
                                "caption": config.get("caption", "")
                            }
                            # Ensure caption is provided for enabled fields
                            if config["status"] == "enabled" and not cleaned_config["caption"]:
                                cleaned_config["caption"] = f"Custom {field_name}"

                            cleaned_section[field_name] = cleaned_config

                if cleaned_section:
                    dictionary[section_name] = cleaned_section
                else:
                    # Remove empty sections
                    del dictionary[section_name]

    return sanitized