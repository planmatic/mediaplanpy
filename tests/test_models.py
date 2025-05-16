"""
Tests for the models module with v1.0.0 schema support.
"""
import json
import tempfile
import os
from datetime import date, datetime
from decimal import Decimal
import copy
import pytest

from mediaplanpy.models import (
    BaseModel,
    LineItem,
    Campaign,
    Budget,
    TargetAudience,
    MediaPlan,
    Meta
)
from mediaplanpy.exceptions import ValidationError


class TestLineItem:
    """Tests for the LineItem model."""

    def test_create_lineitem_v1(self):
        """Test creating a line item with v1.0.0 schema."""
        line_item = LineItem(
            id="line_item_1",
            name="Social Media Campaign",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            cost_total=Decimal("10000"),
            channel="social",
            vehicle="Facebook",
            partner="Meta",
            kpi="CPM",
            metric_impressions=Decimal("1000000"),
            metric_clicks=Decimal("5000")
        )

        assert line_item.id == "line_item_1"
        assert line_item.name == "Social Media Campaign"
        assert line_item.start_date == date(2025, 1, 1)
        assert line_item.end_date == date(2025, 3, 31)
        assert line_item.cost_total == Decimal("10000")
        assert line_item.channel == "social"
        assert line_item.vehicle == "Facebook"
        assert line_item.partner == "Meta"
        assert line_item.kpi == "CPM"
        assert line_item.metric_impressions == Decimal("1000000")
        assert line_item.metric_clicks == Decimal("5000")

    def test_lineitem_backward_compatibility(self):
        """Test creating a v0.0.0 compatible line item and migrating it."""
        # Create with v0.0.0 style fields
        v0_data = {
            "id": "line_item_1",
            "channel": "social",
            "platform": "Facebook",
            "publisher": "Meta",
            "start_date": date(2025, 1, 1),
            "end_date": date(2025, 3, 31),
            "budget": Decimal("10000"),
            "kpi": "CPM",
            "creative_ids": ["creative_1", "creative_2"]
        }

        # Convert to v1.0.0
        v1_line_item = LineItem.from_v0_lineitem(v0_data)

        # Verify conversion
        assert v1_line_item.id == "line_item_1"
        assert v1_line_item.name == "line_item_1"  # Default to ID
        assert v1_line_item.start_date == date(2025, 1, 1)
        assert v1_line_item.end_date == date(2025, 3, 31)
        assert v1_line_item.cost_total == Decimal("10000")
        assert v1_line_item.channel == "social"
        assert v1_line_item.vehicle == "Facebook"
        assert v1_line_item.partner == "Meta"
        assert v1_line_item.kpi == "CPM"
        assert "creative_ids" in v1_line_item.dim_custom1

    def test_invalid_dates(self):
        """Test validation of line item with invalid dates."""
        with pytest.raises(ValueError):
            LineItem(
                id="line_item_1",
                name="Test Line Item",
                start_date=date(2025, 4, 1),  # Start after end
                end_date=date(2025, 3, 31),
                cost_total=Decimal("10000")
            )

    def test_invalid_cost(self):
        """Test validation of line item with invalid cost."""
        with pytest.raises(ValueError):
            LineItem(
                id="line_item_1",
                name="Test Line Item",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31),
                cost_total=Decimal("-100")  # Negative cost
            )

    def test_validation(self):
        """Test validation method."""
        # Valid line item
        line_item = LineItem(
            id="line_item_1",
            name="Test Line Item",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            cost_total=Decimal("10000"),
            channel="social"
        )

        # Should validate without errors
        assert line_item.validate_model() == []

        # Invalid channel
        line_item = LineItem(
            id="line_item_1",
            name="Test Line Item",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            cost_total=Decimal("10000"),
            channel="invalid_channel"  # Invalid channel
        )

        errors = line_item.validate_model()
        assert len(errors) > 0
        assert "channel" in errors[0]

    def test_to_dict(self):
        """Test conversion to dictionary."""
        line_item = LineItem(
            id="line_item_1",
            name="Test Line Item",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            cost_total=Decimal("10000"),
            channel="social"
        )

        data = line_item.to_dict()
        assert data["id"] == "line_item_1"
        assert data["name"] == "Test Line Item"
        assert data["start_date"] == "2025-01-01"
        assert data["end_date"] == "2025-03-31"
        assert data["cost_total"] == 10000
        assert data["channel"] == "social"


