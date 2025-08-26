"""
S3 storage backend for mediaplanpy.

This module provides a storage backend for storing media plans in AWS S3.
"""

import logging
import os
from typing import Dict, Any, Optional, List, Union, BinaryIO, TextIO
import io
import posixpath

import boto3
import botocore
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError

from mediaplanpy.exceptions import StorageError, FileReadError, FileWriteError
from mediaplanpy.storage.base import StorageBackend

logger = logging.getLogger("mediaplanpy.storage.s3")


class S3StorageBackend(StorageBackend):
    """
    Storage backend for AWS S3.

    Reads and writes media plans to Amazon S3 with support for:
    - AWS credential chain: profile -> environment variables -> default
    - Configurable bucket, region, and prefix
    - S3-compatible services via custom endpoint URLs
    """

    def __init__(self, workspace_config: Dict[str, Any]):
        """
        Initialize the S3 storage backend.

        Args:
            workspace_config: The resolved workspace configuration dictionary.

        Raises:
            StorageError: If S3 configuration is invalid or credentials cannot be found.
        """
        super().__init__(workspace_config)

        # Extract S3 storage configuration
        storage_config = workspace_config.get('storage', {})
        if storage_config.get('mode') != 's3':
            raise StorageError("Workspace not configured for S3 storage")

        s3_config = storage_config.get('s3', {})

        # Get required configuration
        self.bucket = s3_config.get('bucket')
        if not self.bucket:
            raise StorageError("No bucket specified for S3 storage")

        self.region = s3_config.get('region')
        if not self.region:
            raise StorageError("No region specified for S3 storage")

        # Get optional configuration with defaults
        workspace_id = workspace_config.get('workspace_id', '')
        self.prefix = s3_config.get('prefix', workspace_id)

        # Ensure prefix ends with '/' if it's not empty
        if self.prefix and not self.prefix.endswith('/'):
            self.prefix += '/'

        # AWS authentication settings
        self.profile = s3_config.get('profile')
        self.endpoint_url = s3_config.get('endpoint_url')
        self.use_ssl = s3_config.get('use_ssl', True)

        # Initialize S3 client
        self.s3_client = self._create_s3_client()

        # Test the connection
        self._test_connection()

        logger.info(f"Initialized S3 storage backend: s3://{self.bucket}/{self.prefix}")

    def _create_s3_client(self):
        """
        Create and configure the S3 client with appropriate credentials.

        Returns:
            boto3.client: Configured S3 client

        Raises:
            StorageError: If credentials cannot be configured or client creation fails
        """
        try:
            # Build client configuration
            client_config = {
                'region_name': self.region,
                'use_ssl': self.use_ssl
            }

            # Add endpoint URL if specified (for S3-compatible services)
            if self.endpoint_url:
                client_config['endpoint_url'] = self.endpoint_url

            # Handle AWS credentials in priority order:
            # 1. AWS profile (if specified)
            # 2. Environment variables
            # 3. Default AWS credentials chain (IAM roles, default profile)

            if self.profile:
                # Use specific AWS profile
                logger.debug(f"Using AWS profile: {self.profile}")
                session = boto3.Session(profile_name=self.profile)
                return session.client('s3', **client_config)
            else:
                # Use default credentials chain
                logger.debug("Using default AWS credentials chain")
                return boto3.client('s3', **client_config)

        except NoCredentialsError as e:
            raise StorageError(
                f"No AWS credentials found. Please configure credentials using:\n"
                f"  1. AWS profile in workspace config\n"
                f"  2. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)\n" 
                f"  3. AWS credentials file (~/.aws/credentials)\n"
                f"  4. IAM roles (for EC2/ECS deployments)\n"
                f"Original error: {e}"
            )
        except Exception as e:
            raise StorageError(f"Failed to create S3 client: {e}")

    def _test_connection(self):
        """
        Test the S3 connection and bucket accessibility.

        Raises:
            StorageError: If connection test fails
        """
        try:
            # Test connection by checking if bucket exists and is accessible
            self.s3_client.head_bucket(Bucket=self.bucket)
            logger.debug(f"Successfully connected to S3 bucket: {self.bucket}")

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')

            if error_code == '404':
                raise StorageError(
                    f"S3 bucket '{self.bucket}' does not exist or is not accessible. "
                    f"Please verify the bucket name and your permissions."
                )
            elif error_code == '403':
                raise StorageError(
                    f"Access denied to S3 bucket '{self.bucket}'. "
                    f"Please verify your AWS credentials have the required permissions."
                )
            else:
                raise StorageError(f"S3 connection test failed: {e}")

        except Exception as e:
            raise StorageError(f"S3 connection test failed: {e}")

    def resolve_s3_key(self, path: str) -> str:
        """
        Convert a relative path to a full S3 key by combining with prefix.

        Args:
            path: Relative path (e.g., "mediaplans/plan1.json")

        Returns:
            Full S3 key (e.g., "workspace123/mediaplans/plan1.json")
        """
        # Clean the path - convert backslashes to forward slashes, remove leading slashes
        clean_path = path.replace('\\', '/').lstrip('/')

        if self.prefix:
            # Use posixpath.join to properly handle S3 paths (always forward slashes)
            return posixpath.join(self.prefix.rstrip('/'), clean_path)
        else:
            return clean_path

    def resolve_path(self, path: str) -> str:
        """
        Resolve a path according to S3 storage rules.

        Args:
            path: The path to resolve

        Returns:
            The resolved S3 key
        """
        return self.resolve_s3_key(path)

    def join_path(self, *parts: str) -> str:
        """
        Join path components using S3 conventions (forward slashes).

        Args:
            *parts: Path components to join

        Returns:
            The joined path using forward slashes
        """
        # Filter out empty parts and join with forward slashes
        clean_parts = [p.replace('\\', '/').strip('/') for p in parts if p]
        return '/'.join(clean_parts)

    def create_directory(self, path: str) -> None:
        """
        Create a directory at the specified path.

        In S3, directories don't exist as separate entities, so this is a no-op.
        S3 automatically creates the directory structure when objects are uploaded.

        Args:
            path: The directory path to create (ignored in S3)
        """
        # S3 doesn't have real directories - they're created implicitly when objects are uploaded
        logger.debug(f"S3 directory creation requested for '{path}' - no action needed")
        pass

    def exists(self, path: str) -> bool:
        """
        Check if a file exists at the specified path in S3.

        Args:
            path: The path to check

        Returns:
            True if the file exists, False otherwise
        """
        s3_key = self.resolve_s3_key(path)

        try:
            # Use head_object for efficient existence check (doesn't download content)
            self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            return True

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')

            if error_code == '404':
                # Object doesn't exist
                return False
            else:
                # Other error (permissions, etc.) - log and re-raise
                logger.error(f"Error checking existence of s3://{self.bucket}/{s3_key}: {e}")
                raise StorageError(f"Failed to check if file exists at {path}: {e}")

        except Exception as e:
            logger.error(f"Unexpected error checking existence of s3://{self.bucket}/{s3_key}: {e}")
            raise StorageError(f"Failed to check if file exists at {path}: {e}")

    def read_file(self, path: str, binary: bool = False) -> Union[str, bytes]:
        """
        Read a file from S3.

        Args:
            path: The path to the file
            binary: If True, read the file in binary mode

        Returns:
            The contents of the file, either as a string or as bytes

        Raises:
            FileReadError: If the file cannot be read
        """
        s3_key = self.resolve_s3_key(path)

        try:
            # Download the object from S3
            response = self.s3_client.get_object(Bucket=self.bucket, Key=s3_key)

            # Read the content from the streaming body
            content_bytes = response['Body'].read()

            if binary:
                return content_bytes
            else:
                # Decode to string using UTF-8
                try:
                    return content_bytes.decode('utf-8')
                except UnicodeDecodeError as e:
                    raise FileReadError(
                        f"Failed to decode file {path} as UTF-8. "
                        f"Use binary=True for binary files. Error: {e}"
                    )

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')

            if error_code == 'NoSuchKey':
                raise FileReadError(f"File not found: {path} (s3://{self.bucket}/{s3_key})")
            elif error_code == '403':
                raise FileReadError(f"Access denied reading file: {path}")
            else:
                raise FileReadError(f"Failed to read file {path} from S3: {e}")

        except Exception as e:
            raise FileReadError(f"Failed to read file {path}: {e}")

    def write_file(self, path: str, content: Union[str, bytes]) -> None:
        """
        Write content to a file in S3.

        Args:
            path: The path where the file should be written
            content: The content to write, either as a string or as bytes

        Raises:
            FileWriteError: If the file cannot be written
        """
        s3_key = self.resolve_s3_key(path)

        try:
            # Convert string content to bytes if needed
            if isinstance(content, str):
                content_bytes = content.encode('utf-8')
                content_type = 'text/plain; charset=utf-8'
            else:
                content_bytes = content
                # Try to infer content type from file extension
                content_type = self._infer_content_type(path)

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=content_bytes,
                ContentType=content_type
            )

            logger.debug(f"Successfully wrote {len(content_bytes)} bytes to s3://{self.bucket}/{s3_key}")

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')

            if error_code == '403':
                raise FileWriteError(f"Access denied writing file: {path}")
            else:
                raise FileWriteError(f"Failed to write file {path} to S3: {e}")

        except Exception as e:
            raise FileWriteError(f"Failed to write file {path}: {e}")

    def list_files(self, path: str, pattern: Optional[str] = None) -> List[str]:
        """
        List files at the specified path in S3.

        Args:
            path: The directory path to list files from
            pattern: Optional glob pattern to filter files

        Returns:
            A list of file paths relative to the storage root

        Raises:
            StorageError: If the files cannot be listed
        """
        # Convert path to S3 key prefix
        if path:
            s3_prefix = self.resolve_s3_key(path)
            if not s3_prefix.endswith('/'):
                s3_prefix += '/'
        else:
            s3_prefix = self.prefix if self.prefix else ''

        try:
            # List objects with the specified prefix
            files = []
            paginator = self.s3_client.get_paginator('list_objects_v2')

            for page in paginator.paginate(Bucket=self.bucket, Prefix=s3_prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        s3_key = obj['Key']

                        # Convert S3 key back to relative path
                        if self.prefix and s3_key.startswith(self.prefix):
                            relative_path = s3_key[len(self.prefix):]
                        else:
                            relative_path = s3_key

                        # Skip if it's just the prefix (directory marker)
                        if relative_path and not relative_path.endswith('/'):
                            files.append(relative_path)

            # Apply pattern filter if specified
            if pattern:
                import fnmatch
                files = [f for f in files if fnmatch.fnmatch(f, pattern)]

            # Sort files for consistent ordering
            files.sort()

            logger.debug(f"Listed {len(files)} files from s3://{self.bucket}/{s3_prefix}")
            return files

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')

            if error_code == '403':
                raise StorageError(f"Access denied listing files at path: {path}")
            else:
                raise StorageError(f"Failed to list files at {path}: {e}")

        except Exception as e:
            raise StorageError(f"Failed to list files at {path}: {e}")

    def delete_file(self, path: str) -> None:
        """
        Delete a file at the specified path in S3.

        Args:
            path: The path to the file to delete

        Raises:
            StorageError: If the file cannot be deleted
        """
        s3_key = self.resolve_s3_key(path)

        try:
            # Delete the object from S3
            self.s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.debug(f"Successfully deleted s3://{self.bucket}/{s3_key}")

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')

            if error_code == '403':
                raise StorageError(f"Access denied deleting file: {path}")
            else:
                raise StorageError(f"Failed to delete file {path} from S3: {e}")

        except Exception as e:
            raise StorageError(f"Failed to delete file {path}: {e}")

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """
        Get information about a file in S3.

        Args:
            path: The path to the file

        Returns:
            A dictionary with file information (size, modified date, etc)

        Raises:
            StorageError: If the file information cannot be retrieved
        """
        s3_key = self.resolve_s3_key(path)

        try:
            # Get object metadata using head_object (efficient, no download)
            response = self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)

            # Extract relevant information
            file_info = {
                'path': path,
                's3_key': s3_key,
                's3_url': f"s3://{self.bucket}/{s3_key}",
                'size': response.get('ContentLength', 0),
                'modified': response.get('LastModified'),
                'content_type': response.get('ContentType', 'unknown'),
                'etag': response.get('ETag', '').strip('"'),  # Remove quotes from ETag
                'is_directory': False  # S3 objects are always files
            }

            # Add storage class if available
            if 'StorageClass' in response:
                file_info['storage_class'] = response['StorageClass']

            # Add server-side encryption info if available
            if 'ServerSideEncryption' in response:
                file_info['encryption'] = response['ServerSideEncryption']

            return file_info

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')

            if error_code == '404':
                raise StorageError(f"File not found: {path} (s3://{self.bucket}/{s3_key})")
            elif error_code == '403':
                raise StorageError(f"Access denied getting file info: {path}")
            else:
                raise StorageError(f"Failed to get file info for {path}: {e}")

        except Exception as e:
            raise StorageError(f"Failed to get file info for {path}: {e}")

    def open_file(self, path: str, mode: str = 'r') -> Union[TextIO, BinaryIO]:
        """
        Open a file and return a file-like object.

        Args:
            path: The path to the file
            mode: The mode to open the file in ('r', 'w', 'rb', 'wb', 'a')

        Returns:
            A file-like object

        Raises:
            StorageError: If the file cannot be opened
        """
        # Parse the mode
        if mode not in ['r', 'w', 'rb', 'wb', 'a', 'ab']:
            raise StorageError(f"Unsupported file mode: {mode}")

        is_binary = 'b' in mode
        is_write = 'w' in mode or 'a' in mode
        is_append = 'a' in mode

        if is_write:
            # Write modes: return a file-like object that uploads on close
            return S3WriteWrapper(self, path, is_binary, is_append)
        else:
            # Read modes: download content and return StringIO/BytesIO
            try:
                content = self.read_file(path, binary=is_binary)

                if is_binary:
                    return io.BytesIO(content)
                else:
                    return io.StringIO(content)

            except FileReadError as e:
                raise StorageError(f"Failed to open file {path} for reading: {e}")

    def _infer_content_type(self, path: str) -> str:
        """
        Infer the MIME content type from file extension.

        Args:
            path: File path to infer type from

        Returns:
            MIME content type string
        """
        import mimetypes

        # Get the file extension
        _, ext = posixpath.splitext(path.lower())

        # Use mimetypes to guess, with fallbacks for common types
        content_type, _ = mimetypes.guess_type(path)

        if content_type:
            return content_type

        # Fallback mappings for common file types
        type_mappings = {
            '.json': 'application/json',
            '.parquet': 'application/octet-stream',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.csv': 'text/csv',
            '.txt': 'text/plain',
            '.log': 'text/plain'
        }

        return type_mappings.get(ext, 'application/octet-stream')


