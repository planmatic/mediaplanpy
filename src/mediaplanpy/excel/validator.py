"""
Excel validator for mediaplanpy.

This module provides functionality for validating Excel files against the
Media Plan Open Data Standard schema.
"""

import os
import logging
import tempfile
from typing import Dict, Any, List, Optional, Union, Tuple

import openpyxl
from openpyxl import Workbook

from mediaplanpy.exceptions import ValidationError
from mediaplanpy.schema import SchemaValidator
from mediaplanpy.excel.importer import import_from_excel

logger = logging.getLogger("mediaplanpy.excel.validator")


def validate_excel(file_path: str, schema_validator: Optional[SchemaValidator] = None,
                   schema_version: Optional[str] = None) -> List[str]:
    """
    Validate an Excel file against the Media Plan Open Data Standard schema.

    Args:
        file_path: Path to the Excel file.
        schema_validator: Optional schema validator to use. If None, creates a new one.
        schema_version: Optional schema version to validate against. If None, uses the version
                       specified in the Excel file, or the current version if not specified.

    Returns:
        A list of validation error messages, empty if validation succeeds.

    Raises:
        ValidationError: If the Excel file cannot be read or is structurally invalid.
    """
    try:
        # Import the Excel file to a media plan structure
        media_plan = import_from_excel(file_path)

        # Create schema validator if not provided
        if schema_validator is None:
            schema_validator = SchemaValidator()

        # If no schema version provided, use the one from the imported media plan
        if schema_version is None:
            schema_version = media_plan.get("meta", {}).get("schema_version")

        # Validate the media plan against the schema
        errors = schema_validator.validate(media_plan, schema_version)

        # Add Excel-specific validation
        excel_errors = _validate_excel_structure(file_path)
        errors.extend(excel_errors)

        if not errors:
            logger.info(f"Excel file validated successfully: {file_path}")
        else:
            logger.warning(f"Excel file validation failed with {len(errors)} errors: {file_path}")

        return errors

    except Exception as e:
        raise ValidationError(f"Failed to validate Excel file: {e}")


def validate_excel_template(template_path: str, schema_version: Optional[str] = None) -> List[str]:
    """
    Validate an Excel template for compatibility with the media plan structure.

    Args:
        template_path: Path to the Excel template.
        schema_version: Optional schema version to validate against.

    Returns:
        A list of validation error messages, empty if validation succeeds.

    Raises:
        ValidationError: If the template cannot be read or is structurally invalid.
    """
    try:
        # Load the template
        workbook = openpyxl.load_workbook(template_path)

        # Check for required sheets
        required_sheets = ["Metadata", "Campaign", "Line Items"]
        missing_sheets = [sheet for sheet in required_sheets if sheet not in workbook.sheetnames]

        errors = []
        if missing_sheets:
            errors.append(f"Template is missing required sheets: {', '.join(missing_sheets)}")

        # Check line items sheet structure
        if "Line Items" in workbook.sheetnames:
            line_items_sheet = workbook["Line Items"]

            # Get headers
            headers = [cell.value for cell in line_items_sheet[1] if cell.value]

            # Check for required headers based on schema version
            if schema_version and schema_version.startswith("v0.0.0"):
                required_headers = ["ID", "Channel", "Platform", "Publisher", "Start Date", "End Date", "Budget", "KPI"]
            else:  # Default to v1.0.0
                required_headers = ["ID", "Name", "Start Date", "End Date", "Cost Total"]

            missing_headers = [header for header in required_headers if header not in headers]

            if missing_headers:
                errors.append(f"Template Line Items sheet is missing required headers: {', '.join(missing_headers)}")

        if not errors:
            logger.info(f"Excel template validated successfully: {template_path}")
        else:
            logger.warning(f"Excel template validation failed with {len(errors)} errors: {template_path}")

        return errors

    except Exception as e:
        raise ValidationError(f"Failed to validate Excel template: {e}")


