"""
MediaPlanPy Examples - Schema Access and Authoring a Plan From Scratch

This script demonstrates the v3.0.10 schema access functions, which let you (or
an LLM agent) build a valid media plan without an existing file to copy.

Why this matters: before these functions, the practical way to produce a valid
media plan was to export one and edit it. That does not work for a brand-new,
empty workspace, and it does not work for a program generating plans from some
other source of truth. `get_schema()` tells you the shape; `get_example()` gives
you a working starting point.

Progressive Demonstration:
1. Inspect the schema catalog (versions, what is available)
2. Get the media plan schema and read its structure
3. See why references matter: raw vs resolved
4. Generate a working example and import it
5. Author a plan from scratch, supplying no ids at all
6. Validate before importing, and read the errors

Prerequisites:
- MediaPlanPy SDK v3.0.10+ installed
- No workspace needed for steps 1-3 and 6 (schemas are shipped with the SDK)
- Steps 4-5 save to a workspace (see examples_01_create_workspace.py)

How to Run:
1. Run: python examples_16_schemas.py
   Steps 1-3 and 6 run with no setup at all.
2. To also run steps 4-5, first run examples_01_create_workspace.py, then
   update the WORKSPACE_ID constant below (or provide it when prompted).

Key Concepts:
- Schemas ship with the SDK - no network call, no workspace, no API
- Resolved schemas are self-contained: nothing points at a file you cannot read
- Examples are GENERATED, not stored, so they cannot drift from the schema
- meta.id, campaign.id and lineitems[].id are marked required but are minted
  for you when omitted - the single most useful thing to know when authoring.
  This applies to the JSON *import* path (import_from_json / the API and MCP
  import tools). MediaPlan.from_dict() builds a model directly and still
  requires all three.
- schema.validate() checks a document literally, so it still reports those ids
  as missing. It and the import path answer different questions; step 5 shows
  how to read that.
"""

import json
import os
import tempfile

from mediaplanpy import schema
from mediaplanpy.models import MediaPlan
from mediaplanpy.workspace import WorkspaceManager


# ============================================================================
# USER CONFIGURATION
# Only needed for steps 4-5. Update after running examples_01_create_workspace.py
# ============================================================================

WORKSPACE_ID = "workspace_xxxxxxxx"

# ============================================================================


def banner(title):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def step_01_inspect_the_catalog():
    """What schemas are available, and at which versions."""
    banner("STEP 1: What is available")

    print(f"Current schema version:    {schema.get_current_version()}")
    print(f"Supported versions:        {', '.join(schema.get_supported_versions())}")

    # The four documents that make up a media plan. 'mediaplan' references the
    # other three; the rest are standalone.
    bundle = schema.get_schema_bundle()
    print(f"\nSchema documents ({len(bundle)}):")
    for filename, document in sorted(bundle.items()):
        print(f"  {filename:28} {document.get('title', '(untitled)')}")


def step_02_read_the_schema():
    """Read the structure of the media plan schema."""
    banner("STEP 2: The media plan schema")

    mediaplan_schema = schema.get_schema("mediaplan")

    print(f"Title:    {mediaplan_schema['title']}")
    print(f"Required: {', '.join(mediaplan_schema['required'])}")

    print("\nTop-level structure:")
    for name, prop in mediaplan_schema["properties"].items():
        required = "required" if name in mediaplan_schema["required"] else "optional"
        print(f"  {name:12} ({prop.get('type', 'object'):6}, {required})")

    # campaign and lineitems are where the real field lists live.
    campaign = mediaplan_schema["properties"]["campaign"]
    lineitem = mediaplan_schema["properties"]["lineitems"]["items"]
    print(f"\nCampaign fields:  {len(campaign['properties'])} "
          f"({len(campaign['required'])} required: {', '.join(campaign['required'])})")
    print(f"Line item fields: {len(lineitem['properties'])} "
          f"({len(lineitem['required'])} required: {', '.join(lineitem['required'])})")

    # A specific field, with its description - this is what makes the schema
    # usable as documentation and not just as a validator.
    budget = campaign["properties"]["budget_total"]
    print(f"\ncampaign.budget_total -> {budget.get('type')}: {budget.get('description', '')}")


