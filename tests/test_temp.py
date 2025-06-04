# Testing recommendations for Phase 5.3 Excel integration updates

# Test Case 1: Excel export with current version media plan
def test_excel_export_current_version():
    """Test that Excel export works with v1.0 media plan."""
    media_plan = {
        "meta": {"schema_version": "1.0", "id": "test", "created_by": "test"},
        "campaign": {"id": "camp1", "name": "Test Campaign", "objective": "Test",
                     "start_date": "2025-01-01", "end_date": "2025-12-31", "budget_total": 10000},
        "lineitems": []
    }
    # Should succeed without errors
    path = export_to_excel(media_plan)
    assert path.endswith('.xlsx')


# Test Case 2: Excel export with legacy version format (should normalize)
def test_excel_export_legacy_version_format():
    """Test that Excel export normalizes v1.0.0 to 1.0."""
    media_plan = {
        "meta": {"schema_version": "v1.0.0", "id": "test", "created_by": "test"},
        # ... rest of media plan
    }
    # Should normalize version and succeed
    path = export_to_excel(media_plan)

    # Verify the exported file uses "1.0" format
    imported_plan = import_from_excel(path)
    assert imported_plan["meta"]["schema_version"] == "1.0"


# Test Case 3: Excel export with unsupported version (should fail)
def test_excel_export_unsupported_version():
    """Test that Excel export rejects unsupported versions."""
    media_plan = {
        "meta": {"schema_version": "0.0", "id": "test", "created_by": "test"},
        # ... rest of media plan
    }
    # Should raise StorageError
    with pytest.raises(StorageError) as exc_info:
        export_to_excel(media_plan)

    assert "Excel export only supports current schema version 1.0" in str(exc_info.value)


# Test Case 4: Excel import with current version file
def test_excel_import_current_version():
    """Test that Excel import works with v1.0 Excel files."""
    # Create a test Excel file with "1.0" in metadata
    # Should succeed without errors
    media_plan = import_from_excel("test_v1_0.xlsx")
    assert media_plan["meta"]["schema_version"] == "1.0"


# Test Case 5: Excel import with legacy version file (should fail)
def test_excel_import_legacy_version():
    """Test that Excel import rejects v0.0.0 files."""
    # Create a test Excel file with v0.0.0 structure
    # Should raise ValidationError
    with pytest.raises(ValidationError) as exc_info:
        import_from_excel("test_v0_0_0.xlsx")

    assert "Excel import only supports schema version 1.0" in str(exc_info.value)


# Test Case 6: Excel validation with current version
def test_excel_validation_current_version():
    """Test that Excel validation passes for v1.0 files."""
    errors = validate_excel("test_v1_0.xlsx")
    assert len(errors) == 0


# Test Case 7: Excel validation with unsupported version
def test_excel_validation_unsupported_version():
    """Test that Excel validation fails for unsupported versions."""
    errors = validate_excel("test_unsupported.xlsx")
    assert len(errors) > 0
    assert any("unsupported schema version" in error.lower() for error in errors)


# Test Case 8: Round-trip consistency
def test_excel_roundtrip_consistency():
    """Test that export->import maintains data integrity."""
    original_plan = {
        "meta": {"schema_version": "1.0", "id": "test", "created_by": "test"},
        "campaign": {"id": "camp1", "name": "Test Campaign", "objective": "Test",
                     "start_date": "2025-01-01", "end_date": "2025-12-31", "budget_total": 10000},
        "lineitems": [
            {"id": "li1", "name": "Line Item 1", "start_date": "2025-01-01",
             "end_date": "2025-01-31", "cost_total": 5000}
        ]
    }

    # Export to Excel
    excel_path = export_to_excel(original_plan)

    # Import back from Excel
    imported_plan = import_from_excel(excel_path)

    # Verify key data is preserved
    assert imported_plan["meta"]["schema_version"] == "1.0"
    assert imported_plan["campaign"]["id"] == original_plan["campaign"]["id"]
    assert len(imported_plan["lineitems"]) == len(original_plan["lineitems"])
    assert imported_plan["lineitems"][0]["id"] == original_plan["lineitems"][0]["id"]