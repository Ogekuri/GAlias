"""@brief Schema-driven GAlias configuration management.
@details Owns configuration metadata, hierarchical JSON access, atomic
persistence, and CLI rendering. Alias execution stays in core; this module
performs no subprocess execution and implements no legacy migration.
@satisfies DES-010, REQ-014, REQ-242, REQ-253
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
    @param kind {type} Exact JSON-compatible Python type of the value.
    @param description {str} English field meaning and input constraints.
    @param default {Any} Default applied when the key is absent.
    @param fields {dict[str, Parameter]} Object field schema; empty for scalars.
    @param item {Parameter | None} Array element schema; None for non-arrays.
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
    item: "Parameter | None" = None  ## @brief Array element schema.
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
# constrained choices today; the schema and renderers fully support them.
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
TYPE_LABELS = {str: "String", int: "Integer", bool: "Boolean",
               list: "Array", dict: "Dictionary"}

## @brief Management command syntax and descriptions used by both help paths.
# @satisfies REQ-243, REQ-252
COMMAND_HELP = {
    "--print-raw": "--print-raw [Global|Local]: emit exact file bytes; labels go to stderr.",
    "--print": "--print: show the effective configuration tree with tables for complex values.",
    "--params": "--params: show every path with input type, description, and input example.",
    "--set": "--set PATH VALUE: set one field, array, object, or scope from one argument.",
    "--unset": "--unset PATH: remove a key, scope, array entry, or optional object field.",
    "--get": "--get PATH: extract an effective value or scope as JSON.",
}

## @brief Shared input instructions appended to configuration command help.
# @satisfies REQ-244, REQ-247, REQ-252
INPUT_HELP = r"""Paths are case-sensitive and use ':' separators: Global:edit_command,
Local:work, Local:ver_rules:0:pattern. Array indices are zero-based; set an
existing index or replace the whole array to add entries. Use Global or Local
alone to get, replace (--set JSON object), or clear (--unset) a scope.
Unset top-level keys restores defaults; unset array entries removes them;
unset regex is allowed only for a ! exclusion rule. Scope clearing prints a warning.
Strings accept plain text or JSON strings. Objects and arrays require valid JSON
as one shell-quoted argument. JSON regex backslashes must be doubled.
Examples:
  g --set Global:edit_command 'vim -f'
  g --set Global:edit_command "$EDITOR"
  g --set Local:ver_rules '[{"pattern":"VERSION","regex":"(\\d+\\.\\d+\\.\\d+)"}]'
  g --set Local:ver_rules:0 '{"pattern":"!vendor/**"}'
  g --get Local:ver_rules:0:pattern
  g --unset Local:default_commit_module
  g --unset Local
