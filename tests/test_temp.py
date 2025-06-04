from mediaplanpy.workspace import WorkspaceManager

# Load existing workspace
manager = WorkspaceManager("C:\mediaplanpy\workspace_5f56431a_settings.json")
manager.load()

# Check compatibility first
compatibility = manager.check_workspace_compatibility()
print(f"Compatible: {compatibility['is_compatible']}")

# Run upgrade (dry run first)
result = manager.upgrade_workspace(dry_run=True)
print(f"Would migrate {result['json_files_migrated']} JSON files")

# Actually perform upgrade
result = manager.upgrade_workspace()
print(f"Upgrade completed: {result['workspace_updated']}")