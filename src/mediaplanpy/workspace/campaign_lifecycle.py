"""
Campaign lifecycle operations for mediaplanpy.

Campaigns have no independent existence in this data model. There is no campaign
file, no campaign row, no campaign record to flip a flag on: list_campaigns()
(workspace/query.py) derives campaign rows entirely from media plan files, keeping
one row per campaign_id taken from that campaign's current/latest plan, after
archived *plans* have been filtered out at the SQL level.

Three consequences drive everything in this module:

1. A campaign's "archived" state is derived, not stored. A campaign only drops out
   of a default list_campaigns() listing once EVERY one of its plans is archived --
   archiving some plans leaves the campaign fully visible, sourced from a survivor.
2. A campaign ceases to exist when its last plan is deleted.
3. Therefore every campaign lifecycle operation is a cascade over that campaign's
   media plans, never a state transition on a campaign.

That is not an implementation shortcut -- it is the only semantics the storage
model can express. Do not "fix" it later by inventing a campaign record.

These functions are patched onto WorkspaceManager at import time (see
patch_workspace_manager() at the bottom, and workspace/__init__.py), the same
mechanism workspace/query.py uses. They live in their own module rather than in
query.py because query.py is read-only querying and this is write/destructive.

None of these operations is atomic. There is no transaction spanning file storage,
Parquet and PostgreSQL, so a cascade that fails partway leaves some plans changed
and some not. That is a real outcome, and it is reported rather than hidden: every
function returns per-plan lists (plans_changed / plans_skipped / plans_failed) and
sets success=False if anything failed. Retrying is safe -- an already-archived plan
is skipped, not re-archived or errored.
"""

import logging
from typing import Any, Dict, List, Optional

from mediaplanpy.exceptions import CampaignNotFoundError

logger = logging.getLogger("mediaplanpy.workspace.campaign_lifecycle")


def _campaign_plan_rows(self, campaign_id: str) -> List[Dict[str, Any]]:
    """
    Every media plan belonging to a campaign, archived ones included.

    include_archived=True is required, not incidental: an archive cascade must see
    already-archived plans to skip them rather than re-archiving, a restore cascade
    exists only to act on them, and a delete cascade must remove them too.

    Raises:
        CampaignNotFoundError: The campaign has no media plans at all, which -- in a
            model where campaigns are derived from plans -- is what "no such
            campaign" means.
    """
    if not campaign_id or not str(campaign_id).strip():
        raise CampaignNotFoundError("campaign_id is required and cannot be empty.")

    plans = self.list_mediaplans(
        filters={"campaign_id": campaign_id},
        include_stats=False,
        include_archived=True,
        return_dataframe=False,
    )

    if not plans:
        raise CampaignNotFoundError(
            f"No media plans found for campaign '{campaign_id}'. Campaigns are derived "
            f"from their media plans, so a campaign with no plans does not exist in "
            f"this workspace."
        )
    return plans


def _load_plan(self, plan_row: Dict[str, Any]):
    """Load the full MediaPlan for one row returned by list_mediaplans()."""
    from mediaplanpy.models import MediaPlan

    return MediaPlan.load(
        self,
        media_plan_id=plan_row["meta_id"],
        validate_version=True,
        auto_migrate=True,
    )


def _new_result(campaign_id: str, operation: str, plans_total: int) -> Dict[str, Any]:
    """The result envelope shared by all three cascades."""
    return {
        "campaign_id": campaign_id,
        "operation": operation,
        "success": False,
        "plans_total": plans_total,
        # The plan ids this call actually transitioned. Callers that want a precise,
        # non-lossy inverse operation later should persist this -- see the DEC-1 note
        # in archive_campaign()'s docstring.
        "plans_changed": [],
        "plans_skipped": [],   # [{"media_plan_id": ..., "reason": ...}]
        "plans_failed": [],    # [{"media_plan_id": ..., "error": ...}]
    }


