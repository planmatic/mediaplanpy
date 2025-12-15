"""
MediaPlanPy Examples - API Client Interface

This script demonstrates how to interact with a Planmatic API Server using the MediaPlanPy SDK.
The Planmatic API provides remote access to workspace and media plan operations.

v3.0 Features Demonstrated:
- API authentication with session tokens
- Remote workspace loading
- Remote media plan retrieval
- Media plan import/upload to server
- Campaign listing and inspection
- Error handling and best practices

Prerequisites:
- MediaPlanPy SDK v3.0.0+ installed
- Planmatic API Server access (https://api.planmatic.io)
- Valid API key (contact server administrator)
- requests library: pip install requests

How to Run:
1. Request an API key from your Planmatic API Server administrator
2. Set your API key and workspace ID in the script or environment variables
3. Open this file in your IDE
4. Run the entire script: python examples_14_api_client.py
5. Or run individual functions from __main__

API Key Format:
    plnmtc_<env>_<client_id>_<token>
    Example: plnmtc_prod1_4_abc123def456...

Security Notes:
- Never commit API keys to version control
- Use environment variables for sensitive credentials
- Rotate API keys regularly
- Keep session tokens secure

Next Steps After Running:
- Integrate API calls into your workflows
- Build automation scripts using the API
- Create custom dashboards with API data
"""

import os
import sys
import json
import requests
import tempfile
from typing import Optional, Dict, Any
from pathlib import Path

# Import MediaPlanPy SDK
try:
    from mediaplanpy import MediaPlan
except ImportError as e:
    print(f"Error: MediaPlanPy SDK not installed: {e}")
    print("Install with: pip install mediaplanpy")
    exit(1)


# =============================================================================
# API CLIENT CONFIGURATION
# =============================================================================

# API Server URL (default: Planmatic production)
API_BASE_URL = "https://api.planmatic.io"

# API Key - REPLACE WITH YOUR KEY or set environment variable
# API_KEY = os.environ.get("PLANMATIC_API_KEY", "your_api_key_here")

# Workspace ID - REPLACE WITH YOUR WORKSPACE ID
# WORKSPACE_ID = os.environ.get("PLANMATIC_WORKSPACE_ID", "workspace_id_here")


# =============================================================================
# EXAMPLE 1: API KEY REQUEST INSTRUCTIONS
# =============================================================================

def show_api_key_request_instructions():
    """
    Display instructions for requesting an API key from the Planmatic API Server.

    Use Case:
        First-time users need to know how to obtain API credentials before
        they can interact with the Planmatic API Server.

    API Key Format:
        plnmtc_<env>_<client_id>_<token>
        Example: plnmtc_prod1_4_abc123def456...

    Security Considerations:
        - API keys grant full access to workspace data
        - Keys should be kept secure and never committed to version control
        - Use environment variables to store sensitive credentials
        - Rotate keys regularly according to security policies

    Next Steps:
        - Contact your Planmatic API Server administrator
        - Provide your use case and required access level
        - Receive API key via secure channel
        - Store key in environment variable: PLANMATIC_API_KEY
    """
    print("\n" + "=" * 80)
    print("HOW TO REQUEST A PLANMATIC API KEY")
    print("=" * 80)

    print("\nSTEP 1: Contact API Server Administrator")
    print("-" * 80)
    print("Contact your Planmatic API Server administrator to request an API key.")
    print("\nProvide the following information:")
    print("  - Your name and organization")
    print("  - Use case / purpose (e.g., 'Media plan automation')")
    print("  - Required workspace access")
    print("  - Expected usage volume")

    print("\nSTEP 2: Receive API Key")
    print("-" * 80)
    print("The administrator will provide you with:")
    print("  - API Key (format: plnmtc_<env>_<client_id>_<token>)")
    print("  - Workspace ID(s) you can access")
    print("  - API endpoint URL (default: https://api.planmatic.io)")

    print("\nSTEP 3: Secure Storage")
    print("-" * 80)
    print("Store your API key securely using environment variables:")
    print("\n  On Linux/macOS:")
    print("    export PLANMATIC_API_KEY='plnmtc_prod1_4_abc123...'")
    print("    export PLANMATIC_WORKSPACE_ID='workspace_49aa28ac'")
    print("\n  On Windows (Command Prompt):")
    print("    set PLANMATIC_API_KEY=plnmtc_prod1_4_abc123...")
    print("    set PLANMATIC_WORKSPACE_ID=workspace_49aa28ac")
    print("\n  On Windows (PowerShell):")
    print("    $env:PLANMATIC_API_KEY='plnmtc_prod1_4_abc123...'")
    print("    $env:PLANMATIC_WORKSPACE_ID='workspace_49aa28ac'")

    print("\nSTEP 4: Use in Scripts")
    print("-" * 80)
    print("Access credentials in your Python scripts:")
    print("""
    import os

    API_KEY = os.environ.get("PLANMATIC_API_KEY")
    WORKSPACE_ID = os.environ.get("PLANMATIC_WORKSPACE_ID")

    if not API_KEY:
        raise ValueError("PLANMATIC_API_KEY environment variable not set")
    """)

    print("\nSECURITY BEST PRACTICES:")
    print("-" * 80)
    print("  - Never commit API keys to version control (.git, .svn)")
    print("  - Add API keys to .gitignore or .env files")
    print("  - Use separate keys for development and production")
    print("  - Rotate API keys regularly (every 90 days recommended)")
    print("  - Revoke compromised keys immediately")
    print("  - Use least-privilege access (only necessary permissions)")

    print("\nREADY TO PROCEED:")
    print("-" * 80)
    print("Once you have your API key and workspace ID:")
    print("  1. Set environment variables as shown above")
    print("  2. Run authentication example: authenticate_with_api()")
    print("  3. Continue with other examples in this script")

    print("\n" + "=" * 80)


