#!/usr/bin/env python3
"""
fetch_linkedin.py  (v5) — pull your own LinkedIn data via the DMA Member Data Portability API.

Replaces the "request an archive and wait up to 24 hours" flow with a command that
finishes in under a minute. Output is written in the same shape as the official
export, so the Network Desk pipeline reads it without changes.

SETUP (once, ~5 minutes)
  1. https://developer.linkedin.com/  ->  Create app
     Company page: use "Member Data Portability (Member) Default Company".
     Do NOT create a new company page — the product will not appear if you do.
  2. In the app, Products tab -> Member Data Portability API (Member) -> Request access
     -> accept the terms. Access is granted immediately, no review.
  3. https://www.linkedin.com/developers/tools/oauth -> Create token
     Pick your app, tick the scope  r_dma_portability_self_serve , sign in, consent.
  4. Put the token in your environment (never in this file, never in a chat window):
       export LINKEDIN_TOKEN='...'          # macOS / Linux
       setx LINKEDIN_TOKEN "..."            # Windows, then reopen the terminal

RUN
  python3 fetch_linkedin.py                 # everything the desk uses
  python3 fetch_linkedin.py --domains CONNECTIONS INBOX
  python3 fetch_linkedin.py --out ~/linkedin-data --zip

ELIGIBILITY
  EEA + Switzerland members only. Copenhagen qualifies.

NO DEPENDENCIES - standard library only.

v3: `start` is a chunk index, not a row offset. v1 and v2 stepped it by 10 and
kept only the first chunk of every domain -- 1,446 of 8,150 messages, silently.
v4: de-duplicates rows, because LinkedIn can serve the same records in more than
one chunk. Also: domains that 404 on a fresh app may simply not be assembled yet;
MEMBER_FOLLOWING, INFERENCE_TAKEOUT and ACTOR_SAVE_ITEM all appeared a day later.
"""

import argparse
import csv
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import date

API = "https://api.linkedin.com/rest/memberSnapshotData"
# The docs pin this product to a single version. Other values return 426 NONEXISTENT_VERSION.
LINKEDIN_VERSION = "202312"

# Domain -> filename the official export uses, so downstream parsing is unchanged.
DOMAINS = {
    "CONNECTIONS":            "Connections.csv",
    "INBOX":                  "messages.csv",
    "INVITATIONS":            "Invitations.csv",
    "PROFILE":                "Profile.csv",
    "POSITIONS":              "Positions.csv",
    "COMPANY_FOLLOWS":        "Company Follows.csv",
    "MEMBER_FOLLOWING":       "Member_Follows.csv",
    "SAVED_JOBS":             "Jobs/Saved Jobs.csv",
    "JOB_APPLICATIONS":       "Jobs/Job Applications.csv",
    "JOB_SEEKER_PREFERENCES": "Jobs/Job Seeker Preferences.csv",
    "SAVED_JOB_ALERTS":       "SavedJobAlerts.csv",
    "AD_TARGETING":           "Ad_Targeting.csv",
    "INFERENCE_TAKEOUT":      "Inferences_about_you.csv",
    "ACTOR_SAVE_ITEM":        "Saved_Items.csv",
}

MAX_CHUNKS = 500        # backstop so a paging bug cannot loop forever
PAUSE = 0.25            # be polite; the product publishes no documented rate limit
BLANK_TOLERANCE = 3     # blank chunks to ride out before giving up on a domain

# `start` is a CHUNK index, not a row offset.
#
# One request returns an entire chunk of the domain -- CONNECTIONS came back as 2,749
# rows in a single call -- and paging.total is the number of chunks, not rows. Earlier
# versions stepped start by 10, sailed past the end of a 7-chunk domain, took the 404
# as end-of-data and kept only chunk 0. That returned 1,446 of 8,150 messages while
# looking like a completely clean run. Step by 1, and stop only on 404.


class Done(Exception):
    """The API has told us, one way or another, that there is nothing more."""


