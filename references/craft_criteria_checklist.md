# Manuscript Craft Criteria Checklist

## Purpose

`review_criteria_framework.md` scores **scientific merit** (seven weighted dimensions). This file covers the orthogonal layer: **manuscript craft** — whether the paper is built, written, and packaged so a reader can actually use it. Craft defects do not lower the merit score on their own, but they are the defects authors most often cannot self-see, and they are what a reviewer is expected to catch.

The checklist exists to replace free-form criticism with **30 enumerable criteria** that a reviewer can walk one by one and report on individually. Every criterion has a stable ID (`ARC-01` … `PRC-03`) and a named owner in the reviewer panel, so coverage is auditable instead of assumed.

**Scope boundary.** This is a coverage checklist, not a style manual. Where a criterion has a deeper rule already in this skill, the row links to it and the deep reference wins. Do not restate those rules here.

> **Provenance.** The six-part taxonomy (structure / prose / math / figures / citations / process) is adapted from the `academic-writing-agents` project (MIT, andrehuang), which distills Michael Black, *Writing a Good Scientific Paper*. The criteria below are rewritten for this suite's agent roster, cross-linked to this skill's own references, and numbered independently. No text is carried over. Terms and categories upstream treated as current were re-derived; only the mechanism is taken.

---

## 1. Criterion Index (6 categories, 30 criteria)

`Owner` is the panelist accountable for that category by default. `field_analyst_agent` owns none — it configures the panel, it does not audit. Any reassignment must be recorded in the Reviewer Configuration Card (Phase 0), not decided silently in Phase 1.

| ID | Criterion | Owner |
| --- | --- | --- |
| **ARC — Argument & Section Architecture** | | |
| ARC-01 | Section lead-in matches delivery | `devils_advocate_reviewer_agent` |
| ARC-02 | Claim precedes apparatus | `eic_agent` |
| ARC-03 | Paragraph-level bridges | `devils_advocate_reviewer_agent` |
| ARC-04 | Paragraph closure resolves | `devils_advocate_reviewer_agent` |
| ARC-05 | One load-bearing thesis | `eic_agent` |
| ARC-06 | Claim-evidence spine intact | `domain_reviewer_agent` |
| ARC-07 | Conclusion stays inside the evidence | `devils_advocate_reviewer_agent` |
| **PRO — Prose & Register** | | |
| PRO-01 | One claim per sentence | `eic_agent` |
| PRO-02 | Calibrated confidence language | `methodology_reviewer_agent` |
| PRO-03 | Non-exhaustive framing | `eic_agent` |
| PRO-04 | Positive phrasing (negation-contrast audit) | `eic_agent` |
| PRO-05 | Compression budget | `eic_agent` |
| PRO-06 | Terminology lock | `domain_reviewer_agent` |
| PRO-07 | Register matches venue and discipline | `eic_agent` |
| **MTH — Math, Notation & Formalism** | | |
| MTH-01 | Symbol defined before use, one meaning per symbol | `methodology_reviewer_agent` |
| MTH-02 | Notational economy | `methodology_reviewer_agent` |
| MTH-03 | Formulation-implementation correspondence | `methodology_reviewer_agent` |
| MTH-04 | Load-bearing construct carries ≥2 explanatory modalities | `methodology_reviewer_agent` |
| **FIG — Figures, Tables & Captions** | | |
| FIG-01 | No orphan floats | `perspective_reviewer_agent` |
| FIG-02 | Caption self-sufficiency | `perspective_reviewer_agent` |
| FIG-03 | Figure-text-caption agreement | `perspective_reviewer_agent` |
| FIG-04 | One message per figure | `perspective_reviewer_agent` |
| FIG-05 | Figures are interpreted, not just cited | `perspective_reviewer_agent` |
| **CIT — Citations & Bibliography** | | |
| CIT-01 | Named work cited at first mention per division | `domain_reviewer_agent` |
| CIT-02 | Dataset / instrument / measure carries a resolvable identifier | `methodology_reviewer_agent` |
| CIT-03 | Reference list integrity | `domain_reviewer_agent` |
| CIT-04 | In-text ↔ reference-list parity | `domain_reviewer_agent` |
| **PRC — Process & Submission Hygiene** | | |
| PRC-01 | Limitations placed to suit document type | `eic_agent` |
| PRC-02 | Mandatory statements present | `editorial_synthesizer_agent` |
| PRC-03 | Per-issue change traceability | `editorial_synthesizer_agent` |

