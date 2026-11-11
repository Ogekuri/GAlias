## @file release_scripts_support.py
# @brief Hermetic sandbox fixture shared by the release-script test suites.
# @details Builds a throwaway git repository holding copies of the repository
#          release scripts, `.gitignore`, and packaging manifests, plus a fake
#          `uv` executable. The scripts under test resolve their repository
#          root from their own location, so every script side effect stays
#          inside the sandbox and the real repository is never touched.
#          Isolation: real `uv`, network, user git configuration, `HOME`, and
#          `TMPDIR` are replaced; only the real `git` executable and coreutils
#          are reused on temporary paths.

import os
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

## @brief Repository root providing the scripts and manifests under test.
REPO_ROOT = Path(__file__).resolve().parents[1]

## @brief Fake `uv` executable body used by every sandbox.
# @details Appends one argv block per invocation to `$UV_CAPTURE_FILE`
#          terminated by a `--STEP--` marker, then emulates the repository
#          side effects of the real tool. `run` creates `.venv`,
#          `.pytest_cache`, `__pycache__`, and `src/*.egg-info` residue;
#          `build` writes a fake sdist and wheel plus the uv `.gitignore`
#          marker into the `--out-dir` directory and creates `build/` and
#          `src/*.egg-info` intermediates. Behavior switches:
#          `UV_FAIL_MATCH` (exit 1 when the space-padded argv contains the
#          value), `UV_BUILD_OMIT=wheel` (skip the wheel), `UV_STRAY_FILE`
#          (create an extra repository file during pytest),
#          `UV_TOUCH_TRACKED` (append to a tracked file during pytest), and
#          `UV_BLOCK_FIFO` (signal readiness through the FIFO, then block).
FAKE_UV_SCRIPT = """#!/bin/sh
{
  printf '%s\\n' "$@"
  printf '%s\\n' '--STEP--'
} >> "$UV_CAPTURE_FILE"
joined=" $* "
case "$1" in
  run)
    mkdir -p "$PWD/.venv" "$PWD/.pytest_cache" "$PWD/src/git_alias/__pycache__" "$PWD/src/galias.egg-info"
    : > "$PWD/.venv/pyvenv.cfg"
    : > "$PWD/.pytest_cache/cache.db"
    : > "$PWD/src/git_alias/__pycache__/module.cpython-311.pyc"
    : > "$PWD/src/galias.egg-info/PKG-INFO"
    case "$joined" in
      *" pytest "*)
        if [ -n "${UV_STRAY_FILE:-}" ]; then
          : > "$PWD/$UV_STRAY_FILE"
        fi
        if [ -n "${UV_TOUCH_TRACKED:-}" ]; then
          printf 'modified\\n' >> "$PWD/$UV_TOUCH_TRACKED"
        fi
        if [ -n "${UV_BLOCK_FIFO:-}" ]; then
          printf 'ready\\n' > "$UV_BLOCK_FIFO"
          exec sleep 600
        fi
        ;;
    esac
    ;;
  build)
    out="$3"
    mkdir -p "$out" "$PWD/build/lib" "$PWD/src/galias.egg-info"
    : > "$PWD/build/lib/residue.bin"
    : > "$PWD/src/galias.egg-info/PKG-INFO"
    printf '*' > "$out/.gitignore"
    printf 'sdist' > "$out/galias-1.2.3.tar.gz"
    if [ "${UV_BUILD_OMIT:-}" != "wheel" ]; then
      printf 'wheel' > "$out/galias-1.2.3-py3-none-any.whl"
    fi
    ;;
esac
if [ -n "${UV_FAIL_MATCH:-}" ]; then
  case "$joined" in
    *"$UV_FAIL_MATCH"*) exit 1 ;;
  esac
fi
exit 0
"""