def request(token, domain, start):
    qs = urllib.parse.urlencode({"q": "criteria", "domain": domain, "start": start})
    req = urllib.request.Request(
        f"{API}?{qs}",
        headers={
            "Authorization": f"Bearer {token}",
            "LinkedIn-Version": LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        # End-of-data is signalled as an error, not an empty page. Documented quirk.
        if "No data found" in body:
            raise Done
        if e.code == 401:
            sys.exit("\n401 Unauthorized — the token is expired or wrong.\n"
                     "Generate a new one at https://www.linkedin.com/developers/tools/oauth\n")
        if e.code == 403:
            sys.exit("\n403 Forbidden — the app is missing the Member Data Portability (Member)\n"
                     "product, or the token lacks r_dma_portability_self_serve.\n")
        if e.code == 426:
            sys.exit(f"\n426 — LinkedIn-Version {LINKEDIN_VERSION} rejected. Check the current\n"
                     "pinned version in the docs and update LINKEDIN_VERSION at the top.\n")
        if e.code == 429:
            print("    throttled, waiting 30s…", flush=True)
            time.sleep(30)
            return request(token, domain, start)
        raise SystemExit(f"\nHTTP {e.code} on {domain} at start={start}:\n{body[:600]}\n")


def fetch(token, domain):
    """Walk a domain chunk by chunk until the API 404s."""
    rows, start, blanks, total = [], 0, 0, None
    while start < MAX_CHUNKS:
        try:
            payload = request(token, domain, start)
        except Done:
            break
        if total is None:
            total = (payload.get("paging") or {}).get("total")
        elements = payload.get("elements") or []
        batch = [item for el in elements for item in (el.get("snapshotData") or [])]
        if batch:
            rows.extend(batch)
            blanks = 0
            print(f"    chunk {start}: {len(batch)} rows"
                  + (f"  (of {total} chunks)" if total and start == 0 else ""), flush=True)
        else:
            blanks += 1
            if blanks >= BLANK_TOLERANCE:
                break
        start += 1
        time.sleep(PAUSE if batch else 0.1)
    if total and start < total:
        print(f"    WARNING: stopped at chunk {start} but the API reported {total}.", flush=True)

    # LinkedIn can serve the same records across more than one chunk -- on 26 Aug 2026
    # every multi-chunk domain came back exactly doubled. Identical rows are an artifact
    # of that, never real data: two genuine messages differ by at least a timestamp.
    seen, unique = set(), []
    for r in rows:
        k = json.dumps(r, sort_keys=True, default=str)
        if k not in seen:
            seen.add(k)
            unique.append(r)
    dropped = len(rows) - len(unique)
    if dropped:
        print(f"    dropped {dropped} duplicate row(s) served across chunks", flush=True)
    return unique



CHANGELOG = "https://api.linkedin.com/rest/memberChangeLogs"


def fetch_changelog(token, days=28):
    """Pull the live event stream that sits in front of the batch snapshot.

    The snapshot is regenerated by LinkedIn on its own schedule and can be days
    behind. The changelog is live, but each event carries only internal URNs --
    no vanity name, no profile URL, and for a message you sent, no recipient at
    all. So it can say how much activity the snapshot is missing, and can be
    matched to EXISTING conversations by thread id, but it cannot identify a
    person you have just written to for the first time.
    """
    import datetime as _dt
    start = int((_dt.datetime.now(_dt.timezone.utc).timestamp() - days * 86400) * 1000)
    events, pages = [], 0
    while pages < 400:
        qs = urllib.parse.urlencode({"q": "memberAndApplication", "startTime": start, "count": 50})
        req = urllib.request.Request(
            f"{CHANGELOG}?{qs}",
            headers={"Authorization": f"Bearer {token}",
                     "LinkedIn-Version": LINKEDIN_VERSION,
                     "X-Restli-Protocol-Version": "2.0.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                payload = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:200]
            print(f"    changelog unavailable (HTTP {e.code}) {body}", flush=True)
            return events
        els = payload.get("elements") or []
        if not els:
            break
        events.extend(els)
        nxt = max(int(e.get("processedAt") or e.get("capturedAt") or 0) for e in els)
        if nxt <= start:
            break
        start = nxt + 1
        pages += 1
        time.sleep(PAUSE)
    return events


def summarise_changelog(events):
    """Reduce events to what is safely usable: counts, timings, thread ids.

    Message BODIES are deliberately not kept. The desk shows message text from
    the snapshot, where sender and recipient are known; carrying unattributable
    text around would only create cards nobody can act on.
    """
    import collections
    out = {"total": len(events), "by_type": {}, "newest": None,
           "messages_sent": 0, "messages_received": 0, "threads": {}, "invitations": 0}
    kinds = collections.Counter()
    newest = 0
    owner = None
    for e in events:
        kinds[f"{e.get('resourceName')}/{e.get('method')}"] += 1
        t = int(e.get("capturedAt") or e.get("processedAt") or 0)
        newest = max(newest, t)
        owner = owner or e.get("owner")
        name = str(e.get("resourceName"))
        if name == "invitations":
            out["invitations"] += 1
        if name != "messages":
            continue
        act = e.get("activity") or {}
        thread = str(act.get("thread") or "")
        tid = thread.rsplit(":", 1)[-1] if thread else ""
        author = act.get("author")
        mine = bool(owner and author == owner)
        out["messages_sent" if mine else "messages_received"] += 1
        if tid:
            th = out["threads"].setdefault(tid, {"sent": 0, "recv": 0, "last": 0,
                                                 "last_mine": None})
            th["sent" if mine else "recv"] += 1
            when = int(act.get("createdAt") or t or 0)
            if when >= th["last"]:
                # who spoke last is what decides "waiting on you" on the desk
                th["last"], th["last_mine"] = when, mine
    out["by_type"] = dict(kinds)
    out["newest"] = newest or None
    return out

# The official archive puts three notice lines above the header of Connections.csv.
# Tools built against the export skip them, so reproduce the shape rather than
# silently handing back a file that is one header row out of alignment.
CONNECTIONS_PREAMBLE = (
    "Notes:\n"
    '"Fetched via the LinkedIn Member Data Portability API rather than the archive '
    "export. Email addresses appear only for connections who allow it. See "
    'https://www.linkedin.com/help/linkedin/answer/261"\n'
    "\n"
)


def write_csv(path, rows, preamble=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text(preamble, encoding="utf-8")
        return
    # Union of keys, first-seen order — snapshot rows are not guaranteed uniform.
    cols, seen = [], set()
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k)
                cols.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        if preamble:
            f.write(preamble)
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in cols})


def main():
    ap = argparse.ArgumentParser(description="Fetch your LinkedIn data via the DMA portability API.")
    ap.add_argument("--out", default=f"linkedin_export_{date.today():%Y%m%d}",
                    help="output directory (default: linkedin_export_<today>)")
    ap.add_argument("--domains", nargs="*", default=list(DOMAINS),
                    help="subset of domains to fetch (default: all the desk uses)")
    ap.add_argument("--zip", action="store_true", help="also produce a .zip of the output")
    ap.add_argument("--token-file", help="read the token from this file instead of $LINKEDIN_TOKEN")
    args = ap.parse_args()

    token = os.environ.get("LINKEDIN_TOKEN", "").strip()
    if args.token_file:
        token = pathlib.Path(args.token_file).expanduser().read_text(encoding="utf-8").strip()
    if not token:
        sys.exit("No token. Set LINKEDIN_TOKEN in your environment, or pass --token-file.\n"
                 "See the SETUP notes at the top of this file.")

    out = pathlib.Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    raw, summary = {}, []

    for domain in args.domains:
        if domain not in DOMAINS:
            print(f"  ? {domain} — not in the known list, fetching anyway")
        print(f"  {domain}…", flush=True)
        rows = fetch(token, domain)
        raw[domain] = rows
        write_csv(out / DOMAINS.get(domain, f"{domain}.csv"), rows,
                  CONNECTIONS_PREAMBLE if domain == "CONNECTIONS" else "")
        summary.append((domain, len(rows)))
        print(f"  {domain}: {len(rows)} rows", flush=True)

    print("  CHANGELOG (live events, last 28 days)...", flush=True)
    events = fetch_changelog(token)
    # NB: `summary` is already the list of (domain, rowcount) pairs used for the
    # report below. Name this one distinctly or the report line unpacks a dict.
    cl_summary = summarise_changelog(events)
    (out / "_changelog.json").write_text(json.dumps(cl_summary, indent=1), encoding="utf-8")
    if cl_summary["total"]:
        import datetime as _dt
        newest = cl_summary.get("newest")
        when = (_dt.datetime.fromtimestamp(newest/1000, _dt.timezone.utc)
                .strftime("%Y-%m-%d %H:%M UTC")) if newest else "?"
        print(f"  CHANGELOG: {cl_summary['total']} events, newest {when} "
              f"({cl_summary['messages_sent']} sent, {cl_summary['messages_received']} received, "
              f"{cl_summary['invitations']} invitation events)", flush=True)

    (out / "_raw_snapshot.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "_fetch_report.txt").write_text(
        f"fetched {date.today():%Y-%m-%d} via memberSnapshotData v{LINKEDIN_VERSION}\n" +
        "\n".join(f"{d:<24} {n:>7}" for d, n in summary) + "\n", encoding="utf-8")

    if args.zip:
        z = out.with_suffix(".zip")
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in out.rglob("*"):
                if p.is_file():
                    zf.write(p, p.relative_to(out))
        print(f"\nzipped -> {z}")

    total = sum(n for _, n in summary)
    print(f"\n{total} rows across {len(summary)} domains -> {out}")
    if total == 0:
        print("Nothing came back. Most likely the app is missing the product, or you are\n"
              "outside the EEA. Check the Products tab on your app first.")


if __name__ == "__main__":
    main()
