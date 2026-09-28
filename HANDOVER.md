# Handover

Everything an engineer — or another AI assistant — needs to pick this up cold.
The code says *what* it does. This says *why*, and where the traps are.

---

## What this is

A local tool that turns a LinkedIn data export into a ranked action queue for a job
search or for keeping a professional network alive. Python writes an HTML page; a small
local server shows it and stores what you mark. No cloud, no accounts, no database.

Built over five weeks against a real network of ~3,000 connections and ~8,700 messages.
Every number quoted below is measured from that data, not estimated.

---

## The architecture in one paragraph

`fetch_linkedin.py` pulls from LinkedIn's Member Data Portability API into a dated
folder. `build_desk.py` copies the newest folder into a temp work area, runs seven
pipeline stages in order, and writes `site/desk.html`. `desk_server.py` serves that page
and exposes `GET/POST /state` so the page reads and writes `desk-state.json` — the file
holding everything the user records. The page itself is a single self-contained HTML
document with the data embedded as JSON.

**Stage order matters and is not obvious:**

```
dk.py      location inference        -> conn.pkl
msg.py     thread state + live join  -> merged.pkl, threads.pkl, _me.txt
score.py   role scoring              -> final.pkl
refine.py  actions + priority        -> final2.pkl
export.py  page data + keep-warm     -> data.json
expand.py  companies, targets, grow  -> expand.json
build.py   renders template          -> desk.html
```

---

## The five things that will bite you

### 1. `start` in the Snapshot API is a chunk index, not a row offset

This cost two days. The API returns an entire chunk per call — CONNECTIONS came back as
2,749 rows in one response — and `paging.total` is the number of *chunks*, not rows.
Stepping `start` by 10 sails past a 7-chunk domain, gets a 404, and looks like a clean
finish while returning 18% of the data. Step by 1. End of data is signalled as
**HTTP 404 "No data found"**, not an empty array.

### 2. LinkedIn serves the same rows across multiple chunks

Every multi-chunk domain came back exactly doubled on one occasion. `fetch_linkedin.py`
does exact-row dedupe (`json.dumps(row, sort_keys=True)` as the key) and reports how many
it dropped. Do not remove that; the duplication is intermittent.

### 3. Percent-encoding differs between files in the same export

`Connections.csv` percent-encodes non-ASCII vanity URLs — `dennis-fib%C3%A6k-hansen` —
while `messages.csv` stores them decoded. Without `unquote()` on **both** sides, every
profile URL containing æ, ø or å fails to match, and those people read as "never
contacted". This produced 132 false negatives, falling almost entirely on the Danish half
of the network, which is the half the tool exists to serve. See `nu()` in `msg.py`.

### 4. The snapshot is a batch archive; the changelog is live but anonymous

Two APIs, neither sufficient alone:

- **Snapshot** (`memberSnapshotData`) — complete, but rebuilt on LinkedIn's schedule,
  routinely 12–48 hours behind.
- **Changelog** (`memberChangeLogs?q=memberAndApplication`) — current to the minute,
  28-day window, but message events carry **no recipient**. Only an internal thread URN.

**The join:** the changelog's `activity.thread` URN tail is the snapshot's
`CONVERSATION ID`, verbatim. Measured: 54 of 55 live threads matched. So the changelog
says *which conversation* moved and the snapshot knows who that is with. This keeps
last-contact dates current while the archive lags. See the fold-in block in `msg.py`.

**What the join cannot do:** a brand-new conversation has no id in the snapshot, so a
first message to someone is invisible until the next rebuild. That is exactly the
"never contacted" pile a user works through daily, which is why the page offers a manual
"I messaged them" mark — and audits it after three days against the snapshot.

### 5. Pin `LinkedIn-Version: 202312`

Other values return HTTP 426. Scope is `r_dma_portability_self_serve`. Tokens last ~60
days. The daily call quota is per app; one full fetch is comfortable, a fetch plus
experimentation is not (HTTP 429, resets midnight UTC).

