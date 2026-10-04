# Academic Paper Reviewer v3.11.0 — Multi-Perspective Academic Paper Review Agent Team

Simulates a complete international journal peer review process: automatically identifies the paper's field, dynamically configures 5 reviewers (Editor-in-Chief + 3 peer reviewers + Devil's Advocate) who review from four non-overlapping perspectives — methodology, domain expertise, cross-disciplinary viewpoints, and core argument challenges — ultimately producing a structured Editorial Decision and Revision Roadmap.

**v1.1 Improvements**:

1. Added Devil's Advocate Reviewer — specifically challenges core arguments, detects logical fallacies, and identifies the strongest counter-arguments
2. Added `re-review` mode — verification review, focused on checking whether revisions address the review comments
3. Expanded review team from 4 to 5 members

> **Routing discipline:** cross-module routing is handled by the suite entry [`../SKILL.md`](../SKILL.md)（按 `$ARGUMENTS[0]` 路由到 search/paper/reviewer/pipeline 四模块）. This document assumes routing has already settled — ambiguous cross-phase materials should have been clarified upstream.

---

## Quick Start

**Simplest command:**

```
Review this paper: [paste paper or provide file]
```

**Output:**

1. Automatically identifies the paper's field and methodology type
2. Dynamically configures the specific identities and expertise of 5 reviewers
3. 5 independent review reports (each from a different perspective)
4. 1 Editorial Decision Letter + Revision Roadmap

---

## Trigger Conditions

### Trigger Keywords

**English**: review paper, peer review, manuscript review, referee report, review my paper, critique paper, simulate review, editorial review, calibrate reviewer, reviewer calibration, measure reviewer accuracy

### Non-Trigger Scenarios

| Scenario                                              | Module to Use                     |
| ----------------------------------------------------- | -------------------------------- |
| Need to write a paper (not review)                    | paper 模块（[`reference/paper.md`](paper.md)）                 |
| Need to search / download papers (as the primary task) | search 模块（[`reference/search.md`](search.md)）             |
| Need to revise a paper (already have review comments) | paper 模块（revision 模式） |

（评审**内部**的背景证据检索不在此列：`full` 模式可按 [`../references/review_retrieval_protocol.md`](../references/review_retrieval_protocol.md) 调用 search 模块脚本拉取证据，检索器是 search，判断仍是评审员。）

### Quick Mode Selection Guide

| Your Situation                                                            | Recommended Mode  | Spectrum    |
| ------------------------------------------------------------------------- | ----------------- | ----------- |
| Need comprehensive review (first submission)                              | full              | balanced    |
| Checking if revisions addressed comments                                  | re-review         | fidelity    |
| Quick quality assessment (15 min)                                         | quick             | fidelity    |
| Focus only on methods/statistics                                          | methodology-focus | fidelity    |
| Want to learn by doing (guided review)                                    | guided            | originality |
| Want to know this reviewer's own error profile before trusting its scores | calibration       | fidelity    |

**Spectrum** (v3.2): _fidelity_ = template-heavy, predictable output; _balanced_ = default; _originality_ = exploratory, template-light. （上游 ARS 的跨技能 spectrum 表 `shared/mode_spectrum.md` ⚠️ 依赖缺失，未随本套件发布；三档定义以本句为准。）

Not sure? Use `full` for pre-submission review, `re-review` for post-revision verification. `calibration` is opt-in — run it once per domain when you want to know the reviewer's FNR/FPR before relying on its rubric scores.

---

## Agent Team (7 Agents)

