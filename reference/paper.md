# Academic Paper — Academic Paper Writing Agent Team

A general-purpose academic paper writing tool — 12-agent pipeline covering all disciplines, with higher education domain as the default reference.

**v2.5** adds two writing quality features:

- **Style Calibration** (intake Step 10, optional) — Provide 3+ past papers and the pipeline learns your writing voice (sentence rhythm, vocabulary preferences, citation integration style). Applied as a soft guide during drafting; discipline conventions always take priority. ⚠️ 依赖缺失，当前版本未实现：上游 ARS 的 `shared/style_calibration_protocol.md` 未随本套件发布；本套件按此句的文字约定执行（软引导、纪律惯例优先），无独立协议文件。
- **Writing Quality Check** (`../references/writing_quality_check.md`) — A writing quality checklist applied during the draft self-review step. Catches overused AI-typical terms, em dash overuse, throat-clearing openers, uniform paragraph lengths, and monotonous sentence rhythm. These are good writing rules, not detection evasion.

> **Routing discipline:** cross-module routing is handled by the suite entry [`../SKILL.md`](../SKILL.md)（按 `$ARGUMENTS[0]` 路由到 search/paper/reviewer/pipeline 四模块）. This document assumes routing has already settled — ambiguous cross-phase materials should have been clarified upstream.

## Quick Start

**Minimal command:**

```
Write a paper on the impact of AI on higher education quality assurance
```

```
Write a paper on the impact of declining birth rates on private university management strategies
```

**Execution flow:**

1. Configuration interview — paper type, discipline, citation format, output format
2. Literature search — systematic search strategy, source screening
3. Architecture design — paper structure, outline, word count allocation
4. Argumentation construction — claim-evidence chains, logical flow
5. Full-text drafting — section-by-section draft, register adjustment
6. Citation compliance + bilingual abstract (parallel)
7. Peer review — five-dimension scoring, revision suggestions
8. Output formatting — LaTeX/DOCX (via Pandoc)/PDF/Markdown

---

## Trigger Conditions

### Trigger Keywords

**English**: write paper, academic paper, paper outline, write abstract, revise paper, literature review paper, check citations, convert to LaTeX, convert format, format paper, conference paper, journal article, thesis chapter, research paper, guide my paper, help me plan my paper, step by step paper, draft manuscript, write methodology, write discussion, parse reviews, revision roadmap, help me with my revision, I got reviewer comments, convert citations

**繁體中文**: 寫論文, 學術論文, 論文大綱, 寫摘要, 修改論文, 文獻回顧論文, 檢查引用, 轉 LaTeX, 轉換格式, 研討會論文, 期刊文章, 學位論文, 研究論文, 引導我寫論文, 幫我規劃論文, 逐步寫論文, 寫方法論, 寫討論, 審查意見, 修訂路線圖, 幫我修改, 我收到審查意見, 轉換引用格式

### Plan Mode Activation

Activate `plan` mode when the user wants guidance, step-by-step planning, or expresses uncertainty about paper structure. **Default rule**: when ambiguous between `plan` and `full`, prefer `plan`.

> See `../references/plan_mode_protocol.md` for full intent signals and activation rules.

### Does NOT Trigger

| Scenario                                          | Use Instead               |
| ------------------------------------------------- | ------------------------- |
| Searching / downloading papers (not writing)      | search 模块（[`reference/search.md`](search.md)） |
| Reviewing a paper (structured review)             | reviewer 模块（[`reference/reviewer.md`](reviewer.md)） |
| Full research-to-paper pipeline                   | pipeline 模块（[`reference/pipeline.md`](pipeline.md)） |

### Distinction from the search 模块

| Feature        | paper 模块                                     | search 模块      |
| -------------- | --------------------------------------------- | ---------------- |
| Primary output | Publishable paper draft                       | 论文清单 + Markdown 全文语料 |
| Structure      | Journal-ready (IMRaD, etc.)                   | 无固定结构（每篇按原文转换） |
| Citation       | Multi-format (APA/Chicago/MLA/IEEE/Vancouver) | 仅记录元数据（标题/来源/标识符） |
| Abstract       | Bilingual (zh-TW + EN)                        | 转录原文摘要     |
| Peer review    | Simulated 5-dimension review                  | 无               |
| Output format  | LaTeX/DOCX (via Pandoc)/PDF/Markdown          | Markdown only    |
| Revision loop  | Max 2 rounds with targeted feedback           | 无               |

---

## Agent Team (12 Agents)