def archive_campaign(self, campaign_id: str) -> Dict[str, Any]:
    """
    Archive every media plan in a campaign, so the campaign itself drops out of
    default (non-archived) list_campaigns() results.

    Campaigns have no stored archived state -- a campaign is "archived" exactly when
    all of its plans are (see this module's docstring). This therefore archives ALL
    of the campaign's plans, the current one included, via
    MediaPlan.archive(allow_current=True). That override preserves is_current rather
    than clearing it, so restore_campaign() reinstates the same current plan with no
    re-election step; MediaPlan.archive()'s own docstring documents this as its
    intended use.

    Non-atomic and continue-on-error: one plan failing does not abandon the rest, and
    plans already archived are left untouched and reported as skipped (so re-running
    after a partial failure is safe).

    Args:
        campaign_id: The campaign whose plans should be archived.

    Returns:
        Dict with:
        - campaign_id, operation ("archive")
        - success: True only if no plan failed
        - plans_total: how many plans the campaign has
        - plans_changed: ids actually archived by THIS call
        - plans_skipped: [{media_plan_id, reason: "already_archived"}]
        - plans_failed: [{media_plan_id, error}]
        - campaign_now_hidden: whether the campaign is now absent from a default
          list_campaigns() listing

    Raises:
        CampaignNotFoundError: No media plans carry this campaign_id.
        WorkspaceInactiveError: The workspace is inactive.

    Example:
        >>> result = manager.archive_campaign("camp_123")
        >>> result["campaign_now_hidden"]
        True
        >>> # Precise inverse later, instead of restore_campaign()'s restore-all:
        >>> archived_by_us = result["plans_changed"]
    """
    self.check_workspace_active("campaign archival")

    plans = _campaign_plan_rows(self, campaign_id)
    result = _new_result(campaign_id, "archive", len(plans))
    result["campaign_now_hidden"] = False

    for row in plans:
        plan_id = row.get("meta_id")
        try:
            if row.get("meta_is_archived") is True:
                result["plans_skipped"].append(
                    {"media_plan_id": plan_id, "reason": "already_archived"}
                )
                continue

            plan = _load_plan(self, row)
            # allow_current=True is exactly the campaign-cascade case this parameter
            # was added for (mediaplanpy 3.0.5). A campaign cannot be archived
            # without archiving its current plan -- it has no other plans left to be
            # visible from.
            plan.archive(self, allow_current=True)
            result["plans_changed"].append(plan_id)
            logger.debug(f"Archived plan {plan_id} of campaign {campaign_id}")

        except Exception as e:
            # Deliberately broad: a cascade should make as much progress as it can,
            # and one unloadable or unsaveable plan must not strand the others.
            result["plans_failed"].append({"media_plan_id": plan_id, "error": str(e)})
            logger.error(f"Failed to archive plan {plan_id} of campaign {campaign_id}: {e}")

    result["success"] = not result["plans_failed"]
    result["campaign_now_hidden"] = result["success"]

    logger.info(
        f"Campaign '{campaign_id}' archive: {len(result['plans_changed'])} archived, "
        f"{len(result['plans_skipped'])} skipped, {len(result['plans_failed'])} failed "
        f"(of {result['plans_total']} plans)"
    )
    return result