| #   | Agent                                | Role                                                                                                    | Phase       |
| --- | ------------------------------------ | ------------------------------------------------------------------------------------------------------- | ----------- |
| 1   | `field_analyst_agent`                | Analyzes the paper's field, dynamically configures 5 reviewer identities                                | Phase 0     |
| 2   | `eic_agent`                          | Journal Editor-in-Chief — journal fit, originality, overall quality                                     | Phase 1     |
| 3   | `methodology_reviewer_agent`         | Peer Reviewer 1 — research design, statistical validity, reproducibility                                | Phase 1     |
| 4   | `domain_reviewer_agent`              | Peer Reviewer 2 — literature coverage, theoretical framework, domain contribution                       | Phase 1     |
| 5   | `perspective_reviewer_agent`         | Peer Reviewer 3 — cross-disciplinary connections, practical impact, challenging fundamental assumptions | Phase 1     |
| 6   | **`devils_advocate_reviewer_agent`** | **Devil's Advocate — core argument challenges, logical fallacy detection, strongest counter-arguments** | **Phase 1** |
| 7   | `editorial_synthesizer_agent`        | Synthesizes all reviews, identifies consensus and disagreements, makes editorial decision               | Phase 2     |

---

## Orchestration Workflow (3 Phases)

```
User: "Review this paper"
     |
=== Phase 0: FIELD ANALYSIS & PERSONA CONFIGURATION ===
     |
     +-> [field_analyst_agent] -> Reviewer Configuration Card (x5)
         - Reads the complete paper
         - Identifies: primary discipline, secondary discipline, research paradigm, methodology type, target journal tier, paper maturity
         - Dynamically generates specific identities for 5 reviewers:
           * EIC: Which journal's editor, area of expertise, review preferences
           * Reviewer 1 (Methodology): Methodological expertise, what they particularly focus on
           * Reviewer 2 (Domain): Domain expertise, research interests
           * Reviewer 3 (Perspective): Cross-disciplinary angle, what unique perspective they bring
           * Devil's Advocate: Specifically challenges core arguments, detects logical gaps
     |
     ** Presents Reviewer Configuration to user for confirmation (adjustable) **
     |
=== Phase 1: PARALLEL MULTI-PERSPECTIVE REVIEW ===
     |
     |-> [eic_agent] -------> EIC Review Report
     |   - Journal fit, originality, significance, relevance to readership
     |   - Does not go deep into methodology (that's Reviewer 1's job)
     |   - Sets the review tone
     |
     |-> [methodology_reviewer_agent] -> Methodology Review Report
     |   - Research design rigor, sampling strategy, data collection
     |   - Analysis method selection, statistical validity, effect sizes
     |   - Reproducibility, data transparency
     |
     |-> [domain_reviewer_agent] -------> Domain Review Report
     |   - Literature review completeness, theoretical framework appropriateness
     |   - Academic argument accuracy, incremental contribution to the field
     |   - Missing key references
     |
     |-> [perspective_reviewer_agent] --> Perspective Review Report
     |   - Cross-disciplinary connections and borrowing opportunities
     |   - Practical applications and policy implications
     |   - Broader social or ethical implications
     |
     +-> [devils_advocate_reviewer_agent] --> Devil's Advocate Report
         - Core argument challenges (strongest counter-arguments)
         - Cherry-picking detection
         - Confirmation bias detection
         - Logic chain validation
         - Overgeneralization detection
         - Alternative paths analysis
         - Stakeholder blind spots
         - "So what?" test
     |
=== Phase 2: EDITORIAL SYNTHESIS & DECISION ===
     |
     +-> [editorial_synthesizer_agent] -> Editorial Decision Package
         - Consolidates 5 reports (including Devil's Advocate challenges)
         - Identifies consensus (5 agree) vs. disagreement (divergent opinions)
         - Arbitration and argumentation for disputed issues
         - Devil's Advocate CRITICAL issues are specially flagged in the Editorial Decision
         - Merges duplicate issues across panelists, preserving the surviving issue ID; runs the Consistency Pass (`../references/issue_lifecycle_protocol.md` §6)
         - Reconciles the 5 craft-criteria coverage blocks; an unexplained panel gap is stated as a limitation of this review
         - Editorial Decision Letter
         - Revision Roadmap (prioritized, can be directly input to paper 模块 revision mode)
     |
=== Phase 2.5: REVISION COACHING (Socratic Revision Guidance) ===
     |
     ** Only triggered when Decision = Minor/Major Revision **
     |
     +-> [eic_agent] guides the user through Socratic dialogue:
         1. Overall positioning — "After reading the review comments, what surprised you the most?"
         2. Core issue focus — Guides user to understand consensus issues
         3. Revision strategy — "If you could only change three things, which three would you choose?"
         4. Counter-argument response — Guides user to think about how to respond to Devil's Advocate challenges
         5. Implementation planning — Helps prioritize revisions
     |
     +-> After dialogue ends, produces:
         - User's self-formulated revision strategy
         - Reprioritized Revision Roadmap
     |
     ** User can say "just fix it" to skip guidance **
```

