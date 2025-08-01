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
        Updated for v2.0 schema support.

        Returns:
            PyArrow schema with proper data types and version fields.
        """
        fields = []

        # Meta fields (all strings except created_at) - updated for v2.0
        fields.extend([
            pa.field("meta_id", pa.string()),
            pa.field("meta_schema_version", pa.string()),  # 2-digit format (e.g., "1.0")
            pa.field("meta_created_by", pa.string()),  # Legacy field for backward compatibility
            pa.field("meta_created_at", pa.timestamp('ns')),
            pa.field("meta_name", pa.string()),
            pa.field("meta_comments", pa.string()),
            # NEW v2.0 meta fields
            pa.field("meta_created_by_id", pa.string()),
            pa.field("meta_created_by_name", pa.string()),  # Required in v2.0
            pa.field("meta_is_current", pa.bool_()),
            pa.field("meta_is_archived", pa.bool_()),
            pa.field("meta_parent_id", pa.string()),
        ])

        # Campaign fields - existing v1.0 fields
        fields.extend([
            pa.field("campaign_id", pa.string()),
            pa.field("campaign_name", pa.string()),
            pa.field("campaign_objective", pa.string()),
            pa.field("campaign_start_date", pa.date32()),
            pa.field("campaign_end_date", pa.date32()),
            pa.field("campaign_budget_total", pa.float64()),
            pa.field("campaign_product_name", pa.string()),
            pa.field("campaign_product_description", pa.string()),
            pa.field("campaign_audience_name", pa.string()),
            pa.field("campaign_audience_age_start", pa.int32()),
            pa.field("campaign_audience_age_end", pa.int32()),
            pa.field("campaign_audience_gender", pa.string()),
            pa.field("campaign_audience_interests", pa.string()),  # JSON string
            pa.field("campaign_location_type", pa.string()),
            pa.field("campaign_locations", pa.string()),  # JSON string
        ])

        # NEW v2.0 Campaign fields
        fields.extend([
            pa.field("campaign_budget_currency", pa.string()),
            pa.field("campaign_agency_id", pa.string()),
            pa.field("campaign_agency_name", pa.string()),
            pa.field("campaign_advertiser_id", pa.string()),
            pa.field("campaign_advertiser_name", pa.string()),
            pa.field("campaign_product_id", pa.string()),
            pa.field("campaign_campaign_type_id", pa.string()),
            pa.field("campaign_campaign_type_name", pa.string()),
            pa.field("campaign_workflow_status_id", pa.string()),
            pa.field("campaign_workflow_status_name", pa.string()),
        ])

        # Line item fields - existing v1.0 fields
        fields.extend([
            pa.field("lineitem_id", pa.string()),
            pa.field("lineitem_name", pa.string()),
            pa.field("lineitem_start_date", pa.date32()),
            pa.field("lineitem_end_date", pa.date32()),
            pa.field("lineitem_cost_total", pa.float64()),
            pa.field("lineitem_channel", pa.string()),
            pa.field("lineitem_channel_custom", pa.string()),
            pa.field("lineitem_vehicle", pa.string()),
            pa.field("lineitem_vehicle_custom", pa.string()),
            pa.field("lineitem_partner", pa.string()),
            pa.field("lineitem_partner_custom", pa.string()),
            pa.field("lineitem_media_product", pa.string()),
            pa.field("lineitem_media_product_custom", pa.string()),
            pa.field("lineitem_location_type", pa.string()),
            pa.field("lineitem_location_name", pa.string()),
            pa.field("lineitem_target_audience", pa.string()),
            pa.field("lineitem_adformat", pa.string()),
            pa.field("lineitem_adformat_custom", pa.string()),
            pa.field("lineitem_kpi", pa.string()),
            pa.field("lineitem_kpi_custom", pa.string()),
        ])

        # NEW v2.0 Line item fields
        fields.extend([
            pa.field("lineitem_cost_currency", pa.string()),
            pa.field("lineitem_dayparts", pa.string()),
            pa.field("lineitem_dayparts_custom", pa.string()),
            pa.field("lineitem_inventory", pa.string()),
            pa.field("lineitem_inventory_custom", pa.string()),
        ])

        # Custom dimension fields (all strings) - unchanged from v1.0
        for i in range(1, 11):
            fields.append(pa.field(f"lineitem_dim_custom{i}", pa.string()))

        # Cost fields (all floats) - unchanged from v1.0
        cost_fields = [
            "lineitem_cost_media", "lineitem_cost_buying",
            "lineitem_cost_platform", "lineitem_cost_data",
            "lineitem_cost_creative"
        ]
        fields.extend([pa.field(name, pa.float64()) for name in cost_fields])

        # Custom cost fields (all floats) - unchanged from v1.0
        for i in range(1, 11):
            fields.append(pa.field(f"lineitem_cost_custom{i}", pa.float64()))

        # Existing v1.0 metric fields (all floats)
        metric_fields = [
            "lineitem_metric_impressions", "lineitem_metric_clicks",
            "lineitem_metric_views"
        ]
        fields.extend([pa.field(name, pa.float64()) for name in metric_fields])

        # NEW v2.0 standard metric fields (all floats) - 17 new metrics
        new_metric_fields = [
            "lineitem_metric_engagements", "lineitem_metric_followers", "lineitem_metric_visits",
            "lineitem_metric_leads", "lineitem_metric_sales", "lineitem_metric_add_to_cart",
            "lineitem_metric_app_install", "lineitem_metric_application_start", "lineitem_metric_application_complete",
            "lineitem_metric_contact_us", "lineitem_metric_download", "lineitem_metric_signup",
            "lineitem_metric_max_daily_spend", "lineitem_metric_max_daily_impressions", "lineitem_metric_audience_size"
        ]
        fields.extend([pa.field(name, pa.float64()) for name in new_metric_fields])

        # Custom metric fields (all floats) - unchanged from v1.0
        for i in range(1, 11):
            fields.append(pa.field(f"lineitem_metric_custom{i}", pa.float64()))

        # Add metadata fields for version tracking
        fields.extend([
            pa.field("is_placeholder", pa.bool_()),
            pa.field("export_timestamp", pa.timestamp('ns')),  # When this Parquet was created
            pa.field("sdk_version", pa.string()),  # SDK version used for export
        ])

        return pa.schema(fields)

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
        Updated for v2.0 field support and optimized for pandas future compatibility.

        Args:
            df: The DataFrame to type.

        Returns:
            DataFrame with proper types.
        """
        # Make a copy to avoid SettingWithCopyWarning
        df = df.copy()

        # String columns (convert None to empty string)
        string_columns = [
            col for col in df.columns
            if col.startswith(('meta_', 'campaign_', 'lineitem_'))
               and not any(col.endswith(x) for x in [
                '_age_start', '_age_end', '_total', '_cost_', '_metric_',
                '_impressions', '_clicks', '_views', '_created_at',
                '_start_date', '_end_date', '_is_current', '_is_archived'
            ])
        ]

        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str)

        # Ensure schema version is properly formatted
        if 'meta_schema_version' in df.columns:
            # Remove 'v' prefix if present and ensure 2-digit format
            df['meta_schema_version'] = df['meta_schema_version'].apply(
                lambda x: x.lstrip('v') if isinstance(x, str) else str(x) if x else ''
            )

        # Integer columns (unchanged from v1.0)
        int_columns = ['campaign_audience_age_start', 'campaign_audience_age_end']
        for col in int_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype('Int32')

        # Float columns - existing v1.0 fields plus new v2.0 metric fields
        float_columns = [
            col for col in df.columns
            if col.endswith(('_total', '_cost_media', '_cost_buying',
                             '_cost_platform', '_cost_data', '_cost_creative',
                             '_impressions', '_clicks', '_views'))
               or ('_cost_custom' in col)
               or ('_metric_custom' in col)
               # NEW v2.0 metric fields
               or col.endswith(('_metric_engagements', '_metric_followers', '_metric_visits',
                                '_metric_leads', '_metric_sales', '_metric_add_to_cart',
                                '_metric_app_install', '_metric_application_start', '_metric_application_complete',
                                '_metric_contact_us', '_metric_download', '_metric_signup',
                                '_metric_max_daily_spend', '_metric_max_daily_impressions', '_metric_audience_size'))
        ]

        for col in float_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0).astype(float)

        # Date columns (unchanged from v1.0)
        date_columns = [col for col in df.columns if col.endswith(('_start_date', '_end_date'))]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        # Timestamp columns (unchanged from v1.0)
        timestamp_columns = ['meta_created_at', 'export_timestamp']
        for col in timestamp_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Boolean columns - existing and NEW v2.0 fields
        # Explicit boolean conversion to avoid FutureWarning about downcasting
        boolean_columns = ['is_placeholder', 'meta_is_current', 'meta_is_archived']
        for col in boolean_columns:
            if col in df.columns:
                # Simple approach: replace NaN with False first, then convert to bool
                df[col] = df[col].where(df[col].notna(), False).astype(bool)

        # SDK version should be string (unchanged from v1.0)
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
        Get all expected columns for v1.0.0+ schema with version metadata.
        Updated for v2.0 schema support.

        Returns:
            List of column names in order.
        """
        # Meta fields - updated for v2.0
        meta_fields = [
            "meta_id", "meta_schema_version", "meta_created_by",
            "meta_created_at", "meta_name", "meta_comments",
            # NEW v2.0 meta fields
            "meta_created_by_id", "meta_created_by_name",
            "meta_is_current", "meta_is_archived", "meta_parent_id"
        ]

        # Campaign fields - existing v1.0 fields
        campaign_fields = [
            "campaign_id", "campaign_name", "campaign_objective",
            "campaign_start_date", "campaign_end_date", "campaign_budget_total",
            "campaign_product_name", "campaign_product_description",
            "campaign_audience_name", "campaign_audience_age_start",
            "campaign_audience_age_end", "campaign_audience_gender",
            "campaign_audience_interests", "campaign_location_type",
            "campaign_locations"
        ]

        # NEW v2.0 campaign fields
        campaign_fields.extend([
            "campaign_budget_currency",
            "campaign_agency_id", "campaign_agency_name",
            "campaign_advertiser_id", "campaign_advertiser_name",
            "campaign_product_id",
            "campaign_campaign_type_id", "campaign_campaign_type_name",
            "campaign_workflow_status_id", "campaign_workflow_status_name"
        ])

        # Line item fields - existing v1.0 fields
        lineitem_fields = [
            "lineitem_id", "lineitem_name", "lineitem_start_date",
            "lineitem_end_date", "lineitem_cost_total",
            "lineitem_channel", "lineitem_channel_custom",
            "lineitem_vehicle", "lineitem_vehicle_custom",
            "lineitem_partner", "lineitem_partner_custom",
            "lineitem_media_product", "lineitem_media_product_custom",
            "lineitem_location_type", "lineitem_location_name",
            "lineitem_target_audience", "lineitem_adformat",
            "lineitem_adformat_custom", "lineitem_kpi", "lineitem_kpi_custom"
        ]

        # NEW v2.0 line item fields
        lineitem_fields.extend([
            "lineitem_cost_currency",
            "lineitem_dayparts", "lineitem_dayparts_custom",
            "lineitem_inventory", "lineitem_inventory_custom"
        ])

        # Add dimension custom fields (unchanged from v1.0)
        for i in range(1, 11):
            lineitem_fields.append(f"lineitem_dim_custom{i}")

        # Add cost fields (unchanged from v1.0)
        cost_fields = [
            "lineitem_cost_media", "lineitem_cost_buying",
            "lineitem_cost_platform", "lineitem_cost_data",
            "lineitem_cost_creative"
        ]
        lineitem_fields.extend(cost_fields)

        # Add cost custom fields (unchanged from v1.0)
        for i in range(1, 11):
            lineitem_fields.append(f"lineitem_cost_custom{i}")

        # Add existing v1.0 metric fields
        metric_fields = [
            "lineitem_metric_impressions", "lineitem_metric_clicks",
            "lineitem_metric_views"
        ]
        lineitem_fields.extend(metric_fields)

        # Add NEW v2.0 standard metric fields (17 new metrics)
        new_metric_fields = [
            "lineitem_metric_engagements", "lineitem_metric_followers", "lineitem_metric_visits",
            "lineitem_metric_leads", "lineitem_metric_sales", "lineitem_metric_add_to_cart",
            "lineitem_metric_app_install", "lineitem_metric_application_start", "lineitem_metric_application_complete",
            "lineitem_metric_contact_us", "lineitem_metric_download", "lineitem_metric_signup",
            "lineitem_metric_max_daily_spend", "lineitem_metric_max_daily_impressions", "lineitem_metric_audience_size"
        ]
        lineitem_fields.extend(new_metric_fields)

        # Add metric custom fields (unchanged from v1.0)
        for i in range(1, 11):
            lineitem_fields.append(f"lineitem_metric_custom{i}")

        return meta_fields + campaign_fields + lineitem_fields

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