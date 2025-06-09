"""
Testing guide and examples for the updated Schema Validator with v2.0 support.

This file provides examples of how to test the enhanced validation functionality.
"""

import json
from mediaplanpy.schema import SchemaValidator
from mediaplanpy.models import MediaPlan
from datetime import datetime

def test_v2_schema_validation():
    """Test basic v2.0 schema validation."""

    # Create a SchemaValidator instance
    validator = SchemaValidator()

    # Test 1: Valid v2.0 media plan
    valid_v2_plan = {
        "meta": {
            "id": "test_plan_v2",
            "schema_version": "2.0",
            "created_by_name": "Test User",  # Required in v2.0
            "created_by_id": "user123",      # Optional in v2.0
            "created_at": datetime.now().isoformat(),
            "is_current": True,
            "is_archived": False
        },
        "campaign": {
            "id": "campaign_123",
            "name": "Test Campaign v2.0",
            "objective": "awareness",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "budget_total": 100000,
            "budget_currency": "USD",           # New in v2.0
            "agency_id": "agency_123",          # New in v2.0
            "agency_name": "Test Agency",       # New in v2.0
            "campaign_type_id": "brand_awareness", # New in v2.0
            "campaign_type_name": "Brand Awareness" # New in v2.0
        },
        "lineitems": [
            {
                "id": "lineitem_1",
                "name": "Test Line Item",
                "start_date": "2024-01-01",
                "end_date": "2024-06-30",
                "cost_total": 50000,
                "cost_currency": "USD",         # New in v2.0
                "dayparts": "Primetime",        # New in v2.0
                "inventory": "Premium",         # New in v2.0
                "metric_impressions": 1000000,
                "metric_engagements": 10000,    # New v2.0 metric
                "metric_visits": 5000           # New v2.0 metric
            }
        ],
        "dictionary": {                         # New in v2.0
            "custom_dimensions": {
                "dim_custom1": {
                    "status": "enabled",
                    "caption": "Custom Dimension 1"
                }
            },
            "custom_metrics": {
                "metric_custom1": {
                    "status": "enabled",
                    "caption": "Custom Metric 1"
                }
            }
        }
    }

    # Validate the plan
    errors = validator.validate(valid_v2_plan, "2.0")
    print(f"Valid v2.0 plan validation errors: {len(errors)}")
    if errors:
        for error in errors:
            print(f"  - {error}")

    # Test 2: Test comprehensive validation
    comprehensive_result = validator.validate_comprehensive(valid_v2_plan, "2.0")
    print(f"\nComprehensive validation results:")
    print(f"  Errors: {len(comprehensive_result['errors'])}")
    print(f"  Warnings: {len(comprehensive_result['warnings'])}")
    print(f"  Info: {len(comprehensive_result['info'])}")

    return errors == []

def test_v2_dictionary_validation():
    """Test v2.0 dictionary validation specifically."""

    validator = SchemaValidator()

    # Test invalid dictionary configuration
    invalid_dict_plan = {
        "meta": {
            "id": "test_dict_invalid",
            "schema_version": "2.0",
            "created_by_name": "Test User",
            "created_at": datetime.now().isoformat()
        },
        "campaign": {
            "id": "campaign_123",
            "name": "Test Campaign",
            "objective": "awareness",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "budget_total": 100000
        },
        "lineitems": [],
        "dictionary": {
            "custom_dimensions": {
                "invalid_field": {           # Invalid field name
                    "status": "enabled",
                    "caption": "Invalid"
                },
                "dim_custom1": {
                    "status": "enabled"      # Missing caption when enabled
                },
                "dim_custom2": {
                    "status": "invalid_status", # Invalid status
                    "caption": "Test"
                }
            }
        }
    }

    errors = validator.validate(invalid_dict_plan, "2.0")
    print(f"\nDictionary validation test - found {len(errors)} errors:")
    for error in errors:
        print(f"  - {error}")

    return len(errors) > 0  # Should have errors