---

## 2. The Criteria

Each criterion gives the check, the typical violation, and where the deep rule lives. Report violations as issues — never as free-text remarks. Issue ID grammar and the diagnose→act split are in [`issue_lifecycle_protocol.md`](issue_lifecycle_protocol.md).

### ARC — Argument & Section Architecture

**ARC-01 — Section lead-in matches delivery**
*Check:* For every section, compare the topics its lead-in enumerates against the topics its subsections actually cover, in the same order.
*Violations:* Lead-in promises three things and delivers two; a subsection exists that the lead-in never announces; announced order differs from actual order.
*Basis:* the paper's own outline is the contract; a reader who follows the lead-in must not be stranded.

**ARC-02 — Claim precedes apparatus**
*Check:* The first one to two sentences of each section state what the section establishes before any equation, procedure, table, or implementation detail appears.
*Violations:* Section opens on a formula or dataset description; motivation is deferred to the section's end.

**ARC-03 — Paragraph-level bridges**
*Check:* Adjacent paragraphs are joined by an explicit logical bridge, not merely by topical adjacency. Section-level transitions do not substitute for paragraph-level ones.
*Violations:* Silent topic shift between paragraphs; a subsection that starts with no reference to what preceded it; a chapter that ends without setting up its successor.

**ARC-04 — Paragraph closure resolves**
*Check:* The last sentence of a paragraph synthesizes, draws an implication, or poses what the next paragraph answers.
*Violations:* Paragraph ends on a bare citation, on "which we detail below", or on a new piece of information that is never resolved.

**ARC-05 — One load-bearing thesis**
*Check:* The paper's central insight is stateable in a single sentence, and every section, result, and figure serves it. Where two claims compete for that role, report focus drift.
*Violations:* Several loosely related contributions with no unifying insight; an abstract that lists techniques rather than states what was learned; a conclusion that enumerates results instead of crystallising the takeaway.
*Note:* the thesis is the understanding the reader walks away with, not the name of the method. "We use method X" is a thesis only if X resolves a specific problem the reader already had.

**ARC-06 — Claim-evidence spine intact**
*Check:* Every substantive claim introduced in the Introduction and Discussion is matched with the result, citation, or analysis that supports it.
*Violations:* Claim asserted in the Introduction and never revisited; Discussion introduces a mechanism that no result in the paper supports.

**ARC-07 — Conclusion stays inside the evidence**
*Check:* The Conclusion asserts nothing stronger than the results section establishes.
*Violations:* Causal language for correlational designs; generalization to a population, setting, or time period the sample cannot support; new evidence appearing for the first time in the Conclusion.

### PRO — Prose & Register

**PRO-01 — One claim per sentence**
*Check:* Sentences that stitch two independent claims with a semicolon, "while", or "unlike" are split.
*Violations:* "Unlike X which …, we do Y and achieve Z"; a subordinate clause carrying a claim equal in weight to its main clause.
*Deep rule:* `writing_quality_check.md`, `academic_writing_style.md`.

**PRO-02 — Calibrated confidence language**
*Check:* Assertive verbs for measured findings; hedged forms for causal interpretation. Neither the finding nor the mechanism is under- or over-claimed.
*Violations:* "because" / "leads to" / "due to" attached to an unestablished mechanism; "may" / "might" attached to an already-measured number; two confidence levels inside one sentence.
*Owner note:* `methodology_reviewer_agent` owns this because mis-calibration is most damaging around reported results.

**PRO-03 — Non-exhaustive framing**
*Check:* Partial lists are framed as illustrative — "such as", "including", "e.g." — never as complete.
*Violations:* "benchmarks for A, B, C" where A/B/C are examples; an enumeration implying a survey that was never conducted.

