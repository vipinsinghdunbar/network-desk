#!/usr/bin/env python3
"""
make_demo_export.py - write a throwaway LinkedIn export so the desk can be run safely.

Everything else in this repo refuses to be interesting without your real data: the
build needs a linkedin_export_* folder and will not invent one. This writes a
synthetic one - invented people, invented employers, invented message text - so you
can see the whole thing work before deciding what to upload anywhere.

  py make_demo_export.py                  # -> demo_export/
  py make_demo_export.py --n 400          # a bigger fake network

Then build it explicitly:
  py build_desk.py --src demo_export

The folder is called demo_export and NOT linkedin_export_demo on purpose.
build_desk.py picks the newest linkedin_export_* folder by name, and "d"
sorts after "2" - a folder called linkedin_export_demo would therefore win
over a real linkedin_export_20260928 and quietly build the fake one instead
of the real one. Nothing should be able to shadow your actual data by
accident, so this name cannot match the glob at all.

NOTHING HERE IS REAL. No real contact, employer or conversation is involved, and
the folder it writes is excluded by .gitignore. Delete it when you are done; a
demo build is a good way to confuse yourself about which desk you are looking at.
"""

import argparse
import csv
import pathlib
import random
import urllib.parse
from datetime import datetime, timedelta, timezone

HERE = pathlib.Path(__file__).resolve().parent
ME_URL = "https://www.linkedin.com/in/vipin-singh-dunbar"
ME_NAME = "Vipin Singh Dunbar"

