"""
@brief Unit tests for the `l` command (text-based tree visualization).
@details Validates forest engine helper functions, option parsing,
COMMANDS/HELP_TEXTS registration, and integration with the CLI dispatcher.
@satisfies REQ-098, REQ-099, REQ-100, REQ-101, REQ-102, REQ-103, REQ-104,
REQ-105, REQ-106, REQ-109, REQ-110, REQ-111
"""

import os
import re
import tempfile
import unittest
from unittest.mock import patch

from git_alias import core
from git_alias import forest


class TestLCommandRegistration(unittest.TestCase):
    """
    @brief Level 0: Verify `l` is registered in COMMANDS and HELP_TEXTS.
    @satisfies REQ-098
    """

    def test_l_in_commands(self):
        """l MUST be present in COMMANDS dispatch map."""
        self.assertIn("l", core.COMMANDS)

    def test_l_in_help_texts(self):
        """l MUST be present in HELP_TEXTS."""
        self.assertIn("l", core.HELP_TEXTS)

    def test_l_help_text_mentions_options(self):
        """l help text MUST mention key options."""
        text = core.HELP_TEXTS["l"]
        for opt in ("--all", "--style", "--svdepth", "--no-color", "--wrap"):
            self.assertIn(opt, text)

    def test_l_command_is_cmd_l(self):
        """l dispatch entry MUST reference cmd_l function symbol."""
        self.assertIs(core.COMMANDS["l"], core.cmd_l)


class TestLCommandDefaultDepth(unittest.TestCase):
    """
    @brief Level 1: Verify `cmd_l` default depth argument wiring.
    @satisfies REQ-111
    """

    @patch("git_alias.forest.run")
    def test_cmd_l_injects_default_n_25_only_without_args(self, mock_run):
        """cmd_l MUST inject '-n 25' when invoked without parameters."""
        core.cmd_l([])
        mock_run.assert_called_once_with(["-n", "25"])

    @patch("git_alias.forest.run")
    def test_cmd_l_preserves_user_args_without_injecting_default_n_25(self, mock_run):
        """cmd_l MUST NOT inject '-n 25' when user parameters are present."""
        core.cmd_l(["--all", "--reverse"])
        mock_run.assert_called_once_with(["--all", "--reverse"])


class TestForestaHelpers(unittest.TestCase):
    """
    @brief Level 0: Test pure helper functions from forest module.
    """

    def test_maxof(self):
        self.assertEqual(forest._maxof(3, 5), 5)
        self.assertEqual(forest._maxof(7, 2), 7)
        self.assertEqual(forest._maxof(4, 4), 4)

    def test_round_down2_positive_even(self):
        self.assertEqual(forest._round_down2(4), 4)

    def test_round_down2_positive_odd(self):
        self.assertEqual(forest._round_down2(5), 4)

    def test_round_down2_negative(self):
        self.assertEqual(forest._round_down2(-3), -3)

    def test_round_down2_zero(self):
        self.assertEqual(forest._round_down2(0), 0)

    def test_str_expand_shorter(self):
        self.assertEqual(forest._str_expand("ab", 5), "ab   ")

    def test_str_expand_equal(self):
        self.assertEqual(forest._str_expand("abcde", 5), "abcde")

    def test_str_expand_longer(self):
        self.assertEqual(forest._str_expand("abcdef", 3), "abcdef")

    def test_remove_trailing_blanks(self):
        vine = ["a", None, "b", None, None]
        forest._remove_trailing_blanks(vine)
        self.assertEqual(vine, ["a", None, "b"])

    def test_remove_trailing_blanks_all_none(self):
        vine = [None, None]
        forest._remove_trailing_blanks(vine)
        self.assertEqual(vine, [])

    def test_remove_trailing_blanks_no_none(self):
        vine = ["a", "b"]
        forest._remove_trailing_blanks(vine)
        self.assertEqual(vine, ["a", "b"])


class TestForestaTerminalWidth(unittest.TestCase):
    """
    @brief Level 1: Verify terminal-width truncation and `--wrap` override behavior.
    @satisfies REQ-100, REQ-104
    """

    def test_truncate_line_to_terminal_width_preserves_visible_width(self):
        rendered = "\033[0;31mabcdef\033[0m\n"
        truncated = forest._truncate_line_to_terminal_width(rendered, 4)
        visible = re.sub(r"\x1b\[[0-9;]*m", "", truncated.rstrip("\n"))
        self.assertEqual(visible, "abcd")

    @patch("git_alias.forest._process")
    @patch("git_alias.forest._get_refs")
    @patch("git_alias.forest._git_command")
    @patch("git_alias.forest.shutil.get_terminal_size")
    def test_run_resolves_terminal_columns_when_wrap_disabled(
        self,
        mock_get_terminal_size,
        mock_git_command,
        mock_get_refs,
        mock_process,
    ):
        mock_get_terminal_size.return_value = os.terminal_size((50, 24))
        mock_get_refs.return_value = {}
        mock_git_command.return_value = "abcd1234\n"
        forest.run(["--no-status"])
        mock_get_terminal_size.assert_called_once()
        self.assertEqual(mock_process.call_args.kwargs["terminal_columns"], 50)

    @patch("git_alias.forest._process")
    @patch("git_alias.forest._get_refs")
    @patch("git_alias.forest._git_command")
    @patch("git_alias.forest.shutil.get_terminal_size")
    def test_run_wrap_disables_terminal_width_truncation(
        self,
        mock_get_terminal_size,
        mock_git_command,
        mock_get_refs,
        mock_process,
    ):
        mock_get_refs.return_value = {}
        mock_git_command.return_value = "abcd1234\n"
        forest.run(["--no-status", "--wrap"])
        mock_get_terminal_size.assert_not_called()
        self.assertIsNone(mock_process.call_args.kwargs["terminal_columns"])