class TestCampaign:
    """Tests for the Campaign model."""

    def test_create_campaign_v1(self):
        """Test creating a campaign with v1.0.0 schema."""
        campaign = Campaign(
            id="campaign_1",
            name="Test Campaign",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000"),
            audience_age_start=18,
            audience_age_end=34,
            audience_gender="Any",
            audience_interests=["sports", "technology"],
            location_type="Country",
            locations=["United States"]
        )

        assert campaign.id == "campaign_1"
        assert campaign.name == "Test Campaign"
        assert campaign.objective == "awareness"
        assert campaign.start_date == date(2025, 1, 1)
        assert campaign.end_date == date(2025, 12, 31)
        assert campaign.budget_total == Decimal("100000")
        assert campaign.audience_age_start == 18
        assert campaign.audience_age_end == 34
        assert campaign.audience_gender == "Any"
        assert "sports" in campaign.audience_interests
        assert campaign.location_type == "Country"
        assert "United States" in campaign.locations

    def test_campaign_backward_compatibility(self):
        """Test creating a v0.0.0 compatible campaign and migrating it."""
        # Create with v0.0.0 style fields
        v0_data = {
            "id": "campaign_1",
            "name": "Test Campaign",
            "objective": "awareness",
            "start_date": date(2025, 1, 1),
            "end_date": date(2025, 12, 31),
            "budget": {
                "total": Decimal("100000"),
                "by_channel": {
                    "social": Decimal("50000"),
                    "display": Decimal("50000")
                }
            },
            "target_audience": {
                "age_range": "18-34",
                "location": "United States",
                "interests": ["sports", "technology"]
            }
        }

        # Convert to v1.0.0
        v1_campaign = Campaign.from_v0_campaign(v0_data)

        # Verify conversion
        assert v1_campaign.id == "campaign_1"
        assert v1_campaign.name == "Test Campaign"
        assert v1_campaign.objective == "awareness"
        assert v1_campaign.start_date == date(2025, 1, 1)
        assert v1_campaign.end_date == date(2025, 12, 31)
        assert v1_campaign.budget_total == Decimal("100000")
        assert v1_campaign.audience_age_start == 18
        assert v1_campaign.audience_age_end == 34
        assert "sports" in v1_campaign.audience_interests
        assert v1_campaign.location_type == "Country"
        assert "United States" in v1_campaign.locations

    def test_invalid_dates(self):
        """Test validation of campaign with invalid dates."""
        with pytest.raises(ValueError):
            Campaign(
                id="campaign_1",
                name="Test Campaign",
                objective="awareness",
                start_date=date(2025, 12, 31),  # Start after end
                end_date=date(2025, 1, 1),
                budget_total=Decimal("100000")
            )

    def test_budget_validation(self):
        """Test budget validation."""
        # Valid budget total
        campaign = Campaign(
            id="campaign_1",
            name="Test Campaign",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000")
        )
        assert campaign.validate_model() == []

        # Invalid budget total (negative)
        with pytest.raises(ValueError):
            Campaign(
                id="campaign_1",
                name="Test Campaign",
                objective="awareness",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("-100")
            )

    def test_audience_validation(self):
        """Test audience validation."""
        # Valid audience
        campaign = Campaign(
            id="campaign_1",
            name="Test Campaign",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000"),
            audience_age_start=18,
            audience_age_end=34
        )
        assert campaign.validate_model() == []

        # Invalid audience age (start > end)
        campaign = Campaign(
            id="campaign_1",
            name="Test Campaign",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000"),
            audience_age_start=34,
            audience_age_end=18
        )
        errors = campaign.validate_model()
        assert len(errors) > 0
        assert "audience_age" in errors[0]

        # Invalid gender
        with pytest.raises(ValueError):
            Campaign(
                id="campaign_1",
                name="Test Campaign",
                objective="awareness",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000"),
                audience_gender="Invalid"
            )

        # Invalid location type
        with pytest.raises(ValueError):
            Campaign(
                id="campaign_1",
                name="Test Campaign",
                objective="awareness",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000"),
                location_type="Invalid"
            )

    def test_legacy_budget_class(self):
        """Test that the legacy Budget class still works for backward compatibility."""
        budget = Budget(
            total=Decimal("100000"),
            by_channel={
                "social": Decimal("50000"),
                "display": Decimal("50000")
            }
        )
        assert budget.total == Decimal("100000")
        assert budget.by_channel["social"] == Decimal("50000")
        assert budget.validate_model() == []

    def test_legacy_targetaudience_class(self):
        """Test that the legacy TargetAudience class still works for backward compatibility."""
        target_audience = TargetAudience(
            age_range="18-34",
            location="United States",
            interests=["sports", "technology"]
        )
        assert target_audience.age_range == "18-34"
        assert target_audience.location == "United States"
        assert "sports" in target_audience.interests


