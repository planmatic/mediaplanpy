"""
JSON Schema ``$ref`` resolution for mediaplanpy's bundled schema definitions.

Why this lives in the SDK
-------------------------
``mediaplan.schema.json`` is not self-contained: it references its sibling
definitions **by bare filename** (``{"$ref": "campaign.schema.json"}``), which
is a convention of this package's own ``schema/definitions/<version>/`` layout
and nothing else. Any consumer that wants a single usable document -- an API
serving the schema over HTTP, an LLM agent authoring a media plan, a form
generator -- has to understand that convention to dereference it.

Re-implementing it outside this package means every consumer breaks, silently
and at runtime, the first time these definitions are reorganised. So resolution
belongs here, next to the files whose layout it encodes.

The two reference shapes, and why they are treated differently
--------------------------------------------------------------
This is a deliberately small resolver for exactly the two shapes these schemas
use, not a general-purpose JSON Schema reference implementation:

* **bare sibling filenames** -- ``{"$ref": "campaign.schema.json"}``, used by
  ``mediaplan`` to pull in its three sub-documents. These are **inlined**: they
  point outside the document, so a consumer that cannot read this package's
  ``definitions/`` directory cannot follow them.

* **local JSON Pointers** -- ``{"$ref": "#/$defs/custom_field_config"}``, used
  throughout ``dictionary`` to share one definition across ~35 custom-field
  slots. These are **hoisted, not inlined**: their targets are collected into
  the result's own ``$defs`` and the pointers rewritten to match.

Hoisting rather than inlining is a size decision, and a large one. Inlining
``dictionary``'s single shared definition at all ~35 use sites takes the
resolved media plan schema from ~23 KB to ~92 KB -- and the consumer this
exists for is an LLM agent paying for every one of those bytes in its context
window. The definition is identical at each site, so the copies buy nothing.

What matters for a consumer is that the document is **self-contained**: it must
not point at anything the consumer cannot reach. A local pointer into the same
document satisfies that; a filename does not. Hence ``contains_external_ref()``
rather than a blanket "no $ref anywhere" check.

Pointers cannot simply be left alone, though. Once ``dictionary.schema.json``
is spliced into ``mediaplan.schema.json``, a bare ``#/$defs/...`` would resolve
against the *mediaplan* root, where ``$defs`` does not exist -- producing a
document that looks fine and validates nothing. Hoisting is what keeps them
pointing at a real target.

This module does not fetch over the network, does not resolve pointers into
*remote* documents, and does not implement ``$dynamicRef``. An unrecognised
reference raises rather than being silently left in place.
"""
import copy
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("mediaplanpy.schema.refs")

# Keys that make an inlined subschema look like a standalone document. Once a
# subschema is spliced into its parent it is no longer one, and leaving these
# behind produces a document with several conflicting $id/$schema declarations
# -- which some validators reject outright.
_DOCUMENT_LEVEL_KEYS = ("$schema", "$id")

_DEFS = "$defs"


class SchemaRefError(ValueError):
    """Raised when a ``$ref`` cannot be resolved, or when references form a cycle."""


