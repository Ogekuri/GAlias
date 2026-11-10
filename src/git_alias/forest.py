#!/usr/bin/env python3
## @file forest.py
# @brief Text-based tree visualization engine for git commit history.
# @details Implements a vine-based graph algorithm that renders commit history
# as a Unicode tree with configurable styles, symbols, colors, and margins.
# Ported from a Perl reference implementation preserving 1:1 algorithmic logic.
# @satisfies REQ-098, REQ-099, REQ-100, REQ-101, REQ-102, REQ-103, REQ-104,
# REQ-105, REQ-106, REQ-107, REQ-108, REQ-109, REQ-110, REQ-111

import os
import re
import signal
import shutil
import subprocess
import sys
from time import localtime, strftime
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Default configuration constants
# ---------------------------------------------------------------------------

## @brief Default pretty format for git log output.
_PRETTY_FMT = "format:%H\t%at\t%an\t%C(reset)%C(auto)%d%C(reset)\t%s"

## @brief Default reverse order flag.
_REVERSE_ORDER = False

## @brief Default show-all-branches flag.
_SHOW_ALL = False

## @brief Default show-rebase-markers flag.
_SHOW_REBASE = True

## @brief Default show-status flag.
_SHOW_STATUS = True

## @brief Default visual style.
_STYLE = 1

## @brief Default subvine depth.
_SUBVINE_DEPTH = 2

## @brief ANSI color map for named semantic colors plus base/bold palette.
# @satisfies REQ-103
_COLOR: Dict[str, str] = {
    "default": "\033[0m",
    "tree": "\033[0;36m",
    "hash": "\033[0;35m",
    "date": "\033[0;34m",
    "author": "\033[0;33m",
    "tag": "\033[1;35m",
    "black": "\033[0;30m",
    "red": "\033[0;31m",
    "green": "\033[0;32m",
    "yellow": "\033[0;33m",
    "blue": "\033[0;34m",
    "magenta": "\033[0;35m",
    "cyan": "\033[0;36m",
    "white": "\033[0;37m",
    "black_bold": "\033[1;30m",
    "red_bold": "\033[1;31m",
    "green_bold": "\033[1;32m",
    "yellow_bold": "\033[1;33m",
    "blue_bold": "\033[1;34m",
    "magenta_bold": "\033[1;35m",
    "cyan_bold": "\033[1;36m",
    "white_bold": "\033[1;37m",
}

## @brief Branch color palette for cycling assignment.
# @satisfies REQ-110
_BRANCH_COLORS_REF = [
    "blue_bold",
    "yellow_bold",
    "magenta_bold",
    "green_bold",
    "cyan_bold",
]

## @brief Current branch color assignments (parallel to vine even-index slots).
_branch_colors_now: List[str] = []

## @brief Minimum hash abbreviation width.
_HASH_MIN_WIDTH = 8

## @brief Hash display width; 0 means auto-detect.
_HASH_WIDTH = 0

## @brief Date format string for strftime.
_DATE_FORMAT = "%Y-%m-%d %H:%M"

## @brief Date column display width.
_DATE_WIDTH = 16

## @brief Left margin columns for graph segment.
# @satisfies REQ-105
_GRAPH_MARGIN_LEFT = 2

## @brief Right margin columns for graph segment.
# @satisfies REQ-105
_GRAPH_MARGIN_RIGHT = 1

## @brief Default graph symbol for a regular commit.
# @satisfies REQ-102
_GRAPH_SYMBOL_COMMIT = "\u25cf"  # ●

## @brief Default graph symbol for a merge commit.
# @satisfies REQ-102
_GRAPH_SYMBOL_MERGE = "\u25ce"  # ◎

## @brief Default graph symbol for an overpass.
# @satisfies REQ-102
_GRAPH_SYMBOL_OVERPASS = "\u2550"  # ═

## @brief Default graph symbol for a root commit.
# @satisfies REQ-102
_GRAPH_SYMBOL_ROOT = "\u25a0"  # ■

## @brief Default graph symbol for a tip (branch head).
# @satisfies REQ-102
_GRAPH_SYMBOL_TIP = "\u25cb"  # ○

## @brief Compiled matcher for ANSI SGR escape sequences.
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


# ---------------------------------------------------------------------------
# Internal helper functions
# ---------------------------------------------------------------------------


def _maxof(x: int, y: int) -> int:
    """
    @brief Return the greater of two integers.
    @details Performs a single conditional comparison and returns the larger operand.
    @param x {int} First operand.
    @param y {int} Second operand.
    @return {int} max(x, y).
    """
    return x if x > y else y


def _round_down2(i: int) -> int:
    """
    @brief Round down to the nearest even number.
    @details Preserves negative values; for non-negative values clears the least-significant bit.
    @param i {int} Input integer.
    @return {int} Nearest even number <= i; returns i unchanged if negative.
    """
    if i < 0:
        return i
    return i & ~1


def _str_expand(s: str, length: int) -> str:
    """
    @brief Expand string to at least the given length with spaces.
    @details Appends trailing spaces only when the current length is smaller than the target.
    @param s {str} Input string.
    @param length {int} Minimum required length.
    @return {str} String padded with trailing spaces if shorter than length.
    """
    if len(s) < length:
        s += " " * (length - len(s))
    return s


def _remove_trailing_blanks(vine: list) -> None:
    """
    @brief Remove trailing None entries from vine array in place.
    @details Pops elements from the tail while the last slot is `None`.
    @param vine {list} Column array of expected parent commit IDs.
    @return None. Mutates vine in place.
    """
    while vine and vine[-1] is None:
        vine.pop()


# ---------------------------------------------------------------------------
# Translation table generator
# ---------------------------------------------------------------------------


## @brief Build a character translation function for graph control codes.
# @details Maps single-character control codes C/M/O/r/t to the configured graph symbols.
#          Uses a chained replace pipeline because `str.translate` does not support
#          multi-codepoint replacement targets.
# @param sym_commit {str} Replacement for 'C' (commit marker).
# @param sym_merge {str} Replacement for 'M' (merge marker).
# @param sym_overpass {str} Replacement for 'O' (overpass marker).
# @param sym_root {str} Replacement for 'r' (root marker).
# @param sym_tip {str} Replacement for 't' (tip marker).
# @return {Callable[[str], str]} Translator closure that maps control strings to rendered symbols.
def _trgen(
    sym_commit: str,
    sym_merge: str,
    sym_overpass: str,
    sym_root: str,
    sym_tip: str,
):
    ## @brief Translate graph control markers into configured symbol glyphs.
    # @details Applies deterministic single-character substitutions for commit, merge,
    #          overpass, root, and tip tokens.
    # @param s {str} Graph control-string segment to transform.
    # @return {str} Transformed control string with configured symbols.
    def translate(s: str) -> str:
        s = s.replace("C", sym_commit)
        s = s.replace("M", sym_merge)
        s = s.replace("O", sym_overpass)
        s = s.replace("r", sym_root)
        s = s.replace("t", sym_tip)
        return s

    return translate


