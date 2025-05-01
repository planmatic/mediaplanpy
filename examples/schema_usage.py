"""
Example usage of the schema module.

This script demonstrates how to use the schema module to validate
and migrate media plans.
"""

import json
import os
import logging
from pathlib import Path

from mediaplanpy.schema import (
    SchemaRegistry,
    SchemaValidator,
    SchemaMigrator,
    get_current_version,
    validate_file
)
from mediaplanpy.exceptions import SchemaError, ValidationError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mediaplanpy.examples")

def main():
    """Main function for the example."""
    # Create a schema registry
    logger.info("Creating schema registry...")
    registry = SchemaRegistry()

    # Get schema versions
    current_version = registry.get_current_version()
    supported_versions = registry.get_supported_versions()

    logger.info(f"Current schema version: {current_version}")
    logger.info(f"Supported schema versions: {supported_versions}")

    # Load schema definitions
    try:
        logger.info(f"Loading schema for version {current_version}...")
        schema = registry.load_schema(current_version, "mediaplan.schema.json")
        logger.info(f"Loaded schema: {schema['title']}")
    except SchemaError as e:
        logger.error(f"Error loading schema: {e}")
        return

    # Create a validator
    validator = SchemaValidator(registry=registry)

    # Example media plan
    media_plan = {
        "meta": {
            "schema_version": current_version,
            "created_by": "example@test.com",
            "created_at": "2025-05-01T12:00:00Z"
        },
        "campaign": {
            "id": "example_campaign",
            "name": "Example Campaign",
            "objective": "Brand awareness",
            "start_date": "2025-06-01",
            "end_date": "2025-06-30",
            "budget": {
                "total": 100000
            }
        },
        "lineitems": [
            {
                "id": "li_001",
                "channel": "social",
                "platform": "Facebook",
                "publisher": "Meta",
                "start_date": "2025-06-01",
                "end_date": "2025-06-15",
                "budget": 50000,
                "kpi": "CPM"
            }
        ]
    }

    # Validate the media plan
    logger.info("Validating media plan...")
    errors = validator.validate(media_plan)

    if errors:
        logger.error("Validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
    else:
        logger.info("Validation successful!")

    # Save the media plan to a file
    # Use an absolute path for the output directory
    script_dir = Path(__file__).parent.absolute()
    output_dir = script_dir / "output"

    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    output_file = output_dir / "example_media_plan.json"

    with open(output_file, 'w') as f:
        json.dump(media_plan, f, indent=2)

    logger.info(f"Saved media plan to {output_file}")

    # Validate the file
    logger.info(f"Validating file {output_file}...")
    try:
        file_errors = validator.validate_file(str(output_file))
        if file_errors:
            logger.error("File validation failed:")
            for error in file_errors:
                logger.error(f"  - {error}")
        else:
            logger.info("File validation successful!")
    except ValidationError as e:
        logger.error(f"Error validating file: {e}")

    # Create a migrator (for future use)
    migrator = SchemaMigrator(registry=registry)

    logger.info("Example completed successfully!")


if __name__ == "__main__":
    main()