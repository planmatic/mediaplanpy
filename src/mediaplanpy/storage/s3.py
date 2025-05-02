"""
S3 storage backend for mediaplanpy.

This module provides a storage backend for storing media plans in AWS S3.

Note: This is a placeholder module for future implementation.
"""

import logging
from typing import Dict, Any, Optional, List, Union, BinaryIO, TextIO

from mediaplanpy.exceptions import StorageError, FileReadError, FileWriteError
from mediaplanpy.storage.base import StorageBackend

logger = logging.getLogger("mediaplanpy.storage.s3")


class S3StorageBackend(StorageBackend):
    """
    Storage backend for AWS S3.

    Reads and writes media plans to Amazon S3.

    Note: This is a placeholder class for future implementation.
    """

    def __init__(self, workspace_config: Dict[str, Any]):
        """
        Initialize the S3 storage backend.

        Args:
            workspace_config: The resolved workspace configuration dictionary.
        """
        super().__init__(workspace_config)

        # Extract S3 storage configuration
        storage_config = workspace_config.get('storage', {})
        if storage_config.get('mode') != 's3':
            raise StorageError("Workspace not configured for S3 storage")

        s3_config = storage_config.get('s3', {})

        # Get bucket name
        self.bucket = s3_config.get('bucket')
        if not self.bucket:
            raise StorageError("No bucket specified for S3 storage")

        # Get prefix (optional)
        self.prefix = s3_config.get('prefix', '')

        # Get region (optional)
        self.region = s3_config.get('region')

        # Get profile (optional)
        self.profile = s3_config.get('profile')

        # This is a placeholder for future implementation
        logger.warning("S3StorageBackend is not yet implemented")

    def exists(self, path: str) -> bool:
        """
        Check if a file exists at the specified path.

        Args:
            path: The path to check.

        Returns:
            True if the file exists, False otherwise.
        """
        raise NotImplementedError("S3StorageBackend.exists is not yet implemented")

    def read_file(self, path: str, binary: bool = False) -> Union[str, bytes]:
        """
        Read a file from S3.

        Args:
            path: The path to the file.
            binary: If True, read the file in binary mode.

        Returns:
            The contents of the file, either as a string or as bytes.

        Raises:
            FileReadError: If the file cannot be read.
        """
        raise NotImplementedError("S3StorageBackend.read_file is not yet implemented")

    def write_file(self, path: str, content: Union[str, bytes]) -> None:
        """
        Write content to a file in S3.

        Args:
            path: The path where the file should be written.
            content: The content to write, either as a string or as bytes.

        Raises:
            FileWriteError: If the file cannot be written.
        """
        raise NotImplementedError("S3StorageBackend.write_file is not yet implemented")

    def list_files(self, path: str, pattern: Optional[str] = None) -> List[str]:
        """
        List files at the specified path.

        Args:
            path: The path to list files from.
            pattern: Optional glob pattern to filter files.

        Returns:
            A list of file paths.

        Raises:
            StorageError: If the files cannot be listed.
        """
        raise NotImplementedError("S3StorageBackend.list_files is not yet implemented")

    def delete_file(self, path: str) -> None:
        """
        Delete a file at the specified path.

        Args:
            path: The path to the file to delete.

        Raises:
            StorageError: If the file cannot be deleted.
        """
        raise NotImplementedError("S3StorageBackend.delete_file is not yet implemented")

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """
        Get information about a file.

        Args:
            path: The path to the file.

        Returns:
            A dictionary with file information (size, modified date, etc).

        Raises:
            StorageError: If the file information cannot be retrieved.
        """
        raise NotImplementedError("S3StorageBackend.get_file_info is not yet implemented")

    def open_file(self, path: str, mode: str = 'r') -> Union[TextIO, BinaryIO]:
        """
        Open a file and return a file-like object.

        Args:
            path: The path to the file.
            mode: The mode to open the file in ('r', 'w', 'rb', 'wb', etc).

        Returns:
            A file-like object.

        Raises:
            StorageError: If the file cannot be opened.
        """
        raise NotImplementedError("S3StorageBackend.open_file is not yet implemented")