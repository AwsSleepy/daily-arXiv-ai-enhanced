# Implementation Plan

> 基于 [docs/specs/SPEC.md](../docs/specs/SPEC.md)，将 robotics daily arXiv 改造拆分为 6 个可独立验证的任务。

---

## 依赖图

```
Task 1: Fork & Configure
   │
   └──▶ Task 2: Config + Filter Core
            │
            ├──▶ Task 3: Filter CI Integration
            │
            └──▶ Task 4: Push Core
                     │
                     └──▶ Task 5: Push CI Integration
                              │
                              └──▶ Task 6: Polish & Verify
```

---

## Task 1: Fork & Baseline Verification

**目标：** Fork 仓库并配通基础流程（爬取 + AI 摘要 + Pages），确认现有链路可用。

**前置依赖：** 无

### 1.1 Fork 仓库
- 在 GitHub 上将 `dw-dengwei/daily-arXiv-ai-enhanced` fork 到个人账户
- Clone fork 到本地

### 1.2 配置 Secrets
- Settings → Secrets and variables → Actions → Secrets
- 新增 `OPENAI_API_KEY`：DeepSeek API Key
- 新增 `OPENAI_BASE_URL`：DeepSeek API Base URL
- （后续才需要 `WECHAT_WEBHOOK_URL`，现在先不配）

### 1.3 配置 Variables
- Settings → Secrets and variables → Actions → Variables
- `CATEGORIES`: `cs.RO, cs.AI, cs.LG, cs.CV`
- `LANGUAGE`: `Chinese`
- `MODEL_NAME`: `deepseek-chat`
- `EMAIL`: GitHub 邮箱
- `NAME`: GitHub 用户名

### 1.4 手动触发验证
- Actions → arXiv-daily-ai-enhanced → Run workflow
- 等待完成（预计 30-60 分钟）
- 验证：GitHub Pages 可访问，有新论文数据

### 1.5 开启 GitHub Pages
- Settings → Pages → Source: `Deploy from a branch` → Branch: `main` / `(root)`

### 验收标准
- [ ] Workflow 手动触发后全部 steps 绿勾
- [ ] `https://<username>.github.io/daily-arXiv-ai-enhanced/` 可访问
- [ ] 网页上有今日论文，AI 摘要正常显示

### 涉及文件
无代码变更，纯配置操作。

---

## Task 2: Config + AI Filter 核心实现

**目标：** 创建子方向配置文件和 AI 过滤模块，本地跑通过滤流程。

**前置依赖：** Task 1 完成（需要数据库中有 AI 增强后的 jsonl 文件用于测试）

### 2.1 创建 `config/topics.yaml`
- 新建 `config/` 目录
- 将 SPEC 中定义的全部 topics + watched 配置写入 `config/topics.yaml`
- 7 个 topics：`vla`, `wam`, `navigation`, `motion-planning`, `physics-motion`, `whole-body-control`, `other`
- 完整的 `watched.labs`（~50 个组）和 `watched.authors`（~40 人）

### 2.2 创建 `ai/filter_structure.py`
- 定义 Pydantic 模型 `RelevanceFilter`：
  ```python
  class RelevanceFilter(BaseModel):
      is_relevant: bool
      matched_topics: List[str]
      from_watchlist: bool
      confidence: float
      reason: str
  ```
- 参考已有 `ai/structure.py` 的模式

### 2.3 实现 `ai/filter.py`
- 实现 `load_config(path)` — 加载 topics.yaml
- 实现 `stage1_watchlist_match(paper, config)` — 零 LLM 成本字符串匹配
  - 对每个 paper 的 `authors` 字段检查是否命中 `watched.authors[*].name`
  - 对每个 paper 的全文检查是否命中 `watched.labs[*].keywords`
- 实现 `stage2_llm_filter(paper, config, model)` — LLM 分类
  - 用 `ChatOpenAI.with_structured_output(RelevanceFilter)`
  - Prompt 涉及 topic_definitions + watched_context + 论文信息
- 实现 `process_all_items(data, config, model_name, max_workers)` — 并行处理
  - 复用 `ai/enhance.py` 的 ThreadPoolExecutor 模式
- 实现 `main()` — argparse CLI
  - `--data`：AI 增强后的 jsonl 文件
  - `--topics`：topics.yaml 路径
  - `--max-workers`：并行数

### 2.4 本地测试
- 从 GitHub Pages 或 data 分支下载一份已有的 `_AI_enhanced_Chinese.jsonl`
- 运行 `python ai/filter.py --data data/2026-XX-XX_AI_enhanced_Chinese.jsonl --topics config/topics.yaml`
- 检查：
  - `data/{date}_filtered.jsonl` 正确生成
  - 阶段 1 匹配的论文 `from_watchlist=true`，无需 LLM 调用
  - 相关论文被正确标记

