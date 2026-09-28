#!/usr/bin/env python3
"""
build_desk.py - turn a fetched LinkedIn export into the Network Desk page, on this PC.

Finds the newest linkedin_export_* folder next to this file, runs the whole analysis
pipeline, and writes site/desk.html. No network, no cloud, nothing leaves the machine.

  py build_desk.py                 # newest export folder
  py build_desk.py --src linkedin_export_20260826
  py build_desk.py --open          # also open it in your browser

Needs pandas and numpy:
  py -m pip install pandas
"""

import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
# outcomes.py is last and does not feed the page: it reads the marks the page
# wrote, and reports on the build. It runs after export.py has staged
# desk-state.json into the work area.
STAGES = ["dk.py", "msg.py", "score.py", "refine.py", "export.py", "expand.py",
          "outcomes.py", "build.py"]
# LinkedIn's API does not always serve these, and they are not fatal if missing.
OPTIONAL = {"Member_Follows.csv", "SavedJobAlerts.csv", "Ad_Targeting.csv",
            "Inferences_about_you.csv", "Saved_Items.csv"}
NEEDED = ["Connections.csv", "messages.csv", "Invitations.csv", "Profile.csv",
          "Positions.csv", "Company Follows.csv",
          "Jobs/Saved Jobs.csv", "Jobs/Job Applications.csv"]


def newest_export():
    folders = sorted((p for p in HERE.glob("linkedin_export_*") if p.is_dir()),
                     key=lambda p: p.name, reverse=True)
    if not folders:
        sys.exit("No linkedin_export_* folder here. Run the fetch first.")
    return folders[0]


def check_deps():
    missing = [m for m in ("pandas", "numpy") if not _has(m)]
    if missing:
        sys.exit("Missing Python package(s): " + ", ".join(missing) +
                 "\n\nInstall them once with:\n    py -m pip install " + " ".join(missing) + "\n")


def _has(mod):
    try:
        __import__(mod)
        return True
    except ImportError:
        return False


def stage_source(src, work_src):
    """Copy the export into the work area, de-duplicating as we go."""
    import pandas as pd
    (work_src / "Jobs").mkdir(parents=True, exist_ok=True)
    for rel in NEEDED:
        p = src / rel
        if not p.exists():
            sys.exit(f"Missing {rel} in {src.name}. Re-run the fetch.")
        if rel == "Connections.csv":
            head = p.read_text(encoding="utf-8", errors="replace").split("\n")[:3]
            d = pd.read_csv(p, skiprows=3).drop_duplicates()
            with open(work_src / rel, "w", encoding="utf-8", newline="") as f:
                f.write("\n".join(head) + "\n")
                d.to_csv(f, index=False)
        else:
            pd.read_csv(p).drop_duplicates().to_csv(work_src / rel, index=False)
    # The API calls this Member_Follows.csv; the official archive ships the same file
    # with a member id appended. Accept either, or the follows view is silently empty.
    dest = work_src / "Member_Follows.csv"
    mf = next((p for p in sorted(src.glob("Member_Follows*.csv")) if p.stat().st_size > 0),
              src / "Member_Follows.csv")
    if mf.exists() and mf.stat().st_size > 0:
        pd.read_csv(mf).drop_duplicates().to_csv(dest, index=False)
    else:
        dest.write_text("Date,Status,FullName\n", encoding="utf-8")
        print("  note: MEMBER_FOLLOWING was not served in this fetch; that view will be empty")


def set_today(work):
    """The action rules compare against 'now'. Use the machine's date, not a baked-in one."""
    from datetime import date
    today = date.today().isoformat()
    for f in ("msg.py", "refine.py"):
        p = work / f
        s = p.read_text(encoding="utf-8")
        s = re.sub(r"pd\.Timestamp\('\d{4}-\d{2}-\d{2}'\)", f"pd.Timestamp('{today}')", s)
        p.write_text(s, encoding="utf-8")
    return today


