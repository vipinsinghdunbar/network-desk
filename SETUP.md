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
- **LinkedIn Page** — this is the one that trips people up. You must associate the app
  with a LinkedIn *Page*, not your personal profile. If you do not have one, create a
  Page first (linkedin.com/company/setup/new) — it takes two minutes and can be a
  placeholder for your own projects.
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

---

## Retuning it for somewhere other than Denmark

`pipeline/dk.py` holds the location scoring: company markers, name-form markers, and
job-title language. The structure is three independent signals summed to a score, with a
threshold for "confident" and a lower one for "possible". To adapt it, replace the marker
lists with ones for your country and keep the structure.

`pipeline/refine.py` holds the action categories and their priorities, and
`pipeline/score.py` holds role scoring (which titles count as someone who can hire).
Both are plain lists you can edit.
