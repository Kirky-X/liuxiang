# Retrieval-Augmented Review Protocol（检索增强评审）

**Status**: v0.1（2026-10-01 新增，借鉴 zhu-minjun/Researcher 的 DeepReviewer Best Mode 两步法）
**Parent**: `../reference/reviewer.md`
**依赖**: search 模块的 `scripts/search_papers.py`（已随套件发布，无需新代码）

---

## 为什么需要这个协议

评审员最常见的误判有两类：把正确但表述陌生的方法判为缺陷（领域背景不足），以及漏掉已被后续研究推翻的关键主张（文献时效不足）。两者的根因相同——评审只看了稿子本身。检索增强评审在评审**之前**把外部证据拉进来：先由评审员提出"这篇稿子的可信度取决于哪些背景事实"，再检索验证，然后带着证据做评审。

上游 DeepReviewer 的验证结论（Best Mode 两步法）：先提 3 个背景核验问题 → 检索 → 带证据二次评审；检索失败时回退单轮评审，可行性已被验证。本协议采用同一形状。

## 何时启用

| 场景 | 是否启用 |
| --- | --- |
| `full` 模式，且论文声称 SOTA / 与已有工作矛盾 / 方法来自评审员不熟的子领域 | **启用（建议默认）** |
| `re-review` / `quick` / `methodology-focus` | 不启用（保持轻量；re-review 的核验对象是修订对照，不是外部文献） |
| `calibration` 模式 | 不启用（校准要求评审条件与被校准的基线一致） |
| 网络受限环境（search 模块报 `host_not_allowed`） | 自动回退单轮评审，并在报告中声明 |

## 两步流程

### Step 1 — 提出背景核验问题（评审前）

由 **`field_analyst_agent`**（主）、`methodology_reviewer_agent` 与 `domain_reviewer_agent`（辅）各提出 **2-3 个**背景核验问题。每个问题必须是**可用论文检索回答的事实性问题**，而不是观点：

- ✅ "论文声称 X 优于 Y——2023 年后是否有工作报告了与 X 相反的结果？"
- ✅ "论文使用的数据集 D，其官方标签质量评估结论是什么？"
- ❌ "这个方法的理论基础是否扎实？"（观点，检索回答不了）

问题产出为 `Retrieval Question Card`：

```
### Retrieval Question Card
- Q1: <事实性问题>（提出人: domain_reviewer；回答它影响哪些评审维度: literature coverage / soundness）
- Q2: ...
- Q3: ...
```

数量上限：**合计 ≤ 6 个问题**（与 calibration 的硬预算规则 6 同理念——检索是增强不是流水线，问题太多会把评审变成文献综述）。

### Step 2 — 检索证据（确定性脚本，不走模型）

用现成的 search 模块脚本逐题检索（脚本驱动、多源聚合、可复现）：

```bash
# 每题 1-2 次检索，多源聚合，取前 5 条判断相关性
python3 scripts/search_papers.py "<Q1 的检索词>" --source multi --limit 5 --json
# 需要引用关系佐证时（如"X 是否被后续工作推翻"）：
python3 scripts/citation_graph.py "<相关 DOI>" --direction citations
```

检索结果整理为 `Evidence Dossier`（每条含：标题/年份/来源/一句话相关性判定/链接），直接附在问题卡后。

**失败路径（必须显性化，规则 11）**：脚本检索失败（限流/无结果/网络策略禁止）时，在 Evidence Dossier 标注 `RETRIEVAL_FAILED: <原因>`，评审继续但报告的 Limitations 节必须声明"以下判断未经外部证据核验"。**禁止**编造检索结果，禁止假装检索过。

### Step 3 — 带证据评审

Phase 1 各评审员的 prompt 前注入 Evidence Dossier。约束：

1. **证据改变判断必须留痕**：评审员因证据升降级的每一条意见，标注 `evidence-backed`（引用 Dossier 条目）或 `revised-by-evidence`（说明原判断是什么、证据为何推翻它）。
2. **证据不改变独立评审铁律**：各评审员仍独立评审（Checkpoint Rule #2），Dossier 是共享输入，评审结论不得互相引用。
3. **未被证据支持的反驳降级**：Devil's Advocate 的反驳若与 Dossier 中的证据直接冲突，须在意见中列出冲突并说明采信哪边的理由——"Pressure is not evidence" 同样适用于评审员自己。
4. Issue ID 照常铸造（`<SOURCE>-<NN>`），evidence-backed 的意见在 issue 条目中加 `Evidence: <Dossier 条目>` 字段。

## 与其他协议的关系

| 协议 | 关系 |
| --- | --- |
| `integrity_verification_agent`（Stage 2.5/4.5） | 互补：integrity 核对**稿内**引用真实性，本协议核对外部证据与稿子主张的一致性 |
| `claim_verification_protocol` | 本协议的 Evidence Dossier 可作为其 Phase "source tracing" 的输入语料 |
| `calibration_mode_protocol` | 不叠加（校准要求条件与基线一致） |
| pipeline Stage 3 | orchestrator 在调度 reviewer 模块前，若启用本协议，先完成 Step 1/2 再派发评审员 |

## 硬预算上限（不可自动绕过）

- 背景核验问题合计 ≤ 6；每题检索调用 ≤ 2 次（search + citation_graph 各算 1 次）。
- 超出必须获得用户显式批准并在会话中记录；orchestrator 不得以"证据更充分"为由自行扩预算。