# ---------------------------------------------------------------------------
# Git repository interaction
# ---------------------------------------------------------------------------


def _git_command(args: List[str], cwd: Optional[str] = None) -> str:
    """
    @brief Execute a git command and return stripped stdout.
    @details Invokes `subprocess.run(..., check=True)` and propagates non-zero exits as `CalledProcessError`.
    @param args {List[str]} Git sub-command and arguments.
    @param cwd {Optional[str]} Working directory override.
    @return {str} Stripped stdout text.
    @throws {subprocess.CalledProcessError} On non-zero git exit.
    """
    result = subprocess.run(
        ["git"] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
        cwd=cwd,
    )
    return result.stdout.strip()


## @brief Open a git command subprocess with piped stdout for streaming.
# @details Spawns `git <args>` with text-mode stdout/stderr pipes and optional working-directory override.
# @param args {List[str]} Git sub-command tokens forwarded without transformation.
# @param cwd {Optional[str]} Optional command working directory.
# @return {subprocess.Popen} Process handle with readable stdout pipe.
def _git_command_output_pipe(
    args: List[str], cwd: Optional[str] = None
) -> subprocess.Popen:
    return subprocess.Popen(
        ["git"] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
    )


# ---------------------------------------------------------------------------
# Working tree status detection
# ---------------------------------------------------------------------------


def _get_status(repo_path: str, git_dir: str) -> str:
    """
    @brief Determine working tree dirty flags and mid-flow state indicators.
    @details Checks for unstaged, staged, stash, and untracked changes, then
    probes git internal state files for rebase/merge/cherry-pick/revert/bisect.
    @satisfies REQ-106, REQ-107
    @param repo_path {str} Path to .git directory (or gitdir for worktrees).
    @param git_dir {str} GIT_DIR value used for git commands.
    @return {str} Status string like " *+$%|REBASE-i" or empty.
    """
    dirty = ""
    mid_flow = ""

    try:
        has_unstaged = bool(
            _git_command(["diff", "--shortstat"])
        )
    except subprocess.CalledProcessError:
        has_unstaged = False
    try:
        has_staged = bool(
            _git_command(["diff", "--shortstat", "--cached"])
        )
    except subprocess.CalledProcessError:
        has_staged = False
    try:
        has_stash = bool(_git_command(["stash", "list"]))
    except subprocess.CalledProcessError:
        has_stash = False
    try:
        has_untracked = bool(
            _git_command(["ls-files", "--others", "--exclude-standard"])
        )
    except subprocess.CalledProcessError:
        has_untracked = False

    if has_unstaged:
        dirty += "*"
    if has_staged:
        dirty += "+"
    if has_stash:
        dirty += "$"
    if has_untracked:
        dirty += "%"
    if dirty:
        dirty = " " + dirty

    rebase_merge = os.path.join(repo_path, "rebase-merge")
    rebase_apply = os.path.join(repo_path, "rebase-apply")

    if os.path.isdir(rebase_merge):
        if os.path.isfile(os.path.join(rebase_merge, "interactive")):
            mid_flow = "|REBASE-i"
        else:
            mid_flow = "|REBASE-m"
    elif os.path.isdir(rebase_apply):
        if os.path.isfile(os.path.join(rebase_apply, "rebasing")):
            mid_flow = "|REBASE"
        elif os.path.isfile(os.path.join(rebase_apply, "applying")):
            mid_flow = "|AM"
        else:
            mid_flow = "|AM/REBASE"
    elif os.path.isfile(os.path.join(repo_path, "MERGE_HEAD")):
        mid_flow = "|MERGING"
    elif os.path.isfile(os.path.join(repo_path, "CHERRY_PICK_HEAD")):
        mid_flow = "|CHERRY-PICKING"
    elif os.path.isfile(os.path.join(repo_path, "REVERT_HEAD")):
        mid_flow = "|REVERTING"
    elif os.path.isfile(os.path.join(repo_path, "BISECT_LOG")):
        mid_flow = "|BISECTING"

    return dirty + mid_flow


# ---------------------------------------------------------------------------
# Ref collection
# ---------------------------------------------------------------------------


def _get_next_pick(lines: List[str], start: int) -> Optional[str]:
    """
    @brief Parse rebase-todo file lines to find the next pick target.
    @details Skips comments/blank lines and returns the second token from the first actionable row.
    @param lines {List[str]} Lines from git-rebase-todo.
    @param start {int} Starting line index.
    @return {Optional[str]} Short SHA of next pick target, or None.
    """
    for line in lines[start:]:
        if line.strip().startswith("#") or not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2:
            return parts[1]
    return None


## @brief Build a SHA-to-ref mapping from repository references and HEAD state.
# @details Parses `git show-ref`, resolves annotated tags to target commits, and conditionally
#          augments the map with active rebase markers (`rebase/next`, `rebase/onto`, `rebase/new`).
# @satisfies REQ-108
# @param show_rebase {bool} Enables inclusion of rebase markers when true.
# @return {Dict[str, List[str]]} Map from full commit SHA to rendered ref labels.
def _get_refs(
    show_rebase: bool = True,
) -> Dict[str, List[str]]:
    refs: Dict[str, List[str]] = {}

    try:
        output = _git_command(["show-ref"])
    except subprocess.CalledProcessError:
        output = ""

    for ln in output.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        parts = ln.split(None, 1)
        if len(parts) < 2:
            continue
        sha, name = parts
        if sha not in refs:
            refs[sha] = []
        refs[sha].append(name)

        if name.startswith("refs/tags/"):
            try:
                sub_sha = _git_command(
                    ["log", "-1", "--pretty=format:%H", name]
                )
                sub_sha = sub_sha.strip()
                if sha != sub_sha:
                    if sub_sha not in refs:
                        refs[sub_sha] = []
                    refs[sub_sha].append(name)
            except subprocess.CalledProcessError:
                pass

    # Detect active rebase
    try:
        repo_path = _git_command(["rev-parse", "--git-dir"])
    except subprocess.CalledProcessError:
        repo_path = ".git"

    rebase_todo = os.path.join(repo_path, "rebase-merge", "git-rebase-todo")
    rebase = os.path.isfile(rebase_todo) and show_rebase

    if rebase:
        try:
            with open(rebase_todo, "r", encoding="utf-8") as fh:
                todo_lines = fh.readlines()
            if todo_lines:
                # Skip first line, find next pick
                curr = _get_next_pick(todo_lines, 1)
                if curr is not None:
                    try:
                        curr = _git_command(["rev-parse", curr]).strip()
                        if curr not in refs:
                            refs[curr] = []
                        refs[curr].insert(0, "rebase/next")
                    except subprocess.CalledProcessError:
                        pass
        except (IOError, OSError):
            pass

        try:
            onto = _git_command(["rev-parse", "rebase-merge/onto"]).strip()
            if onto not in refs:
                refs[onto] = []
            refs[onto].insert(0, "rebase/onto")
        except subprocess.CalledProcessError:
            pass

    try:
        head = _git_command(["rev-parse", "HEAD"]).strip()
    except subprocess.CalledProcessError:
        head = ""

    if head:
        if head not in refs:
            refs[head] = []
        if rebase:
            refs[head].insert(0, "rebase/new")
        refs[head].insert(0, "HEAD")

    return refs