def resolve_refs(
    schema: Dict[str, Any],
    sibling_schemas: Dict[str, Dict[str, Any]],
    inline_local: bool = False,
) -> Dict[str, Any]:
    """
    Return a deep copy of ``schema`` that references nothing outside itself.

    Args:
        schema: The schema document to resolve.
        sibling_schemas: Available targets, keyed by the filename used in the
            ``$ref`` (e.g. ``{"campaign.schema.json": {...}}``).
        inline_local: Also expand local ``#/$defs/...`` pointers in place,
            leaving a document with no ``$ref`` of any kind. Off by default --
            it multiplies the size of any schema that shares a definition across
            many fields (see the module docstring).

    Returns:
        A new dict containing no external (filename) reference. Local pointers
        remain unless ``inline_local=True``, and every one of them resolves
        against the returned document's own ``$defs``.

    Raises:
        SchemaRefError: If a reference names a schema or definition that does
            not exist, or if references form a cycle.

    Sibling keys alongside a ``$ref`` are preserved and take precedence over the
    referenced document, matching JSON Schema 2020-12, where ``$ref`` no longer
    replaces its neighbours. This matters in practice: ``mediaplan``'s reference
    to ``campaign`` carries its own ``description``, which is more specific to
    the use site than the campaign schema's own title.
    """
    hoisted: Dict[str, Any] = {}
    resolved = _resolve_node(
        schema,
        sibling_schemas=sibling_schemas,
        stack=[],
        doc_root=schema,
        doc_name=None,
        hoisted=hoisted,
        inline_local=inline_local,
    )

    if not isinstance(resolved, dict):
        return resolved

    # Drop the source document's own $defs and replace it with just the
    # definitions actually reached. An unreferenced definition would otherwise
    # ride along at full size for no one's benefit.
    resolved.pop(_DEFS, None)
    if hoisted:
        resolved[_DEFS] = hoisted
    return resolved


def _resolve_node(
    node: Any,
    sibling_schemas: Dict[str, Dict[str, Any]],
    stack: List[str],
    doc_root: Dict[str, Any],
    doc_name: Optional[str],
    hoisted: Dict[str, Any],
    inline_local: bool,
) -> Any:
    """
    Recursively resolve one node of a schema document.

    doc_root/doc_name identify the document a local ``#/`` pointer belongs to.
    Both change when we descend into an inlined sibling, so that file's own
    pointers keep resolving against that file rather than against whatever
    pulled it in, and its hoisted definitions keep a name that says where they
    came from.
    """
    recurse = lambda child: _resolve_node(  # noqa: E731 -- keeps 7 identical args off five call sites
        child, sibling_schemas, stack, doc_root, doc_name, hoisted, inline_local
    )

    if isinstance(node, list):
        return [recurse(item) for item in node]

    if not isinstance(node, dict):
        return node

    ref = node.get("$ref")
    if ref is None:
        # $defs is hoisted on demand as pointers are encountered; copying the
        # block wholesale here would defeat the "only what is reached" trim.
        return {key: recurse(value) for key, value in node.items() if key != _DEFS}

    siblings = {key: recurse(value) for key, value in node.items() if key != "$ref"}

    if ref.startswith("#"):
        return _resolve_local(
            ref, siblings, sibling_schemas, stack, doc_root, doc_name, hoisted, inline_local
        )

    return _resolve_external(
        ref, siblings, sibling_schemas, stack, hoisted, inline_local
    )


def _resolve_local(
    ref: str,
    siblings: Dict[str, Any],
    sibling_schemas: Dict[str, Dict[str, Any]],
    stack: List[str],
    doc_root: Dict[str, Any],
    doc_name: Optional[str],
    hoisted: Dict[str, Any],
    inline_local: bool,
) -> Any:
    """Hoist (or inline) a local ``#/...`` pointer."""
    target = _lookup_pointer(ref, doc_root)

    if inline_local:
        if _cycles(ref, stack):
            raise SchemaRefError(f"Circular schema reference detected: {' -> '.join(stack + [ref])}")
        resolved = _resolve_node(
            target, sibling_schemas, stack + [ref], doc_root, doc_name, hoisted, inline_local
        )
        return _merge(resolved, siblings)

    key = _hoisted_key(ref, doc_name)
    if key not in hoisted:
        # Reserve the name before resolving, so a definition that refers to
        # itself terminates here instead of recursing forever.
        hoisted[key] = {}
        hoisted[key] = _resolve_node(
            target, sibling_schemas, stack + [ref], doc_root, doc_name, hoisted, inline_local
        )

    return _merge({"$ref": f"#/{_DEFS}/{key}"}, siblings)


