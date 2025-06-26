# MediaPlanPy

Open source Python SDK providing the foundational tools developers need to build, manage, and analyze media plans based on our open data standard (mediaplanschema).

## 🔗 Related Projects

MediaPlanPy is the official Python implementation of the **[MediaPlan Schema](https://github.com/planmatic/mediaplanschema)** standard. The two repositories work together:

- **[mediaplanschema](https://github.com/planmatic/mediaplanschema)** - Defines the open data standard for media plans
- **mediaplanpy** - Python SDK that fully conforms to and implements the mediaplanschema standard

MediaPlanPy handles schema validation, versioning, and migration to ensure full compliance with the MediaPlan Schema specification.

## Key Features

- **Multi-Format Support** - Work with JSON, Excel, and Parquet files seamlessly
- **Schema Versioning** - Automatic version detection and migration between schema versions
- **Flexible Storage** - Local filesystem, S3, Google Drive, and PostgreSQL backends
- **Workspace Management** - Multi-environment support with isolated configurations
- **CLI Interface** - Comprehensive command-line tools for all operations
- **Validation Framework** - Schema-based validation with detailed error reporting
- **Analytics Ready** - Built-in Parquet generation and SQL query capabilities
- **Database Integration** - Automatic PostgreSQL synchronization for analytics

## Documentation

- **[GET_STARTED.md](GET_STARTED.md)** - Detailed setup and first steps guide

## Schema Compliance

MediaPlanPy fully implements the [MediaPlan Schema](https://github.com/planmatic/mediaplanschema) standard:

- **Schema v2.0** - Full support for current specification
- **Schema v1.0** - Legacy support with automatic migration
- **Validation** - Comprehensive schema validation
- **Migration** - Automatic version upgrades
- **Extensibility** - Support for custom fields and dimensions

## Requirements

- **Python**: 3.7 or higher
- **Core Dependencies**: 
  - `pydantic>=1.10.0` - Data validation
  - `pandas>=1.5.0` - Data manipulation
- **Optional Dependencies**:
  - `openpyxl>=3.0.0` - Excel support
  - `psycopg2-binary>=2.9.0` - PostgreSQL integration
  - `pyarrow>=10.0.0` - Parquet support
  - `duckdb>=0.8.0` - Advanced analytics

## Roadmap

- **Cloud Storage Backends** - AWS S3 and Google Drive integration
- **Google Sheets** - Ability to Export to / Import from Google Sheets
- **Schema v3.0** - Next generation schema support

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/planmatic/mediaplanpy/issues)
- **Discussions**: [GitHub Discussions](https://github.com/planmatic/mediaplanpy/discussions)
- **Documentation**: [Wiki](https://github.com/planmatic/mediaplanpy/wiki)

## 🏷️ Version Information

- **SDK Version**: 2.0.0
- **Schema Version**: 2.0 (backwards compatible with 1.0)
- **Python Support**: 3.7, 3.8, 3.9, 3.10, 3.11, 3.12
