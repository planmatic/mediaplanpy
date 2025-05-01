"""
Tests for the models module.
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

    def test_create_lineitem(self):
        """Test creating a line item."""
        line_item = LineItem(
            id="line_item_1",
            channel="social",
            platform="Facebook",
            publisher="Meta",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            budget=Decimal("10000"),
            kpi="CPM",
            creative_ids=["creative_1", "creative_2"]
        )

        assert line_item.id == "line_item_1"
        assert line_item.channel == "social"
        assert line_item.platform == "Facebook"
        assert line_item.publisher == "Meta"
        assert line_item.start_date == date(2025, 1, 1)
        assert line_item.end_date == date(2025, 3, 31)
        assert line_item.budget == Decimal("10000")
        assert line_item.kpi == "CPM"
        assert line_item.creative_ids == ["creative_1", "creative_2"]

    def test_invalid_dates(self):
        """Test validation of line item with invalid dates."""
        with pytest.raises(ValueError):
            LineItem(
                id="line_item_1",
                channel="social",
                platform="Facebook",
                publisher="Meta",
                start_date=date(2025, 4, 1),  # Start after end
                end_date=date(2025, 3, 31),
                budget=Decimal("10000"),
                kpi="CPM"
            )

    def test_invalid_budget(self):
        """Test validation of line item with invalid budget."""
        with pytest.raises(ValueError):
            LineItem(
                id="line_item_1",
                channel="social",
                platform="Facebook",
                publisher="Meta",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31),
                budget=Decimal("-100"),  # Negative budget
                kpi="CPM"
            )

    def test_validation(self):
        """Test validation method."""
        # Valid line item
        line_item = LineItem(
            id="line_item_1",
            channel="social",
            platform="Facebook",
            publisher="Meta",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            budget=Decimal("10000"),
            kpi="CPM"
        )

        # Should validate without errors
        assert line_item.validate_model() == []

        # Invalid channel
        line_item = LineItem(
            id="line_item_1",
            channel="invalid_channel",  # Invalid channel
            platform="Facebook",
            publisher="Meta",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            budget=Decimal("10000"),
            kpi="CPM"
        )

        errors = line_item.validate_model()
        assert len(errors) > 0
        assert "channel" in errors[0]

    def test_to_dict(self):
        """Test conversion to dictionary."""
        line_item = LineItem(
            id="line_item_1",
            channel="social",
            platform="Facebook",
            publisher="Meta",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            budget=Decimal("10000"),
            kpi="CPM"
        )

        data = line_item.to_dict()
        assert data["id"] == "line_item_1"
        assert data["channel"] == "social"
        assert data["start_date"] == "2025-01-01"
        assert data["end_date"] == "2025-03-31"
        assert data["budget"] == 10000


class TestCampaign:
    """Tests for the Campaign model."""

    def test_create_campaign(self):
        """Test creating a campaign."""
        campaign = Campaign(
            id="campaign_1",
            name="Test Campaign",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget=Budget(
                total=Decimal("100000"),
                by_channel={
                    "social": Decimal("50000"),
                    "display": Decimal("50000")
                }
            ),
            target_audience=TargetAudience(
                age_range="18-34",
                location="United States",
                interests=["sports", "technology"]
            )
        )

        assert campaign.id == "campaign_1"
        assert campaign.name == "Test Campaign"
        assert campaign.objective == "awareness"
        assert campaign.start_date == date(2025, 1, 1)
        assert campaign.end_date == date(2025, 12, 31)
        assert campaign.budget.total == Decimal("100000")
        assert campaign.budget.by_channel["social"] == Decimal("50000")
        assert campaign.target_audience.age_range == "18-34"
        assert "sports" in campaign.target_audience.interests

    def test_invalid_dates(self):
        """Test validation of campaign with invalid dates."""
        with pytest.raises(ValueError):
            Campaign(
                id="campaign_1",
                name="Test Campaign",
                objective="awareness",
                start_date=date(2025, 12, 31),  # Start after end
                end_date=date(2025, 1, 1),
                budget=Budget(total=Decimal("100000"))
            )

    def test_budget_validation(self):
        """Test budget validation."""
        # Valid budget
        budget = Budget(
            total=Decimal("100000"),
            by_channel={
                "social": Decimal("50000"),
                "display": Decimal("50000")
            }
        )
        assert budget.validate_model() == []

        # Invalid budget (sum exceeds total)
        budget = Budget(
            total=Decimal("100000"),
            by_channel={
                "social": Decimal("60000"),
                "display": Decimal("50000")  # Total = 110000 > 100000
            }
        )
        errors = budget.validate_model()
        assert len(errors) > 0
        assert "exceeds" in errors[0]

    def test_validation(self):
        """Test validation method."""
        # Valid campaign
        campaign = Campaign(
            id="campaign_1",
            name="Test Campaign",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget=Budget(total=Decimal("100000"))
        )

        # Should validate without errors
        assert campaign.validate_model() == []

        # Invalid objective
        campaign = Campaign(
            id="campaign_1",
            name="Test Campaign",
            objective="invalid_objective",  # Invalid objective
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget=Budget(total=Decimal("100000"))
        )

        errors = campaign.validate_model()
        assert len(errors) > 0
        assert "objective" in errors[0]


class TestMediaPlan:
    """Tests for the MediaPlan model."""

    def test_create_mediaplan(self):
        """Test creating a media plan."""
        media_plan = MediaPlan(
            meta=Meta(
                schema_version="v1.0.0",
                created_by="test@example.com",
                created_at=datetime(2025, 1, 1, 12, 0, 0),
                comments="Test media plan"
            ),
            campaign=Campaign(
                id="campaign_1",
                name="Test Campaign",
                objective="awareness",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget=Budget(total=Decimal("100000"))
            ),
            lineitems=[
                LineItem(
                    id="line_item_1",
                    channel="social",
                    platform="Facebook",
                    publisher="Meta",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 3, 31),
                    budget=Decimal("30000"),
                    kpi="CPM"
                ),
                LineItem(
                    id="line_item_2",
                    channel="display",
                    platform="Google Display Network",
                    publisher="Google",
                    start_date=date(2025, 4, 1),
                    end_date=date(2025, 6, 30),
                    budget=Decimal("40000"),
                    kpi="CPC"
                )
            ]
        )

        assert media_plan.meta.schema_version == "v1.0.0"
        assert media_plan.meta.created_by == "test@example.com"
        assert media_plan.campaign.name == "Test Campaign"
        assert len(media_plan.lineitems) == 2
        assert media_plan.lineitems[0].channel == "social"
        assert media_plan.lineitems[1].channel == "display"

    def test_add_lineitem(self):
        """Test adding a line item."""
        media_plan = MediaPlan(
            meta=Meta(
                schema_version="v1.0.0",
                created_by="test@example.com"
            ),
            campaign=Campaign(
                id="campaign_1",
                name="Test Campaign",
                objective="awareness",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget=Budget(total=Decimal("100000"))
            ),
            lineitems=[]
        )

        # Add line item as object
        line_item1 = LineItem(
            id="line_item_1",
            channel="social",
            platform="Facebook",
            publisher="Meta",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            budget=Decimal("30000"),
            kpi="CPM"
        )

        media_plan.add_lineitem(line_item1)

        # Add line item as dict
        line_item2_dict = {
            "id": "line_item_2",
            "channel": "display",
            "platform": "Google Display Network",
            "publisher": "Google",
            "start_date": date(2025, 4, 1),
            "end_date": date(2025, 6, 30),
            "budget": Decimal("40000"),
            "kpi": "CPC"
        }

        media_plan.add_lineitem(line_item2_dict)

        assert len(media_plan.lineitems) == 2
        assert media_plan.lineitems[0].id == "line_item_1"
        assert media_plan.lineitems[1].id == "line_item_2"

    def test_invalid_lineitem_dates(self):
        """Test adding a line item with invalid dates."""
        media_plan = MediaPlan(
            meta=Meta(
                schema_version="v1.0.0",
                created_by="test@example.com"
            ),
            campaign=Campaign(
                id="campaign_1",
                name="Test Campaign",
                objective="awareness",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget=Budget(total=Decimal("100000"))
            ),
            lineitems=[]
        )

        # Line item starts before campaign
        with pytest.raises(ValidationError):
            media_plan.add_lineitem({
                "id": "line_item_1",
                "channel": "social",
                "platform": "Facebook",
                "publisher": "Meta",
                "start_date": date(2024, 12, 1),  # Before campaign start
                "end_date": date(2025, 3, 31),
                "budget": Decimal("30000"),
                "kpi": "CPM"
            })

        # Line item ends after campaign
        with pytest.raises(ValidationError):
            media_plan.add_lineitem({
                "id": "line_item_1",
                "channel": "social",
                "platform": "Facebook",
                "publisher": "Meta",
                "start_date": date(2025, 10, 1),
                "end_date": date(2026, 1, 31),  # After campaign end
                "budget": Decimal("30000"),
                "kpi": "CPM"
            })

    def test_calculate_total_budget(self):
        """Test calculating total budget."""
        media_plan = MediaPlan(
            meta=Meta(
                schema_version="v1.0.0",
                created_by="test@example.com"
            ),
            campaign=Campaign(
                id="campaign_1",
                name="Test Campaign",
                objective="awareness",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget=Budget(total=Decimal("100000"))
            ),
            lineitems=[
                LineItem(
                    id="line_item_1",
                    channel="social",
                    platform="Facebook",
                    publisher="Meta",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 3, 31),
                    budget=Decimal("30000"),
                    kpi="CPM"
                ),
                LineItem(
                    id="line_item_2",
                    channel="display",
                    platform="Google Display Network",
                    publisher="Google",
                    start_date=date(2025, 4, 1),
                    end_date=date(2025, 6, 30),
                    budget=Decimal("40000"),
                    kpi="CPC"
                )
            ]
        )

        total_budget = media_plan.calculate_total_budget()
        assert total_budget == Decimal("70000")

    def test_create_new(self):
        """Test creating a new media plan."""
        media_plan = MediaPlan.create_new(
            created_by="test@example.com",
            campaign_name="Summer Campaign",
            campaign_objective="awareness",
            campaign_start_date="2025-06-01",
            campaign_end_date="2025-08-31",
            campaign_budget=100000,
            comments="Summer campaign for brand launch",
            target_audience={
                "age_range": "18-34",
                "location": "United States",
                "interests": ["summer", "outdoors"]
            }
        )

        assert media_plan.meta.created_by == "test@example.com"
        assert media_plan.meta.schema_version == "v1.0.0"  # Default version
        assert media_plan.campaign.name == "Summer Campaign"
        assert media_plan.campaign.start_date == date(2025, 6, 1)
        assert media_plan.campaign.budget.total == Decimal("100000")
        assert media_plan.campaign.target_audience.age_range == "18-34"
        assert "summer" in media_plan.campaign.target_audience.interests
        assert len(media_plan.lineitems) == 0

    def test_save_and_load(self):
        """Test saving and loading a media plan."""
        media_plan = MediaPlan.create_new(
            created_by="test@example.com",
            campaign_name="Test Campaign",
            campaign_objective="awareness",
            campaign_start_date="2025-01-01",
            campaign_end_date="2025-12-31",
            campaign_budget=100000
        )

        # Save to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            media_plan.save(tmp_path)

            # Load from the file
            loaded_plan = MediaPlan.from_file(tmp_path)

            # Verify data was preserved
            assert loaded_plan.meta.created_by == "test@example.com"
            assert loaded_plan.campaign.name == "Test Campaign"
            assert loaded_plan.campaign.start_date == date(2025, 1, 1)
            assert loaded_plan.campaign.budget.total == Decimal("100000")

        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)