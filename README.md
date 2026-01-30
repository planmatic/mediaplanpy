# MediaPlanPy v3.0.0

Open source Python SDK providing the foundational tools developers need to build, manage, and analyze media plans based on our open data standard (mediaplanschema).

**Latest Release:** v3.0.0 - [View Changelog](CHANGE_LOG.md)

## 🔗 Related Projects

MediaPlanPy is the official Python implementation of the **[MediaPlan Schema](https://github.com/planmatic/mediaplanschema)** standard. The two repositories work together:

- **[mediaplanschema](https://github.com/planmatic/mediaplanschema)** - Defines the open data standard for media plans
- **mediaplanpy** - Python SDK that fully conforms to and implements the mediaplanschema standard

MediaPlanPy handles schema validation, versioning, and migration to ensure full compliance with the MediaPlan Schema specification.

## Key Features

- **Schema v3.0 Support** - Full implementation of the latest schema with enhanced targeting, formulas, and 40 more fields
- **Multi-Format Support** - Work with JSON, Excel, and Parquet files seamlessly
- **Formula System** - Dynamic metric calculations with multiple formula types and support for dependencies
- **Schema Versioning & Migration** - Automatic version detection and v2.0 → v3.0 workspace upgrade utility
- **Flexible Storage** - Local filesystem, S3 and PostgreSQL backends
- **Workspace Management** - Multi-environment support with isolated configurations and strict version enforcement
- **Excel Integration** - Formula-aware import/export with automatic coefficient calculation
- **CLI Interface** - Comprehensive command-line tools for workspace management and operations
- **Validation Framework** - Schema-based validation with detailed error reporting
- **Analytics Ready** - Built-in Parquet generation and SQL query capabilities
- **Database Integration** - Automatic PostgreSQL synchronization for analytics with enhanced schema migration

## Documentation

- **[GET_STARTED.md](GET_STARTED.md)** - Detailed setup and first steps guide
- **[SDK_REFERENCE.md](SDK_REFERENCE.md)** - Complete API reference and usage examples
- **[CHANGE_LOG.md](CHANGE_LOG.md)** - Version history and release notes
- **[examples/](examples/)** - Comprehensive examples library demonstrating all key SDK functionality

## Schema Compliance & Version Support

MediaPlanPy fully implements the [MediaPlan Schema](https://github.com/planmatic/mediaplanschema) standard:

- **Schema v3.0** - Full support for current production specification with target audiences/locations arrays, metric formulas, and 40 more fields
- **Validation** - Comprehensive schema validation with detailed error reporting
- **Extensibility** - Support for custom fields, dimensions, and properties at meta, campaign, and lineitem levels

### Important Version Notes

**SDK v3.0.x** (Current):
- ✅ **Only supports** workspaces using **schema v3.0**
- ✅ Provides CLI-based migration utility to upgrade v2.0 workspaces to v3.0
- ✅ Automatic backups before migration
- ⚠️ **Cannot load** v2.0 workspaces directly - migration required

**SDK v2.0.7** (Previous):
- ✅ Continue using this version to work with existing v2.0 workspaces
- ⚠️ Does not support v3.0 schema features

**Migration Path**: Use the CLI command `mediaplanpy workspace upgrade` to migrate v2.0 workspaces to v3.0. See [GET_STARTED.md](GET_STARTED.md) for details.

## Requirements

- **Python**: 3.8 or higher
- **Core Dependencies**:
  - `pydantic>=1.10.0` - Data validation
  - `pandas>=1.5.0` - Data manipulation
- **Optional Dependencies**:
  - `openpyxl>=3.0.0` - Excel support
  - `psycopg2-binary>=2.9.0` - PostgreSQL integration
  - `pyarrow>=10.0.0` - Parquet support
  - `duckdb>=0.8.0` - Advanced analytics

## 🏷️ Version Information

- **SDK Version**: 3.0.0
- **Schema Version**: 3.0 (v2.0 migration utility included)
- **Python Support**: 3.8, 3.9, 3.10, 3.11, 3.12

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Contact & Support

For questions, support, or to learn more about commercial offerings:
- Visit our [website](https://www.planmatic.io)
- Follow us on [LinkedIn](https://www.linkedin.com/company/planmatic)
- Email us at [contact@planmatic.io](mailto:contact@planmatic.io)