# =============================================================================
# EXAMPLE 2: AUTHENTICATE WITH API
# =============================================================================

def authenticate_with_api(api_key: str, base_url: str = API_BASE_URL) -> Optional[str]:
    """
    Authenticate with the Planmatic API Server using an API key.

    Use Case:
        First step for all API interactions. Authentication returns a session
        token that must be included in subsequent API requests.

    Authentication Flow:
        1. Send POST request to /auth/authenticate with API key
        2. Receive session token in response
        3. Use session token in Authorization header for subsequent requests
        4. Session token expires after period of inactivity

    Args:
        api_key: API key in format plnmtc_<env>_<client_id>_<token>
        base_url: API server base URL (default: https://api.planmatic.io)

    Returns:
        Session token if successful, None otherwise

    Error Handling:
        - 401: Invalid API key
        - 500: Server error
        - Network errors: Connection failures, timeouts

    Next Steps:
        - Store session token for subsequent requests
        - Load workspace using load_workspace_from_api()
        - Session tokens have limited lifetime (refresh as needed)
    """
    print("\n" + "=" * 80)
    print("AUTHENTICATING WITH PLANMATIC API SERVER")
    print("=" * 80)

    print("\nAPI Configuration:")
    print(f"  - Base URL: {base_url}")
    print(f"  - API Key: {api_key[:20]}... (truncated for security)")

    try:
        print("\nStep 1: Sending authentication request...")
        response = requests.post(
            f"{base_url}/auth/authenticate",
            json={"api_key": api_key},
            timeout=30
        )

        print(f"  - Response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if data.get('success'):
                session_token = data['data']['session_token']
                client_info = data['data'].get('client', {})

                print("\n✓ Authentication Successful")
                print("\nSession Information:")
                print(f"  - Session token: {session_token[:20]}... (truncated)")
                print(f"  - Client ID: {client_info.get('client_id', 'N/A')}")
                print(f"  - Client name: {client_info.get('name', 'N/A')}")

                print("\nNext Steps:")
                print("  1. Use session token in subsequent API requests")
                print("  2. Load workspace: load_workspace_from_api(session_token, workspace_id)")
                print("  3. Token is valid until session expires or logout")

                print("\n" + "=" * 80)
                return session_token
            else:
                print(f"\n✗ Authentication Failed")
                print(f"  - Error: {data.get('message', 'Unknown error')}")
                return None

        elif response.status_code == 401:
            print(f"\n✗ Authentication Failed - Invalid API Key")
            print(f"  - HTTP Status: 401 Unauthorized")
            print(f"  - Verify your API key is correct")
            print(f"  - Contact administrator if key should be valid")
            return None

        else:
            print(f"\n✗ Authentication Failed")
            print(f"  - HTTP Status: {response.status_code}")
            try:
                error_data = response.json()
                print(f"  - Error: {error_data.get('message', 'Unknown error')}")
            except:
                print(f"  - Response: {response.text[:200]}")
            return None

    except requests.exceptions.Timeout:
        print(f"\n✗ Request Timeout")
        print(f"  - Server did not respond within 30 seconds")
        print(f"  - Check network connectivity")
        print(f"  - Verify server URL is correct: {base_url}")
        return None

    except requests.exceptions.ConnectionError:
        print(f"\n✗ Connection Error")
        print(f"  - Cannot connect to server: {base_url}")
        print(f"  - Check network connectivity")
        print(f"  - Verify server is online")
        return None

    except Exception as e:
        print(f"\n✗ Unexpected Error")
        print(f"  - Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


# =============================================================================
# EXAMPLE 3: LOAD WORKSPACE FROM API
# =============================================================================

def load_workspace_from_api(
    session_token: str,
    workspace_id: str,
    base_url: str = API_BASE_URL
) -> bool:
    """
    Load a workspace into the API session.

    Use Case:
        After authentication, you must load a workspace before accessing
        campaigns and media plans. The workspace context is stored server-side
        in your session.

    Workspace Loading:
        - Associates your session with a specific workspace
        - Validates your access permissions to the workspace
        - Enables subsequent operations on workspace data
        - Session maintains workspace context until changed or logged out

    Args:
        session_token: Session token from authenticate_with_api()
        workspace_id: Workspace identifier to load
        base_url: API server base URL (default: https://api.planmatic.io)

    Returns:
        True if successful, False otherwise

    Access Control:
        - System clients: Unrestricted workspace access
        - User clients: Limited to whitelisted workspaces
        - Returns 403 if access denied

    Next Steps:
        - List campaigns: list_campaigns_from_api()
        - Load media plan: load_media_plan_from_api()
        - Import media plan: import_media_plan_to_api()
    """
    print("\n" + "=" * 80)
    print("LOADING WORKSPACE FROM API")
    print("=" * 80)

    print("\nWorkspace Configuration:")
    print(f"  - Workspace ID: {workspace_id}")
    print(f"  - API Base URL: {base_url}")

    try:
        print("\nStep 1: Sending workspace load request...")
        response = requests.post(
            f"{base_url}/workspace/load",
            headers={"Authorization": f"Bearer {session_token}"},
            params={"workspace_id": workspace_id},
            timeout=30
        )

        print(f"  - Response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if data.get('success'):
                workspace_data = data.get('data', {})

                print("\n✓ Workspace Loaded Successfully")
                print("\nWorkspace Information:")
                print(f"  - Workspace ID: {workspace_id}")
                print(f"  - Name: {workspace_data.get('workspace_name', 'N/A')}")
                print(f"  - Schema version: {workspace_data.get('schema_version', 'N/A')}")
                print(f"  - Environment: {workspace_data.get('environment', 'production')}")

                print("\nSession Context:")
                print(f"  - Workspace context stored in session")
                print(f"  - All subsequent API calls will use this workspace")

                print("\nNext Steps:")
                print("  1. List campaigns in workspace")
                print("  2. Load media plans from campaigns")
                print("  3. Import/export media plans")

                print("\n" + "=" * 80)
                return True
            else:
                print(f"\n✗ Workspace Load Failed")
                print(f"  - Error: {data.get('message', 'Unknown error')}")
                return False

        elif response.status_code == 403:
            print(f"\n✗ Access Denied")
            print(f"  - HTTP Status: 403 Forbidden")
            print(f"  - You do not have permission to access this workspace")
            print(f"  - Contact administrator to request access")
            return False

        elif response.status_code == 404:
            print(f"\n✗ Workspace Not Found")
            print(f"  - HTTP Status: 404 Not Found")
            print(f"  - Workspace ID '{workspace_id}' does not exist")
            print(f"  - Verify workspace ID is correct")
            return False

        else:
            print(f"\n✗ Workspace Load Failed")
            print(f"  - HTTP Status: {response.status_code}")
            try:
                error_data = response.json()
                print(f"  - Error: {error_data.get('message', 'Unknown error')}")
            except:
                print(f"  - Response: {response.text[:200]}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Request Error")
        print(f"  - Error: {str(e)}")
        return False

    except Exception as e:
        print(f"\n✗ Unexpected Error")
        print(f"  - Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# EXAMPLE 4: LIST CAMPAIGNS FROM API
# =============================================================================

def list_campaigns_from_api(
    session_token: str,
    base_url: str = API_BASE_URL
) -> Optional[list]:
    """
    Retrieve list of campaigns from the loaded workspace.

    Use Case:
        Inspect available campaigns in workspace, get campaign IDs for
        loading media plans, and view campaign summary information.

    Campaign Information Returned:
        - Campaign ID and name
        - Budget and currency
        - Start and end dates
        - Plan counts (current, archived, total)
        - Line item statistics

    Args:
        session_token: Session token from authenticate_with_api()
        base_url: API server base URL (default: https://api.planmatic.io)

    Returns:
        List of campaign dictionaries if successful, None otherwise

    Prerequisites:
        - Must call authenticate_with_api() first
        - Must call load_workspace_from_api() first

    Next Steps:
        - Select campaign to work with
        - Load media plan: load_media_plan_from_api(campaign_id)
        - View plan history: GET /campaigns/{campaign_id}/plans
    """
    print("\n" + "=" * 80)
    print("LISTING CAMPAIGNS FROM API")
    print("=" * 80)

    try:
        print("\nStep 1: Retrieving campaigns list...")
        response = requests.get(
            f"{base_url}/campaigns",
            headers={"Authorization": f"Bearer {session_token}"},
            timeout=30
        )

        print(f"  - Response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if data.get('success'):
                campaigns = data['data'].get('campaigns', [])

                print(f"\n✓ Retrieved {len(campaigns)} campaigns")

                if campaigns:
                    print("\nCampaigns:")
                    print("-" * 80)

                    for i, campaign in enumerate(campaigns, 1):
                        print(f"\n{i}. Campaign: {campaign.get('campaign_name', 'N/A')}")
                        print(f"   - Campaign ID: {campaign.get('campaign_id', 'N/A')}")
                        print(f"   - Objective: {campaign.get('campaign_objective', 'N/A')}")
                        print(f"   - Budget: ${campaign.get('campaign_budget_total', 0):,.0f} {campaign.get('campaign_budget_currency', 'USD')}")
                        print(f"   - Period: {campaign.get('campaign_start_date', 'N/A')} to {campaign.get('campaign_end_date', 'N/A')}")
                        print(f"   - Media plans: {campaign.get('stat_media_plan_count', 0)} total")

                    print("\n" + "-" * 80)
                    print("\nNext Steps:")
                    print("  1. Select a campaign_id from the list above")
                    print("  2. Load current plan: load_media_plan_from_api(session_token, campaign_id)")
                    print("  3. Or list all plans: GET /campaigns/{campaign_id}/plans")
                else:
                    print("\nNo campaigns found in workspace")
                    print("  - Workspace may be empty")
                    print("  - Create campaigns using Python API")

                print("\n" + "=" * 80)
                return campaigns
            else:
                print(f"\n✗ Failed to Retrieve Campaigns")
                print(f"  - Error: {data.get('message', 'Unknown error')}")
                return None

        else:
            print(f"\n✗ Request Failed")
            print(f"  - HTTP Status: {response.status_code}")
            try:
                error_data = response.json()
                print(f"  - Error: {error_data.get('message', 'Unknown error')}")
            except:
                print(f"  - Response: {response.text[:200]}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Request Error")
        print(f"  - Error: {str(e)}")
        return None

    except Exception as e:
        print(f"\n✗ Unexpected Error")
        print(f"  - Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


# =============================================================================
# EXAMPLE 5: LOAD MEDIA PLAN FROM API
# =============================================================================

def load_media_plan_from_api(
    session_token: str,
    campaign_id: str,
    base_url: str = API_BASE_URL
) -> Optional[MediaPlan]:
    """
    Load current media plan from a campaign via API.

    Use Case:
        Retrieve the current media plan for a campaign to inspect, edit,
        or analyze using MediaPlanPy SDK. The API returns JSON which is
        converted to a MediaPlan object for local manipulation.

    Workflow:
        1. API returns current plan JSON for campaign
        2. JSON is converted to MediaPlan object using MediaPlanPy SDK
        3. MediaPlan object can be inspected and edited locally
        4. Changes can be saved back via import_media_plan_to_api()

    Args:
        session_token: Session token from authenticate_with_api()
        campaign_id: Campaign ID to load current plan from
        base_url: API server base URL (default: https://api.planmatic.io)

    Returns:
        MediaPlan object if successful, None otherwise

    v3.0 Features Accessible:
        - Complete meta information (schema v3.0)
        - Campaign details with target_audiences, target_locations
        - Line items with all v3.0 fields
        - MetricFormula objects
        - Dictionary configuration
        - Custom dimensions and properties

    Next Steps:
        - Inspect plan: plan.meta, plan.campaign, plan.lineitems
        - Edit plan using MediaPlanPy SDK methods
        - Save changes: import_media_plan_to_api()
    """
    print("\n" + "=" * 80)
    print("LOADING MEDIA PLAN FROM API")
    print("=" * 80)

    print("\nRequest Details:")
    print(f"  - Campaign ID: {campaign_id}")
    print(f"  - API Endpoint: {base_url}/campaigns/{campaign_id}")

    try:
        print("\nStep 1: Fetching current plan from API...")
        response = requests.get(
            f"{base_url}/campaigns/{campaign_id}",
            headers={"Authorization": f"Bearer {session_token}"},
            timeout=30
        )

        print(f"  - Response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if data.get('success'):
                current_plan_dict = data['data'].get('current_plan')

                if not current_plan_dict:
                    print("\n✗ No Current Plan Found")
                    print(f"  - Campaign '{campaign_id}' has no current plan")
                    print(f"  - Create a plan using MediaPlanPy SDK")
                    return None

                print(f"  - Current plan found")

                print("\nStep 2: Converting JSON to MediaPlan object...")
                media_plan = MediaPlan.from_dict(current_plan_dict)

                print("  - MediaPlan object created")

                print("\n✓ Media Plan Loaded Successfully")

                print("\nMedia Plan Information:")
                print(f"  - Media Plan ID: {media_plan.meta.id}")
                print(f"  - Name: {media_plan.meta.name}")
                print(f"  - Schema version: {media_plan.meta.schema_version}")
                print(f"  - Created by: {media_plan.meta.created_by_name}")
                print(f"  - Created at: {media_plan.meta.created_at}")

                print("\nCampaign Information:")
                print(f"  - Campaign ID: {media_plan.campaign.id}")
                print(f"  - Campaign name: {media_plan.campaign.name}")
                print(f"  - Budget: ${media_plan.campaign.budget_total:,.0f} {media_plan.campaign.budget_currency}")
                print(f"  - Period: {media_plan.campaign.start_date} to {media_plan.campaign.end_date}")

                print("\nLine Items:")
                print(f"  - Total line items: {len(media_plan.lineitems)}")
                if media_plan.lineitems:
                    print(f"  - First 3 line items:")
                    for i, lineitem in enumerate(media_plan.lineitems[:3], 1):
                        print(f"    {i}. {lineitem.name} (ID: {lineitem.id})")

                print("\nv3.0 Features Available:")
                if media_plan.campaign.target_audiences:
                    print(f"  - Target audiences: {len(media_plan.campaign.target_audiences)} configured")
                if media_plan.campaign.target_locations:
                    print(f"  - Target locations: {len(media_plan.campaign.target_locations)} configured")

                print("\nNext Steps:")
                print("  1. Inspect plan details: plan.meta, plan.campaign, plan.lineitems")
                print("  2. Edit plan using MediaPlanPy SDK methods")
                print("  3. Save changes: import_media_plan_to_api()")
                print("  4. Export locally: plan.save('/path/to/file.json')")

                print("\n" + "=" * 80)
                return media_plan
            else:
                print(f"\n✗ Failed to Load Plan")
                print(f"  - Error: {data.get('message', 'Unknown error')}")
                return None

        elif response.status_code == 403:
            print(f"\n✗ Access Denied")
            print(f"  - You do not have permission to access this campaign")
            return None

        elif response.status_code == 404:
            print(f"\n✗ Campaign Not Found")
            print(f"  - Campaign ID '{campaign_id}' does not exist")
            return None

        else:
            print(f"\n✗ Request Failed")
            print(f"  - HTTP Status: {response.status_code}")
            try:
                error_data = response.json()
                print(f"  - Error: {error_data.get('message', 'Unknown error')}")
            except:
                print(f"  - Response: {response.text[:200]}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Request Error")
        print(f"  - Error: {str(e)}")
        return None

    except Exception as e:
        print(f"\n✗ Unexpected Error")
        print(f"  - Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


# =============================================================================
# EXAMPLE 6: IMPORT MEDIA PLAN TO API
# =============================================================================

def import_media_plan_to_api(
    session_token: str,
    media_plan: MediaPlan,
    base_url: str = API_BASE_URL
) -> Optional[str]:
    """
    Import/upload a MediaPlan object to the API server.

    Use Case:
        Upload a new media plan or updated version to the API server.
        The plan is validated, imported, and automatically set as the
        current plan for its campaign.

    Import Process:
        1. MediaPlan object is converted to JSON
        2. JSON is saved to temporary file
        3. File is uploaded via multipart form-data
        4. Server validates and imports the plan
        5. Plan is set as current for the campaign
        6. Temporary file is cleaned up

    Args:
        session_token: Session token from authenticate_with_api()
        media_plan: MediaPlan object to import
        base_url: API server base URL (default: https://api.planmatic.io)

    Returns:
        New plan ID if successful, None otherwise

    File Formats Supported:
        - JSON (.json) - Recommended for API import
        - Excel (.xlsx) - Also supported by API

    Automatic Actions:
        - Plan is validated against v3.0 schema
        - Plan is set as current for its campaign
        - Previous current plan remains but is no longer current
        - Plan is saved to workspace storage

    Next Steps:
        - Verify import: load_media_plan_from_api(campaign_id)
        - View plan in UI/dashboard
        - Continue editing if needed
    """
    print("\n" + "=" * 80)
    print("IMPORTING MEDIA PLAN TO API")
    print("=" * 80)

    print("\nMedia Plan Information:")
    print(f"  - Media Plan ID: {media_plan.meta.id}")
    print(f"  - Campaign ID: {media_plan.campaign.id}")
    print(f"  - Campaign name: {media_plan.campaign.name}")
    print(f"  - Line items: {len(media_plan.lineitems)}")
    print(f"  - Schema version: {media_plan.meta.schema_version}")

    temp_json_path = None

    try:
        print("\nStep 1: Converting MediaPlan to JSON...")
        plan_dict = media_plan.to_dict()
        print("  - Conversion successful")

        print("\nStep 2: Creating temporary JSON file...")
        temp_fd, temp_json_path = tempfile.mkstemp(suffix='.json', prefix='mediaplan_')
        print(f"  - Temporary file: {temp_json_path}")

        print("\nStep 3: Writing JSON to file...")
        with os.fdopen(temp_fd, 'w') as f:
            json.dump(plan_dict, f, indent=2, default=str)
        print(f"  - File size: {os.path.getsize(temp_json_path) / 1024:.1f} KB")

        print("\nStep 4: Uploading to API server...")
        with open(temp_json_path, 'rb') as f:
            files = {'file': ('mediaplan.json', f, 'application/json')}

            response = requests.post(
                f"{base_url}/plans/import",
                headers={"Authorization": f"Bearer {session_token}"},
                files=files,
                timeout=60
            )

        print(f"  - Response status: {response.status_code}")

        if response.status_code == 200:
            result_data = response.json()

            if result_data.get('success'):
                imported_plan = result_data['data'].get('imported_plan', {})
                new_plan_id = imported_plan.get('plan_id')

                print("\n✓ Media Plan Imported Successfully")

                print("\nImported Plan Details:")
                print(f"  - Plan ID: {new_plan_id}")
                print(f"  - Campaign ID: {imported_plan.get('campaign_id', 'N/A')}")
                print(f"  - Is current: {imported_plan.get('is_current', False)}")
                print(f"  - Line items: {imported_plan.get('lineitem_count', 0)}")

                print("\nAutomatic Actions Performed:")
                print("  - Plan validated against schema v3.0")
                print("  - Plan saved to workspace storage")
                print("  - Plan set as current for campaign")
                print("  - Previous current plan (if any) is no longer current")

                print("\nNext Steps:")
                print("  1. Verify plan: load_media_plan_from_api(campaign_id)")
                print("  2. View plan in dashboard/UI")
                print("  3. Export if needed: GET /plans/{plan_id}/export")

                print("\n" + "=" * 80)
                return new_plan_id
            else:
                print(f"\n✗ Import Failed")
                print(f"  - Error: {result_data.get('message', 'Unknown error')}")
                if 'details' in result_data:
                    print(f"  - Details: {result_data['details']}")
                return None

        else:
            print(f"\n✗ Import Failed")
            print(f"  - HTTP Status: {response.status_code}")
            try:
                error_data = response.json()
                print(f"  - Error: {error_data.get('message', 'Unknown error')}")
                if 'details' in error_data:
                    print(f"  - Details: {error_data['details']}")
            except:
                print(f"  - Response: {response.text[:200]}")
            return None

    except Exception as e:
        print(f"\n✗ Error Importing Media Plan")
        print(f"  - Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        # Clean up temporary file
        if temp_json_path and os.path.exists(temp_json_path):
            try:
                os.unlink(temp_json_path)
                print("\nStep 5: Cleaned up temporary file")
            except Exception as cleanup_error:
                print(f"\nWarning: Failed to cleanup temp file: {cleanup_error}")


# =============================================================================
# EXAMPLE 7: COMPLETE WORKFLOW
# =============================================================================

def complete_api_workflow_example():
    """
    Demonstrate complete workflow: authenticate, load workspace, load plan, edit, and import.

    Use Case:
        End-to-end example showing the full API interaction lifecycle.
        This demonstrates how to integrate all API operations in a typical workflow.

    Workflow Steps:
        1. Show API key request instructions
        2. Authenticate with API key
        3. Load workspace
        4. List campaigns
        5. Load current media plan from campaign
        6. Edit media plan (example modification)
        7. Import modified plan back to API

    Prerequisites:
        - Set PLANMATIC_API_KEY environment variable
        - Set PLANMATIC_WORKSPACE_ID environment variable
        - Have at least one campaign with a current plan

    Error Handling:
        - Each step validates success before proceeding
        - Clear error messages guide troubleshooting
        - Workflow stops at first failure

    Next Steps:
        - Adapt this workflow for your use case
        - Add custom business logic between steps
        - Integrate with other systems and tools
    """
    print("\n" + "=" * 80)
    print("COMPLETE API WORKFLOW EXAMPLE")
    print("=" * 80)

    # Step 1: Show API key instructions (informational only)
    print("\n" + "=" * 80)
    print("STEP 1: API KEY SETUP (Informational)")
    print("=" * 80)
    print("Before running this workflow, ensure you have:")
    print("  - Valid API key from administrator")
    print("  - Environment variables set:")
    print("    - PLANMATIC_API_KEY")
    print("    - PLANMATIC_WORKSPACE_ID")
    print("\nTo see detailed instructions, run:")
    print("  show_api_key_request_instructions()")

    # Get credentials from environment
    api_key = os.environ.get("PLANMATIC_API_KEY")
    workspace_id = os.environ.get("PLANMATIC_WORKSPACE_ID")

    if not api_key:
        print("\n✗ ERROR: PLANMATIC_API_KEY environment variable not set")
        print("Please set it before running this example:")
        print("  export PLANMATIC_API_KEY='your_api_key_here'")
        return

    if not workspace_id:
        print("\n✗ ERROR: PLANMATIC_WORKSPACE_ID environment variable not set")
        print("Please set it before running this example:")
        print("  export PLANMATIC_WORKSPACE_ID='your_workspace_id_here'")
        return

    # Step 2: Authenticate
    print("\n" + "=" * 80)
    print("STEP 2: AUTHENTICATION")
    print("=" * 80)
    session_token = authenticate_with_api(api_key)

    if not session_token:
        print("\n✗ Workflow stopped: Authentication failed")
        return

    # Step 3: Load workspace
    print("\n" + "=" * 80)
    print("STEP 3: LOAD WORKSPACE")
    print("=" * 80)
    workspace_loaded = load_workspace_from_api(session_token, workspace_id)

    if not workspace_loaded:
        print("\n✗ Workflow stopped: Workspace load failed")
        return

    # Step 4: List campaigns
    print("\n" + "=" * 80)
    print("STEP 4: LIST CAMPAIGNS")
    print("=" * 80)
    campaigns = list_campaigns_from_api(session_token)

    if not campaigns or len(campaigns) == 0:
        print("\n✗ Workflow stopped: No campaigns found")
        return

    # Select first campaign for demo
    campaign_id = campaigns[0].get('campaign_id')
    print(f"\nSelected campaign for demo: {campaign_id}")

    # Step 5: Load media plan
    print("\n" + "=" * 80)
    print("STEP 5: LOAD MEDIA PLAN")
    print("=" * 80)
    media_plan = load_media_plan_from_api(session_token, campaign_id)

    if not media_plan:
        print("\n✗ Workflow stopped: Media plan load failed")
        return

    # Step 6: Edit media plan (example modification)
    print("\n" + "=" * 80)
    print("STEP 6: EDIT MEDIA PLAN (Example)")
    print("=" * 80)
    print("Making example modification to media plan...")

    # Example edit: Update plan name
    original_name = media_plan.meta.name
    media_plan.meta.name = f"{original_name} (API Updated)"

    print(f"  - Original name: {original_name}")
    print(f"  - Updated name: {media_plan.meta.name}")
    print("  - Note: In practice, you would make meaningful edits here")

    # Step 7: Import modified plan
    print("\n" + "=" * 80)
    print("STEP 7: IMPORT MODIFIED PLAN")
    print("=" * 80)
    new_plan_id = import_media_plan_to_api(session_token, media_plan)

    if not new_plan_id:
        print("\n✗ Workflow stopped: Media plan import failed")
        return

    # Workflow complete
    print("\n" + "=" * 80)
    print("WORKFLOW COMPLETE")
    print("=" * 80)
    print("\n✓ All steps completed successfully!")
    print(f"\nResults:")
    print(f"  - Authenticated with API")
    print(f"  - Loaded workspace: {workspace_id}")
    print(f"  - Found {len(campaigns)} campaigns")
    print(f"  - Loaded plan from campaign: {campaign_id}")
    print(f"  - Made example modifications")
    print(f"  - Imported new plan: {new_plan_id}")

    print("\n" + "=" * 80)


# =============================================================================
# INTERACTIVE WORKFLOW
# =============================================================================

def interactive_workflow():
    """
    Interactive guided workflow for API client operations.

    This function provides a step-by-step guided experience through the
    complete API workflow, from requesting an API key to importing an
    edited media plan.

    Workflow Steps:
        1. Display API key request instructions
        2. Prompt for API key (with validation)
        3. Authenticate with API server
        4. Prompt for workspace ID
        5. Load workspace
        6. List campaigns
        7. Load media plan from first campaign
        8. Edit media plan description
        9. Import edited plan back to API
        10. Display results

    User Interaction:
        - Interactive prompts guide user through each step
        - Option to skip if not ready
        - Clear error messages if steps fail
        - Validation at each stage

    Next Steps:
        - Adapt workflow for your specific use case
        - Integrate into automation scripts
        - Build custom dashboards and tools
    """
    print("\n" + "=" * 80)
    print("INTERACTIVE API WORKFLOW")
    print("=" * 80)
    print("\nThis interactive workflow will guide you through:")
    print("  1. API key management and authentication")
    print("  2. Workspace loading")
    print("  3. Campaign listing")
    print("  4. Media plan loading and editing")
    print("  5. Importing changes back to API")

    # Step 1: Show API key instructions
    print("\n" + "=" * 80)
    print("STEP 1: API KEY REQUEST INSTRUCTIONS")
    print("=" * 80)
    show_api_key_request_instructions()

    # Step 2: Ask if user has API key
    print("\n" + "=" * 80)
    print("STEP 2: API KEY CHECK")
    print("=" * 80)
    has_key = input("\nDo you have an API key? (y/n): ").strip().lower()

    if has_key != 'y':
        print("\n✗ Workflow Stopped")
        print("Please request an API key from your administrator before continuing.")
        print("Follow the instructions shown above in Step 1.")
        return

    # Step 3: Get API key from user
    print("\n" + "=" * 80)
    print("STEP 3: PROVIDE API KEY")
    print("=" * 80)
    print("\nAPI Key Format: plnmtc_<env>_<client_id>_<token>")
    print("Example: plnmtc_prod1_4_abc123def456...")
    api_key = input("\nEnter your API key: ").strip()

    if not api_key:
        print("\n✗ Workflow Stopped")
        print("API key is required to continue.")
        return

    if not api_key.startswith('plnmtc_'):
        print("\n⚠️  Warning: API key does not match expected format")
        print("Expected format: plnmtc_<env>_<client_id>_<token>")
        continue_anyway = input("Continue anyway? (y/n): ").strip().lower()
        if continue_anyway != 'y':
            print("\n✗ Workflow Stopped")
            return

    # Step 4: Authenticate
    print("\n" + "=" * 80)
    print("STEP 4: AUTHENTICATE WITH API SERVER")
    print("=" * 80)
    session_token = authenticate_with_api(api_key, API_BASE_URL)

    if not session_token:
        print("\n✗ Workflow Stopped: Authentication failed")
        print("Please verify your API key is correct and try again.")
        return

    # Step 5: Get workspace ID
    print("\n" + "=" * 80)
    print("STEP 5: PROVIDE WORKSPACE ID")
    print("=" * 80)
    print("\nWorkspace ID Format: workspace_<hash>")
    print("Example: workspace_49aa28ac")
    workspace_id = input("\nEnter workspace ID: ").strip()

    if not workspace_id:
        print("\n✗ Workflow Stopped")
        print("Workspace ID is required to continue.")
        return

    # Step 6: Load workspace
    print("\n" + "=" * 80)
    print("STEP 6: LOAD WORKSPACE")
    print("=" * 80)
    workspace_loaded = load_workspace_from_api(session_token, workspace_id, API_BASE_URL)

    if not workspace_loaded:
        print("\n✗ Workflow Stopped: Workspace load failed")
        print("Please verify the workspace ID is correct and you have access.")
        return

    # Step 7: List campaigns
    print("\n" + "=" * 80)
    print("STEP 7: LIST CAMPAIGNS")
    print("=" * 80)
    campaigns = list_campaigns_from_api(session_token, API_BASE_URL)

    if not campaigns or len(campaigns) == 0:
        print("\n✗ Workflow Stopped: No campaigns found in workspace")
        print("Please create campaigns using the Python API or web interface.")
        return

    # Step 8: Load media plan from first campaign
    print("\n" + "=" * 80)
    print("STEP 8: LOAD MEDIA PLAN")
    print("=" * 80)

    campaign_id = campaigns[0].get('campaign_id')
    campaign_name = campaigns[0].get('campaign_name', 'N/A')

    print(f"\nLoading current plan from first campaign:")
    print(f"  - Campaign ID: {campaign_id}")
    print(f"  - Campaign Name: {campaign_name}")

    media_plan = load_media_plan_from_api(session_token, campaign_id, API_BASE_URL)

    if not media_plan:
        print("\n✗ Workflow Stopped: Media plan load failed")
        print("The selected campaign may not have a current plan.")
        print("Please create a plan using the Python API.")
        return

    # Step 9: Edit media plan
    print("\n" + "=" * 80)
    print("STEP 9: EDIT MEDIA PLAN USING SDK")
    print("=" * 80)
    print("\nNow we'll edit the media plan using MediaPlanPy SDK methods.")
    print("This demonstrates the power of combining API and SDK.")

    # Show original values
    print("\nOriginal Values:")
    print(f"  - Plan name: {media_plan.meta.name}")
    print(f"  - Plan description: {media_plan.meta.comments or '(empty)'}")

    # Edit description to show API integration
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    original_description = media_plan.meta.comments or ""
    new_description = f"{original_description}\n\nEdited via API on {timestamp}"
    media_plan.meta.comments = new_description.strip()

    # Also update the name slightly to show it was edited
    original_name = media_plan.meta.name
    if "(API Edited)" not in original_name:
        media_plan.meta.name = f"{original_name} (API Edited)"

    print("\n✓ Media Plan Edited")
    print("\nUpdated Values:")
    print(f"  - Plan name: {media_plan.meta.name}")
    print(f"  - Plan description: {media_plan.meta.comments}")

    print("\nEdits made using MediaPlanPy SDK:")
    print("  - Updated meta.name to include '(API Edited)' suffix")
    print("  - Updated meta.comments with timestamp")
    print("  - All changes made locally using SDK methods")

    # Step 10: Import edited plan
    print("\n" + "=" * 80)
    print("STEP 10: IMPORT EDITED PLAN TO API")
    print("=" * 80)
    print("\nUploading edited media plan back to API server...")

    new_plan_id = import_media_plan_to_api(session_token, media_plan, API_BASE_URL)

    if not new_plan_id:
        print("\n✗ Workflow Stopped: Media plan import failed")
        print("Please check error messages above.")
        return

    # Success summary
    print("\n" + "=" * 80)
    print("✓ WORKFLOW COMPLETED SUCCESSFULLY!")
    print("=" * 80)

    print("\nWorkflow Summary:")
    print(f"  1. ✓ Authenticated with API server")
    print(f"  2. ✓ Loaded workspace: {workspace_id}")
    print(f"  3. ✓ Listed {len(campaigns)} campaigns")
    print(f"  4. ✓ Loaded plan from campaign: {campaign_name}")
    print(f"  5. ✓ Edited plan using MediaPlanPy SDK")
    print(f"  6. ✓ Imported edited plan: {new_plan_id}")

    print("\nWhat Happened:")
    print("  - Original plan downloaded from API")
    print("  - Plan converted to MediaPlan SDK object")
    print("  - Plan edited using SDK methods locally")
    print("  - Edited plan uploaded back to API")
    print("  - New plan version created and set as current")

    print("\nNext Steps:")
    print("  1. View updated plan in web interface/dashboard")
    print("  2. Verify changes in plan description and name")
    print("  3. Adapt this workflow for your use case")
    print("  4. Integrate into automation scripts")

    print("\n" + "=" * 80)


# =============================================================================
# MAIN - RUN EXAMPLES
# =============================================================================

if __name__ == "__main__":
    """
    Run API client examples.

    Interactive Mode (Default):
        python examples_14_api_client.py

        This runs an interactive guided workflow that:
        - Shows API key request instructions
        - Prompts for API key and workspace ID
        - Walks through complete workflow step-by-step
        - Demonstrates loading, editing, and importing plans

    Individual Functions:
        You can also call individual example functions:
        - show_api_key_request_instructions()
        - authenticate_with_api(api_key)
        - load_workspace_from_api(session_token, workspace_id)
        - list_campaigns_from_api(session_token)
        - load_media_plan_from_api(session_token, campaign_id)
        - import_media_plan_to_api(session_token, media_plan)
        - complete_api_workflow_example() (uses environment variables)
    """

    print("=" * 80)
    print("MediaPlanPy Examples - API Client Interface")
    print("=" * 80)
    print("\nThis script demonstrates how to interact with a Planmatic API Server.")
    print("\nTwo modes available:")
    print("  1. Interactive Workflow (Guided, step-by-step)")
    print("  2. Individual Functions (For reference and custom usage)")

    print("\n" + "=" * 80)
    print("RUNNING: INTERACTIVE WORKFLOW")
    print("=" * 80)
    print("\nThis will guide you through a complete API workflow:")
    print("  - API authentication")
    print("  - Workspace loading")
    print("  - Campaign listing")
    print("  - Media plan loading and editing")
    print("  - Importing changes via API")

    print("\nPress Enter to start the interactive workflow...")
    print("(Or press Ctrl+C to exit)")

    try:
        input()
        interactive_workflow()
    except KeyboardInterrupt:
        print("\n\n✗ Workflow cancelled by user")
        print("\n" + "=" * 80)
        sys.exit(0)

    print("\n" + "=" * 80)
    print("ADDITIONAL EXAMPLES")
    print("=" * 80)
    print("\nYou can also call these functions individually:")
    print("  - show_api_key_request_instructions()")
    print("  - authenticate_with_api(api_key)")
    print("  - load_workspace_from_api(session_token, workspace_id)")
    print("  - list_campaigns_from_api(session_token)")
    print("  - load_media_plan_from_api(session_token, campaign_id)")
    print("  - import_media_plan_to_api(session_token, media_plan)")
    print("  - complete_api_workflow_example()  # Uses env variables")
    print("\n" + "=" * 80)