def step_03_why_resolution_matters():
    """Raw schemas reference each other by filename; resolved ones stand alone."""
    banner("STEP 3: Raw vs resolved")

    raw = schema.get_schema("mediaplan", resolve_refs=False)
    resolved = schema.get_schema("mediaplan")

    print("Raw (resolve_refs=False) - campaign is a pointer to another file:")
    print(f"  {json.dumps(raw['properties']['campaign'])[:90]}...")
    print("\n  That filename only means something inside the SDK package. Hand this")
    print("  document to anything else - a form generator, an LLM, an HTTP client -")
    print("  and it cannot follow the reference.")

    print("\nResolved (the default) - campaign is spliced in:")
    campaign = resolved["properties"]["campaign"]
    print(f"  type={campaign['type']}, {len(campaign['properties'])} properties, "
          f"description preserved from the use site")

    print(f"\n  External references remaining: {schema.contains_external_ref(resolved)}")

    # Local pointers are kept and retargeted rather than expanded, because the
    # dictionary schema shares one definition across ~35 custom-field slots.
    print(f"\nShared definitions are hoisted into the document's own $defs:")
    for name in resolved.get("$defs", {}):
        print(f"  $defs/{name}")

    hoisted = len(json.dumps(resolved))
    inlined = len(json.dumps(schema.get_schema("mediaplan", inline_local=True)))
    print(f"\n  Hoisted (default):        {hoisted:>7,} bytes")
    print(f"  inline_local=True:        {inlined:>7,} bytes  "
          f"({inlined / hoisted:.1f}x larger, same information)")
    print("\n  Use inline_local=True only if your consumer cannot follow a local")
    print("  '#/$defs/...' pointer. Most can.")