### Checkpoint Rules

1. **After Phase 0 completes**: Present Reviewer Configuration Card to user; user can adjust reviewer identities
2. ⚠️ **IRON RULE**: 5 reviewers review independently, without cross-referencing each other.
3. ⚠️ **IRON RULE**: Synthesizer cannot fabricate review comments; must be based on specific reports from Phase 1.
4. ⚠️ **IRON RULE**: If the Devil's Advocate finds CRITICAL issues, the Editorial Decision cannot be Accept.
5. **Phase 2.5**: Revision Coaching only triggers when Decision is not Accept; user can choose to skip
6. ⚠️ **IRON RULE — READ-ONLY CONSTRAINT**: Reviewers MUST NOT modify the submitted manuscript. All review output (reports, decisions, roadmaps) is produced as separate documents. The reviewer examines the paper — it never rewrites it. If a reviewer agent attempts to edit the manuscript file, STOP and redirect to report generation.
7. ⚠️ **IRON RULE — STAGE D IS DIAGNOSE-ONLY**: Review is the diagnose stage of a two-stage loop (diagnose → act). Beyond the read-only constraint of Rule #6, a reviewer reports defects and the direction of a fix; it never supplies the replacement text. Diagnosis and revision never run in the same pass — the separation is what makes the round's diff auditable. Full rules in `../references/issue_lifecycle_protocol.md`.
8. ⚠️ **IRON RULE — CRAFT CRITERIA ARE MANDATORY**: Every Phase 1 report ends with a Criteria Coverage block walking the craft criteria that panelist owns (per `../references/craft_criteria_checklist.md`). A criterion that does not apply is marked N/A with a reason; a criterion that was not walked is marked with a reason. Silence is read by the synthesizer as a gap. Clean criteria produce no issue — the coverage block, not the issue list, is what proves the checklist was walked.
9. ⚠️ **IRON RULE — EVERY ISSUE CARRIES AN ID**: Each weakness, minor issue, and Devil's Advocate finding is minted a stable ID (`<SOURCE>-<NN>`, e.g. `R2-3`, `DA-1`) plus the criterion ID it was raised against. IDs are minted once, never renumbered, never recycled. Grammar, merge/split rules, and the five-artifact ID chain in `../references/issue_lifecycle_protocol.md`.

---

## Phase-by-phase Invocation Contract (v3.9.2)

The reviewer 模块 runs in 3 phases internally (Phase 0 field analysis → Phase 1 panel review → Phase 2 editorial synthesis). Within the full pipeline, this module sits at Stage 3 (Review), but each agent inside the module is single-phase relative to the module's own phase numbering.

Two invocation modes:

**Mode A — orchestrator-driven (default):** `pipeline_orchestrator_agent` (in the pipeline 模块) dispatches the reviewer 模块 as part of pipeline Stage 3 (Review).

**Mode B — phase-by-phase (cross-session resume):** User invokes one reviewer agent per phase across sessions, or runs the full reviewer panel standalone（经 [`../SKILL.md`](../SKILL.md) 以 `$ARGUMENTS[0]=reviewer` 进入）.

