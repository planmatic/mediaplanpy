"""
MediaPlanPy Examples - Manage Campaign

This script demonstrates campaign lifecycle management using MediaPlanPy SDK v3.0.11.
Shows archive, restore, and delete of an entire campaign.

The key idea to take away: a campaign has no independent existence in this data
model. There is no campaign file and no campaign record - list_campaigns() derives
its rows entirely from media plan files. So a campaign is "archived" exactly when
every one of its plans is, it ceases to exist when its last plan is deleted, and
every campaign lifecycle operation is a CASCADE OVER ITS PLANS.

This script is written to make that observable rather than just assertable: each
step prints whether the campaign is still visible in list_campaigns() before and
after, so you can see the derived state change.

v3.0.11 Features Demonstrated:
- archive_campaign() to archive every plan in a campaign at once
- restore_campaign() to bring the whole campaign back
- delete_campaign() with its dry_run=True default
- The plans_changed / plans_skipped / plans_failed result envelope
- Campaign visibility in list_campaigns() as a derived, not stored, property
- Using plans_changed for a precise, non-lossy restore

Prerequisites:
- MediaPlanPy SDK v3.0.11+ installed
- Workspace created (see examples_01_create_workspace.py)
- Media plans created (see examples_03_create_mediaplan.py)

How to Run:
1. First run examples_01_create_workspace.py to create a workspace
2. Then run examples_03_create_mediaplan.py to create media plans
3. Update WORKSPACE_ID below, or provide when prompted
4. Open this file in your IDE
5. Run the entire script: python examples_17_manage_campaign.py

Next Steps After Running:
- Use campaign archival for completed campaigns instead of looping over plans
- Always preview a campaign delete before running it for real
- Persist plans_changed if you need an exact inverse of an archive
"""

from datetime import date, datetime
from decimal import Decimal

from mediaplanpy.workspace import WorkspaceManager
from mediaplanpy.models import MediaPlan, Campaign, LineItem, Meta
from mediaplanpy.exceptions import CampaignNotFoundError


# ============================================================================
# USER CONFIGURATION
# Update these values after creating workspace and media plans
# ============================================================================

# Copy the "Workspace ID" from examples_01_create_workspace.py output
WORKSPACE_ID = "workspace_xxxxxxxx"

# ============================================================================


def get_configuration_value(config_name, prompt_message, example_value):
    """
    Get configuration value - either from constant or interactive user input.

    Args:
        config_name: Name of the configuration constant (e.g., 'WORKSPACE_ID')
        prompt_message: Message to show when prompting user
        example_value: Example value to show user

    Returns:
        Configuration value or None if user chooses to skip
    """
    if config_name == 'WORKSPACE_ID':
        current_value = WORKSPACE_ID
    else:
        return None

    if "xxxxxxxx" not in current_value:
        return current_value

    print(f"\nConfiguration needed: {config_name}")
    print(f"Example: {example_value}")
    print(f"\nOptions:")
    print(f"  1. Enter the value now")
    print(f"  2. Type 'skip' to skip")
    print(f"  3. Update the constant at the top of this file and re-run")

    user_input = input(f"\n{prompt_message}: ").strip()

    if user_input.lower() == 'skip':
        print("Skipping.")
        return None

    if user_input:
        return user_input

    print("No value provided. Skipping.")
    return None


def load_workspace():
    """
    Load workspace once for use across all examples.

    Returns:
        WorkspaceManager or None if config not provided
    """
    workspace_id = get_configuration_value(
        'WORKSPACE_ID',
        'Enter workspace ID',
        'workspace_abc12345'
    )

    if workspace_id is None:
        return None

    print(f"\nLoading workspace: {workspace_id}")
    manager = WorkspaceManager()
    manager.load(workspace_id=workspace_id)
    print(f"✓ Workspace loaded successfully")

    return manager


# ============================================================================
# HELPERS
# ============================================================================

def campaign_is_visible(manager, campaign_id, include_archived=False):
    """
    Whether a campaign appears in list_campaigns().

    This is the whole point of the examples below: campaign visibility is DERIVED
    from its plans' archive state, so it changes as a side effect of plan-level
    operations rather than because a campaign flag was set.
    """
    rows = manager.list_campaigns(
        include_stats=False,
        include_archived=include_archived,
        return_dataframe=False
    )
    return campaign_id in {row["campaign_id"] for row in rows}


def show_campaign_visibility(manager, campaign_id, label):
    """Print the campaign's visibility in both listings."""
    default_view = campaign_is_visible(manager, campaign_id)
    archived_view = campaign_is_visible(manager, campaign_id, include_archived=True)

    print(f"\n  {label}")
    print(f"    list_campaigns()                       -> {'visible' if default_view else 'NOT visible'}")
    print(f"    list_campaigns(include_archived=True)  -> {'visible' if archived_view else 'NOT visible'}")


