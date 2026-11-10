"""@brief Isolated configuration contract tests, ordered by dependency level.
@details HDT Refactorer: replaces the removed writer tests; preserves loader
and default coverage while adding schema, path, rendering, persistence, and
CLI failure coverage. Filesystem, process, and network boundaries are mocked.
@satisfies DES-010, REQ-014, REQ-097, REQ-242, REQ-243, REQ-248
"""

import copy
import io
import json
from pathlib import Path
from unittest import mock

import pytest

from git_alias import configuration as config
from git_alias import core


@pytest.mark.parametrize("scope", ["Global", "Local"])
def test_schema_covers_runtime_keys_and_discovery(scope):
    """@brief Verify schema/default/discovery parity for each scope.
    @details Level 0; O(N) pure metadata checks with explicit inventories.
    @param scope {str} Scope under test.
    @return {None} Every configured field is discoverable with type and example.
    @satisfies DES-010, REQ-242, REQ-251
    """
    expected_output = set(
        core.GLOBAL_CONFIG_KEYS if scope == "Global" else core.LOCAL_CONFIG_KEYS
    )
    actual = config.defaults(scope)
    assert set(actual) == expected_output
    assert actual == {key: core.DEFAULT_CONFIG[key] for key in expected_output}
    rendered = config.render_tree()
    for key in expected_output:
        assert key in rendered
        assert config.resolve_path(f"{scope}:{key}")[1] is config.SCHEMA[scope].fields[key]
        assert "(Input example: " in rendered


def test_params_lines_label_types_and_allowed_values():
    """@brief Enforce typed discovery lines and allowed-value tables.
    @details Level 0; checks String/Array labels, per-field input examples,
    zero-based path hints, and Selection tables through a synthetic schema.
    @return {None} Every field line carries type, description, and example.
    @satisfies REQ-242, REQ-251
    """
    expected_output = ("Value", "Meaning", "MEMORIA", "(Input example: MEMORIA)")
    original = config.SCHEMA["Global"].fields["edit_command"]
    constrained = config.Parameter(
        str, "Cache strategy", "MEMORIA",
        choices=(("NESSUNA", "No cache"), ("MEMORIA", "RAM cache"), ("DISCO", "Disk cache")),
        example="MEMORIA")
    try:
        config.SCHEMA["Global"].fields["edit_command"] = constrained
        rendered = config.render_tree()
    finally:
        config.SCHEMA["Global"].fields["edit_command"] = original
    for token in expected_output:
        assert token in rendered
    assert "[Selection] Cache strategy. Allowed values:" in rendered
    assert "[String] Default conventional-commit scope" in config.render_tree()
    assert "Local:ver_rules:<index>:pattern [String]" in config.render_tree()


@pytest.mark.parametrize("path", ["", "global", "Global:", "Local::work", "Local:editor",
                                  "Global:work", "Local:ver_rules:-1", "Local:ver_rules:01",
                                  "Local:ver_rules:0:glob", "Local:work:child"])
def test_invalid_path_rejected(path):
    """@brief Reject unknown and malformed configuration paths.
    @details Level 0; schema-only validation; no I/O.
    @param path {str} Invalid path specimen.
    @return {None} ValueError observed.
    @satisfies REQ-244, REQ-248
    """
    expected_exception = ValueError
    with pytest.raises(expected_exception):
        config.resolve_path(path)


@pytest.mark.parametrize("value", [None, True, 12, {}, [["README.md", "x"]],
                                   [{"glob": "README.md", "regex": "x"}],
                                   [{"pattern": "README.md"}],
                                   [{"pattern": "README.md", "regex": "["}],
                                   [{"pattern": "", "regex": "x"}]])
def test_invalid_rules_rejected(value):
    """@brief Reject noncanonical rule arrays before persistence.
    @details Level 0; type, structure, required-field, and regex failures.
    @param value {Any} Invalid rule-array specimen.
    @return {None} ValueError observed.
    @satisfies REQ-207, REQ-248
    """
    expected_exception = ValueError
    spec = config.SCHEMA["Local"].fields["ver_rules"]
    with pytest.raises(expected_exception):
        config.validate(value, spec, "Local:ver_rules")


