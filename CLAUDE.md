# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing
- Run all tests: `pytest`
- Run specific test file: `pytest tests/test_models.py`
- Run with coverage: `pytest --cov=mediaplanpy`

### Code Quality
- Format code: `black src/ tests/`
- Sort imports: `isort src/ tests/`
- Type checking: `mypy src/mediaplanpy`
- Install dev dependencies: `pip install -e ".[dev]"`

### Build & Install
- Install package in development mode: `pip install -e .`
- Build package: `python -m build`

### CLI Usage
- Access CLI: `mediaplanpy --help`
- The CLI entry point is in `src/mediaplanpy/cli.py`

## Architecture Overview

MediaPlanPy is a Python SDK for working with media plans that follow the MediaPlan Schema standard. The codebase is organized into several key modules:

### Core Components

**Models (`src/mediaplanpy/models/`)**
- `MediaPlan`: Main model representing a complete media plan with campaigns and line items
- `Campaign`: Represents a campaign with budget and target audience information
- `LineItem`: Individual line items within campaigns with metrics and cost data
- `TargetAudience`: New v3.0 model for audience arrays with 13+ attributes
- `TargetLocation`: New v3.0 model for location arrays with multiple targeting options
- `MetricFormula`: New v3.0 model for calculated metric formulas
- All models inherit from `BaseModel` and use Pydantic for validation
- Models support schema v3.0 with v2.0 migration capability

**Schema Management (`src/mediaplanpy/schema/`)**
- Version-aware schema validation and migration system
- Supports schema version 3.0 with v2.0 migration support (v0.0 and v1.0 no longer supported)
- `SchemaValidator`: Validates media plans against schemas
- `SchemaMigrator`: Migrates v2.0 → v3.0 with automatic audience/location restructuring
- `SchemaRegistry`: Manages schema definitions stored in `definitions/` subdirectories

**Storage (`src/mediaplanpy/storage/`)**
- Pluggable storage backends: Local filesystem, S3, Google Drive, PostgreSQL
- Format handlers for JSON, Excel, and Parquet files
- `read_mediaplan()` and `write_mediaplan()` are the main entry points
- Storage configuration is managed through workspace settings

**Workspace Management (`src/mediaplanpy/workspace/`)**
- Multi-environment configuration system
- Workspace configurations define storage locations and database connections
- Query functionality across multiple media plans within a workspace
- Workspace validation against JSON schemas

**Excel Integration (`src/mediaplanpy/excel/`)**
- Import/export functionality for Excel files
- Template-based Excel generation
- Excel validation against schema requirements
- Custom formatting and style handling

### Key Patterns

**Schema Versioning**
- The system supports schema version 3.0 as current, with v2.0 migration support
- Version detection is automatic from media plan metadata
- v2.0 → v3.0 migration handles audience/location restructuring and new field additions
- v0.0 and v1.0 are no longer supported

**Database Integration**
- PostgreSQL integration is optional (requires `psycopg2-binary`)
- Database functionality is patched into MediaPlan models when available
- Use `is_database_available()` to check if database features are accessible

**Error Handling**
- Custom exception hierarchy in `exceptions.py`
- All exceptions inherit from `MediaPlanError`
- Specific exceptions for schema, storage, validation, and workspace errors

## Configuration

**Version Information**
- Current SDK version: 3.0.0
- Current schema version: 3.0
- Supported major versions: [2, 3]

**Dependencies**
- Core: pydantic, pandas, jsonschema
- Optional: openpyxl (Excel), psycopg2-binary (PostgreSQL), pyarrow (Parquet), boto3 (S3)
- All dependencies are listed in `pyproject.toml`

## Testing Notes

- Tests are in `tests/` directory using pytest
- Test files follow `test_*.py` naming convention
- Tests cover models, schema validation, storage backends, Excel functionality, and workspace management
- Use `pytest tests/test_specific.py::TestClass::test_method` to run individual tests