def import_plan(plan, manager):
    """Import an authored plan dict through the real JSON import path.

    Note this goes through import_from_json rather than MediaPlan.from_dict:
    id minting lives on the file-import path, so from_dict still requires
    meta.id, campaign.id and every line item id to be present. If you build
    plans in memory rather than from a file, supply the ids yourself.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_name = "authored_plan.json"
        with open(os.path.join(tmp_dir, file_name), "w", encoding="utf-8") as handle:
            json.dump(plan, handle, default=str)
        return MediaPlan.import_from_json(file_path=tmp_dir, file_name=file_name)


def step_04_generated_example(manager):
    """Get a working example and import it unchanged."""
    banner("STEP 4: A generated example")

    example = schema.get_example("mediaplan")

    print("get_example() builds a minimal valid plan via MediaPlan.create(), so it")
    print("is produced by the same code that builds a real plan - it cannot drift")
    print("out of sync with the schema the way a checked-in fixture would.\n")

    print(f"  meta.name:        {example['meta']['name']}")
    print(f"  meta.id:          {example['meta']['id']}")
    print(f"  campaign.name:    {example['campaign']['name']}")
    print(f"  campaign.budget:  {example['campaign']['budget_total']}")
    print(f"  line items:       {len(example['lineitems'])}")

    if manager is None:
        print("\n  (Skipping import - no workspace configured.)")
        return None

    # Round-trip it through the real import path.
    media_plan = import_plan(example, manager)
    media_plan.save(manager, set_as_current=False)
    print(f"\n  Imported as: {media_plan.meta.id}")
    return media_plan


def step_05_author_from_scratch(manager):
    """Write a plan by hand, omitting every id."""
    banner("STEP 5: Authoring from scratch, with no ids")

    # Note what is NOT here: meta.id, campaign.id, and any lineitems[].id.
    # All three are marked "required" in the schema, and all three are minted
    # for you when omitted (v3.0.10+). Supply them only when you need to
    # control the value - for instance, re-importing a plan you exported.
    plan = {
        "meta": {
            "schema_version": f"v{schema.get_current_version()}",
            "created_by_name": "examples_16_schemas.py",
            "created_at": "2026-01-15T09:00:00Z",
            "name": "Q1 Launch - Authored From Scratch",
        },
        "campaign": {
            "name": "Q1 Product Launch",
            "objective": "Awareness",
            "start_date": "2026-01-01",
            "end_date": "2026-03-31",
            "budget_total": 250000,
        },
        "lineitems": [
            {
                "name": "Social - Prospecting",
                "channel": "Social",
                "start_date": "2026-01-01",
                "end_date": "2026-03-31",
                "cost_total": 150000,
            },
            {
                "name": "CTV - Reach",
                "channel": "CTV",
                "start_date": "2026-02-01",
                "end_date": "2026-03-31",
                "cost_total": 100000,
            },
        ],
    }

    print("Authored JSON supplies no ids at all:")
    print(f"  meta:      {sorted(plan['meta'])}")
    print(f"  campaign:  {sorted(plan['campaign'])}")
    print(f"  lineitems: {len(plan['lineitems'])}, keys {sorted(plan['lineitems'][0])}")

    # IMPORTANT: schema.validate() checks the document exactly as written, and
    # the schema marks the ids "required" - so it reports them missing even
    # though the import path mints them. The two functions answer different
    # questions: validate() asks "is this document schema-valid as it stands?",
    # import asks "can this be turned into a plan?". Expect id errors here when
    # validating an authored plan, and read past them.
    errors = schema.validate(plan)
    id_errors = [e for e in errors if "'id' is a required property" in e]
    other = [e for e in errors if e not in id_errors]
    print(f"\n  schema.validate() before import: {len(errors)} error(s)")
    print(f"    {len(id_errors)} about ids the import will mint  <- expected, ignore")
    print(f"    {len(other)} real problem(s): {other if other else 'none'}")

    if manager is None:
        print("\n  (Skipping import - no workspace configured.)")
        return None

    media_plan = import_plan(plan, manager)
    media_plan.save(manager, set_as_current=False)

    print("\nIds minted on import:")
    print(f"  meta.id:      {media_plan.meta.id}")
    print(f"  campaign.id:  {media_plan.campaign.id}")
    for item in media_plan.lineitems:
        print(f"  lineitem.id:  {item.id}  ({item.name})")

    return media_plan


def step_06_validate_before_importing():
    """Catch problems before they reach storage."""
    banner("STEP 6: Reading validation errors")

    # Ids are supplied here so the errors that surface are the ones being
    # demonstrated. Omit them and the first thing reported is the missing
    # meta.id, which masks the faults below (see step 5's note).
    broken = {
        "meta": {
            "id": "mediaplan_example",
            "schema_version": f"v{schema.get_current_version()}",
            "created_by_name": "examples_16_schemas.py",
            "created_at": "2026-01-15T09:00:00Z",
        },
        "campaign": {
            "id": "campaign_example",
            # "name" omitted - required
            "start_date": "2026-01-01",
            "end_date": "2026-03-31",
            "budget_total": "not a number",  # wrong type
        },
        "lineitems": [],
    }

    # Two faults are seeded, but validate() reports the first failure it finds
    # rather than every one - so fixing and re-validating is a loop, not a
    # single pass. Worth knowing before you build a form around it.
    print("Two faults seeded: campaign.name missing, budget_total the wrong type.\n")

    for attempt in range(1, 4):
        errors = schema.validate(broken)
        if not errors:
            print(f"  Pass {attempt}: clean")
            break
        print(f"  Pass {attempt}: {len(errors)} error reported")
        for error in errors:
            print(f"    - {error}")

        # Apply the obvious fix for whatever was reported, then go round again.
        if "'name' is a required property" in errors[0]:
            broken["campaign"]["name"] = "Now Named"
            print("    -> fixed: added campaign.name")
        elif "budget_total" in errors[0]:
            broken["campaign"]["budget_total"] = 250000
            print("    -> fixed: budget_total is now a number")
        else:
            break

    print("\nValidating before importing is worth it for exactly these: a missing")
    print("required field or a type error is far easier to read here than as a")
    print("failure part-way through a save. Just expect one error per call.")


def main():
    print("=" * 70)
    print("MediaPlanPy Examples - Schema Access")
    print("=" * 70)

    # Steps 1-3 and 6 need nothing at all: the schemas ship with the SDK.
    step_01_inspect_the_catalog()
    step_02_read_the_schema()
    step_03_why_resolution_matters()

    manager = None
    workspace_id = WORKSPACE_ID
    if workspace_id == "workspace_xxxxxxxx":
        entered = input(
            "\nWorkspace ID for steps 4-5 (press Enter to skip them): "
        ).strip()
        workspace_id = entered or None

    if workspace_id:
        try:
            manager = WorkspaceManager()
            manager.load(workspace_id=workspace_id)
            print(f"\nLoaded workspace: {workspace_id}")
        except Exception as e:
            print(f"\nCould not load workspace '{workspace_id}': {e}")
            print("Continuing without it - steps 4-5 will not save.")
            manager = None

    try:
        step_04_generated_example(manager)
        step_05_author_from_scratch(manager)
        step_06_validate_before_importing()

        banner("✓ All Steps Completed Successfully!")
        print("\nWhat you learned:")
        print("  1. Schemas ship with the SDK - no workspace, no network, no API")
        print("  2. Resolved schemas are self-contained and safe to hand to any consumer")
        print("  3. get_example() is generated, so it cannot drift from the schema")
        print("  4. meta.id, campaign.id and line item ids are minted when omitted")
        print("  5. schema.validate() catches real problems early, but reports the")
        print("     auto-minted ids as missing - read past those")
        print("\nNext Steps:")
        print("  • examples_03_create_mediaplan.py - build plans with MediaPlan.create()")
        print("  • examples_07_import_mediaplan.py - import from JSON and Excel files")
        print("  • examples_12_manage_dictionary.py - configure the custom fields you")
        print("    saw referenced under $defs in step 3")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