def test_nested_edits_copy_defaults_and_remove_items():
    """@brief Exercise nested set/unset without mutating schema defaults.
    @details Level 0; O(N) in-memory mutation with independent expected data.
    @return {None} Defaults stay unchanged and array deletion shifts indices.
    @satisfies REQ-244, REQ-245, REQ-247
    """
    expected_output = config.defaults("Local")
    changed = config.change_scope({}, ["Local", "ver_rules", "0", "pattern"], "VERSION", False)
    removed = config.change_scope(changed, ["Local", "ver_rules", "0"], None, True)
    assert changed["ver_rules"][0]["pattern"] == "VERSION"
    assert removed["ver_rules"] == expected_output["ver_rules"][1:]
    assert config.defaults("Local") == expected_output


def test_optional_regex_unset_and_required_field_rejection():
    """@brief Permit exclusion regex removal and reject incomplete rules.
    @details Level 0; validates the resulting object after nested deletion.
    @return {None} Optional field removed; required deletion raises ValueError.
    @satisfies REQ-247, REQ-248
    """
    expected_output = {"ver_rules": [{"pattern": "!vendor/**"}]}
    data = {"ver_rules": [{"pattern": "!vendor/**", "regex": "x"}]}
    actual = config.change_scope(data, ["Local", "ver_rules", "0", "regex"], None, True)
    assert actual == expected_output
    with pytest.raises(ValueError):
        config.change_scope({}, ["Local", "ver_rules", "0", "pattern"], None, True)


def test_tree_tables_and_canonical_global_order():
    """@brief Verify plain-text scalars, complex tables, and canonical order.
    @details Level 0; scalars render unquoted, arrays render as box-drawing
    Index/Value tables, and the eight REQ-192 keys stay contiguous in order.
    @return {None} Print and params preserve every canonical key.
    @satisfies REQ-192, REQ-250
    """
    expected_output = list(core.GLOBAL_CONFIG_KEYS)
    actual = config.render_tree({scope: config.defaults(scope) for scope in config.SCHEMA})
    positions = [actual.index(key + " =") for key in expected_output]
    assert positions == sorted(positions)
    assert all(char in actual for char in "┌┬┐├┼┤└┴┘─│")
    assert "edit_command = edit\n" in actual
    assert '"edit_command"' not in actual
    assert "pattern = README.md" in actual
    assert "Index" in actual and "Value" in actual


@pytest.fixture
def sandbox(monkeypatch):
    """@brief Provide an in-memory configuration filesystem and isolated state.
    @details Level 1 fixture; replaces file reads, writes, path lookup, and
    update checks with synthetic boundaries and copied state.
    @param monkeypatch {pytest.MonkeyPatch} Automatically restored patches.
    @return {dict[Path, bytes]} Synthetic files keyed by selected scope path.
    """
    files = {}
    paths = {"Global": Path("/synthetic/home/.config/galias/config.json"),
             "Local": Path("/synthetic/repo/.galias.conf")}

    def read_bytes(path):
        """@brief Read synthetic bytes or report a missing file.
        @details O(1) mapping lookup; no physical I/O.
        @param path {Path} Synthetic path.
        @return {bytes} Stored content.
        @throws FileNotFoundError Missing synthetic path.
        """
        if path not in files:
            raise FileNotFoundError(str(path))
        return files[path]

    def read_text(path, encoding="utf-8"):
        """@brief Decode synthetic file bytes.
        @details O(N) decode propagating missing-file and encoding failures.
        @param path {Path} Synthetic path.
        @param encoding {str} Requested codec.
        @return {str} Decoded content.
        @throws FileNotFoundError Missing file.
        @throws UnicodeError Invalid encoding.
        """
        return read_bytes(path).decode(encoding)

    def save(path, data):
        """@brief Record the externally observable persisted JSON.
        @details O(N) serialization mutating only the selected in-memory file.
        @param path {Path} Selected destination.
        @param data {dict} Validated canonical scope.
        @return {None} Synthetic file updated.
        """
        files[path] = json.dumps(data).encode()

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setattr(Path, "read_text", read_text)
    monkeypatch.setattr(Path, "exists", lambda path: path in files)
    monkeypatch.setattr(core, "get_git_root", lambda: Path("/synthetic/repo"))
    monkeypatch.setattr(core, "get_global_config_path", lambda home=None: paths["Global"])
    monkeypatch.setattr(core, "CONFIG", copy.deepcopy(core.DEFAULT_CONFIG))
    monkeypatch.setattr(config, "write_scope", save)
    monkeypatch.setattr(core, "check_for_newer_version", mock.Mock(return_value=None))
    return files, paths