In Mode B, **single-phase agents (Bucket A) stay strictly within their assigned phase for writes**. The 6 Bucket A agents in the reviewer 模块 are: `eic_agent`, `methodology_reviewer`, `domain_reviewer`, `perspective_reviewer`, `devils_advocate_reviewer` (all Phase 1 panel) + `editorial_synthesizer` (Phase 2 synthesis). Reading the full paper draft is **expected** for all reviewers — without context they cannot evaluate.

The 1 Bucket D agent (`field_analyst` at Phase 0) is meta — it configures the panel; no boundary fence needed.

The v3.6.2 Sprint Contract Protocol (paper-blind Phase 1 + paper-visible Phase 2 + data delimiter) additionally constrains all reviewer agents' within-phase discipline. Phase Boundary (phase scope) and Sprint Contract (within-phase paper-blind/paper-visible discipline) both apply — neither overrides the other.

Routing into Mode B requires an explicit user signal — a `[direct-mode]` prefix or an explicit `$ARGUMENTS` selection（见 [`../SKILL.md`](../SKILL.md) 模块路由）. Ambiguous cross-phase input defaults to clarification before any phase runs.

**Enforcement:** prompt-level via Phase Boundary blocks on Bucket A agents. 阶段交接物的确定性校验由 [`../scripts/check_pipeline_integrity.py`](../scripts/check_pipeline_integrity.py) 提供（`issue-ids` / `rr-matrix` 子命令覆盖本模块产物；评审完成后 orchestrator 调用，校验不过不得进入下一阶段）。⚠️ 依赖缺失，当前版本未实现：deterministic PreToolUse hook、multi-phase envelope 未随本套件发布，仍以 prompt 级约束为准。

---

## Retrieval-Augmented Review (opt-in, v0.1)

`full` 模式可在评审前按 [`../references/review_retrieval_protocol.md`](../references/review_retrieval_protocol.md) 执行两步检索增强：评审员提出 ≤6 个背景核验问题 → `scripts/search_papers.py` / `scripts/citation_graph.py` 检索证据（确定性脚本，不走模型）→ Evidence Dossier 注入 Phase 1 后带证据评审。检索失败回退单轮评审并在 Limitations 声明。参与提问的 agent：`field_analyst`（主）+ `methodology_reviewer` + `domain_reviewer`（辅）。

---

## Operational Modes (6 Modes)

| Mode                     | Trigger                                                | Agents                                                      | Output                                                                                                                         |
| ------------------------ | ------------------------------------------------------ | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `full`                   | Default / "full review"                                | All 7 agents                                                | 5 review reports + Editorial Decision + Revision Roadmap                                                                       |
| **`re-review`**          | **Pipeline Stage 3' / "verification review"**          | **field_analyst + eic + editorial_synthesizer**             | **Revision response checklist + residual issues + new Decision**                                                               |
| `quick`                  | "quick review"                                         | field_analyst + eic                                         | EIC quick assessment + key issues list (15-minute version)                                                                     |
| `methodology-focus`      | "check methodology"                                    | field_analyst + eic + methodology_reviewer                  | In-depth methodology review report (panel 2 under v3.6.2 sprint contract: EIC + methodology)                                   |
| `guided`                 | "guide me"                                             | All + Socratic dialogue                                     | Socratic issue-by-issue guided review                                                                                          |
| **`calibration`** (v3.2) | **"calibrate reviewer" / "measure reviewer accuracy"** | **All 7 agents, 5x per gold paper, cross-model default-on** | **Calibration Report: FNR/FPR/balanced accuracy/AUC + per-dimension calibration error + session-scoped confidence disclosure** |

### Mode Selection Logic

```
"Review this paper"                      -> full
"Give me a quick look at this paper"     -> quick
"Help me check the methodology"          -> methodology-focus
"Does this paper have methodology issues"-> methodology-focus
"Guide me to improve this paper"         -> guided
"Walk me through the issues in my paper" -> guided
"Verification review" / "Check revisions"-> re-review
"How accurate is your review scoring?"   -> calibration
"Calibrate against these 10 papers"      -> calibration
```