def print_result(result):
    """Print the shared cascade result envelope."""
    print(f"\n  Result:")
    print(f"    success:        {result['success']}")
    print(f"    plans_total:    {result['plans_total']}")
    print(f"    plans_changed:  {result['plans_changed']}")
    print(f"    plans_skipped:  {[s['media_plan_id'] for s in result['plans_skipped']]}")
    print(f"    plans_failed:   {[f['media_plan_id'] for f in result['plans_failed']]}")


def create_test_campaign(manager, campaign_id, plan_count=3):
    """
    Create a campaign with several plan versions, one of them current.

    Multiple plans matter here: with a single plan you cannot see the difference
    between "archive this plan" and "archive this campaign".
    """
    print(f"\nCreating test campaign '{campaign_id}' with {plan_count} plans...")

    for index in range(plan_count):
        plan_id = f"MP_{campaign_id}_{index + 1}"
        plan = MediaPlan(
            meta=Meta(
                id=plan_id,
                schema_version="v3.0",
                name=f"Version {index + 1}",
                created_by_name="Examples Script",
                created_at=datetime.now(),
                # The FIRST plan is the campaign's current plan. Archiving a
                # campaign has to handle it, which is why archive_campaign()
                # passes allow_current=True internally.
                is_current=(index == 0),
            ),
            campaign=Campaign(
                id=campaign_id,
                name="Campaign Lifecycle Example",
                objective="awareness",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000"),
            ),
            lineitems=[
                LineItem(
                    id=f"LI_{plan_id}",
                    name="Display Line Item",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 6, 30),
                    cost_total=Decimal("25000"),
                    channel="display",
                    vehicle="Programmatic",
                )
            ],
        )
        plan.save(manager)
        print(f"  ✓ Created {plan_id} (is_current={index == 0})")

    return campaign_id


# ============================================================================
# EXAMPLES
# ============================================================================

def archive_and_restore_campaign(manager):
    """
    Archive a whole campaign, then restore it.

    Before v3.0.11 this had to be done by the caller as a loop over the campaign's
    plans - and that loop could not complete, because MediaPlan.archive() refuses
    to archive the campaign's current plan without allow_current=True.
    archive_campaign() handles that internally.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Archive and Restore a Campaign")
    print("=" * 60)
    print("""
    Campaigns have no stored archived state. A campaign disappears from
    list_campaigns() only once EVERY one of its plans is archived - so
    archive_campaign() archives all of them, the current plan included.

    archive() with allow_current=True PRESERVES is_current rather than
    clearing it, so restore_campaign() reinstates the same current plan
    with no re-election step.
    """)

    campaign_id = create_test_campaign(manager, "CAM_EXAMPLE_ARCHIVE")
    show_campaign_visibility(manager, campaign_id, "Before archiving:")

    print("\n  Calling archive_campaign()...")
    result = manager.archive_campaign(campaign_id)
    print_result(result)
    print(f"    campaign_now_hidden: {result['campaign_now_hidden']}")

    show_campaign_visibility(manager, campaign_id, "After archiving:")
    print("\n  ↑ Note the campaign is HIDDEN, not gone - still there with "
          "include_archived=True.")

    # Archiving again is safe: already-archived plans are skipped, not errored.
    print("\n  Calling archive_campaign() a second time (idempotency check)...")
    repeat = manager.archive_campaign(campaign_id)
    print(f"    success: {repeat['success']}, "
          f"changed: {len(repeat['plans_changed'])}, "
          f"skipped: {len(repeat['plans_skipped'])} (already_archived)")

    print("\n  Calling restore_campaign()...")
    restored = manager.restore_campaign(campaign_id)
    print_result(restored)
    show_campaign_visibility(manager, campaign_id, "After restoring:")

    current = manager.list_mediaplans(
        filters={"campaign_id": campaign_id, "meta_is_current": [True]},
        include_stats=False, return_dataframe=False
    )
    print(f"\n  Current plan after restore: "
          f"{[row['meta_id'] for row in current]} (no re-election needed)")

    return campaign_id


def precise_restore_with_plans_changed(manager):
    """
    restore_campaign() restores EVERY archived plan - including plans archived
    individually before the campaign was archived.

    Nothing in the data model records why a plan was archived, so that loss is
    unavoidable without a schema change, and it is documented rather than hidden.
    When it matters, persist archive_campaign()'s plans_changed list and restore
    exactly those plans instead.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Precise Restore Using plans_changed")
    print("=" * 60)
    print("""
    Scenario: one plan was archived on its own weeks ago. Later the whole
    campaign is archived. Should restoring the campaign bring that older
    plan back too?

    restore_campaign() says yes (it cannot tell the two apart). If you need
    it to say no, use the plans_changed list instead.
    """)

    campaign_id = create_test_campaign(manager, "CAM_EXAMPLE_PRECISE")

    # Someone archives one old version individually.
    old_version_id = f"MP_{campaign_id}_3"
    print(f"\n  Archiving {old_version_id} individually (an old version)...")
    MediaPlan.load(manager, media_plan_id=old_version_id).archive(manager)

    print("\n  Now archiving the whole campaign...")
    result = manager.archive_campaign(campaign_id)
    print(f"    plans_changed (archived by THIS call): {result['plans_changed']}")
    print(f"    plans_skipped (already archived):      "
          f"{[s['media_plan_id'] for s in result['plans_skipped']]}")

    print("\n  Precise restore - only what the campaign archive actually changed:")
    for plan_id in result["plans_changed"]:
        MediaPlan.load(manager, media_plan_id=plan_id).restore(manager)
        print(f"    ✓ Restored {plan_id}")

    still_archived = manager.list_mediaplans(
        filters={"campaign_id": campaign_id, "meta_is_archived": [True]},
        include_stats=False, include_archived=True, return_dataframe=False
    )
    print(f"\n    Still archived (as intended): "
          f"{[row['meta_id'] for row in still_archived]}")
    print("\n  ↑ restore_campaign() would have restored this one too.")

    return campaign_id