# Deliberately mixed: the location scorer in pipeline/dk.py is tuned to separate
# Danish from Swedish, so the demo has to contain both to exercise it.
PEOPLE = [
    # first, last, company, position, tier-note
    ("Lars", "Jensen", "Novo Nordisk", "Senior Product Manager"),
    ("Anne", "Mette Kjeldsen", "Danske Bank", "Product Owner"),
    ("Søren", "Kristensen", "Ørsted", "Head of Digital"),
    ("Camilla", "Holm", "Grundfos", "Agile Coach"),
    ("Jens", "Bæksø", "Netcompany", "Solution Architect"),
    ("Freja", "Lindqvist", "Spotify", "Product Designer"),
    ("Erik", "Sjöberg", "Ericsson", "Engineering Manager"),
    ("Magnus", "Ström", "Volvo", "Team Lead"),
    ("Per", "Berglund", "Klarna", "Backend Engineer"),
    ("Katrine", "Bech", "Novo Nordisk", "Clinical Data Manager"),
    ("Henrik", "Toft", "Vestas", "Portfolio Manager"),
    ("Ida", "Nørgaard", "Lunar", "Product Owner"),
    ("Mads", "Bjerre", "Trustpilot", "Growth Lead"),
    ("Trine", "Dalgaard", "GN Store Nord", "UX Researcher"),
    ("Oliver", "Krag", "Bang & Olufsen", "Product Director"),
    ("Sofie", "Damgaard", "Coloplast", "Program Manager"),
    ("Jesper", "Ravn", "Carlsberg Group", "Digital Lead"),
    ("Nanna", "Friis", "Novo Nordisk", "Regulatory Affairs Manager"),
    ("Peter", "Klausen", "IBM", "Enterprise Architect"),
    ("Maria", "Rossi", "Spotify", "Data Scientist"),
    ("Lukas", "Weber", "Zalando", "Senior Engineer"),
    ("Emma", "Schmid", "Siemens", "Project Manager"),
    ("Jonas", "Berg", "Volvo", "Scrum Master"),
    ("Clara", "Weiss", "Zendesk", "Customer Success Manager"),
    ("Rasmus", "Dahl", "LEGO Group", "Product Owner"),
    ("Ingrid", "Madsen", "Danske Bank", "Compliance Lead"),
    ("Anders", "Skov", "Ørsted", "Procurement Manager"),
    ("Mette", "Kirk", "Tryg", "Business Developer"),
    ("Thomas", "Agger", "Carlsberg Group", "Innovation Manager"),
    ("Laura", "Bek", "LEGO Group", "Product Owner"),
    ("Nikolaj", "Frost", "GN Store Nord", "Hardware Lead"),
    ("Josefine", "Krag", "Lunar", "Product Manager"),
    ("Rune", "Dalgaard", "Ramboll", "Chief Engineer"),
    ("Amalie", "Holm", "Novo Nordisk", "Medical Writer"),
    ("Mikkel", "Ravnkilde", "Netcompany", "Developer"),
    ("Sofia", "Lind", "Spotify", "People Partner"),
    ("Christian", "Bach", "Ericsson", "Talent Acquisition"),
    ("Line", "Toft", "Vestas", "Supply Chain Lead"),
    ("Gustav", "Lindberg", "Klarna", "Staff Engineer"),
    ("Caroline", "Mose", "Coloplast", "Product Strategy"),
    ("Villads", "Krag", "IBM", "Delivery Manager"),
    ("Birgitte", "Sand", "Tryg", "Actuary"),
    ("Frederik", "Holm", "Lunar", "Frontend Developer"),
    ("Anna", "Berg", "Volvo", "Quality Manager"),
    ("Henrik", "Nygaard", "Grundfos", "Systems Engineer"),
    ("Signe", "Vestergaard", "GN Store Nord", "Brand Manager"),
    ("Bo", "Knudsen", "Ørsted", "Marine Engineer"),
    ("Tina", "Overgaard", "Danske Bank", "Data Engineer"),
    ("Kasper", "Riis", "Trustpilot", "Product Analyst"),
    ("Marie", "Dahl", "Bang & Olufsen", "Interaction Designer"),
    ("Jacob", "Bruun", "Carlsberg Group", "Sustainability Lead"),
    ("Asta", "Jensen", "LEGO Group", "Community Manager"),
    ("Simon", "Vestergaard", "Ramboll", "Geotechnical Engineer"),
    ("Nina", "Bach", "Coloplast", "Nurse Educator"),
    ("Peter", "Schmidt", "Siemens", "Plant Manager"),
    ("Lise", "Holm", "Novo Nordisk", "Research Scientist"),
    ("Anders", "Riis", "Ramboll", "Project Director"),
    ("Gitte", "Munk", "Tryg", "HR Business Partner"),
    ("Jan", "Overgaard", "Grundfos", "Purchasing Manager"),
    ("Susanne", "Krag", "Lunar", "Compliance Officer"),
    ("Bent", "Poulsen", "Vestas", "Site Manager"),
    ("Anna", "Friis", "Netcompany", "Test Manager"),
    ("Kim", "Strøm", "Ericsson", "Radio Engineer"),
    ("Mads", "Winther", "Ørsted", "Data Analyst"),
    ("Trine", "Berg", "Klarna", "Product Owner"),
    ("Johan", "Lund", "Spotify", "Staff Product Manager"),
    ("Siri", "Kjeldsen", "GN Store Nord", "Design Lead"),
    ("Halvor", "Nilsen", "Vestas", "Automation Engineer"),
    ("Lea", "Sommer", "Coloplast", "Legal Counsel"),
    ("Morten", "Bak", "Ørsted", "Construction Lead"),
    ("Josefine", "Ravn", "LEGO Group", "Community Manager"),
    ("Anders", "Grut", "IBM", "Cloud Architect"),
    ("Ida", "Krogh", "Trustpilot", "Researcher"),
    ("Peter", "Bang", "Carlsberg Group", "Category Manager"),
    ("Sara", "Lyngsø", "Bang & Olufsen", "Audio Engineer"),
    ("Mads", "Thygesen", "Grundfos", "Software Developer"),
    ("Anne", "Riise", "Tryg", "Underwriting Manager"),
]