---

## Re-Review Mode (Verification Review)

Dedicated mode for Pipeline Stage 3' — verifies whether revisions address first-round review comments. Uses R&R Traceability Matrix (Schema 11) with Author's Claim + Verified? columns.

**Input**: Original Revision Roadmap + Revised manuscript + Response to Reviewers (optional)
**Output**: Verification Review Report with traceability matrix + new issues + Decision

> See `../references/re_review_mode_protocol.md` for full verification logic, output format template, and Socratic guidance details.

---

## Guided Mode (Socratic Guided Review)

Helps authors understand problems themselves through progressive revelation. EIC opens with strengths, then gradually introduces deeper issues from each reviewer perspective.

> See `../references/guided_mode_protocol.md` for dialogue flow, rules, and progressive revelation sequence.

---

## Calibration Mode (v3.2)

Opt-in mode that measures this reviewer's FNR / FPR / balanced accuracy against a user-supplied gold set. Runs the `full` review with fresh context per paper, cross-model default-on. Produces a Calibration Report attached as a confidence disclosure to subsequent reviews in the session.

> **⚠️ 规则6 — 硬预算上限（不可自动绕过）**：calibration 金标论文 **≤3 篇**、每篇评审 **≤2 次**（全流程评审调用合计 ≤6 次）。任何超出（更多金标论文、更多重复次数、或对整批 5-20 篇跑 ensembling）**必须先获得用户显式批准**并在会话中记录批准语；orchestrator 与 reviewer 代理不得以"提升统计置信度"为由自行扩大预算。

> See `../references/calibration_mode_protocol.md` for full spec: intake rules, ensembling methodology, output format, and failure cases this mode does not fix.

---

## Review Output Format

Each reviewer's report structure is detailed in `../templates/peer_review_report_template.md`.

### Issue IDs (required)

Every weakness, minor issue, and Devil's Advocate finding is minted a stable ID at report time, in the format `<SOURCE>-<NN>` where `<SOURCE>` is the raising panelist (`EIC` / `R1` / `R2` / `R3` / `DA`) and `<NN>` is a two-digit per-panelist sequence. Each issue also names the craft criterion it was raised against (`ARC-02`, `PRO-05`, …).

```
### W2: Section 3.2 opens on the model equation before stating its purpose
- **Issue ID**: R2-3
- **Criterion**: ARC-02 (claim precedes apparatus)
- **Problem**: The subsection begins with Eq. 7 and defers its purpose to the third paragraph...
- **Why it matters**: ...
- **Suggested direction**: State the purpose in the opening sentence, then introduce Eq. 7...
- **Severity**: Major
```

The `W1…W5` labels remain as presentation numbering within a report; the `Issue ID` is the durable handle that survives into the Revision Roadmap, the Revision Tracking Table, and re-review. Full grammar, merge/split rules, and the ID chain across all five artifacts: `../references/issue_lifecycle_protocol.md`.

### Craft Criteria Coverage (required)

Each report ends with a coverage block proving which craft criteria that panelist walked, which did not apply, and why. Panel coverage across all six categories is a Phase 2 precondition; an unexplained panel gap is escalated by `editorial_synthesizer_agent` as a review limitation in the Decision Letter.

> See `../references/craft_criteria_checklist.md` for the 30 criteria, their owners, the coverage block format, and the reduced sets used by `quick` / `methodology-focus` / `re-review` / `guided`.

### Devil's Advocate Report Structure (Special Format)

The Devil's Advocate uses a dedicated format, not the standard reviewer template:

- **Strongest Counter-Argument** (200-300 words)
- **Issue List** (categorized as CRITICAL / MAJOR / MINOR, with dimension and location; each row carries an `Issue ID` under the `DA-` prefix and the criterion ID it was raised against)
- **Ignored Alternative Explanations/Paths**
- **Missing Stakeholder Perspectives**
- **Observations (Non-Defects)**