| #   | Agent                         | Role                                                                                                                                                                   | Phase                 |
| --- | ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| 1   | `intake_agent`                | Configuration interview: paper type, discipline, journal, citation format, output format, language, word count; Handoff detection; Plan mode simplified interview      | Phase 0               |
| 2   | `literature_strategist_agent` | Search strategy design, source screening, annotated bibliography, literature matrix                                                                                    | Phase 1               |
| 3   | `structure_architect_agent`   | Paper structure selection, detailed outline, word count allocation, evidence mapping                                                                                   | Phase 2               |
| 4   | `argument_builder_agent`      | Argument construction, claim-evidence chains, logical flow, counter-argument handling; Plan mode argument stress test                                                  | Phase 3 / Plan Step 3 |
| 5   | `draft_writer_agent`          | Section-by-section full draft writing, discipline register adjustment, word count tracking                                                                             | Phase 4               |
| 6   | `citation_compliance_agent`   | Citation format verification, reference list completeness, DOI checking                                                                                                | Phase 5a              |
| 7   | `abstract_bilingual_agent`    | Bilingual abstract (zh-TW + EN), 5-7 keywords each                                                                                                                     | Phase 5b              |
| 8   | `peer_reviewer_agent`         | Simulated double-blind review, five-dimension scoring, revision suggestions (max 2 rounds)                                                                             | Phase 6               |
| 9   | `formatter_agent`             | Convert to LaTeX/DOCX (via Pandoc)/PDF/Markdown, journal formatting, cover letter, citation format conversion (APA 7 / Chicago / MLA / IEEE / Vancouver)               | Phase 7               |
| 10  | `socratic_mentor_agent`       | Plan mode Socratic mentor: chapter-by-chapter guidance, convergence criteria (4 signals), question taxonomy (4 types), INSIGHT extraction                              | Plan Step 0-3         |
| 11  | `visualization_agent`         | Parse paper data and generate publication-quality figure code (Python matplotlib / R ggplot2) with APA 7.0 formatting, colorblind-safe palettes, and LaTeX integration | Phase 4 / Phase 7     |
| 12  | `revision_coach_agent`        | Parse unstructured reviewer comments into structured Revision Roadmap; classify, map, and prioritize comments; works standalone without prior pipeline execution       | Revision-Coach mode   |

---

## Output Formats

### Text Formats

LaTeX (.tex + .bib), DOCX (via Pandoc), PDF (via LaTeX or Pandoc), Markdown.

### Figures

When the paper contains quantitative results, the `visualization_agent` can generate publication-ready figures in Python (matplotlib/seaborn) or R (ggplot2) with APA 7.0 formatting and colorblind-safe palettes. Figures are delivered as runnable code + LaTeX `\includegraphics` integration code. See `../references/statistical_visualization_standards.md` for chart type decision trees and code templates.

### Citation Formats

APA 7.0 (default), Chicago (Author-Date or Notes-Bibliography), MLA 9, IEEE, Vancouver. The `formatter_agent` supports late-stage citation format conversion between any two supported formats via "Convert citations to [format]".

---

## Orchestration Workflow (8 Phases)

```
Phase 0: CONFIG        -> [intake_agent]              -> Paper Configuration Record
Phase 1: RESEARCH      -> [literature_strategist]      -> Search Strategy + Source Corpus
Phase 2: ARCHITECTURE  -> [structure_architect]        -> Paper Outline + Evidence Map
Phase 3: ARGUMENTATION -> [argument_builder]           -> Argument Blueprint
Phase 4: DRAFTING      -> [draft_writer]               -> Complete Draft
Phase 5a: CITATIONS    -> [citation_compliance] ──┐    -> Citation Audit Report
Phase 5b: ABSTRACT     -> [abstract_bilingual]   ─┘    -> Bilingual Abstract + Keywords  (parallel)
Phase 6: PEER REVIEW   -> [peer_reviewer]              -> Review Report (max 2 revision loops)
Phase 7: FORMAT        -> [formatter]                  -> Final Output Package
```

> See `../references/workflow_phase_details.md` for detailed per-phase agent behavior and output descriptions.

### Checkpoint Rules

1. ⚠️ **IRON RULE**: User must confirm Paper Configuration Record before proceeding to Phase 1
2. **Phase 2 -> 3**: User must approve outline (can request restructuring)
3. ⚠️ **IRON RULE**: Max 2 revision loops; unresolved items -> "Acknowledged Limitations"
4. **Peer Review** Critical-severity issues block progression to Phase 7
5. User can skip Phase 1 (literature) if providing own sources

---

> **v3.4.0 compliance (applies to `full` mode):** Before finalization, a RAISE principles-only compliance check runs (warn-only; primary research is outside PRISMA-trAIce scope). Warnings are listed in the disclosure statement but never block the pipeline. ⚠️ 依赖缺失，当前版本未实现：上游 ARS 的 `shared/raise_framework.md` 与独立 `compliance_agent` 未随本套件发布；按本句文字约定以 warn-only 方式在披露声明中执行。

## Phase-by-phase Invocation Contract (v3.9.2)