@pytest.mark.parametrize("scope,key", [(scope, key) for scope, schema in config.SCHEMA.items()
                                       for key in schema.fields])
def test_every_field_roundtrips_and_unsets(sandbox, capsys, scope, key):
    """@brief Enforce CLI parity for every schema field automatically.
    @details Level 2; default-shaped inputs traverse routing, parsing,
    validation, and get/unset behavior using isolated persistence.
    @param sandbox {tuple} Synthetic filesystem and paths.
    @param capsys {pytest.CaptureFixture} Captured output.
    @param scope {str} Field scope.
    @param key {str} Canonical field name.
    @return {None} Set/get roundtrip succeeds; unset restores the default.
    @satisfies DES-010, REQ-242, REQ-243, REQ-245, REQ-246, REQ-247
    """
    files, paths = sandbox
    expected_output = config.defaults(scope)[key]
    core.main(["--set", f"{scope}:{key}", json.dumps(expected_output)], check_updates=False)
    capsys.readouterr()
    core.main(["--get", f"{scope}:{key}"], check_updates=False)
    assert json.loads(capsys.readouterr().out) == expected_output
    core.main(["--unset", f"{scope}:{key}"], check_updates=False)
    assert json.loads(files[paths[scope]]) == {}
    capsys.readouterr()
    core.main(["--get", f"{scope}:{key}"], check_updates=False)
    assert json.loads(capsys.readouterr().out) == expected_output


def test_selected_scope_isolation_and_canonical_keys(sandbox, capsys):
    """@brief Preserve the other file and drop out-of-scope stored keys.
    @details Level 2; corrupt local content cannot block global configuration.
    @param sandbox {tuple} Synthetic files and paths.
    @param capsys {pytest.CaptureFixture} Captured output.
    @return {None} Only the selected file changes.
    @satisfies REQ-015, REQ-253, REQ-255
    """
    files, paths = sandbox
    expected_output = b"not json\r\n"
    files[paths["Local"]] = expected_output
    files[paths["Global"]] = b'{"editor":"old","gp_command":"viewer"}'
    core.main(["--set", "Global:edit_command", "--dev"], check_updates=False)
    assert json.loads(files[paths["Global"]]) == {"gp_command": "viewer", "edit_command": "--dev"}
    assert files[paths["Local"]] == expected_output
    assert "Configuration saved" in capsys.readouterr().out


def test_scope_object_and_nested_access(sandbox, capsys):
    """@brief Set whole scopes and extract nested object/scalar values.
    @details Level 2; exercises array and dictionary input plus scope clearing.
    @param sandbox {tuple} Synthetic filesystem and paths.
    @param capsys {pytest.CaptureFixture} Captured output.
    @return {None} JSON subtrees match input and clearing restores defaults.
    @satisfies REQ-245, REQ-246, REQ-247
    """
    files, paths = sandbox
    expected_output = {"pattern": "!vendor/**"}
    core.main(["--set", "Local", json.dumps({"ver_rules": [expected_output]})], check_updates=False)
    capsys.readouterr()
    core.main(["--get", "Local:ver_rules:0"], check_updates=False)
    assert json.loads(capsys.readouterr().out) == expected_output
    core.main(["--set", "Local:ver_rules:0:pattern", "!other/**"], check_updates=False)
    core.main(["--unset", "Local"], check_updates=False)
    assert json.loads(files[paths["Local"]]) == {}
    assert "WARNING:" in capsys.readouterr().out


