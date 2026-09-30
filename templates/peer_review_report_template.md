# Peer Review Report Template

This template is used by all reviewer agents (EIC, Reviewers 1-3). Each reviewer uses the same structure but fills in review content from their respective perspectives.

---

## Usage Instructions

1. Text in `[brackets]` is explanatory and needs to be replaced with actual content
2. Each reviewer must fully complete all required fields (items marked with *)
3. Detailed Comments are section-by-section commentary; only comment on sections relevant to your review focus
4. Language follows the paper's language (Chinese papers reviewed in Chinese, English papers in English)
5. Every weakness and minor issue is minted a stable `Issue ID` (`<SOURCE>-<NN>`, where `<SOURCE>` is your panel slot: `EIC` / `R1` / `R2` / `R3` / `DA`) and names the craft criterion it was raised against. `W1…W5` are presentation numbering; the `Issue ID` is the durable handle that follows the issue into the Revision Roadmap, the Revision Tracking Table, and re-review — see `../references/issue_lifecycle_protocol.md`
6. The report ends with the Craft Criteria Coverage block (`../references/craft_criteria_checklist.md` § Coverage Attestation). Walk the criteria you own; mark the rest N/A or not-checked with a reason. Do not report replacement text for a defect — report the defect and the direction of a fix

---

## Template

