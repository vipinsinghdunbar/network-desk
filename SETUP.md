# Setup

From nothing to a working desk. Budget about 40 minutes the first time, most of it
waiting on LinkedIn.

---

## 1. Python

**Windows.** Install from [python.org/downloads](https://www.python.org/downloads/).
On the first screen tick **Add python.exe to PATH** before clicking Install — if you
miss it, nothing below works and the error is confusing.

Check it:

```powershell
py --version
```

**macOS.** Python 3 arrives with Apple's command line tools:

```bash
xcode-select --install
python3 --version
```

**Then, on both:**

```
py -m pip install pandas          # Windows
python3 -m pip install --user pandas   # macOS
```

---

## 2. The folder

Unzip the release somewhere you will find again. `~/network-desk` or
`C:\Users\you\network-desk` are good choices. You should have:

```
fetch_linkedin.py
build_desk.py
desk_server.py
pipeline.tgz
Refresh Network Desk.cmd        (Windows)
Refresh Network Desk.command    (macOS)
Desk on my phone.cmd / .command
```

---

## 3. LinkedIn API access

This is the fiddly part. LinkedIn's Member Data Portability API lets you download your
own data through an app you register. It is free, and it is the API's actual purpose,
but the form asks questions that are easy to answer wrongly.

**Create an app.** Go to
[linkedin.com/developers/apps](https://www.linkedin.com/developers/apps) and click
**Create app**.

- **App name** — anything. "Network Desk" is fine.
- **Company page** — this is the one that trips people up. Leave it as
  **"Member Data Portability (Member) Default Company"**. Do *not* create a page
  first, even if you have none: LinkedIn supplies that one, and the product does
  not appear in the Products tab if the app is tied to a page you made.
- **Privacy policy URL** — any URL you control. For a personal tool this can be a link
  to the repository.
- **App logo** — any image.

**Request the product.** In the app, open the **Products** tab and request
**Member Data Portability (Member)**. Not the Enterprise version — that one is for
companies processing other people's data and you will not be approved for it. Member
access is usually granted immediately.

**Get a token.** Open the **Auth** tab, then use LinkedIn's
[OAuth token generator](https://www.linkedin.com/developers/tools/oauth/token-generator)
with your app selected and the scope **`r_dma_portability_self_serve`** ticked. Sign in,
approve, and copy the access token.

**Store it.** Never paste a token into a chat, a commit, or a screenshot.

```powershell
notepad $HOME\.linkedin_token          # Windows: paste, save, close
```
```bash
nano ~/.linkedin_token                 # macOS: paste, ctrl+O, return, ctrl+X
```

Tokens expire — typically after 60 days. When a fetch starts returning `401
Unauthorized`, generate a new one the same way and replace the file. Nothing else
changes.

---

## 4. First run

**Windows:** double-click **Refresh Network Desk.cmd**.
**macOS:** `chmod +x *.command` once, then right-click **Refresh Network Desk.command**
→ **Open** → **Open** (macOS blocks downloaded scripts on first launch; after that a
normal double-click works).

It will fetch, build, and open the page. The first fetch takes a few minutes and prints
progress per domain.

Your browser opens `http://localhost:8901/desk.html`.

---

## 5. On your phone

Run **Desk on my phone**. It prints an address like `http://192.168.1.42:8902/desk.html`.
Type that into your phone's browser on the same wi-fi — include the `http://` or the
browser will search for it instead.

Add to Home Screen and it behaves like an app. Close the window on the computer and the
address stops working.

---

## What goes where

```
linkedin_export_YYYYMMDD/   one folder per fetch; only the newest is used
desk-state.json             everything you mark. Back this up.
state-history/              the last 20 versions of the above
site/desk.html              the page
config.json                 optional, see below
```

**`desk-state.json` is the only irreplaceable file.** The exports can always be
re-fetched; your notes and outcomes cannot.

---

## Troubleshooting

**`401 Unauthorized` on fetch** — the token expired. Generate a new one (step 3).

**`429 Too Many Requests`** — LinkedIn's daily call quota. It resets at midnight UTC.
One full fetch a day is comfortably within it; several fetches plus experiments is not.

**"Could not work out which profile is yours"** — the tool identifies you as the profile
appearing on both sides of your message log. If your export is unusual (very few
messages, for instance), create `config.json` next to `build_desk.py`:

```json
{ "profile_url": "https://www.linkedin.com/in/your-vanity-name" }
```

**The newest message is a day or two old** — expected, and not a bug. LinkedIn builds the
snapshot in batches. Contact dates are kept current by the changelog join; only message
*text* waits for the batch. The header tells you which you are looking at.

**Marks are not saving** — you are opening `desk.html` as a file instead of through the
server. Start it with the Refresh launcher, or run `python3 desk_server.py`, and the
bar under the tiles will read "saved on this PC" rather than offering a save button.

**`tar is not recognized` (Windows)** — your PATH is missing System32. The launcher
restores it; if you are running commands by hand, use the launcher instead.

**Want to see it working before you have any real data?** `make_demo_export.py` writes
an entirely invented network — fake names, fake employers, fake message text — so you
can run the whole pipeline and look at the result:

```
py make_demo_export.py
py build_desk.py --src demo_export
```

Note the folder is `demo_export`, not `linkedin_export_*`, and the build names it
explicitly. That is deliberate: the build auto-picks the newest `linkedin_export_*`
folder, and a demo folder matching that pattern would quietly win over your real
export and build the fake one instead. This way it cannot. Delete it when you are
done.

---

## 7. Is the ranking actually any good?

The desk tells you who to write to. It cannot tell you whether writing to them
worked, because the one thing LinkedIn does not know — what actually happened —
is recorded by hand on the card, and until now nothing ever read it back.

Every build now prints a report. Nothing to type:

```
py build_desk.py
```

It answers three questions. Which action categories actually produce meetings.
Whether the priority ordering predicts outcome at all, as a rank correlation.
And how that differs by Denmark tier. It also writes `site/outcomes.json` so the
same report can be re-read without rebuilding.

**Read it with its limits.** You record outcomes for people you decided to write
to, and the high-priority cards are the ones in front of you. The sample is
selected twice, so this can show the ranking is not working. It cannot prove the
ranking causes anything to work.

**Do not trust a thin row.** Every rate carries a 95% interval and anything under
eight resolved outcomes is marked `*thin`. A category showing 100% off three rows
is not a finding, and the mark is there to stop it being read as one. The number
to raise first is the number of recorded outcomes, not the formula.

A **negative** correlation is the finding that matters most: it means the cards
at the top of the queue are the ones that did worst, so the ordering is not merely
uninformative but inverted. If you see that, `PRIO` in `pipeline/refine.py` wants
rebuilding from the evidence rather than adjusting.

---

## 8. On your phone, from anywhere

Step 5 gets you the desk on any phone on your own wi-fi. If you want it to work away
from home — no laptop open at home, or simply a different network — use the tunnel.

**Windows:** double-click **Start-Desk-Tunnel.cmd**.
**macOS:** `chmod +x *.command` once, then open **Start Desk Tunnel.command**.

It asks you to choose a password the first time, stores it in `desk-password.txt`, and
prints an `https://something.trycloudflare.com` address. Type that into any phone
browser. The address changes every time you start it.

**What this does and does not do.** The desk, the export and `desk-state.json` stay on
your machine — nothing is uploaded, and there is no copy of your network anywhere else.
What is relayed is the page, which does contain your data, to whoever holds the address.
So it is open to anyone the URL is sent to, which is why the password is mandatory and
why the launcher refuses to start without one. The address cannot be guessed from your
name and is not indexed, but it is not private by magic: treat it like any other link
containing something you would not paste into a chat.

Two things to know. The address only works while this machine is switched on and the
tunnel is running. And the marks still save to this machine's `desk-state.json`, so if
you make a mark on your phone it is on your laptop's disk, not on a cloud copy.

If you would rather not have a relay at all, step 5 is the whole of it — the desk on
your own wi-fi, no tunnel, no password, nothing off the machine.

---

## Retuning it for somewhere other than Denmark

`pipeline/dk.py` holds the location scoring: company markers, name-form markers, and
job-title language. The structure is three independent signals summed to a score, with a
threshold for "confident" and a lower one for "possible". To adapt it, replace the marker
lists with ones for your country and keep the structure.

`pipeline/refine.py` holds the action categories and their priorities, and
`pipeline/score.py` holds role scoring (which titles count as someone who can hire).
Both are plain lists you can edit.
