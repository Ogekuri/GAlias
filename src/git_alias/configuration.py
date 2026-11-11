"""@brief Schema-driven GAlias configuration management.
@details Owns configuration metadata, hierarchical JSON access, atomic
persistence, global auto-initialization, and CLI rendering for --print-raw,
--print, --info, --set, --unset, and --get. Alias execution stays in core;
this module performs no subprocess execution and implements no legacy
migration. All rendered text is English.
@satisfies DES-010, REQ-014, REQ-242, REQ-243, REQ-253, REQ-272
"""

import copy
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Parameter:
    """@brief Describe one configurable field or container.
    @details Immutable metadata node; nested dictionaries preserve display
    order. Construction is O(1); consumers deep-copy defaults before mutation.
    A dict node with a non-None item declares a dynamic map keyed by arbitrary
    strings whose values validate against the item schema.
    @param kind {type} Exact JSON-compatible Python type of the value.
    @param description {str} English field meaning and input constraints.
    @param default {Any} Default applied when the key is absent.
    @param fields {dict[str, Parameter]} Object field schema; empty for scalars and maps.
    @param item {Parameter | None} Array element schema, or map value schema for dict nodes.
    @param choices {tuple[tuple[str, str], ...]} Allowed values with meanings.
    @param example {str} One canonical input example for discovery output.
    @param empty {bool} Permit an empty string value.
    @param strip {bool} Strip surrounding whitespace from string values.
    @return {Parameter} Immutable schema node.
    @satisfies REQ-242, REQ-251
    """

    kind: type  ## @brief Exact accepted value type.
    description: str  ## @brief English field contract.
    default: Any = None  ## @brief Default value copied on resolution.
    fields: dict[str, "Parameter"] = field(default_factory=dict)  ## @brief Object fields.
    item: "Parameter | None" = None  ## @brief Array element or map value schema.
    choices: tuple[tuple[str, str], ...] = ()  ## @brief Allowed values and meanings.
    example: str = ""  ## @brief Canonical input example.
    empty: bool = False  ## @brief Empty-string acceptance flag.
    strip: bool = False  ## @brief Whitespace normalization flag.


## @brief Version-rule element schema with canonical object fields.
# @details Regex is required for inclusion patterns; negation patterns may omit it.
RULE = Parameter(dict, "Version rule pairing a file selector with an extractor", fields={
    "pattern": Parameter(
        str, "gitignore(5) file selector; a leading ! excludes files",
        "src/**/*.py", example="src/**/*.py"),
    "regex": Parameter(
        str, "Python regex extracting the version; omit only for ! patterns",
        r"(\d+\.\d+\.\d+)", example=r"(\d+\.\d+\.\d+)"),
}, example='[{"pattern": "VERSION", "regex": "(\\\\d+\\\\.\\\\d+\\\\.\\\\d+)"}]')

## @brief Canonical ordered schema for every persisted configuration field.
# @details Global keys stay contiguous in REQ-192 order; Local owns repository
# branches, the conventional-commit scope, and version rules. No field defines
# constrained choices or dynamic maps today; the schema and renderers fully
# support both constructs for future fields.
# @satisfies DES-006, DES-010, REQ-186, REQ-191, REQ-192, REQ-242
SCHEMA = {
    "Global": Parameter(dict, "User settings stored in $HOME/.config/galias/config.json", fields={
        "edit_command": Parameter(
            str, "Terminal editor launcher", "edit", example="vim -f"),
        "edit_command_gfx": Parameter(
            str, "Graphical editor launcher; empty selects the terminal command",
            "sublime_text", example="subl --wait", empty=True),
        "diff_command": Parameter(
            str, "Terminal visual diff tool; empty uses the git default",
            "icdiff", example="icdiff", empty=True),
        "diff_command_gfx": Parameter(
            str, "Graphical visual diff tool; empty selects the terminal command",
            "meld", example="meld", empty=True),
        "gr_command": Parameter(
            str, "Terminal decorated-history viewer", "tig", example="tig"),
        "gr_command_gfx": Parameter(
            str, "Graphical decorated-history viewer; empty selects the terminal command",
            "gitg", example="gitg", empty=True),
        "gp_command": Parameter(
            str, "Terminal commit-graph viewer", "gitui", example="gitui"),
        "gp_command_gfx": Parameter(
            str, "Graphical commit-graph viewer; empty selects the terminal command",
            "sublime_merge --multiinstance .", example="sublime_merge", empty=True),
    }),
    "Local": Parameter(dict, "Workspace settings stored in .galias.conf at the repository root", fields={
        "master": Parameter(str, "Primary release branch", "master", example="main"),
        "develop": Parameter(str, "Integration branch", "develop", example="devel"),
        "work": Parameter(str, "Working branch", "work", example="topic"),
        "default_commit_module": Parameter(
            str, "Default conventional-commit scope; empty omits the scope",
            "", example="core", empty=True, strip=True),
        "ver_rules": Parameter(
            list, "Version rules selecting files and version extractors",
            [
                {"pattern": "README.md", "regex": r"\s*\((\d+\.\d+\.\d+)\)\n"},
                {"pattern": "src/**/*.py", "regex": r'__version__\s*=\s*["\']?(\d+\.\d+\.\d+)["\']?'},
                {"pattern": "pyproject.toml", "regex": r'\bversion\s*=\s*"(\d+\.\d+\.\d+)"'},
            ],
            item=RULE,
            example='[{"pattern": "VERSION", "regex": "(\\\\d+\\\\.\\\\d+\\\\.\\\\d+)"}]'),
    }),
}

## @brief Display labels for schema types used by parameter discovery output.
# @details Selection labels constrained fields whose choices are defined.
# @satisfies REQ-251
TYPE_LABELS = {str: "String", int: "Integer", float: "Float", bool: "Boolean",
               list: "Array", dict: "Dictionary"}

## @brief Management command syntax and descriptions used by both help paths.
# @satisfies REQ-243, REQ-252
COMMAND_HELP = {
    "--print-raw": "--print-raw [Global|Local]: emit exact file bytes; labels go to stderr.",
    "--print": "--print [PATH]: show the effective configuration tree, or only the PATH subtree.",
    "--info": "--info [PATH]: show types, constraints, defaults, and ready-to-run commands.",
    "--set": "--set PATH VALUE: set a field, map key, row, or cell; ':append' or ':+' adds, ':insert:<Idx>' inserts.",
    "--unset": "--unset PATH: restore defaults, remove keys, delete rows, or reset cells.",
    "--get": "--get PATH: extract a value, row, cell, map key, or subtree as JSON.",
}

