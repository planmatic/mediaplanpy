"""
Tests for schema exposure (get_schema / get_schema_bundle / get_example) and
for the reference resolver behind it.

These back a specific promise made to consumers outside this package -- chiefly
planmatic_ask_api, which re-serves these schemas over HTTP so an agent can
author a media plan from scratch. The promise is that what comes back is
self-contained: it references nothing the consumer cannot reach.
"""
import json

import jsonschema
import pytest

from mediaplanpy import schema as schema_module
from mediaplanpy.schema import (
    contains_external_ref,
    contains_ref,
    get_current_version,
    get_example,
    get_schema,
    get_schema_bundle,
    resolve_refs,
)
from mediaplanpy.schema.refs import SchemaRefError

SCHEMA_TYPES = ["mediaplan", "campaign", "lineitem", "dictionary"]


# ---------------------------------------------------------------------------
# get_schema
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("schema_type", SCHEMA_TYPES)
def test_resolved_schema_has_no_external_reference(schema_type):
    """The core contract: nothing points at a file the consumer cannot read."""
    assert not contains_external_ref(get_schema(schema_type))


def test_mediaplan_subschemas_are_inlined():
    """campaign/lineitem/dictionary arrive as real subschemas, not filenames."""
    schema = get_schema("mediaplan")

    assert "properties" in schema["properties"]["campaign"]
    assert "properties" in schema["properties"]["lineitems"]["items"]
    assert "properties" in schema["properties"]["dictionary"]


def test_use_site_description_wins_over_referenced_document():
    """
    JSON Schema 2020-12 keeps siblings of a $ref. mediaplan's reference to
    campaign carries its own description, which is more specific to the use
    site than the campaign document's own -- losing it would be a silent
    downgrade in what the schema tells an agent.
    """
    schema = get_schema("mediaplan")
    campaign_at_use_site = schema["properties"]["campaign"]

    assert campaign_at_use_site["description"] == (
        "Campaign information and configuration for this media plan"
    )


def test_local_pointers_are_hoisted_not_inlined_by_default():
    """
    Local pointers stay pointers, retargeted at the result's own $defs.
    Inlining them instead triples the document -- see refs.py.
    """
    schema = get_schema("mediaplan")

    assert "$defs" in schema
    dim = schema["properties"]["dictionary"]["properties"]["campaign_custom_dimensions"]
    ref = dim["properties"]["dim_custom1"]["$ref"]

    assert ref.startswith("#/$defs/")
    assert ref.rsplit("/", 1)[-1] in schema["$defs"]


def test_hoisted_definitions_are_namespaced_by_source_document():
    """Two documents may each define '$defs/config'; the prefix keeps them apart."""
    schema = get_schema("mediaplan")

    assert all(key.startswith("dictionary__") for key in schema["$defs"])


def test_inline_local_leaves_no_ref_at_all():
    schema = get_schema("mediaplan", inline_local=True)

    assert not contains_ref(schema)
    assert "$defs" not in schema


def test_hoisting_is_substantially_smaller_than_inlining():
    """
    The size difference is the whole reason hoisting is the default, and the
    consumer is an LLM paying per byte of context. Guard the property rather
    than an exact number, which would churn with every schema edit.
    """
    hoisted = len(json.dumps(get_schema("mediaplan")))
    inlined = len(json.dumps(get_schema("mediaplan", inline_local=True)))

    assert hoisted * 2 < inlined


def test_resolve_refs_false_returns_the_raw_document():
    raw = get_schema("mediaplan", resolve_refs=False)

    assert raw["properties"]["campaign"]["$ref"] == "campaign.schema.json"


def test_defaults_to_current_version():
    assert get_schema("mediaplan") == get_schema("mediaplan", version=get_current_version())


def test_explicit_version_is_honoured():
    schema = get_schema("mediaplan", version="2.0")

    assert not contains_external_ref(schema)
    assert "properties" in schema["properties"]["campaign"]


def test_invalid_schema_type_raises():
    with pytest.raises(ValueError):
        get_schema("nonexistent")


def test_invalid_version_raises():
    with pytest.raises(ValueError):
        get_schema("mediaplan", version="not-a-version")


# ---------------------------------------------------------------------------
# get_schema_bundle
# ---------------------------------------------------------------------------

