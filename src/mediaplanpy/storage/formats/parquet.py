"""
Enhanced Parquet format handler for mediaplanpy with version validation.

This module provides a Parquet format handler for serializing and
deserializing media plans with proper version handling and validation.
"""

import io
import json
import logging
from typing import Dict, Any, List, Union, BinaryIO

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from mediaplanpy.exceptions import StorageError, SchemaVersionError
from mediaplanpy.storage.formats.base import FormatHandler, register_format

logger = logging.getLogger("mediaplanpy.storage.formats.parquet")


@register_format
class ParquetFormatHandler(FormatHandler):
    """
    Handler for Parquet format with version validation and compatibility checking.

    Serializes and deserializes media plans to/from Parquet format while ensuring
    schema version compatibility and providing migration warnings.
    """

    format_name = "parquet"
    file_extension = "parquet"
    media_types = ["application/x-parquet"]
    is_binary = True

    def __init__(self, compression: str = "snappy", validate_version: bool = True, **kwargs):
        """
        Initialize the Parquet format handler.

        Args:
            compression: Compression algorithm to use.
            validate_version: If True, validate schema versions during operations.
            **kwargs: Additional Parquet encoding options.
        """
        self.compression = compression
        self.validate_version = validate_version
        self.options = kwargs

    def validate_schema_version(self, data: Dict[str, Any]) -> None:
        """
        Validate schema version in media plan data.

        Args:
            data: Media plan data to validate

        Raises:
            SchemaVersionError: If version is invalid or incompatible
        """
        if not self.validate_version:
            return

        # Extract schema version
        schema_version = data.get("meta", {}).get("schema_version")
        if not schema_version:
            logger.warning("No schema version found in media plan data")
            return

        try:
            from mediaplanpy.schema.version_utils import (
                normalize_version,
                get_compatibility_type,
                get_migration_recommendation
            )

            # Normalize and check compatibility
            normalized_version = normalize_version(schema_version)
            compatibility = get_compatibility_type(normalized_version)

            if compatibility == "unsupported":
                recommendation = get_migration_recommendation(normalized_version)
                raise SchemaVersionError(
                    f"Schema version '{schema_version}' is not supported for Parquet export. "
                    f"{recommendation.get('message', 'Upgrade required.')}"
                )
            elif compatibility == "deprecated":
                logger.warning(
                    f"Schema version '{schema_version}' is deprecated. "
                    "Consider upgrading before exporting to Parquet."
                )

            # Check if version is compatible with Parquet export (v1.0.0+)
            major_version = int(normalized_version.split('.')[0])
            if major_version < 1:
                raise SchemaVersionError(
                    f"Schema version '{schema_version}' is not supported for Parquet export. "
                    "Parquet export requires schema version 1.0 or higher."
                )

        except ImportError:
            # Fallback validation if version utilities not available
            import re
            # Remove 'v' prefix and check for 2-digit format
            clean_version = schema_version.lstrip('v')
            if not re.match(r'^[0-9]+\.[0-9]+(\.[0-9]+)?$', clean_version):
                raise SchemaVersionError(f"Invalid schema version format: '{schema_version}'")

    def normalize_version_in_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize schema version in data to 2-digit format.

        Args:
            data: Media plan data

        Returns:
            Data with normalized schema version
        """
        if not self.validate_version:
            return data

        schema_version = data.get("meta", {}).get("schema_version")
        if not schema_version:
            return data

        try:
            from mediaplanpy.schema.version_utils import normalize_version

            # Normalize version to 2-digit format
            normalized_version = normalize_version(schema_version)

            # Update the data if version changed
            if normalized_version != schema_version.lstrip('v'):
                logger.debug(f"Normalized version from '{schema_version}' to '{normalized_version}'")
                data = data.copy()  # Avoid modifying original
                if "meta" not in data:
                    data["meta"] = {}
                data["meta"]["schema_version"] = normalized_version  # Store without 'v' prefix for Parquet

        except Exception as e:
            logger.warning(f"Could not normalize schema version '{schema_version}': {e}")

        return data

    def serialize(self, data: Dict[str, Any], **kwargs) -> bytes:
        """
        Serialize data to Parquet binary format with version validation.

        Args:
            data: The media plan data to serialize.
            **kwargs: Additional Parquet encoding options.

        Returns:
            The serialized Parquet binary data.

        Raises:
            StorageError: If the data cannot be serialized.
            SchemaVersionError: If version validation fails.
        """
        try:
            # Validate version before serialization
            self.validate_schema_version(data)

            # Normalize version format
            data = self.normalize_version_in_data(data)

            # Convert to flattened DataFrame
            df = self._flatten_media_plan(data)

            # Convert to Parquet bytes
            buffer = io.BytesIO()
            table = pa.Table.from_pandas(df, schema=self._get_arrow_schema())

            pq.write_table(
                table,
                buffer,
                compression=kwargs.get('compression', self.compression)
            )

            return buffer.getvalue()

        except SchemaVersionError:
            # Re-raise version errors
            raise
        except Exception as e:
            raise StorageError(f"Failed to serialize data to Parquet: {e}")

    def deserialize(self, content: bytes, **kwargs) -> Dict[str, Any]:
        """
        Deserialize content from Parquet binary format.

        Note: This is not implemented as we don't need to reconstruct
        the hierarchical structure from flattened Parquet for now.

        Args:
            content: The Parquet binary content to deserialize.
            **kwargs: Additional Parquet decoding options.

        Returns:
            The deserialized data as a dictionary.

        Raises:
            NotImplementedError: This method is not implemented.
        """
        raise NotImplementedError(
            "Deserializing from Parquet to hierarchical media plan is not implemented. "
            "Use JSON format for round-trip serialization."
        )

    def serialize_to_file(self, data: Dict[str, Any], file_obj: BinaryIO, **kwargs) -> None:
        """
        Serialize data and write it to a file object with version validation.

        Args:
            data: The data to serialize.
            file_obj: A file-like object to write to.
            **kwargs: Additional Parquet encoding options.

        Raises:
            StorageError: If the data cannot be serialized or written.
            SchemaVersionError: If version validation fails.
        """
        try:
            content = self.serialize(data, **kwargs)

            # Check if file is opened in binary mode
            if hasattr(file_obj, 'mode') and 'b' in file_obj.mode:
                # Binary mode - write directly
                file_obj.write(content)
            else:
                # Text mode - this shouldn't happen for Parquet
                raise StorageError("Parquet files must be opened in binary mode")

        except SchemaVersionError:
            # Re-raise version errors
            raise
        except Exception as e:
            raise StorageError(f"Failed to serialize and write Parquet data: {e}")

    def deserialize_from_file(self, file_obj: BinaryIO, **kwargs) -> Dict[str, Any]:
        """
        Read and deserialize data from a file object.

        Note: This is not implemented as we don't need to reconstruct
        the hierarchical structure from flattened Parquet for now.

        Args:
            file_obj: A file-like object to read from.
            **kwargs: Additional Parquet decoding options.

        Returns:
            The deserialized data as a dictionary.

        Raises:
            NotImplementedError: This method is not implemented.
        """
        raise NotImplementedError(
            "Deserializing from Parquet to hierarchical media plan is not implemented. "
            "Use JSON format for round-trip serialization."
        )

    def _get_arrow_schema(self) -> pa.Schema:
        """
        Define explicit schema for the Parquet file with version metadata.
        Updated for v3.0 schema support using shared schema definition.

        Returns:
            PyArrow schema with proper data types and version fields.
        """
        # Use shared schema definition for v3.0 fields
        from mediaplanpy.storage.schema_columns import get_pyarrow_schema

        # Get base schema from shared definition (all v3.0 scalar fields)
        schema = get_pyarrow_schema()

        # Add metadata fields for version tracking
        metadata_fields = [
            pa.field("is_placeholder", pa.bool_()),
            pa.field("export_timestamp", pa.timestamp('ns')),  # When this Parquet was created
            pa.field("sdk_version", pa.string()),  # SDK version used for export
        ]

        # Combine base schema fields with metadata fields
        all_fields = list(schema) + metadata_fields

        return pa.schema(all_fields)

    def _create_complete_dataframe(self, rows: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Create a complete DataFrame with all expected columns efficiently.

        This method creates the DataFrame with all required columns upfront,
        avoiding the performance issues of adding columns one by one.

        Args:
            rows: List of row dictionaries

        Returns:
            Complete DataFrame with all expected columns and proper types
        """
        # Get all expected columns
        all_columns = self._get_all_columns()

        # Add metadata columns that might not be in the column list
        metadata_columns = ["is_placeholder", "export_timestamp", "sdk_version"]
        for col in metadata_columns:
            if col not in all_columns:
                all_columns.append(col)

        if not rows:
            # Create empty DataFrame with all columns
            df = pd.DataFrame(columns=all_columns)
        else:
            # Create DataFrame from rows
            df = pd.DataFrame(rows)

            # Find missing columns
            missing_columns = [col for col in all_columns if col not in df.columns]

            if missing_columns:
                # Create a DataFrame with missing columns filled with None
                missing_df = pd.DataFrame({col: [None] * len(df) for col in missing_columns})

                # Concatenate efficiently - this is much faster than adding columns one by one
                df = pd.concat([df, missing_df], axis=1)

        # Reorder columns for consistency
        df = df[all_columns]

        # Apply data types efficiently
        df = self._apply_data_types(df)

        return df

    def _flatten_media_plan(self, data: Dict[str, Any]) -> pd.DataFrame:
        """
        Flatten hierarchical media plan to tabular format with version metadata.

        Args:
            data: The media plan data to flatten.

        Returns:
            A pandas DataFrame with one row per line item, or a single placeholder row if no line items.
        """
        from datetime import datetime

        meta = data.get("meta", {})
        campaign = data.get("campaign", {})
        lineitems = data.get("lineitems", [])

        # Add export metadata
        export_timestamp = datetime.now()
        try:
            from mediaplanpy import __version__
            sdk_version = __version__
        except ImportError:
            sdk_version = "unknown"

        # Prepare rows
        rows = []

        # If no line items, create a placeholder row with meta and campaign info only
        if not lineitems:
            row = {}

            # Add meta fields with prefix
            for key, value in meta.items():
                row[f"meta_{key}"] = self._convert_value(value)

            # Add campaign fields with prefix
            for key, value in campaign.items():
                row[f"campaign_{key}"] = self._convert_value(value)

            # Add export metadata
            row["is_placeholder"] = True
            row["export_timestamp"] = export_timestamp
            row["sdk_version"] = sdk_version

            rows.append(row)
        else:
            # Create rows with denormalized data for actual line items
            for lineitem in lineitems:
                row = {}

                # Add meta fields with prefix
                for key, value in meta.items():
                    row[f"meta_{key}"] = self._convert_value(value)

                # Add campaign fields with prefix
                for key, value in campaign.items():
                    row[f"campaign_{key}"] = self._convert_value(value)

                # Add lineitem fields with prefix
                for key, value in lineitem.items():
                    row[f"lineitem_{key}"] = self._convert_value(value)

                # Add export metadata
                row["is_placeholder"] = False
                row["export_timestamp"] = export_timestamp
                row["sdk_version"] = sdk_version

                rows.append(row)

        # Create complete DataFrame efficiently
        return self._create_complete_dataframe(rows)

    def _apply_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply explicit data types to DataFrame columns with enhanced version handling.
        Updated for v3.0 field support using type inference from shared schema.

        Args:
            df: The DataFrame to type.

        Returns:
            DataFrame with proper types.
        """
        # Make a copy to avoid SettingWithCopyWarning
        df = df.copy()

        # Import type utilities from shared schema
        from mediaplanpy.storage.schema_columns import get_column_types
        from decimal import Decimal
        from datetime import datetime, date

        # Get column type mapping from shared schema
        column_types = get_column_types()

        # Apply types based on shared schema definition
        for col in df.columns:
            if col not in df.columns:
                continue

            # Skip metadata columns (handled separately)
            if col in ['is_placeholder', 'export_timestamp', 'sdk_version']:
                continue

            # Get expected type from shared schema
            expected_type = column_types.get(col)

            if expected_type == str:
                df[col] = df[col].fillna('').astype(str)
            elif expected_type == Decimal:
                # Decimal -> float for Parquet
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0).astype(float)
            elif expected_type == datetime:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            elif expected_type == date:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
            elif expected_type == bool:
                df[col] = df[col].where(df[col].notna(), False).astype(bool)

        # Ensure schema version is properly formatted (remove 'v' prefix)
        if 'meta_schema_version' in df.columns:
            df['meta_schema_version'] = df['meta_schema_version'].apply(
                lambda x: x.lstrip('v') if isinstance(x, str) else str(x) if x else ''
            )

        # Handle metadata columns
        if 'is_placeholder' in df.columns:
            df['is_placeholder'] = df['is_placeholder'].where(df['is_placeholder'].notna(), False).astype(bool)

        if 'export_timestamp' in df.columns:
            df['export_timestamp'] = pd.to_datetime(df['export_timestamp'], errors='coerce')

        if 'sdk_version' in df.columns:
            df['sdk_version'] = df['sdk_version'].fillna('unknown').astype(str)

        return df

    def _convert_value(self, value: Any) -> Any:
        """
        Convert complex values to Parquet-compatible types.

        Args:
            value: The value to convert.

        Returns:
            The converted value.
        """
        # Convert lists to JSON strings
        if isinstance(value, list):
            return json.dumps(value)

        # Convert Decimal to float
        if hasattr(value, 'is_integer'):  # Decimal check
            return float(value)

        # Keep other types as-is (pandas will handle date/datetime)
        return value

    def _get_all_columns(self) -> List[str]:
        """
        Get all expected columns for v3.0 schema with version metadata.
        Updated to use shared schema definition.

        Returns:
            List of column names in order.
        """
        # Use shared schema definition for v3.0 fields
        from mediaplanpy.storage.schema_columns import get_column_names

        # Get all v3.0 scalar field columns from shared definition
        return get_column_names()

    def get_version_compatibility_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get version compatibility information for the data.

        Args:
            data: Media plan data

        Returns:
            Dictionary with version compatibility details
        """
        schema_version = data.get("meta", {}).get("schema_version")

        compatibility_info = {
            "schema_version": schema_version,
            "is_compatible": False,
            "compatibility_type": "unknown",
            "warnings": [],
            "errors": []
        }

        if not schema_version:
            compatibility_info["errors"].append("No schema version found in data")
            return compatibility_info

        try:
            from mediaplanpy.schema.version_utils import (
                normalize_version,
                get_compatibility_type,
                get_migration_recommendation
            )

            normalized_version = normalize_version(schema_version)
            compatibility_type = get_compatibility_type(normalized_version)

            compatibility_info["normalized_version"] = normalized_version
            compatibility_info["compatibility_type"] = compatibility_type

            if compatibility_type == "unsupported":
                compatibility_info["is_compatible"] = False
                recommendation = get_migration_recommendation(normalized_version)
                compatibility_info["errors"].append(recommendation.get("message", "Version not supported"))
            elif compatibility_type == "deprecated":
                compatibility_info["is_compatible"] = True
                compatibility_info["warnings"].append("Schema version is deprecated")
            else:
                compatibility_info["is_compatible"] = True

            # Check Parquet export requirements
            major_version = int(normalized_version.split('.')[0])
            if major_version < 1:
                compatibility_info["is_compatible"] = False
                compatibility_info["errors"].append("Parquet export requires schema version 1.0 or higher")

        except Exception as e:
            compatibility_info["errors"].append(f"Version validation failed: {str(e)}")

        return compatibility_info