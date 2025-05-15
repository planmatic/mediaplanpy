"""
Example demonstrating how to use the workspace query methods.

This script shows how to use the new list_campaigns, list_mediaplans, and
list_lineitems methods to query and analyze media plans across a workspace.
"""

import os
import datetime
import json
from mediaplanpy.workspace import WorkspaceManager


def print_json(data):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=2, default=str))


# Initialize and load workspace
workspace_path = "workspace.json"  # Change to your workspace path
workspace = WorkspaceManager(workspace_path)
workspace.load()

print("Workspace loaded successfully from:", workspace_path)

# Example 1: List all campaigns
print("\n=== List all campaigns ===")
campaigns = workspace.list_campaigns()
print(f"Found {len(campaigns)} campaigns")
if campaigns:
    print("First campaign:")
    print_json(campaigns[0])

# Example 2: Filter campaigns by budget
print("\n=== List campaigns with budget over $50,000 ===")
high_budget_campaigns = workspace.list_campaigns(filters={
    'campaign_budget_total': {'min': 50000}
})
print(f"Found {len(high_budget_campaigns)} campaigns with budget over $50,000")
if high_budget_campaigns:
    print("Campaign names:")
    for campaign in high_budget_campaigns:
        print(f"- {campaign['campaign_name']} (${campaign['campaign_budget_total']})")

# Example 3: List media plans created in a specific date range
print("\n=== List media plans created in the last 30 days ===")
thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
recent_plans = workspace.list_mediaplans(filters={
    'meta_created_at': {'min': thirty_days_ago}
})
print(f"Found {len(recent_plans)} media plans created in the last 30 days")
if recent_plans:
    print("Plan names and creation dates:")
    for plan in recent_plans:
        print(f"- {plan.get('meta_name', 'Unnamed')} (created: {plan['meta_created_at']})")

# Example 4: Get line items for a specific channel and analyze with pandas
print("\n=== Analyze social media line items with pandas ===")
social_items_df = workspace.list_lineitems(
    filters={'lineitem_channel': 'social'},
    return_dataframe=True
)

if not social_items_df.empty:
    print(f"Found {len(social_items_df)} social media line items")

    # Calculate average cost by social media platform
    if 'lineitem_vehicle' in social_items_df.columns and 'lineitem_cost_total' in social_items_df.columns:
        avg_cost_by_platform = social_items_df.groupby('lineitem_vehicle')['lineitem_cost_total'].agg(
            ['mean', 'count']).reset_index()
        avg_cost_by_platform.columns = ['Platform', 'Avg Cost', 'Count']
        print("\nAverage cost by social media platform:")
        print(avg_cost_by_platform.to_string(index=False))
else:
    print("No social media line items found in workspace")

# Example 5: Compare metrics across campaigns
print("\n=== Compare metrics across campaigns ===")
campaigns_df = workspace.list_campaigns(return_dataframe=True)

if not campaigns_df.empty and 'stat_total_cost' in campaigns_df.columns:
    # Sort by total cost
    sorted_by_cost = campaigns_df.sort_values('stat_total_cost', ascending=False)

    # Select relevant columns for output
    display_cols = ['campaign_name', 'campaign_objective', 'stat_total_cost', 'stat_lineitem_count']
    available_cols = [col for col in display_cols if col in sorted_by_cost.columns]

    print("Campaigns ranked by total cost:")
    print(sorted_by_cost[available_cols].head(5).to_string(index=False))