## @brief Shared input instructions appended to configuration command help.
# @satisfies REQ-244, REQ-247, REQ-252
INPUT_HELP = r"""Paths are case-sensitive and use ':' separators rooted at Global or Local:
Global:edit_command, Local:work, Local:ver_rules:0:pattern, Local:ver_rules:0.
Array indices are zero-based. Reserved tokens on array paths: ':append' or ':+'
appends one schema-validated item; ':insert:<Idx>' inserts at <Idx> and shifts
later rows; ':<Idx>' replaces a whole row or updates a primitive row;
':<Idx>:<Field>' targets one object cell; ':<Key>' addresses one dynamic map
key. '--unset' removes a key, scope, array row, map key, or optional object
field and always re-indexes arrays contiguously from zero; absent top-level
keys resolve to defaults. Use Global or Local alone to get, replace
(--set JSON object), or clear (--unset) a scope; clearing prints a warning.
Strings accept plain text or JSON strings. Objects, arrays, numbers, and
booleans require valid JSON as one shell-quoted argument; JSON regex
backslashes are doubled.
Examples:
  g --set Global:edit_command 'vim -f'
  g --set Global:gp_command_gfx 'sublime_merge --multiinstance .'
  g --set Local:ver_rules '[{"pattern":"VERSION","regex":"(\\d+\\.\\d+\\.\\d+)"}]'
  g --set Local:ver_rules:+ '{"pattern":"!vendor/**"}'
  g --set Local:ver_rules:insert:0 '{"pattern":"!tmp/**"}'
  g --set Local:ver_rules:0:pattern 'src/**/*.py'
  g --unset Local:ver_rules:0
  g --get Local:ver_rules:0:pattern
  g --unset Local:default_commit_module
  g --unset Local
The shell expands environment variables before invocation; values are stored
exactly as received and are never evaluated as shell commands. Use --info for
per-field types, constraints, defaults, and copy-pasteable commands. --get
resolves absent top-level keys from defaults. --print-raw shows only bytes on
disk. Global storage: $HOME/.config/galias/config.json, auto-created with
defaults on the first configuration command. Local storage: .galias.conf at
the repository root, or the current directory outside a repository; the local
file is created only by explicit mutations.
"""


def defaults(scope: str) -> dict[str, Any]:
    """@brief Copy the defaults belonging to one scope.
    @details O(N) deep copy protecting schema defaults from nested mutation.
    @param scope {str} Global or Local.
    @return {dict[str, Any]} Independent default configuration object.
    @throws KeyError Unknown scope.
    @satisfies REQ-242, REQ-246
    """
    return {key: copy.deepcopy(spec.default)
            for key, spec in SCHEMA[scope].fields.items()}


def resolve_path(path: str) -> tuple[list[str], Parameter]:
    """@brief Resolve a colon path against the schema without filesystem I/O.
    @details O(D) traversal. Array indices must be canonical non-negative
    decimals. A dict node with an item schema accepts any non-empty token as a
    dynamic map key and descends to the item schema.
    @param path {str} Scope followed by optional fields, indices, and map keys.
    @return {tuple[list[str], Parameter]} Path tokens and terminal schema node.
    @throws ValueError Unknown scope, unknown field, empty segment, or invalid index.
    @satisfies REQ-244, REQ-248, REQ-267, REQ-268
    """
    parts = path.split(":")
    if parts[0] not in SCHEMA or any(not part for part in parts):
        raise ValueError(f"Invalid configuration path: {path}")
    spec = SCHEMA[parts[0]]
    for part in parts[1:]:
        if spec.kind is dict and spec.item is not None:
            spec = spec.item
        elif part in spec.fields:
            spec = spec.fields[part]
        elif spec.kind is list and spec.item is not None and re.fullmatch(r"0|[1-9][0-9]*", part):
            spec = spec.item
        else:
            raise ValueError(f"Unknown configuration path: {path}")
    return parts, spec


def validate(value: Any, spec: Parameter, path: str) -> Any:
    """@brief Validate and copy a canonical JSON value.
    @details O(N) recursive validation rejecting wrong types, unknown object
    fields, and invalid rule structures; compiles rule regexes. Dict nodes
    with an item schema validate every value against that item schema and
    accept arbitrary string keys. Normalizes only fields marked strip;
    performs no I/O.
    @param value {Any} Candidate JSON value.
    @param spec {Parameter} Expected type, children, and constraints.
    @param path {str} Diagnostic path.
    @return {Any} Independent normalized value.
    @throws ValueError Wrong type, unknown key, empty required string, invalid rule.
    @satisfies REQ-207, REQ-245, REQ-248
    """
    if type(value) is not spec.kind:
        raise ValueError(f"{path}: expected {spec.kind.__name__}")
    if spec.kind is str:
        if not spec.empty and not value.strip():
            raise ValueError(f"{path}: expected a non-empty string")
        return value.strip() if spec.strip else value
    if spec.kind is list and spec.item is not None:
        return [validate(item, spec.item, f"{path}:{index}")
                for index, item in enumerate(value)]
    if spec.kind is dict:
        if spec.item is not None:
            return {key: validate(item, spec.item, f"{path}:{key}")
                    for key, item in value.items()}
        unknown = set(value) - set(spec.fields)
        if unknown:
            raise ValueError(f"{path}: unknown fields: {', '.join(sorted(unknown))}")
        result = {key: validate(item, spec.fields[key], f"{path}:{key}")
                  for key, item in value.items()}
        if spec is RULE:
            pattern = result.get("pattern", "").strip()
            if not pattern or (not pattern.startswith("!") and not result.get("regex")):
                raise ValueError(f"{path}: pattern and inclusion regex are required")
            if "regex" in result:
                try:
                    re.compile(result["regex"])
                except re.error as exc:
                    raise ValueError(f"{path}: invalid regex: {exc}") from exc
        return result
    return value


