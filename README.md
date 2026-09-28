# Network Desk

Turn a LinkedIn data export into a ranked list of who to contact, why, and what you
said to them last time.

LinkedIn gives you a feed. If you are running a job search, or keeping a professional
network alive, what you actually need is a pipeline: who owes whom a reply, which
conversations went warm and then died, which companies you can genuinely walk into.
None of that is in the export. It has to be inferred.

Network Desk does that inference locally. Your data never leaves your machine — there
is no server, no account, no cloud service. It is a Python script that writes an HTML
page and a tiny local web server that shows it to you.

The one exception is optional and you have to turn it on deliberately. If you want the
desk on your phone away from home, a launcher hands you a public `https` address and
relays the page through a tunnel. Your export and your marks still never leave the
machine; what crosses the wire is the rendered page, which does contain your network —
so that path is password-gated and refuses to start without one. Left alone, the desk
is on your own wi-fi and nothing goes anywhere.



---

## What it works out

A LinkedIn export is a list of names and a log of messages, with nothing joining them.
Three things you need are simply absent, and each has to be derived:

**Which contacts are in your country.** There is no country field. Location is scored
from the company, the shape of the name, and the language of the job title. The default
rules are tuned for Denmark, including scoring Swedish name markers *negatively* so the
other side of the Øresund bridge does not leak in. `pipeline/dk.py` is where you would
retune this for somewhere else.

**The state of each conversation.** Every thread is read end to end: who spoke last,
whether a reply ever came, whether it was warm before it went quiet, and whether the
other person politely closed it.

**Promises.** When someone writes "let's talk in August" or "after the summer", that is
a commitment with a date, and it disappears the moment the thread scrolls away. The tool
detects the phrase, works out the date it refers to, and surfaces the person when it
arrives.

## What it shows you

**Today** — the ten highest-priority live cards and nothing else, plus a weekly count of
messages sent, replies in, requests sent and accepted, taken from LinkedIn's own record
rather than from anything you ticked.

**Worth keeping warm** — people who genuinely talked back and then went quiet.
Recruiters are excluded; this is about relationships, not a pipeline. Each card shows
the last thing *they* wrote, because that line is usually the reason to write again.

**Action queue** — everyone, ranked by what a card unblocks rather than by seniority.
A director who politely declined ranks below a peer who asked to meet.

**Companies** — where your network actually sits, ranked by how reachable a company is
rather than by headcount: people who can move a hire, people who have replied, and the
pool you have not used yet.

**Newest connections** — the freshest end of the list, with a one-click **Message**
button that moves someone out of "never messaged" as you go.

---

## Honesty by design

This is the part I would want to read first if I were evaluating the tool.

**The data states its own age.** LinkedIn builds the portability snapshot in batches, so
it runs hours to days behind. The page says so, in the header, always.

**Live activity is joined on, carefully.** LinkedIn also exposes a changelog of the last
28 days, current to the minute — but it never says who a message went to. It turns out
the changelog's thread id is the snapshot's conversation id, verbatim (measured: 54 of 55
matched), so the desk can tell *which conversation* moved and the snapshot already knows
who that is with. Last-contact dates are therefore current even when the archive is not.
Message *text* is not carried across, and cards moved this way say so.

**Claims you make by hand get audited.** A new conversation has no id to match, so when
you message someone for the first time the desk cannot see it. You can mark it yourself
— and three days later, if LinkedIn still shows no message to that person, the desk flags
it back at you rather than quietly believing you.

**Every inference shows its evidence.** The location signal, the detected promise, the
last thing either of you wrote. A wrong guess should be visible, not silently trusted.

---

## What it deliberately does not do

**It does not scrape LinkedIn.** No profile collection, no automated browsing, no actor
farms. That breaks LinkedIn's terms and means compiling records on named people who never
agreed to it. Where you need people you are not connected to, the desk builds a LinkedIn
people-search link and you run it yourself — which is better anyway, because LinkedIn
shows you who shares a connection with you and a scraper cannot.

**It does not write your messages.** It tells you who to write to and what you last said.
The words are yours.

**It does not send anything.** No automation of requests or messages. Rate is what gets
accounts restricted, and a fast connection request is worth less than a slow one with a
note.

---

## Getting started

Full walkthrough in [SETUP.md](SETUP.md); the design decisions and the traps are in [HANDOVER.md](HANDOVER.md) — it covers installing Python, getting your own
LinkedIn API access, and the first run. The short version:

```bash
# 1. put your LinkedIn access token in a file
echo "YOUR_TOKEN" > ~/.linkedin_token

# 2. fetch your data and build the desk
python3 fetch_linkedin.py --token-file ~/.linkedin_token
python3 build_desk.py

# 3. open it
python3 desk_server.py
```

On Windows, double-click **Refresh Network Desk.cmd** and it does all three.

**Requirements:** Python 3.9+, pandas, numpy. A LinkedIn account and API access via the
Member Data Portability API (free; SETUP.md walks through it).

---

## How it is put together

```
fetch_linkedin.py   pulls your data from LinkedIn's Member Data Portability API
build_desk.py       runs the pipeline, writes site/desk.html
desk_server.py      serves the page and saves your marks to desk-state.json
pipeline/
  dk.py             location inference
  msg.py            thread reconstruction, live changelog join
  score.py          role scoring
  refine.py         action categories and priority
  export.py         the data the page reads
  expand.py         companies, targets, recommendations
  build.py          renders the template
  tpl.html          the page itself
```

Everything you record — done, snoozed, notes, outcomes, "I messaged them", conversation
dates — lives in `desk-state.json`, keyed by profile URL, written automatically. That
file is the only thing you would be sad to lose, and it is plain JSON you can read.

---

## A note on how this was built

I specified this, tested it, and corrected it; I wrote it with Claude rather than by hand.
What I did was decide what the tool needed to answer, check its output against the raw
export, and fix the inference logic where it guessed wrong.

One example of why that mattered: an early version reported 132 people as "never
contacted" who I had definitely messaged. Danish characters are percent-encoded in one
export file and stored decoded in another, so every profile URL containing æ, ø or å
failed to match — and the blind spot fell entirely on the Danish half of the network,
which is the half the tool exists to serve. The fix is two `unquote()` calls. Finding it
required knowing the data well enough to notice that a plausible number was wrong.

---

## Licence

MIT — see [LICENSE](LICENSE). Use it, change it, no warranty.

Built by [Vipin Singh Dunbar](https://www.linkedin.com/in/vipinsinghdunbar).