def restore_campaign(self, campaign_id: str) -> Dict[str, Any]:
    """
    Restore every archived media plan in a campaign, bringing the campaign back into
    default list_campaigns() results.

    IMPORTANT -- this un-archives EVERY archived plan in the campaign, not only those
    archived by a previous archive_campaign() call. Nothing in the data model records
    why a plan was archived, so a plan a user archived on its own before the campaign
    was archived is restored too. This is a deliberate, accepted tradeoff (it avoids a
    schema change to track provenance); callers needing a precise inverse should
    persist archive_campaign()'s plans_changed list and restore those plans
    individually via MediaPlan.restore() instead of calling this.

    Plans that are not archived are left untouched and reported as skipped. If the
    campaign's current plan was archived with is_current preserved (which is what
    archive_campaign() does), it comes back as current with no re-election step.

    Args:
        campaign_id: The campaign whose plans should be restored.

    Returns:
        Same envelope as archive_campaign(), with operation "restore",
        plans_skipped reasons of "not_archived", and campaign_now_visible in place of
        campaign_now_hidden.

    Raises:
        CampaignNotFoundError: No media plans carry this campaign_id.
        WorkspaceInactiveError: The workspace is inactive.
    """
    self.check_workspace_active("campaign restoration")

    plans = _campaign_plan_rows(self, campaign_id)
    result = _new_result(campaign_id, "restore", len(plans))
    result["campaign_now_visible"] = False

    for row in plans:
        plan_id = row.get("meta_id")
        try:
            if row.get("meta_is_archived") is not True:
                result["plans_skipped"].append(
                    {"media_plan_id": plan_id, "reason": "not_archived"}
                )
                continue

            plan = _load_plan(self, row)
            plan.restore(self)
            result["plans_changed"].append(plan_id)
            logger.debug(f"Restored plan {plan_id} of campaign {campaign_id}")

        except Exception as e:
            result["plans_failed"].append({"media_plan_id": plan_id, "error": str(e)})
            logger.error(f"Failed to restore plan {plan_id} of campaign {campaign_id}: {e}")

    result["success"] = not result["plans_failed"]
    # A campaign is visible as long as at least one of its plans is not archived --
    # so it is back in default listings if anything was restored, or if a plan was
    # already unarchived to begin with.
    result["campaign_now_visible"] = bool(result["plans_changed"]) or bool(result["plans_skipped"])

    logger.info(
        f"Campaign '{campaign_id}' restore: {len(result['plans_changed'])} restored, "
        f"{len(result['plans_skipped'])} skipped, {len(result['plans_failed'])} failed "
        f"(of {result['plans_total']} plans)"
    )
    return result


