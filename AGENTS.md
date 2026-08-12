# AGENTS.md — process contract for agents working in this repository

This file is the **process** half of the agent rules: how work is divided, what counts
as evidence, and what gates a merge or a release. It is written to survive being copied
into an unrelated repository.

**Charter.** Normative rules here are repo-independent — a rule that would stop making
sense in another repository does not belong in this file and lives in
[CLAUDE.md](CLAUDE.md) instead. Illustrative examples drawn from this repository *do*
appear here, because a rule nobody can picture is a rule nobody follows. Examples are
marked as examples and are never the normative statement; the rule is always the
sentence, not the example.

Where a rule needs a concrete instance ("which files are user-owned?", "which command
runs the suite?", "what is the release procedure?"), CLAUDE.md holds the answer. Follow
the link rather than assuming.

---

## 0. How to read the prohibitions

Rules in this file and in CLAUDE.md are marked with one of **three** tags. They are not
degrees of the same thing — they differ in whether any path forward exists, and in
whether *who you are* is part of the answer.

> **[NEVER]** — There is no path. No agent may do this, no agent may authorize it, and
> asking is not the remedy. If a task appears to require it, the task is wrong.

> **[ASK]** — Permitted, but only with explicit authorization, from the party named in
> the rule. The default answer is no. You may ask; you may not proceed while waiting,
> and silence is not consent. Authorization is per-instance: approval to do it once is
> not approval to do it again.

> **[ASK-OP]** — Everything [ASK] requires, **plus an eligibility condition that
> authorization cannot satisfy**: only an agent holding the release-operator role (§1)
> may perform it, and every quality gate must already have passed and been recorded.
> The role requirement is itself a [NEVER] for everyone else — no authorization from any
> party lifts it, because it is separation of duties rather than permission.

**`[ASK-OP]` is one token, not `[ASK]` with a comment after it.** The restriction is
part of the tag, and an agent that reads only the `[ASK]` and treats the rest as prose
has misread it. Wherever this tag appears, the eligibility condition applies in full;
the tag is never written as a bare `[ASK]` followed by a qualifying clause.

**Why the third tag exists.** Two tags can express *whether* an action may happen but
not *who* may perform it, and for actions that commit a principal's identity those are
different questions with different answers — the principal can license the act while
still requiring that a party with no stake in the outcome carries it out.

Anything unmarked is ordinary guidance — follow it, use judgement, and say so if you
depart from it.

**All three tags are about permission, never about correctness.** They answer "may I?", not
"is this right?". A statement that some implementation is simply *wrong* — that summing
a set of values miscounts, that an ordering produces the incorrect result — is a
correctness fact, and it carries no tag even when stated emphatically. The distinction
matters because the remedies differ: a permission rule is resolved by asking the right
party, while a correctness fact is resolved only by the code being right. Asking
permission to compute a wrong number is not a coherent request.

---

## 1. Roles

Every change has four roles, plus one that exists only at release time. **One agent holds
at most one role per change.**

| Role | Owns | Must not |
| --- | --- | --- |
| **Developer** | The production files of the change (§2 defines "production file"). | Author or alter the tests that gate the change (§2 Condition A). |
| **Verifier** | Tests, fixtures, and the run that proves the change works. | Have edited any production file of this change (§2 Condition B). |
| **Reviewer** | Reading the diff for correctness and scope; sign-off. | Sign off on their own code or their own tests. |
| **Coordinator** | Role assignment, file ownership, the merge decision (§8). | Silently absorb another role to unblock themselves. |
| **Release operator** | Executing authorized release steps in order, recording each outcome, stopping on first failure. | Have held **any other role** — Developer, Verifier, Reviewer, **or Coordinator** — on anything in the release. |

**The release operator is a separation-of-duties role, and it is the only role permitted
to perform the credential-bearing actions in
[§6's second class](#outward-facing-steps-two-classes-not-one).** It is deliberately
narrow: the party who wrote, tested, or blessed an artifact must not also be the party who
signs the principal's name to it, because those are the two judgements that most need to
be made independently — "is this correct" and "is this what we are willing to vouch for".
An agent that has not held a role on the change may take it; an agent that has, may not.

**The Coordinator is excluded too, and that is the case most worth stating.** §6 requires
the Coordinator's recorded sign-off that a release is ready. If the Coordinator could also
operate the release, the party certifying "this is ready to ship" would be the party
signing the principal's name to it — the same self-approval loop §1 forbids a Reviewer,
reappearing at the release boundary where it matters most. The Coordinator also owns role
assignment, so without this clause it could simply appoint itself. **A Coordinator may
never take the operator role on a release it coordinated.**

Holding this role is not itself authorization. It determines *who may act once the
principal has authorized*, never *whether* they have.

Roles are per-change, not per-session. An agent that was Developer on change A may be
Verifier on change B. What is forbidden is holding two roles on the *same* change.

An agent holding **no role** on a change is *uninvolved* in it. Uninvolved agents are a
resource, not a gap: §2 Condition C draws on them. "Uninvolved" is about this change
only — an agent uninvolved in change B is uninvolved even if it was Developer on A.

If only one agent is available, that is not an exemption — it is a declared exception,
handled under §2 Condition C.

---

## 2. Developer–Verifier separation

This is the rule most often reduced to a slogan. It is stated here as three checkable
conditions. A reviewer can confirm or refute each one from the diff and the git log
alone, without asking anyone what they intended.

### What counts as a production file

A **production file** is any file that is not a test and not documentation, whose
content determines the behaviour of the shipped product — application source, build
configuration, packaging manifests, and anything else that changes what a user runs.

Tests, fixtures, and test helpers are **not** production files; neither are Markdown
documents. A change may have several production files, which is why the checks below
are phrased over *sets* of files even where the prose says "the production file" for
readability. CLAUDE.md's repo layout identifies which files in this repository are
production files.

**Condition A — the Developer does not touch the gating assertions.**
The Developer must not author, modify, reorder, delete, or relax the assertions or
fixtures of any test that gates their change. "Reorder" is included deliberately:
changing the order of values in a fixture can silently change what the test
discriminates (§3). Renaming a test, adjusting its docstring, or fixing an import is
not a gating change; touching an `assert`, an expected value, or a fixture literal is.

A Developer **may** write tests that do not gate the change — exploratory tests,
scratch reproductions, characterization tests of existing behaviour — and may propose
test cases in prose for the Verifier to implement. What they may not do is author the
assertions that the change is then judged against. If a Developer-written test is later
promoted to gating status, the Verifier must re-derive its expected values
independently before it counts (§2 Condition C describes what re-derivation means).

*Check:* in the diff, no commit whose author is the Developer modifies assertion or
fixture lines in the gating test file.

**Condition B — the Verifier has clean hands on the production files.**
The Verifier must be an agent that has edited **none** of the production files of this
change. Not "has not edited them much" — has not edited them at all. An agent who wrote
the fix cannot be the one who confirms the fix works, because both activities draw on
the same mistaken model of the problem, and a wrong model produces a fix and a test
that agree with each other and disagree with reality.

*Check:* the set of files the Verifier edited and the set of production files this
change edited are disjoint.

**Condition C — a declared exception requires an independent re-derivation.**
Sometimes separation genuinely cannot be maintained. That is permitted only if it is
*declared*, in the change description, before merge — never discovered afterwards.

The re-derivation must be performed by an agent that holds **either the Reviewer role
or no role at all** on this change. This does not create a fifth role and does not break
the one-role cap in §1: re-deriving is a duty attached to the Reviewer role, or a task
handed to an uninvolved agent, who by definition has a role to spare.

To **re-derive** is to recompute the expected values from the specification or from
first principles, *without reading the existing test's expected values first*, and then
state whether they match. "I ran the suite and it passed" is not a re-derivation; the
suite passing is precisely what is in question.

*Check:* the change description names the exception, names the re-deriver, records the
numbers that agent derived independently, and states that they were derived before the
existing expected values were read.

---

## 3. Red before green

**A test that has never been observed failing has not been shown to test anything.**

The required sequence is:

1. Write the test against the **unfixed** code.
2. **Run it and watch it fail.** Record the failure output — the actual assertion
   message, not a claim that it failed.
3. Land the fix.
4. Run it again and watch it pass.

Step 2 is not a formality, and it cannot be reconstructed from memory. Once the fix is
in the working tree, the opportunity to observe the red state has passed.

### The non-discriminating test hazard

A test that passes *before* the fix proves nothing. It is not a weak test — it is a
test of nothing at all, and it is dangerous precisely because it is green in the final
state and therefore looks like evidence.

The general failure: a fixture can be constructed so that the correct behaviour and a
bug produce **the same** result. The test then passes in both worlds, distinguishes
neither, and looks exactly like a passing test that does.

### The rule

**Enumerate every plausible wrong behaviour, and confirm the fixture yields a distinct
result under each one. If any rival collapses onto the correct answer, the fixture is
unfinished.**

Three things in that sentence carry the weight:

- **Every, and plural.** Not "the wrong behaviour" — there is almost never just one.
  Ruling out one rival while a second still agrees with the correct answer produces a
  test that feels discriminating and is not. Write the list down.
- **Distinct result under each.** Not "would probably differ" — compute what each rival
  actually returns for this fixture and check that no two of them coincide with the
  expected value.
- **Plausible.** Rivals worth listing are the implementations someone might actually
  write, especially the one the language makes easiest to write by accident.

The practical form is a truth table: fixture down one side, candidate implementations
across the top, and the expected value in one cell of each row. If the expected value
appears twice in a row, that row proves nothing about the two behaviours that tied.

> *Example (from this repository; the rule is the statement above, not this case).*
> Log rows repeat, and the correct behaviour is to keep the **maximum** of a duplicate
> set. The plausible rivals are first-wins, last-wins (which is what a plain
> `seen[key] = row` overwrite gives you, and so the easiest to write by accident), and
> summing. For a two-row fixture:
>
> | rows (encounter order) | first | last | **max** | sum |
> | --- | --- | --- | --- | --- |
> | `[200, 5]` | 200 | 5 | **200** | 205 |
> | `[5, 200]` | 5 | 200 | **200** | 205 |
>
> The originally written fixture was `[200, 5]`, where first-wins ties with max — the
> bug being fixed was invisible. Reordering to `[5, 200]` does not fix it: it merely
> swaps which rival ties, since last-wins now agrees instead. **With two rows this is
> impossible in principle** — the maximum is necessarily either the first element or the
> last, so it always coincides with one rival.
>
> A single three-row fixture with the maximum strictly interior settles all four at
> once: `[5, 200, 50]` gives first 5, last 50, max 200, sum 255 — every candidate
> distinct. One fixture is enough; what was missing was never a count of fixtures but
> the enumeration that would have revealed the tie.
>
> The production rule this protects, and its full list of rejected behaviours, are in
> [CLAUDE.md's JSONL invariants](CLAUDE.md#jsonl-invariants); they are not restated here.

**Tie-break behaviour needs its own fixture.** A rule of the form "on equal values, keep
the later one" is exercised by *no* ordering of distinct values — every fixture above has
a unique maximum, so the tie-break branch never executes. Testing it requires a fixture
with two genuinely equal values that differ in the discriminator (here: equal weighted
totals with different timestamps), asserting that the expected one survives. A test suite
that covers the main rule and skips this leaves the tie-break entirely unexecuted while
reporting full green.

This is also why Condition A forbids *reordering* fixtures, not just editing assertions:
`[5, 200, 50]` → `[200, 50, 5]` changes no assertion and silently reintroduces the tie.

### When a non-discriminating test is found after the fix landed

Do not simply reorder the fixture and call it verified — that produces a green test
whose red state still nobody has seen.

1. **Preferred: revert and observe.** Restore the pre-fix behaviour in a scratch copy or
   a throwaway branch, run the corrected test, record the failure output, then discard
   the revert. This recovers genuine red-before-green evidence, and is almost always
   possible when the fix is a known diff.
2. **If that is impossible** — the pre-fix state cannot be reconstructed, or reverting
   would require touching files you may not touch — then **declare the evidence
   unrecoverable.** Say so in the change description, mark the test as *unverified
   red*, and treat the behaviour as untested until someone can produce a red run. Do
   not describe it as verified. An unverified test is a placeholder, not a gate.

**[NEVER]** present a test as red-before-green when the red run was not actually
observed. A fabricated or assumed red state is worse than a missing one: it converts an
open question into a false answer, which is the same failure mode as a wrong commit
trailer (§7).

---

## 4. Preserving untracked work

**[ASK] Untracked files are off-limits by default. You may create and modify the files
your assignment explicitly names as deliverables, and nothing else.**

### The rule is provenance plus authorization, not timing

A tempting definition is "files that existed before my task started are the user's".
Reject it. That predicate is recorded nowhere, so it cannot be reconstructed by anyone
auditing the change later — which defeats the whole purpose of §7's trailers, namely
being checkable from `git log` months afterwards by someone who was not present. It also
only defers the problem by one session: next session, a previous agent's untracked
deliverable is indistinguishable from a file the user hand-wrote.

Use provenance instead, made explicit at assignment time:

- **Default: off-limits.** Any untracked file is presumed to be someone else's work.
- **Deliverables are named in the assignment.** An agent may create and modify the files
  its assignment explicitly names as its deliverables — and only those.
- **The deliverable list goes in the change description.** This is what makes the
  decision auditable later: a reader can see which files this change was licensed to
  produce, without needing to know what the tree looked like at the time.
- **Anything not named is off-limits regardless of when it appeared** — before the task,
  during it, or created by a parallel agent. "It wasn't there an hour ago" licenses
  nothing.
- **Tracked files are outside this rule.** They have history, so a mistaken edit is
  recoverable and ordinary review governs them.

**[ASK] What an assignment may name is itself limited.** This rule's safety rests on
assignments being written responsibly, so the licence has a ceiling that no assignment
can raise on its own. An assignment may name as a deliverable only:

- a path that **does not yet exist**, or
- a path the **assigning party itself created**.

**Naming an already-existing untracked file that the assigning party did not create does
not license touching it** — that requires the user, directly. An assignment cannot
launder access to someone else's file by listing it. If your deliverable list names a
file you did not expect to already exist, stop and ask before touching it; discovering
that a "new" file is already there is a signal that it is someone else's, not an
invitation to overwrite it.

If your work genuinely requires touching an untracked file not on your list, stop and
ask. Only the user can authorize touching their own files; a Coordinator cannot grant
this, and neither can another agent. Ask, wait, and do not proceed meanwhile.

### The hard floor

These hold no matter how the definitional question is resolved, and they are what
actually prevents data loss.

**[NEVER] run a bulk destructive command against the working tree.** Not to tidy up, not
to reproduce a clean state, not before a build. This is absolute in the §0 sense: there
is no authorization path, because none is ever needed. If a specific file must go, delete
that file by name — a targeted deletion is reviewable and its blast radius is what you
typed. The banned forms, and what each one actually does — note that only the first three
rows reach untracked files at all:

| Command | What it removes from the working tree | Recoverable? |
| --- | --- | --- |
| `git clean -fd` / `-fdx` | **Untracked files, including user files.** | **No.** |
| `git stash -u` / `-a` | **Untracked files** (plain `git stash` does not). | Only until the stash is dropped — and a stash is easy to lose track of. |
| `rm -rf <dir>` | **Everything in the directory**, tracked and untracked alike, with no git involvement at all. | Tracked paths yes, untracked **no**. |
| `git reset --hard` | Uncommitted changes to **tracked** files. | No, unless committed or stashed first. |
| `git checkout .` / `git restore .` | Uncommitted changes to **tracked** files. | No, same. |
| `git checkout -f` / `git switch --force` | Uncommitted changes to **tracked** files, discarded without a prompt. | No. |

**Correcting a reason that was wrong here.** An earlier version of this section said all
of these are "the commands by which untracked work is destroyed". That is false for most
of them: `git reset --hard`, `git checkout .`, and `git restore .` touch tracked paths
only, and plain `git stash` without `-u`/`-a` leaves untracked files alone. They destroy
uncommitted **tracked** work — a real hazard, but a different one from the hazard this
section is named for. The ban on all of them stands; the reason differs by row, and the
table says which. This matters because of the same argument §6 makes about capability
claims: **a stated reason an agent can falsify invites it to discount the rule**, and an
agent that checks and finds `git reset --hard` cannot touch `diag.py` has been handed a
reason to doubt the rest of the section.

**Ordinary branch operations are not on this list.** Plain `git checkout <branch>` and
`git switch <branch>` refuse to proceed when switching would overwrite local
modifications, and carry compatible changes across — so they destroy nothing on their own
and are not banned. Only the `-f`/`--force` forms are, which is why the table names those
specifically. Creating and switching to a throwaway branch is a normal, encouraged move —
[§3's revert-and-observe remedy](#when-a-non-discriminating-test-is-found-after-the-fix-landed)
depends on it.

**[ASK] Do not delete an untracked file you did not create in this task.** Only the user
can authorize deleting their own file, and only for that specific file. This is [ASK]
rather than [NEVER] because the user may legitimately ask you to remove something of
theirs — but no agent, Coordinator included, can grant it, and a bulk command is never
the way to carry it out even once granted.

Also do not run formatters, codemods, or bulk rewrites that would sweep untracked files
up.

The reason for the asymmetry with tracked files is recoverability: an untracked file has
no git history, so overwriting or deleting it is unrecoverable, and no review catches it
after the fact.

This connects directly to the release gate: a tree containing untracked files **is**
the normal state here, and the temptation to "clean" it before a release run is exactly
where this rule gets violated. See [§6's definition of clean tree](#what-clean-tree-means-here),
which is written so that no release step ever requires removing an untracked file.

Documenting an untracked file is allowed and encouraged — writing down that a file
exists and must not be touched is not touching it, and putting that note in a tracked
document is fine.

The specific user-owned files in this repository are listed in
[CLAUDE.md](CLAUDE.md#user-owned-files).

---

## 5. Evidence and refutation standard

This section governs **investigation and verification records**: findings, bug reports,
hypotheses, verification notes, and the change description. It does not govern
user-facing release notes — see §6 for how those two connect.

### Every quantitative claim ships with its provenance

A number without its provenance is not a finding. Any quantitative claim — a rate, a
count, a percentage, a "most", a "usually" — must be accompanied by **all** of:

- the **grouping key** (what one unit of the count is: a row? a request? a file? a
  session?);
- **both window bounds**, start and end, as absolute timestamps — never "the last 7
  days", which means something different every time it is read;
- the **file set** actually read, enumerated or precisely specified;
- the raw **numerator and denominator**, not just their quotient;
- a **timestamp** for when the measurement was taken.

**A bare percentage is rejected.** "83% of records are duplicates" is not a finding;
"4,981 of 6,000 assistant rows (grouping key: message id paired with request id), across
the 12 files listed below, between 2026-08-01T00:00Z and 2026-08-08T00:00Z, measured
2026-08-12T14:10Z" is. The reason is not bureaucratic: percentages with unstated
denominators are the single most common way a real effect and a sampling artifact become
indistinguishable.

### Hypotheses are presumed wrong until reproduced by a non-author

The author of a hypothesis is the worst-placed agent to confirm it. A hypothesis moves
from "proposed" to "established" only when a **different** agent reproduces it from the
stated procedure and gets the same numbers. Until then it is written down as a
hypothesis and labelled as one, and downstream work does not build on it as fact.

### A confirming result from a narrow sample is not confirmation

Finding the predicted pattern in one file, one session, or one day tells you the pattern
*can* occur. It does not tell you how often, and it cannot distinguish "this is how the
system behaves" from "this is how the system behaved once". Narrow samples are useful
for refutation — a single counterexample does kill a universal claim — and nearly
worthless for confirmation. State the sample size and scope alongside any confirming
result, and treat the two directions asymmetrically.

### Observations and invariants are different claims — never let one become the other

This is where sample-derived claims cause lasting damage: not in the finding, which is
usually careful, but in what gets written down afterwards, where the hedges fall off and
an observation hardens into a rule the code then relies on.

Keep three things in separate sentences, and never merge them:

1. **What the data did** — an *observation*. It carries its scope: what was examined,
   when, and how it was gathered. It is true of that sample and claims nothing beyond it.
   If it was not measured to the standard above, say so in the same breath; an
   unquantified observation is still worth recording, but only if labelled as one.
2. **What the data can do** — an *invariant*. This constrains the code and needs a
   source: a format specification, a guarantee from the producer, or an exhaustive
   argument. **An observation is never a source for an invariant.**
3. **What someone must therefore do** — the *operational consequence*. State it
   separately from both, so that qualifying an observation later does not silently
   weaken the instruction.

**Slot 1 is for sample-derived claims only.** A fact you read directly out of source —
what a function calls, what a flag does, which branch runs — is not an "observation" in
this sense and must not be labelled as one. It is deterministic and checkable by anyone,
and dressing it in the vocabulary of uncertain evidence *understates* it: a reader who
sees "observed" reasonably discounts the claim, when in fact it can be confirmed exactly.
Cite the source instead. Reserve the hedging vocabulary for claims that actually depend
on which data you happened to look at.

**A universal negative does not follow from observation** — "only", "never", "always",
"in every case". A sample can *refute* a universal claim with one counterexample, and
cannot *establish* one at any size. This carries no permission tag, and deliberately so
(§0): it is not that you are forbidden to write such a sentence, it is that the sentence
does not follow from the evidence. No authorization makes an invalid inference valid.

The failure this prevents is specific and worth naming, because it looks like diligence:
an observation written as a rule invites a later optimization that special-cases on it.
That optimization will pass every existing test — the tests were built from the same
sample — and will fail the first time reality produces the case the sample happened to
miss. By then the rule reads as documented behaviour, and the person removing the
special case has to argue against the document.

### Never measure a corpus your own session is writing

If your work generates data into the corpus you are measuring, your measurement is
contaminated: you will find whatever your own activity put there, and the effect size
will track how busy you were rather than anything about the system. If this is
unavoidable, **say so explicitly in the finding** — state that the corpus was live and
being written by the measuring session, and treat every number as an upper bound of
unknown tightness. An uncontaminated measurement of a frozen snapshot is always
preferable; take a copy first when you can.

---

## 6. Release gate

**A release requires everything a merge requires, plus the release-specific conditions
below.** [§8's merge checklist](#8-merge-checklist) is the canonical list of the shared
conditions — separation, red-before-green, Reviewer sign-off, a green suite, untouched
untracked files, §5-conforming claims. It is stated once, there, and deliberately not
repeated here: two copies of the same list drift, and the copy a reader happens to open
becomes the one they trust.

### The release has two phases, and this gate sits between them

A gate demanded *before* the release commit exists could never be satisfied. §8's
checklist requires commit trailers, and there are no trailers until there is a commit;
the clean-tree condition below requires an unmodified tracked tree, and the version bump
and the notes are modifications to tracked files. Requiring both before the commit asks
the release to be judged before the thing being judged has been made. So the release
divides into two phases, and the gate is evaluated at the one point where both conditions
can hold.

**The release commit is the phase boundary.**

- **Preparation.** The version bump, the release notes, the named-path staging, and the
  release commit itself. These run *before* the gate is evaluated, because they are what
  produces the thing the gate judges. The release commit carries the `Developer:` and
  `Verifier:` trailers, so the merge checklist becomes evaluable the moment that commit
  exists — and not one step earlier.
- **Execution gate.** Evaluated *after* the release commit, when the tracked tree is
  clean: the Verifier re-runs the full suite from that clean tree and records the command
  and its output, the release notes are checked, the Coordinator's sign-off is recorded,
  and an eligible release operator is named with their eligibility stated.
- **Only once the execution gate is GREEN** may the release's artifact build, signing,
  notarization, local tag, push, and publication run. No preparation step waits on the
  gate; no step after it begins before the gate is GREEN.

CLAUDE.md's release procedure states that boundary in the same words, and maps it onto
this repository's numbered steps.

Preparation is not ungated — it is gated by §8, as any commit is, and by the
authorizations in [Release steps are separately authorized](#release-steps-are-separately-authorized).
What it is not gated by is the execution gate, which cannot yet be evaluated.

So the **execution gate** is:

1. **Every condition in [§8](#8-merge-checklist) holding for every change in the release,
   the release commit included** — not merely at the time each was merged, but confirmed
   for the release as a whole. That commit's own trailers are what make item 1 evaluable
   at all, which is why this gate is evaluated after it rather than before.
2. **The suite re-run from a clean tree** (defined below) by the Verifier, with the
   command and its output recorded — not summarized. §8 requires a green suite; this
   adds the clean-tree condition and the re-run. The release commit is what leaves the
   tracked tree clean, so this re-run happens after it.
3. **Release notes written and checked** against the exemption rules below.
4. **The Coordinator's sign-off, recorded** — not implied by silence.
5. **The release operator named, with their eligibility stated**, in a record that
   outlives the session — the release notes, the release commit message, or the release
   itself. Name who executed the credential-bearing steps and state which roles they did
   *not* hold on this release.

   This exists for the same reason as §7's trailers. Those make §2's separation checkable
   from `git log` months later by someone who was not present; without item 5 the
   corresponding release question — *who signed this, and had they already built,
   reviewed, or certified it?* — is unanswerable after the fact, and an eligibility rule
   nobody can audit is an eligibility rule that decays into an honour system. Recording it
   costs one line and is the only thing that makes the operator restriction verifiable
   rather than merely stated.

Items 2 to 5 are what a release adds. If you are reconciling this section against §8 and
they appear to disagree, §8 governs the shared conditions and this section governs only
items 2 to 5.

### What "clean tree" means here

**No uncommitted modifications to tracked files. That is all it means**, and it is
deliberately the whole definition.

**Untracked files are expected to be present and are not an obstacle to a clean tree.**
Some are permanently untracked by design (§4), so a tree containing them is the normal
state, and `git status` showing `??` entries is not a failure of this gate. Verify with
`git status --porcelain` and look only at the modification (`M`), addition (`A`), and
deletion (`D`) columns for tracked paths.

**Build output is not part of this definition.** An earlier version of this section also
required "no stray build output", which was a defect on three counts: build output is
untracked, so the stated check cannot see it; there was no permitted way to satisfy the
clause, since removing untracked files is forbidden by §4 and by this section; and an
agent trying to comply would reach for a directory-wide delete whose blast radius
includes user files. **Build output is managed by the project's build and release
tooling, which cleans its own outputs. Do not remove it by hand.** If you believe stale
build output would corrupt a release artifact, say so and let the build tooling or the
maintainer handle it — that is a build-correctness question, not a working-tree-hygiene
one.

**[NEVER] A clean tree is never achieved by removing anything.** Not untracked files, not
build directories. The commands that would do it are banned by §4's hard floor, and this
definition is written so that no release step ever needs them. If tracked files are
dirty, commit them or ask. If untracked files are present — user files, build output,
anything — proceed; they do not block this gate.

Note the interaction with the repository layout: whether a given build directory is
gitignored, partly gitignored, or contains tracked and user-owned files alongside
generated ones **varies per repository and is not guessable**. A directory that looks
purely generated may hold a tracked asset and a user's working file. The repository's
own documentation states which is which; consult it before assuming any path is
disposable.

### Release notes are exempt from §5's format

User-facing release notes are written for users, in the user's language, and demanding
grouping keys and absolute window bounds in them would make them unreadable while
improving nothing. So:

- **Release notes are exempt from the §5 provenance format.**
- **The exemption is from the format, not from the truth requirement.** Any quantitative
  claim that appears in release notes must be backed by a §5-conforming record in the
  change description or verification record, which is where a reader who wants the
  numbers is pointed.
- **Do not put unquantified magnitude or frequency claims in release notes.** Two
  distinct kinds of smuggled number, and both need the same treatment:
  - *Magnitude* — "much worse in case X", "significantly undercounted", "a huge
    difference". Claims about **how much**.
  - *Frequency* — "usually", "rarely affects anyone", "in most sessions", "this almost
    never happens". Claims about **how often**, and the easier of the two to write
    without noticing, because they read as hedges rather than as measurements.

  Either state the mechanism instead ("partial snapshots appear in these files, so the
  old rule picked a mid-response value there") or give the real number from the backing
  record. Describing *what changed and why* needs no quantification; asserting *how much*
  or *how often* does. A frequency claim is especially treacherous in a changelog,
  because a user who is in the minority reads "rarely" as a statement that their problem
  is not real.

### Release steps are separately authorized

The version bump, the release commit, the tag, the push, the signing/notarization, and
the publication are **separate steps, each gated on its own**. An approval to implement
is never an approval to release.

This section is about their *separateness*. It does not tag them — they do not share a
tag, and an earlier version of this sentence carried a blanket **[ASK]** that read as
permission to sign. Each step's tag comes from
[the two classes below](#outward-facing-steps-two-classes-not-one):

| Step | Tag | Who authorizes |
| --- | --- | --- |
| Version bump, release commit, local tag | ordinary authorized work | the user **or** the Coordinator |
| Push, publish | **[ASK]** | the **user** only — not a Coordinator, not an agent relaying them |
| Sign, notarize | **[ASK-OP]** | the **user** only, plus all gates recorded, plus an eligible operator |

**Never infer a step's tag from the list above the table.** Note that Coordinator
authorization survives only for the first row: once a step is outward-facing, the
principal is the only party who can license it.

**This table groups steps by who authorizes them, not by phase.** The version bump and
the release commit are preparation; the local tag, sharing their row here because the
same parties authorize it, runs after the execution gate along with every step below it.

Concretely: an agent implementing a fix does not touch the version constant, does not
create a tag, and does not push. Those happen only when an authorized party asks
for that specific step, one step at a time. If you have finished an implementation and
believe it is ready to ship, say so and stop.

**This does not make ordinary commits require authorization.** An *implementation
commit* — recording work on a branch as part of the task you were given — is normal
work, authorized by the task itself, and gated by §8, not by this section. What requires
its own authorization is the *release commit*: the commit that bumps the version
constant and finalizes the release notes, together with the tag and push that follow it.
If a commit changes the version constant, it is a release commit. If it does not, it is
an implementation commit.

### Blanket authorization of the release sequence

A human may authorize the whole release sequence in advance, in a single instruction,
rather than being asked between every step. That is legitimate and often sensible. It is
also the single most dangerous instruction in this document, so it carries four guards,
all of which must hold.

1. **It changes only who must be asked between steps. It changes nothing about the
   gate.** Every execution-gate condition must be true *and recorded* before the first
   step after the gate runs — preparation still comes first, since it is what makes the
   gate evaluable at all. The steps still run in their stated order, and each outcome is
   recorded as it completes. If a gate condition is not yet satisfiable, blanket authorization licenses
   proceeding **once it passes** — never now, and never "it will pass". An authorization
   to release is not a finding that the release is ready.
2. **It must come from a human, in the user's own words, quoted verbatim in the change
   description.** Paraphrase does not preserve scope, and scope is the entire content of
   this authorization.
3. **[NEVER] treat an agent's report of authorization as authorization.** "The
   Coordinator says the user approved the release" is a claim about a conversation you
   cannot see, and it is exactly the shape a laundered approval takes. If you were not
   given the human's words, you do not have the authorization — go get it.
4. **[NEVER] accept blanket authorization from a Coordinator.** A Coordinator's authority
   over release steps is per-step and stays per-step; it cannot be aggregated into
   advance approval of a sequence. Only the human whose identity and credentials the
   release is published under can grant this.

**Blanket authorization removes the need to ask *between* steps. It changes nothing
else.** In particular, two constraints below survive it intact:

- **The role restriction.** An agent ineligible to operate the release stays ineligible.
  **Blanket authorization does not make an ineligible agent eligible** — it speaks to
  *whether* the steps may happen, never to *who* may perform them, and those are separate
  questions decided by separate parties.
- **The shortcut ban.** `ship`-style combined commands stay forbidden for everyone,
  because what was authorized was the sequence with its checkpoints, not a single call
  that erases them.

Neither is a gap in the authorization that a broader grant could fill. They are limits on
what an authorization is capable of licensing at all.

### Outward-facing steps: two classes, not one

An earlier version of this section put every outward-facing step under one blanket
[NEVER]. That was a tagging error. §0 defines [NEVER] as *no path exists — asking is not
the remedy*, and for some of these actions asking the owner plainly **is** the remedy.
Lumping them together makes the strongest prohibition look arbitrary, which is how strong
prohibitions get discounted. They divide by **what the action commits, and who can
release it**:

**[ASK] Performing an action within a principal's own account** — pushing a tag,
publishing a release, posting to a channel they own. Outward-facing and effectively
irrevocable: once fetched, it cannot be recalled from whoever received it. But it is an
**event**: it happens, it is done, and what remains is its consequences, not a continuing
claim. It is the owner's own property, and **the owner can authorize it**, so the correct
tag is [ASK] with them named as authorizer, per-instance. Authorization is required before
each such act; it is never inferred from the last one.

**[ASK-OP] Creating an artifact that goes on asserting something in the
principal's name** — code signing under their certificate, submitting to a vendor's review
system under their developer account. Here the output **carries their identity with it**
and keeps testifying, to everyone who inspects it, that they vouch for these contents. The
act does not end when the command returns.

This class was previously [NEVER], which was wrong by §0's own test: the principal *can*
authorize the use of their own certificate, so asking is a coherent remedy and no
prohibition is absolute here. What the persistence property justifies is not a bar but a
**narrower gate** — three constraints on top of ordinary [ASK], all of which must hold:

1. **Explicit authorization from the principal**, per-instance, for this artifact.
2. **Every quality gate passed and recorded first** (§6). Authorization is not a finding
   that the gates passed.
3. **[NEVER] executed by anyone except a dedicated release operator.** An agent holding
   **any other role on the release — Developer, Verifier, Reviewer, or Coordinator —
   must not** perform these actions, regardless of authorization. This is the one absolute
   in this class, and it is a separation-of-duties rule, not a capability claim: the party
   who built, blessed, or *certified as ready* an artifact must not also be the party who
   signs the principal's name to it. The Coordinator is included because §6 makes it the
   party whose sign-off says the release is ready.

The operator **records the outcome of each step as it completes and stops on the first
failure**. That is what makes the sequence reviewable, and it is why the shortcut
commands remain forbidden (see below).

**The discriminator is persistence, not credentials.** Both classes use the principal's
credentials — a push authenticates as them too, so "uses their credential" cannot be the
line. The difference is what survives: an authorized push leaves a fact about something
they permitted, while a signature leaves a standing assertion in their voice that outlives
the release and cannot be withdrawn from artifacts already distributed. That is why this
class carries the extra constraints and the first class does not.

Nor is the discriminator severity. Pushing a tag may reach more people faster than signing
does. It is *who is speaking, and for how long*: the first is an act the owner authorized,
the second is an act performed **as** the owner, indefinitely — which is why the second
adds a role restriction rather than a prohibition.

For both classes, the reason is never that an agent lacks the ability. Credentials are
often present on the machine, and an agent may well find that it *can*. **"Can" is not
the question, and a document that says "cannot" invites an agent that discovers otherwise
to conclude the prohibition was mistaken too.**

**If any of the three conditions is unmet** — no per-instance authorization, a gate not
yet passed and recorded, or you are not an eligible operator — stop and hand the work to
the principal, with the artifact ready and what remains stated plainly. Being unable to
proceed is a normal outcome here, and saying so is the correct result, not a failure to
complete the task.

### Sequencing is part of the authorization

**[NEVER] run a command that collapses several separately-gated steps into one
invocation** — a single "do the whole release" entry point that bumps, builds, signs,
publishes, and pushes without pausing.

This holds even when every individual step has been authorized, and it is not redundant
with the per-step rules. An authorization granted step-by-step is conditioned on the
checkpoints *between* the steps: the chance to observe that a build failed before it is
signed, that the wrong version was tagged before it is pushed. A combined command removes
those checkpoints while appearing to perform the same work, so it converts a sequence of
reviewable decisions into one irreversible act. What was authorized was the sequence,
not the shortcut through it.

Run the steps individually, in order, checking each outcome before starting the next.

The repository's actual release commands and version constant are in
[CLAUDE.md](CLAUDE.md#release-procedure).

---

## 7. Commit trailers

Every commit carries both trailers:

```
Developer: <who wrote the change>
Verifier: <who verified it — see below for what that means per commit type>
```

**[NEVER] Identical values block the merge.** If `Developer:` and `Verifier:` name the
same party, the separation in §2 did not hold, and the commit is not mergeable as-is.
The remedy is to have an agent with clean hands write and run the gating tests, or to
declare the exception under §2 Condition C and name the re-deriver.

What `Verifier:` means depends on what the commit changes:

| Commit type | `Developer:` | `Verifier:` |
| --- | --- | --- |
| Changes production files | Author of the production change | Agent who wrote and ran the gating tests (§2 Condition B) |
| Declared §2 exception | Author | The independent re-deriver (§2 Condition C) |
| **Documentation only** | Author of the docs | Agent who checked the documented claims against the source and found them accurate |
| Test-only | Author of the tests | Agent who confirmed the tests fail against the unfixed behaviour (§3) |

A documentation-only commit still needs both trailers and still cannot name the same
party twice. Documentation makes factual claims about the system, and an author checking
their own claims reproduces exactly the failure §2 exists to prevent — a wrong mental
model producing a document and a check that agree with each other and disagree with the
code.

The trailers exist so that §2 is auditable from `git log` alone, months later, by
someone who was not present. **Filling them in accurately matters more than filling them
in at all** — a trailer naming the wrong party is worse than a missing one, because it
converts an open question into a false answer.

Adding trailers is part of making a commit. Do not make a commit purely to demonstrate
the format.

### A declared §2 exception must be recorded in the commit itself

An exception under §2 Condition C is written in the change description — but a change
description may live in a pull request, a task tracker, or a chat log, none of which
`git log` can see. That reintroduces exactly the invisibility the trailers exist to
prevent: a reader six months later sees `Developer:` and `Verifier:` naming different
parties and concludes separation held, with no way to learn that it did not.

So when an exception is declared, **the commit message body must record it**: that an
exception was taken, who re-derived the numbers, and what they derived. The `Verifier:`
trailer then names the re-deriver, per the table above. If the exception is only in an
external description, it is not recorded.

### A solo agent cannot produce a mergeable commit

**Say this plainly, because the natural failure mode is to paper over it.** If you are
the only agent working on a change, you cannot satisfy §2: you wrote the production
change, so you cannot be the Verifier, and there is no one else to be. Both trailers
would have to name you, which §7 blocks.

The remedy is **never** to invent a plausible name for the `Verifier:` trailer. A
fabricated trailer is the precise case this section calls worse than a missing one — it
converts "was this verified?" from an open question into a false answer, and it is
undetectable later because it looks exactly like a correct trailer. The same applies to
naming an agent who did not actually re-derive anything, or naming the human who assigned
the work as though they had verified it.

What to do instead, in order of preference: get a second agent to verify; or declare a §2
Condition C exception and have an uninvolved agent re-derive the numbers; or, if neither
is available, **stop and say so** — hand back a change that is complete but explicitly
not mergeable, stating which condition is unmet. An unmergeable change honestly labelled
is a normal outcome. A mergeable-looking change with a fabricated trailer is a
falsification of the audit trail.

---

## 8. Merge checklist

§6 gates *releases*. This section gates *merges*, which happen far more often. The
Coordinator makes the merge decision (§1) against this list.

**This list is canonical.** §6 references it rather than restating it, so these seven
conditions have exactly one home. If you are adding or amending a condition that applies
to both merging and releasing, amend it here and nowhere else.

A change is mergeable when:

1. **Both trailers are present and different** (§7). This is a hard block, not a
   preference.
2. **Developer–Verifier separation held**, or an exception is declared with a named
   re-deriver and recorded re-derived numbers (§2).
3. **Red-before-green is documented** for every behavioural change — the recorded
   failure output, not an assertion that it failed — or the gap is explicitly declared
   unrecoverable (§3).
4. **A Reviewer has signed off**, and is neither Developer nor Verifier (§1).
5. **The full suite is green**, run by the Verifier.
6. **No untracked file outside the declared deliverable list was touched** (§4), and no
   destructive git command was run against the working tree.
7. **Quantitative claims in the change description meet §5.**

**Red-before-green and Reviewer sign-off gate the merge, not just the release.** They
appear again in §6 because a release must confirm they held for everything it contains,
not because they may be deferred to release time. Deferring them means merging code
whose tests have never been shown to test anything, and discovering it at release time
when reverting is most expensive.

What a release adds beyond this list is release-specific, and it falls in two places.
Preparation contributes the version bump and the release notes, before the release
commit. §6's execution gate then adds the suite re-run from a clean tree, the checked
notes, the Coordinator's recorded sign-off on shipping, and the recorded identity and
eligibility of the release operator. A merge does not require those.

**A change that cannot satisfy item 1 or 2 is not mergeable, and that is an acceptable
outcome.** See [§7's note on solo agents](#a-solo-agent-cannot-produce-a-mergeable-commit):
hand back an honestly-labelled unmergeable change rather than manufacturing the missing
party.