def parse_value(text: str, spec: Parameter, path: str) -> Any:
    """@brief Decode one CLI value using the selected field type.
    @details O(N) parsing; plain strings stay literal; JSON strings and complex
    JSON values (objects, arrays, integers, floats, booleans) decode without
    shell evaluation so CLI strings are cast to strict schema types before
    persistence.
    @param text {str} One argument after shell processing.
    @param spec {Parameter} Selected schema node.
    @param path {str} Diagnostic path.
    @return {Any} Validated typed value.
    @throws ValueError Malformed JSON or schema mismatch.
    @satisfies REQ-245, REQ-248, REQ-252
    """
    value = text
    if spec.kind is not str or text.startswith('"'):
        value = json.loads(text)
    return validate(value, spec, path)


def read_scope(path: Path, scope: str) -> dict[str, Any]:
    """@brief Read one scope without creating files or inserting defaults.
    @details O(N) JSON decode plus validation; absent files yield an empty
    object; out-of-scope stored keys are ignored; invalid data fails closed.
    @param path {Path} Configuration file.
    @param scope {str} Schema scope.
    @return {dict[str, Any]} Canonical persisted values only.
    @throws OSError File cannot be read.
    @throws ValueError Invalid JSON, encoding, root object, or field values.
    @satisfies DES-006, REQ-015, REQ-097, REQ-248
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    scoped = {key: value for key, value in data.items() if key in SCHEMA[scope].fields}
    return validate(scoped, SCHEMA[scope], scope)


def write_scope(path: Path, data: dict[str, Any]) -> None:
    """@brief Atomically replace one validated configuration file.
    @details O(N) serialization; writes and fsyncs a private temporary file in
    the target directory then renames it over the target. Cleans the temporary
    file on failure and creates parent directories for this explicit mutation
    or bootstrapping path.
    @param path {Path} Selected destination.
    @param data {dict[str, Any]} Validated canonical scope object.
    @return {None} Persisted JSON ends with one newline.
    @throws OSError Directory creation, write, flush, or replace failure.
    @satisfies REQ-014, REQ-097, REQ-253, REQ-254, REQ-272
    """
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def descend(data: Any, parts: list[str]) -> Any:
    """@brief Traverse existing JSON fields, indices, and map keys.
    @details O(D) traversal rejecting missing members and out-of-range indices.
    @param data {Any} Effective scope or subtree.
    @param parts {list[str]} Schema-validated relative path tokens.
    @return {Any} Referenced subtree; callers copy before mutation.
    @throws ValueError Missing field, map key, or out-of-range array index.
    @satisfies REQ-244, REQ-246, REQ-248, REQ-268
    """
    for part in parts:
        try:
            data = data[int(part)] if isinstance(data, list) else data[part]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise ValueError(f"Configuration member does not exist: {part}") from exc
    return data


def change_scope(data: dict[str, Any], parts: list[str], value: Any,
                 unset: bool) -> dict[str, Any]:
    """@brief Compute a validated scope replacement without writing.
    @details O(N) copy plus validation; absent top-level values use defaults
    for nested changes; removing top-level keys restores defaults on the next
    read. Array row deletion re-indexes the list contiguously from zero, and
    out-of-range indices fail with the valid range and the ':append' hint.
    @param data {dict[str, Any]} Persisted canonical scope values.
    @param parts {list[str]} Schema-validated full path including the scope.
    @param value {Any} Parsed replacement; ignored when unset is True.
    @param unset {bool} Delete instead of assign.
    @return {dict[str, Any]} Validated scope after mutation.
    @throws ValueError Missing nested member, out-of-range index, or invalid structure.
    @satisfies REQ-245, REQ-247, REQ-248, REQ-269, REQ-270
    """
    scope = parts[0]
    result = copy.deepcopy(data)
    if len(parts) == 1:
        result = {} if unset else value
    elif len(parts) == 2:
        if unset:
            result.pop(parts[1], None)
        else:
            result[parts[1]] = value
    else:
        key = parts[1]
        if key not in result:
            result[key] = defaults(scope)[key]
        parent = descend(result, parts[1:-1])
        if isinstance(parent, list):
            index = _array_index(parent, parts, unset)
            if unset:
                del parent[index]
            else:
                parent[index] = value
        elif unset:
            parent.pop(parts[-1], None)
        else:
            parent[parts[-1]] = value
    return validate(result, SCHEMA[scope], scope)


def _array_index(parent: list[Any], parts: list[str], unset: bool) -> int:
    """@brief Resolve one array index token with a strict bounds check.
    @details O(1); rejects non-canonical decimals and out-of-range indices
    with an English diagnostic carrying the valid range and the ':append'
    alternative so scripts can self-correct.
    @param parent {list[Any]} Target array value.
    @param parts {list[str]} Full path including the scope; the last token is the index.
    @param unset {bool} True for deletions; selects the diagnostic verb.
    @return {int} Zero-based index inside the array.
    @throws ValueError Non-canonical index or index outside 0..len(parent)-1.
    @satisfies REQ-270
    """
    token = parts[-1]
    name = ":".join(parts[:-1])
    if not re.fullmatch(r"0|[1-9][0-9]*", token):
        raise ValueError(f"{name}: invalid array index: {token}")
    index = int(token)
    if index >= len(parent):
        action = "remove" if unset else "update"
        raise ValueError(
            f"Error: Index {index} out of bounds. Valid indices for {name} "
            f"are 0..{len(parent) - 1} to {action} an existing item. "
            f"Use ':append' to add a new item.")
    return index


def _mutate_array(data: dict[str, Any], parts: list[str], value: Any,
                  mode: str, index: int | None) -> tuple[dict[str, Any], int]:
    """@brief Append or insert one validated item into an array parameter.
    @details O(N) copy; backfills a missing top-level array from defaults,
    appends at the end or inserts at the requested position shifting later
    items down, and validates the resulting scope. Insert at the length equals
    append.
    @param data {dict[str, Any]} Persisted canonical scope values.
    @param parts {list[str]} Schema-validated array path including the scope.
    @param value {Any} Parsed and validated item value.
    @param mode {str} 'append' or 'insert'.
    @param index {int | None} Zero-based insert position for 'insert' mode.
    @return {tuple[dict[str, Any], int]} Validated scope and the assigned index.
    @throws ValueError Out-of-range insert position or invalid resulting structure.
    @satisfies REQ-265, REQ-266
    """
    scope = parts[0]
    result = copy.deepcopy(data)
    if parts[1] not in result:
        result[parts[1]] = defaults(scope)[parts[1]]
    container = descend(result, parts[1:-1])
    name = parts[-1]
    items = container[name]
    if not isinstance(items, list):
        raise ValueError(f"{':'.join(parts)}: expected an array parameter")
    length = len(items)
    if mode == "append":
        items.append(value)
        placed = length
    else:
        if index is None:
            raise ValueError(f"{':'.join(parts)}: ':insert' requires an index")
        if index > length:
            raise ValueError(
                f"Error: Index {index} out of bounds. Valid insert positions "
                f"for {name} are 0..{length}. Use ':append' to add a new item.")
        items.insert(index, value)
        placed = index
    return validate(result, SCHEMA[scope], scope), placed


def _split_set_target(raw: str) -> tuple[str, str, int | None]:
    """@brief Split reserved append and insert tokens off a --set path.
    @details O(len(path)); recognizes the trailing ':append' or ':+' keyword
    and the ':insert:<Idx>' suffix with a canonical zero-based index; every
    other path is an assignment target.
    @param raw {str} Raw PATH operand of --set.
    @return {tuple[str, str, int | None]} Target path, mode ('assign', 'append',
    'insert'), and the insert index when mode is 'insert'.
    @satisfies REQ-265, REQ-266
    """
    if raw.endswith(":append") or raw.endswith(":+"):
        return raw.rsplit(":", 1)[0], "append", None
    match = re.search(r":insert:(0|[1-9][0-9]*)$", raw)
    if match:
        return raw[:match.start()], "insert", int(match.group(1))
    return raw, "assign", None


def _bootstrap_global(paths: dict[str, Path]) -> None:
    """@brief Create the global configuration file with defaults when missing.
    @details O(1) existence probe plus one atomic default write; creates the
    directory tree through write_scope before any configuration command
    proceeds. The local workspace file is never created here.
    @param paths {dict[str, Path]} Global and Local file destinations.
    @return {None} Global config.json exists with schema defaults on return.
    @throws OSError Directory creation, write, or replace failure.
    @satisfies REQ-272
    """
    path = paths["Global"]
    if not path.exists():
        write_scope(path, defaults("Global"))


def _scalar_text(value: Any) -> str:
    """@brief Render one value as JSON-style display text.
    @details O(1) for scalars; strings render JSON-quoted, booleans lowercase,
    containers compact JSON; credentials render unmasked plain text.
    @param value {Any} Configuration value.
    @return {str} Display text without code-like decorations.
    @satisfies REQ-250, REQ-274
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return "null"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _default_note(value: Any, spec: Parameter) -> str:
    """@brief Build the default or custom annotation for one value.
    @details O(1) deep equality against the schema default; custom notes carry
    the JSON-rendered default so --unset restoration is explicit.
    @param value {Any} Effective value.
    @param spec {Parameter} Schema node owning the default.
    @return {str} '(default)' or '(custom | default: <default>)'.
    @satisfies REQ-258
    """
    if value == spec.default:
        return "(default)"
    return f"(custom | default: {_scalar_text(spec.default)})"