def create_validation_report(file_path: str, errors: List[str], output_path: Optional[str] = None) -> str:
    """
    Create a validation report for an Excel file.

    Args:
        file_path: Path to the validated Excel file.
        errors: List of validation errors.
        output_path: Optional path to save the report. If None, generates a default path.

    Returns:
        The path to the saved validation report.

    Raises:
        ValidationError: If the report cannot be created.
    """
    try:
        # Create a new workbook for the report
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Validation Report"

        # Set column widths
        sheet.column_dimensions["A"].width = 20
        sheet.column_dimensions["B"].width = 80

        # Add header
        sheet['A1'] = "Validation Report"
        sheet['A1'].font = openpyxl.styles.Font(bold=True, size=14)
        sheet.merge_cells('A1:B1')

        # Add file information
        row = 2
        sheet[f'A{row}'] = "Validated File:"
        sheet[f'B{row}'] = os.path.basename(file_path)

        row += 1
        sheet[f'A{row}'] = "Date:"
        sheet[f'B{row}'] = openpyxl.utils.datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row += 1
        sheet[f'A{row}'] = "Result:"
        if errors:
            sheet[f'B{row}'] = f"Failed ({len(errors)} errors)"
            sheet[f'B{row}'].font = openpyxl.styles.Font(color="FF0000")  # Red
        else:
            sheet[f'B{row}'] = "Passed"
            sheet[f'B{row}'].font = openpyxl.styles.Font(color="008000")  # Green

        # Add errors
        if errors:
            row += 2
            sheet[f'A{row}'] = "Errors:"
            sheet[f'A{row}'].font = openpyxl.styles.Font(bold=True)

            for i, error in enumerate(errors, 1):
                row += 1
                sheet[f'A{row}'] = f"Error {i}:"
                sheet[f'B{row}'] = error

        # Determine output path if not provided
        if not output_path:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_path = f"{base_name}_validation_report.xlsx"

        # Save the report
        workbook.save(output_path)

        logger.info(f"Validation report saved to: {output_path}")
        return output_path

    except Exception as e:
        raise ValidationError(f"Failed to create validation report: {e}")


def _validate_excel_structure(file_path: str) -> List[str]:
    """
    Validate the structure of an Excel file.

    Args:
        file_path: Path to the Excel file.

    Returns:
        A list of structural validation errors.
    """
    try:
        # Load the workbook
        workbook = openpyxl.load_workbook(file_path)

        errors = []

        # Check for required sheets
        required_sheets = ["Metadata", "Campaign", "Line Items"]
        missing_sheets = [sheet for sheet in required_sheets if sheet not in workbook.sheetnames]

        if missing_sheets:
            errors.append(f"Excel file is missing required sheets: {', '.join(missing_sheets)}")

        # Check line items structure
        if "Line Items" in workbook.sheetnames:
            line_items_sheet = workbook["Line Items"]

            # Check if first row contains headers
            headers = [cell.value for cell in line_items_sheet[1] if cell.value]
            if not headers:
                errors.append("Line Items sheet is missing headers in first row")

            # Check for data rows
            has_data = False
            for row in range(2, line_items_sheet.max_row + 1):
                if any(cell.value for cell in line_items_sheet[row]):
                    has_data = True
                    break

            if not has_data:
                errors.append("Line Items sheet has no data rows")

        # Check campaign data
        if "Campaign" in workbook.sheetnames:
            campaign_sheet = workbook["Campaign"]

            # Check for essential campaign information
            essential_fields = ["Campaign ID", "Campaign Name", "Start Date", "End Date"]
            missing_fields = []

            for field in essential_fields:
                found = False
                for row in range(1, campaign_sheet.max_row + 1):
                    cell_value = campaign_sheet.cell(row=row, column=1).value
                    if cell_value and field in str(cell_value):
                        found = True
                        break

                if not found:
                    missing_fields.append(field)

            if missing_fields:
                errors.append(f"Campaign sheet is missing essential fields: {', '.join(missing_fields)}")

        return errors

    except Exception as e:
        return [f"Error validating Excel structure: {str(e)}"]