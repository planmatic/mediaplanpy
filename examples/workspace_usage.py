from mediaplanpy import WorkspaceManager

# Load a workspace
workspace = WorkspaceManager(r"C:\Users\laure\PycharmProjects\mediaplanpy\examples\fixtures\sample_workspace.json")
workspace.load()
print(f"WORKSPACE IS LOADED: {workspace.is_loaded}")

# Get storage configuration
storage_config = workspace.get_storage_config()
print(f"WORKSPACE CONFIG: {str(storage_config)}")