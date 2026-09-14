# Demo video, script and shot list

Target 4:24. The published cap is 5:00, confirmed against the official rules. Check it again
on the submission form before uploading. Public on YouTube or Vimeo.

Every number spoken here is checked against `docs/data/site.json` and `eval/RESULTS.md`.
Do not add one that is not.

## Opening, pick one

**A, cold open on the case.** Recommended.

> In July 2023, Baltimore's city council rezoned a block on Cold Spring Lane. The bill
> died. Nobody told the neighbours it came back. This year, under a different file
> number, it did.

**B, direct question.**

> How would you know if your city decided the same thing twice, two and a half years
> apart, under two different file numbers? Most people would not. That is the problem
> Quorum solves.

**C, the thesis, spoken slowly.**

> Cities decide slowly, across many meetings, under changing names. Residents lose,
> because nobody can hold the thread. Quorum holds the thread.

## Narration

Read this aloud. Written for the ear.

> In July 2023, Baltimore's city council rezoned a block on Cold Spring Lane. The bill
> died. Nobody told the neighbours it came back. This year, under a different file
> number, it did.
>
> Local government produces a lot of paper. Bills get renamed, reintroduced, buried in
> agendas. A resident with a full time job cannot track every filing that touches their
> block. Quorum is built for that resident. It watches Baltimore's council record so
> they do not have to.
>
> Here is a real example, live on the site right now. Bill 23-0411 rezoned 205 to 209
> East Cold Spring Lane, owned by Loyola University Maryland. It failed at the end of
> the council term. Two and a half years later the same sponsor, Mark Conway, filed it
> again, as 26-0148. Same rezoning, R-1-C to EC-2. One lot smaller. Different file
> number. Nothing links them by name. Quorum linked them anyway, because it is not
> reading titles. It is reading parcels.
>
> Here is the part that matters most. A public hearing on this exact bill is scheduled
> for September 24th. This video is due before that date. The hearing lands inside the
> judging window. You can go and look. And the city's own parcel records back it up
> independently. Block 5053I holds exactly two lots today, still zoned R-1-C. The 2023
> rezoning never happened.
>
> Here is why this is hard. Title similarity between those two bills is 0.943. Two
> completely different bills, on Mura Street, score 0.944. Higher, for the wrong reason.
> Any system built on text matching alone gets this backwards. What separates them is
> the parcel comparison, exact against merely adjacent, whether the earlier bill died,
> and whether the zoning transition repeats.
>
> A resident adds their address once. Quorum checks it against every new filing, across
> 237,092 parcels. Most weeks nothing shows up, and that is the point. When something
> does, it arrives in one feed, tied to the address, with the history attached.
>
> Quorum drafts a public comment, correct file number, correct hearing date, already
> filled in. And then it stops. The button opens your own email client. Quorum has not
> sent anything, and it never will.
>
> Underneath, this runs as a Strands Graph on Amazon Bedrock. Five stages. Four agents,
> and one deterministic node that resolves addresses to parcels with no model call at
> all. It read all 1,679 records in Baltimore's council corpus, cached and timestamped,
> nothing fetched live during this demo, and 270 of them named a parcel it could resolve.
>
> Now the honest part. Fifty hand labeled pairs, nineteen continuations, thirty one
> distinct issues. Quorum scored fifty out of fifty. So does a tuned two clause rule,
> and we say that plainly, because it is the strongest objection to this project. So we
> tested it. Strip every hint of domain knowledge out of the prompt and the agent still
> scores forty seven out of fifty, against seventy eight percent for the best single
> rule. What the knowledge buys back is three cases: a liquor licence matched to its own
> zoning approval, a charter amendment returning after a failed term, and one street
> condemnation split into two halves. That is not the rule in a costume.
>
> Quorum does not vote and it does not submit. It makes sure a resident finds out before
> the hearing, not after the vote.
>
> There is a hearing on this exact bill on September 24th. Go look.

## Shot list

Record in this order. The site lands on the hero thread with no clicking.

1. Two or three seconds of the dark backdrop before narration starts. No logo.
2. Load the site. It opens on **Thread** showing 23-0411 and 26-0148 by default. Hold on
   the headline.
3. Scroll slowly through the timeline spine.
4. Continue through the two appearance cards and the delta list under the newer one.
5. Stop on the hearing card at the bottom of the thread. This is the beat that matters.
6. Nav to **Evidence**. Both panels are there by default: the hero as a continuation, and
   701 against 702 Mura Street as not one. Show both cosine numbers on screen.
7. Nav to **Watch an address**. Type `205 East Cold Spring Lane` and add it.
8. Nav to **Feed**. Show the entries and the line about how many records were read.
9. Nav to **Draft comment**. Show the locked file number and hearing date, the drafted
   text, and the line saying Quorum has not sent anything. Hover the button. Do not click.
10. Still on **Thread**, scroll to **What actually arrives** and hold on the notification for
    five seconds. This is the product's whole premise in one artifact: the resident is not
    watching, so something has to arrive.
11. Nav to **Agent run**. Scroll straight past the runner to **Run it yourself**. Pick a pair
    from the dropdown, press the button, and let it run on camera. Read the session id and the
    latency off the screen out loud. Do not cut away while it thinks. This is the single
    strongest shot available and it takes about ten seconds.
12. Nav to **Evaluation**. Stop on the baselines table, specifically the row where the
    tuned two clause rule also scores 100%, then the ablation table under it.
13. Cut back to the hero thread for the close. End on black.

## The last line

> There is a hearing on this exact bill on September 24th. Go look.

Nail this in one take. It is checkable, it falls inside the judging window, and it is the
only claim in the video a judge can verify against the world rather than against us.

## Do not

No thank you slide. No team photo. No logo animation. No architecture before the problem
has landed. Never say leverage, seamlessly, or empowering communities.
