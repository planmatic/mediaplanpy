# Storage Module for MediaPlanPy

The Storage module in MediaPlanPy provides functionality for reading and writing media plans to various storage backends in different formats.

## Overview

The storage module is designed with the following principles:

1. **Backend Abstraction**: Different storage backends (local file system, S3, Google Drive) are supported through a common interface.
2. **Format Abstraction**: Different file formats (JSON, Parquet) are supported through a common interface.
3. **Integration with Models**: The MediaPlan model has methods for saving to and loading from storage.
4. **Workspace Configuration**: Storage settings are defined in the workspace configuration.

## Storage Backends

Currently implemented backends:

- **Local**: Stores media plans in the local file system.

Planned backends (implemented as placeholders):

- **S3**: Will store media plans in Amazon S3.
- **Google Drive**: Will store media plans in Google Drive.

## File Formats

Currently implemented formats:

- **JSON**: Stores media plans as JSON files.

Planned formats (implemented as placeholders):

- **Parquet**: Will store media plans as Parquet files for faster analytical processing.

## Usage

### Configuring Storage in Workspace

The storage configuration is defined in the workspace.json file:

```json
{
  "workspace_name": "Example Workspace",
  "storage": {
    "mode": "local",
    "local": {
      "base_path": "/path/to/storage",
      "create_if_missing": true
    }
  },
  "storage_formats": {
    "default_format": "json",
    "json": {
      "indent": 2,
      "ensure_ascii": false
    }
  }
}
```

### Using MediaPlan Storage Methods

The MediaPlan model has methods for saving to and loading from storage:

```python
from mediaplanpy import WorkspaceManager, MediaPlan

# Load workspace
manager = WorkspaceManager("path/to/workspace.json")
manager.load()

# Create a media plan
media_plan = MediaPlan.create(
    campaign_id="fall_2025_campaign",
    # other required parameters...
)

# Save to storage with automatic path generation based on campaign ID
saved_path = media_plan.save(manager)
# The media plan is saved to "fall_2025_campaign.json"

# Alternatively, specify a path
media_plan.save(manager, "campaigns/my_campaign.json")

# Load from storage using campaign ID
loaded_plan = MediaPlan.load_from_storage(manager, campaign_id="fall_2025_campaign")

# Or load from a specific path
loaded_plan = MediaPlan.load_from_storage(manager, "campaigns/my_campaign.json")
```

#### Automatic Path Generation

If you don't specify a path when saving a media plan, the storage module will automatically generate a path based on the campaign ID:

1. The campaign ID is sanitized (replacing `/` and `\` with `_`)
2. The default file format is JSON
3. The file is saved as `{campaign_id}.json`

This makes it easy to save and load media plans without specifying a path every time.


### Using Storage Module Directly

You can also use the storage module directly:

```python
from mediaplanpy.storage import read_mediaplan, write_mediaplan

# Get workspace configuration
workspace_config = manager.get_resolved_config()

# Write media plan
write_mediaplan(workspace_config, media_plan.to_dict(), "path/to/save.json")

# Read media plan
data = read_mediaplan(workspace_config, "path/to/save.json")
```

### Using Storage Backend and Format Handler Directly

For more control, you can use the storage backend and format handler directly:

```python
from mediaplanpy.storage import get_storage_backend, get_format_handler_instance

# Get workspace configuration
workspace_config = manager.get_resolved_config()

# Get storage backend
backend = get_storage_backend(workspace_config)

# Get format handler
format_handler = get_format_handler_instance("json", indent=4)

# Write the file
serialized_data = format_handler.serialize(media_plan.to_dict())
backend.write_file("path/to/save.json", serialized_data)

# Read the file
read_content = backend.read_file("path/to/save.json")
data = format_handler.deserialize(read_content)
```

## Storage Backend Interface

All storage backends implement the following interface:

```python
class StorageBackend(abc.ABC):
    @abc.abstractmethod
    def exists(self, path: str) -> bool:
        """Check if a file exists at the specified path."""
        pass

    @abc.abstractmethod
    def read_file(self, path: str, binary: bool = False) -> Union[str, bytes]:
        """Read a file from the storage location."""
        pass
    
    @abc.abstractmethod
    def write_file(self, path: str, content: Union[str, bytes]) -> None:
        """Write content to a file at the specified path."""
        pass
    
    @abc.abstractmethod
    def list_files(self, path: str, pattern: Optional[str] = None) -> List[str]:
        """List files at the specified path."""
        pass
    
    @abc.abstractmethod
    def delete_file(self, path: str) -> None:
        """Delete a file at the specified path."""
        pass
    
    @abc.abstractmethod
    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get information about a file."""
        pass
    
    @abc.abstractmethod
    def open_file(self, path: str, mode: str = 'r') -> Union[TextIO, BinaryIO]:
        """Open a file and return a file-like object."""
        pass
```

## Format Handler Interface

All format handlers implement the following interface:

```python
class FormatHandler(abc.ABC):
    @abc.abstractmethod
    def serialize(self, data: Dict[str, Any], **kwargs) -> Union[str, bytes]:
        """Serialize data to the format's string or binary representation."""
        pass
    
    @abc.abstractmethod
    def deserialize(self, content: Union[str, bytes], **kwargs) -> Dict[str, Any]:
        """Deserialize content from the format's string or binary representation."""
        pass
    
    @abc.abstractmethod
    def serialize_to_file(self, data: Dict[str, Any], file_obj: Union[TextIO, BinaryIO], **kwargs) -> None:
        """Serialize data and write it to a file object."""
        pass
    
    @abc.abstractmethod
    def deserialize_from_file(self, file_obj: Union[TextIO, BinaryIO], **kwargs) -> Dict[str, Any]:
        """Read and deserialize data from a file object."""
        pass
```

## Future Plans

1. **Implement S3 Backend**: Add support for storing media plans in Amazon S3.
2. **Implement Google Drive Backend**: Add support for storing media plans in Google Drive.
3. **Implement Parquet Format**: Add support for storing media plans as Parquet files.
4. **Add Compression/Decompression Support**: Add support for automatically compressing and decompressing media plans during storage and retrieval operations. This would include:
   - Configurable compression algorithms (gzip, bzip2, lzma, etc.)
   - Compression level settings
   - Transparent decompression when loading files
   - Option to store files in compressed format with appropriate file extensions
   - Performance benchmarks for different compression methods
5. **Add Partitioning Support**: Add support for partitioning media plans by campaign, date, etc.
6. **Add Encryption Support**: Add support for encrypting media plans.