**PRO-04 — Positive phrasing (negation-contrast audit)**
*Check:* negation-contrast constructions — the "not X but Y" shape, its "not because … but because …" variant, and the correlative "not only … but also" — are recast as direct positive assertions. This doubles as a high-signal marker of machine-generated prose.
*Violations:* a sentence that negates a foil in order to assert its point — recast it as a direct assertion of the point; the correlative pair used to weld together two assertions that each deserve their own sentence.
*Deep rule:* `writing_quality_check.md` § B.

**PRO-05 — Compression budget**
*Check:* Filler frames are removed and relative clauses compressed, without loss of content. A paragraph that spends 100 words on what 60 carries is reported as waste, not as thoroughness.
*Violations:* filler frames that survive a line edit — "it is important to note that" (cut entirely), "in order to" for "to", a nominalised causal link where a conjunction will do; discourse markers padding a paragraph opener ("importantly" / "interestingly" / "notably"); the Conclusion restating the Abstract in new words.
*Deep rule:* `writing_quality_check.md` § A.

**PRO-06 — Terminology lock**
*Check:* One term per concept across the whole manuscript. Flag synonym drift, spelling variants, and competing acronym forms; flag acronyms not expanded before first use.
*Violations:* "feature" in one section and "representation" in the next for one object; "out-of-distribution" / "OOD" / "out of distribution" used interchangeably.
*Cross-link:* this is also the substance of the Consistency Pass in `issue_lifecycle_protocol.md` §5.

**PRO-07 — Register matches venue and discipline**
*Check:* Formality, person (first-person plural vs impersonal passive), and hedging density follow the target venue and discipline convention.
*Violations:* Journal expects impersonal voice and the draft is conversational, or the reverse; colloquial register carrying a formal claim.
*Deep rule:* `academic_writing_style.md` § Register Adjustment by Discipline.

### MTH — Math, Notation & Formalism

For non-quantitative papers the whole category is N/A — record it as such in the coverage block rather than silently omitting it.

**MTH-01 — Symbol defined before use, one meaning per symbol**
*Check:* Every symbol is defined at or before first use; no symbol changes meaning between sections.
*Violations:* Undefined variable in a result; a symbol reused for two quantities; subscript conventions that differ across subsections.

**MTH-02 — Notational economy**
*Check:* Notation that does not buy precision is inlined rather than formalised; a single-use symbol is not minted.
*Violations:* One-use symbols; an intuitive concept formalised into something harder to read than the prose it replaced; several new symbols introduced in one sentence with no intervening explanation.
*Judgment note:* formality is a means, not a virtue. Report unnecessary formalisation as a defect, not as rigour.

**MTH-03 — Formulation-implementation correspondence**
*Check:* Where a paper presents both a formal formulation and an implementation (pseudocode, algorithm block, or a cited code release), names map across the two explicitly; any non-trivial mapping is stated in the text.
*Violations:* Equations using one symbol set and pseudocode another, with no mapping; loss functions defined differently in each; dimension ordering differing between formulation and implementation without comment.

**MTH-04 — Load-bearing construct carries ≥2 explanatory modalities**
*Check:* Each construct central to the contribution is explained through at least two of {prose, formal statement, figure}; the single core construct carries all three, and the three explanations add to each other rather than restate.
*Violations:* Core method given only as equations; a figure that shows the pipeline but not the idea it embodies; text paraphrasing an equation without adding intuition.
*Judgment note:* not every construct needs all three. Over-application is itself a defect — flag it as a criticism of the checklist's owner, not of the paper.

### FIG — Figures, Tables & Captions

Chart-type, axis, and colour rules are not repeated here.

**FIG-01 — No orphan floats**
*Check:* Every figure and table is explicitly referenced in the body text, and its first reference does not lag far behind its appearance.
*Violations:* A float present in the document but never referenced; a table mentioned once with no discussion of what it contains.

**FIG-02 — Caption self-sufficiency**
*Check:* The caption is comprehensible without the body text — it states what is shown, expands abbreviations and symbols used inside the figure, carries units on reported quantities, and gives the takeaway.
*Violations:* Caption reading only "Results on dataset X"; caption depending on terms defined solely in the body; caption walking through the panel arrangement instead of stating the claim the figure makes.
*Rationale:* readers scan figures and captions before committing to the full text, so a caption is the figure's only chance to make its case.