---

## Editorial Decision Format

The Editorial Decision Letter structure is detailed in `../templates/editorial_decision_template.md`.

---

## Integration

### Upstream/Downstream Relationships

```
search 模块 --> paper 模块 --> [integrity check] --> reviewer 模块 --> paper 模块 (revision) --> reviewer 模块 (re-review) --> [final integrity] --> finalize
(文献语料)      (写作)          (integrity audit)     (评审)               (修订)                (verification review)          (final verification)   (定稿)
```

### Specific Integration Methods

| Integration Direction                             | Description                                                                                                    |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Upstream: paper 模块 -> reviewer**              | Receives the complete paper output from paper 模块 `full` mode（`reference/paper.md`）, directly enters Phase 0 |
| **Upstream: integrity check -> reviewer**         | In the Pipeline, the paper must pass integrity check before entering reviewer                                  |
| **Downstream: reviewer -> paper 模块**            | The Revision Roadmap format can be directly used as reviewer feedback input for paper 模块 revision mode |
| **Downstream: reviewer (re-review) -> integrity** | After re-review completes, proceeds to final integrity verification（pipeline 模块 Stage 4.5）                  |

### Pipeline Usage Example

> See `../references/integration_guide.md` for a complete pipeline usage example.

---

## Agent File References

| Agent                              | Definition File                                |
| ---------------------------------- | ---------------------------------------------- |
| field_analyst_agent                | `../agents/field_analyst_agent.md`                |
| eic_agent                          | `../agents/eic_agent.md`                          |
| methodology_reviewer_agent         | `../agents/methodology_reviewer_agent.md`         |
| domain_reviewer_agent              | `../agents/domain_reviewer_agent.md`              |
| perspective_reviewer_agent         | `../agents/perspective_reviewer_agent.md`         |
| **devils_advocate_reviewer_agent** | **`../agents/devils_advocate_reviewer_agent.md`** |
| editorial_synthesizer_agent        | `../agents/editorial_synthesizer_agent.md`        |

---

## Reference Files

| Reference                                       | Purpose                                                                                                                                                 | Used By                    |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- |
| `../references/review_criteria_framework.md`       | Structured review criteria framework (differentiated by paper type)                                                                                     | all reviewers              |
| `../references/craft_criteria_checklist.md`        | 30 enumerable manuscript-craft criteria in 6 categories (ARC / PRO / MTH / FIG / CIT / PRC), owner mapping, coverage attestation block, per-mode subsets        | all reviewers              |
| `../references/issue_lifecycle_protocol.md`        | Stable issue ID grammar, diagnose→act separation rules, dispositions, merge/split rules, the five-artifact ID chain                                        | all reviewers, synthesizer |
| `../references/top_journals_by_field.md`           | Top journal lists for major academic fields (EIC role calibration)                                                                                      | field_analyst, eic         |
| `../references/editorial_decision_standards.md`    | Accept/Minor/Major/Reject criteria and decision matrix                                                                                                  | eic, editorial_synthesizer |
| `../references/statistical_reporting_standards.md` | Statistical reporting standards + APA 7.0 format quick reference + red flag list                                                                        | methodology_reviewer       |
| `../references/quality_rubrics.md`                 | Calibrated 0-100 scoring rubrics for 7 review dimensions with decision mapping                                                                          | all reviewers              |
| `../references/review_quality_thinking.md`         | Cognitive framework for review quality: three lenses (internal validity, external validity, contribution), common reviewer traps, calibration questions | all reviewers              |
| `../references/re_review_mode_protocol.md`         | Full re-review verification logic, R&R traceability output format, Socratic guidance after re-review                                                    | eic, editorial_synthesizer |
| `../references/guided_mode_protocol.md`            | Guided mode dialogue flow, progressive revelation sequence, dialogue rules                                                                              | all reviewers              |
| `../references/calibration_mode_protocol.md`       | Calibration mode: FNR/FPR/balanced accuracy measurement against user-supplied gold set, ensembling（受规则6硬上限：金标 ≤3 篇、每篇 ≤2 次）, session-scoped confidence disclosure (v3.2)      | all reviewers              |
| `../references/review_retrieval_protocol.md`       | Retrieval-augmented review: 评审前背景核验问题 + search/citation_graph 脚本检索 + Evidence Dossier（v0.1，full 模式 opt-in）                                                                  | field_analyst, methodology_reviewer, domain_reviewer |
| `../references/integration_guide.md`               | Complete 9-step pipeline usage example                                                                                                                  | —                          |
| `../references/changelog-reviewer.md`                       | Full version history                                                                                                                                    | —                          |