The shell expands environment variables before invocation; values are stored
exactly as received and are never evaluated as shell commands. Use --params for
every field, its input type, and an input example. --get resolves absent
top-level keys from defaults; --print-raw shows only bytes on disk.
Global storage: $HOME/.config/galias/config.json. Local storage: .galias.conf
at the repository root, or the current directory outside a repository.
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
    @details O(D) traversal; indices must be canonical non-negative decimals.
    @param path {str} Scope followed by optional fields and array indices.
    @return {tuple[list[str], Parameter]} Path tokens and terminal schema node.
    @throws ValueError Unknown scope, unknown field, empty segment, or invalid index.
    @satisfies REQ-244, REQ-248
    """
    parts = path.split(":")
    if parts[0] not in SCHEMA or any(not part for part in parts):
        raise ValueError(f"Invalid configuration path: {path}")
    spec = SCHEMA[parts[0]]
    for part in parts[1:]:
        if part in spec.fields:
            spec = spec.fields[part]
        elif spec.item is not None and re.fullmatch(r"0|[1-9][0-9]*", part):
            spec = spec.item
        else:
            raise ValueError(f"Unknown configuration path: {path}")
    return parts, spec


def validate(value: Any, spec: Parameter, path: str) -> Any:
    """@brief Validate and copy a canonical JSON value.
    @details O(N) recursive validation rejecting wrong types, unknown object
    fields, and invalid rule structures; compiles rule regexes. Normalizes
    only fields marked strip; performs no I/O.
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
    JSON values decode without shell evaluation.
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
    the target directory then renames it. Cleans the temporary file on failure
    and creates parent directories only for this explicit mutation path.
    @param path {Path} Selected destination.
    @param data {dict[str, Any]} Validated canonical scope object.
    @return {None} Persisted JSON ends with one newline.
    @throws OSError Directory creation, write, flush, or replace failure.
    @satisfies REQ-014, REQ-097, REQ-253, REQ-254
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
    """@brief Traverse existing JSON fields and array indices.
    @details O(D) traversal rejecting missing members and out-of-range indices.
    @param data {Any} Effective scope or subtree.
    @param parts {list[str]} Schema-validated relative path tokens.
    @return {Any} Referenced subtree; callers copy before mutation.
    @throws ValueError Missing field or out-of-range array index.
    @satisfies REQ-244, REQ-246, REQ-248
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
    read. Nested array deletion is guarded by an existence probe.
    @param data {dict[str, Any]} Persisted canonical scope values.
    @param parts {list[str]} Schema-validated full path including the scope.
    @param value {Any} Parsed replacement; ignored when unset is True.
    @param unset {bool} Delete instead of assign.
    @return {dict[str, Any]} Validated scope after mutation.
    @throws ValueError Missing nested member or invalid resulting structure.
    @satisfies REQ-245, REQ-247, REQ-248
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
            descend(parent, [parts[-1]])
            index = int(parts[-1])
            if unset:
                del parent[index]
            else:
                parent[index] = value
        elif unset:
            parent.pop(parts[-1], None)
        else:
            parent[parts[-1]] = value
    return validate(result, SCHEMA[scope], scope)


def plain(value: Any) -> str:
    """@brief Render one scalar as plain text without code-like syntax.
    @details O(1) formatting; strings print verbatim, booleans lowercase,
    other scalars via str; complex values are never passed here.
    @param value {Any} Scalar configuration value.
    @return {str} Unquoted human-readable text.
    @satisfies REQ-250
    """
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """@brief Render a rectangular box-drawing table.
    @details O(N) cell scan; callers pre-flatten cells to plain text so no
    code-like syntax appears; performs no I/O or width truncation.
    @param headers {list[str]} Column labels.
    @param rows {list[list[str]]} Rectangular string cells.
    @return {list[str]} Border, header, separator, rows, and closing border.
    @satisfies REQ-250, REQ-251
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
    """@brief Resolve the discovery label for one schema node.
    @details O(1) lookup; constrained fields label as Selection.
    @param spec {Parameter} Schema node.
    @return {str} English input-type label.
    @satisfies REQ-251
    """
    return "Selection" if spec.choices else TYPE_LABELS[spec.kind]


def _array_rows(value: list[Any]) -> list[list[str]]:
    """@brief Flatten array entries into plain table cells.
    @details O(N) traversal; object entries join their present fields as
    `key = value` text separated by a middle dot, avoiding code-like syntax.
    @param value {list[Any]} Effective array value.
    @return {list[list[str]]} One `[index, text]` row per entry.
    @satisfies REQ-250
    """
    rows = []
    for index, item in enumerate(value):
        if isinstance(item, dict):
            text = " · ".join(f"{key} = {plain(part)}" for key, part in item.items())
        else:
            text = plain(item)
        rows.append([str(index), text])
    return rows