# ---------------------------------------------------------------------------
# Vine algorithm: branch, commit, merge
# ---------------------------------------------------------------------------


## @brief Draw branch fan topology when a commit SHA appears in multiple vine columns.
# @details Scans vine slots for duplicate commit references, emits a branch fan line when needed,
#          and preserves branch-color continuity via `_vis_post`.
# @satisfies REQ-109
# @param vine {list} Mutable vine columns storing expected parent SHAs.
# @param rev {str} Current commit SHA.
# @param color {Dict[str,str]} ANSI color token map.
# @param hash_width {int} Width of abbreviated hash column.
# @param date_width {int} Width of formatted date column.
# @param graph_margin_left {int} Left-side graph margin.
# @param style {int} Active graph style identifier.
# @param reverse_order {bool} Indicates reverse rendering order.
# @param graph_symbol_tr {Callable[[str], str]} Graph control-code translator.
# @param branch_colors_now {List[str]} Current branch color assignments.
# @param branch_colors_ref {List[str]} Allowed branch color palette.
# @return {Optional[str]} Rendered branch line or None if no duplicate SHA columns exist.
## @brief Execute `_vine_branch` graph-processing logic for Foresta rendering.
# @details Executes `_vine_branch` as deterministic commit-graph transformation/output logic.
# @param vine Input parameter consumed by `_vine_branch`.
# @param rev Input parameter consumed by `_vine_branch`.
# @param color Input parameter consumed by `_vine_branch`.
# @param hash_width Input parameter consumed by `_vine_branch`.
# @param date_width Input parameter consumed by `_vine_branch`.
# @param graph_margin_left Input parameter consumed by `_vine_branch`.
# @param style Input parameter consumed by `_vine_branch`.
# @param reverse_order Input parameter consumed by `_vine_branch`.
# @param graph_symbol_tr Input parameter consumed by `_vine_branch`.
# @param branch_colors_now Input parameter consumed by `_vine_branch`.
# @param branch_colors_ref Input parameter consumed by `_vine_branch`.
# @return Result emitted by `_vine_branch` according to command contract.
def _vine_branch(
    vine: list,
    rev: str,
    color: Dict[str, str],
    hash_width: int,
    date_width: int,
    graph_margin_left: int,
    style: int,
    reverse_order: bool,
    graph_symbol_tr,
    branch_colors_now: List[str],
    branch_colors_ref: List[str],
) -> Optional[str]:
    matched = 0
    master = False
    ret = ""

    for idx in range(len(vine)):
        if vine[idx] is None:
            ret += " "
        elif vine[idx] != rev:
            ret += "I"
        else:
            if not master and idx % 2 == 0:
                ret += "S"
                master = True
            else:
                ret += "s"
                vine[idx] = None
            matched += 1

    if matched < 2:
        return None

    _remove_trailing_blanks(vine)
    prefix = (
        f"{'':>{hash_width}.{hash_width}s} {'':>{date_width}s}"
        f"{'':>{graph_margin_left}s}"
    )
    vis = _vis_post(
        _vis_fan(ret, "branch"),
        None,
        style,
        reverse_order,
        graph_symbol_tr,
        color,
        branch_colors_now,
        branch_colors_ref,
    )
    return prefix + vis + "\n"


def _vine_commit(vine: list, rev: str, parents: List[str]) -> str:
    """
    @brief Draw commit node on the vine graph.
    @details Places the commit at its vine position or allocates a new tip slot.
    Differentiates commit types: 'C' regular, 'r' root (no parents),
    'M' merge (multiple parents), 't' tip (new branch head).
    @satisfies REQ-109
    @param vine {list} Column array of expected parent IDs.
    @param rev {str} Current commit SHA.
    @param parents {List[str]} Parent commit SHAs.
    @return {str} Control string representing the commit line.
    """
    ret = ""

    for i in range(len(vine)):
        if vine[i] is None:
            ret += " "
        elif vine[i] == rev:
            ret += "C"
        else:
            ret += "I"

    if "C" not in ret:
        # Tip: not yet in vine, find a slot
        placed = False
        for i in range(_round_down2(len(vine) - 1), -1, -2):
            if i >= 0 and i < len(ret) and ret[i] == " ":
                ret = ret[:i] + "t" + ret[i + 1 :]
                while len(vine) <= i:
                    vine.append(None)
                vine[i] = rev
                placed = True
                break
        if not placed:
            if len(vine) % 2 != 0:
                vine.append(None)
                ret += " "
            ret += "t"
            vine.append(rev)

    _remove_trailing_blanks(vine)

    if len(parents) == 0:
        ret = ret.replace("C", "r")
    elif len(parents) > 1:
        ret = ret.replace("C", "M")

    return ret