@pytest.mark.parametrize("args", [
    ["--set"], ["--get"], ["--unset"], ["--params", "extra"], ["--print", "extra"],
    ["--print-raw", "bad"], ["--get", "Local:work", "extra"],
    ["--set", "Local:ver_rules", "{"], ["--set", "Local", '{"work":true}'],
    ["--set", "Local:ver_rules:999:pattern", "VERSION"],
    ["--set", "Local:work", ""], ["--unset", "Local:ver_rules:99"],
])
def test_invalid_cli_input_leaves_files_unchanged(sandbox, capsys, args):
    """@brief Fail invalid commands without file mutation or traceback.
    @details Level 2; covers arity, JSON, type, path bounds, and empty values.
    @param sandbox {tuple} Synthetic files and paths.
    @param capsys {pytest.CaptureFixture} Captured output.
    @param args {list[str]} Invalid command vector.
    @return {None} Non-zero SystemExit and unchanged file inventory.
    @satisfies REQ-243, REQ-248
    """
    files, _ = sandbox
    expected_output = dict(files)
    with pytest.raises(SystemExit) as exc:
        core.main(args, check_updates=False)
    assert exc.value.code != 0
    assert files == expected_output
    assert "Configuration error:" in capsys.readouterr().err


@pytest.mark.parametrize("payload", [b"{", b"[]", b'{"work":1}', b"\xff"])
def test_invalid_stored_configuration_fails_closed(sandbox, capsys, payload):
    """@brief Preserve invalid JSON and encoding bytes on mutation failure.
    @details Level 2; validates fully before calling persistence.
    @param sandbox {tuple} Synthetic files and paths.
    @param capsys {pytest.CaptureFixture} Captured output.
    @param payload {bytes} Invalid stored configuration.
    @return {None} Existing bytes retained with an English error.
    @satisfies REQ-248
    """
    files, paths = sandbox
    expected_output = payload
    files[paths["Local"]] = payload
    with pytest.raises(SystemExit):
        core.main(["--set", "Local:work", "topic"], check_updates=False)
    assert files[paths["Local"]] == expected_output
    assert "Configuration error:" in capsys.readouterr().err


def test_raw_preserves_bytes_and_global_local_order(sandbox, monkeypatch, capsys):
    """@brief Verify byte-exact raw debugging, including invalid UTF-8/JSON.
    @details Level 2; in-memory binary stdout captures original CRLF and bytes.
    @param sandbox {tuple} Synthetic files and paths.
    @param monkeypatch {pytest.MonkeyPatch} Scoped stdout replacement.
    @param capsys {pytest.CaptureFixture} Stderr capture.
    @return {None} No labels, delimiters, or added newlines reach stdout.
    @satisfies REQ-249
    """
    files, paths = sandbox
    files[paths["Global"]] = b' {"edit_command":"vim"}\r\n'
    files[paths["Local"]] = b"\xffbroken"
    expected_output = files[paths["Global"]] + files[paths["Local"]]
    output = io.BytesIO()
    with monkeypatch.context() as patch:
        patch.setattr(config.sys, "stdout", mock.Mock(buffer=output))
        core.main(["--print-raw"], check_updates=False)
    assert output.getvalue() == expected_output
    assert "Global:" in capsys.readouterr().err


def test_raw_missing_scope_and_help_are_read_only(sandbox, monkeypatch, capsys):
    """@brief Handle absent raw files and expose help without writing.
    @details Level 2; raw missing scope produces stderr only; all help forms work.
    @param sandbox {tuple} Synthetic files and paths.
    @param monkeypatch {pytest.MonkeyPatch} Stdout boundary replacement.
    @param capsys {pytest.CaptureFixture} Text output capture.
    @return {None} Empty file inventory and complete command-specific help.
    @satisfies REQ-097, REQ-243, REQ-249, REQ-252
    """
    files, _ = sandbox
    expected_output = {}
    binary = io.BytesIO()
    with monkeypatch.context() as patch:
        patch.setattr(config.sys, "stdout", mock.Mock(buffer=binary))
        core.main(["--print-raw", "Global"], check_updates=False)
    assert binary.getvalue() == b""
    assert "missing" in capsys.readouterr().err
    for command in config.COMMAND_HELP:
        core.main([command, "--help"], check_updates=False)
        assert "zero-based" in capsys.readouterr().out
        core.main(["--help", command], check_updates=False)
        assert "shell-quoted" in capsys.readouterr().out
    core.main(["--params"], check_updates=False)
    core.main(["--print"], check_updates=False)
    assert files == expected_output