def delete_campaign_example(manager, campaign_ids):
    """
    Delete campaigns, previewing first.

    delete_campaign() defaults to dry_run=True, unlike MediaPlan.delete() which
    defaults to dry_run=False. The cascade is far more destructive, so the safer
    default was chosen for the new method.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Delete a Campaign (dry run first)")
    print("=" * 60)
    print("""
    delete_campaign() removes every media plan in the campaign, which
    removes the campaign itself - unlike archive, this is NOT recoverable.

    dry_run defaults to True here. The preview lists the plan ids it would
    delete, not just a count, so it is actually reviewable.

    Note it deletes the CURRENT plan too, with no override flag: a campaign
    cannot be deleted while keeping its current plan.
    """)

    for campaign_id in campaign_ids:
        print(f"\n  --- {campaign_id} ---")
        show_campaign_visibility(manager, campaign_id, "Before delete:")

        print("\n  Step 1: preview (dry_run defaults to True)")
        preview = manager.delete_campaign(campaign_id)
        print(f"    dry_run:          {preview['dry_run']}")
        print(f"    plans_to_delete:  {preview['plans_to_delete']}")
        print(f"    files_found:      {preview['files_found']}")
        print(f"    files_deleted:    {preview['files_deleted']}  <- nothing removed yet")

        print("\n  Step 2: delete for real (dry_run=False)")
        result = manager.delete_campaign(campaign_id, dry_run=False)
        print(f"    success:          {result['success']}")
        print(f"    files_deleted:    {result['files_deleted']}")
        print(f"    campaign_deleted: {result['campaign_deleted']}")

        show_campaign_visibility(manager, campaign_id, "After delete:")
        print("\n  ↑ Gone from BOTH listings - a deleted campaign is not an "
              "archived one.")


def handle_unknown_campaign(manager):
    """All three methods raise CampaignNotFoundError for an unknown campaign."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Unknown Campaign")
    print("=" * 60)
    print("""
    "Campaign not found" means "no media plan carries this campaign_id" -
    which, in a model where campaigns are derived from plans, is the only
    thing it can mean. CampaignNotFoundError is distinct from StorageError
    so callers can map it to a 404 without inspecting messages.
    """)

    try:
        manager.archive_campaign("CAM_DOES_NOT_EXIST")
    except CampaignNotFoundError as e:
        print(f"\n  ✓ CampaignNotFoundError raised as expected:")
        print(f"    {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("MediaPlanPy Examples - Manage Campaign")
    print("=" * 60)

    print("\nLoading workspace...")
    manager = load_workspace()

    if manager is None:
        print("\nNo workspace loaded. Exiting.")
        print("\nTo run these examples:")
        print("  1. Run examples_01_create_workspace.py first")
        print("  2. Update WORKSPACE_ID at top of this file")
        print("  3. Or provide value when prompted")
        exit(0)

    archived_campaign = archive_and_restore_campaign(manager)
    precise_campaign = precise_restore_with_plans_changed(manager)

    handle_unknown_campaign(manager)

    # Cleanup: delete the campaigns this script created.
    delete_campaign_example(manager, [archived_campaign, precise_campaign])

    print("\n" + "=" * 60)
    print("Manage Campaign Examples Completed!")
    print("=" * 60)

    print(f"\nWhat We Demonstrated:")
    print(f"  1. Campaign visibility is DERIVED from its plans, not stored")
    print(f"  2. archive_campaign() cascades over every plan, current one included")
    print(f"  3. is_current survives the archive, so restore needs no re-election")
    print(f"  4. Archiving twice is safe - already-archived plans are skipped")
    print(f"  5. restore_campaign() restores ALL archived plans (including any")
    print(f"     archived individually beforehand)")
    print(f"  6. plans_changed gives you a precise inverse when that matters")
    print(f"  7. delete_campaign() defaults to dry_run=True and previews plan ids")
    print(f"  8. A deleted campaign leaves both listings; an archived one does not")

    print(f"\nNext Steps:")
    print(f"  - Replace any client-side 'loop over the campaign's plans' code")
    print(f"  - Always preview a campaign delete before running it for real")
    print(f"  - Persist plans_changed if you need an exact inverse of an archive")
    print(f"  - Remember: documents/measurements your application attaches to a")
    print(f"    campaign live outside the SDK and are NOT removed by delete_campaign()")
