# Editorial Decision Template

This template is used by `editorial_synthesizer_agent` to produce the final Editorial Decision Package.

---

## Template

```markdown
# Editorial Decision

## Manuscript Information
- **Title**: [Paper title]
- **Manuscript ID**: [If available]
- **Submission Date**: [Submission date]
- **Decision Date**: [Decision date]
- **Review Round**: [Round N]

---

## Decision *

### [Accept / Minor Revision / Major Revision / Reject]

[If Reject, indicate subtype: Out of Scope / Fundamental Flaw / Insufficient Contribution / Premature / Resubmit Encouraged]

---

## Reviewer Summary

| Reviewer | Role | Recommendation | Confidence |
|----------|------|---------------|------------|
| EIC | [Journal editor identity] | [Accept/Minor/Major/Reject] | [1-5] |
| Reviewer 1 | [Methodology expert identity] | [Accept/Minor/Major/Reject] | [1-5] |
| Reviewer 2 | [Domain expert identity] | [Accept/Minor/Major/Reject] | [1-5] |
| Reviewer 3 | [Cross-disciplinary expert identity] | [Accept/Minor/Major/Reject] | [1-5] |

---

## Consensus Analysis *

### Points of Agreement (Consensus)

**[CONSENSUS-4]** (All reviewers agree):
1. [Consensus content — cite relevant passages from each reviewer's report]
2. [...]

**[CONSENSUS-3]** (3/4 reviewers agree):
1. [Consensus content — indicate which 3 agree and which 1 has a different view]
2. [...]

> Each consensus item lists the issue IDs it consolidates: `[CONSENSUS-2] (R1-4, R2-7, DA-2) — …`. When several panelists raised the same defect, merge per `../references/issue_lifecycle_protocol.md` §5: the surviving issue keeps the ID of the source earliest in panel order (`EIC` → `R1` → `R2` → `R3` → `DA`), absorbed IDs are recorded as `merged-from`, and the merged item takes the highest severity.

### Points of Disagreement

**Disagreement 1: [Issue name]**
- **R[X] view**: [Specific viewpoint, citing report]
- **R[Y] view**: [Specific viewpoint, citing report]
- **Disagreement type**: [Perspective difference / Severity disagreement / Existence disagreement / Direction disagreement]
- **Editor's Resolution**: [Arbitration result]
- **Resolution Rationale**: [Arbitration rationale — based on evidence/expertise/conservative principle]

**Disagreement 2: [Issue name]**
- [Same format as above]

---

## Decision Rationale *

[200-300 words explaining the basis for this decision]

Requirements:
- Cite specific reviewer opinions
- Explain how disagreements were resolved
- Explain why this decision was chosen rather than a more or less strict one
- If Reject, explain why revision also cannot salvage it

---

## Required Revisions * (Must Fix)

[Only needed for Minor Revision and Major Revision]

⚠️ Roadmap rows are numbered `RM-<NN>` and carry an `origin` column of source issue IDs. They are **not** numbered `R1`/`R2`/`R3` — those labels belong to the panelists, and reusing them here makes "R2" ambiguous within this same document.

| # | Revision Item | Origin (issue IDs) | Source Reviewer | Severity | Section | Estimated Effort |
|---|--------------|-------------------|----------------|----------|---------|-----------------|
| RM-1 | [Description] | [R2-3, DA-1] | [EIC/R1/R2/R3/DA] | Critical | [Section name] | [X days] |
| RM-2 | [Description] | [Issue IDs] | [Source] | Critical/Major | [Section name] | [X days] |
| RM-3 | [Description] | [Issue IDs] | [Source] | Major | [Section name] | [X days] |
...

### Required Item Details

**RM-1: [Title]**
- **Origin issue ID(s)**: [R2-3 (merged-from: DA-1)] / [Criterion: ARC-02]
- **Problem**: [Specific description]
- **Source**: [Which reviewer raised it, citing report passage]
- **Requirement**: [Specifically what the fix must accomplish]
- **Acceptance criteria**: [How to confirm the issue is resolved after fixing]

**RM-2: [Title]**
- [Same format as above]

---

## Suggested Revisions (Should Fix)

| # | Revision Item | Origin (issue IDs) | Source Reviewer | Priority | Section | Expected Improvement |
|---|--------------|-------------------|----------------|----------|---------|---------------------|
| RM-4 | [Description] | [Issue IDs] | [Source] | P2 | [Section name] | [What it improves] |
| RM-5 | [Description] | [Issue IDs] | [Source] | P2/P3 | [Section name] | [What it improves] |
...

---

## Revision Roadmap *

### Priority 1 — Structural Revisions (Estimated total effort: X days)
- [ ] RM-1: [Task description — linked to Required Revisions above]
- [ ] RM-2: [Task description]
- [ ] RM-3: [Task description]

### Priority 2 — Content Supplementation (Estimated total effort: X days)
- [ ] RM-4: [Task description]
- [ ] RM-5: [Task description]

### Priority 3 — Text and Formatting (Estimated total effort: X days)
- [ ] RM-6: [Merged Minor Issues from all reviewers]
- [ ] RM-7: [Language polishing items]
- [ ] RM-8: [Citation format corrections]

### Total Estimated Effort
- **Minor Revision**: [X-Y days]
- **Major Revision**: [X-Y weeks]

---

## Revision Deadline

- **Recommended deadline**: [Date]
- **Basis**: [Minor: 2-4 weeks / Major: 6-8 weeks]
- **Extension policy**: [If extension is needed, notify 1 week before the deadline]

---

## Response Letter Instructions

Please use the format in `revision_response_template.md` to respond to every reviewer comment item by item.

**Must include**:
1. Response and revision description for each Required Revision
2. Response for each Suggested Revision (adopted or reason for not adopting)
3. Change markup (mark all changes in the revised manuscript with color or track changes)
4. Cross-reference table of new page numbers/paragraphs

---

## Closing

[Formal closing, adjusting tone based on decision type]

### Accept Version
We are pleased to accept your manuscript for publication in [Journal Name]. [If applicable, include minor suggestions]

### Minor Revision Version
We invite you to submit a revised version of your manuscript, addressing the points raised by the reviewers. We look forward to receiving your revision within [deadline].

### Major Revision Version
We encourage you to carefully consider the reviewers' comments and submit a substantially revised manuscript. Please note that the revised manuscript will undergo another round of review.

### Reject Version
After careful consideration, we are unable to accept your manuscript for publication in [Journal Name]. We appreciate the effort you have put into this work and hope the reviewers' comments will be helpful for future development of this research.

[If appropriate, recommend alternative journals]

---

## Appendix: Full Reviewer Reports

[Attach all 4 complete reviewer reports for the author's reference]
```

---

## Format Guidelines

### Revision Roadmap Design Principles

1. **Actionability**: Every item is a concrete task, not an abstract suggestion
2. **Traceability**: Every item carries its `origin` issue ID(s) back to specific reviewer comments; re-review joins on that ID, not on wording or row order
3. **ID immutability**: Roadmap IDs (`RM-<NN>`) and issue IDs are minted once. Reordering the roadmap does not renumber it, and a Roadmap ID is never reused for a different item
4. **Prioritization**: Priority 1 > 2 > 3; authors can process in order
5. **Time estimation**: Helps authors plan their revision timeline
6. **Compatibility**: Format can be directly used as `paper` 模块 revision mode input, which consumes it as the Stage A issue set (`../references/issue_lifecycle_protocol.md`)

### Severity-to-Priority Mapping

| Severity | Priority | Revision Type |
|----------|----------|--------------|
| Critical | P1 | Required Revision |
| Major | P1/P2 | Required / Strongly Suggested |
| Minor | P2/P3 | Suggested |
| Cosmetic | P3 | Optional |