def refresh_pipeline():
    """Unpack pipeline.tgz whenever it is newer than what is already unpacked.

    Without this, an updated archive sits unused next to a stale pipeline/ folder
    and the fix you were just sent silently never runs.
    """
    import tarfile
    tgz = HERE / "pipeline.tgz"
    marker = HERE / "pipeline" / "build.py"
    if not tgz.exists():
        return
    if marker.exists() and marker.stat().st_mtime >= tgz.stat().st_mtime:
        return
    print("  refreshing the pipeline scripts from pipeline.tgz")
    with tarfile.open(tgz) as t:
        t.extractall(HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", help="export folder to build from (default: the newest)")
    ap.add_argument("--open", action="store_true", help="open the page when done")
    args = ap.parse_args()

    check_deps()
    src = pathlib.Path(args.src) if args.src else newest_export()
    if not src.is_absolute():
        src = HERE / src
    if not src.is_dir():
        sys.exit(f"Not a folder: {src}")

    print(f"  building from {src.name}")
    work = pathlib.Path(tempfile.mkdtemp(prefix="nd-"))
    work_src = work / "src"
    try:
        refresh_pipeline()
        for f in STAGES + ["tpl.html"]:
            p = HERE / "pipeline" / f
            if not p.exists():
                sys.exit(f"Missing pipeline file: {p}\nUnpack pipeline.tgz next to this script.")
            shutil.copy(p, work / f)
        stage_source(src, work_src)
        # The live changelog is what keeps last-contact dates current. The official
        # archive does not contain one, so fall back to the newest we have fetched --
        # otherwise building from an archive silently drops the live join.
        cl = src / "_changelog.json"
        if not cl.exists():
            found = sorted(HERE.glob("linkedin_export_*/_changelog.json"),
                           key=lambda p: p.stat().st_mtime, reverse=True)
            if found:
                cl = found[0]
                print(f"  no changelog in this export; using the one from {cl.parent.name}")
        if cl.exists():
            shutil.copy(cl, work / "_changelog.json")
        # Your done-marks, notes, outcomes and conversation dates live in the browser,
        # which is one clear-site-data away from gone and never shared with your phone.
        # "Save my marks" downloads them; this picks the file up and bakes it into the
        # build, so every browser starts from the same record.
        inbox = pathlib.Path.home() / "Downloads" / "desk-state.json"
        keep = HERE / "desk-state.json"
        if inbox.exists() and (not keep.exists() or inbox.stat().st_mtime > keep.stat().st_mtime):
            shutil.move(str(inbox), keep)
            print("  picked up newly saved marks from Downloads")
        if keep.exists():
            shutil.copy(keep, work / "desk-state.json")

        for extra in ("calendar-next.json", "config.json"):
            p = HERE / extra
            if p.exists():
                shutil.copy(p, work / extra)
        today = set_today(work)
        print(f"  treating today as {today}")

        # PYTHONUTF8 puts the interpreter in UTF-8 mode, so open() defaults to UTF-8
        # instead of the Windows code page. Without it, writing a message containing
        # an emoji dies with a cp1252 UnicodeEncodeError.
        env = dict(os.environ, ND_SRC=str(work_src), ND_WORK=str(work),
                   PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        for stage in STAGES:
            r = subprocess.run([sys.executable, stage], cwd=work, env=env,
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode != 0:
                print(f"\n  {stage} failed:\n{(r.stdout or '')[-800:]}{(r.stderr or '')[-1500:]}")
                sys.exit(1)
            # outcomes.py is the one stage that reports rather than transforms.
            # Its whole purpose is the text it prints, so swallowing that into the
            # captured buffer - which only ever surfaces on failure - would make
            # the stage pointless. Show it every time.
            if stage == "outcomes.py":
                print((r.stdout or "").rstrip())
            else:
                print(f"  {stage:<12} done")

        out_dir = HERE / "site"
        out_dir.mkdir(exist_ok=True)
        built = work / "desk.html"
        if not built.exists():
            sys.exit("The renderer produced no desk.html.")
        shutil.copy(built, out_dir / "desk.html")
        kb = (out_dir / "desk.html").stat().st_size // 1024
        print(f"\n  Desk rebuilt: {os.path.join('site', 'desk.html')}  ({kb} KB)")
        # The outcome report is written by outcomes.py; keep it next to the page
        # so it can be re-read without paying for another whole build.
        rep = work / "outcomes.json"
        if rep.exists():
            shutil.copy(rep, out_dir / "outcomes.json")

        if args.open:
            import webbrowser
            webbrowser.open((out_dir / "desk.html").as_uri())
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
