# Quick diagnosis script to check current CLI state
# Run this to see what's in your current CLI file

import os
import sys

# Add current directory to path
sys.path.insert(0, 'src')

try:
    # Check CLI module import
    from mediaplanpy import cli

    print("✅ CLI module imports successfully")

    # Check if setup_argparse exists and what it contains
    if hasattr(cli, 'setup_argparse'):
        parser = cli.setup_argparse()
        print("✅ setup_argparse function exists")
        print(f"📋 Available actions: {[action.dest for action in parser._actions if hasattr(action, 'dest')]}")

        # Check for version argument
        has_version = any('version' in str(action) for action in parser._actions)
        print(f"📋 Has --version argument: {has_version}")

    else:
        print("❌ setup_argparse function not found")

    # Check current version info
    from mediaplanpy import __version__, __schema_version__

    print(f"📦 SDK Version: {__version__}")
    print(f"📋 Schema Version: {__schema_version__}")

except Exception as e:
    print(f"❌ Error importing CLI: {e}")

# Check if CLI file exists and show first few lines
cli_path = "src/mediaplanpy/cli.py"
if os.path.exists(cli_path):
    print(f"\n📁 CLI file exists at: {cli_path}")
    with open(cli_path, 'r') as f:
        lines = f.readlines()[:20]  # First 20 lines
        print("First 20 lines:")
        for i, line in enumerate(lines, 1):
            print(f"{i:2d}: {line.rstrip()}")
else:
    print(f"❌ CLI file not found at: {cli_path}")