class TestMediaPlan:
    """Tests for the MediaPlan model."""

    def test_create_mediaplan_v1(self):
        """Test creating a media plan with v1.0.0 schema."""
        media_plan = MediaPlan(
            meta=Meta(
                id="mediaplan_12345",
                schema_version="v1.0.0",
                created_by="test@example.com",
                created_at=datetime(2025, 1, 1, 12, 0, 0),
                name="Test Media Plan",
                comments="Test media plan"
            ),
            campaign=Campaign(
                id="campaign_1",
                name="Test Campaign",
                objective="awareness",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000"),
                audience_age_start=18,
                audience_age_end=34,
                location_type="Country",
                locations=["United States"]
            ),
            lineitems=[
                LineItem(
                    id="line_item_1",
                    name="Social Line Item",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 3, 31),
                    cost_total=Decimal("30000"),
                    channel="social",
                    vehicle="Facebook",
                    partner="Meta",
                    kpi="CPM"
                ),
                LineItem(
                    id="line_item_2",
                    name="Display Line Item",
                    start_date=date(2025, 4, 1),
                    end_date=date(2025, 6, 30),
                    cost_total=Decimal("40000"),
                    channel="display",
                    vehicle="Google Display Network",
                    partner="Google",
                    kpi="CPC"
                )
            ]
        )

        assert media_plan.meta.id == "mediaplan_12345"
        assert media_plan.meta.schema_version == "v1.0.0"
        assert media_plan.meta.created_by == "test@example.com"
        assert media_plan.meta.name == "Test Media Plan"
        assert media_plan.campaign.name == "Test Campaign"
        assert media_plan.campaign.budget_total == Decimal("100000")
        assert len(media_plan.lineitems) == 2
        assert media_plan.lineitems[0].name == "Social Line Item"
        assert media_plan.lineitems[0].channel == "social"
        assert media_plan.lineitems[1].name == "Display Line Item"
        assert media_plan.lineitems[1].channel == "display"

    def test_mediaplan_backward_compatibility(self):
        """Test migrating a v0.0.0 media plan to v1.0.0."""
        # Create with v0.0.0 style data
        v0_data = {
            "meta": {
                "schema_version": "v0.0.0",
                "created_by": "test@example.com",
                "created_at": "2025-01-01T12:00:00Z",
                "comments": "Test media plan"
            },
            "campaign": {
                "id": "campaign_1",
                "name": "Test Campaign",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget": {
                    "total": 100000,
                    "by_channel": {
                        "social": 50000,
                        "display": 50000
                    }
                },
                "target_audience": {
                    "age_range": "18-34",
                    "location": "United States",
                    "interests": ["sports", "technology"]
                }
            },
            "lineitems": [
                {
                    "id": "line_item_1",
                    "channel": "social",
                    "platform": "Facebook",
                    "publisher": "Meta",
                    "start_date": "2025-01-01",
                    "end_date": "2025-03-31",
                    "budget": 30000,
                    "kpi": "CPM"
                },
                {
                    "id": "line_item_2",
                    "channel": "display",
                    "platform": "Google Display Network",
                    "publisher": "Google",
                    "start_date": "2025-04-01",
                    "end_date": "2025-06-30",
                    "budget": 40000,
                    "kpi": "CPC"
                }
            ]
        }

        # Convert to v1.0.0
        v1_media_plan = MediaPlan.from_v0_mediaplan(v0_data)

        # Verify conversion
        assert v1_media_plan.meta.schema_version == "v1.0.0"
        assert v1_media_plan.meta.created_by == "test@example.com"
        assert hasattr(v1_media_plan.meta, "id")
        assert v1_media_plan.campaign.name == "Test Campaign"
        assert v1_media_plan.campaign.budget_total == Decimal("100000")
        assert v1_media_plan.campaign.audience_age_start == 18
        assert v1_media_plan.campaign.audience_age_end == 34
        assert len(v1_media_plan.lineitems) == 2
        assert v1_media_plan.lineitems[0].cost_total == Decimal("30000")
        assert v1_media_plan.lineitems[0].channel == "social"
        assert v1_media_plan.lineitems[0].vehicle == "Facebook"
        assert v1_media_plan.lineitems[1].cost_total == Decimal("40000")

    def test_add_lineitem(self):
        """Test adding a line item to a media plan."""
        media_plan = MediaPlan(
            meta=Meta(
                id="mediaplan_12345",
                schema_version="v1.0.0",
                created_by="test@example.com",
                name="Test Media Plan"
            ),
            campaign=Campaign(
                id="campaign_1",
                name="Test Campaign",
                objective="awareness",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000")
            ),
            lineitems=[]
        )

        # Add line item as object
        line_item1 = LineItem(
            id="line_item_1",
            name="Social Line Item",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            cost_total=Decimal("30000"),
            channel="social"
        )

        media_plan.add_lineitem(line_item1)

        # Add line item as dict
        line_item2_dict = {
            "id": "line_item_2",
            "name": "Display Line Item",
            "start_date": date(2025, 4, 1),
            "end_date": date(2025, 6, 30),
            "cost_total": Decimal("40000"),
            "channel": "display"
        }

        media_plan.add_lineitem(line_item2_dict)

        assert len(media_plan.lineitems) == 2
        assert media_plan.lineitems[0].id == "line_item_1"
        assert media_plan.lineitems[1].id == "line_item_2"

    def test_invalid_lineitem_dates(self):
        """Test adding a line item with invalid dates."""
        media_plan = MediaPlan(
            meta=Meta(
                id="mediaplan_12345",
                schema_version="v1.0.0",
                created_by="test@example.com",
                name="Test Media Plan"
            ),
            campaign=Campaign(
                id="campaign_1",
                name="Test Campaign",
                objective="awareness",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000")
            ),
            lineitems=[]
        )

        # Line item starts before campaign
        with pytest.raises(ValidationError):
            media_plan.add_lineitem({
                "id": "line_item_1",
                "name": "Invalid Line Item",
                "start_date": date(2024, 12, 1),  # Before campaign start
                "end_date": date(2025, 3, 31),
                "cost_total": Decimal("30000")
            })

        # Line item ends after campaign
        with pytest.raises(ValidationError):
            media_plan.add_lineitem({
                "id": "line_item_1",
                "name": "Invalid Line Item",
                "start_date": date(2025, 10, 1),
                "end_date": date(2026, 1, 31),  # After campaign end
                "cost_total": Decimal("30000")
            })

    def test_calculate_total_cost(self):
        """Test calculating total cost."""
        media_plan = MediaPlan(
            meta=Meta(
                id="mediaplan_12345",
                schema_version="v1.0.0",
                created_by="test@example.com",
                name="Test Media Plan"
            ),
            campaign=Campaign(
                id="campaign_1",
                name="Test Campaign",
                objective="awareness",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000")
            ),
            lineitems=[
                LineItem(
                    id="line_item_1",
                    name="Social Line Item",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 3, 31),
                    cost_total=Decimal("30000"),
                    channel="social"
                ),
                LineItem(
                    id="line_item_2",
                    name="Display Line Item",
                    start_date=date(2025, 4, 1),
                    end_date=date(2025, 6, 30),
                    cost_total=Decimal("40000"),
                    channel="display"
                )
            ]
        )

        total_cost = media_plan.calculate_total_cost()
        assert total_cost == Decimal("70000")

    def test_create_new(self):
        """Test creating a new media plan with v1.0.0 schema."""
        media_plan = MediaPlan.create(
            created_by="test@example.com",
            campaign_name="Summer Campaign",
            campaign_objective="awareness",
            campaign_start_date="2025-06-01",
            campaign_end_date="2025-08-31",
            campaign_budget=100000,
            mediaplan_id="mediaplan_summer_2025",  # v1.0.0 specific
            media_plan_name="Summer 2025 Campaign Plan",  # v1.0.0 specific
            comments="Summer campaign for brand launch",
            target_audience={
                "age_range": "18-34",
                "location": "United States",
                "interests": ["summer", "outdoors"]
            }
        )

        assert media_plan.meta.created_by == "test@example.com"
        assert media_plan.meta.schema_version == "v1.0.0"  # Default now v1.0.0
        assert media_plan.meta.id == "mediaplan_summer_2025"
        assert media_plan.meta.name == "Summer 2025 Campaign Plan"
        assert media_plan.campaign.name == "Summer Campaign"
        assert media_plan.campaign.start_date == date(2025, 6, 1)
        assert media_plan.campaign.budget_total == Decimal("100000")
        assert media_plan.campaign.audience_age_start == 18
        assert media_plan.campaign.audience_age_end == 34
        assert media_plan.campaign.location_type == "Country"
        assert "United States" in media_plan.campaign.locations
        assert "summer" in media_plan.campaign.audience_interests
        assert len(media_plan.lineitems) == 0

    def test_save_and_load(self):
        """Test saving and loading a media plan."""
        media_plan = MediaPlan.create(
            created_by="test@example.com",
            campaign_name="Test Campaign",
            campaign_objective="awareness",
            campaign_start_date="2025-01-01",
            campaign_end_date="2025-12-31",
            campaign_budget=100000,
            mediaplan_id="mediaplan_test",
            media_plan_name="Test Media Plan"
        )

        # Save to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            media_plan.export_to_json(tmp_path)

            # Load from the file
            loaded_plan = MediaPlan.import_from_json(tmp_path)

            # Verify data was preserved
            assert loaded_plan.meta.created_by == "test@example.com"
            assert loaded_plan.meta.id == "mediaplan_test"
            assert loaded_plan.meta.name == "Test Media Plan"
            assert loaded_plan.campaign.name == "Test Campaign"
            assert loaded_plan.campaign.start_date == date(2025, 1, 1)
            assert loaded_plan.campaign.budget_total == Decimal("100000")

        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)