---

## Templates

| Template                                   | Purpose                                                 |
| ------------------------------------------ | ------------------------------------------------------- |
| `../templates/peer_review_report_template.md` | Review report template used by each reviewer            |
| `../templates/editorial_decision_template.md` | EIC final decision letter template                      |
| `../templates/revision_response_template.md`  | Revision response template for authors (R->A->C format) |

---

## Examples

| Example                                        | Demonstrates                                                                                                     |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `../examples/hei_paper_review_example.md`         | Full review example: "Impact of Declining Birth Rates on Management Strategies of Taiwan's Private Universities" |
| `../examples/interdisciplinary_review_example.md` | Cross-disciplinary review example: "Using Machine Learning to Predict University Closure Risk in Taiwan"         |

---

## Anti-Patterns

Explicit prohibitions to prevent common failure modes, especially during long conversations:

| #   | Anti-Pattern                                    | Why It Fails                                                       | Correct Behavior                                                                      |
| --- | ----------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| 1   | **Fabricating review comments**                 | Synthesizer invents critique not in any reviewer report            | Every synthesis point must trace to a specific Phase 1 reviewer report                |
| 2   | **Duplicate criticisms across reviewers**       | R1/R2/R3 raise identical points = fake diversity                   | Each reviewer has a distinct perspective; overlapping topics get different angles     |
| 3   | **Ignoring Devil's Advocate CRITICAL findings** | Editorial Decision says Accept despite DA flagging critical issues | If DA finds CRITICAL → Decision cannot be Accept (Checkpoint Rule #4)                 |
| 4   | **Rubber-stamp re-review**                      | Re-review says "all addressed" without verification                | Each concern must be independently verified against the revised manuscript            |
| 5   | **Sycophantic score inflation**                 | Giving 8/10 to mediocre work to avoid conflict                     | Scores must be evidence-based; a paper with methodology gaps cannot score >6 on rigor |
| 6   | **Editing the manuscript**                      | Reviewer "helpfully" fixes the paper directly                      | READ-ONLY: produce reports, never modify the paper (Checkpoint Rule #6)               |
| 7   | **Generic feedback**                            | "The methodology could be stronger" without specifics              | Every criticism must include: what's wrong, where it is, and a proposed fix           |
| 8   | **Diagnosing and editing in one pass**          | The reviewer rewrites the passage it just criticised               | Report the defect and the direction of a fix; editing is the revision stage's job (Checkpoint Rule #7) |
| 9   | **Silent criterion skipping**                   | A category is not walked and nothing says so — the gap is invisible | Emit a coverage block; mark N/A or not-checked with a reason (Checkpoint Rule #8)     |

---

## Quality Standards

| Dimension                         | Requirement                                                                                     |
| --------------------------------- | ----------------------------------------------------------------------------------------------- |
| Perspective differentiation       | Each reviewer's review must come from a different angle; no duplicate criticisms                |
| Evidence-based                    | EIC's decision must be based on specific reviewer comments; no fabrication                      |
| Specificity                       | Reviews must cite specific passages, data, or page numbers from the paper; no vague comments    |
| Balance                           | Strengths and Weaknesses must be balanced; cannot only criticize without affirming              |
| Professional tone                 | Review tone must be professional and constructive; avoid personal attacks or demeaning language |
| Actionability                     | Each weakness must include specific improvement suggestions                                     |
| Format consistency                | All reports must follow the template structure; no freestyle                                    |
| **Devil's Advocate completeness** | **Devil's Advocate must produce the strongest counter-argument; cannot be omitted**             |
| **Craft coverage**                 | Every report walks its owned craft criteria and reports a coverage block; no silent skips      |
| **Issue traceability**             | Every issue carries a stable ID (`<SOURCE>-<NN>`) and criterion ID, reusable at re-review      |
| **CRITICAL threshold**            | **⚠️ IRON RULE: Devil's Advocate CRITICAL issues cannot be ignored by the Editorial Decision**  |

---

## Output Language

Follows the paper's language. Academic terms remain in English. User can override (e.g., "review this Chinese paper in English").

---

## Related Modules

| Module                | Relationship                                                       |
| --------------------- | ------------------------------------------------------------------ |
| paper（`reference/paper.md`） | Upstream (provides paper) + Downstream (receives revision roadmap) |
| search（`reference/search.md`） | Upstream (provides literature corpus for domain analysis)          |
| pipeline（`reference/pipeline.md`） | Orchestrated by (Stage 3 + Stage 3')                               |

（上游 ARS 的辅助技能 `tw-hei-intelligence` ⚠️ 依赖缺失，未随本套件发布。）

---

## v3.6.2 Sprint Contract Hard Gate

- **Reviewer hard gate.** All reviewer modes that ship with contracts (`reviewer_full`, `reviewer_methodology_focus`) now run two-call Phase 1 (paper-content-blind) + Phase 2 (paper-visible) orchestration. See `../references/sprint_contract_protocol.md`.
- **Schema 13 sprint contract.** Template-driven acceptance criteria with `panel_size`, `acceptance_dimensions`, `failure_conditions` (with `severity` precedence + `cross_reviewer_quantifier` panel-relative thresholds), `measurement_procedure`, optional `override_ladder`, bounded `agent_amendments`. ⚠️ 依赖缺失，当前版本未实现：validator `scripts/check_sprint_contract.py` 与 schema `shared/sprint_contract.schema.json` 未随本套件发布；契约以文字约束（`../references/sprint_contract_protocol.md` 与各 agent 文件）为准。
- **Synthesizer three-step mechanical protocol.** Build cross-reviewer matrix → evaluate each failure_condition with panel-relative quantifier + expression vocabulary → resolve precedence by severity. Forbidden operations explicit in `../agents/editorial_synthesizer_agent.md`.
- **methodology_focus reduced panel.** `reviewer_methodology_focus` mode runs a 2-reviewer panel (EIC + methodology only) instead of the default 5.
- **Templates:** ⚠️ 依赖缺失，当前版本未实现：`shared/contracts/reviewer/full.json`（panel 5）与 `shared/contracts/reviewer/methodology_focus.json`（panel 2）未随本套件发布，以 `../references/sprint_contract_protocol.md` 的文字版契约为准。Reserved modes (`reviewer_re_review`, `reviewer_calibration`, `reviewer_guided`) keep pre-v3.6.2 behaviour.

---

## Version Info

| Item             | Content                                                |
| ---------------- | ------------------------------------------------------ |
| Skill Version    | 0.1.3（套件统一版本，与 skill.json / git tag v0.1.3 一致；正文 `v3.2`–`v3.9.2` 等为上游 ARS 机制历史标注） |
| Last Updated     | 2026-10-01 |
| Maintainer       | Cheng-I Wu                                             |
| Dependent Modules | paper 模块（upstream/downstream integration）           |
| Role             | Multi-perspective academic paper review simulator      |

---

## Changelog

> See `../references/changelog-reviewer.md` for full version history.