### 验收标准
- [ ] `config/topics.yaml` 语法有效（YAML 可解析）
- [ ] `filter_structure.py` 模型与 SPEC 定义一致
- [ ] `filter.py --data xxx --topics xxx` 本地无报错运行完成
- [ ] 输出 `_filtered.jsonl` 每行包含完整的 `AI.is_relevant`, `AI.matched_topics`, `AI.from_watchlist`, `AI.confidence`, `AI.reason`
- [ ] 阶段 1 命中的论文不计入 LLM 调用（log 验证）

### 涉及文件
```
🆕 config/topics.yaml
🆕 ai/filter_structure.py
🆕 ai/filter.py
```

---

## Task 3: Filter 接入 GitHub Actions

**目标：** 修改 workflow，在 AI Enhancement 之后自动执行过滤。

**前置依赖：** Task 2 完成

### 3.1 修改 `.github/workflows/run.yml`
- 在 "AI Enhancement Processing" step 之后插入新 step：

```yaml
- name: AI Relevance Filtering
  if: steps.dedup_check.outputs.has_new_content == 'true'
  run: |
    source .venv/bin/activate
    today=${{ steps.crawl_step.outputs.crawl_date }}
    cd ai
    python filter.py \
      --data ../data/${today}_AI_enhanced_${LANGUAGE}.jsonl \
      --topics ../config/topics.yaml
```

### 3.2 确保依赖可用
- `pyproject.toml` 已有 `pyyaml`？检查一下，如果没有就加上
- `ai/filter.py` import 的模块都在 `pyproject.toml` 依赖中

### 3.3 手动触发验证
- Push Task 2 + Task 3 的改动到 fork 的 main 分支
- 手动触发 workflow
- 验证 filter step 绿勾
- 下载 artifact 或查看 data 分支确认 `_filtered.jsonl` 已生成

### 验收标准
- [ ] Workflow 中 "AI Relevance Filtering" step 绿勾
- [ ] data 分支存在 `{date}_filtered.jsonl`
- [ ] filtered.jsonl 内容正确（抽样检查几篇）

### 涉及文件
```
✏️ .github/workflows/run.yml       # 新增一个 step
✏️ pyproject.toml                  # 可能需要加 pyyaml 依赖
```

---

## Task 4: 微信推送模块核心实现

**目标：** 实现推送模块，本地 dry-run 验证消息格式。

**前置依赖：** Task 2 完成（需要 filtered.jsonl 作为输入）

### 4.1 创建 `push/__init__.py`
- 空文件，标记为 Python package

### 4.2 创建 `push/base.py`
- 定义 `AbstractPushChannel(ABC)` 抽象基类
- `send(papers: List[Dict], date: str) -> bool`
- `channel_name() -> str`

### 4.3 创建 `push/formatter.py`
- `group_by_topic(papers)` — 按 `matched_topics` 分组，一篇论文可出现在多个组
- `sort_by_priority(papers)` — 先按 `from_watchlist` 降序，再按 `confidence` 降序
- `build_topic_section(topic_name, papers, top_n=5)` — 单个 topic 的 Markdown 段落
- `build_wecom_messages(papers, date)` — 企业微信 Markdown 消息，超 4096 字节自动分段
- `build_text_digest(papers, date)` — 纯文本摘要（PushPlus 用）
- 消息格式遵循 SPEC 中定义：⭐ 标记关注列表论文，底部统计

### 4.4 创建 `push/wechat.py`
- 实现 `WeChatPushChannel(AbstractPushChannel)`
- `_send_wecom(papers, date)` — 企业微信机器人 webhook
- `_send_pushplus(papers, date)` — PushPlus API
- `_send_serverchan(papers, date)` — Server 酱 API（预留）

### 4.5 创建 `push/main.py`
- argparse CLI：`--data`, `--dry-run`
- 读取 filtered jsonl
- 按 channel 发送
- dry-run 模式：只打印消息内容，不实际发送

### 4.6 本地测试
```bash
python push/main.py --data data/2026-XX-XX_filtered.jsonl --dry-run
```
- 验证消息格式、分组、排序
- 验证长消息自动分段
- 验证 ⭐ 标记正确

### 验收标准
- [ ] `python push/main.py --dry-run` 无报错运行
- [ ] 输出消息 Markdown 渲染后格式正确
- [ ] 超 4096 字节消息正确分段（每段 < 4096）
- [ ] 关注列表论文带 ⭐ 标记
- [ ] 每个 topic 最多 `PUSH_TOP_N` 篇

