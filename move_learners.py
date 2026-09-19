"""Put the 119 learners back where they belong.

Every one of them is sitting on batch "d" - cancelled, with no course - and
is therefore invisible to every count, every report and every schedule sent
to the awarding body. This puts each one on the batch they actually studied
with.

WHERE THE GROUPING COMES FROM
-----------------------------
Not from guesswork. Each learner's email was matched against the enrolments
on the DHB Moodle platform, and the groups below are what Moodle says:

    57  enrolled ONLY in course 9  (IGC Arabic)
    53  enrolled in 6 + 9, and 46 of them have opened DI1 and never once
        opened IGC - so their real course is DI1
     7  enrolled in course 8 (IGC English)
     2  enrolled in course 12 (EMC)
     1  in no course at all - Dr Hassan's own line, already cancelled

First sign-in dates say both large groups are single August intakes:
IGC peaks on 22 August, DI1 on 21-22 August. Neither is a scattered remnant
of older cohorts.

HOW TO RUN IT
-------------
1. Fill in the four dates below. Nothing runs while any of them is blank -
   a batch date is what goes on a schedule sent to NEBOSH, and this script
   will not invent one.
2. Run it as it is. DRY_RUN is True, so it writes NOTHING and prints the
   whole plan: every learner, from which batch to which.
3. Read the plan. If it is right, set DRY_RUN = False and run it again.

It is safe to run twice: a learner already moved is skipped.
"""

# ====================================================================
# FILL THESE IN
# ====================================================================
# The August IGC intake. Moodle says the learners first signed in on
# 22 August. The end date is the one you know and Moodle does not.
IGC_START = ""          # e.g. "2026-08-22"
IGC_END   = ""          # e.g. "2026-10-03"

# The August DI1 intake. It has no batch in the system at all, so one is
# created with these dates.
DI1_START = ""          # e.g. "2026-08-21"
DI1_END   = ""          # e.g. "2026-11-15"

# The seven on IGC English. There is no English course in the catalogue, so
# they are LEFT WHERE THEY ARE and listed at the end, unless you put the
# code of a batch here.
IGC_EN_BATCH_CODE = ""

# Set to False only after you have read the plan.
DRY_RUN = True
# ====================================================================

IGC_AR_EMAILS = {
    "aalsawwed@gmail.com", "abdalrhmanmhh2@gmail.com",
    "abdot7471@gmail.com", "abdullamalik290@gmail.com",
    "adlanr4424@gmail.com", "ahmed27997@gmail.com",
    "ahmedfag09119@gmail.com", "ahmedsulimanelkamil@gmail.com",
    "ali999badarali999@gmail.com", "alibasheerpe2020@gmail.com",
    "alminshawi1991@gmail.com", "amar222co@gmail.com",
    "amgadkindera93@gmail.com", "azizfaisal00965@gmail.com",
    "bandrbnm9@gmail.com", "bdronew1@gmail.com", "bodzetrill@gmail.com",
    "bom6r@msn.com", "daoudy77@gmail.com", "dazzyzool81@gmail.com",
    "doha.ali20@outlook.sa", "elmashedali@gmail.com",
    "eng.mohamedalhaj@hotmail.com", "eng.zsalharbi@gmail.com",
    "fidih79194@bocably.com", "h714624@gmail.com",
    "hafizfath@gmail.com", "hossam.a.elmonem@gmail.com",
    "hozyfa225@gmail.com", "isam12041997@gmail.com",
    "joodabaa@gmail.com", "kalmohammadi18@gmail.com",
    "kg82055@gmail.com", "lookaaleem@gmail.com",
    "mahmo0000od121212@gmail.com", "mamounhassan252@gmail.com",
    "moh0696128@gmail.com", "mohamad.haroon888@gmail.com",
    "mohamadelfatih999@gmail.com", "mohamedelimam99@gmail.com",
    "mohamedezelden00@gmail.com", "mohamedhafezalla@gmail.com",
    "mohamedsalih491@yahoo.com", "mohammedabdelkarim82@gmail.com",
    "mohammedarafatahmedd@gmail.com", "mohammedyousif257@gmail.com",
    "mohannadfaiz1601@gmail.com", "mohtaha898@gmail.com",
    "mortada.mm16@gmail.com", "mustafaanamy@gmail.com",
    "natheer6020@gmail.com", "nosaosman7707@gmail.com",
    "osmanazoz9@gmail.com", "redcat.11110@gmail.com",
    "shnboo121@gmail.com", "wdyahia121h@gmail.com",
    "yousif_monem@yahoo.com",
}