The paper 模块 pipeline runs in 8 phases (Phase 0 intake → 7 formatting). Two invocation modes:

**Mode A — orchestrator-driven (default):** `pipeline_orchestrator_agent` (in the pipeline 模块) runs all phases end-to-end with state tracking via Material Passport.

**Mode B — phase-by-phase (cross-session resume):** User invokes one agent per phase across sessions for long-running projects. Common pattern: write the draft in one session, return next week to citation-check / abstract / peer-review independently.

In Mode B, **single-phase agents (Bucket A) stay strictly within their assigned phase for writes**. The 7 Bucket A agents in the paper module are: `literature_strategist` (P1), `structure_architect` (P2), `draft_writer` (P4/P6 per invocation), `citation_compliance` (P5a), `abstract_bilingual` (P5b), `peer_reviewer` (P6), `formatter` (P7). Reads from upstream phases are allowed.

Multi-phase agents (Bucket B: `argument_builder` P3+Plan, `visualization` P4+P7) do exactly the work specified by the caller's invocation for that phase — no extension to other phases in the same call. The v3.6.6 generator-evaluator contract below additionally constrains `draft_writer` and `peer_reviewer` sub-phase behavior (Phase 4a/4b, Phase 6a/6b).

Routing into Mode B requires an explicit user signal — a `[direct-mode]` prefix or an explicit per-module `$ARGUMENTS` selection（见 [`../SKILL.md`](../SKILL.md) 模块路由）. Ambiguous cross-phase input defaults to clarification before any phase runs.

**Enforcement:** prompt-level via Phase Boundary blocks on Bucket A agents. ⚠️ 依赖缺失，当前版本未实现：上游 ARS 的 advisory verifier（`scripts/check_pipeline_integrity.py`）、deterministic PreToolUse hook、multi-phase envelope 均未随本套件发布。

## v3.6.6 Generator-Evaluator Contract Protocol

> Authoritative orchestration block for the v3.6.6 contract-gated phase splits inside paper 模块 `full` mode. ⚠️ 依赖缺失，当前版本未实现：上游 ARS 的机器可读契约文件（`shared/sprint_contract.schema.json`、`shared/contracts/writer/full.json`、`shared/contracts/evaluator/full.json`）与设计文档（`docs/design/2026-04-27-ars-v3.6.6-generator-evaluator-contract-design.md`）均未随本套件发布。契约基线以**本节及两个 agent 文件中的文字约束为准**：writer 维度 D1–D7 与失败条件 F1/F4/F2/F3/F0 见 `../agents/draft_writer_agent.md` § "Phase 4b output contract"；evaluator 维度 D1–D5 与失败条件 F1/F2/F3/F6/F4/F5/F0 见 `../agents/peer_reviewer_agent.md` § "Phase 6b output contract"。
>
> **Applies to paper 模块 `full` mode only.** Nine non-full modes (`plan`, `outline-only`, `revision`, `revision-coach`, `abstract-only`, `lit-review`, `format-convert`, `citation-check`, `disclosure`) are byte-equivalent across v3.6.5 → v3.6.6 and do not invoke this protocol. Pipeline boundary unchanged: pipeline 模块 Stage 2 dispatches paper 模块 in plan or full mode (full only invokes this protocol); Stage 3 dispatches reviewer 模块 (5-panel external editorial review). The in-pair Phase 6 evaluator under this protocol and the Stage 3 reviewer are different review layers — see `../agents/peer_reviewer_agent.md` § layer-disambiguation.

### Overview

v3.6.6 splits Phase 4 (writer drafting) and Phase 6 (in-pair evaluator review) into paper-blind / paper-visible call pairs gated by the `writer_full` and `evaluator_full` contracts. The split mirrors `../references/sprint_contract_protocol.md` (the v3.6.2 reviewer pattern) but adapts it for single-agent generator modes that have no panel and (for the writer) no scoring_plan.

The load-bearing mechanism is the **physical separation of calls**: writer Phase 4a never sees the runtime drafting artefacts; evaluator Phase 6a never sees the writer Phase 4b draft. This destroys the "read the paper, then rationalise the standard" drift path on the in-pair self-quality gate.

### Four-call structure

For each paper 模块 `full` invocation, Phase 4 + Phase 6 expand from two single calls into four separate model calls. Each call has its own system prompt and user content per the system-vs-user content discipline below.

1. **Phase 4a — writer paper-blind pre-commitment.**
   - System prompt: `### Phase 4a — Writer paper-blind pre-commitment` sub-section in `../agents/draft_writer_agent.md` § "v3.6.6 Generator-Evaluator Contract Protocol".
   - User content: `writer_full` contract JSON + paper metadata only (`title`, `field`, `word_count`).
   - Output: `## Acceptance Criteria Paraphrase` section + terminal `[PRE-COMMITMENT-ACKNOWLEDGED]` tag.
   - Lint: 3 structural checks (see § "Phase 4a / 6a output lint" below).