POS_OPEN = [
    "Hi {f} — hope the week is treating you kindly. I saw you moved into the {co} role; " \
    "congrats on it. What made you take it?",
    "Hello {f}, good to see you active on LinkedIn again. How is the move to {co} going so far?",
    "Hi {f}, we spoke briefly at the conference last autumn and I never followed up. " \
    "Sorry about that. What have you been up to since?",
    "Hi {f}, I have been trying to get my head around how teams at {co} structure product " \
    "ownership. Curious how it works there in practice?",
    "Hey {f} — I am putting together a small roundtable on product discovery and you were " \
    "the first name I thought of. Interested?",
    "Hi {f}, noticed you are hiring for design at {co}. Not looking, but I always like to " \
    "know who is building what.",
    "Hello {f}, random question — how do you handle roadmap trade-offs when engineering " \
    "capacity is fixed? Curious about your approach at {co}.",
    "Hi {f}, it has been a while. I moved teams this year and would like to catch up properly. " \
    "Coffee sometime?",
]

REPLY_WARM = [
    "Thanks for reaching out {f}! That is genuinely interesting, and yes — let's find a time.",
    "Hi, good to hear from you. Yes definitely, I have been meaning to catch up too.",
    "Hey — really kind of you to write. Let's talk. Are you free the week after next?",
    "That is a great question. Happy to chat about it, I have a view or two.",
    "Perfect timing actually, we are rethinking exactly that at the moment.",
    "Thanks {f} — yes! Let's do a proper coffee, not a fifteen-minute hallway thing.",
    "Ha, I was just reading your post and thinking the same thing. Let's catch up.",
]

REPLY_NEUTRAL = [
    "Thanks {f} — yes, makes sense. Let me think about it and get back to you.",
    "Appreciate the message. Things are hectic but good.",
    "Hi, good to hear from you. How have you been?",
    "Noted, thanks for the heads up.",
    "That is interesting. I will have a look.",
]

REPLY_CLOSE = [
    "Thanks for thinking of me, but I am pretty happy where I am at the moment. " \
    "I hope it goes well.",
    "Thanks {f}, but I am not looking at the moment. Best of luck with it.",
    "Much appreciated, though this is not quite the direction I am heading in.",
    "Thanks for the invitation, but I should probably pass on this one.",
]

REPLY_IGNORE = []  # no reply at all is handled by not generating one

PROMISES = [
    ("let us talk after the summer", "September"),
    ("speak again in August", "August"),
    ("circle back in the new year", "January"),
    ("catch up once things settle down", "October"),
    ("reconnect in the spring", "April"),
]

# Outbound invites that were never accepted - they show up in the "waiting" count.
PENDING_NAMES = [
    "Benedikte Holst", "Christian Krogh", "Nina Bjerre", "Peter Salomonsen",
    "Amalie Winther", "Jonas Falk", "Signe Vestergaard",
]


