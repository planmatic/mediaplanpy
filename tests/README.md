# MediaPlanPy Test Suite

This directory contains the complete test suite for MediaPlanPy SDK v3.0.

## Quick Start

### Run All Tests
```bash
# From project root
pytest tests/ -v

# With coverage report
pytest tests/ --cov=mediaplanpy --cov-report=html
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/test_*.py -v

# Integration tests only
pytest tests/integration/ -v

# End-to-end tests only
pytest tests/e2e/ -v
```

### Run Individual Test Files
```bash
# Specific test file
pytest tests/test_models.py -v

# Specific test class
pytest tests/test_models.py::TestMediaPlan -v

# Specific test method
pytest tests/test_models.py::TestMediaPlan::test_create_minimal_v3_plan -v
```

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures for all tests
├── test_*.py                # Unit tests (models, schema, storage, etc.)
├── integration/             # Integration tests
│   ├── __init__.py
│   ├── conftest.py          # Integration-specific fixtures
│   ├── test_database.py     # Database integration (placeholder)
│   └── test_query.py        # Workspace query integration
└── e2e/                     # End-to-end tests
    ├── __init__.py
    ├── conftest.py          # E2E-specific fixtures
    ├── test_cli.py          # CLI command testing
    └── test_workflows.py    # Multi-component workflows
```

### Test Categories

**Unit Tests** (`test_*.py`)
- Test individual components in isolation
- Models, schema validation, storage backends, Excel functionality
- Fast execution, no external dependencies

**Integration Tests** (`integration/`)
- Test component interactions
- Workspace queries across multiple media plans
- Database integration (when configured)

**End-to-End Tests** (`e2e/`)
- Test complete workflows
- CLI commands with subprocess calls
- Multi-format persistence scenarios

## Test Fixtures

### Global Fixtures (`conftest.py`)

**`temp_dir`** - Temporary directory for test files
```python
def test_my_feature(temp_dir):
    file_path = os.path.join(temp_dir, "test.json")
    # Directory is automatically cleaned up after test
```

**`mediaplan_v3_minimal`** - Minimal v3.0 media plan
```python
def test_with_minimal_plan(mediaplan_v3_minimal):
    assert mediaplan_v3_minimal.schema_version == "3.0"
    assert len(mediaplan_v3_minimal.campaigns) == 1
```

**`mediaplan_v3_full`** - Complete v3.0 media plan with all features
```python
def test_with_full_plan(mediaplan_v3_full):
    campaign = mediaplan_v3_full.campaigns[0]
    assert campaign.target_audiences is not None
    assert campaign.target_locations is not None
```

**`mediaplan_v2_sample`** - v2.0 media plan for migration testing
```python
def test_migration(mediaplan_v2_sample):
    assert mediaplan_v2_sample.schema_version == "2.0"
```

### Integration Fixtures (`integration/conftest.py`)

**`temp_workspace_with_v3_plans`** - Workspace with test media plans
```python
def test_query_workspace(temp_workspace_with_v3_plans):
    workspace = WorkspaceManager(workspace_path=temp_workspace_with_v3_plans)
    workspace.load()
    campaigns = workspace.list_campaigns()
```

## Database Tests

### Current Status
Database tests in `integration/test_database.py` are **placeholder tests** that skip automatically unless a PostgreSQL test database is configured.

### Expected Behavior
```bash
pytest tests/integration/test_database.py -v

# Output:
# - 2 PASSED: Infrastructure tests (availability check)
# - 12 SKIPPED: Integration tests (require database)
```

### To Enable Database Tests (Optional)
Only needed if actively developing PostgreSQL integration:

1. **Set up test database**
   ```bash
   # Create PostgreSQL test database
   createdb mediaplan_test
   ```

2. **Configure environment variables**
   ```bash
   export MEDIAPLAN_DB_HOST=localhost
   export MEDIAPLAN_DB_PORT=5432
   export MEDIAPLAN_DB_NAME=mediaplan_test
   export MEDIAPLAN_DB_USER=your_user
   export MEDIAPLAN_DB_PASSWORD=your_password
   ```

3. **Implement test logic**
   - Current tests call `pytest.skip()` after checking env vars
   - Replace skip calls with actual database operations

## Platform-Specific Notes

### Windows
CLI tests use subprocess calls that require UTF-8 encoding for Unicode characters (emojis in output):

```python
env = os.environ.copy()
env['PYTHONIOENCODING'] = 'utf-8'
result = subprocess.run(["mediaplanpy", "..."], env=env)
```

This is already configured in the test suite.

### Working Directory
CLI tests use `cwd` parameter to ensure workspace files are found:

```python
result = subprocess.run(
    ["mediaplanpy", "workspace", "settings", "--workspace_id", workspace_id],
    cwd=temp_dir  # Run CLI in temp directory
)
```

## Coverage Reporting

### Generate Coverage Report
```bash
# HTML report (opens in browser)
pytest tests/ --cov=mediaplanpy --cov-report=html
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows

# Terminal report
pytest tests/ --cov=mediaplanpy --cov-report=term-missing

# Multiple formats
pytest tests/ --cov=mediaplanpy --cov-report=html --cov-report=term
```

### Expected Coverage
- **Target**: >90% coverage for core modules
- **Models**: ~95% (well-tested with fixtures)
- **Schema**: ~90% (validation and migration)
- **Storage**: ~85% (multiple backends)
- **Workspace**: ~90% (query functionality)

## Common Test Commands

```bash
# Run tests with verbose output
pytest tests/ -v

# Run tests and stop at first failure
pytest tests/ -x

# Run tests matching pattern
pytest tests/ -k "test_campaign"

# Run with print statements visible
pytest tests/ -s

# Run in parallel (requires pytest-xdist)
pytest tests/ -n auto

# Show slowest tests
pytest tests/ --durations=10

# Run only failed tests from last run
pytest tests/ --lf

# Run failed tests first, then all
pytest tests/ --ff
```

## Test Development Guidelines

### Writing New Tests

1. **Use appropriate fixtures**
   ```python
   def test_new_feature(temp_dir, mediaplan_v3_minimal):
       # temp_dir for file operations
       # mediaplan_v3_minimal for media plan data
       pass
   ```

2. **Follow naming conventions**
   - Test files: `test_*.py`
   - Test classes: `TestClassName`
   - Test methods: `test_method_name`

3. **Use descriptive names**
   ```python
   def test_save_v3_plan_with_target_audiences_to_json():
       """Test saving v3.0 plan with target_audiences to JSON format."""
       pass
   ```

4. **Organize with test classes**
   ```python
   class TestCampaignV3Features:
       """Test v3.0 campaign features."""

       def test_target_audiences(self):
           pass

       def test_target_locations(self):
           pass
   ```

### Testing Best Practices

- **Isolation**: Each test should be independent
- **Cleanup**: Use fixtures with cleanup (temp_dir handles this)
- **Assertions**: Clear, specific assertion messages
- **Edge cases**: Test boundary conditions and error cases
- **Parametrize**: Use `@pytest.mark.parametrize` for similar tests

```python
@pytest.mark.parametrize("schema_version", ["2.0", "3.0"])
def test_load_plan(schema_version, temp_dir):
    # Test runs twice, once for each version
    pass
```

## Continuous Integration

### Running Tests in CI
```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install -e ".[dev]"
    pytest tests/ --cov=mediaplanpy --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

## Troubleshooting

### Tests Fail on Windows
- Ensure `PYTHONIOENCODING=utf-8` is set for CLI tests
- Check file path separators (use `os.path.join()`)

### Import Errors
```bash
# Install package in development mode
pip install -e .

# Install test dependencies
pip install -e ".[dev]"
```

### Fixture Not Found
- Check `conftest.py` files in test directory hierarchy
- Ensure fixture is defined before being used

### Database Tests Always Skip
- This is expected behavior (placeholder tests)
- Only run with PostgreSQL configured (optional)

### CLI Tests Take Long Time
- CLI tests spawn subprocesses (slower than unit tests)
- Run CLI tests separately when needed:
  ```bash
  pytest tests/e2e/test_cli.py -v
  ```

## Test Statistics

**Total Tests**: ~154
- Unit tests: ~120
- Integration tests: ~20 (14 active, 12 database placeholders)
- E2E tests: ~34

**Execution Time** (approximate):
- Unit tests: ~5-10 seconds
- Integration tests: ~2-3 seconds
- E2E tests (CLI): ~15-20 seconds
- **Total**: ~25-35 seconds

## Version-Specific Testing

### v3.0 Features Tested
- ✅ Target audiences (campaign-level)
- ✅ Target locations (campaign-level)
- ✅ New metrics (view_starts, reach, conversions)
- ✅ Metric formulas (custom calculations)
- ✅ Schema validation (3.0 schemas)
- ✅ Migration (2.0 → 3.0)
- ✅ Storage (JSON, Parquet, Excel with v3.0 data)
- ✅ Workspace queries (list_campaigns, list_mediaplans, sql_query)
- ✅ CLI commands (all workspace and list commands)

### Backwards Compatibility
- ✅ v2.0 media plans load correctly
- ✅ v2.0 → v3.0 migration tested
- ✅ Schema version detection
- ✅ Version enforcement in workspaces

## Questions?

For issues or questions about testing:
1. Check CLAUDE.md in project root for development commands
2. Review SDK_REFERENCE.md for API documentation
3. See examples/ directory for usage patterns
