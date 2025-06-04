# Test the new version utilities
from mediaplanpy.schema.version_utils import *

# Test version parsing
assert get_major("2.0") == 2
assert get_minor("2.0") == 0
assert get_major("v1.0.0") == 1  # Backward compatibility

# Test compatibility checks
assert is_backwards_compatible("1.0") == True
assert is_forward_minor("1.1") == True
assert is_unsupported("0.0") == False  # Should be supported but deprecated
assert is_unsupported("3.0") == True   # Future version

# Test migration recommendations
rec = get_migration_recommendation("0.0")
assert rec["can_import"] == True
assert rec["action"] == "migrate"

# Test schema loading with new format
from mediaplanpy.schema import SchemaManager

manager = SchemaManager()

# Test loading schemas with new format
schema_1_0 = manager.get_schema("mediaplan", "1.0")
schema_0_0 = manager.get_schema("mediaplan", "0.0")

# Test backward compatibility with old format
schema_old = manager.get_schema("mediaplan", "v1.0.0")  # Should work

# Test version listing
versions = manager.get_supported_versions()
assert "1.0" in versions
assert "0.0" in versions

# Test registry functions
from mediaplanpy.schema import get_current_version, get_supported_versions

assert get_current_version() == "1.0"
assert "1.0" in get_supported_versions()
assert "0.0" in get_supported_versions()
assert "2.0" not in get_supported_versions()