def _is_section(spec: Parameter) -> bool:
    """@brief Report whether a schema node renders as a named section.
    @details O(1); sections are fixed-field dict nodes, excluding dynamic maps.
    @param spec {Parameter} Schema node.
    @return {bool} True for fixed-field object nodes.
    """
    return spec.kind is dict and spec.item is None and bool(spec.fields)


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """@brief Render a rectangular box-drawing table.
    @details O(N) cell scan; callers pre-flatten cells to plain text so no
    code-like syntax appears; performs no I/O or width truncation.
    @param headers {list[str]} Column labels.
    @param rows {list[list[str]]} Rectangular string cells.
    @return {list[str]} Border, header, separator, rows, and closing border.
    @satisfies REQ-250, REQ-251, REQ-259, REQ-260, REQ-261, REQ-264
    """
    widths = [max(len(row[i]) for row in [headers, *rows])
              for i in range(len(headers))]
    lines = ["┌" + "┬".join("─" * (width + 2) for width in widths) + "┐"]
    for index, row in enumerate([headers, *rows]):
        lines.append("│ " + " │ ".join(
            cell.ljust(width) for cell, width in zip(row, widths)) + " │")
        if index == 0:
            lines.append("├" + "┼".join("─" * (width + 2) for width in widths) + "┤")
    lines.append("└" + "┴".join("─" * (width + 2) for width in widths) + "┘")
    return lines


def _type_label(spec: Parameter) -> str:
    """@brief Resolve the flat discovery label for one schema node.
    @details O(1) lookup; constrained fields label as Selection.
    @param spec {Parameter} Schema node.
    @return {str} English input-type label.
    @satisfies REQ-251
    """
    return "Selection" if spec.choices else TYPE_LABELS[spec.kind]


def _params_type_label(spec: Parameter) -> str:
    """@brief Resolve the constrained type label used by --info headers.
    @details O(1); composes Array[...] and Map[String, ...] container labels
    and appends non-empty and boolean constraints to scalar bases.
    @param spec {Parameter} Schema node.
    @return {str} Bracketed English type and constraint label.
    @satisfies REQ-263
    """
    if spec.choices:
        return "Selection"
    if spec.kind is dict and spec.item is not None:
        return f"Map[String, {_type_label(spec.item)}]"
    if spec.kind is list and spec.item is not None:
        return f"Array[{_type_label(spec.item)}]"
    base = TYPE_LABELS[spec.kind]
    if spec.kind is str and not spec.empty:
        base = f"{base}: non-empty"
    if spec.kind is bool:
        base = f"{base}: true|false"
    return base


def _command_arg(text: str, style: str = "str") -> str:
    """@brief Render one example value as a shell-safe command argument.
    @details O(len(text)); 'raw' emits bare tokens, 'json' single-quotes
    JSON payloads, 'str' double-quotes plain strings and falls back to single
    quotes when the text itself contains double quotes.
    @param text {str} Example text.
    @param style {str} One of 'str', 'json', 'raw'.
    @return {str} Copy-pasteable shell argument.
    @satisfies REQ-252, REQ-263, REQ-264
    """
    if style == "raw":
        return text or '""'
    if style == "json":
        return f"'{text}'"
    if not text:
        return '""'
    return f"'{text}'" if '"' in text else f'"{text}"'