### 涉及文件
```
🆕 push/__init__.py
🆕 push/base.py
🆕 push/formatter.py
🆕 push/wechat.py
🆕 push/main.py
```

---

## Task 5: 推送接入 GitHub Actions

**目标：** 配置微信 webhook，每天推送经过滤的论文摘要到微信。

**前置依赖：** Task 3 + Task 4 完成

### 5.1 配置微信 Webhook
- 方案 A（推荐）：企业微信 → 创建群机器人 → 获取 Webhook URL
- 方案 B：PushPlus → 获取 token
- 将 Webhook URL/Token 配入 GitHub Secrets：
  - `WECHAT_WEBHOOK_URL`（wecom_bot 方案）
  - 或 `PUSH_WECHAT_METHOD=pushplus` + `PUSH_WECHAT_KEY=xxx`

### 5.2 修改 `.github/workflows/run.yml`
- 在 Markdown 转换 step 之后插入：

```yaml
- name: Push to WeChat
  if: steps.dedup_check.outputs.has_new_content == 'true'
  run: |
    source .venv/bin/activate
    today=${{ steps.crawl_step.outputs.crawl_date }}
    export WECHAT_WEBHOOK_URL="${{ secrets.WECHAT_WEBHOOK_URL }}"
    export PUSH_WECHAT_METHOD="${{ vars.PUSH_WECHAT_METHOD }}"
    export PUSH_WECHAT_KEY="${{ secrets.PUSH_WECHAT_KEY }}"
    cd push
    python main.py --data ../data/${today}_filtered.jsonl
```

### 5.3 手动触发验证
- Push 改动，手动触发 workflow
- 等待 "Push to WeChat" step 完成
- **验证：微信收到论文推送消息**

### 验收标准
- [ ] "Push to WeChat" step 绿勾
- [ ] 微信收到每日论文推送
- [ ] 消息格式正确，⭐ 标记关注列表
- [ ] （如论文多）消息正确分段

### 涉及文件
```
✏️ .github/workflows/run.yml       # 新增 push step
```

---

## Task 6: 收尾验证 & 优化

**目标：** 端到端验证 + 过滤质量抽检 + prompt 微调。

**前置依赖：** Task 5 完成

### 6.1 过滤质量抽样
- 随机抽 20 篇被标记为 `is_relevant=true` 的论文
- 人工判断是否确实相关（precision）
- 随机抽 20 篇被标记为 `is_relevant=false` 的论文
- 人工判断是否有漏网之鱼（recall）
- 记录准确率，决定是否需要调整 prompt 或 topic keywords

### 6.2 Prompt 微调
- 如果 precision 低 → 在 prompt 中收紧匹配标准
- 如果 recall 低 → 放宽 topic keywords 或降低 `PUSH_MIN_CONFIDENCE`
- 如果某个 topic 论文过多/过少 → 调整该 topic 的 keywords

### 6.3 最终端到端验证
- 完整跑一次 workflow
- 验证：
  - 爬取 → 去重 → 摘要 → 过滤 → Markdown → Pages → 微信推送 全链路
  - 无 step 失败
  - 微信推送内容与网页一致

### 验收标准
- [ ] 全链路端到端跑通
- [ ] 过滤 precision > 80%（主观评估）
- [ ] 无因配置/代码错误导致的 workflow 失败
- [ ] `tasks/plan.md` 全部任务打勾

### 涉及文件
```
✏️ config/topics.yaml              # 可能微调 keywords
✏️ ai/filter.py                    # 可能微调 prompt
```

---

## 时间估算

| Task | 预计时间 |
|------|---------|
| Task 1: Fork & Configure | 0.5h |
| Task 2: Config + Filter Core | 1.5h |
| Task 3: Filter CI Integration | 0.5h |
| Task 4: Push Core | 1.5h |
| Task 5: Push CI Integration | 0.5h |
| Task 6: Polish & Verify | 0.5h |
| **合计** | **~5h** |

---

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| DeepSeek API 限流导致 AI 摘要失败 | `enhance.py` 已有 retry，filter 也加 try/except |
| cs.CV 某天论文暴增（CVPR 截稿日） | filter 阶段 1 先筛一遍，减少 LLM 调用量 |
| 企业微信 webhook 推送失败 | 代码已 try/except，单个 channel 失败不影响其他 |
| GitHub Actions 超时（6h 限制） | 预估 30-60min，远低于上限 |

---

*最后更新：2026-06-21*
