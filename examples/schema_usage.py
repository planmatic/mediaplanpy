"""
Example usage of the schema module with v1.0.0 schema support.

This script demonstrates how to use the schema module to validate
and migrate media plans between schema versions.
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

    # Example v1.0.0 media plan
    v1_media_plan = {
        "meta": {
            "id": "mediaplan_example",  # Required in v1.0.0
            "schema_version": current_version,
            "name": "Example Media Plan",  # Optional in v1.0.0
            "created_by": "example@test.com",
            "created_at": "2025-05-01T12:00:00Z"
        },
        "campaign": {
            "id": "example_campaign",
            "name": "Example Campaign",
            "objective": "Brand awareness",
            "start_date": "2025-06-01",
            "end_date": "2025-06-30",
            "budget_total": 100000,  # Changed from budget.total in v1.0.0
            # v1.0.0 audience fields
            "audience_age_start": 18,
            "audience_age_end": 34,
            "audience_gender": "Any",
            "audience_interests": ["technology", "social media"],
            # v1.0.0 location fields
            "location_type": "Country",
            "locations": ["United States"]
        },
        "lineitems": [
            {
                "id": "li_001",
                "name": "Social Media Campaign",  # Required in v1.0.0
                "start_date": "2025-06-01",
                "end_date": "2025-06-15",
                "cost_total": 50000,  # Changed from budget in v1.0.0
                "channel": "social",
                "vehicle": "Facebook",  # Changed from platform in v1.0.0
                "partner": "Meta",      # Changed from publisher in v1.0.0
                "kpi": "CPM",
                # v1.0.0 metrics
                "metric_impressions": 5000000,
                "metric_clicks": 75000
            }
        ]
    }

    # Validate the v1.0.0 media plan
    logger.info("Validating v1.0.0 media plan...")
    errors = validator.validate(v1_media_plan)

    if errors:
        logger.error("Validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
    else:
        logger.info("Validation successful!")

    # Save the v1.0.0 media plan to a file
    # Use an absolute path for the output directory
    script_dir = Path(__file__).parent.absolute()
    output_dir = script_dir / "output"

    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    output_file = output_dir / "example_media_plan_v1.json"

    with open(output_file, 'w') as f:
        json.dump(v1_media_plan, f, indent=2)

    logger.info(f"Saved v1.0.0 media plan to {output_file}")

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

    # Example v0.0.0 media plan
    v0_media_plan = {
        "meta": {
            "schema_version": "v0.0.0",
            "created_by": "example@test.com",
            "created_at": "2025-05-01T12:00:00Z"
        },
        "campaign": {
            "id": "legacy_campaign",
            "name": "Legacy Campaign",
            "objective": "Brand awareness",
            "start_date": "2025-06-01",
            "end_date": "2025-06-30",
            "budget": {
                "total": 80000,
                "by_channel": {
                    "social": 50000,
                    "display": 30000
                }
            },
            "target_audience": {
                "age_range": "18-34",
                "location": "United States",
                "interests": ["technology", "social media"]
            }
        },
        "lineitems": [
            {
                "id": "legacy_li_001",
                "channel": "social",
                "platform": "Facebook",
                "publisher": "Meta",
                "start_date": "2025-06-01",
                "end_date": "2025-06-15",
                "budget": 50000,
                "kpi": "CPM",
                "creative_ids": ["cr001", "cr002"]
            }
        ]
    }

    # Save the v0.0.0 media plan
    v0_output_file = output_dir / "legacy_media_plan_v0.json"
    with open(v0_output_file, 'w') as f:
        json.dump(v0_media_plan, f, indent=2)

    logger.info(f"Saved v0.0.0 media plan to {v0_output_file}")

    # Create a migrator
    migrator = SchemaMigrator(registry=registry)

    # Migrate v0.0.0 to v1.0.0
    logger.info("Migrating media plan from v0.0.0 to v1.0.0...")
    try:
        # Migrate the plan
        migrated_plan = migrator.migrate(v0_media_plan, "v0.0.0", "v1.0.0")

        # Log the changes
        logger.info("Migration successful!")
        logger.info(f"Generated media plan ID: {migrated_plan['meta']['id']}")
        logger.info(f"Original budget: {v0_media_plan['campaign']['budget']['total']}")
        logger.info(f"New budget_total: {migrated_plan['campaign']['budget_total']}")

        # Show the transformation of audience information
        logger.info("Audience transformation:")
        if "audience_age_start" in migrated_plan["campaign"]:
            logger.info(f"  Original age_range: {v0_media_plan['campaign']['target_audience']['age_range']}")
            logger.info(f"  New age range: {migrated_plan['campaign']['audience_age_start']}-"
                        f"{migrated_plan['campaign']['audience_age_end']}")

        # Show the transformation of line items
        logger.info("Line item transformation:")
        if migrated_plan["lineitems"]:
            logger.info(f"  Original budget: {v0_media_plan['lineitems'][0]['budget']}")
            logger.info(f"  New cost_total: {migrated_plan['lineitems'][0]['cost_total']}")
            logger.info(f"  Original platform: {v0_media_plan['lineitems'][0]['platform']}")
            logger.info(f"  New vehicle: {migrated_plan['lineitems'][0]['vehicle']}")
            logger.info(f"  Original publisher: {v0_media_plan['lineitems'][0]['publisher']}")
            logger.info(f"  New partner: {migrated_plan['lineitems'][0]['partner']}")

        # Save the migrated plan
        migrated_output_file = output_dir / "migrated_media_plan_v1.json"
        with open(migrated_output_file, 'w') as f:
            json.dump(migrated_plan, f, indent=2)

        logger.info(f"Saved migrated media plan to {migrated_output_file}")

        # Validate the migrated plan
        logger.info("Validating migrated plan against v1.0.0 schema...")
        migration_errors = validator.validate(migrated_plan, "v1.0.0")

        if migration_errors:
            logger.error("Migrated plan validation failed:")
            for error in migration_errors:
                logger.error(f"  - {error}")
        else:
            logger.info("Migrated plan validation successful!")

    except SchemaError as e:
        logger.error(f"Error during migration: {e}")

    logger.info("Schema example completed successfully!")


if __name__ == "__main__":
    main()