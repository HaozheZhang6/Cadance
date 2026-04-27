"""Persistent render worker — read STEP-render tasks from stdin, output to stdout.

Protocol (one task per line, both directions):
  stdin:  "<step_path>|<png_dir>|<stem>"
  stdout: "OK|<stem>|<composite_path>"   on success
  stdout: "FAIL|<stem>|<error_brief>"    on failure
  stdin:  "EXIT"  → clean exit

Used by run_simple_ops_100k.py phase2 with a watchdog so stuck workers
(OCCT/VTK U-state) get SIGKILL'd from outside and respawned.
"""

import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "data_generation"))


def main():
    # Pre-import once so per-task latency is just the actual render.
    from render_normalized_views import render_step_normalized

    sys.stdout.write("READY\n")
    sys.stdout.flush()

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        if line == "EXIT":
            break
        try:
            step_path, png_dir, stem = line.split("|", 2)
        except ValueError:
            sys.stdout.write(f"FAIL|?|bad input: {line[:60]}\n")
            sys.stdout.flush()
            continue
        try:
            os.makedirs(png_dir, exist_ok=True)
            paths = render_step_normalized(step_path, png_dir, prefix=f"{stem}_")
            sys.stdout.write(f"OK|{stem}|{paths['composite']}\n")
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:160]}"
            sys.stdout.write(f"FAIL|{stem}|{err}\n")
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
