## Inspiration

I work with Baltimore communities through the digital navigator program, and I have watched
people find out too late. Not because the information was hidden. Baltimore publishes
everything. It is on Legistar, it has a file number, it is searchable.

They found out too late because the thing that affected them did not arrive in one piece. It
arrived as a bill in 2023 that died quietly, and then again in 2026 under a different number,
with a different title, about the same land. Nobody in the neighborhood connected the two,
because connecting them requires somebody to be watching for two and a half years.

That is the whole idea. Cities do not decide things in one sitting. They decide slowly, across
many meetings, under changing labels. Residents do not lose because they are apathetic. They
lose because no one can hold the thread that long.

I wanted to find out whether an agent could hold it.

## What it does

Quorum reads Baltimore City Council's published legislative record, resolves each item to a
parcel, and decides whether a new record continues an issue it has already seen or starts a new
one. When something on a watched address comes back, it explains what changed since last time
and drafts a public comment carrying the correct file number and hearing date.

Then it stops. Quorum never submits anything on anyone's behalf. The button opens your own
email client, and the interface says so.

The case it is built around is real and you can check it while you judge this. Bill 23-0411
proposed rezoning 205-209 East Cold Spring Lane in Baltimore in July 2023, and it failed at the
end of the council term without a vote. In February 2026 the same sponsor filed it again as
26-0148, covering two lots where the first covered three. **The public hearing is 24 September
2026.** That date is after this deadline and inside the judging window. Open Legistar and look.

The file numbers share nothing. The titles differ in formatting. What links them is the parcel.

## How we built it

Four Strands agents and one deterministic node, assembled as a Strands `Graph` and deployed to
Amazon Bedrock AgentCore Runtime with OpenTelemetry tracing.

The node that is not an agent is the interesting one. Resolution turns the text of a record into
a parcel identifier, and it makes no model call at all. Address normalization is a solved
problem, and a hallucinated parcel identifier is the single error in this system a user could
never detect. So it is code, inside the Graph, on the same orchestration surface as the agents.

The Continuity Agent is the one that matters. It does not get asked "are these the same?" It
gets a comparison table computed deterministically in code, parcel match, sponsor overlap,
zoning transition, committee progression, title similarity, and it has to say which of those
drove its decision and which it explicitly set aside. That last part is the product. A
similarity score cannot be interrogated. A decision that says "I used the parcel and the
terminal status, and I ignored the title similarity of 0.943 because rezoning titles are
boilerplate" can be checked line by line.

Everything runs on a cached, timestamped corpus: 1,679 council records and 237,092 parcels from
the city's own open property layer. No demo touches the live internet.

## Challenges we ran into

**The evaluation nearly killed the project, and publishing that is the best thing in it.**

We hand labeled 50 pairs and the agent got 50 of 50. Then we wrote the baselines, and a tuned
two clause rule, `parcel exact OR (cosine >= 0.97 AND prior terminal)`, also got 50 of 50. Our
own evidence said the agent was unnecessary.

So we went at it properly. A held out split with the threshold frozen on a tune half before
touching the test half: it separates nothing, McNemar p = 1.0, and we report that as a null
result rather than burying it. An ablation that strips every domain hint out of the prompt: 47
of 50, against 78% for the best single deterministic feature, so the model is reasoning from the
evidence table rather than reciting the prompt. And a per tier breakdown, which is where the
real answer was hiding: on the parcel tier a lookup is perfect, and **on the citywide tier that
same lookup finds 0 of 11 true continuations**, because those records name no property at all.
58% of every real continuation in the set has no parcel.

The honest division of labour is a lookup where a lookup is exact, and a model where the
alternative is a threshold we already showed is brittle.

**The agent hallucinated a fact in the one paragraph that matters most.** The drafted comment
told a resident that EC-2 is "a commercial district that allows shops and apartments." It is
not. EC-2 is Baltimore's Educational Campus district, and our own parcel table proves it: all
274 EC-2 parcels in the city belong to the State of Maryland, Loyola or Johns Hopkins. The real
story is a university expanding its campus. That false sentence sat directly under a line
claiming nothing in the draft could be contradicted by the file. We fixed it at the root by
computing zoning facts from the parcel data and forbidding the agent from characterizing a
district code it was not given facts for.

**Three bugs existed only in deployment.** Cold start exceeded AgentCore's 30 second limit
because the module imported everything at load time. Path resolution assumed a repository layout
that direct code deploy flattens. And direct code deploy packages only the entrypoint's own
directory, so the corpus was never in the image. The fix made the design better: the runtime now
ships a 339 KB bundle of exactly the 50 labeled pairs instead of a corpus it can never use.

**The rate limiter on the public endpoint could not work.** AgentCore isolates every invocation
to its own container, so an in process counter never coordinates with anything. Measured worst
case was roughly 760 dollars a day against an intended five. The real limits had to live outside
the process: throttling at the API Gateway edge, and a shared daily counter in S3 written
conditionally so two containers cannot claim the same slot.

## Accomplishments that we're proud of

A judge can press a button on the site and run the agent themselves, on any of the 50 labeled
pairs including ones we never discuss, against the deployed AgentCore runtime. The AgentCore
session id is different on every call, which is how you know it is not a recording.

`eval/RESULTS.md` regenerates byte identically from a clean clone with no AWS credentials. Every
number on it is produced by running code. When we found a hardcoded number sitting under a
header promising otherwise, we replaced it with a function.

And we are proud of what the system refuses to do. It refuses to draft a comment on 18 of 19
threads, because their comment windows have closed and writing to a committee about a finished
bill wastes the little standing a resident has. It refuses to name private individuals as
property owners even though the public record does. It refuses to send.

## What we learned

That the most valuable output of an evaluation is the result that embarrasses you.

Our exhaustive search claimed the parcel population was complete. It was not, and the pair we
missed was a genuine false positive: a skybridge franchise and an alley closing three miles
apart matched because the parser read the phrase "a 10 foot alley" as a street called 10 Foot
Alley. A search that finds something is worth more than one that finds nothing, so it is written
up rather than quietly fixed.

We also learned where an agent belongs. The deterministic features do most of the work here. The
model generalizes from them better than any single feature does, and the domain knowledge in the
prompt buys exactly three cases: a liquor licence matched to its own zoning approval, a charter
amendment returning after a failed term, and one street condemnation split into two ordinances.
That is a hybrid, and saying so is more useful than claiming the agent is doing magic.

## What's next for Quorum

Neighborhood level watching. The parcel layer already carries a NEIGHBOR field, and a resident
does not fear a rezoning of their own parcel so much as the one across the street.

Closing the loop. Quorum notices and drafts, but it never learns what happened at the hearing.
Reading the minutes and the vote record afterwards would turn it from a monitor into something
that finishes what it starts.

And more cities, carefully. Legistar serves hundreds of American municipalities on the same API,
and the citywide tier, which is 11 of our 19 threads, needs no parcel gazetteer at all. The
adapter generalizes. The claim will not be made until it is tested.

For now the honest scope is one city, deep, and a hearing on 24 September that somebody on that
block now knows about.