**FIG-03 — Figure-text-caption agreement**
*Check:* Caption, body text, and depicted content describe the same thing in the same terms, and positional claims ("upper left", "second panel") match the actual layout.
*Violations:* Caption naming an element not in the figure; body text pointing to the wrong quadrant; three different names for one element across caption, text, and axis label.

**FIG-04 — One message per figure**
*Check:* A float answers one question. A float carrying two arguments is a candidate for splitting.
*Violations:* A grid whose subpanels each support a different claim; one figure carrying both method overview and headline results.

**FIG-05 — Figures are interpreted, not just cited**
*Check:* Where the text points at a figure, it says what to look for.
*Violations:* Bare "see Figure 3" / "as shown in Figure 3"; a paragraph that leaves the reader to extract the figure's message unaided.
*Relationship to FIG-01:* FIG-01 asks whether the reference exists; FIG-05 asks whether it carries information. Both must pass.
*Deep rule:* `statistical_visualization_standards.md` for chart-specific standards.

### CIT — Citations & Bibliography

**CIT-01 — Named work cited at first mention per division**
*Check:* A named method, model, or theory is cited at first mention *in each major division* that uses it, even when cited earlier in the paper. Readers may enter at any division.
*Violations:* "Transformer" cited in the Introduction and used bare in Chapter 3; a named approach assumed known because it was cited twenty pages back.

**CIT-02 — Dataset / instrument / measure carries a resolvable identifier**
*Check:* Named datasets, instruments, and measurement scales are cited with a resolvable identifier (DOI, accession, or registry ID) at first use.
*Violations:* Dataset named in Methods with no reference; a scale cited by nickname only; a secondary citation used where the primary source is retrievable.
*Deep rule:* `citation_compliance_agent`, `plagiarism_detection_protocol.md`.

**CIT-03 — Reference list integrity**
*Check:* Entries are complete for their type, internally consistent, and current.
*Violations:* Missing fields (pages, DOI, venue); the same author rendered two ways across entries; one venue abbreviation used in one entry and its spelled-out form in another; an arXiv preprint cited where a version of record exists; placeholder entries ("forthcoming", "to appear") never resolved; unresolved citation markers surviving into the compiled output.
*Deep rule:* `citation_format_switcher.md`, `apa7_chinese_citation_guide.md`.

**CIT-04 — In-text ↔ reference-list parity**
*Check:* Every in-text citation resolves to a reference-list entry, and every reference-list entry is cited at least once. Orphans in both directions are defects.
*Violations:* Reference list carrying uncited entries (a self-citation padding signal worth naming explicitly); in-text citation with no matching entry.

### PRC — Process & Submission Hygiene

**PRC-01 — Limitations placed to suit document type**
*Check:* Where and when limitations are disclosed matches the document type.
*Peer-reviewed paper:* disclose after results have established enough confidence for the limitation to be evaluable — brief acknowledgement with a mitigation, a dedicated limitations section, or framing as future work. Premature disclosure in Methods reads as a weakness before the reader has seen the result.
*Thesis / internal document:* disclose alongside the design decision it constrains, so the supervisor or committee sees the tradeoff at the moment it was made rather than reading about it afterwards.
*Violations:* Limitations omitted entirely; listed as a bare inventory with no mitigation offered; defensive tone wrapped around a constraint the author plainly knows about.

**PRC-02 — Mandatory statements present**
*Check:* Data Availability, Ethics Declaration, Author Contributions (CRediT), Conflict of Interest, Funding Acknowledgment, and AI Usage Disclosure are all present and non-empty.
*Cross-link:* `paper.md` § Mandatory Inclusions defines the statements; this criterion is the reviewer-side presence check.
*Note:* a missing statement is an editorial defect, not a scientific one — it routes to Priority 3 unless the venue makes it desk-reject relevant (`venue_disclosure_policies.md`).

