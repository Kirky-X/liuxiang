# Issue Lifecycle Protocol — Diagnose → Act Separation and Stable Issue IDs

## Purpose

Two defects recur in multi-agent academic workflows, and both are structural rather than stylistic.

**Mixed diagnose-and-act.** When the same pass both criticises a sentence and rewrites it, two things collapse at once. The reviewer loses the ability to report faithfully (a critic who has already committed to a fix rationalises the defect away), and the author loses the ability to see what changed — the edit and its justification arrive fused, so neither can be audited. The paper reads as "revised" with no record of what was wrong or why the new wording is better. In a multi-agent setting this is worse, not better: with five independent reviewers and one writing pass, an unseparated workflow produces a diff nobody can attribute.

**Anonymous issues.** "The discussion needs more depth" cannot be re-reviewed. In round 2 there is no way to ask whether the same concern was resolved, partially resolved, or quietly dropped. Issues that arrive without an identity survive exactly one round.

This protocol fixes both. Diagnosis produces issues; revision consumes them. Every issue carries an ID that is minted once and never reused, and the ID follows the issue across all five downstream artifacts.

> **Provenance.** The diagnose→act split and the notion of a persisted, addressable finding set are adapted from the `academic-writing-agents` project (MIT, andrehuang). The ID grammar, merge rules, and artifact chain below are written for this suite's existing Revision Roadmap and Commitment Ledger (Schema 11) rather than carried over.

---

## 1. Two stages, hard boundary

```
STAGE D — DIAGNOSE (read-only)                    STAGE A — ACT (write)
──────────────────────────────────────────         ──────────────────────────────────
reviewer panel, Phase 1                           paper revision / draft writer
  reads manuscript, writes nothing                  reads issue set, edits manuscript
  emits issues with IDs                             emits disposition per issue ID
                                                   mints no new issue IDs
        │                                                    │
        └──────────── issue set (IDs frozen) ─────────────────┘
```

### Stage D obligations

1. **Read-only.** The manuscript is not edited, annotated, or rewritten. `reference/reviewer.md` Checkpoint Rule #6 already binds the panel; this protocol adds the converse obligation below.
2. **Quote the pre-revision text.** Every issue quotes the passage it objects to *as it currently stands*. A reviewer who cannot quote it cannot report it.
3. **One issue per defect.** A defect is the smallest unit an author could act on independently. Do not bundle three unrelated defects into one issue for economy — they will be tracked as one and resolved as zero.
4. **Suggest, do not supply.** An issue may state the direction of a fix. It must not carry replacement text presented as the fix; the writing voice belongs to Stage A.
5. **Census, not sampling.** Stage D does not decide it has seen enough. It walks the criteria it owns (`craft_criteria_checklist.md` § Coverage Attestation) and reports what it walked.

### Stage A obligations

