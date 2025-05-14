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
            table = pa.Table.from_pandas(df)

            writer_properties = pq.ParquetWriter(
                buffer,
                table.schema,
                compression=kwargs.get('compression', self.compression)
            )
            writer_properties.write_table(table)
            writer_properties.close()

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
            file_obj.write(content)
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