## @brief Draw merge fan topology and update vine state across commit parents.
# @details For single-parent commits the vine is only advanced; for merge commits a fan visualization
#          is generated, using lookahead heuristics to preserve adjacent branch continuity.
# @satisfies REQ-109
# @param vine {list} Mutable vine columns storing expected parent SHAs.
# @param rev {str} Current commit SHA.
# @param next_sha {List[Optional[str]]} Lookahead SHAs used for branch-placement heuristics.
# @param parents {list} Mutable parent SHA list for merge fan rendering.
# @param color {Dict[str,str]} ANSI color token map.
# @param hash_width {int} Width of abbreviated hash column.
# @param date_width {int} Width of formatted date column.
# @param graph_margin_left {int} Left-side graph margin.
# @param style {int} Active graph style identifier.
# @param reverse_order {bool} Indicates reverse rendering order.
# @param graph_symbol_tr {Callable[[str], str]} Graph control-code translator.
# @param branch_colors_now {List[str]} Current branch color assignments.
# @param branch_colors_ref {List[str]} Allowed branch color palette.
# @return {Optional[str]} Rendered merge line or None when no explicit merge line is emitted.
## @brief Execute `_vine_merge` graph-processing logic for Foresta rendering.
# @details Executes `_vine_merge` as deterministic commit-graph transformation/output logic.
# @param vine Input parameter consumed by `_vine_merge`.
# @param rev Input parameter consumed by `_vine_merge`.
# @param next_sha Input parameter consumed by `_vine_merge`.
# @param parents Input parameter consumed by `_vine_merge`.
# @param color Input parameter consumed by `_vine_merge`.
# @param hash_width Input parameter consumed by `_vine_merge`.
# @param date_width Input parameter consumed by `_vine_merge`.
# @param graph_margin_left Input parameter consumed by `_vine_merge`.
# @param style Input parameter consumed by `_vine_merge`.
# @param reverse_order Input parameter consumed by `_vine_merge`.
# @param graph_symbol_tr Input parameter consumed by `_vine_merge`.
# @param branch_colors_now Input parameter consumed by `_vine_merge`.
# @param branch_colors_ref Input parameter consumed by `_vine_merge`.
# @return Result emitted by `_vine_merge` according to command contract.
def _vine_merge(
    vine: list,
    rev: str,
    next_sha: List[Optional[str]],
    parents: list,
    color: Dict[str, str],
    hash_width: int,
    date_width: int,
    graph_margin_left: int,
    style: int,
    reverse_order: bool,
    graph_symbol_tr,
    branch_colors_now: List[str],
    branch_colors_ref: List[str],
) -> Optional[str]:
    orig_vine = -1
    for i in range(len(vine)):
        if vine[i] == rev:
            orig_vine = i
            break

    if orig_vine == -1:
        return None  # vine_commit did not add this vine

    if len(parents) <= 1:
        vine[orig_vine] = parents[0] if parents else None
        _remove_trailing_blanks(vine)
        return None

    # Put previously seen branches in subvine columns
    ret = ""
    j = 0
    while j <= len(parents) - 1 and len(parents) > 1:
        spliced = False
        for idx in range(len(vine)):
            z = vine[idx]
            if z is None:
                continue
            if vine[idx] != parents[j]:
                continue
            if z not in next_sha:
                continue
            if idx == orig_vine:
                continue

            if idx < orig_vine:
                p = idx + 1
                if p < len(vine) and vine[p] is not None:
                    p = idx - 1
                if p < 0 or (p < len(vine) and vine[p] is not None):
                    continue
                while len(vine) <= p:
                    vine.append(None)
                vine[p] = parents[j]
                ret = _str_expand(ret, p + 1)
                ret = ret[:p] + "s" + ret[p + 1 :]
            else:
                p = idx - 1
                if p < 0 or (p < len(vine) and vine[p] is not None):
                    p = idx + 1
                if p < len(vine) and vine[p] is not None:
                    continue
                while len(vine) <= p:
                    vine.append(None)
                vine[p] = parents[j]
                ret = _str_expand(ret, p + 1)
                ret = ret[:p] + "s" + ret[p + 1 :]

            parents.pop(j)
            j -= 1
            spliced = True
            break
        if not spliced:
            pass
        j += 1

    # Find slots for remaining parents
    slot = [orig_vine]
    parent_idx = 0

    seeker = 2
    while parent_idx < len(parents) - 1 and seeker < 2 + len(vine):
        direction = -1 if seeker % 2 == 0 else 1
        offset = direction * (seeker // 2) * 2
        idx = orig_vine + offset

        if 0 <= idx < len(vine) and vine[idx] is None:
            slot.append(idx)
            vine[idx] = "0" * 40
            parent_idx += 1
        seeker += 1

    idx = orig_vine + 2
    while parent_idx < len(parents) - 1:
        while idx < len(vine) and vine[idx] is not None:
            idx += 2
        if idx >= len(vine):
            while len(vine) <= idx:
                vine.append(None)
        if vine[idx] is None:
            slot.append(idx)
            parent_idx += 1
        idx += 2

    if len(slot) != len(parents):
        return None  # should not happen

    slot.sort()
    max_len = len(vine) + 2 * len(slot)

    for i in range(max_len):
        ret = _str_expand(ret, i + 1)
        if slot and i == slot[0]:
            slot.pop(0)
            while len(vine) <= i:
                vine.append(None)
            vine[i] = parents.pop(0)
            ch = "S" if i == orig_vine else "s"
            ret = ret[:i] + ch + ret[i + 1 :]
        elif ret[i] == "s":
            pass  # keep existing fanouts
        elif i < len(vine) and vine[i] is not None:
            ret = ret[:i] + "I" + ret[i + 1 :]
        else:
            ret = ret[:i] + " " + ret[i + 1 :]

    prefix = (
        f"{'':>{hash_width}.{hash_width}s} {'':>{date_width}s}"
        f"{'':>{graph_margin_left}s}"
    )
    vis = _vis_post(
        _vis_fan(ret, "merge"),
        None,
        style,
        reverse_order,
        graph_symbol_tr,
        color,
        branch_colors_now,
        branch_colors_ref,
    )
    return prefix + vis + "\n"


# ---------------------------------------------------------------------------
# Visual transformation pipeline
# ---------------------------------------------------------------------------


def _vis_commit(s: str, f: Optional[str] = None) -> str:
    """
    @brief Post-process commit control string.
    @details Trims trailing spaces and appends the optional suffix segment when provided.
    @param s {str} Raw control string from vine_commit.
    @param f {Optional[str]} Optional suffix.
    @return {str} Trimmed control string.
    """
    s = s.rstrip()
    if f is not None:
        s += f
    return s


def _vis_fan(s: str, fan_type: str) -> str:
    """
    @brief Transform control string for branch/merge fan visualization.
    @details Converts 's' fan markers into directional edge characters,
    resolves overpass sequences, and performs left/right edge transforms.
    Normalizes interior spaces between fan markers (`S`/`s`) to preserve
    continuous connector rendering.
    @param s {str} Raw control string.
    @param fan_type {str} Either "branch" or "merge".
    @return {str} Transformed control string.
    """
    is_branch = fan_type == "branch"

    # Normalize span between first and last fan markers (S/s).
    marker_positions = [
        idx for idx, ch in enumerate(s) if ch in ("S", "s")
    ]
    if len(marker_positions) >= 2:
        first_marker = marker_positions[0]
        last_marker = marker_positions[-1]
        middle = s[first_marker:last_marker + 1]
        new_middle = ""
        for ch in middle:
            if ch == " ":
                new_middle += "D"
            elif ch == "I":
                new_middle += "O"
            else:
                new_middle += ch
        s = s[:first_marker] + new_middle + s[last_marker + 1 :]

    # Transform ODODO.. sequences into contiguous overpass
    ## @brief Expand matched overpass control segments to contiguous overpass markers.
    # @details Converts regex match groups for `O[DO]+O` into equal-length `O...O` spans.
    # @param m {re.Match[str]} Regex match object for the overpass control segment.
    # @return {str} Replacement string composed only of `O` markers.
    def _overpass_replace(m):
        return "O" * len(m.group(0))

    s = re.sub(r"O[DO]+O", _overpass_replace, s)

    # Do left/right edge transformation
    s_idx = s.find("S")
    first_s = s.find("s")
    last_s = s.rfind("s")

    if s_idx != -1 and first_s != -1 and first_s < s_idx and last_s > s_idx:
        # Both sides
        left = s[:s_idx]
        right = s[s_idx + 1 :]
        left = _vis_fan2L(left)
        right = _vis_fan2R(right)
        s = left + "K" + right
    elif s_idx != -1 and first_s != -1 and first_s < s_idx:
        # Left side only
        left = s[:s_idx]
        left = _vis_fan2L(left)
        suffix = s[s_idx + 1 :]
        s = left + "B" + suffix
    elif s_idx != -1 and last_s != -1 and last_s > s_idx:
        # Right side only
        prefix = s[:s_idx]
        right = s[s_idx + 1 :]
        right = _vis_fan2R(right)
        s = prefix + "A" + right
    # If none matched, keep as is (should not happen in normal flow)

    if is_branch:
        # swap efg <-> xyz for branch
        trans = str.maketrans("efg", "xyz")
        s = s.translate(trans)

    return s


def _vis_fan2L(left: str) -> str:
    """
    @brief Transform left side of fan visualization.
    @details Converts the first `s` marker to `e` and remaining `s` markers to
    `f`, preserving any leading spacing used for vine alignment.
    @param left {str} Left portion of control string.
    @return {str} Transformed left portion.
    """
    first_s = left.find("s")
    if first_s != -1:
        left = left[:first_s] + "e" + left[first_s + 1 :]
    left = left.replace("s", "f")
    return left


def _vis_fan2R(right: str) -> str:
    """
    @brief Transform right side of fan visualization.
    @details Converts the rightmost `s` marker to `g` and remaining `s` markers
    to `f`, preserving trailing spacing used for vine alignment.
    @param right {str} Right portion of control string.
    @return {str} Transformed right portion.
    """
    last_s = right.rfind("s")
    if last_s == -1:
        return right
    prefix = right[:last_s].replace("s", "f")
    suffix = right[last_s + 1 :].replace("s", "f")
    return prefix + "g" + suffix


# Style translation tables
# @satisfies REQ-101
_STYLE_MAPS = {
    1: str.maketrans(
        "ABDefgIKmxyz",
        "\u251c\u2524\u2500\u250c\u252c\u2510\u2502\u253c\u2500\u2514\u2534\u2518",
    ),
    2: str.maketrans(
        "ABDefgIKmxyz",
        "\u2560\u2563\u2550\u2554\u2566\u2557\u2551\u256c\u2500\u255a\u2569\u255d",
    ),
    10: str.maketrans(
        "ABDefgIKmxyz",
        "\u251c\u2524\u2500\u256d\u252c\u256e\u2502\u253c\u2500\u2570\u2534\u256f",
    ),
    15: str.maketrans(
        "ABDefgIKmxyz",
        "\u2523\u252b\u2501\u250f\u2533\u2513\u2503\u254b\u2501\u2517\u253b\u251b",
    ),
}


## @brief Convert graph control-string tokens into styled Unicode output.
# @details Applies optional space-filling after commit markers, reverse-order fan transformation,
#          style-specific Unicode translation, and final graph-symbol replacement.
# @satisfies REQ-101
# @param s {str} Graph control-string line.
# @param spc {bool} Enables post-commit-space fill when true.
# @param style {int} Style selector (`1`, `2`, `10`, `15`).
# @param reverse_order {bool} Enables reverse fan transformation when true.
# @param graph_symbol_tr {Callable[[str], str]} Control-to-symbol translator function.
# @return {str} Rendered graph line with selected style and symbols.
def _vis_xfrm(
    s: str,
    spc: bool,
    style: int,
    reverse_order: bool,
    graph_symbol_tr,
) -> str:
    if spc:
        # Fill spaces after commit/tip/root markers with '*'
        match = re.search(r"[Ctr]", s)
        if match:
            pos = match.start()
            tail = s[pos:]
            tail = tail.replace(" ", "*")
            s = s[:pos] + tail

    # Change branch colors tracking is done externally

    if reverse_order:
        # Swap efg <-> xyz
        swap = str.maketrans("efgxyz", "xyzefg")
        s = s.translate(swap)

    style_map = _STYLE_MAPS.get(style)
    if style_map:
        s = s.translate(style_map)

    return graph_symbol_tr(s)


## @brief Post-process graph control strings with style transform and branch coloring.
# @details Applies `_vis_xfrm` to graph/control suffix segments, preserves ANSI spans, and injects
#          branch-color-specific commit glyph coloring based on tracked branch state.
# @param s {str} Primary graph control string.
# @param f {Optional[str]} Optional suffix containing refs/message text.
# @param style {int} Active graph style identifier.
# @param reverse_order {bool} Indicates reverse rendering order.
# @param graph_symbol_tr {Callable[[str], str]} Graph control-code translator.
# @param color {Dict[str,str]} ANSI color token map (empty in no-color mode).
# @param branch_colors_now {List[str]} Current branch color assignments.
# @param branch_colors_ref {List[str]} Allowed branch color palette.
# @return {str} Final rendered line with style transformation and ANSI colors.
## @brief Execute `_vis_post` graph-processing logic for Foresta rendering.
# @details Executes `_vis_post` as deterministic commit-graph transformation/output logic.
# @param s Input parameter consumed by `_vis_post`.
# @param f Input parameter consumed by `_vis_post`.
# @param style Input parameter consumed by `_vis_post`.
# @param reverse_order Input parameter consumed by `_vis_post`.
# @param graph_symbol_tr Input parameter consumed by `_vis_post`.
# @param color Input parameter consumed by `_vis_post`.
# @param branch_colors_now Input parameter consumed by `_vis_post`.
# @param branch_colors_ref Input parameter consumed by `_vis_post`.
# @return Result emitted by `_vis_post` according to command contract.
def _vis_post(
    s: str,
    f: Optional[str],
    style: int,
    reverse_order: bool,
    graph_symbol_tr,
    color: Dict[str, str],
    branch_colors_now: List[str],
    branch_colors_ref: List[str],
) -> str:
    # Update branch color assignments before transforming
    _update_branch_colors(s, branch_colors_now, branch_colors_ref)

    has_suffix = f is not None
    s = _vis_xfrm(s, has_suffix, style, reverse_order, graph_symbol_tr)
    if has_suffix:
        # Transform non-ANSI parts of f
        parts = re.split(r"(\x1b\[[\d;]*m)", f)
        new_f = ""
        for i, part in enumerate(parts):
            if part.startswith("\x1b"):
                new_f += part
            else:
                new_f += _vis_xfrm(
                    part, False, style, reverse_order, graph_symbol_tr
                )
        f = new_f

        s = s.replace("*", f or "")
        if color:
            default_code = color.get("default", "")
            tree_code = color.get("tree", "")
            if default_code:
                s = s.replace(default_code, default_code + tree_code)
        if f:
            s += f

    # Color the commit symbol with branch color
    sym_commit = graph_symbol_tr("C")
    sym_merge = graph_symbol_tr("M")
    sym_root = graph_symbol_tr("r")
    sym_tip = graph_symbol_tr("t")
    symbol_chars = sym_commit + sym_merge + sym_root + sym_tip
    if symbol_chars and color:
        pattern = re.compile(
            r"^(.*?)([" + re.escape(symbol_chars) + r"])"
        )
        match = pattern.match(s)
        if match:
            prefix_len = len(match.group(1))
            color_idx = prefix_len // 2
            if color_idx < len(branch_colors_now) and branch_colors_now[color_idx]:
                branch_color_name = branch_colors_now[color_idx]
                branch_color_code = color.get(branch_color_name, "")
                tree_code = color.get("tree", "")
                symbol = match.group(2)
                s = (
                    s[: match.start(2)]
                    + branch_color_code
                    + symbol
                    + tree_code
                    + s[match.end(2) :]
                )

    tree_code = color.get("tree", "")
    default_code = color.get("default", "")
    return tree_code + s + default_code


## @brief Update branch-color assignments using current vine control-string content.
# @details Scans even vine slots for branch indicators (`e`, `f`, `g`, `t`) and assigns colors
#          from the reference palette while avoiding immediate neighbor color collisions.
# @satisfies REQ-110
# @param s {str} Vine control string for the current rendered line.
# @param branch_colors_now {List[str]} Mutable current branch-color assignments.
# @param branch_colors_ref {List[str]} Fixed branch-color palette.
# @return None. Mutates `branch_colors_now` in place.
def _update_branch_colors(
    s: str,
    branch_colors_now: List[str],
    branch_colors_ref: List[str],
) -> None:
    # Extract odd-indexed characters (even vine slots)
    s_arr_odd = [s[i] for i in range(0, len(s), 2)]

    # Extend branch_colors_now to match
    while len(branch_colors_now) < len(s_arr_odd):
        branch_colors_now.append("")

    for i, ch in enumerate(s_arr_odd):
        if ch in ("e", "f", "g", "t"):
            j = 0
            while j <= len(branch_colors_ref) - 1:
                candidate = branch_colors_ref[j]
                conflict = False
                if i > 0 and branch_colors_now[i - 1] == candidate:
                    conflict = True
                if branch_colors_now[i] == candidate:
                    conflict = True
                if (
                    i < len(s_arr_odd) - 1
                    and i + 1 < len(branch_colors_now)
                    and branch_colors_now[i + 1] == candidate
                ):
                    conflict = True
                if not conflict:
                    break
                j += 1
            if j < len(branch_colors_ref):
                branch_colors_now[i] = branch_colors_ref[j]


# ---------------------------------------------------------------------------
# Line block reader for subvine lookahead
# ---------------------------------------------------------------------------


## @brief Read one commit-log line plus bounded lookahead for subvine processing.
# @details Maintains a rolling prefetch buffer and returns the current line with up to
#          `max_count - 1` subsequent entries for merge lookahead heuristics.
# @param lines_iter {Iterator[str]} Iterator yielding raw git-log lines.
# @param buffer {list} Mutable rolling prefetch buffer.
# @param max_count {int} Maximum total items in returned block.
# @return {Tuple[Optional[str], List[Optional[str]]]} Current line and lookahead list.
def _get_line_block(
    lines_iter, buffer: list, max_count: int
) -> Tuple[Optional[str], List[Optional[str]]]:
    while len(buffer) < max_count:
        try:
            x = next(lines_iter)
            buffer.append(x)
        except StopIteration:
            break

    if not buffer:
        return None, []

    current = buffer.pop(0)
    lookahead = buffer[:max_count - 1]
    return current, lookahead


# ---------------------------------------------------------------------------
# Reverse output handler
# ---------------------------------------------------------------------------


class _ReverseOutput:
    """
    @brief Buffer that collects output and writes it in reverse line order.
    @details Used when --reverse is specified. Accumulates all printed output
    and flushes in reverse order on close().
    """

    def __init__(self, stream):
        """
        @brief Initialize reverse output buffer.
        @param stream Output stream to write reversed content to.
        """
        self._stream = stream
        self._saved = ""

    def write(self, text: str) -> None:
        """
        @brief Accumulate text for later reversed output.
        @param text {str} Text to buffer.
        """
        self._saved += text

    def flush(self) -> None:
        """
        @brief No-op flush for buffered mode.
        """
        pass

    def close(self) -> None:
        """
        @brief Write buffered content in reverse line order to the stream.
        """
        lines = self._saved.split("\n")
        lines.reverse()
        self._stream.write("\n".join(lines))
        if lines:
            self._stream.write("\n")
        self._stream.flush()


# ---------------------------------------------------------------------------
# Terminal-width output shaping
# ---------------------------------------------------------------------------


## @brief Resolve terminal column width for default non-wrapping rendering.
# @details Reads active terminal size using `shutil.get_terminal_size` and enforces
#          a minimum width of one printable column.
# @satisfies REQ-100
# @return {int} Terminal columns used for line truncation.
def _resolve_terminal_columns() -> int:
    return max(shutil.get_terminal_size(fallback=(120, 24)).columns, 1)


## @brief Truncate one rendered line to a visible terminal-width budget.
# @details Preserves ANSI escape sequences as zero-width tokens, truncates only
#          printable glyph columns, and preserves trailing newline semantics.
# @satisfies REQ-100
# @param line {str} Rendered output line with optional ANSI escape sequences.
# @param terminal_columns {int} Maximum number of visible printable columns.
# @return {str} Width-bounded line preserving ANSI tokens and newline suffix.
def _truncate_line_to_terminal_width(line: str, terminal_columns: int) -> str:
    if terminal_columns < 1:
        terminal_columns = 1
    line_no_nl = line[:-1] if line.endswith("\n") else line
    newline = "\n" if line.endswith("\n") else ""
    visible_columns = 0
    out: List[str] = []
    index = 0
    truncated = False
    while index < len(line_no_nl):
        escape_match = _ANSI_ESCAPE_RE.match(line_no_nl, index)
        if escape_match is not None:
            out.append(escape_match.group(0))
            index = escape_match.end()
            continue
        if visible_columns >= terminal_columns:
            truncated = True
            break
        out.append(line_no_nl[index])
        visible_columns += 1
        index += 1
    if index < len(line_no_nl):
        truncated = True
    rendered = "".join(out)
    if truncated and "\x1b[" in rendered and not rendered.endswith(_COLOR["default"]):
        rendered += _COLOR["default"]
    return rendered + newline


## @brief Write one rendered line with optional terminal-width truncation.
# @details Applies width truncation only when `terminal_columns` is provided;
#          otherwise writes the full input line.
# @satisfies REQ-100, REQ-104
# @param output_stream {IO[str]} Destination stream.
# @param line {str} Rendered output line.
# @param terminal_columns {Optional[int]} Width budget or `None` for wrapping.
# @return None.
def _write_rendered_line(
    output_stream,
    line: str,
    terminal_columns: Optional[int],
) -> None:
    if terminal_columns is None:
        output_stream.write(line)
        return
    output_stream.write(_truncate_line_to_terminal_width(line, terminal_columns))


# ---------------------------------------------------------------------------
# Main process loop
# ---------------------------------------------------------------------------


## @brief Stream git log commits, render vine graph lines, and emit final output.
# @details Opens a `git log` pipe, iterates commits, executes vine_branch/vine_commit/vine_merge
#          rendering stages, and writes normalized lines to the configured output stream.
# @satisfies REQ-099, REQ-100, REQ-109
# @param refs {Dict[str,List[str]]} SHA-to-reference mapping.
# @param status {str} Working-tree status token set.
# @param show_status {bool} Enables status markers in HEAD decorations.
# @param pretty_fmt {str} Git pretty-format expression.
# @param argv {List[str]} Additional passthrough arguments for `git log`.
# @param color {Dict[str,str]} ANSI color token map.
# @param hash_width {int} Width of hash output column.
# @param date_width {int} Width of date output column.
# @param date_format {str} Datetime format string for commit dates.
# @param graph_margin_left {int} Left graph margin width.
# @param graph_margin_right {int} Right graph margin width.
# @param subvine_depth {int} Maximum subvine lookahead depth.
# @param style {int} Active graph style identifier.
# @param reverse_order {bool} Enables reverse commit-output ordering.
# @param graph_symbol_tr {Callable[[str], str]} Graph symbol translator function.
# @param output_stream {IO[str]} Destination stream for rendered lines.
# @param branch_colors_now {List[str]} Mutable current branch-color state.
# @param branch_colors_ref {List[str]} Fixed branch-color palette.
# @param terminal_columns {Optional[int]} Visible-width budget; `None` disables truncation.
# @return None.
## @brief Execute `_process` graph-processing logic for Foresta rendering.
# @details Executes `_process` as deterministic commit-graph transformation/output logic.
# @param refs Input parameter consumed by `_process`.
# @param status Input parameter consumed by `_process`.
# @param show_status Input parameter consumed by `_process`.
# @param pretty_fmt Input parameter consumed by `_process`.
# @param argv Input parameter consumed by `_process`.
# @param color Input parameter consumed by `_process`.
# @param hash_width Input parameter consumed by `_process`.
# @param date_width Input parameter consumed by `_process`.
# @param date_format Input parameter consumed by `_process`.
# @param graph_margin_left Input parameter consumed by `_process`.
# @param graph_margin_right Input parameter consumed by `_process`.
# @param subvine_depth Input parameter consumed by `_process`.
# @param style Input parameter consumed by `_process`.
# @param reverse_order Input parameter consumed by `_process`.
# @param graph_symbol_tr Input parameter consumed by `_process`.
# @param output_stream Input parameter consumed by `_process`.
# @param branch_colors_now Input parameter consumed by `_process`.
# @param branch_colors_ref Input parameter consumed by `_process`.
# @param terminal_columns Input parameter consumed by `_process`.
# @return Result emitted by `_process` according to command contract.
def _process(
    refs: Dict[str, List[str]],
    status: str,
    show_status: bool,
    pretty_fmt: str,
    argv: List[str],
    color: Dict[str, str],
    hash_width: int,
    date_width: int,
    date_format: str,
    graph_margin_left: int,
    graph_margin_right: int,
    subvine_depth: int,
    style: int,
    reverse_order: bool,
    graph_symbol_tr,
    output_stream,
    branch_colors_now: List[str],
    branch_colors_ref: List[str],
    terminal_columns: Optional[int],
) -> None:
    vine: list = []
    proc = _git_command_output_pipe(
        [
            "log",
            "--date-order",
            f"--pretty=format:<%H><%h><%P>{pretty_fmt}",
        ]
        + argv
    )

    buffer: list = []

    ## @brief Yield streamed git-log lines from subprocess stdout.
    # @details Wraps `proc.stdout` iteration to keep generator creation local to `_process`.
    # @return {Iterator[str]} Iterator emitting raw log lines including trailing newlines.
    def _lines_iter():
        assert proc.stdout is not None
        for raw_line in proc.stdout:
            yield raw_line

    line_iter = _lines_iter()

    while True:
        line, next_lines = _get_line_block(line_iter, buffer, subvine_depth)
        if line is None:
            break

        line = line.rstrip("\n").rstrip("\r")
        # Parse: <SHA><short_sha><parents>rest
        match = re.match(r"^<(.*?)><(.*?)><(.*?)>(.*)", line, re.DOTALL)
        if not match:
            continue

        sha = match.group(1)
        _mini_sha = match.group(2)
        parents_str = match.group(3)
        msg = match.group(4)

        # Extract next SHAs from lookahead lines
        next_sha_list: List[Optional[str]] = []
        for nl in next_lines:
            if nl is not None:
                nl = nl.rstrip("\n").rstrip("\r")
                nm = re.match(r"^<(.*?)>", nl)
                if nm:
                    next_sha_list.append(nm.group(1))
                else:
                    next_sha_list.append(None)
            else:
                next_sha_list.append(None)

        parents = parents_str.split() if parents_str.strip() else []
        parts = msg.split("\t", 4)
        if len(parts) < 5:
            parts.extend([""] * (5 - len(parts)))
        commit_hash, time_str, author, auto_refs, subject = parts

        try:
            timestamp = int(time_str)
            date_str = strftime(date_format, localtime(timestamp))
        except (ValueError, OSError):
            date_str = time_str

        # vine_branch
        branch_line = _vine_branch(
            vine,
            sha,
            color,
            hash_width,
            date_width,
            graph_margin_left,
            style,
            reverse_order,
            graph_symbol_tr,
            branch_colors_now,
            branch_colors_ref,
        )
        if branch_line:
            _write_rendered_line(output_stream, branch_line, terminal_columns)

        # Print hash and date prefix
        hash_color = color.get("hash", "")
        date_color = color.get("date", "")
        default_color = color.get("default", "")
        author_color = color.get("author", "")
        tag_color = color.get("tag", "")

        prefix = (
            f"{hash_color}"
            f"{commit_hash:<{hash_width}.{hash_width}s} "
            f"{date_color}"
            f"{date_str:<{date_width}s}"
            f"{'':>{graph_margin_left}s}"
            f"{default_color}"
        )
        # vine_commit
        commit_str = _vine_commit(vine, sha, parents)
        vis = _vis_post(
            _vis_commit(commit_str),
            None,
            style,
            reverse_order,
            graph_symbol_tr,
            color,
            branch_colors_now,
            branch_colors_ref,
        )
        author_segment = f"{author_color}{author}{default_color}"

        # Annotate refs
        if sha in refs:
            ref_list = refs[sha]
            if show_status and "HEAD" in ref_list:
                # Inject status after HEAD in auto_refs
                auto_refs = re.sub(
                    r"([^/])HEAD",
                    lambda m: m.group(0) + status,
                    auto_refs,
                )
            if any(r.startswith("refs/tags/") for r in ref_list):
                if tag_color:
                    auto_refs = re.sub(
                        r"\x1b\[\d;\d\dm(?=tag: )",
                        tag_color,
                        auto_refs,
                    )

        rendered_commit_line = (
            f"{prefix}{vis}{' ' * graph_margin_right}"
            f"{author_segment}{auto_refs} {subject}\n"
        )
        _write_rendered_line(output_stream, rendered_commit_line, terminal_columns)

        # vine_merge
        merge_line = _vine_merge(
            vine,
            sha,
            next_sha_list,
            list(parents),
            color,
            hash_width,
            date_width,
            graph_margin_left,
            style,
            reverse_order,
            graph_symbol_tr,
            branch_colors_now,
            branch_colors_ref,
        )
        if merge_line:
            _write_rendered_line(output_stream, merge_line, terminal_columns)

    if proc.stdout is not None:
        proc.stdout.close()
    proc.wait()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run(extra_args: Optional[List[str]] = None) -> None:
    """
    @brief Execute the tree visualization command.
    @details Parses command-line options, configures the visualization engine,
    and runs the main processing loop. Unrecognized options are passed through
    to git log.
    @satisfies REQ-098, REQ-099, REQ-100, REQ-104, REQ-111
    @param extra_args {Optional[List[str]]} CLI arguments from the dispatcher.
    @return None. Output written to stdout.
    """
    # Ignore SIGPIPE
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # pyright: ignore[reportAttributeAccessIssue]

    args = list(extra_args) if extra_args else []

    # Mutable config state
    show_all = _SHOW_ALL
    show_status = _SHOW_STATUS
    reverse_order = _REVERSE_ORDER
    wrap_lines = False
    style = _STYLE
    subvine_depth = _SUBVINE_DEPTH
    hash_min_width = _HASH_MIN_WIDTH
    hash_width = _HASH_WIDTH
    graph_margin_left = _GRAPH_MARGIN_LEFT
    graph_margin_right = _GRAPH_MARGIN_RIGHT
    sym_commit = _GRAPH_SYMBOL_COMMIT
    sym_merge = _GRAPH_SYMBOL_MERGE
    sym_overpass = _GRAPH_SYMBOL_OVERPASS
    sym_root = _GRAPH_SYMBOL_ROOT
    sym_tip = _GRAPH_SYMBOL_TIP
    color = dict(_COLOR)

    # Parse known options, collect passthrough for git log
    passthrough: List[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--all":
            show_all = True
        elif arg == "--no-color":
            color = {}
        elif arg == "--no-status":
            show_status = False
        elif arg == "--reverse":
            reverse_order = True
        elif arg == "--wrap":
            wrap_lines = True
        elif arg.startswith("--pretty=") or arg.startswith("--format="):
            pass  # ignore
        elif arg.startswith("--pretty") and i + 1 < len(args) and not args[i + 1].startswith("-"):
            i += 1  # skip value
        elif arg.startswith("--format") and i + 1 < len(args) and not args[i + 1].startswith("-"):
            i += 1  # skip value
        elif arg.startswith("--abbrev="):
            try:
                hash_min_width = int(arg.split("=", 1)[1])
            except ValueError:
                pass
        elif arg.startswith("--svdepth="):
            try:
                subvine_depth = int(arg.split("=", 1)[1])
            except ValueError:
                pass
        elif arg.startswith("--style="):
            try:
                style = int(arg.split("=", 1)[1])
            except ValueError:
                pass
        elif arg.startswith("--graph-margin-left="):
            try:
                graph_margin_left = int(arg.split("=", 1)[1])
            except ValueError:
                pass
        elif arg.startswith("--graph-margin-right="):
            try:
                graph_margin_right = int(arg.split("=", 1)[1])
            except ValueError:
                pass
        elif arg.startswith("--graph-symbol-commit="):
            sym_commit = arg.split("=", 1)[1]
        elif arg.startswith("--graph-symbol-merge="):
            sym_merge = arg.split("=", 1)[1]
        elif arg.startswith("--graph-symbol-overpass="):
            sym_overpass = arg.split("=", 1)[1]
        elif arg.startswith("--graph-symbol-root="):
            sym_root = arg.split("=", 1)[1]
        elif arg.startswith("--graph-symbol-tip="):
            sym_tip = arg.split("=", 1)[1]
        else:
            passthrough.append(arg)
        i += 1

    # Build translation function
    graph_symbol_tr = _trgen(sym_commit, sym_merge, sym_overpass, sym_root, sym_tip)

    subvine_depth += 1

    # Handle --all
    if show_all:
        passthrough = ["--all", "HEAD"] + passthrough

    # Handle color flags
    if color:
        passthrough = ["--color"] + passthrough
    else:
        passthrough = ["--no-color"] + passthrough

    # Determine hash width
    if hash_width:
        hash_width = max(4, min(40, hash_width))
    else:
        hash_min_width = min(40, hash_min_width)
        try:
            short_head = _git_command(["rev-parse", "--short", "HEAD"]).strip()
            hash_width = _maxof(hash_min_width, len(short_head))
        except subprocess.CalledProcessError:
            hash_width = hash_min_width

    # Collect refs
    refs = _get_refs(show_rebase=_SHOW_REBASE)

    # Get status
    status = ""
    if show_status:
        try:
            repo_path = _git_command(["rev-parse", "--git-dir"]).strip()
        except subprocess.CalledProcessError:
            repo_path = ".git"
        status = _get_status(repo_path, repo_path)

    # Branch colors state
    branch_colors_now: List[str] = []
    branch_colors_ref = list(_BRANCH_COLORS_REF)

    # Setup output stream
    if reverse_order:
        output = _ReverseOutput(sys.stdout)
    else:
        output = sys.stdout
    terminal_columns = None if wrap_lines else _resolve_terminal_columns()

    try:
        _process(
            refs=refs,
            status=status,
            show_status=show_status,
            pretty_fmt=_PRETTY_FMT[7:],  # strip "format:" prefix
            argv=passthrough,
            color=color,
            hash_width=hash_width,
            date_width=_DATE_WIDTH,
            date_format=_DATE_FORMAT,
            graph_margin_left=graph_margin_left,
            graph_margin_right=graph_margin_right,
            subvine_depth=subvine_depth,
            style=style,
            reverse_order=reverse_order,
            graph_symbol_tr=graph_symbol_tr,
            output_stream=output,
            branch_colors_now=branch_colors_now,
            branch_colors_ref=branch_colors_ref,
            terminal_columns=terminal_columns,
        )
    except BrokenPipeError:
        pass
    finally:
        if reverse_order and isinstance(output, _ReverseOutput):
            try:
                output.close()
            except BrokenPipeError:
                pass
