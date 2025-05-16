"""
Updated StorageBackend base class with directory creation support.

This module adds a create_directory method to the base StorageBackend class
to support the new subdirectory structure.
"""

import abc
import logging
from typing import Dict, Any, Optional, List, Union, BinaryIO, TextIO, Tuple

from mediaplanpy.exceptions import StorageError, FileReadError, FileWriteError

logger = logging.getLogger("mediaplanpy.storage.base")


class StorageBackend(abc.ABC):
    """
    Abstract base class for storage backends.

    A storage backend is responsible for reading and writing media plans to
    a specific storage location, such as local filesystem, S3, or Google Drive.
    """

    def __init__(self, workspace_config: Dict[str, Any]):
        """
        Initialize the storage backend with the workspace configuration.

        Args:
            workspace_config: The resolved workspace configuration dictionary.
        """
        self.config = workspace_config

    @abc.abstractmethod
    def exists(self, path: str) -> bool:
        """
        Check if a file exists at the specified path.

        Args:
            path: The path to check.

        Returns:
            True if the file exists, False otherwise.
        """
        pass

    @abc.abstractmethod
    def read_file(self, path: str, binary: bool = False) -> Union[str, bytes]:
        """
        Read a file from the storage location.

        Args:
            path: The path to the file.
            binary: If True, read the file in binary mode.

        Returns:
            The contents of the file, either as a string or as bytes.

        Raises:
            FileReadError: If the file cannot be read.
        """
        pass

    @abc.abstractmethod
    def write_file(self, path: str, content: Union[str, bytes]) -> None:
        """
        Write content to a file at the specified path.

        Args:
            path: The path where the file should be written.
            content: The content to write, either as a string or as bytes.

        Raises:
            FileWriteError: If the file cannot be written.
        """
        pass

    @abc.abstractmethod
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
        pass

    @abc.abstractmethod
    def delete_file(self, path: str) -> None:
        """
        Delete a file at the specified path.

        Args:
            path: The path to the file to delete.

        Raises:
            StorageError: If the file cannot be deleted.
        """
        pass

    @abc.abstractmethod
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
        pass

    @abc.abstractmethod
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
        pass

    def create_directory(self, path: str) -> None:
        """
        Create a directory at the specified path if it doesn't exist.

        This method should be implemented by storage backends that support
        directory creation. The base implementation does nothing.

        Args:
            path: The path to the directory to create.

        Raises:
            StorageError: If the directory cannot be created.
        """
        # Default implementation does nothing
        # Subclasses should override this method if they support directory creation
        pass

    def resolve_path(self, path: str) -> str:
        """
        Resolve a path according to the storage backend's rules.

        Args:
            path: The path to resolve.

        Returns:
            The resolved path.
        """
        return path

    def join_path(self, *parts: str) -> str:
        """
        Join path components according to the storage backend's rules.

        Args:
            *parts: Path components to join.

        Returns:
            The joined path.
        """
        return '/'.join(p.strip('/') for p in parts if p)