2. **Phase 4b — writer paper-visible drafting + self-scoring.**
   - System prompt: `### Phase 4b — Writer paper-visible drafting + self-scoring` sub-section in the same agent file.
   - User content: `writer_full` contract JSON (re-injected) + Phase 4a output wrapped in `<phase4a_output>...</phase4a_output>` data delimiter + upstream drafting artefacts (Paper Configuration Record, Paper Outline, Argument Blueprint, Annotated Bibliography, optional Style Profile, optional Knowledge Isolation Directive).
   - Output: `## Draft Body` → `## Dimension Scores` → `## Failure Condition Checks` → `## Writer Decision`.
   - Lint: 4 structural checks (see § "Phase 4b / 6b output lint" below).
3. **Phase 6a — evaluator paper-blind pre-commitment.**
   - System prompt: `### Phase 6a — Evaluator paper-blind pre-commitment` sub-section in `../agents/peer_reviewer_agent.md` § "v3.6.6 Generator-Evaluator Contract Protocol".
   - User content: `evaluator_full` contract JSON + paper metadata + the writer's most recent `<phase4a_output>` (the writer artefact the evaluator must verify per `disagreement_handling.pre_commitment_check_protocol.check_writer_artifact`).
   - Output: `## Contract Paraphrase` + `## Scoring Plan` (per-dimension `dimension_id` / `what_to_look_for` / `what_triggers_block` / `what_triggers_warn`) + terminal `[PRE-COMMITMENT-ACKNOWLEDGED]` tag.
   - Lint: 5 structural checks.
4. **Phase 6b — evaluator paper-visible scoring + decision.**
   - System prompt: `### Phase 6b — Evaluator paper-visible scoring + decision` sub-section in the same agent file.
   - User content: `evaluator_full` contract JSON (re-injected) + Phase 6a output wrapped in `<phase6a_output>...</phase6a_output>` + the writer's `<phase4a_output>` (unconditional per `pre_commitment_check_protocol.check_writer_artifact`) + the writer Phase 4b draft (the artefact under review).
   - Output: `## Dimension Scores` → `## Failure Condition Checks` → `## Review Body` → `## Evaluator Decision`.
   - Lint: 5 structural checks.

### System prompt vs user content discipline

Mirrors `../references/sprint_contract_protocol.md` §2 reviewer pattern verbatim:

- **System prompt carries invariant policy text only**: the phase sub-section instructions from the agent file's `## v3.6.6 Generator-Evaluator Contract Protocol` block, the lint description, and the phase-boundary tag conventions.
- **User content carries the contract JSON (re-injected per call) plus the runtime inputs allowed at that phase**: paper metadata, `<phase4a_output>` / `<phase6a_output>` delimiter blocks, upstream drafting artefacts, the paper draft.

All dynamic LLM output (Phase Na runtime emissions, paper content) lives in user content via data delimiters, never in the system prompt. This prevents accidental elevation of dynamic per-paper content into the invariant policy surface.

### Schema field name vs runtime emission distinction

`pre_commitment_artifacts` (snake_case, backticks) is the contract baseline field name (⚠️ 依赖缺失：上游 schema 文件 `shared/sprint_contract.schema.json` 未随本套件发布，字段语义以下述文字为准) — a configuration declaration in the frozen contract baseline. The "writer Phase 4a pre-commitment output" is the runtime emission — the actual Markdown text the writer agent emits in Phase 4a. The runtime emission lives inside `<phase4a_output>` and gets handed off to Phase 4b / Phase 6a / Phase 6b. Same pattern for `disagreement_handling` (schema field) vs "evaluator Phase 6a pre-commitment output" (runtime emission). Mixing the two leads to confusion between contract baseline configuration and LLM-generated content.

### Phase 4a / 6a output lint

Mode-specific structural check counts, per `../references/sprint_contract_protocol.md` §4 enumeration convention:

- **Writer Phase 4a (3 checks)**: required sections in order (`## Acceptance Criteria Paraphrase`, terminal `[PRE-COMMITMENT-ACKNOWLEDGED]`); paraphrase paragraph count ≥ the `pre_commitment_artifacts.acceptance_criteria_paraphrase.minimum_dimensions` value declared in the contract baseline (文字约束见 `../agents/draft_writer_agent.md`); Phase 4a content references contract baseline + paper metadata only. **No `## Scoring Plan` section** — the writer contract carries no scoring_plan.
- **Evaluator Phase 6a (5 checks)**: required sections in order (`## Contract Paraphrase`, `## Scoring Plan`, terminal `[PRE-COMMITMENT-ACKNOWLEDGED]`); paraphrase paragraph count ≥ the `disagreement_handling.paraphrase_minimum_dimensions` value declared in the contract baseline ("all" in the shipped baseline, meaning all five D1–D5); one `### <Dn>: <name>` subsection per acceptance dimension; each scoring_plan subsection contains the four-field shape (`dimension_id`, `what_to_look_for`, `what_triggers_block`, `what_triggers_warn`); Phase 6a content references contract baseline + paper metadata + the writer's `<phase4a_output>` only (no full draft / paper content).