**PRC-03 — Per-issue change traceability**
*Check:* In round ≥2, every change made during revision is traceable to an issue ID with a recorded disposition and location.
*Violations:* Edits with no originating issue; an issue reported as addressed with no location; two issues collapsed into one edit with no record of which was resolved.
*Cross-link:* `issue_lifecycle_protocol.md` — this criterion is the reviewer's read-back of the author's tracking table, and its failure is what makes re-review impossible to audit.

---

## 3. Coverage Attestation (required output)

The checklist is only enforceable if reviewers report what they looked at. Every Phase 1 review report ends with a coverage block; the synthesizer's gap analysis reads it.

```markdown
### Criteria Coverage
| Category | Checked | Not checked (reason) |
|----------|---------|----------------------|
| ARC (7)  | ARC-01, ARC-02, ... | — |
| PRO (7)  | PRO-01, ...          | — |
| MTH (4)  | —                    | N/A: non-quantitative manuscript |
| FIG (5)  | FIG-01, ...          | — |
| CIT (4)  | CIT-01, ...          | — |
| PRC (3)  | —                    | PRC-03: single round, no revision history |

Clean: 19/30 checked, 8 N/A, 3 not applicable this round
```

Rules:

1. **A category is not silently skipped.** Either its criteria are checked, or the reason they do not apply is written in the block. Silence is read by the synthesizer as a gap.
2. **`Not checked` needs a reason**, and the synthesizer surfaces the reason in its own gap analysis. An unexplained gap is a review defect, not a paper defect — report it as such.
3. **Clean criteria need no issue.** Only violations become issues. The coverage block, not the issue list, is what proves the criteria were walked.
4. **Panel coverage, not per-reviewer coverage.** In `full` mode the panel collectively covers all 30. A panel gap (a criterion no reviewer checked, with no N/A justification) is escalated by `editorial_synthesizer_agent` as a **review limitation** in the Decision Letter.

### Mode subsets

Full 30-criterion coverage is `full` mode's job alone. Other modes run a reduced set, and the reduction is stated in the report header so the author knows what was not examined.

| Mode | Criteria | Rationale |
|------|----------|-----------|
| `full` | all 30 across the panel | Complete first-round review |
| `methodology-focus` | MTH (4) + PRO-02 + CIT-02 + ARC-06 | 2-reviewer panel: rigor and claim support |
| `quick` | ARC-05, PRO-01, PRO-05, FIG-05, CIT-04, PRC-02 | 15-minute triage: thesis, readability, visual claims, citation orphans, submission blockers |
| `re-review` | PRC-03 first, then the criteria named by each carried-over issue ID | Verification is targeted by construction — see `re_review_mode_protocol.md` |
| `calibration` | inherits `full` | Calibration measures decision accuracy, not craft coverage |
| `guided` | ARC (7) + PRO (7) | Progressive revelation works on structure and prose; other categories surface only if reached |

**New-issue detection is not bounded by the mode subset.** Whatever subset ran, the panel still reports new defects it encounters — the subset governs what is *swept for*, not what may be *said*.

---

## 4. Relationship to Other References

| Reference | Relationship |
|-----------|--------------|
| `review_criteria_framework.md` | Scores scientific merit. This file covers craft. Both are required; neither substitutes for the other. |
| `quality_rubrics.md` | Calibrated 0–100 scoring. This file supplies what Dimension 5 (Writing Quality) is scored *against*. |
| `review_quality_thinking.md` | Cognitive lenses (internal validity, external validity, contribution) and reviewer traps. This file is the per-item checklist those lenses are applied through. |
| `writing_quality_check.md` | Deep rule for PRO-04, PRO-05 and the flagged-term list. |
| `academic_writing_style.md` | Deep rule for PRO-01, PRO-07 and discipline register. |
| `statistical_visualization_standards.md` | Deep rule for FIG-01…FIG-05 chart specifics. |
| `citation_format_switcher.md` | Deep rule for CIT-03 formatting. |
| `issue_lifecycle_protocol.md` | How a criterion violation becomes a tracked issue, and how the revision stage closes it. |
| `re_review_mode_protocol.md` | Verifies the round-2 disposition of every carried-over issue. |