def delete_campaign(
    self,
    campaign_id: str,
    dry_run: bool = True,
    include_database: bool = True,
) -> Dict[str, Any]:
    """
    Permanently delete every media plan in a campaign, which deletes the campaign --
    a campaign has no existence independent of its plans.

    Note dry_run defaults to True here, whereas MediaPlan.delete() defaults it to
    False. That divergence is deliberate rather than an oversight: this cascade is N
    times more destructive than deleting one plan, and being a new method it carries
    no backwards-compatibility obligation to the riskier default. Preview first, then
    call again with dry_run=False.

    There is deliberately no allow_current_plan_deletion parameter. Deleting a
    campaign means deleting all of its plans, its current plan included; a guard
    against that would make this method impossible to complete. (MediaPlan.delete()
    has no is_current guard of its own -- unlike archive() -- so nothing needs
    overriding here.)

    This does NOT touch anything outside mediaplanpy's own storage. Documents,
    measurements and other artefacts that consuming applications attach to a campaign
    live outside this SDK and are left pointing at a campaign that no longer exists;
    warning about those is the consuming application's job, since only it can see
    them.

    Args:
        campaign_id: The campaign to delete.
        dry_run: If True (default), report what would be deleted and delete nothing.
        include_database: Also delete each plan's database records, if configured.

    Returns:
        Same envelope as archive_campaign() (operation "delete"), except that the
        outcome fields differ by mode so that no field name claims something
        happened when it did not:

        Both modes:
        - dry_run: echoed back
        - plans_to_delete: every plan id in the campaign -- the INTENT, and the
          reviewable preview, since a dry run reporting only a count is not
          reviewable
        - plans_failed: plans that could not be deleted (or, on a dry run, could
          not be previewed)
        - files_found / files_deleted / database_rows_deleted: batch totals
          (files_deleted is 0 on a dry run)
        - campaign_deleted: whether the campaign is now gone entirely

        Dry run only:  files_to_delete -- the paths that WOULD be removed.
        Real run only: plans_changed   -- the ids actually deleted, matching the
                       meaning the field has in archive_campaign()/restore_campaign();
                       deleted_files  -- the paths actually removed.

        On a dry run, "previewed cleanly" is plans_to_delete minus plans_failed.

    Raises:
        CampaignNotFoundError: No media plans carry this campaign_id.
        WorkspaceInactiveError: The workspace is inactive.

    Example:
        >>> preview = manager.delete_campaign("camp_123")           # dry run
        >>> preview["plans_to_delete"]
        ['mp_a', 'mp_b']
        >>> manager.delete_campaign("camp_123", dry_run=False)      # for real
    """
    self.check_workspace_active("campaign deletion")

    plans = _campaign_plan_rows(self, campaign_id)
    result = _new_result(campaign_id, "delete", len(plans))
    result.update({
        "dry_run": dry_run,
        "plans_to_delete": [row.get("meta_id") for row in plans],
        "files_found": 0,
        "files_deleted": 0,
        "database_rows_deleted": 0,
        "campaign_deleted": False,
    })
    # Collected under a neutral name, then reported below under one that matches
    # what actually happened -- see the past/conditional split at the end.
    file_paths: List[str] = []

    for row in plans:
        plan_id = row.get("meta_id")
        try:
            plan = _load_plan(self, row)
            plan_result = plan.delete(
                workspace_manager=self,
                dry_run=dry_run,
                include_database=include_database,
            )

            result["files_found"] += plan_result.get("files_found", 0)
            result["files_deleted"] += plan_result.get("files_deleted", 0)
            result["database_rows_deleted"] += plan_result.get("database_rows_deleted", 0)
            file_paths.extend(plan_result.get("deleted_files", []))

            # MediaPlan.delete() collects its own per-file errors rather than raising,
            # so a plan that reports errors has NOT fully succeeded even though no
            # exception reached us. Treat it as failed, or a partial delete would be
            # reported as a clean one.
            plan_errors = plan_result.get("errors", [])
            if plan_errors:
                result["plans_failed"].append(
                    {"media_plan_id": plan_id, "error": "; ".join(plan_errors)}
                )
            else:
                result["plans_changed"].append(plan_id)

            logger.debug(
                f"{'[DRY RUN] Would delete' if dry_run else 'Deleted'} plan {plan_id} "
                f"of campaign {campaign_id}"
            )

        except Exception as e:
            result["plans_failed"].append({"media_plan_id": plan_id, "error": str(e)})
            logger.error(f"Failed to delete plan {plan_id} of campaign {campaign_id}: {e}")

    result["success"] = not result["plans_failed"]
    # In a dry run nothing was removed, so the campaign is emphatically still there.
    result["campaign_deleted"] = result["success"] and not dry_run

    # A preview must not report its findings in past-tense field names. Sharing
    # plans_changed/deleted_files across both modes meant a dry run listed every
    # plan under "changed" and every path under "deleted" -- and plans_changed
    # means "ids actually transitioned" in archive_campaign/restore_campaign, so
    # a caller reading it the same way here concludes the delete already ran.
    # Only dry_run/files_deleted/campaign_deleted contradicted that, which is
    # three fields too many to have to cross-check on the safest verb available.
    #
    # So the two modes report disjoint outcome fields, and each name states its
    # own tense:
    #   dry run  -> plans_to_delete, files_to_delete   (conditional)
    #   real run -> plans_changed,   deleted_files     (past)
    # plans_to_delete is present in both -- it is the intent, not an outcome --
    # and plans_failed works unchanged either way (a preview can fail to load a
    # plan). Nothing is lost: on a dry run "previewed cleanly" is
    # plans_to_delete minus plans_failed.
    if dry_run:
        result["files_to_delete"] = file_paths
        del result["plans_changed"]
    else:
        result["deleted_files"] = file_paths

    applied = len(result["plans_to_delete"]) - len(result["plans_failed"]) if dry_run \
        else len(result["plans_changed"])
    logger.info(
        f"Campaign '{campaign_id}' delete (dry_run={dry_run}): "
        f"{applied} plan(s) "
        f"{'would be removed' if dry_run else 'removed'}, "
        f"{len(result['plans_failed'])} failed, "
        f"{result['files_found']} file(s) found"
    )
    return result


def patch_workspace_manager():
    """Attach the campaign lifecycle methods to WorkspaceManager."""
    from mediaplanpy.workspace.loader import WorkspaceManager

    WorkspaceManager._campaign_plan_rows = _campaign_plan_rows
    WorkspaceManager._load_campaign_plan = _load_plan
    WorkspaceManager.archive_campaign = archive_campaign
    WorkspaceManager.restore_campaign = restore_campaign
    WorkspaceManager.delete_campaign = delete_campaign


patch_workspace_manager()
