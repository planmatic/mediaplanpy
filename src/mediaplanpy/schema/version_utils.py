"""
Version utility functions for mediaplanpy schema version handling.

This module provides utilities for comparing, validating, and determining
compatibility between different schema versions using the new 2-digit format.
Updated for SDK v2.0 with v0.0 support completely removed.
"""

import re
import logging
from typing import Tuple, Optional
from mediaplanpy.exceptions import SchemaVersionError

logger = logging.getLogger("mediaplanpy.schema.version_utils")

# Import version constants from main module - Updated for v2.0
try:
    from mediaplanpy import CURRENT_MAJOR, CURRENT_MINOR, SUPPORTED_MAJOR_VERSIONS
except ImportError:
    # Fallback values if importing from main module fails - Updated for v2.0
    CURRENT_MAJOR = 2
    CURRENT_MINOR = 0
    SUPPORTED_MAJOR_VERSIONS = [1, 2]  # v0.0 no longer supported


def parse_version(version: str) -> Tuple[int, int]:
    """
    Parse a schema version string into major and minor components.

    Supports both old format (v1.0.0) and new format (1.0).
    IMPORTANT: v0.0 versions are no longer supported and will raise an error.

    Args:
        version: Version string to parse (e.g., "2.0", "1.0", "v1.0.0")

    Returns:
        Tuple of (major, minor) version numbers

    Raises:
        SchemaVersionError: If version format is invalid or v0.0 is detected
    """
    if not version:
        raise SchemaVersionError("Version string cannot be empty")

    # Remove 'v' prefix if present (old format compatibility)
    cleaned_version = version.lstrip('v')

    # Split by dots
    parts = cleaned_version.split('.')

    if len(parts) < 2:
        raise SchemaVersionError(f"Invalid version format: {version}. Expected format: 'X.Y' or 'vX.Y.Z'")

    try:
        major = int(parts[0])
        minor = int(parts[1])

        # CRITICAL: Reject v0.0 versions completely
        if major == 0:
            raise SchemaVersionError(
                f"Schema version {version} (v0.0.x) is no longer supported in SDK v2.0. "
                f"Please use SDK v1.x to migrate v0.0 plans to v1.0 first, then upgrade to SDK v2.0."
            )

        # Ignore patch version if present (backwards compatibility)
        return (major, minor)
    except ValueError:
        raise SchemaVersionError(f"Invalid version format: {version}. Version components must be integers")


def get_major(version: str) -> int:
    """
    Extract major version number from version string.

    Args:
        version: Version string (e.g., "2.0", "1.0")

    Returns:
        Major version number

    Raises:
        SchemaVersionError: If version is v0.0 or invalid
    """
    major, _ = parse_version(version)
    return major