class S3WriteWrapper:
    """
    A file-like wrapper that accumulates writes and uploads to S3 on close.

    This allows the storage backend to support the standard file interface
    while efficiently handling S3 uploads.
    """

    def __init__(self, backend: 'S3StorageBackend', path: str, is_binary: bool, is_append: bool):
        self.backend = backend
        self.path = path
        self.is_binary = is_binary
        self.is_append = is_append
        self.closed = False

        if is_binary:
            self._buffer = io.BytesIO()
        else:
            self._buffer = io.StringIO()

        # For append mode, pre-load existing content
        if is_append and backend.exists(path):
            try:
                existing_content = backend.read_file(path, binary=is_binary)
                self._buffer.write(existing_content)
            except FileReadError:
                # If we can't read existing content, start fresh
                pass

    def write(self, data: Union[str, bytes]) -> int:
        """Write data to the buffer."""
        if self.closed:
            raise ValueError("I/O operation on closed file")

        return self._buffer.write(data)

    def writelines(self, lines):
        """Write a list of lines to the buffer."""
        if self.closed:
            raise ValueError("I/O operation on closed file")

        self._buffer.writelines(lines)

    def flush(self):
        """Flush the buffer (no-op for this implementation)."""
        if self.closed:
            raise ValueError("I/O operation on closed file")

        self._buffer.flush()

    def close(self):
        """Close the file and upload content to S3."""
        if not self.closed:
            try:
                # Get all content from buffer
                content = self._buffer.getvalue()

                # Upload to S3
                self.backend.write_file(self.path, content)

                # Close the buffer
                self._buffer.close()
                self.closed = True

            except Exception as e:
                self.closed = True
                raise StorageError(f"Failed to upload file {self.path} to S3: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    @property
    def mode(self) -> str:
        """Return the file mode."""
        if self.is_append:
            return 'ab' if self.is_binary else 'a'
        else:
            return 'wb' if self.is_binary else 'w'

    @property
    def name(self) -> str:
        """Return the file path."""
        return self.path

    def readable(self) -> bool:
        """Return whether the file supports reading."""
        return False

    def writable(self) -> bool:
        """Return whether the file supports writing."""
        return not self.closed

    def seekable(self) -> bool:
        """Return whether the file supports seeking."""
        return not self.closed