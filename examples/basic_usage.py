from mediaplanpy import WorkspaceManager

# Load a workspace
workspace = WorkspaceManager(r"C:\Users\laure\PycharmProjects\mediaplanpy\examples\fixtures\sample_workspace.json")
workspace.load()

# Get storage configuration
storage_config = workspace.get_storage_config()
print(storage_config)