## @brief Fixed four-character indentation unit of one tree depth level.
# @details Every rendered tree node adds exactly this unit below its parent,
# so indentation derives exclusively from node depth (REQ-275).
# @satisfies REQ-275
TREE_INDENT = "    "

## @brief Continuation prefix rendered below a non-last tree node.
# @details Keeps the ancestor vertical guide above later siblings; equal in
# width to TREE_INDENT so sibling alignment stays depth-derived (REQ-275).
# @satisfies REQ-275
TREE_CONTINUATION = "│   "

## @brief Connector prefix of a tree node followed by siblings.
# @satisfies REQ-277, REQ-279
TREE_BRANCH = "├── "

## @brief Connector prefix of the last tree node among its siblings.
# @satisfies REQ-277, REQ-279
TREE_LAST_BRANCH = "└── "


def _tree_prefix(prefix: str, is_last: bool) -> tuple[str, str]:
    """@brief Resolve the branch and child prefixes of one tree node.
    @details O(1) concatenation; every node adds exactly one four-character
    indentation unit below its parent using the standard `├── ` or `└── `
    connector for the node line and `│   ` or four blanks for its children.
    The result depends only on the ancestor prefix and the sibling position,
    never on node name, value, or metadata text lengths.
    @param prefix {str} Ancestor continuation prefix.
    @param is_last {bool} Selects the `└── ` connector.
    @return {tuple[str, str]} Node branch prefix and its children depth prefix.
    @satisfies REQ-275, REQ-276
    """
    if is_last:
        return prefix + TREE_LAST_BRANCH, prefix + TREE_INDENT
    return prefix + TREE_BRANCH, prefix + TREE_CONTINUATION


def _append_metadata(lines: list[str], prefix: str, entries: list[str],
                     has_siblings: bool = False) -> None:
    """@brief Append parameter metadata as fixed-depth tree children.
    @details O(N) emission; each entry renders exactly one four-character
    indentation unit below the owning parameter with the standard `├── `
    connector, or `└── ` for the last entry when no later sibling follows so
    the tree stays strictly recursive. Entry text is emitted verbatim with no
    name-based padding.
    @param lines {list[str]} Output line accumulator.
    @param prefix {str} Depth prefix owned by the parameter children.
    @param entries {list[str]} Metadata texts in display order.
    @param has_siblings {bool} True when later siblings follow the metadata.
    @return {None} Appends rendered lines.
    @satisfies REQ-276, REQ-277
    """
    last_index = len(entries) - 1
    for index, text in enumerate(entries):
        closing = index == last_index and not has_siblings
        connector = TREE_LAST_BRANCH if closing else TREE_BRANCH
        lines.append(f"{prefix}{connector}{text}")


def _values_array(lines: list[str], branch: str, child: str, name: str,
                  item: Parameter, value: list[Any], path: str) -> None:
    """@brief Append the --print rendering of one array parameter.
    @details O(N); emits the count header with row or cell target syntax and the
    Idx table one depth level below the parameter, or the empty-list hint with a
    copy-pasteable append command.
    @param lines {list[str]} Output line accumulator.
    @param branch {str} Tree connector prefix of the parameter line.
    @param child {str} Children depth prefix of the parameter.
    @param name {str} Parameter name printed verbatim as the path token.
    @param item {Parameter} Array element schema.
    @param value {list[Any]} Effective array value.
    @param path {str} Canonical colon path of the parameter.
    @return {None} Appends rendered lines.
    @satisfies REQ-250, REQ-260, REQ-261, REQ-262, REQ-276, REQ-278
    """
    count = len(value)
    if count == 0:
        lines.append(
            f"{branch}{name} = (empty list — add row with: --set {path}:+ <value>)")
        return
    if _is_section(item):
        fields = list(item.fields)
        lines.append(
            f"{branch}{name} = ({count} rows | cell target: {path}:<Idx>:<Field> | add: :+)")
        rows = [[str(index)] + [_scalar_text(row.get(field_name)) for field_name in fields]
                for index, row in enumerate(value)]
        lines.extend(child + line for line in table(["Idx", *fields], rows))
        return
    lines.append(
        f"{branch}{name} = ({count} items | row target: {path}:<Idx> | add: :+)")
    rows = [[str(index), _scalar_text(entry)] for index, entry in enumerate(value)]
    lines.extend(child + line for line in table(["Idx", "Value"], rows))


def _values_map(lines: list[str], branch: str, child: str, name: str,
                value: dict[str, Any], path: str) -> None:
    """@brief Append the --print rendering of one dynamic map parameter.
    @details O(N); emits the entry-count header with key target syntax and the
    Key/Value table one depth level below the parameter, or the empty-map hint
    with a copy-pasteable set command.
    @param lines {list[str]} Output line accumulator.
    @param branch {str} Tree connector prefix of the parameter line.
    @param child {str} Children depth prefix of the parameter.
    @param name {str} Parameter name printed verbatim as the path token.
    @param value {dict[str, Any]} Effective map value.
    @param path {str} Canonical colon path of the parameter.
    @return {None} Appends rendered lines.
    @satisfies REQ-250, REQ-259, REQ-262, REQ-276, REQ-278
    """
    if not value:
        lines.append(
            f"{branch}{name} = (empty map — set key with: --set {path}:<Key> <value>)")
        return
    lines.append(
        f"{branch}{name} = ({len(value)} entries | key target: {path}:<Key>)")
    rows = [[_scalar_text(key), _scalar_text(entry)] for key, entry in value.items()]
    lines.extend(child + line for line in table(["Key", "Value"], rows))