def slug(first, last):
    s = f"{first}-{last}".lower()
    for ch in ("æ", "ø", "å"):
        s = s.replace(ch, {"æ": "ae", "ø": "oe", "å": "aa"}[ch])
    return "".join(ch for ch in s if ch.isalnum() or ch == "-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=len(PEOPLE), help="how many fake connections")
    ap.add_argument("--out", default="demo_export")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    people = PEOPLE[:args.n]
    out = HERE / args.out
    (out / "Jobs").mkdir(parents=True, exist_ok=True)

    now = datetime(2026, 9, 25, 9, 0, tzinfo=timezone.utc)
    me_url = urllib.parse.quote(ME_URL, safe=":/")

    # ---------------- Connections.csv ----------------
    # LinkedIn puts three lines of provenance above the real header; the build
    # skips them with skiprows=3, so the demo has to reproduce that.
    rows = []
    for first, last, co, pos in people:
        url = f"https://www.linkedin.com/in/{slug(first, last)}"
        conn = (now - timedelta(days=rng.randint(40, 2400))).strftime("%d %b %Y")
        rows.append({"First Name": first, "Last Name": last, "URL": url,
                     "Company": co, "Position": pos, "Connected On": conn})
    with open(out / "Connections.csv", "w", newline="", encoding="utf-8") as f:
        f.write("Note: This file was generated by Network Desk's demo export builder.\n")
        f.write("Every person, company and message in it is invented.\n")
        f.write("It exists so the pipeline can be run without a real export.\n")
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    # ---------------- messages.csv ----------------
    msgs = []
    me = dict(FROM=ME_NAME, **{"SENDER PROFILE URL": ME_URL})
    for first, last, co, pos in people:
        them_url = f"https://www.linkedin.com/in/{slug(first, last)}"
        them = dict(FROM=f"{first} {last}", **{"SENDER PROFILE URL": them_url})
        subj = "Quick question about " + co
        roll = rng.random()

        def stamp(days_ago, hour=9):
            return (now - timedelta(days=days_ago, hours=rng.randint(0, 8))
                    ).strftime("%Y-%m-%d %H:%M:%S UTC")

        def send(sender, recipient_name, recipient_url, days_ago, content):
            msgs.append({"FROM": sender["FROM"],
                         "SENDER PROFILE URL": sender["SENDER PROFILE URL"],
                         "TO": recipient_name,
                         "RECIPIENT PROFILE URLS": recipient_url,
                         "DATE": stamp(days_ago),
                         "FOLDER": "SENT" if sender["FROM"] == ME_NAME else "INBOX",
                         "SUBJECT": subj,
                         "CONTENT": content})

        # 1. never messaged - a first-class state the tool is built around
        if roll < 0.22:
            continue

        start = rng.randint(20, 700)
        send(me, them["FROM"], them_url, start,
             rng.choice(POS_OPEN).format(f=first, co=co))

        # 2. no reply at all
        if roll < 0.40:
            continue

        send(them, ME_NAME, ME_URL, start - rng.randint(2, 20),
             rng.choice(REPLY_NEUTRAL))

        # 3. warm, then went quiet - the "worth keeping warm" pile
        if roll < 0.56:
            send(me, them["FROM"], them_url, start - 25,
                 "Thanks for that - it is exactly the problem I was trying to describe.")
            return_early = rng.random() < 0.5
            if not return_early:
                send(them, ME_NAME, ME_URL, start - 30,
                     "Sorry, lost track of this one. What are you working on now?")
            continue

        # 4. politely closed out
        if roll < 0.64:
            send(them, ME_NAME, ME_URL, start - rng.randint(1, 9),
                 rng.choice(REPLY_CLOSE))
            continue

        # 5. they made a promise with a date in it
        if roll < 0.72:
            phrase, label = rng.choice(PROMISES)
            send(them, ME_NAME, ME_URL, start - rng.randint(1, 12),
                 f"Good to hear from you {first}! It has been a busy quarter here too, " \
                 f"so {phrase}.")
            continue

        # 6. ball is in my court - a live card on Today
        send(them, ME_NAME, ME_URL, start - rng.randint(1, 6),
             rng.choice(REPLY_WARM))
        continue

    with open(out / "messages.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["FROM", "SENDER PROFILE URL", "TO",
                                          "RECIPIENT PROFILE URLS", "DATE",
                                          "FOLDER", "SUBJECT", "CONTENT"])
        w.writeheader()
        w.writerows(msgs)

    # ---------------- Invitations.csv ----------------
    inv = []
    for i in range(18):
        p = people[i % len(people)]
        inv.append({"Direction": "OUTGOING",
                    "From": ME_NAME, "To": f"{p[0]} {p[1]}",
                    "inviteeProfileUrl": f"https://www.linkedin.com/in/{slug(p[0], p[1])}",
                    "inviterProfileUrl": "", "Sent At":
                    (now - timedelta(days=rng.randint(2, 90))).strftime("%m/%d/%y, %I:%M %p"),
                    "Invitation Type": "Personal", "Status": "Pending"})
    for p in PENDING_NAMES:
        inv.append({"Direction": "OUTGOING", "From": ME_NAME, "To": p,
                    "inviteeProfileUrl": "", "inviterProfileUrl": "", "Sent At":
                    (now - timedelta(days=rng.randint(1, 30))).strftime("%m/%d/%y, %I:%M %p"),
                    "Invitation Type": "Personal", "Status": "Pending"})
    for i in range(6):
        p = people[(i * 5) % len(people)]
        inv.append({"Direction": "INCOMING",
                    "From": f"{p[0]} {p[1]}", "To": ME_NAME,
                    "inviteeProfileUrl": "",
                    "inviterProfileUrl": f"https://www.linkedin.com/in/{slug(p[0], p[1])}",
                    "Sent At": (now - timedelta(days=rng.randint(2, 200))
                                ).strftime("%m/%d/%y, %I:%M %p"),
                    "Invitation Type": "Personal", "Status": "Accepted"})
    with open(out / "Invitations.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["From", "To", "Direction",
                                          "inviteeProfileUrl", "inviterProfileUrl",
                                          "Sent At", "Invitation Type", "Status"])
        w.writeheader()
        w.writerows(inv)

    # ---------------- Jobs ----------------
    jobs = [("Novo Nordisk", "Senior Product Owner", 6),
            ("Grundfos", "Product Manager, Digital", 13),
            ("Ørsted", "Product Lead, Offshore", 2),
            ("Lunar", "Product Owner, Payments", 21)]
    with open(out / "Jobs" / "Saved Jobs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Company Name", "Job Title", "Saved Date", "Job Url"])
        for co, title, d in jobs:
            w.writerow([co, title,
                        (now - timedelta(days=d)).strftime("%m/%d/%y, %I:%M %p"),
                        f"https://www.linkedin.com/jobs/view/{slug(co, title)}"])
    with open(out / "Jobs" / "Job Applications.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Company Name", "Job Title", "Application Date", "Job Url"])
        w.writerow(["Novo Nordisk", "Product Owner, Diabetes",
                    (now - timedelta(days=4)).strftime("%m/%d/%y, %I:%M %p"),
                    "https://www.linkedin.com/jobs/view/demo-1"])
        w.writerow(["Vestas", "Senior Product Manager",
                    (now - timedelta(days=33)).strftime("%m/%d/%y, %I:%M %p"),
                    "https://www.linkedin.com/jobs/view/demo-2"])

    # ---------------- Company Follows / Member Follows ----------------
    with open(out / "Company Follows.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Followed On", "Organization"])
        for co, d in [("Widex", 3), ("Sky DK", 9), ("Norlys", 15), ("Haldor Topsoe", 40),
                      ("Siteimprove", 2), ("Trackunit", 55)]:
            w.writerow([(now - timedelta(days=d)).strftime("%a %b %d %H:%M:%S UTC %Y"), co])

    with open(out / "Member_Follows.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Status", "FullName"])
        for nm, d in [("Karen Sørensen", 1), ("Peter Rønde", 8), ("Astrid Bruun", 14),
                      ("Michael Sjöholm", 20), ("Trine Dahl", 3)]:
            w.writerow([(now - timedelta(days=d)).strftime("%Y-%m-%d"), "Active", nm])

    # Required by the build but not read by any stage - present so it does not stop.
    with open(out / "Profile.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["First Name", "Last Name", "Headline", "Email Address", "City", "Country"])
        w.writerow(["Vipin", "Singh Dunbar", "Product Owner", "", "Copenhagen", "Denmark"])
    with open(out / "Positions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Company Name", "Title", "Started On", "Ended On"])
        w.writerow(["Demo ApS", "Product Owner", "2023-01-01", ""])

    print(f"\n  Wrote a synthetic export to {out.name}/")
    print(f"    {len(rows)} connections, {len(msgs)} messages, {len(inv)} invitations.")
    print( "    Every name in it is invented. Delete the folder when you are done.\n")


if __name__ == "__main__":
    main()
