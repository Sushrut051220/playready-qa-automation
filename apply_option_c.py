"""
apply_option_c.py
=================
Permanently fixes the dashboard history folder by:
  1. Reading current DEEPEVAL_RESULTS_FOLDER at User + Machine + Process scope.
  2. Setting it to the CORRECT path at User scope (survives reboots & new shells).
  3. Optionally clearing the Machine scope value (if it was set there).
  4. Telling you exactly what to do next.

Run:
    python apply_option_c.py
"""

from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORRECT = ROOT / "Deepeval_Foundry_dashboard-main" / "eval_history"
VAR = "DEEPEVAL_RESULTS_FOLDER"


def ps(cmd: str) -> str:
    """Run a PowerShell command and return stripped stdout."""
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", cmd],
            text=True, errors="ignore", stderr=subprocess.STDOUT,
        )
        return out.strip()
    except subprocess.CalledProcessError as e:
        return f"[ERR] {e.output.strip()}"
    except Exception as e:
        return f"[ERR] {type(e).__name__}: {e}"


def main() -> int:
    print("=" * 70)
    print("Option C — permanent env var fix")
    print("=" * 70)

    if not CORRECT.exists():
        CORRECT.mkdir(parents=True, exist_ok=True)
    print(f"\nCorrect path:\n  {CORRECT}\n")

    print("[1/4] Current values across all scopes:")
    proc = os.environ.get(VAR, "<unset>")
    user = ps(f':GetEnvironmentVariable("{VAR}", "User")') or "<unset>"
    mach = ps(f':GetEnvironmentVariable("{VAR}", "Machine")') or "<unset>"
    print(f"  Process  : {proc}")
    print(f"  User     : {user}")
    print(f"  Machine  : {mach}")

    # Flag any that contain the OneDrive smell
    bad = []
    for scope, val in (("Process", proc), ("User", user), ("Machine", mach)):
        if isinstance(val, str) and "dashboard-main-local" in val:
            bad.append(scope)
    if bad:
        print(f"\n  [!] OneDrive path detected at scope(s): {', '.join(bad)}")
    else:
        print("\n  [i] No scope currently holds the OneDrive path.")
        print("      The leaking value may come from a parent shell's session,")
        print("      a VS Code workspace env, or the dashboard's own .env file.")

    print("\n[2/4] Setting User scope to the correct path...")
    set_user = ps(
        f':SetEnvironmentVariable("{VAR}", '
        f'"{CORRECT}", "User"); '
        f':GetEnvironmentVariable("{VAR}", "User")'
    )
    print(f"  User now : {set_user}")

    print("\n[3/4] Clearing Machine scope (if it was set there)...")
    if "ERR" not in mach and mach != "<unset>" and mach:
        cleared = ps(
            f':SetEnvironmentVariable("{VAR}", $null, "Machine"); '
            f':GetEnvironmentVariable("{VAR}", "Machine")'
        )
        print(f"  Machine now : {cleared or '<unset>'}")
        if "Access" in cleared or "ERR" in cleared:
            print("  [WARN] Clearing Machine scope requires admin PowerShell.")
            print("  Open an elevated PowerShell and run:")
            print(f'    :SetEnvironmentVariable("{VAR}", $null, "Machine")')
    else:
        print("  Machine was not set — nothing to clear.")

    print("\n[4/4] Also setting the CURRENT process so the next 'restart' works:")
    os.environ[VAR] = str(CORRECT)
    print(f"  Process now : {os.environ[VAR]}")

    print("\n" + "=" * 70)
    print("NEXT STEPS (this is the part that actually fixes the dashboard)")
    print("=" * 70)
    print("1. Stop the running dashboard:")
    print("     In its terminal window press Ctrl+C")
    print()
    print("2. CLOSE ALL PowerShell windows (including VS Code integrated terminals).")
    print("   This is the most important step — only fresh shells will pick up")
    print("   the new User-scope env var.")
    print()
    print("3. Open a NEW PowerShell window and confirm the var is set:")
    print(f"     :GetEnvironmentVariable('{VAR}', 'User')")
    print(f"     # should print: {CORRECT}")
    print()
    print("4. Activate venv + start the dashboard:")
    print("     cd C:\\Users\\v-snistane\\playready-qa-automation")
    print("     .venv\\Scripts\\Activate.ps1")
    print("     python fix_and_start_dashboard.py")
    print()
    print("5. Watch the boot log — it must say:")
    print(f"     History folder : {CORRECT}")
    print()
    print("6. Open http://localhost:5000 (Ctrl+Shift+R hard-refresh).")
    print("   All 7 runs will appear with full metric scores.")
    return 0


if __name__ == "__main__":
    sys.exit(main())