def _values_node(lines: list[str], name: str, spec: Parameter, value: Any,
                 prefix: str, tokens: tuple[str, ...], is_last: bool,
                 file_path: Path | None = None) -> None:
    """@brief Append the --print rendering of one configuration node.
    @details O(subtree); sections recurse over their fields with the node child
    prefix, arrays and maps delegate to their renderers, and scalars plus
    selections print the value with the default or custom annotation; selection
    values add a table one depth level below the parameter. Indentation derives
    only from depth (REQ-275) and no name or value is padded (REQ-276).
    @param lines {list[str]} Output line accumulator.
    @param name {str} Node name printed verbatim as its CLI path token.
    @param spec {Parameter} Schema node.
    @param value {Any} Effective value at this node.
    @param prefix {str} Tree prefix inherited from the parent section.
    @param tokens {tuple[str, ...]} Canonical path tokens including the scope.
    @param is_last {bool} Selects the └── connector.
    @param file_path {Path | None} Scope file shown on scope-level badges.
    @return {None} Appends rendered lines.
    @satisfies REQ-250, REQ-257, REQ-258, REQ-259, REQ-275, REQ-276, REQ-278, REQ-279
    """
    branch, child = _tree_prefix(prefix, is_last)
    path = ":".join(tokens)
    if _is_section(spec):
        extra = f" - [File: {file_path}]" if file_path else ""
        lines.append(f"{branch}{name}{extra}  [Path: {path}]")
        entries = list(spec.fields.items())
        for index, (key, field_spec) in enumerate(entries):
            _values_node(lines, key, field_spec, (value or {}).get(key), child,
                         tokens + (key,), index == len(entries) - 1)
        return
    if spec.kind is list and spec.item is not None:
        _values_array(lines, branch, child, name, spec.item, value or [], path)
        return
    if spec.kind is dict and spec.item is not None:
        _values_map(lines, branch, child, name, value or {}, path)
        return
    note = _default_note(value, spec)
    if spec.choices:
        note = note[:-1] + f" | set: {path} <Value>)"
        lines.append(f"{branch}{name} = {_scalar_text(value)}  {note}")
        rows = [["[*]" if value == option else "[ ]", option]
                for option, _meaning in spec.choices]
        lines.extend(child + line for line in table(["Sel", "Value"], rows))
        return
    lines.append(f"{branch}{name} = {_scalar_text(value)}  {note}")


def render_values_tree(values: dict[str, dict[str, Any]],
                       paths: dict[str, Path] | None = None,
                       root_path: str | None = None) -> str:
    """@brief Render the effective configuration as an annotated box tree.
    @details O(N); without root_path prints the Application_Configuration root
    header plus every scope; with root_path prints only that subtree. Sections
    carry canonical [Path: ...] badges, scalars carry default or custom
    annotations, and arrays, maps, and selections render as actionable tables.
    Indentation derives only from node depth with four characters per level
    (REQ-275) and no node name or value is padded (REQ-276).
    @param values {dict[str, dict[str, Any]]} Effective values per scope.
    @param paths {dict[str, Path] | None} Scope files shown on scope badges.
    @param root_path {str | None} Optional colon path restricting the output.
    @return {str} Unicode tree without trailing newline.
    @throws ValueError Invalid root_path.
    @satisfies DES-009, REQ-250, REQ-257, REQ-258, REQ-259, REQ-260, REQ-261,
        REQ-262, REQ-275, REQ-276, REQ-278, REQ-279
    """
    lines: list[str] = []
    if root_path is None:
        lines.append("Application_Configuration - [Program: galias]")
        lines.append("│")
        scopes = list(SCHEMA)
        for index, scope in enumerate(scopes):
            _values_node(lines, scope, SCHEMA[scope], values[scope], "",
                         (scope,), index == len(scopes) - 1,
                         file_path=paths[scope] if paths else None)
        return "\n".join(lines)
    parts, spec = resolve_path(root_path)
    scope = parts[0]
    value = descend(values[scope], parts[1:])
    _values_node(lines, parts[-1], spec, value, "", tuple(parts), True,
                 file_path=paths[scope] if paths and len(parts) == 1 else None)
    return "\n".join(lines)


def _params_node(lines: list[str], name: str, spec: Parameter, prefix: str,
                 tokens: tuple[str, ...], is_last: bool) -> None:
    """@brief Append the --info documentation rendering of one node.
    @details O(subtree); prints the '[<type and constraints>] <description>'
    header, renders every metadata line and table as children exactly one
    four-character depth level deeper with standard `├── `/`└── ` connectors,
    and recurses into sections so child parameters nest under their parent.
    Indentation derives only from depth (REQ-275) and no name or value is
    padded (REQ-276).
    @param lines {list[str]} Output line accumulator.
    @param name {str} Node name printed verbatim as its CLI path token.
    @param spec {Parameter} Schema node.
    @param prefix {str} Tree prefix inherited from the parent section.
    @param tokens {tuple[str, ...]} Canonical path tokens including the scope.
    @param is_last {bool} Selects the └── connector.
    @return {None} Appends rendered lines.
    @satisfies REQ-251, REQ-263, REQ-264, REQ-275, REQ-276, REQ-277, REQ-278, REQ-279
    """
    branch, child = _tree_prefix(prefix, is_last)
    path = ":".join(tokens)
    label = _params_type_label(spec)
    if _is_section(spec):
        shown = f" - [{label}] {spec.description}" if len(tokens) > 1 else f" - {spec.description}"
        lines.append(f"{branch}{name}{shown}  [Path: {path}]")
        entries = list(spec.fields.items())
        block = json.dumps({key: field_spec.default
                            for key, field_spec in spec.fields.items()},
                           ensure_ascii=False)
        _append_metadata(lines, child, [
            f"Full overwrite : --set {path} {_command_arg(block, 'json')}",
            f"Reset block    : --unset {path}",
        ], has_siblings=bool(entries))
        for index, (key, field_spec) in enumerate(entries):
            _params_node(lines, key, field_spec, child, tokens + (key,),
                         index == len(entries) - 1)
        return
    lines.append(f"{branch}{name} - [{label}] {spec.description}")
    if spec.kind is list and spec.item is not None:
        _params_array(lines, child, path, spec, spec.item)
        return
    if spec.kind is dict and spec.item is not None:
        item_example = _command_arg(
            spec.item.example or "value",
            "str" if spec.item.kind is str else "json")
        block = _command_arg(spec.example or '{"KEY": "value"}', 'json')
        _append_metadata(lines, child, [
            f"Set/Add key    : --set {path}:<KEY> {item_example}",
            f"Remove key     : --unset {path}:<KEY>",
            f"Full overwrite : --set {path} {block}",
            f"Clear map      : --unset {path}",
        ])
        return
    if spec.choices:
        rows = [[option, "Yes" if option == spec.default else "No", meaning]
                for option, meaning in spec.choices]
        lines.append(f"{child}{TREE_BRANCH}Allowed Values :")
        lines.extend(child + TREE_CONTINUATION + line
                     for line in table(["Value", "Default", "Meaning"], rows))
        example = spec.example or spec.choices[-1][0]
        _append_metadata(lines, child, [
            f"Set cmd   : --set {path} {_command_arg(example, 'raw')}",
            f"Reset cmd : --unset {path}",
        ])
        return
    style = "str" if spec.kind is str else "raw"
    _append_metadata(lines, child, [
        f"Default : {_scalar_text(spec.default)} (restored via: --unset {path})",
        f"Set cmd : --set {path} {_command_arg(spec.example, style)}",
    ])