def render_tree(values: dict[str, dict[str, Any]] | None = None) -> str:
    """@brief Render schema discovery or the effective configuration.
    @details O(N) schema traversal; scopes form tree branches. Discovery lines
    label the input type, description, and input example, adding allowed-value
    tables for constrained fields; effective output prints scalars as plain
    text and arrays as Index/Value tables.
    @param values {dict[str, dict[str, Any]] | None} Effective scopes; None selects params.
    @return {str} Unicode tree with box-drawing tables, without trailing newline.
    @satisfies REQ-192, REQ-250, REQ-251
    """
    lines = ["GAlias Configuration" if values is not None else "GAlias Parameters"]
    for scope_index, (scope, schema) in enumerate(SCHEMA.items()):
        last_scope = scope_index == len(SCHEMA) - 1
        prefix = "    " if last_scope else "│   "
        lines.append(("└── " if last_scope else "├── ") + scope + " - " + schema.description)
        fields = list(schema.fields.items())
        for index, (key, spec) in enumerate(fields):
            last = index == len(fields) - 1
            branch = prefix + ("└── " if last else "├── ")
            indent = prefix + ("    " if last else "│   ")
            label = _type_label(spec)
            if values is None:
                head = f"{branch}{key} [{label}] {spec.description}"
                if spec.choices:
                    lines.append(head + ". Allowed values:")
                    rows = [[value, meaning] for value, meaning in spec.choices]
                    lines.extend(indent + line for line in table(["Value", "Meaning"], rows))
                    lines.append(f"{indent}(Input example: {spec.example})")
                else:
                    lines.append(f"{head} (Input example: {spec.example})")
            elif spec.kind not in (dict, list):
                lines.append(f"{branch}{key} = {plain(values[scope][key])}")
            else:
                lines.append(f"{branch}{key}")
            if spec.kind is list and spec.item is not None:
                if values is None:
                    sub = prefix + ("    " if last else "│   ")
                    for name, field_spec in spec.item.fields.items():
                        field_head = (f"{sub}{scope}:{key}:<index>:{name} "
                                      f"[{_type_label(field_spec)}] {field_spec.description}")
                        lines.append(f"{field_head} (Input example: {field_spec.example})")
                    lines.append(f"{sub}{key} [{label}] {spec.description} "
                                 f"(Input example: {spec.example})")
                    lines.append(f"{sub}Input: one shell-quoted JSON array of objects.")
                else:
                    rows = _array_rows(values[scope][key])
                    lines.extend(indent + line for line in table(["Index", "Value"], rows))
    if values is None:
        lines.append("Input: strings as one argument; scope objects and arrays as shell-quoted JSON.")
        lines.append("See --set --help for quoting, environment expansion, and nested examples.")
    return "\n".join(lines)


def print_raw(paths: dict[str, Path]) -> None:
    """@brief Emit exact stored bytes with identification on stderr only.
    @details O(N) reads; missing files are reported and skipped. No decoding,
    JSON parsing, masking, reformatting, or added stdout newline.
    @param paths {dict[str, Path]} Selected scope paths in output order.
    @return {None} Writes file bytes to stdout.buffer.
    @throws OSError File read or output failure.
    @satisfies REQ-097, REQ-249
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


def execute(args: list[str], paths: dict[str, Path]) -> None:
    """@brief Execute one standalone configuration command.
    @details O(N) selected-scope processing; help and params avoid reads; raw
    output bypasses JSON validation. Mutations validate fully before exactly
    one atomic write of the selected scope.
    @param args {list[str]} Command plus operands, or command plus --help.
    @param paths {dict[str, Path]} Global and Local file destinations.
    @return {None} Emits JSON, tree, raw bytes, help, or a mutation confirmation.
    @throws ValueError Invalid command operands, path, input, or stored JSON.
    @throws OSError Configuration read or write failure.
    @satisfies REQ-014, REQ-243, REQ-245, REQ-246, REQ-247, REQ-248, REQ-253
    """
    command, *operands = args
    if operands == ["--help"]:
        print(COMMAND_HELP[command])
        print(INPUT_HELP)
        return
    if command == "--print-raw":
        if len(operands) > 1 or (operands and operands[0] not in SCHEMA):
            raise ValueError(COMMAND_HELP[command])
        print_raw({scope: paths[scope] for scope in (operands or list(SCHEMA))})
        return
    arity = {"--set": 2, "--get": 1, "--unset": 1}.get(command, 0)
    if len(operands) != arity:
        raise ValueError(COMMAND_HELP[command])
    if command == "--params":
        print(render_tree())
        return
    if command == "--print":
        values = {scope: defaults(scope) | read_scope(paths[scope], scope)
                  for scope in SCHEMA}
        print(render_tree(values))
        return
    path = operands[0]
    parts, spec = resolve_path(path)
    scope = parts[0]
    data = read_scope(paths[scope], scope)
    if command == "--get":
        value = descend(defaults(scope) | data, parts[1:])
        print(json.dumps(value, indent=2, ensure_ascii=False))
        return
    value = parse_value(operands[1], spec, path) if command == "--set" else None
    result = change_scope(data, parts, value, command == "--unset")
    write_scope(paths[scope], result)
    if command == "--unset" and len(parts) == 1:
        print(f"WARNING: Removed all persisted parameters for {scope}; defaults apply.")
    else:
        print(f"Configuration saved: {path}")