---

## Design decisions worth keeping

**Every number equals what clicking it lists.** Counts, chips and the company table all
compute from the same filtered row set (`inView()`), because an early version had
headline figures ignoring done/snoozed marks while the lists respected them — "10 need a
reply" opening onto 9 cards. If you add a count, route it through the same predicate.

**Rank by what a card unblocks, not by seniority.** A director who politely declined
ranks below a peer who asked to meet. `PRIO` in `refine.py`.

**"Never contacted" is a first-class state, not an absence.** Absences do not appear in
interfaces, so they never get acted on.

**Show the evidence behind every inference.** The location signal, the detected promise,
the last thing either party wrote. A wrong guess should be visible, not silently trusted.

**State the data's age.** The header leads with what is actually current (changelog time)
and names the snapshot lag separately, because leading with the snapshot made a fully
working desk read as broken.

**Audit the user's own claims.** A manual "messaged" mark is a claim; if the snapshot
still shows no message after three days, the page flags it back rather than believing it.

---

## What is deliberately absent

**No scraping.** No profile collection, no browser automation, no actor farms. It breaks
LinkedIn's terms and means compiling records on named people who never agreed. Where
people outside the network are needed, the page builds a LinkedIn people-search URL the
user runs themselves — which is also strictly better, because LinkedIn marks shared
connections and a scraped list cannot.

**No "who else might know someone there".** Tempting, and it was promised once before
being cut: the export holds only a connection's *current* employer, with no history, so
any such claim would be invention dressed as inference.

**No message drafting or sending.** The tool says who and why; the words are the user's.
No automation of requests — rate is what gets accounts restricted.

---

## Findings from the real data (these shaped the product)

From 1,146 outbound threads, Fisher's exact test:

| Tested | Result | Significant |
|---|---|---|
| Recruiters vs everyone else | 11.4% vs 25.7% reply | yes, p=0.002 |
| Senior decision-makers vs rest | 17.3% vs 27.3% | yes, p=0.0005 |
| PO/PM peers | 27.8% — best audience | — |
| Citing something they posted | 36% vs 24% | suggestive, p=0.065 |
| Opening in Danish | no difference | no, p>0.9 |
| Asking for coffee first message | no difference | no, p>0.9 |

Two working assumptions were wrong: recruiters were being prioritised and are the worst
audience; writing in Danish was assumed to help and does not move the number.

---

## Known weaknesses

**The "chase again" pile.** Even after splitting out the twice-ignored and the long-cold,
~700 people sit in one bucket that will mostly never convert. A queue you cannot finish
stops being a queue. Needs a rule that closes people out for good.

**The follow-up cue is loose.** "In a few weeks" produces false positives, which is why
the detected phrase is printed on every card rather than hidden.

**Marks are per-file, not synced.** `desk-state.json` lives beside the code. Two machines
means two files; `sync_marks.py` merges them field-by-field, newest-wins, notes joined.

**The ranking has never been validated.** Nothing has tested whether high-priority cards
actually produce meetings. The outcome field (`replied / meeting / referral / applied /
dead`) exists to collect that evidence; with ~50 outcomes recorded the ranking could be
re-weighted or abandoned on evidence.

---

## If you are an AI assistant picking this up

The user is Vipin Singh Dunbar, a Product Owner in Copenhagen. He specified and tested
this; it was written with Claude. He is not a Python developer, so:

- Deliver **complete files**, not diffs to apply by hand.
- He is on Windows (`py`, not `python3`) with a Mac as a second machine.
- He cannot easily run test commands; verify changes yourself before sending.
- File downloads of `.cmd` are blocked by his browser — write those via PowerShell
  here-strings instead.
- When something breaks, ask for the run output rather than guessing. Several bugs here
  were found only because the actual output contradicted a plausible theory.

**The most useful next piece of work** is validating the ranking against recorded
outcomes. Everything else is polish.
