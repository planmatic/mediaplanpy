from mediaplanpy import WorkspaceManager

# Load a workspace
workspace = WorkspaceManager()
workspace.load()

# Get storage configuration
storage_config = workspace.get_storage_config()