Retry semantics: lint failure on the first attempt → retry once with the specific lint gap hinted in the system prompt; second failure → mark this role unusable per § "Single-agent generator unusable handling" below.

### Phase 4b / 6b output lint

- **Writer Phase 4b (4 checks)**: required sections in order — `## Draft Body`, `## Dimension Scores`, `## Failure Condition Checks`, `## Writer Decision`; Dimension Scores one-to-one across the seven writer dimensions D1–D7 (D1 section_completeness, D2 citation_density, D3 argument_blueprint_fidelity, D4 total_word_count, D5 per_section_word_count, D6 acknowledged_limitations, D7 register_consistency — enumerated in `../agents/draft_writer_agent.md`); Failure Condition Checks one-to-one across F1 / F4 / F2 / F3 / F0; Writer Decision derivable from F-condition severity precedence. **No multi-dissent retry** (writer has no scoring_plan to dissent against). **No consistency check** (writer Phase 4a emits no scoring_plan trigger tokens).
- **Evaluator Phase 6b (5 checks)**: required sections in order — `## Dimension Scores`, `## Failure Condition Checks`, `## Review Body`, `## Evaluator Decision`; Dimension Scores one-to-one across the five evaluator dimensions D1–D5 (originality, methodological rigor, evidence sufficiency, argument coherence, writing quality — enumerated in `../agents/peer_reviewer_agent.md`); Failure Condition Checks one-to-one across F1 / F2 / F3 / F6 / F4 / F5 / F0; consistency check (Phase 6b score substring-matches Phase 6a scoring_plan trigger tokens); Evaluator Decision derivable from F-condition severity precedence. **No multi-dissent retry** (evaluator's intra-phase disagreement is encoded as F-condition action via the `disagreement_handling` rules, not as a retry trigger).

Multi-dissent retry remains reviewer-only (reviewer 模块, `reference/reviewer.md`); generator modes have no panel and no scoring_plan dissent anchor.

Lint count summary across the three modes:

| Phase             | Reviewer (zero-touch) | Writer | Evaluator |
| ----------------- | --------------------- | ------ | --------- |
| Phase 1 / 4a / 6a | 5                     | 3      | 5         |
| Phase 2 / 4b / 6b | 6                     | 4      | 5         |

### Single-agent generator unusable handling

When a writer or evaluator phase becomes unusable (Phase Na lint twice fail OR Phase Nb lint fail), paper 模块 emits a phase-level abort tag and routes to user intervention:

- **Writer Phase 4 unusable** → `[GENERATOR-PHASE-ABORTED: role=writer, contract=<id>, reason=<lint_failure_kind>]` → abort paper 模块 Phase 4 → user intervention decides retry / fallback / regression to Phase 3 (Argument Blueprint).
- **Evaluator Phase 6 unusable** → `[GENERATOR-PHASE-ABORTED: role=evaluator, contract=<id>, reason=<lint_failure_kind>]` → abort paper 模块 Phase 6 → user intervention decides retry / fallback / regression to Phase 5 (Drafting completion).

`[GENERATOR-PHASE-ABORTED]` does **not** constitute a valid Phase 6b emission and cannot enter Stage 3 reviewer dispatch. Two valid Stage 3 entry paths exist (per design doc §5.1):

- **Standard path**: evaluator Phase 6b emits F0 `evaluator_decision=accept` or F4 `evaluator_decision=accept_with_dissent_note`.
- **Exceptional path**: evaluator Phase 6b emits F5 `evaluator_decision=flag_for_reviewer_stage` after the in-pair revision loop exhausts at round 2 with mandatory-dimension block recurring.

paper 模块 carries no panel cardinality invariant for writer / evaluator (no `panel_size` field — Schema 13.1 §3.3.5 reviewer-conditional). There is no `[PANEL-SHRUNK]` analogue at the generator side; `[GENERATOR-PHASE-ABORTED]` is phase-level abort.

**Operational monitor**: track `[GENERATOR-PHASE-ABORTED]` rate over the first three months of v3.6.6 deployment. The denominator is **per paper 模块 `full` run** — one user-perceived top-level invocation. The 5% threshold is `(runs_with_any_abort) / (total_runs)`. If the rate exceeds 5%, v3.6.7 introduces graceful-degradation fallback (see § "Known limitations" below).

### Cross-session resume scope

The v3.6.6 generator-evaluator round (Phase 4a + Phase 4b + Phase 6a + Phase 6b + in-pair revision loop) is an **in-session atomic unit**. Manual session split mid-round → writer Phase 4a output is lost; new session must restart paper 模块 `full` mode from Phase 0.

The v3.6.3 `ARS_PASSPORT_RESET=1` `reset_boundary[]` mechanism (per `../references/passport_as_reset_boundary.md`) operates at pipeline 模块 Stage boundaries, not at paper 模块 internal phase boundaries. paper 模块 internal phases (4a / 4b / 6a / 6b) are **not** boundary points; no `kind: boundary` ledger entry is emitted between them. v3.6.7+ may introduce `pre_commitment_history[]` to persist writer Phase 4a artefacts across sessions if operational data warrants — see § "Known limitations" below.

## Known limitations

- **No graceful-degradation fallback in v3.6.6**: when the writer or evaluator phase aborts via `[GENERATOR-PHASE-ABORTED]`, paper 模块 `full` aborts and routes to user intervention. v3.6.7 may introduce a fallback that degrades the affected phase to v3.6.5 single-call behaviour and logs the degradation. v3.6.6 ships with abort-only behaviour. See § "Single-agent generator unusable handling" above for the operational 5% / three-month monitor.
- **No cross-session resume mid-round**: the four-phase generator-evaluator round is an in-session atomic unit. Manual session split mid-round loses the writer Phase 4a artefact and forces restart from Phase 0. v3.6.7+ may introduce a `pre_commitment_history[]` ledger entry in Schema 9 to persist the writer Phase 4a artefact across session boundaries; v3.6.6 does not implement.
- **In-pair Phase 6 evaluator vs reviewer 模块 external review**: the in-pair `peer_reviewer_agent` (Phase 6 evaluator with the v3.6.6 contract gate) and reviewer 模块 (Stage 3 5-panel external editorial review, `reference/reviewer.md`) serve different review layers and remain documented as known technical debt. Routing / merge decisions are deferred.

## Operational Modes (10 Modes)

See `../references/mode_selection_guide.md` for details.

| Mode                    | Trigger                                                          | Agents                       | Output                                                                                             |
| ----------------------- | ---------------------------------------------------------------- | ---------------------------- | -------------------------------------------------------------------------------------------------- |
| `full`                  | "Write a paper"                                                  | All 9 (+ 11 if quantitative) | Complete paper draft (with figures if applicable)                                                  |
| `outline-only`          | "Paper outline"                                                  | 1->2->3                      | Detailed outline + evidence map                                                                    |
| `revision`              | "Revise paper"                                                   | 8->5->6                      | Revised draft with tracked changes (uses `../templates/revision_tracking_template.md`)                |
| `abstract-only`         | "Write abstract"                                                 | 1->7                         | Bilingual abstract + keywords                                                                      |
| `lit-review`            | "Literature review"                                              | 1->2                         | Annotated bibliography + synthesis                                                                 |
| `format-convert`        | "Convert to LaTeX" / "Convert citations to [format]"             | 9 only                       | Formatted document; includes citation format conversion (APA 7 / Chicago / MLA / IEEE / Vancouver) |
| `citation-check`        | "Check citations"                                                | 6 only                       | Citation error report                                                                              |
| `plan`                  | "guide my paper" / "help me plan my paper"                       | 1->10->3->4                  | Chapter Plan + INSIGHT Collection                                                                  |
| `revision-coach`        | "parse reviews" / "revision roadmap" / "I got reviewer comments" | 12 only                      | Revision Roadmap + optional Tracking Template + Response Letter Skeleton                           |
| **`disclosure`** (v3.2) | **"AI disclosure for Nature" / "generate AI usage statement"**   | **9 only**                   | **Venue-specific AI-usage disclosure paragraph(s) + placement instructions**                       |

### Quick Mode Selection Guide

| Your Situation                                                     | Recommended Mode | Spectrum    |
| ------------------------------------------------------------------ | ---------------- | ----------- |
| Starting from scratch with a clear RQ                              | `full`           | balanced    |
| Need help planning before writing                                  | `plan`           | originality |
| Just need an outline                                               | `outline-only`   | balanced    |
| Have a draft, received review feedback                             | `revision`       | fidelity    |
| Have unstructured reviewer comments                                | `revision-coach` | balanced    |
| Just need an abstract                                              | `abstract-only`  | fidelity    |
| Need to check/fix citations                                        | `citation-check` | fidelity    |
| Need to convert format (LaTeX, DOCX) or citation style             | `format-convert` | fidelity    |
| Want a systematic literature review paper                          | `lit-review`     | fidelity    |
| Need a venue-specific AI-usage disclosure statement for submission | `disclosure`     | fidelity    |

**Spectrum** (v3.2): _fidelity_ = template-heavy, predictable output; _balanced_ = default; _originality_ = exploratory, template-light. （上游 ARS 的跨技能 spectrum 表 `shared/mode_spectrum.md` ⚠️ 依赖缺失，未随本套件发布；三档定义以本句为准。）

Not sure? Start with `plan` — it will guide you step by step. `disclosure` is a finishing step — run it after the paper is drafted, targeting the venue you plan to submit to.

### Mode Selection Logic

> See `../references/mode_selection_guide.md` for trigger-to-mode mappings and the full selection flowchart.

---

## Plan Mode: Chapter-by-Chapter Guided Planning

Socratic mode that guides users through paper planning one chapter at a time. Builds a complete Paper Blueprint through structured dialogue.

> See `../references/plan_mode_protocol.md` for the full chapter-by-chapter dialogue flow and Paper Blueprint structure.

---

## Handoff Protocol: search 模块 → paper 模块

`intake_agent` 自动检测 search 模块的产出物（Literature Corpus 文献清单 + 已下载的 Markdown 全文）并跳过冗余的检索步骤。完整交接格式（一个清单文件 + 每篇标题/来源/本地路径）见 [`search.md`](search.md) §「与其他模块的衔接」与 [`pipeline.md`](pipeline.md) § "Stage 1 Output Convention"。用户自备文献（未走 search 模块）时，`intake_agent` 按普通 existing-materials 流程收录。

---

## Failure Paths

See `../references/failure_paths.md` for details. Quick reference:

| Failure Scenario                           | Handling Strategy                                                  |
| ------------------------------------------ | ------------------------------------------------------------------ |
| Insufficient research foundation           | 先用 search 模块补检索（`reference/search.md`）                            |
| Wrong paper structure selected             | Return to Phase 2, suggest alternative structure                   |
| Word count significantly over/under target | Identify problematic chapters, suggest trimming/expansion          |
| Citation format entirely wrong             | Re-run the entire citation phase                                   |
| Peer review rejection                      | Analyze rejection reasons, suggest major revision or restructuring |
| Plan mode not converging                   | Suggest switching to outline-only mode                             |
| Incomplete handoff materials               | List missing items, suggest supplementing or re-running            |
| User abandons midway                       | Save completed Chapter Plan                                        |

---

## Full Academic Pipeline

See [`pipeline.md`](pipeline.md) for the complete workflow.

---

## Phase 0: Configuration Interview

See `../agents/intake_agent.md` for the complete field definitions of the Phase 0 configuration interview. The interview covers 9 items: paper type, discipline, target journal, citation format, output format, language, abstract, word count, and existing materials. Outputs a Paper Configuration Record, awaiting user confirmation.

---

## File Structure

**Agent definitions**: `../agents/{agent_name}.md` — one file per agent (12 total, matching Agent Team table above).

**References** (19 files in `../references/`):

- Citation: `apa7_extended_guide`, `apa7_chinese_citation_guide`, `citation_format_switcher`
- Writing: `academic_writing_style`, `writing_quality_check`, `writing_judgment_framework`
- Structure: `paper_structure_patterns` (6 types), `abstract_writing_guide`
- Domain: `hei_domain_glossary` (bilingual), `journal_submission_guide`, `latex_template_reference`
- Process: `failure_paths` (12 scenarios), `mode_selection_guide` (10 modes), `plan_mode_protocol`, `workflow_phase_details`
- Ethics: `credit_authorship_guide` (CRediT 14 roles), `funding_statement_guide`, `statistical_visualization_standards`
- Disclosure (v3.2): `disclosure_mode_protocol` (venue-specific AI-usage statement generation), `venue_disclosure_policies` (v1 database: ICLR, NeurIPS, Nature, Science, ACL, EMNLP)
- Also: `../references/apa7_extended_guide.md`（基础引用规范，本模块在其上扩展）

**Templates** (14 files in `../templates/`): `imrad`, `literature_review`, `case_study`, `theoretical_paper`, `policy_brief`, `conference_paper`, `bilingual_abstract`, `credit_statement`, `funding_statement`, `revision_tracking`（4 状态类型）, `peer_review_report`, `editorial_decision`, `revision_response`, `pipeline_status`。LaTeX 模板参考见 `../references/latex_template_reference.md`（上游独立 `latex_article_template.tex` ⚠️ 依赖缺失，未随本套件发布）。

**Examples** (9 files in `../examples/`): `imrad_hei_example`, `literature_review_example`, `plan_mode_guided_writing`, `chinese_paper_example`, `revision_mode_example`, `revision_recovery_example`, `clinical_citation_verification_checklist`, `clinical_epistemic_status_example`, `version_family_reconciliation_example`.

---

## Anti-Patterns

Explicit prohibitions to prevent common failure modes:

| #   | Anti-Pattern                           | Why It Fails                                                              | Correct Behavior                                                                                                     |
| --- | -------------------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| 1   | **AI-typical overused terms**          | "delve into", "crucial", "it is important to note" = instant AI detection | Use discipline-specific vocabulary; see `../references/writing_quality_check.md`                                        |
| 2   | **Em dash abuse**                      | More than 2 em dashes per page signals AI writing                         | Use parentheses, commas, or restructure the sentence                                                                 |
| 3   | **Throat-clearing openers**            | "In this section, we will discuss..." adds no information                 | Start with the claim or finding directly                                                                             |
| 4   | **Uniform paragraph lengths**          | Every paragraph is 4-5 sentences = monotonous AI rhythm                   | Vary paragraph length naturally (2-8 sentences)                                                                      |
| 5   | **⚠️ IRON RULE: Fabricated citations** | Inventing plausible-sounding references that don't exist                  | Every citation must be verified via DOI or WebSearch; see `../agents/integrity_verification_agent.md` |
| 6   | **Sycophantic revision**               | Accepting all reviewer feedback without critical evaluation               | Use REVIEWER_DISAGREE status when reviewer is wrong; justify with evidence                                           |
| 7   | **Scope creep during revision**        | Adding unrequested sections/analyses to "improve" the paper               | Revision addresses reviewer concerns only; new content requires explicit user approval                               |
| 8   | **Ignoring failure paths**             | Continuing despite desk-reject signals or fatal methodology flaws         | Check `../references/failure_paths.md`; invoke F11 Desk-Reject Recovery when triggered                                  |

---

## Quality Standards

### Writing Quality

1. **Every claim must have a citation** or be supported by the paper's own data
2. **Zero citation orphans** — in-text citations <-> reference list must perfectly match
3. **Consistent register** — academic tone appropriate for the discipline
4. **Logical flow** — clear transitions between paragraphs and sections
5. **Word count compliance** — within +/-10% of target

### Bilingual Abstract Quality

6. **Independent writing** — zh-TW and EN abstracts are independently composed, NOT mechanical translations
7. **Structural alignment** — both abstracts cover the same key points in the same order
8. **Keywords** — 5-7 per language, reflecting the paper's core concepts
9. **Word count** — EN: 150-300 words; zh-TW: 300-500 characters

### Citation Quality

10. **Format compliance** — 100% adherence to selected citation style
11. ⚠️ IRON RULE: **DOI inclusion** — every source with a DOI must include it; every citation must be verified via DOI or WebSearch
12. **Currency** — flag sources older than 10 years (unless seminal works)
13. **Self-citation ratio** — flag if >15%

### Peer Review

14. **Five dimensions** — Originality (20%), Methodological Rigor (25%), Evidence Sufficiency (25%), Argument Coherence (15%), Writing Quality (15%)
15. **Actionable feedback** — every criticism must include a specific suggestion
16. **Max 2 revision rounds** — unresolved items become Acknowledged Limitations

### Mandatory Inclusions

⚠️ **IRON RULE**: Every paper MUST include: Data Availability Statement, Ethics Declaration, Author Contributions (CRediT), Conflict of Interest Statement, Funding Acknowledgment. 17. **AI disclosure statement** — every paper must include a statement on AI tool usage 18. **Limitations section** — explicitly discuss study limitations 19. **Ethics statement** — when applicable (human subjects, sensitive data)

---

## Output Language

Follows the user's language. Academic terminology is kept in English. Bilingual abstracts are always provided regardless of the main text language.

---

## Integration with Other Modules

```
paper + search   -> 检索下载语料 -> 写作（Literature Corpus 自动交接，见 Handoff Protocol）
paper + reviewer -> 同行评审 -> 修订循环（Revision Roadmap 直接作为 revision 模式输入）
paper + pipeline -> 端到端编排（10 阶段含诚信审查与两阶段评审）
```

（上游 ARS 的外部组合 `tw-hei-intelligence` / `report-to-website` / `notebooklm-slides-generator` ⚠️ 依赖缺失，均未随本套件发布，当前版本不提供。）

---

## Version Info

| Item             | Content                                                                    |
| ---------------- | -------------------------------------------------------------------------- |
| Skill Version    | 3.11.0（套件统一版本；正文 `v3.2`–`v3.9.2` 等为上游 ARS 机制历史标注）       |
| Last Updated     | 2026-06-01                                                                 |
| Maintainer       | Cheng-I Wu                                                                 |
| Dependent Modules | 本套件 search 模块（upstream 语料）、reviewer 模块（downstream 评审）       |

---

## Version History

> See `../references/changelog-paper.md` for full version history.