DI1_EMAILS = {
    "a.eisawy@yahoo.com", "abadytaysir@gmail.com",
    "abdalsalammly@gmail.com", "ahmed.hussein125@gmail.com",
    "ahmed2emam22@gmail.com", "ahmedabdelraman88@gmail.com",
    "ahmedaldahalmu@gmail.com", "ahmednus17@gmail.com",
    "alaaalbashir2@gmail.com", "alaasatti777@gmail.com",
    "alhassanalskeikh@gmail.com", "altayebelgamri@gmail.com",
    "amakenplus001@gmail.com", "ammarmoment@gmail.com",
    "anasjota@gmail.com", "attafalbadri@yahoo.com",
    "ayc.marar@gmail.com", "ayman5yar212@gmail.com",
    "bahai007.ma@gmail.com", "ch.ahmedsamir3@gmail.com",
    "dbabikerhaj@gmail.com", "elgamlkhaled33@gmail.com",
    "eng.abdallahabass@gmail.com", "engmohammedbadwi@gmail.com",
    "ezeldeensaber88@gmail.com", "f.f3353@icloud.com",
    "hish.elbahrain@gmail.com", "husam94mohammed@gmail.com",
    "khalidhago44@gmail.com", "manal77707@gmail.com",
    "mepet38@gmail.com", "merghaniaboeesa@gmail.com",
    "mo9911hamed@gmail.com", "mohammedaljafary951@gmail.com",
    "mohammedballa1992@gmail.com", "mohmmedaltiyb@gmail.com",
    "montasirmudawi@hotmail.com", "mrifeat@gmail.com",
    "nazaralsawi@gmail.com", "omerkhalid010101@gmail.com",
    "otaibi84@hotmail.com", "othmanhamed1989@gmail.com",
    "rayan.khairalseed@gmail.com", "samialfadil999@gmail.com",
    "samiharron@gmail.com", "sharwany2010@hotmail.com",
    "sheref156@gmail.com", "tagwa9991@gmail.com", "tft124@gmail.com",
    "wadhamed21@hotmail.com", "walid_osman2003@yahoo.com",
    "youssefhsse@gmail.com", "zainab.a.m.qan@gmail.com",
}

IGC_EN_EMAILS = {
    "arwawad@gmail.com", "hibamohee1224@gmail.com",
    "hindoya589@gmail.com", "mohamed.mudawi1989@gmail.com",
    "mustafaboraui@gmail.com", "nemer770@gmail.com",
    "osamahassan0066@gmail.com",
}

EMC_EMAILS = {
    "alderawihussein4@gmail.com", "mamojust15@gmail.com",
}

SOURCE_BATCH_NAME = "d"


def find_batch(env, code=None, course_code=None):
    """The existing batch for a course, by its code or its course."""
    batches = env["dhb.batch"]
    if code:
        found = batches.search([("code", "=", code)], limit=1)
        if found:
            return found
    if course_code:
        course = env["dhb.course"].search([("code", "=", course_code)], limit=1)
        if course:
            return batches.search(
                [("course_id", "=", course.id)], order="date_begin desc",
                limit=1)
    return batches