class TestTrgen(unittest.TestCase):
    """
    @brief Level 0: Test the symbol translation function generator.
    @satisfies REQ-102
    """

    def test_default_symbols(self):
        tr = forest._trgen("\u25cf", "\u25ce", "\u2550", "\u25a0", "\u25cb")
        self.assertEqual(tr("C"), "\u25cf")
        self.assertEqual(tr("M"), "\u25ce")
        self.assertEqual(tr("O"), "\u2550")
        self.assertEqual(tr("r"), "\u25a0")
        self.assertEqual(tr("t"), "\u25cb")

    def test_custom_symbols(self):
        tr = forest._trgen("X", "Y", "Z", "W", "V")
        self.assertEqual(tr("CMOrt"), "XYZWV")

    def test_passthrough(self):
        tr = forest._trgen("X", "Y", "Z", "W", "V")
        self.assertEqual(tr("I "), "I ")


class TestStyleMaps(unittest.TestCase):
    """
    @brief Level 0: Verify all four style translation tables exist.
    @satisfies REQ-101
    """

    def test_style_1_exists(self):
        self.assertIn(1, forest._STYLE_MAPS)

    def test_style_2_exists(self):
        self.assertIn(2, forest._STYLE_MAPS)

    def test_style_10_exists(self):
        self.assertIn(10, forest._STYLE_MAPS)

    def test_style_15_exists(self):
        self.assertIn(15, forest._STYLE_MAPS)


class TestColorConstants(unittest.TestCase):
    """
    @brief Level 0: Verify required ANSI color entries exist.
    @satisfies REQ-103
    """

    def test_semantic_colors(self):
        for key in ("default", "tree", "hash", "date", "author", "tag"):
            self.assertIn(key, forest._COLOR)

    def test_branch_colors_ref(self):
        expected = ["blue_bold", "yellow_bold", "magenta_bold", "green_bold", "cyan_bold"]
        self.assertEqual(forest._BRANCH_COLORS_REF, expected)

    def test_all_branch_colors_in_color_map(self):
        for c in forest._BRANCH_COLORS_REF:
            self.assertIn(c, forest._COLOR)


class TestDefaultSymbols(unittest.TestCase):
    """
    @brief Level 0: Verify default graph symbol values.
    @satisfies REQ-102
    """

    def test_commit_symbol(self):
        self.assertEqual(forest._GRAPH_SYMBOL_COMMIT, "\u25cf")

    def test_merge_symbol(self):
        self.assertEqual(forest._GRAPH_SYMBOL_MERGE, "\u25ce")

    def test_overpass_symbol(self):
        self.assertEqual(forest._GRAPH_SYMBOL_OVERPASS, "\u2550")

    def test_root_symbol(self):
        self.assertEqual(forest._GRAPH_SYMBOL_ROOT, "\u25a0")

    def test_tip_symbol(self):
        self.assertEqual(forest._GRAPH_SYMBOL_TIP, "\u25cb")


class TestDefaultMargins(unittest.TestCase):
    """
    @brief Level 0: Verify default margin values.
    @satisfies REQ-105
    """

    def test_left_margin(self):
        self.assertEqual(forest._GRAPH_MARGIN_LEFT, 2)

    def test_right_margin(self):
        self.assertEqual(forest._GRAPH_MARGIN_RIGHT, 1)


class TestBranchColorUpdate(unittest.TestCase):
    """
    @brief Level 0: Test branch color neighbor-avoidance cycling.
    @satisfies REQ-110
    """

    def test_assign_new_color(self):
        colors_now = ["", "", ""]
        colors_ref = ["blue_bold", "yellow_bold", "magenta_bold"]
        forest._update_branch_colors("t  ", colors_now, colors_ref)
        self.assertEqual(colors_now[0], "blue_bold")

    def test_neighbor_avoidance(self):
        colors_now = ["blue_bold", "", ""]
        colors_ref = ["blue_bold", "yellow_bold", "magenta_bold"]
        forest._update_branch_colors("I t  ", colors_now, colors_ref)
        # Second slot (index 1) should not match neighbor blue_bold
        self.assertNotEqual(colors_now[1], "blue_bold")