def _params_array(lines: list[str], prefix: str, path: str, spec: Parameter,
                  item: Parameter) -> None:
    """@brief Append the --info documentation of one array parameter.
    @details O(item schema); object arrays add the Item Schema table one depth
    level below its labelled entry and the complete append, insert, update,
    reset, replace, delete, overwrite, and clear command set. Every entry is a
    fixed-depth child of the owning parameter with standard connectors.
    @param lines {list[str]} Output line accumulator.
    @param prefix {str} Depth prefix owned by the parameter children.
    @param path {str} Canonical colon path of the array parameter.
    @param spec {Parameter} Array schema node owning the whole-value example.
    @param item {Parameter} Array element schema.
    @return {None} Appends rendered lines.
    @satisfies REQ-251, REQ-264, REQ-277, REQ-278
    """
    style = "str" if item.kind is str else "json"
    item_example = _command_arg(item.example, style)
    whole = _command_arg(spec.example or f"[{item.example}]", "json")
    commands = [f"Add new row    : --set {path}:+ {item_example}",
                f"Insert row idx : --set {path}:insert:0 {item_example}"]
    if _is_section(item):
        fields = list(item.fields)
        rows = []
        for field_name in fields:
            field_spec = item.fields[field_name]
            required = field_spec.default is None or (item is RULE and field_name == "pattern")
            default = "REQUIRED" if required else _scalar_text(field_spec.default)
            example = _command_arg(field_spec.example,
                                   "str" if field_spec.kind is str else "raw")
            rows.append([field_name, f"[{_params_type_label(field_spec)}]",
                         default, f"{field_spec.description} (e.g., {example})"])
        lines.append(f"{prefix}{TREE_BRANCH}Item Schema    :")
        lines.extend(prefix + TREE_CONTINUATION + line for line in table(
            ["Field", "Type & Constraints", "Default / Req", "Description & Example"], rows))
        commands += [
            f"Update cell    : --set {path}:0:{fields[0]} "
            f"{_command_arg(item.fields[fields[0]].example, style)}",
            f"Reset cell     : --unset {path}:0:{fields[0]}",
            f"Replace row    : --set {path}:0 {item_example}",
        ]
    commands += [f"Delete row idx : --unset {path}:0 (auto re-indexes list)",
                 f"Full overwrite : --set {path} {whole}",
                 f"Clear all rows : --unset {path}"]
    _append_metadata(lines, prefix, commands)


def render_params_tree(root_path: str | None = None) -> str:
    """@brief Render the schema-derived `--info` parameter documentation tree.
    @details O(N); without root_path prints the whole Application_Configuration
    documentation tree; with root_path prints only that subtree or parameter.
    Indentation derives only from node depth with four characters per level
    (REQ-275) and metadata renders as fixed-depth children (REQ-277).
    @param root_path {str | None} Optional colon path restricting the output.
    @return {str} Unicode tree without trailing newline.
    @throws ValueError Invalid root_path.
    @satisfies REQ-251, REQ-263, REQ-264, REQ-275, REQ-277, REQ-278, REQ-279
    """
    lines: list[str] = []
    if root_path is None:
        lines.append("Application_Configuration - General settings root")
        lines.append("│")
        scopes = list(SCHEMA.items())
        for index, (scope, spec) in enumerate(scopes):
            _params_node(lines, scope, spec, "", (scope,), index == len(scopes) - 1)
        return "\n".join(lines)
    parts, spec = resolve_path(root_path)
    _params_node(lines, parts[-1], spec, "", tuple(parts), True)
    return "\n".join(lines)


def print_raw(paths: dict[str, Path]) -> None:
    """@brief Emit exact stored bytes with identification on stderr only.
    @details O(N) reads; missing files are reported and skipped. No decoding,
    JSON parsing, masking, reformatting, or added stdout newline.
    @param paths {dict[str, Path]} Selected scope paths in output order.
    @return {None} Writes file bytes to stdout.buffer.
    @throws OSError File read or output failure.
    @satisfies REQ-097, REQ-249, REQ-274
    """
    for scope, path in paths.items():
        try:
            payload = path.read_bytes()
        except FileNotFoundError:
            print(f"{scope}: {path} (missing)", file=sys.stderr)
            continue
        print(f"{scope}: {path}", file=sys.stderr)
        sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def _assign_confirmation(parts: list[str], spec: Parameter, value: Any,
                         target: str) -> str:
    """@brief Build the English confirmation line for one --set mutation.
    @details O(D) schema walks; row, cell, map-key, array, and map overwrites
    name the exact assigned target and index so output matches the --print
    identifiers.
    @param parts {list[str]} Canonical path tokens of the mutation target.
    @param spec {Parameter} Terminal schema node of the target.
    @param value {Any} Assigned value.
    @param target {str} Raw target path text.
    @return {str} Single-line English confirmation.
    @satisfies REQ-245, REQ-267, REQ-271
    """
    if len(parts) <= 2:
        return f"Configuration saved: {target}"
    parent_spec = resolve_path(":".join(parts[:-1]))[1]
    grand_spec = resolve_path(":".join(parts[:-2]))[1]
    if parent_spec.kind is list:
        item = parent_spec.item
        if item is not None and item.kind is dict:
            return f"Object at index {parts[-1]} replaced successfully."
        return f"Row at index {parts[-1]} updated successfully."
    if grand_spec.kind is list:
        return (f"Property '{parts[-1]}' at index {parts[-2]} updated to "
                f"{_scalar_text(value)}.")
    if parent_spec.kind is dict and parent_spec.item is not None:
        return f"Key '{parts[-1]}' set in {':'.join(parts[:-1])}."
    return f"Configuration saved: {target}"