def test_runtime_loader_remains_scoped_and_read_only(sandbox):
    """@brief Retain runtime scope filtering, invalid-value fallback, defaults.
    @details Level 1; synthetic persisted values exercise loader behavior.
    @param sandbox {tuple} Synthetic files and paths.
    @return {None} Flat runtime values match contracts; disk bytes unchanged.
    @satisfies DES-006, REQ-097, REQ-188, REQ-190, REQ-253
    """
    files, paths = sandbox
    files[paths["Global"]] = b'{"edit_command":"vim","master":"wrong","diff_command":"","gp_command_gfx":""}'
    files[paths["Local"]] = b'{"master":"main","work":123,"default_commit_module":"  ui  ","edit_command":"wrong"}'
    expected_output = dict(files)
    core.load_cli_config(Path("/synthetic/repo"))
    assert core.CONFIG["master"] == "main"
    assert core.CONFIG["work"] == "work"
    assert core.CONFIG["edit_command"] == "vim"
    assert core.CONFIG["default_commit_module"] == "ui"
    assert core.CONFIG["diff_command"] == ""
    assert core.CONFIG["gp_command_gfx"] == ""
    assert files == expected_output


def test_atomic_write_and_failure_cleanup():
    """@brief Verify replace ordering and temporary-file cleanup on failure.
    @details Level 1; mocks filesystem boundaries including fsync and rename.
    @return {None} Serialized JSON flushes before replace; failures propagate.
    @satisfies REQ-254
    """
    path = Path("/synthetic/config.json")
    expected_output = '{\n  "work": "topic"\n}\n'
    for failure in (None, OSError("read-only filesystem")):
        stream = mock.MagicMock(name="temporary_stream")
        stream.name = "/synthetic/staged.json"
        stream.fileno.return_value = 7
        with mock.patch.object(config.tempfile, "NamedTemporaryFile") as temporary, \
                mock.patch.object(Path, "mkdir") as mkdir, \
                mock.patch.object(Path, "unlink") as unlink, \
                mock.patch.object(config.os, "fsync") as fsync, \
                mock.patch.object(config.os, "replace", side_effect=failure) as replace:
            temporary.return_value.__enter__.return_value = stream
            if failure:
                with pytest.raises(OSError):
                    config.write_scope(path, {"work": "topic"})
            else:
                config.write_scope(path, {"work": "topic"})
            stream.write.assert_called_once_with(expected_output)
            stream.flush.assert_called_once_with()
            fsync.assert_called_once_with(7)
            replace.assert_called_once_with(Path(stream.name), path)
            unlink.assert_called_once_with(missing_ok=True)
            mkdir.assert_called_once_with(parents=True, exist_ok=True)


def test_configuration_get_does_not_replace_git_get(sandbox):
    """@brief Preserve the independent repository synchronization alias.
    @details Level 2; mocks git-get execution and verifies configuration reads
    use a separate dispatch path.
    @param sandbox {tuple} Isolated core paths and configuration.
    @return {None} Bare get retains its handler; --get uses configuration only.
    @satisfies REQ-253
    """
    expected_output = core.cmd_get
    with mock.patch.object(core, "_execute_get_flow") as synchronize:
        core.main(["get"], check_updates=False)
        synchronize.assert_called_once_with()
        core.main(["--get", "Local:work"], check_updates=False)
        synchronize.assert_called_once_with()
    assert core.COMMANDS["get"] is expected_output
