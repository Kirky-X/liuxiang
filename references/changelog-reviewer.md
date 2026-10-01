# Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.5 | 2026-10-01 | **检索增强评审（liuxiang v0.1，借鉴 zhu-minjun/Researcher DeepReviewer 两步法）**: 新增 `review_retrieval_protocol.md`——full 模式评审前由 field_analyst（主）+ methodology/domain reviewer 各提 2-3 个背景核验问题（合计 ≤6），search_papers.py / citation_graph.py 脚本检索 Evidence Dossier，带证据评审；检索失败显性回退单轮并在 Limitations 声明。**校准基建清偿**: `scripts/test_claim_audit_calibration.py` + 金标 fixture 落地（原 claim_audit_calibration_protocol.md 自述缺失清偿），T-C1/T-C2/T-C3 契约可离线运行。**阶段门禁**: issue-ids / rr-matrix 子命令接入评审产物校验 |
| 1.4 | 2026-03-08 | Quality rubrics reference (0-100 scoring with 5 descriptors per dimension, weighted aggregation formula, decision mapping); Quick Mode Selection Guide; Dimension Scores upgraded from optional 1-5 to required 0-100 with rubric descriptors |
| 1.3 | 2026-03-05 | DA vs R3 role boundaries with explicit responsibility tables; CRITICAL finding criteria with concrete examples; Consensus classification (CONSENSUS-4/3/SPLIT/DA-CRITICAL); Confidence Score weighting rules; Asian & Regional Journals reference (TSSCI + Asia-Pacific + OA options) |
| 1.2 | 2026-03 | Added statistical reporting standards reference; enhanced methodology_reviewer_agent with statistical reporting adequacy sub-step |
| 1.1 | 2026-02 | Added Devil's Advocate Reviewer (7th agent), added re-review mode, expanded review team from 4 to 5 |
| 1.0 | 2026-02 | Initial version: 6 agents, 4 modes, 3-phase workflow |