def test_v2_field_consistency():
    """Test v2.0 field consistency validation."""

    validator = SchemaValidator()

    # Test plan with consistency issues
    inconsistent_plan = {
        "meta": {
            "id": "test_consistency",
            "schema_version": "2.0",
            "created_by_name": "Test User",
            "created_at": datetime.now().isoformat(),
            "is_current": True,
            "is_archived": True,        # Conflicting with is_current
            "parent_id": "test_consistency" # Self-reference
        },
        "campaign": {
            "id": "campaign_123",
            "name": "Test Campaign",
            "objective": "awareness",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "budget_total": 100000,
            "agency_id": "agency_123",  # ID without name
            "advertiser_name": "Test Advertiser" # Name without ID
        },
        "lineitems": [
            {
                "id": "lineitem_1",
                "name": "Test Line Item",
                "start_date": "2024-01-01",
                "end_date": "2024-06-30",
                "cost_total": 50000,
                "cost_currency": "INVALID",     # Invalid currency code
                "metric_application_start": 100,
                "metric_application_complete": 200  # More completions than starts
            }
        ]
    }

    errors = validator.validate(inconsistent_plan, "2.0")
    print(f"\nField consistency test - found {len(errors)} errors:")
    for error in errors:
        print(f"  - {error}")

    return len(errors) > 0  # Should have errors

def test_backwards_compatibility():
    """Test that validator still works with v1.0 plans."""

    validator = SchemaValidator()

    # Valid v1.0 plan
    v1_plan = {
        "meta": {
            "id": "test_v1_plan",
            "schema_version": "1.0",
            "created_by": "Test User",    # v1.0 uses created_by (optional)
            "created_at": datetime.now().isoformat()
        },
        "campaign": {
            "id": "campaign_123",
            "name": "Test Campaign v1.0",
            "objective": "awareness",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "budget_total": 100000
        },
        "lineitems": [
            {
                "id": "lineitem_1",
                "name": "Test Line Item",
                "start_date": "2024-01-01",
                "end_date": "2024-06-30",
                "cost_total": 50000,
                "metric_impressions": 1000000
            }
        ]
    }

    errors = validator.validate(v1_plan, "1.0")
    print(f"\nBackwards compatibility test (v1.0) - found {len(errors)} errors:")
    for error in errors:
        print(f"  - {error}")

    return len(errors) == 0  # Should have no errors

def test_model_integration():
    """Test integration with MediaPlan model validation."""

    # Create a MediaPlan using the model
    try:
        media_plan = MediaPlan.create(
            created_by="Test User",
            campaign_name="Model Integration Test",
            campaign_objective="awareness",
            campaign_start_date="2024-01-01",
            campaign_end_date="2024-12-31",
            campaign_budget=100000,
            schema_version="v2.0"
        )

        # Test model validation
        model_errors = media_plan.validate_model()
        print(f"\nModel integration test - model validation errors: {len(model_errors)}")

        # Test schema validation through model
        schema_errors = media_plan.validate_against_schema()
        print(f"Model integration test - schema validation errors: {len(schema_errors)}")

        # Test comprehensive validation through model
        comprehensive = media_plan.validate_comprehensive()
        print(f"Model integration test - comprehensive validation:")
        print(f"  Errors: {len(comprehensive['errors'])}")
        print(f"  Warnings: {len(comprehensive['warnings'])}")
        print(f"  Info: {len(comprehensive['info'])}")

        return len(schema_errors) == 0

    except Exception as e:
        print(f"Model integration test failed: {e}")
        return False

def run_all_tests():
    """Run all validation tests."""

    print("=" * 60)
    print("SCHEMA VALIDATOR v2.0 TESTING")
    print("=" * 60)

    tests = [
        ("Basic v2.0 Validation", test_v2_schema_validation),
        ("Dictionary Validation", test_v2_dictionary_validation),
        ("Field Consistency", test_v2_field_consistency),
        ("Backwards Compatibility", test_backwards_compatibility),
        ("Model Integration", test_model_integration)
    ]

    results = {}
    for test_name, test_func in tests:
        print(f"\n{'-' * 40}")
        print(f"Running: {test_name}")
        print(f"{'-' * 40}")

        try:
            result = test_func()
            results[test_name] = result
            status = "PASS" if result else "FAIL"
            print(f"Result: {status}")
        except Exception as e:
            print(f"Test failed with exception: {e}")
            results[test_name] = False

    # Summary
    print(f"\n{'=' * 60}")
    print("TEST SUMMARY")
    print(f"{'=' * 60}")

    passed = 0
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test_name:<30} {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{len(tests)} tests passed")

    return passed == len(tests)

if __name__ == "__main__":
    run_all_tests()