1. **Consume, do not originate.** Stage A acts on the issue set. A defect noticed mid-revision is recorded as `new-observation` against the issue being worked on, or raised to the user — it does not become a silently-fixed untracked edit.
2. **No new IDs.** Stage A may not mint an issue ID. An ID space that grows during the act phase cannot be audited against the diagnosis that justified it.
3. **Disposition per issue.** Every ID in the set receives exactly one disposition (§3). An ID with no disposition is an open ID, and open IDs are reported, never dropped.
4. **Scope discipline.** A fix addresses its issue. Adjacent improvements found during the edit are raised, not applied (`paper.md` Anti-Pattern #7).
5. **Preserve voice.** Stage A improves the existing expression. It does not replace the author's argument with a stronger one.

### The boundary rule

⚠️ **IRON RULE — diagnose and act never run in the same pass.** A pass that both reports a defect and applies its fix has destroyed the evidence for both. If a reviewer agent finds itself holding an edit tool on the manuscript it is reviewing, it is in the wrong stage: emit the issue and stop. If the revision agent finds itself inventing a criticism no reviewer made, it is in the wrong stage: raise it and stop.

> **Exception — cosmetic typesetting.** Reference-list style normalisation, hyphenation, and pure typo repair may be applied during Stage D *if and only if* the reviewer records them as issues first and defers the edit. They are not exempt from the issue set; they are exempt from waiting for Stage A. This exception exists because these edits carry no judgment, and making reviewers hand them off adds cost without adding audit value. Anything involving a wording choice is out of scope for the exception.

---

## 2. Stable Issue IDs

### Grammar

```
<ISSUE_ID> := <SOURCE>-<N>

<SOURCE> := EIC | R1 | R2 | R3 | DA      # panelist that raised it
<N>      := integer, 1-99                # per-source, per-round, starts at 1
```

Examples: `EIC-1`, `R2-3`, `DA-7`.

The unpadded form is this skill's existing convention — `revision_tracking_template.md` and the commitment-ledger example already key concerns as `R1-1` / `R2-1`, and the Schema 11 `concern_id` field is populated with it. Adopting a different padding would invalidate existing artifacts for no gain, so the convention is adopted as-is.

### Minting rules

1. **Minted in Stage D, by the raising panelist, once.** A panelist numbers its own issues `1, 2, …` in the order it reports them.
2. **Never renumbered.** If the synthesizer reorders, merges, or reprioritises issues, the IDs travel with them unchanged.
3. **Never recycled.** A closed ID is retired permanently. A later round that raises a different defect gets a new number — it does not reuse `R2-3`.
4. **Round-scoped, not session-scoped.** Round 2 reuses round 1's IDs because it is verifying *those* issues. A defect found fresh in round 2 gets a round-2 number under the same source. The round is carried by the round record, not by the ID, so that `R2-3` means the same issue across both rounds.
5. **Non-panel sources use their own prefixes.** `paper` 模块's in-pair `peer_reviewer_agent` mints `IP-1`…; `revision_coach_agent` parsing external (non-panel) reviewer comments mints `EX-1`…. The panel prefixes are never used for a source outside the panel.

### Why reviewer-scoped rather than a flat sequence

A flat `1, 2, 3` across the panel breaks under merge: when two reviewers raise the same defect, a flat ID forces a choice between the two numbers and loses one. Reviewer-scoped IDs make the collision explicit (`R1-4` + `R2-7` converge on `R1-4`) and keep every reviewer's report internally addressable, which is what lets the synthesizer cross-check consensus.

### Deterministic validation

ID conformance is a string property, so it is checked as a string property — not left to model judgment:

```python
ISSUE_ID_RE = re.compile(r"^(EIC|R1|R2|R3|DA|IP|EX)-([1-9]|[1-9]\d)$")
```

Any ID in a report, roadmap, or tracking table that fails this pattern is malformed. Validation is a deterministic check; do not ask a reviewer agent to "judge whether the IDs look right".

---

## 3. Dispositions

Every issue ID receives exactly one disposition when the revision round closes. Values align with the existing `revision_tracking_template.md` status set, extended with the three states this protocol needs (`PARTIAL`, `REJECTED_AS_INVALID`, `OPEN`).

| Disposition | Meaning | Author obligation |
|-------------|---------|-------------------|
| `RESOLVED` | Change made | Location + description of the change |
| `PARTIAL` | Partially addressed, remainder declined or infeasible | What was done, what was not, and why |
| `DELIBERATE_LIMITATION` | A design boundary, not a defect | Justification + pointer to the Limitations section |
| `UNRESOLVABLE` | Requires a different research design | Constraint + future-research placement |
| `REVIEWER_DISAGREE` | Reviewer's premise is wrong | Evidence-based rebuttal |
| `REJECTED_AS_INVALID` | The issue itself does not hold | Why the finding is wrong — **new in this protocol** |
| `OPEN` | Not yet acted on | None; must be cleared or explicitly carried to the next round |

`REJECTED_AS_INVALID` is separated from `REVIEWER_DISAGREE` on purpose. The second disputes the *suggested remedy* while accepting the finding; the first disputes the *finding*. Collapsing them makes a panel that misread the paper look merely obstinate, and hides a real reviewer failure at re-review.

⚠️ **`OPEN` is a reported state, not a silent one.** A revision round that ends with `OPEN` IDs must surface them in the round summary with their count and IDs. An issue that vanishes between rounds is indistinguishable from an issue that was fixed.

---

## 4. The ID chain across artifacts

One issue, five hops, one identity. Each hop is an existing artifact — this protocol adds an ID column or an `origin` reference, it does not introduce new documents.

```
  Stage D                 Stage D              Stage D/A            Stage A            Stage A'
 ┌──────────────┐       ┌──────────────┐     ┌──────────────┐     ┌─────────────┐    ┌────────────┐
 │ Peer Review  │       │ Devil's      │     │ Editorial    │     │ Revision    │    │ Re-review  │
 │ Report       │       │ Advocate     │     │ Decision     │     │ Tracking    │    │ Report     │
 │              │       │ Report       │     │ + Roadmap    │     │ Table       │    │            │
 │ W → R2-3     │──────▶│ DA-1         │─┐   │ RM-7         │────▶│ concern_id: │───▶│ R2-3       │
 │ + ARC-02     │       │ + ARC-03     │ │   │ origin:      │     │ R2-3        │    │ DA-1       │
 │              │       │              │ └──▶│ R2-3, DA-1   │     │ disposition │    │ (reused)   │
 └──────────────┘       └──────────────┘     └──────────────┘     └─────────────┘    └────────────┘
        ▲                                                                      │
        └──────────── criterion ID (ARC-02, PRO-05, …) ────────────────────────┘
```

### Hop 1 — Peer Review Report (`../templates/peer_review_report_template.md`)

Weaknesses and Minor Issues carry `ISSUE_ID` and `CRITERION` fields. The existing `W1…W5` / `S1…S5` labels become presentation numbering within a report, not the durable handle.

### Hop 2 — Devil's Advocate Report

The Issue List rows carry the same `ISSUE_ID` / `CRITERION` fields under the `DA-` prefix. DA issues are first-class, not a side channel — a DA `CRITICAL` finding that never receives an ID cannot be traced into the Roadmap.

### Hop 3 — Editorial Decision + Revision Roadmap (`../templates/editorial_decision_template.md`)

Two changes:

- **Consensus items** list their member issue IDs: `[CONSENSUS-2] (R1-4, R2-7, DA-2) — …`
- **Roadmap rows** get an `RM-<N>` ID and an `origin` column listing the source issue IDs.

⚠️ **Roadmap ID prefix.** The Roadmap previously labelled its rows `R1`, `R2`, `R3` and `S1`, `S2`. Those labels collide with the panel labels `R1`–`R3` used everywhere else in the same document, so "R2" is unreadable without context. Roadmap rows are renumbered `RM-1`, `RM-2`, … and the `origin` column carries the reviewer-scoped issue IDs. Panel labels keep their meaning.

### Hop 4 — Revision Tracking Table (`../templates/revision_tracking_template.md`)

`concern_id` is the anchor field and takes the **origin issue ID** (`R2-3`), not the Roadmap ID. When the Roadmap was the entry point, the row also records `roadmap_id: RM-7`. Commitments extracted under `commitment_extracted` nest inside the concern as today (`commitment_id` inherits the concern's ID — `R2-3.1`, `R2-3.2` — so a partially fulfilled multi-commitment concern remains addressable per commitment).

The `Disposition` column takes the §3 value set. This is where Stage A's obligation to be legible is discharged.

### Hop 5 — Re-review (`../references/re_review_mode_protocol.md`)

Re-review walks the carried-over issue IDs, not the manuscript. For each: read the disposition, navigate to the recorded location, verify independently, and record the outcome. The ID is the join key. New defects found during re-review are minted as fresh round-2 IDs under the reusing panelist's prefix.

### Criterion ID as the outer anchor

Every issue also names the criterion it came from (`CRITERION: PRO-05`). This is what makes coverage measurable across rounds: a round-2 report can show that PRO-05 was re-examined under `EIC-2` even if the round-1 issue was closed. Criterion IDs come from `craft_criteria_checklist.md` and are stable for the life of the skill.

---

## 5. Merge, split, and carry-forward

### Merge (two issues, one defect)

Deterministic, no judgment call:

1. The surviving issue **keeps the ID of the source that comes first in panel order** — `EIC` → `R1` → `R2` → `R3` → `DA` → `IP` → `EX`.
2. The absorbed IDs are recorded as `merged-from:` on the survivor. They are retired, not deleted.
3. The merged issue keeps the **highest** severity and the **union** of the criterion IDs.

Rationale: panel order is fixed before review begins, so "first in panel order" is reproducible by any later reader without access to the synthesizer's reasoning. Choosing on "which reviewer made the better argument" would be a judgment the audit trail cannot reproduce.

### Split (one issue, two defects)

1. The **largest share** keeps the original ID; sibling shares get `<ID>.a`, `<ID>.b`, `<ID>.c`.
2. Each child carries its own criterion ID and disposition.
3. "Largest share" is decided by the raising panelist at the point of split, where it still has the text in view; once split, the sizes are not re-litigated.

### Carry-forward

An `OPEN` or `PARTIAL` issue crosses into the next round **with its ID intact**. It does not re-enter the queue as a new issue. A re-review that cannot find a carried-forward ID in the tracking table reports it as a missing disposition — the single most common way a revision round quietly loses an issue.

---

## 6. Consistency Pass

After Phase 1 and before the Roadmap is built, one pass over the merged issue set — run by `editorial_synthesizer_agent`, with `domain_reviewer_agent` supplying the terminology lock when the full 5-panelist panel ran (under `methodology-focus`, the synthesizer performs all four steps itself):

1. **Terminology lock** (`PRO-06`) — one term per concept across the manuscript. This is where the pass earns its keep: cross-section synonym drift is invisible to any single perspective but obvious once all five reports are in one place.
2. **Duplicate collapse** — issues describing the same defect under different IDs are merged per §5, so the author is not asked to fix one problem three times.
3. **Coverage reconciliation** — compare each reviewer's coverage block from `craft_criteria_checklist.md`. A criterion no panelist checked and no panelist justified becomes a stated limitation of the review, not a silent gap.
4. **Severity normalisation** — the same defect reported as Critical by one panelist and Minor by another is set to the higher severity, with the disagreement noted in the Decision Letter rather than flattened away.

---

## 7. Prohibitions

| # | Prohibition | Why it fails | Correct behaviour |
|---|-------------|--------------|-------------------|
| 1 | Diagnosing and editing in one pass | Destroys the record of what was wrong and what changed | Emit the issue; the revision stage edits |
| 2 | Reporting a fix instead of a defect | The author cannot audit a fix they did not commission | Report the defect and the direction of a fix |
| 3 | Untracked edits during revision | The round summary is not a diff; the author cannot tell what was touched | Every edit traces to an issue ID |
| 4 | Reusing a retired ID | Round-2 verification then checks the wrong issue | Mint a new ID |
| 5 | Renumbering between rounds | The join key breaks; re-review verifies nothing | IDs are frozen at mint time |
| 6 | An issue with no disposition | Indistinguishable from a fixed issue | Close it, or report it `OPEN` |
| 7 | Fixing a defect the reviewer got wrong without recording it | The panel's error is erased and repeats next round | `REJECTED_AS_INVALID` + reason |
| 8 | Bundling unrelated defects into one issue | Tracked as one, resolved as zero | One issue per independently actionable defect |
| 9 | Roadmap row IDs colliding with panel labels | "R2" is ambiguous in the same document | `RM-<N>` + `origin` column |
| 10 | Silently dropping an `OPEN` issue at round end | The issue is gone and no one knows | Report `OPEN` IDs and count in the round summary |