## @brief Handle of one hermetic release-script sandbox.
# @details Immutable record of the sandbox paths and the isolated process
#          environment used to run scripts and git queries.
# @param repo {Path} Sandbox git work-tree root (path contains a space).
# @param fake_bin {Path} Directory holding the fake `uv` executable.
# @param capture_path {Path} File receiving fake `uv` argv blocks.
# @param tmp_dir {Path} `TMPDIR` assigned to scripts under test.
# @param env {dict[str, str]} Isolated environment for subprocesses.
@dataclass(frozen=True)
class ReleaseSandbox:
    repo: Path
    fake_bin: Path
    capture_path: Path
    tmp_dir: Path
    env: dict

    ## @brief Resolve the sandbox copy of a repository script.
    # @param name {str} Script filename under `scripts/`.
    # @return {Path} Absolute sandbox script path.
    def script(self, name: str) -> Path:
        return self.repo / "scripts" / name

    ## @brief Run one sandbox script through Bash.
    # @details Executes `bash <script> <args...>` with captured text output
    #          and no exception on non-zero exit.
    # @param name {str} Script filename under `scripts/`.
    # @param args {tuple[str, ...]} Script arguments.
    # @param cwd {Path | None} Working directory; sandbox root when None.
    # @param env {dict[str, str] | None} Environment; sandbox env when None.
    # @return {subprocess.CompletedProcess[str]} Completed process record.
    def run(self, name: str, *args: str, cwd=None, env=None):
        return subprocess.run(
            ["bash", str(self.script(name)), *args],
            cwd=str(cwd if cwd is not None else self.repo),
            env=env if env is not None else self.env,
            capture_output=True,
            text=True,
            check=False,
        )

    ## @brief Run one git command inside the sandbox repository.
    # @param args {tuple[str, ...]} Git arguments.
    # @return {str} Captured stdout text.
    # @throws {subprocess.CalledProcessError} Git exited non-zero.
    def git(self, *args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            env=self.env,
            capture_output=True,
            text=True,
            check=True,
        )
        return completed.stdout

    ## @brief List every non-tracked sandbox file, ignored files included.
    # @return {list[str]} Sorted repository-relative paths.
    def untracked_files(self) -> list:
        return sorted(self.git("ls-files", "--others").splitlines())

    ## @brief Split captured fake `uv` argv blocks into invocations.
    # @return {list[list[str]]} One argv list per `uv` invocation; empty
    #         when `uv` was never invoked.
    def uv_invocations(self) -> list:
        if not self.capture_path.exists():
            return []
        invocations = []
        current = []
        for line in self.capture_path.read_text(encoding="utf-8").splitlines():
            if line == "--STEP--":
                invocations.append(current)
                current = []
            else:
                current.append(line)
        return invocations

    ## @brief List leftover script temporary directories.
    # @return {list[str]} Names of entries remaining in the sandbox `TMPDIR`.
    def temp_entries(self) -> list:
        return sorted(entry.name for entry in self.tmp_dir.iterdir())


## @brief Write an executable helper file.
# @param path {Path} Destination path.
# @param content {str} File body encoded as UTF-8.
# @return {None} File exists with the owner-executable bit set.
def write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


## @brief Create a committed hermetic sandbox repository.
# @details Copies the real `.gitignore`, `pyproject.toml`, `uv.lock`, and
#          every `scripts/*.sh` file, adds minimal package, test, and
#          document files, installs the fake `uv`, and commits everything in
#          a fresh git repository isolated from user and system git config.
# @param temp_root {Path} Empty temporary directory owning the sandbox.
# @return {ReleaseSandbox} Sandbox handle with a clean committed work tree.
# @throws {subprocess.CalledProcessError} Git initialization failed.
def create_sandbox(temp_root: Path) -> ReleaseSandbox:
    repo = temp_root / "repo with space"
    fake_bin = temp_root / "bin"
    tmp_dir = temp_root / "tmp"
    home_dir = temp_root / "home"
    for directory in (repo / "scripts", repo / "src" / "git_alias", repo / "tests", fake_bin, tmp_dir, home_dir):
        directory.mkdir(parents=True)
    for name in (".gitignore", "pyproject.toml", "uv.lock"):
        shutil.copy2(REPO_ROOT / name, repo / name)
    for script in sorted((REPO_ROOT / "scripts").glob("*.sh")):
        shutil.copy2(script, repo / "scripts" / script.name)
    (repo / "README.md").write_text("sandbox\n", encoding="utf-8")
    (repo / "LICENSE").write_text("sandbox license\n", encoding="utf-8")
    (repo / "src" / "git_alias" / "__init__.py").write_text('__version__ = "1.2.3"\n', encoding="utf-8")
    (repo / "tests" / "test_sample.py").write_text("def test_sample():\n    assert True\n", encoding="utf-8")
    write_executable(fake_bin / "uv", FAKE_UV_SCRIPT)

    env = os.environ.copy()
    for name in ("BASH_ENV", "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "UV_FAIL_MATCH", "UV_BUILD_OMIT"):
        env.pop(name, None)
    env["PATH"] = f"{fake_bin.as_posix()}:{env.get('PATH', '')}"
    env["HOME"] = str(home_dir)
    env["TMPDIR"] = str(tmp_dir)
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_AUTHOR_NAME"] = "Sandbox"
    env["GIT_AUTHOR_EMAIL"] = "sandbox@example.invalid"
    env["GIT_COMMITTER_NAME"] = "Sandbox"
    env["GIT_COMMITTER_EMAIL"] = "sandbox@example.invalid"
    env["UV_CAPTURE_FILE"] = str(temp_root / "uv-args.txt")

    sandbox = ReleaseSandbox(
        repo=repo,
        fake_bin=fake_bin,
        capture_path=temp_root / "uv-args.txt",
        tmp_dir=tmp_dir,
        env=env,
    )
    sandbox.git("init", "-q")
    sandbox.git("add", "--all")
    sandbox.git("commit", "-q", "-m", "sandbox baseline")
    return sandbox