def test_bundle_is_keyed_by_filename_and_feeds_resolve_refs():
    bundle = get_schema_bundle()

    assert "mediaplan.schema.json" in bundle
    # The bundle's shape is exactly resolve_refs' lookup table.
    resolved = resolve_refs(bundle["mediaplan.schema.json"], bundle)
    assert not contains_external_ref(resolved)


# ---------------------------------------------------------------------------
# get_example
# ---------------------------------------------------------------------------

def test_example_validates_against_the_schema_it_ships_with():
    """
    The point of generating the example rather than storing one: it cannot
    drift out of sync with the schema, because both come from this same
    library at this same version.
    """
    example = json.loads(json.dumps(get_example(), default=str))

    jsonschema.validate(example, get_schema("mediaplan"))


def test_example_validates_against_the_inlined_schema_too():
    """Both resolution modes must describe the same documents."""
    example = json.loads(json.dumps(get_example(), default=str))

    jsonschema.validate(example, get_schema("mediaplan", inline_local=True))


def test_example_is_minimal_but_complete():
    example = get_example()

    assert set(example) >= {"meta", "campaign", "lineitems"}
    assert len(example["lineitems"]) >= 1


def test_example_for_unsupported_type_raises_with_a_useful_message():
    with pytest.raises(ValueError, match="No example generator"):
        get_example("audience")


# ---------------------------------------------------------------------------
# resolve_refs internals
# ---------------------------------------------------------------------------

def test_unknown_filename_reference_raises_rather_than_passing_through():
    """
    Leaving an unresolvable reference in place would hand the consumer a
    document that looks resolved and is not.
    """
    with pytest.raises(SchemaRefError, match="Cannot resolve schema reference"):
        resolve_refs({"properties": {"x": {"$ref": "missing.schema.json"}}}, {})


def test_unknown_local_pointer_raises():
    with pytest.raises(SchemaRefError, match="no such definition"):
        resolve_refs({"properties": {"x": {"$ref": "#/$defs/absent"}}}, {})


def test_circular_reference_is_reported_as_such():
    """A cycle must not surface as an opaque RecursionError."""
    a = {"$id": "a.schema.json", "properties": {"b": {"$ref": "b.schema.json"}}}
    b = {"$id": "b.schema.json", "properties": {"a": {"$ref": "a.schema.json"}}}
    bundle = {"a.schema.json": a, "b.schema.json": b}

    with pytest.raises(SchemaRefError, match="Circular schema reference"):
        resolve_refs(a, bundle)


def test_self_referential_definition_terminates_when_hoisting():
    """A recursive definition is legal JSON Schema; hoisting must not loop on it."""
    doc = {
        "$defs": {"node": {"type": "object", "properties": {"child": {"$ref": "#/$defs/node"}}}},
        "properties": {"root": {"$ref": "#/$defs/node"}},
    }

    resolved = resolve_refs(doc, {})

    assert resolved["properties"]["root"]["$ref"] == "#/$defs/node"
    assert "node" in resolved["$defs"]


def test_unreferenced_definitions_are_dropped():
    """Only what is actually reached is carried into the result."""
    doc = {
        "$defs": {"used": {"type": "string"}, "unused": {"type": "number"}},
        "properties": {"x": {"$ref": "#/$defs/used"}},
    }

    resolved = resolve_refs(doc, {})

    assert set(resolved["$defs"]) == {"used"}


def test_inlined_document_loses_its_document_level_keys():
    """
    A spliced-in subschema is no longer a standalone document; leaving its
    $id/$schema behind yields conflicting declarations some validators reject.
    """
    child = {"$schema": "https://json-schema.org/draft/2020-12/schema",
             "$id": "child.schema.json", "type": "object"}
    parent = {"$id": "parent.schema.json", "properties": {"c": {"$ref": "child.schema.json"}}}

    resolved = resolve_refs(parent, {"child.schema.json": child})

    assert "$id" not in resolved["properties"]["c"]
    assert "$schema" not in resolved["properties"]["c"]
    assert resolved["$id"] == "parent.schema.json"


def test_resolve_refs_does_not_mutate_its_input():
    bundle = get_schema_bundle()
    before = json.dumps(bundle, sort_keys=True)

    resolve_refs(bundle["mediaplan.schema.json"], bundle)

    assert json.dumps(bundle, sort_keys=True) == before


def test_module_exports_the_public_surface():
    for name in ("get_schema", "get_schema_bundle", "get_example",
                 "resolve_refs", "contains_ref", "contains_external_ref"):
        assert name in schema_module.__all__
