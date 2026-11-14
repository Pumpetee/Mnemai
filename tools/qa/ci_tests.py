"""The unit suite for CI: prints the tail of the log and turns every failing test into a check annotation.

GitHub keeps the full log behind a signed-in account; annotations are readable by anyone, so a red run says which
tests failed without opening the log. Cross-platform on purpose: the tests run on Windows, macOS and Linux.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    print(out[-40_000:])
    if proc.returncode:
        seen = 0
        for line in out.splitlines():
            m = re.match(r"^(FAIL|ERROR): (\S+) \(([\w.]+)\)", line)
            if m and seen < 10:  # GitHub shows at most ten annotations per step
                seen += 1
                print(f"::error title={m.group(1)} {m.group(3)}::{line[:400]}")
        print(f"::error title=Unit tests::the suite failed with exit code {proc.returncode}")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
