"""
Example usage of the models module with v1.0.0 schema support.

This script demonstrates how to create, validate, and manipulate
media plans using the models module following the v1.0.0 schema.
"""

import os
import json
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

from mediaplanpy.models import (
    MediaPlan,
    Campaign,
    Budget,
    TargetAudience,
    LineItem,
    Meta
)
from mediaplanpy.exceptions import ValidationError
from mediaplanpy.schema import SchemaValidator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mediaplanpy.examples")


def main():
    """Main function for the example."""
    # Create output directory for our example
    output_dir = Path(__file__).parent / "output"
    os.makedirs(output_dir, exist_ok=True)

    # 1. Create a media plan from scratch using v1.0.0 schema
    logger.info("Creating a media plan from scratch with v1.0.0 schema")

    try:
        # Create a new media plan using the factory method
        media_plan = MediaPlan.create(
            created_by="example@agency.com",
            campaign_name="Summer 2025 Campaign",
            campaign_objective="Increase brand awareness for new product line",
            campaign_start_date="2025-06-01",
            campaign_end_date="2025-08-31",
            campaign_budget=200000,
            mediaplan_id="summer_2025_plan",  # v1.0.0 requires a media plan ID
            media_plan_name="Summer 2025 Media Plan",  # Optional name for the media plan
            comments="Campaign for the summer product launch",
            # v1.0.0 audience parameters - more structured now
            audience_age_start=18,
            audience_age_end=34,
            audience_gender="Any",
            audience_interests=["summer", "outdoors", "lifestyle"],
            location_type="Country",
            locations=["United States"]
        )

        logger.info(f"Created media plan with ID: {media_plan.meta.id}")
        logger.info(f"Media plan name: {media_plan.meta.name}")
        logger.info(f"Campaign date range: {media_plan.campaign.start_date} to {media_plan.campaign.end_date}")
        logger.info(f"Campaign budget: ${media_plan.campaign.budget_total:,.2f}")
        logger.info(f"Target audience: ages {media_plan.campaign.audience_age_start}-{media_plan.campaign.audience_age_end}")

        # 2. Add line items to the media plan
        logger.info("Adding line items to the media plan")

        # Social media line item with v1.0.0 structure
        media_plan.add_lineitem({
            "id": "li_social_fb_01",
            "name": "Facebook Campaign",  # v1.0.0 requires a name
            "start_date": "2025-06-01",
            "end_date": "2025-07-15",
            "cost_total": 60000,  # v1.0.0 uses cost_total instead of budget
            "channel": "social",
            "vehicle": "Facebook",  # v1.0.0 uses vehicle instead of platform
            "partner": "Meta",  # v1.0.0 uses partner instead of publisher
            "kpi": "CPM",
            "metric_impressions": 10000000,  # v1.0.0 supports specific metrics
            "metric_clicks": 150000
        })

        # Display line item with v1.0.0 structure
        media_plan.add_lineitem(LineItem(
            id="li_display_gdn_01",
            name="Google Display Network",  # Required in v1.0.0
            start_date=date(2025, 6, 15),
            end_date=date(2025, 8, 15),
            cost_total=Decimal("80000"),  # v1.0.0 uses cost_total
            channel="display",
            vehicle="Google Display Network",  # v1.0.0 uses vehicle
            partner="Google",  # v1.0.0 uses partner
            kpi="CPC",
            metric_impressions=Decimal("20000000"),
            metric_clicks=Decimal("250000")
        ))

        # Video line item with v1.0.0 structure
        media_plan.add_lineitem({
            "id": "li_video_yt_01",
            "name": "YouTube Pre-roll Campaign",  # Required in v1.0.0
            "start_date": "2025-07-01",
            "end_date": "2025-08-31",
            "cost_total": 60000,  # v1.0.0 uses cost_total
            "channel": "video",
            "vehicle": "YouTube",  # v1.0.0 uses vehicle
            "partner": "Google",  # v1.0.0 uses partner
            "kpi": "CPV",
            "metric_impressions": 5000000,
            "metric_views": 1500000
        })

        logger.info(f"Added {len(media_plan.lineitems)} line items to the media plan")

        # 3. Calculate and verify total cost
        total_cost = media_plan.calculate_total_cost()  # v1.0.0 uses calculate_total_cost
        logger.info(f"Total line item cost: ${total_cost:,.2f}")

        # Check if the line item costs match the campaign budget
        if total_cost == media_plan.campaign.budget_total:
            logger.info("✅ Line item costs sum to campaign budget")
        else:
            logger.warning(
                f"⚠️ Line item costs (${total_cost:,.2f}) do not match campaign budget (${media_plan.campaign.budget_total:,.2f})")

        # 4. Add detailed cost breakdowns (v1.0.0 feature)
        logger.info("Adding detailed cost breakdowns to a line item")

        # Get the first line item
        line_item = media_plan.lineitems[0]

        # Add cost breakdowns
        line_item.cost_media = Decimal("45000")
        line_item.cost_platform = Decimal("5000")
        line_item.cost_data = Decimal("8000")
        line_item.cost_creative = Decimal("2000")

        logger.info(f"Cost breakdown for {line_item.name}:")
        logger.info(f"  - Media: ${line_item.cost_media:,.2f}")
        logger.info(f"  - Platform: ${line_item.cost_platform:,.2f}")
        logger.info(f"  - Data: ${line_item.cost_data:,.2f}")
        logger.info(f"  - Creative: ${line_item.cost_creative:,.2f}")
        cost_sum = line_item.cost_media + line_item.cost_platform + line_item.cost_data + line_item.cost_creative
        logger.info(f"  - Sum of cost components: ${cost_sum:,.2f}")
        logger.info(f"  - Total cost: ${line_item.cost_total:,.2f}")

        # 5. Validate the complete media plan
        logger.info("Validating the media plan")

        # Internal validation
        model_errors = media_plan.validate_model()
        if model_errors:
            logger.error("Model validation failed:")
            for error in model_errors:
                logger.error(f"  - {error}")
        else:
            logger.info("✅ Model validation passed")

        # Schema validation
        schema_validator = SchemaValidator()
        schema_errors = media_plan.validate_against_schema(schema_validator)
        if schema_errors:
            logger.error("Schema validation failed:")
            for error in schema_errors:
                logger.error(f"  - {error}")
        else:
            logger.info("✅ Schema validation passed")

        # 6. Convert to JSON and save to file
        logger.info("Saving media plan to JSON file")

        # Convert to JSON
        json_data = media_plan.to_json(indent=2)

        # Save to file
        media_plan_file = output_dir / "example_media_plan_v1.json"
        media_plan.export_to_json(media_plan_file)
        logger.info(f"Saved media plan to {media_plan_file}")

        # 7. Load the media plan from file
        logger.info("Loading media plan from file")

        loaded_plan = MediaPlan.import_from_json(media_plan_file)
        logger.info(f"Loaded media plan with ID: {loaded_plan.meta.id}")
        logger.info(f"Loaded plan has {len(loaded_plan.lineitems)} line items")

        # 8. Modify the loaded plan
        logger.info("Modifying the loaded plan")

        # Get and update a line item
        line_item = loaded_plan.get_lineitem("li_social_fb_01")
        if line_item:
            original_cost = line_item.cost_total
            line_item.cost_total = Decimal("65000")
            logger.info(f"Updated line item cost from ${original_cost:,.2f} to ${line_item.cost_total:,.2f}")

            # Also update metrics
            line_item.metric_impressions = Decimal("12000000")
            logger.info(f"Updated impressions target to {line_item.metric_impressions:,}")

        # 9. Save the modified plan
        modified_plan_file = output_dir / "modified_media_plan_v1.json"
        loaded_plan.export_to_json(modified_plan_file)
        logger.info(f"Saved modified media plan to {modified_plan_file}")

        # 10. Demonstrate migration from v0.0.0 to v1.0.0
        logger.info("Demonstrating migration from v0.0.0 to v1.0.0")

        # Create a v0.0.0 style media plan
        v0_media_plan = {
            "meta": {
                "schema_version": "v0.0.0",
                "created_by": "example@agency.com",
                "created_at": "2025-06-01T12:00:00Z",
                "comments": "Legacy media plan in v0.0.0 format"
            },
            "campaign": {
                "id": "legacy_campaign",
                "name": "Legacy Campaign",
                "objective": "awareness",
                "start_date": "2025-06-01",
                "end_date": "2025-08-31",
                "budget": {
                    "total": 100000,
                    "by_channel": {
                        "social": 60000,
                        "display": 40000
                    }
                },
                "target_audience": {
                    "age_range": "18-34",
                    "location": "United States",
                    "interests": ["technology", "gadgets"]
                }
            },
            "lineitems": [
                {
                    "id": "legacy_li_001",
                    "channel": "social",
                    "platform": "Instagram",
                    "publisher": "Meta",
                    "start_date": "2025-06-01",
                    "end_date": "2025-07-31",
                    "budget": 60000,
                    "kpi": "CPM",
                    "creative_ids": ["cr001", "cr002"]
                },
                {
                    "id": "legacy_li_002",
                    "channel": "display",
                    "platform": "Google Display Network",
                    "publisher": "Google",
                    "start_date": "2025-07-01",
                    "end_date": "2025-08-31",
                    "budget": 40000,
                    "kpi": "CPC"
                }
            ]
        }

        # Convert to v1.0.0 using our helper method
        v1_migrated_plan = MediaPlan.from_v0_mediaplan(v0_media_plan)

        logger.info(f"Migrated media plan from v0.0.0 to v1.0.0")
        logger.info(f"Generated media plan ID: {v1_migrated_plan.meta.id}")
        logger.info(f"Campaign budget_total: ${v1_migrated_plan.campaign.budget_total:,.2f}")
        logger.info(f"Line item count: {len(v1_migrated_plan.lineitems)}")
        logger.info(f"First line item name: {v1_migrated_plan.lineitems[0].name}")
        logger.info(f"First line item cost_total: ${v1_migrated_plan.lineitems[0].cost_total:,.2f}")

        # Save the migrated plan
        migrated_plan_file = output_dir / "migrated_media_plan_v1.json"
        v1_migrated_plan.export_to_json(migrated_plan_file)
        logger.info(f"Saved migrated plan to {migrated_plan_file}")

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

    logger.info("Example completed successfully!")


if __name__ == "__main__":
    main()