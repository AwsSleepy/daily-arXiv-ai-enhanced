# Task List

> Robotics Daily arXiv 改造。详情见 [plan.md](plan.md)

---

## 🔴 Phase 1: 基础配置

- [ ] **Task 1** — Fork & Baseline Verification
  - [ ] 1.1 Fork 仓库到个人 GitHub
  - [ ] 1.2 配置 Secrets: `OPENAI_API_KEY`, `OPENAI_BASE_URL`
  - [ ] 1.3 配置 Variables: `CATEGORIES`, `LANGUAGE`, `MODEL_NAME`, `EMAIL`, `NAME`
  - [ ] 1.4 手动触发 workflow，验证爬取+摘要+Pages 全链路
  - [ ] 1.5 确认 GitHub Pages 可访问
  > **Checkpoint: 基础链路跑通，网页可见论文**

---

## 🟡 Phase 2: AI 过滤

- [ ] **Task 2** — Config + Filter 核心实现
  - [ ] 2.1 创建 `config/topics.yaml`（7 topics + watched）
  - [ ] 2.2 创建 `ai/filter_structure.py`（Pydantic 模型）
  - [ ] 2.3 实现 `ai/filter.py`（两阶段过滤 + 并行处理）
  - [ ] 2.4 本地用已有数据测试过滤效果
  > **Checkpoint: filter.py 本地跑通，_filtered.jsonl 正确生成**

- [ ] **Task 3** — Filter 接入 CI
  - [ ] 3.1 检查/补充 `pyproject.toml` 依赖（pyyaml）
  - [ ] 3.2 修改 `.github/workflows/run.yml` 新增 filter step
  - [ ] 3.3 手动触发验证 CI 中 filter step 绿勾
  > **Checkpoint: GitHub Actions 自动生成 filtered.jsonl**

---

## 🟢 Phase 3: 微信推送

- [ ] **Task 4** — Push 核心实现
  - [ ] 4.1 创建 `push/__init__.py`
  - [ ] 4.2 创建 `push/base.py`（AbstractPushChannel）
  - [ ] 4.3 创建 `push/formatter.py`（分组/排序/格式化/分段）
  - [ ] 4.4 创建 `push/wechat.py`（企业微信 + PushPlus）
  - [ ] 4.5 创建 `push/main.py`（CLI + dry-run）
  - [ ] 4.6 本地 dry-run 验证消息格式
  > **Checkpoint: dry-run 输出正确的微信消息格式**

- [ ] **Task 5** — Push 接入 CI
  - [ ] 5.1 获取/配置微信 webhook（企业微信机器人 或 PushPlus）
  - [ ] 5.2 添加 GitHub Secrets: `WECHAT_WEBHOOK_URL`
  - [ ] 5.3 修改 `.github/workflows/run.yml` 新增 push step
  - [ ] 5.3 手动触发验证微信实际收到推送
  > **Checkpoint: 微信每日收到论文推送 ⭐**

---

## 🔵 Phase 4: 收尾

- [ ] **Task 6** — 验证 & 微调
  - [ ] 6.1 过滤质量抽样（precision / recall）
  - [ ] 6.2 Prompt / keywords 微调
  - [ ] 6.3 最终端到端验证全链路
  > **Checkpoint: 全链路稳定运行，过滤质量达标**

---

**状态：** 🔴 Phase 1 未开始