def _overwrite_confirmation(parts: list[str], spec: Parameter, value: Any) -> str:
    """@brief Build the confirmation for a whole array or map overwrite.
    @details O(1); reports the item or key count and the resulting index range.
    @param parts {list[str]} Canonical path tokens of the overwritten container.
    @param spec {Parameter} Container schema node.
    @param value {Any} New container value.
    @return {str} Single-line English confirmation.
    @satisfies REQ-271
    """
    name = parts[-1]
    if spec.kind is list:
        count = len(value)
        if count == 0:
            return f"Array {name} overwritten with 0 items."
        return f"Array {name} overwritten with {count} items (indices 0..{count - 1})."
    return f"Map {name} overwritten with {len(value)} keys."


def _unset_confirmation(parts: list[str], spec: Parameter,
                        result: dict[str, Any]) -> str:
    """@brief Build the English confirmation line for one --unset mutation.
    @details O(D) schema walks; row deletions report the contiguous
    re-indexing, cell resets name the restored property, and container clears
    print a WARNING that defaults apply again.
    @param parts {list[str]} Canonical path tokens of the unset target.
    @param spec {Parameter} Terminal schema node of the target.
    @param result {dict[str, Any]} Validated scope after the mutation.
    @return {str} Single-line English confirmation.
    @satisfies REQ-247, REQ-269, REQ-271
    """
    path = ":".join(parts)
    if len(parts) == 1:
        return f"WARNING: All parameters reset to defaults for {parts[0]}."
    if len(parts) >= 3:
        parent_spec = resolve_path(":".join(parts[:-1]))[1]
        grand_spec = resolve_path(":".join(parts[:-2]))[1]
        if parent_spec.kind is list:
            remaining = len(descend(result, parts[1:-1]))
            tail = ("Array is now empty." if remaining == 0 else
                    f"Array re-indexed ({remaining} items remaining, "
                    f"indices 0..{remaining - 1}).")
            return f"Item at index {parts[-1]} removed. {tail}"
        if grand_spec.kind is list:
            return f"Property '{parts[-1]}' at index {parts[-2]} restored to default."
        if parent_spec.kind is dict and parent_spec.item is not None:
            return f"Key '{parts[-1]}' removed from {':'.join(parts[:-1])}."
    if spec.kind is list:
        return f"WARNING: All items removed from {path}; defaults apply."
    if spec.kind is dict and spec.item is not None:
        return f"WARNING: All keys removed from {path}; defaults apply."
    if spec.kind is dict:
        return f"WARNING: All parameters reset to defaults for {path}."
    return f"Restored default for {path}."


def execute(args: list[str], paths: dict[str, Path]) -> None:
    """@brief Execute one standalone configuration command.
    @details O(N) selected-scope processing. Bootstraps the missing global
    configuration file before every command; help and raw output avoid JSON
    reads; --print and --info accept one optional colon path restricting the
    tree; mutations validate fully before exactly one atomic write of the
    selected scope and print an English confirmation.
    @param args {list[str]} Command plus operands, or command plus --help.
    @param paths {dict[str, Path]} Global and Local file destinations.
    @return {None} Emits JSON, trees, raw bytes, help, or a confirmation.
    @throws ValueError Invalid command operands, path, input, or stored JSON.
    @throws OSError Configuration read, bootstrap, or write failure.
    @satisfies REQ-014, REQ-243, REQ-245, REQ-246, REQ-247, REQ-248, REQ-250,
        REQ-251, REQ-253, REQ-265, REQ-266, REQ-267, REQ-268, REQ-269, REQ-271, REQ-272
    """
    command, *operands = args
    _bootstrap_global(paths)
    if operands == ["--help"]:
        print(COMMAND_HELP[command])
        print(INPUT_HELP)
        return
    if command == "--print-raw":
        if len(operands) > 1 or (operands and operands[0] not in SCHEMA):
            raise ValueError(COMMAND_HELP[command])
        print_raw({scope: paths[scope] for scope in (operands or list(SCHEMA))})
        return
    if command in ("--print", "--info"):
        if len(operands) > 1:
            raise ValueError(COMMAND_HELP[command])
        if command == "--info":
            print(render_params_tree(operands[0] if operands else None))
            return
        values = {scope: defaults(scope) | read_scope(paths[scope], scope)
                  for scope in SCHEMA}
        print(render_values_tree(values, paths, operands[0] if operands else None))
        return
    arity = {"--set": 2, "--get": 1, "--unset": 1}[command]
    if len(operands) != arity:
        raise ValueError(COMMAND_HELP[command])
    if command == "--get":
        parts, _spec = resolve_path(operands[0])
        scope = parts[0]
        value = descend(defaults(scope) | read_scope(paths[scope], scope), parts[1:])
        print(json.dumps(value, indent=2, ensure_ascii=False))
        return
    path = operands[0]
    target, mode, insert_index = (_split_set_target(path)
                                  if command == "--set" else (path, "assign", None))
    parts, spec = resolve_path(target)
    scope = parts[0]
    data = read_scope(paths[scope], scope)
    if command == "--unset":
        result = change_scope(data, parts, None, True)
        write_scope(paths[scope], result)
        print(_unset_confirmation(parts, spec, result))
        return
    if mode in ("append", "insert"):
        item_spec = spec.item
        if spec.kind is not list or item_spec is None:
            raise ValueError(f"{target}: ':append' and ':insert' require an array parameter")
        item = parse_value(operands[1], item_spec, target)
        result, placed = _mutate_array(data, parts, item, mode, insert_index)
        write_scope(paths[scope], result)
        noun = "Object" if item_spec.kind is dict else "Item"
        verb = "appended to" if mode == "append" else (
            "inserted into" if item_spec.kind is dict else "inserted at")
        print(f"{noun} {verb} {parts[-1]} at index {placed}."
              + (" Subsequent items shifted." if mode == "insert" else ""))
        return
    value = parse_value(operands[1], spec, target)
    result = change_scope(data, parts, value, False)
    write_scope(paths[scope], result)
    is_container = spec.kind is list or (spec.kind is dict and spec.item is not None)
    if len(parts) == 2 and is_container:
        print(_overwrite_confirmation(parts, spec, value))
    else:
        print(_assign_confirmation(parts, spec, value, target))
