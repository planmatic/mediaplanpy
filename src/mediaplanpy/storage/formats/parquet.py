# src/mediaplanpy/storage/formats/parquet.py
"""
Parquet format handler for mediaplanpy.

This module provides a Parquet format handler for serializing and
deserializing media plans to/from Parquet format.
"""

import io
import json
import logging
from typing import Dict, Any, List, Union, BinaryIO

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from mediaplanpy.exceptions import StorageError
from mediaplanpy.storage.formats.base import FormatHandler, register_format

logger = logging.getLogger("mediaplanpy.storage.formats.parquet")


@register_format
class ParquetFormatHandler(FormatHandler):
    """
    Handler for Parquet format.

    Serializes and deserializes media plans to/from Parquet format.
    """

    format_name = "parquet"
    file_extension = "parquet"
    media_types = ["application/x-parquet"]
    is_binary = True

    def __init__(self, compression: str = "snappy", **kwargs):
        """
        Initialize the Parquet format handler.

        Args:
            compression: Compression algorithm to use.
            **kwargs: Additional Parquet encoding options.
        """
        self.compression = compression
        self.options = kwargs

    def serialize(self, data: Dict[str, Any], **kwargs) -> bytes:
        """
        Serialize data to Parquet binary format.

        Args:
            data: The media plan data to serialize.
            **kwargs: Additional Parquet encoding options.

        Returns:
            The serialized Parquet binary data.

        Raises:
            StorageError: If the data cannot be serialized.
        """
        try:
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
        Serialize data and write it to a file object.

        Args:
            data: The data to serialize.
            file_obj: A file-like object to write to.
            **kwargs: Additional Parquet encoding options.

        Raises:
            StorageError: If the data cannot be serialized or written.
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
        Define explicit schema for the Parquet file.

        Returns:
            PyArrow schema with proper data types.
        """
        fields = []

        # Meta fields (all strings except created_at)
        fields.extend([
            pa.field("meta_id", pa.string()),
            pa.field("meta_schema_version", pa.string()),
            pa.field("meta_created_by", pa.string()),
            pa.field("meta_created_at", pa.timestamp('ns')),
            pa.field("meta_name", pa.string()),
            pa.field("meta_comments", pa.string()),
        ])

        # Campaign fields
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

        # Line item fields
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

        # Custom dimension fields (all strings)
        for i in range(1, 11):
            fields.append(pa.field(f"lineitem_dim_custom{i}", pa.string()))

        # Cost fields (all floats)
        cost_fields = [
            "lineitem_cost_media", "lineitem_cost_buying",
            "lineitem_cost_platform", "lineitem_cost_data",
            "lineitem_cost_creative"
        ]
        fields.extend([pa.field(name, pa.float64()) for name in cost_fields])

        # Custom cost fields (all floats)
        for i in range(1, 11):
            fields.append(pa.field(f"lineitem_cost_custom{i}", pa.float64()))

        # Metric fields (all floats)
        metric_fields = [
            "lineitem_metric_impressions", "lineitem_metric_clicks",
            "lineitem_metric_views"
        ]
        fields.extend([pa.field(name, pa.float64()) for name in metric_fields])

        # Custom metric fields (all floats)
        for i in range(1, 11):
            fields.append(pa.field(f"lineitem_metric_custom{i}", pa.float64()))

        return pa.schema(fields)

    def _flatten_media_plan(self, data: Dict[str, Any]) -> pd.DataFrame:
        """
        Flatten hierarchical media plan to tabular format.

        Args:
            data: The media plan data to flatten.

        Returns:
            A pandas DataFrame with one row per line item.
        """
        meta = data.get("meta", {})
        campaign = data.get("campaign", {})
        lineitems = data.get("lineitems", [])

        # If no line items, create empty DataFrame with all columns
        if not lineitems:
            return self._create_empty_dataframe()

        # Create rows with denormalized data
        rows = []
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

            rows.append(row)

        df = pd.DataFrame(rows)

        # Ensure all expected columns exist (fill missing with None)
        all_columns = self._get_all_columns()
        for col in all_columns:
            if col not in df.columns:
                df[col] = None

        # Reorder columns for consistency
        df = df[all_columns]

        # Apply explicit data types
        df = self._apply_data_types(df)

        return df

    def _apply_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply explicit data types to DataFrame columns.

        Args:
            df: The DataFrame to type.

        Returns:
            DataFrame with proper types.
        """
        # String columns (convert None to empty string)
        string_columns = [
            col for col in df.columns
            if col.startswith(('meta_', 'campaign_', 'lineitem_'))
               and not any(col.endswith(x) for x in [
                '_age_start', '_age_end', '_total', '_cost_', '_metric_',
                '_impressions', '_clicks', '_views', '_created_at',
                '_start_date', '_end_date'
            ])
        ]

        for col in string_columns:
            df[col] = df[col].fillna('').astype(str)

        # Integer columns
        int_columns = ['campaign_audience_age_start', 'campaign_audience_age_end']
        for col in int_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype('Int32')

        # Float columns
        float_columns = [
            col for col in df.columns
            if col.endswith(('_total', '_cost_media', '_cost_buying',
                             '_cost_platform', '_cost_data', '_cost_creative',
                             '_impressions', '_clicks', '_views'))
               or ('_cost_custom' in col)
               or ('_metric_custom' in col)
        ]

        for col in float_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0).astype(float)

        # Date columns
        date_columns = [col for col in df.columns if col.endswith(('_start_date', '_end_date'))]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        # Timestamp columns
        if 'meta_created_at' in df.columns:
            df['meta_created_at'] = pd.to_datetime(df['meta_created_at'], errors='coerce')

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
        Get all expected columns for v1.0.0 schema.

        Returns:
            List of column names in order.
        """
        meta_fields = [
            "meta_id", "meta_schema_version", "meta_created_by",
            "meta_created_at", "meta_name", "meta_comments"
        ]

        campaign_fields = [
            "campaign_id", "campaign_name", "campaign_objective",
            "campaign_start_date", "campaign_end_date", "campaign_budget_total",
            "campaign_product_name", "campaign_product_description",
            "campaign_audience_name", "campaign_audience_age_start",
            "campaign_audience_age_end", "campaign_audience_gender",
            "campaign_audience_interests", "campaign_location_type",
            "campaign_locations"
        ]

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

        # Add dimension custom fields
        for i in range(1, 11):
            lineitem_fields.append(f"lineitem_dim_custom{i}")

        # Add cost fields
        cost_fields = [
            "lineitem_cost_media", "lineitem_cost_buying",
            "lineitem_cost_platform", "lineitem_cost_data",
            "lineitem_cost_creative"
        ]
        lineitem_fields.extend(cost_fields)

        # Add cost custom fields
        for i in range(1, 11):
            lineitem_fields.append(f"lineitem_cost_custom{i}")

        # Add metric fields
        metric_fields = [
            "lineitem_metric_impressions", "lineitem_metric_clicks",
            "lineitem_metric_views"
        ]
        lineitem_fields.extend(metric_fields)

        # Add metric custom fields
        for i in range(1, 11):
            lineitem_fields.append(f"lineitem_metric_custom{i}")

        return meta_fields + campaign_fields + lineitem_fields

    def _create_empty_dataframe(self) -> pd.DataFrame:
        """
        Create an empty DataFrame with all expected columns.

        Returns:
            An empty pandas DataFrame with all columns.
        """
        columns = self._get_all_columns()
        return pd.DataFrame(columns=columns)