```markdown
# Peer Review Report

## Manuscript Information
- **Title**: [Paper title]
- **Manuscript ID**: [If available, enter manuscript ID]
- **Review Date**: [Review date]
- **Review Round**: [Round N review]

---

## Reviewer Information

### Reviewer Role *
[EIC / Peer Reviewer 1 (Methodology) / Peer Reviewer 2 (Domain) / Peer Reviewer 3 (Perspective)]

### Reviewer Identity *
[Identity description configured by field_analyst_agent]

### Review Focus *
[Core focus of this review, 2-3 sentences]

---

## Overall Assessment *

### Recommendation *
[Select one]
- [ ] **Accept** — Can be published directly, only minor formatting changes needed
- [ ] **Minor Revision** — Minor revisions needed, no re-review after revision
- [ ] **Major Revision** — Substantial revisions needed, re-review required after revision
- [ ] **Reject** — Not suitable for publication in this journal

### Confidence Score *
[1-5]
| Score | Meaning |
|-------|---------|
| 5 | Completely within my area of expertise, I am very confident in my assessment |
| 4 | Mostly within my area of expertise, high confidence |
| 3 | Partially within my area of expertise, moderate confidence |
| 2 | Some aspects outside my expertise, somewhat uncertain about my assessment |
| 1 | Mostly outside my expertise, my opinion is for reference only |

### Summary Assessment *
[150-250 word overall assessment]

Requirements:
- Sentences 1-2: What the paper does (topic, methods, main findings)
- Sentences 3-4: Overall quality assessment (from your review focus perspective)
- Sentences 5-6: Most critical strengths and weaknesses
- Final: Your recommendation rationale

---

## Strengths *

List 3-5 strengths of the paper. Each must:
- Have a specific title
- Cite passages, data, or page numbers from the paper
- Explain why it is a strength

### S1: [Strength title] *
[Specific description. E.g., "The research design uses a quasi-experimental pretest-posttest control group design (p. X), effectively controlling for..."]

### S2: [Strength title] *
[Specific description]

### S3: [Strength title] *
[Specific description]

### S4: [Strength title]
[Optional]

### S5: [Strength title]
[Optional]

---

## Weaknesses *

List 3-5 weaknesses of the paper. Each must:
- Have a specific title
- Carry a stable `Issue ID` and the `Criterion` it violates
- Describe the specific problem
- Explain why it is a problem
- Provide the direction of an improvement (not replacement text — see `../references/issue_lifecycle_protocol.md` §1)

### W1: [Weakness title] *
**Issue ID**: [EIC-1 / R1-1 / R2-1 / R3-1 / DA-1]
**Criterion**: [e.g. ARC-06, MTH-03 — or "n/a (merit dimension)"]
**Problem**: [Specific description of the problem, citing paper passages]
**Why it matters**: [Explain the impact of this problem]
**Suggested direction**: [What the fix needs to accomplish, not the finished sentence]
**Severity**: [Critical / Major / Minor]

### W2: [Weakness title] *
**Issue ID**: [...]
**Criterion**: [...]
**Problem**: [...]
**Why it matters**: [...]
**Suggested direction**: [...]
**Severity**: [Critical / Major / Minor]

### W3: [Weakness title] *
**Issue ID**: [...]
**Criterion**: [...]
**Problem**: [...]
**Why it matters**: [...]
**Suggested direction**: [...]
**Severity**: [Critical / Major / Minor]

### W4: [Weakness title]
[Optional, same format as above]

### W5: [Weakness title]
[Optional, same format as above]

---

## Detailed Comments *

Section-by-section commentary on the paper. Only comment on sections relevant to your review focus.

### Title & Abstract
- [Assess title accuracy and appeal]
- [Assess abstract structure and completeness]

### Introduction
- [Is research background sufficient]
- [Is research question/purpose clear]
- [Is research motivation persuasive]

### Literature Review / Theoretical Framework
- [Literature coverage] (Primarily reviewed by Reviewer 2)
- [Theoretical framework appropriateness] (Primarily reviewed by Reviewer 2)
- [Research gap argument]

### Methodology / Research Design
- [Research design appropriateness] (Primarily reviewed by Reviewer 1)
- [Sampling strategy]
- [Data collection]
- [Analysis methods]

### Results / Findings
- [Completeness of results presentation]
- [Figure/table quality]
- [Alignment of results with research questions]

### Discussion
- [Whether discussion addresses research questions]
- [Dialogue with the literature]
- [Theoretical and practical implications]
- [Discussion of limitations]

### Conclusion
- [Whether conclusions over-infer]
- [Value of future research directions]

### References
- [Citation format]
- [Quality and recency of cited references]

---

## Questions for Authors *

List 2-4 questions requiring author response. These questions should:
- Not be rhetorical, but genuinely need answering
- The answer could change the paper's quality or direction
- Be specific and answerable

1. [Question 1]
2. [Question 2]
3. [Question 3] (Optional)
4. [Question 4] (Optional)

---

## Minor Issues

List minor issues that don't affect academic quality but need correction. Each item carries an `Issue ID` and, where it maps to one, a `Criterion` — minor issues are tracked like any other, because most of what blocks acceptance is filed here.

### Language / Grammar
- [ID: EIC-4] [Criterion: PRO-01] [Page X, Line Y: Specific language issue]
- [...]

### Citation Format
- [ID: ...] [Criterion: CIT-03] [Specific citation format issues]
- [...]

### Figures and Tables
- [ID: ...] [Criterion: FIG-02] [Figure/table improvement suggestions]
- [...]

### Layout
- [ID: ...] [Criterion: ...] [Layout issues]
- [...]

---

## Dimension Scores *

Score each dimension 0-100 using the rubrics in `../references/quality_rubrics.md`. Report the range descriptor that best matches.

| Dimension | Score (0-100) | Descriptor | Notes |
|-----------|--------------|------------|-------|
| Originality (20%) | | [Exceptional/Strong/Adequate/Weak/Insufficient] | |
| Methodological Rigor (25%) | | [Exceptional/Strong/Adequate/Weak/Insufficient] | |
| Evidence Sufficiency (25%) | | [Exceptional/Strong/Adequate/Weak/Insufficient] | |
| Argument Coherence (15%) | | [Exceptional/Strong/Adequate/Weak/Insufficient] | |
| Writing Quality (15%) | | [Exceptional/Strong/Adequate/Weak/Insufficient] | |
| Literature Integration (optional) | | [See rubrics] | R2 focus |
| Significance & Impact (optional) | | [See rubrics] | R3 focus |
| **Weighted Average** | | **[Accept/Minor/Major/Reject]** | |

---

## Craft Criteria Coverage *

Walk the craft criteria you own and report the result. Criteria that do not apply to this manuscript are marked N/A with a reason; criteria outside your ownership are left to their owner. Never leave a category silent — the synthesizer reads this block to detect panel gaps, and silence is read as an unchecked gap. Full format and per-mode subsets: `../references/craft_criteria_checklist.md`.

| Category | Checked | Not checked (reason) |
|----------|---------|----------------------|
| ARC (7) | [ARC-01, ARC-02, ...] | [—] |
| PRO (7) | [...] | [...] |
| MTH (4) | [...] | [N/A: non-quantitative manuscript] |
| FIG (5) | [...] | [...] |
| CIT (4) | [...] | [...] |
| PRC (3) | [...] | [...] |

Clean: [N]/30 checked, [N] N/A, [N] not applicable this round
```

---

## Format Guidelines

### Severity Levels

| Level | Definition | Revision Requirement |
|-------|-----------|---------------------|
| **Critical** | Cannot be accepted without fixing | Required Revision |
| **Major** | Significantly affects paper quality | Strongly Recommended |
| **Minor** | Better if fixed, acceptable if not | Suggested |

### How to Cite Paper Passages

```
# Correct
"The author states on p. 12: 'AI can replace human judgment in QA processes,' but..."

# Correct
"The data in Table 3 shows p = 0.04, but the author does not report effect sizes..."

# Incorrect (too vague)
"Methodology has problems"
"Literature review is not comprehensive enough"
```

### Constructive Tone Examples

```
# Good
"The author is encouraged to consider adding X analysis to strengthen the argument for Y."

# Good
"This section's argumentation could be clearer. Specifically, the causal inference in paragraph 2, page 8 needs additional evidence support."

# Bad
"The author clearly does not understand X."

# Bad
"This method is wrong."
```