def get_minor(version: str) -> int:
    """
    Extract minor version number from version string.

    Args:
        version: Version string (e.g., "2.0", "1.0")

    Returns:
        Minor version number

    Raises:
        SchemaVersionError: If version is v0.0 or invalid
    """
    _, minor = parse_version(version)
    return minor


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings.

    Args:
        v1: First version string
        v2: Second version string

    Returns:
        -1 if v1 < v2
         0 if v1 == v2
         1 if v1 > v2

    Raises:
        SchemaVersionError: If either version is v0.0 or invalid
    """
    major1, minor1 = parse_version(v1)
    major2, minor2 = parse_version(v2)

    if major1 < major2:
        return -1
    elif major1 > major2:
        return 1
    else:
        # Major versions are equal, compare minor
        if minor1 < minor2:
            return -1
        elif minor1 > minor2:
            return 1
        else:
            return 0


def is_backwards_compatible(version: str) -> bool:
    """
    Check if a schema version is backwards compatible with current SDK.

    A version is backwards compatible if:
    - It's the same major version but older or equal minor version
    - It's from a supported major version (within SUPPORTED_MAJOR_VERSIONS)
    - It's NOT v0.0 (completely unsupported)

    Args:
        version: Schema version to check

    Returns:
        True if version is backwards compatible, False otherwise
    """
    try:
        major, minor = parse_version(version)
    except SchemaVersionError:
        return False

    # v0.0 is never backwards compatible (handled by parse_version rejection)
    # This check is redundant but kept for clarity
    if major == 0:
        return False

    # Check if major version is supported
    if major not in SUPPORTED_MAJOR_VERSIONS:
        return False

    # If it's an older major version, it's backwards compatible
    if major < CURRENT_MAJOR:
        return True

    # If it's the same major version, check minor version
    if major == CURRENT_MAJOR and minor <= CURRENT_MINOR:
        return True

    return False


def is_forward_minor(version: str) -> bool:
    """
    Check if a schema version is a forward-compatible minor version.

    A version is forward minor compatible if:
    - It's the same major version but newer minor version
    - It's NOT v0.0 (completely unsupported)

    Args:
        version: Schema version to check

    Returns:
        True if version is forward minor compatible, False otherwise
    """
    try:
        major, minor = parse_version(version)
    except SchemaVersionError:
        return False

    # Must be same major version but newer minor version
    return major == CURRENT_MAJOR and minor > CURRENT_MINOR


def is_unsupported(version: str) -> bool:
    """
    Check if a schema version is unsupported by current SDK.

    A version is unsupported if:
    - It's v0.0 (completely removed in SDK v2.0)
    - It's from a major version not in SUPPORTED_MAJOR_VERSIONS
    - It's from a future major version

    Args:
        version: Schema version to check

    Returns:
        True if version is unsupported, False otherwise
    """
    try:
        major, minor = parse_version(version)
    except SchemaVersionError:
        # Invalid format or v0.0 is considered unsupported
        return True

    # v0.0 is unsupported (handled by parse_version, but explicit check for clarity)
    if major == 0:
        return True

    # Not in supported major versions
    if major not in SUPPORTED_MAJOR_VERSIONS:
        return True

    # Too new (future major version)
    if major > CURRENT_MAJOR:
        return True

    return False


def get_compatibility_type(version: str) -> str:
    """
    Determine the compatibility type for a given schema version.

    Args:
        version: Schema version to check

    Returns:
        One of: "native", "forward_minor", "backward_compatible", "deprecated", "unsupported"
    """
    # First check if it's v0.0 - always unsupported
    try:
        major, minor = parse_version(version)
        if major == 0:
            return "unsupported"
    except SchemaVersionError:
        return "unsupported"

    current_version = f"{CURRENT_MAJOR}.{CURRENT_MINOR}"

    try:
        if compare_versions(version, current_version) == 0:
            return "native"
        elif is_forward_minor(version):
            return "forward_minor"
        elif is_backwards_compatible(version):
            major, minor = parse_version(version)
            if major < CURRENT_MAJOR:
                return "deprecated"
            else:
                return "backward_compatible"
        elif is_unsupported(version):
            return "unsupported"
        else:
            return "unknown"
    except SchemaVersionError:
        return "unsupported"


def get_migration_recommendation(version: str) -> dict:
    """
    Get migration recommendation for a given schema version.

    Args:
        version: Schema version to check

    Returns:
        Dictionary with migration recommendation details
    """
    # Special handling for v0.0 versions
    try:
        major, minor = parse_version(version)
        if major == 0:
            return {
                "action": "reject",
                "message": f"Schema version {version} (v0.0.x) is no longer supported in SDK v2.0. Use SDK v1.x to migrate v0.0 plans to v1.0 first.",
                "can_import": False,
                "should_upgrade": True,
                "error": "v0.0 support completely removed in SDK v2.0"
            }
    except SchemaVersionError:
        pass

    compatibility = get_compatibility_type(version)
    current_version = f"{CURRENT_MAJOR}.{CURRENT_MINOR}"

    recommendations = {
        "native": {
            "action": "none",
            "message": f"Schema version {version} is natively supported",
            "can_import": True,
            "should_upgrade": False
        },
        "forward_minor": {
            "action": "downgrade",
            "message": f"Schema version {version} will be downgraded to {current_version} during import",
            "can_import": True,
            "should_upgrade": False,
            "warning": "Some newer fields may be preserved but inactive"
        },
        "backward_compatible": {
            "action": "upgrade",
            "message": f"Schema version {version} will be upgraded to {current_version} during import",
            "can_import": True,
            "should_upgrade": True
        },
        "deprecated": {
            "action": "migrate",
            "message": f"Schema version {version} is deprecated. Consider migrating to {current_version}",
            "can_import": True,
            "should_upgrade": True,
            "warning": f"Support for major version {get_major(version)} may be removed in future releases"
        },
        "unsupported": {
            "action": "reject",
            "message": f"Schema version {version} is not supported by SDK v{current_version}",
            "can_import": False,
            "should_upgrade": True,
            "error": "Import will fail. Upgrade SDK or use compatible schema version"
        }
    }

    return recommendations.get(compatibility, {
        "action": "unknown",
        "message": f"Cannot determine compatibility for version {version}",
        "can_import": False,
        "should_upgrade": False,
        "error": "Unknown version format or compatibility issue"
    })


def normalize_version(version: str) -> str:
    """
    Normalize a version string to the new 2-digit format.

    Args:
        version: Version string in any supported format

    Returns:
        Normalized version string in X.Y format

    Raises:
        SchemaVersionError: If version format is invalid or is v0.0
    """
    major, minor = parse_version(version)  # This will reject v0.0
    return f"{major}.{minor}"


def validate_version_format(version: str) -> bool:
    """
    Validate that a version string follows the expected format and is not v0.0.

    Args:
        version: Version string to validate

    Returns:
        True if version format is valid and not v0.0, False otherwise
    """
    try:
        parse_version(version)  # This will reject v0.0 and invalid formats
        return True
    except SchemaVersionError:
        return False