class TestVineCommit(unittest.TestCase):
    """
    @brief Level 0: Test vine_commit control string generation.
    @satisfies REQ-109
    """

    def test_tip_placement(self):
        vine = []
        result = forest._vine_commit(vine, "abc123", ["parent1"])
        self.assertIn("t", result)
        self.assertIn("abc123", vine)

    def test_existing_in_vine(self):
        vine = ["abc123", None]
        result = forest._vine_commit(vine, "abc123", ["parent1"])
        self.assertIn("C", result)

    def test_root_commit(self):
        vine = ["abc123"]
        result = forest._vine_commit(vine, "abc123", [])
        self.assertIn("r", result)

    def test_merge_commit(self):
        vine = ["abc123"]
        result = forest._vine_commit(vine, "abc123", ["p1", "p2"])
        self.assertIn("M", result)


class TestVisCommit(unittest.TestCase):
    """
    @brief Level 0: Test vis_commit control string processing.
    """

    def test_trailing_spaces_stripped(self):
        self.assertEqual(forest._vis_commit("C  I  "), "C  I")

    def test_suffix_appended(self):
        self.assertEqual(forest._vis_commit("C", "x"), "Cx")


class TestVisFan(unittest.TestCase):
    """
    @brief Level 0: Test vis_fan transformation logic.
    """

    def test_merge_fan_with_S(self):
        result = forest._vis_fan("sDS", "merge")
        # Left fanout: 's' becomes 'e', 'S' becomes 'B' (branch to right)
        self.assertIn("e", result)

    def test_branch_fan_swaps_efg_to_xyz(self):
        result = forest._vis_fan("sDSDs", "branch")
        # After branch transformation, efg chars should become xyz
        for ch in result:
            self.assertNotIn(ch, "efg")

    def test_fan_connectors_render_continuous_edges_with_terminal_corners(self):
        """
        @brief Fan rendering MUST preserve connector continuity and terminal corners.
        @details Validates merge and branch fan transformations used by `g l --all`
        to prevent malformed output such as `├ ┬` and `├ ┴─┘`.
        @satisfies REQ-099, REQ-109
        @return None.
        """
        graph_symbol_tr = forest._trgen("\u25cf", "\u25ce", "\u2550", "\u25a0", "\u25cb")

        merge_vis = forest._vis_xfrm(
            forest._vis_fan("S s  ", "merge"),
            False,
            1,
            False,
            graph_symbol_tr,
        )
        self.assertEqual(merge_vis, "\u251c\u2500\u2510  ")

        branch_vis = forest._vis_xfrm(
            forest._vis_fan("S sDs", "branch"),
            False,
            1,
            False,
            graph_symbol_tr,
        )
        self.assertEqual(branch_vis, "\u251c\u2500\u2534\u2500\u2518")

        prefixed_merge_vis = forest._vis_xfrm(
            forest._vis_fan("I S s    ", "merge"),
            False,
            1,
            False,
            graph_symbol_tr,
        )
        self.assertEqual(prefixed_merge_vis, "\u2502 \u251c\u2500\u2510    ")


class TestGetStatus(unittest.TestCase):
    """
    @brief Level 1: Test working tree status detection with mocked git commands.
    @satisfies REQ-106, REQ-107
    """

    @patch("git_alias.forest._git_command")
    def test_clean_status(self, mock_cmd):
        mock_cmd.return_value = ""
        result = forest._get_status("/tmp/fake/.git", "/tmp/fake/.git")
        self.assertEqual(result, "")

    @patch("git_alias.forest._git_command")
    def test_dirty_unstaged(self, mock_cmd):
        def side_effect(args):
            if args == ["diff", "--shortstat"]:
                return " 1 file changed"
            return ""
        mock_cmd.side_effect = side_effect
        result = forest._get_status("/tmp/fake/.git", "/tmp/fake/.git")
        self.assertIn("*", result)

    @patch("git_alias.forest._git_command")
    def test_dirty_staged(self, mock_cmd):
        def side_effect(args):
            if args == ["diff", "--shortstat", "--cached"]:
                return " 1 file changed"
            return ""
        mock_cmd.side_effect = side_effect
        result = forest._get_status("/tmp/fake/.git", "/tmp/fake/.git")
        self.assertIn("+", result)

    @patch("git_alias.forest._git_command")
    def test_mid_flow_merging(self, mock_cmd):
        mock_cmd.return_value = ""
        with tempfile.TemporaryDirectory() as tmpdir:
            merge_head = os.path.join(tmpdir, "MERGE_HEAD")
            with open(merge_head, "w") as f:
                f.write("abc123\n")
            result = forest._get_status(tmpdir, tmpdir)
            self.assertIn("|MERGING", result)


class TestReverseOutput(unittest.TestCase):
    """
    @brief Level 0: Test reverse output buffer.
    """

    def test_reverse_order(self):
        import io
        stream = io.StringIO()
        rev = forest._ReverseOutput(stream)
        rev.write("line1\nline2\nline3\n")
        rev.close()
        output = stream.getvalue()
        lines = [line for line in output.split("\n") if line]
        self.assertEqual(lines[0], "line3")
        self.assertEqual(lines[1], "line2")
        self.assertEqual(lines[2], "line1")


if __name__ == "__main__":
    unittest.main()