def ensure_di1_batch(env, dry_run):
    """DI1 has no batch at all. Make one, or describe the one we would."""
    existing = find_batch(env, course_code="DI1")
    if existing:
        return existing, False
    course = env["dhb.course"].search([("code", "=", "DI1")], limit=1)
    if not course:
        raise SystemExit("No course with code DI1 - cannot place 53 learners.")
    values = {
        "name": "DI1 - August 2026 - Group 1",
        "course_id": course.id,
        "date_begin": DI1_START + " 00:00:00",
        "date_end": DI1_END + " 23:59:59",
    }
    if dry_run:
        print("  WOULD CREATE batch: %s  (%s -> %s)"
              % (values["name"], DI1_START, DI1_END))
        return env["dhb.batch"], True
    return env["dhb.batch"].create(values), True


def main(env):
    for label, value in (("IGC_START", IGC_START), ("IGC_END", IGC_END),
                         ("DI1_START", DI1_START), ("DI1_END", DI1_END)):
        if not value:
            raise SystemExit(
                "%s is empty. Fill in all four dates first - a batch date is "
                "what goes on a schedule sent to NEBOSH, and this script will "
                "not invent one." % label)

    source = env["dhb.batch"].search(
        [("name", "=", SOURCE_BATCH_NAME)], limit=1)
    if not source:
        raise SystemExit('No batch named "%s" - nothing to move.'
                         % SOURCE_BATCH_NAME)

    igc = find_batch(env, course_code="IGC")
    emc = find_batch(env, course_code="EMC")
    if not igc:
        raise SystemExit("No IGC batch found.")

    di1, created = ensure_di1_batch(env, DRY_RUN)
    en_batch = find_batch(env, code=IGC_EN_BATCH_CODE) \
        if IGC_EN_BATCH_CODE else env["dhb.batch"]

    plan = [
        ("IGC Arabic", IGC_AR_EMAILS, igc),
        ("DI1", DI1_EMAILS, di1),
        ("EMC", EMC_EMAILS, emc),
        ("IGC English", IGC_EN_EMAILS, en_batch),
    ]

    lines = env["dhb.batch.line"].search([("event_id", "=", source.id)])
    by_mail = {}
    for line in lines:
        if line.email:
            by_mail.setdefault(line.email.lower().strip(), line)

    moved = skipped = stranded = 0
    print("=" * 74)
    print("FROM: %s (id %s, %s)" % (source.name, source.id, source.state))
    print("=" * 74)

    for label, emails, target in plan:
        print("\n--- %s -> %s" % (
            label, target.display_name if target else "*** NO BATCH ***"))
        for mail in sorted(emails):
            line = by_mail.get(mail)
            if not line:
                print("      not on the source batch: %s" % mail)
                continue
            who = line.name or mail
            if not target:
                print("      LEFT  %-38s %s" % (who[:38], mail))
                stranded += 1
                continue
            print("      move  %-38s %s" % (who[:38], mail))
            if not DRY_RUN:
                line.event_id = target.id
            moved += 1

    left = env["dhb.batch.line"].search_count([("event_id", "=", source.id)])
    print("\n" + "=" * 74)
    print("to move: %s     left where they are: %s" % (moved, stranded))
    print("still on the source batch afterwards: %s"
          % (left - moved if not DRY_RUN else left))

    # The dates, last, so that a failure above changes nothing.
    if not DRY_RUN:
        igc.write({"date_begin": IGC_START + " 00:00:00",
                   "date_end": IGC_END + " 23:59:59"})
        print("\nIGC batch dates set: %s -> %s" % (IGC_START, IGC_END))
        if "September" in (igc.name or "") and IGC_START.startswith("2026-08"):
            print("  NOTE: this batch is named %r but now runs in August."
                  % igc.name)
            print("  The name and the code are NOT changed here - the code "
                  "may already be on paperwork sent to NEBOSH. Rename it by "
                  "hand if it is not.")
        env.cr.commit()
        print("\nCommitted.")
    else:
        print("\nDRY RUN - nothing was written. Set DRY_RUN = False to apply.")


main(env)
