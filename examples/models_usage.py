"""
Example usage of the models module.

This script demonstrates how to create, validate, and manipulate
media plans using the models module.
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

    # 1. Create a media plan from scratch
    logger.info("Creating a media plan from scratch")

    try:
        # Create a new media plan using the factory method
        media_plan = MediaPlan.create_new(
            created_by="example@agency.com",
            campaign_name="Summer 2025 Campaign",
            campaign_objective="Increase brand awareness for new product line",
            campaign_start_date="2025-06-01",
            campaign_end_date="2025-08-31",
            campaign_budget=200000,
            comments="Campaign for the summer product launch",
            target_audience={
                "age_range": "18-34",
                "location": "United States",
                "interests": ["summer", "outdoors", "lifestyle"]
            }
        )

        logger.info(f"Created media plan with campaign: {media_plan.campaign.name}")
        logger.info(f"Campaign date range: {media_plan.campaign.start_date} to {media_plan.campaign.end_date}")
        logger.info(f"Campaign budget: ${media_plan.campaign.budget.total:,.2f}")

        # 2. Add line items to the media plan
        logger.info("Adding line items to the media plan")

        # Social media line item
        media_plan.add_lineitem({
            "id": "li_social_fb_01",
            "channel": "social",
            "platform": "Facebook",
            "publisher": "Meta",
            "start_date": "2025-06-01",
            "end_date": "2025-07-15",
            "budget": 60000,
            "kpi": "CPM",
            "creative_ids": ["cr_001", "cr_002"]
        })

        # Display line item
        media_plan.add_lineitem(LineItem(
            id="li_display_gdn_01",
            channel="display",
            platform="Google Display Network",
            publisher="Google",
            start_date=date(2025, 6, 15),
            end_date=date(2025, 8, 15),
            budget=Decimal("80000"),
            kpi="CPC",
            creative_ids=["cr_003", "cr_004", "cr_005"]
        ))

        # Video line item
        media_plan.add_lineitem({
            "id": "li_video_yt_01",
            "channel": "video",
            "platform": "YouTube",
            "publisher": "Google",
            "start_date": "2025-07-01",
            "end_date": "2025-08-31",
            "budget": 60000,
            "kpi": "CPV",
            "creative_ids": ["cr_006"]
        })

        logger.info(f"Added {len(media_plan.lineitems)} line items to the media plan")

        # 3. Calculate and verify budget
        total_budget = media_plan.calculate_total_budget()
        logger.info(f"Total line item budget: ${total_budget:,.2f}")

        # Check if the line item budget matches the campaign budget
        if total_budget == media_plan.campaign.budget.total:
            logger.info("✅ Line item budgets sum to campaign budget")
        else:
            logger.warning(
                f"⚠️ Line item budgets (${total_budget:,.2f}) do not match campaign budget (${media_plan.campaign.budget.total:,.2f})")

        # 4. Update the campaign budget structure
        logger.info("Updating campaign budget structure")

        # Create a budget breakdown by channel
        media_plan.campaign.budget = Budget(
            total=Decimal("200000"),
            by_channel={
                "social": Decimal("60000"),
                "display": Decimal("80000"),
                "video": Decimal("60000")
            }
        )

        logger.info("Updated campaign budget with channel breakdown")

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
        media_plan_file = output_dir / "example_media_plan.json"
        media_plan.save(media_plan_file)
        logger.info(f"Saved media plan to {media_plan_file}")

        # 7. Load the media plan from file
        logger.info("Loading media plan from file")

        loaded_plan = MediaPlan.from_file(media_plan_file)
        logger.info(f"Loaded media plan with {len(loaded_plan.lineitems)} line items")

        # 8. Modify the loaded plan
        logger.info("Modifying the loaded plan")

        # Get and update a line item
        line_item = loaded_plan.get_lineitem("li_social_fb_01")
        if line_item:
            original_budget = line_item.budget
            line_item.budget = Decimal("65000")
            logger.info(f"Updated line item budget from ${original_budget:,.2f} to ${line_item.budget:,.2f}")

        # 9. Save the modified plan
        modified_plan_file = output_dir / "modified_media_plan.json"
        loaded_plan.save(modified_plan_file)
        logger.info(f"Saved modified media plan to {modified_plan_file}")

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

    logger.info("Example completed successfully!")


if __name__ == "__main__":
    main()