def _resolve_external(
    ref: str,
    siblings: Dict[str, Any],
    sibling_schemas: Dict[str, Dict[str, Any]],
    stack: List[str],
    hoisted: Dict[str, Any],
    inline_local: bool,
) -> Any:
    """Inline a bare-filename reference to a sibling document."""
    if _cycles(ref, stack):
        raise SchemaRefError(f"Circular schema reference detected: {' -> '.join(stack + [ref])}")

    if ref not in sibling_schemas:
        available = ", ".join(sorted(sibling_schemas)) or "(none)"
        raise SchemaRefError(
            f"Cannot resolve schema reference '{ref}'. Available schemas: {available}. "
            f"Only bare sibling filenames (e.g. 'campaign.schema.json') and local "
            f"pointers (e.g. '#/$defs/name') are supported."
        )

    target = copy.deepcopy(sibling_schemas[ref])
    for key in _DOCUMENT_LEVEL_KEYS:
        target.pop(key, None)

    resolved = _resolve_node(
        target,
        sibling_schemas,
        stack + [ref],
        doc_root=sibling_schemas[ref],  # an inlined document is its own pointer root
        doc_name=ref,
        hoisted=hoisted,
        inline_local=inline_local,
    )
    return _merge(resolved, siblings)


def _merge(resolved: Any, siblings: Dict[str, Any]) -> Any:
    """Apply sibling keys over a resolved target (siblings win)."""
    if not siblings or not isinstance(resolved, dict):
        # A pointer into a non-object (e.g. an enum list) has no keys to merge
        # into; sibling keys alongside such a ref would be meaningless.
        return resolved
    merged = dict(resolved)
    merged.update(siblings)
    return merged


def _cycles(ref: str, stack: List[str]) -> bool:
    """
    Whether following ``ref`` would revisit a reference already being resolved.

    Without this a cycle recurses to the interpreter's stack limit and surfaces
    as a RecursionError naming no schema at all. These definitions form a DAG
    today; assert it rather than assume it.
    """
    return ref in stack


def _hoisted_key(ref: str, doc_name: Optional[str]) -> str:
    """
    Name for a hoisted definition, qualified by its source document.

    Several documents may each define ``#/$defs/config``; merging them into one
    ``$defs`` would otherwise let whichever resolved last win, silently
    validating fields against the wrong definition. Prefixing by source makes
    collisions impossible without a lookup table.
    """
    name = ref.rsplit("/", 1)[-1] or "definition"
    if doc_name is None:
        return name
    stem = doc_name.split(".", 1)[0]
    return f"{stem}__{name}"


def _lookup_pointer(ref: str, doc_root: Dict[str, Any]) -> Any:
    """
    Resolve a local JSON Pointer (``#/a/b``) against doc_root.

    Only the subset RFC 6901 needs here: ``~1``/``~0`` unescaping, no array
    indices (these schemas never point into one).
    """
    pointer = ref[1:]
    if not pointer:
        return copy.deepcopy(doc_root)
    if not pointer.startswith("/"):
        raise SchemaRefError(
            f"Unsupported local reference '{ref}': expected '#/path/to/definition'."
        )

    node: Any = doc_root
    for raw_token in pointer.lstrip("/").split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or token not in node:
            raise SchemaRefError(
                f"Cannot resolve local schema reference '{ref}': no such definition."
            )
        node = node[token]
    return copy.deepcopy(node)


def contains_external_ref(schema: Any) -> bool:
    """
    Whether ``schema`` still references a document other than itself.

    This is the property every consumer of a resolved schema actually depends
    on -- that nothing points at a file they cannot read -- so it is worth being
    able to assert cheaply rather than re-implementing the walk. A local
    ``#/...`` pointer is not an external reference.
    """
    for ref in _iter_refs(schema):
        if not ref.startswith("#"):
            return True
    return False


def contains_ref(schema: Any) -> bool:
    """Whether ``schema`` contains a ``$ref`` of any kind, local ones included."""
    return any(True for _ in _iter_refs(schema))


def _iter_refs(node: Any):
    """Yield every ``$ref`` string in a schema document, at any depth."""
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            yield ref
        for value in node.values():
            yield from _iter_refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_refs(item)
