# Robotics Daily arXiv — Specification

> 基于 daily-arXiv-ai-enhanced 改造，面向 Robotics 领域（VLA、World Action Model、Navigation、Motion Planning、Physics-based Motion Mimic & Interaction、Whole Body Control）的每日论文抓取、AI 过滤与多渠道推送系统。

---

## 1. 目标与范围

### 1.1 目标

每日自动从 arXiv 抓取 Robotics 相关论文，通过 LLM 对论文进行：
1. **结构化摘要**（TLDR / motivation / method / result / conclusion）
2. **相关性判定**（根据用户定义的关键词判断是否属于目标子方向）
3. **多渠道推送**（GitHub Pages 网页 + 微信推送，后续可选扩展飞书/钉钉）

### 1.2 不做的事

- 不构建后端 API 服务——完全依赖 GitHub Actions + Pages
- 不做全文翻译或深度解读——只做摘要 + 分类
- 不爬取付费论文或绕过 arXiv 限制
- 不存储用户数据——前端偏好存 localStorage

### 1.3 目标用户

- 本人（Robotics 研究者），需要每日跟踪特定子方向的新论文
- 可扩展到同实验室/团队其他人订阅

---

## 2. 架构概览

### 2.1 整体流程

```
┌─────────────┐    ┌──────────┐    ┌───────────────┐
│ Scrapy 爬取  │───▶│ 7 天去重  │───▶│ AI 结构化摘要   │
│ (4 个分类)   │    │          │    │ (DeepSeek)     │
└─────────────┘    └──────────┘    └───────┬───────┘
                                           │
                    ┌──────────────────────┘
                    ▼
          ┌─────────────────┐
          │ AI 相关性过滤      │  ◀── 新增模块
          │ (topic config)   │
          └───────┬─────────┘
                  │
      ┌───────────┴───────────┐
      ▼                       ▼
┌───────────┐         ┌──────────────┐
│ Markdown  │         │  微信推送       │  ◀── 新增模块
│ → Pages   │         │ (支持扩展)      │
└───────────┘         └──────────────┘
```

### 2.2 arXiv 分类选择

| 分类 | 理由 | 预计日增量 |
|------|------|-----------|
| `cs.RO` | Robotics 主分类，覆盖全部子方向 | 30-60 篇 |
| `cs.CV` | VLA 的视觉部分 / physics-based motion 的视觉感知 | 80-120 篇 |
| `cs.AI` | VLA / World Action Model 的 AI 方法部分 | 40-80 篇 |
| `cs.LG` | Physics-based motion mimic 等 learning-based 方法 | 60-100 篇 |
| **合计** | — | **~200-350 篇/天** |

> ⚠️ 每天 200-350 篇原始数据，LLM 摘要成本约 **1-2 元/天**（按 DeepSeek 价格），需确认可接受。

---

## 3. 模块规格

### 3.1 子方向配置 `config/topics.yaml`

定义用户关注的 Robotics 子方向，作为 AI 过滤的依据。

```yaml
topics:
  - id: vla
    name: "VLA (Vision-Language-Action)"
    description: >
      视觉-语言-动作模型，将视觉感知和自然语言指令映射为机器人动作。
      包括但不限于：RT-1/RT-2/RT-X, PALM-E, Octo, OpenVLA, π0 等模型。
    keywords:
      - vision-language-action
      - VLA
      - visuomotor
      - instruction following
      - language-conditioned manipulation
      - robot foundation model
      - generalist robot policy
      - embodied agent

  - id: wam
    name: "World Action Model (WAM)"
    description: >
      世界动作模型，学习预测动作在环境中的后果。核心是做 world model 与 action 的结合——
      给定当前观测和动作，预测未来状态/视频帧，用于机器人规划和决策。
      包括但不限于：视频生成式 world model、action-conditioned video prediction、
      基于 world model 的 planning/RL、Genie/UniSim 等。
    keywords:
      - world model
      - world action model
      - action-conditioned video prediction
      - video generation for planning
      - model-based reinforcement learning
      - learned dynamics model
      - latent world model
      - predictive model
      - future state prediction
      - video prediction
      - Genie
      - UniSim
      - Dreamer
      - observation prediction
      - forward dynamics

  - id: navigation
    name: "Robot Navigation"
    description: >
      机器人导航，包括视觉导航、语义导航、社交导航、SLAM 等。
    keywords:
      - visual navigation
      - autonomous navigation
      - SLAM
      - path planning
      - exploration
      - semantic navigation
      - social navigation
      - mapless navigation
      - point-goal navigation
      - object-goal navigation

  - id: motion-planning
    name: "Motion Planning"
    description: >
      运动规划，包括轨迹优化、采样规划、强化学习运动规划等。
    keywords:
      - motion planning
      - trajectory optimization
      - path planning
      - sampling-based planning
      - optimization-based planning
      - kinodynamic planning
      - motion primitive

  - id: physics-motion
    name: "Physics-based Motion Mimic & Interaction"
    description: >
      基于物理的角色运动模仿与交互，源自 Xuebin (Jason) Peng 等人的工作线
      （DeepMimic, ASE, AMP, ASE 等）及其衍生方向。
      核心关注：(1) 物理仿真中的运动模仿/跟踪——从 mocap 数据学习控制策略；
      (2) sim-to-real 迁移；(3) 角色动画与人体运动合成；
      **特别关注：与物体/环境交互的动作 mimic——角色在模仿运动的同时与物体交互
      （如搬运、推开、抓取等物理交互行为）。**
      涉及平台：Isaac Gym, Isaac Sim, MuJoCo 等。
    keywords:
      - DeepMimic
      - motion imitation
      - motion tracking
      - physics-based animation
      - physics-based character animation
      - motion capture
      - physics simulation
      - reinforcement learning locomotion
      - sim-to-real
      - Isaac Gym
      - Isaac Sim
      - MuJoCo
      - adversarial motion prior
      - AMP
      - object interaction
      - physical interaction
      - character-object interaction
      - whole-body manipulation
      - physics-based grasping
      - contact-rich motion
      - humanoid motion synthesis
      - human motion reconstruction
      - kinematic tracking
      - real-time motion tracking
      - physics-based motion generation

  - id: whole-body-control
    name: "Whole Body Control"
    description: >
      全身控制，包括全身运动控制、全身 MPC、人形机器人全身控制、接触感知控制。
    keywords:
      - whole-body control
      - whole-body MPC
      - model predictive control
      - locomotion control
      - balance control
      - humanoid control
      - bipedal locomotion
      - quadrupedal locomotion
      - contact-aware control
      - operational space control
      - task-space control
      - hierarchical control

  - id: other
    name: "Other Relevant Robotics"
    description: >
      其他值得关注的机器人学论文，包括但不限于：强化学习用于机器人、
      机器人操作、灵巧手、具身智能等未涵盖在上述方向中的重要工作。
    keywords:
      - reinforcement learning
      - imitation learning
      - learning from demonstration
      - robot manipulation
      - embodied AI
      - robotic grasping
      - sim-to-real transfer
      - domain randomization
      - teleoperation

# ──────────────────────────────────────
# 关注列表：名组/大厂/名作者
# 命中即标记为 relevant，不必同时命中 topic 关键词
# ──────────────────────────────────────
watched:
  # ── 国际大厂 robotics 团队 ──
  labs:
    - name: "NVIDIA GEAR Lab"
      description: "Jim Fan / Yuke Zhu 组，VLA、robot foundation model、simulation"
      keywords:
        - Jim Fan
        - Yuke Zhu
        - GEAR Lab
        - NVIDIA Robotics
    - name: "Google DeepMind Robotics"
      description: "RT 系列、Gemini Robotics、VLA"
      keywords:
        - Google DeepMind
        - DeepMind
        - RT-1
        - RT-2
        - RT-X
        - Gemini Robotics
        - Robotics at Google
    - name: "Meta FAIR / Embodied AI"
      description: "Meta AI robotics, embodied agents"
      keywords:
        - Meta AI
        - Facebook AI Research
        - FAIR
        - Meta Robotics
    - name: "OpenAI Robotics"
      description: "OpenAI 机器人相关"
      keywords:
        - OpenAI
    - name: "Apple Robotics / MLR"
      description: "Apple 机器人/具身智能研究"
      keywords:
        - Apple Robotics
        - Apple MLR
    - name: "Amazon Robotics"
      description: "Amazon 仓储/物流机器人"
      keywords:
        - Amazon Robotics
        - Amazon Science
    - name: "Microsoft Research"
      description: "MSR robotics"
      keywords:
        - Microsoft Research
        - MSR

  # ── 国际知名高校 robotics 组 ──
    - name: "Stanford IRIS / SVL / ILIAD"
      description: "Stanford robotics labs"
      keywords:
        - Stanford Vision
        - Stanford IRIS
        - Stanford SVL
        - Stanford ILIAD
        - Fei-Fei Li
        - Chelsea Finn
        - Dorsa Sadigh
        - Jeannette Bohg
        - Shuran Song
    - name: "MIT CSAIL / Improbable AI"
      description: "MIT robotics & RL"
      keywords:
        - MIT CSAIL
        - Improbable AI
        - Pulkit Agrawal
        - Leslie Kaelbling
        - Tomas Lozano-Perez
        - Russ Tedrake
    - name: "CMU Robotics Institute"
      description: "CMU robotics, manipulation, locomotion"
      keywords:
        - Carnegie Mellon
        - CMU Robotics
        - CMU Robotics Institute
        - Deepak Pathak
        - Abhinav Gupta
        - Katerina Fragkiadaki
        - David Held
        - Matthew Johnson-Roberson
    - name: "UC Berkeley BAIR / RAIL"
      description: "Berkeley robotics & RL"
      keywords:
        - UC Berkeley
        - BAIR
        - RAIL Lab
        - Sergey Levine
        - Pieter Abbeel
        - Ken Goldberg
        - Jitendra Malik
    - name: "UPenn GRASP Lab"
      description: "UPenn robotics"
      keywords:
        - UPenn GRASP
        - GRASP Lab
        - Vijay Kumar
        - Dinesh Jayaraman
    - name: "Georgia Tech"
      description: "Georgia Tech robotics & RL"
      keywords:
        - Georgia Institute of Technology
        - Georgia Tech
        - Animesh Garg
        - Seth Hutchinson
        - Sonia Chernova
    - name: "UT Austin"
      description: "UT Austin robotics"
      keywords:
        - UT Austin
        - Texas Robotics
        - Peter Stone
        - Scott Niekum
        - Yuke Zhu
    - name: "NYU / NYU Courant"
      description: "NYU robotics"
      keywords:
        - New York University
        - NYU Robotics
        - Lerrel Pinto
    - name: "UIUC"
      description: "UIUC robotics"
      keywords:
        - UIUC
        - Illinois Robotics
        - Saurabh Gupta
    - name: "Oxford Robotics Institute"
      description: "Oxford robotics"
      keywords:
        - Oxford Robotics Institute
        - ORI
        - Ingmar Posner
        - Nick Hawes
    - name: "Imperial College London"
      description: "Imperial robotics"
      keywords:
        - Imperial College
        - Imperial Robotics
        - Edward Johns
    - name: "ETH Zurich / UZH Robotics"
      description: "ETH/UZH robotics, legged locomotion, control"
      keywords:
        - ETH Zurich
        - ETH AI Center
        - UZH Robotics
        - Marco Hutter
        - Stelian Coros
        - Robert Katzschmann
    - name: "TU Munich / TU Darmstadt"
      description: "TUM/TU Darm robotics"
      keywords:
        - TU Munich
        - TU Darmstadt
        - Georgia Chalvatzaki
        - Jan Peters
    - name: "University of Washington"
      description: "UW robotics & RL"
      keywords:
        - University of Washington
        - UW Robotics
        - Dieter Fox
        - Byron Boots
        - Abhishek Gupta

  # ── 国际机器人公司 ──
    - name: "Boston Dynamics"
      description: "Atlas, Spot, 全身控制"
      keywords:
        - Boston Dynamics
        - Scott Kuindersma
    - name: "Tesla / Tesla Optimus"
      description: "人形机器人 Optimus"
      keywords:
        - Tesla Bot
        - Tesla Optimus
    - name: "Figure AI"
      description: "人形机器人 Figure"
      keywords:
        - Figure AI
        - Figure Robotics
    - name: "1X Technologies"
      description: "人形机器人 NEO"
      keywords:
        - 1X Technologies
        - 1X Robotics
    - name: "Toyota Research Institute"
      description: "TRI robotics"
      keywords:
        - Toyota Research Institute
        - TRI
    - name: "Agility Robotics"
      description: "Digit 人形机器人"
      keywords:
        - Agility Robotics
    - name: "Sanctuary AI"
      description: "Phoenix 人形机器人"
      keywords:
        - Sanctuary AI
    - name: "Apptronik"
      description: "Apollo 人形机器人"
      keywords:
        - Apptronik

  # ── 中国大厂 robotics 团队 ──
    - name: "华为 Noah's Ark / 具身智能"
      description: "华为机器人研究、具身智能、自动驾驶"
      keywords:
        - Huawei
        - 华为
        - Noah's Ark
        - 华为诺亚
    - name: "腾讯 Robotics X"
      description: "腾讯机器人实验室，灵巧手、四足、移动操作"
      keywords:
        - Tencent Robotics X
        - 腾讯 Robotics X
        - 腾讯机器人
    - name: "阿里巴巴 / 达摩院"
      description: "阿里达摩院机器人、具身智能"
      keywords:
        - Alibaba
        - 阿里巴巴
        - 达摩院
        - Damo Academy
    - name: "百度 / 百度机器人"
      description: "百度具身智能、自动驾驶 Apollo、飞桨"
      keywords:
        - Baidu
        - 百度
        - Baidu Research
    - name: "字节跳动 / ByteDance Research"
      description: "字节 AI/机器人研究"
      keywords:
        - ByteDance
        - 字节跳动
        - ByteDance Research
    - name: "小米 / Xiaomi Robotics"
      description: "小米 CyberOne/CyberDog 机器人"
      keywords:
        - Xiaomi
        - 小米
        - CyberOne
        - CyberDog
    - name: "美团 / 美团无人机"
      description: "美团无人配送、无人机"
      keywords:
        - Meituan
        - 美团

  # ── 中国机器人初创公司 ──
    - name: "宇树科技 / Unitree"
      description: "四足/人形机器人，H1/G1/B2"
      keywords:
        - Unitree
        - 宇树
        - Unitree Robotics
    - name: "智元机器人 / Agibot"
      description: "人形机器人，稚晖君"
      keywords:
        - Agibot
        - 智元
        - 智元机器人
    - name: "星尘智能 / Astribot"
      description: "人形机器人"
      keywords:
        - Astribot
        - 星尘智能
    - name: "傅利叶智能 / Fourier Intelligence"
      description: "通用人形机器人 GR 系列"
      keywords:
        - Fourier Intelligence
        - 傅利叶
        - Fourier GR
    - name: "优必选 / UBTech"
      description: "人形机器人 Walker"
      keywords:
        - UBTech
        - 优必选
        - Walker Robot
    - name: "银河通用 / Galbot"
      description: "通用机器人，embodied AI"
      keywords:
        - Galbot
        - 银河通用
    - name: "星海图 / 星海图智能"
      description: "具身智能"
      keywords:
        - 星海图
        - 星海图智能
    - name: "地平线 / Horizon Robotics"
      description: "机器人芯片、具身智能计算平台"
      keywords:
        - Horizon Robotics
        - 地平线
        - 地平线机器人
    - name: "云深处 / Deep Robotics"
      description: "四足机器人"
      keywords:
        - Deep Robotics
        - 云深处
    - name: "小鹏鹏行 / XPeng Robotics"
      description: "小鹏机器人/自动驾驶"
      keywords:
        - XPeng
        - 小鹏
        - 小鹏鹏行
    - name: "达闼 / CloudMinds"
      description: "云端智能机器人"
      keywords:
        - CloudMinds
        - 达闼
    - name: "追觅 / Dreame"
      description: "扫地机器人 + 具身智能"
      keywords:
        - Dreame
        - 追觅
    - name: "松灵机器人 / AgileX"
      description: "移动机器人底盘、具身智能平台"
      keywords:
        - AgileX
        - 松灵
        - 松灵机器人

  authors:
    # ── Physics-based Animation / Motion ──
    - name: "Xuebin (Jason) Peng"
      affiliation: "Simon Fraser University"
      note: "DeepMimic, AMP, ASE, physics-based character animation"
    - name: "Michiel van de Panne"
      affiliation: "UBC"
      note: "Physics-based animation, character control"
    - name: "Jessica Hodgins"
      affiliation: "CMU / Disney Research"
      note: "Character animation, motion capture"
    - name: "Sehoon Ha"
      affiliation: "Georgia Tech"
      note: "Physics-based animation, RL for locomotion"
    - name: "C. Karen Liu"
      affiliation: "Stanford"
      note: "Physics-based animation, character control"

    # ── Whole-body Control / Locomotion ──
    - name: "Russ Tedrake"
      affiliation: "MIT / TRI"
      note: "Whole-body control, manipulation, Drake, humanoid"
    - name: "Scott Kuindersma"
      affiliation: "Boston Dynamics"
      note: "Atlas whole-body locomotion and control"
    - name: "Marco Hutter"
      affiliation: "ETH Zurich"
      note: "Legged locomotion, whole-body control, ANYmal"
    - name: "Donghyun Kim"
      affiliation: "UMass Amherst / ex-Boston Dynamics"
      note: "Legged locomotion, whole-body MPC"
    - name: "Sangbae Kim"
      affiliation: "MIT"
      note: "MIT Cheetah, legged robot design and control"
    - name: "Aaron Ames"
      affiliation: "Caltech"
      note: "Bipedal locomotion, control theory, Cassie"

    # ── VLA / Robot Foundation Models ──
    - name: "Yuke Zhu"
      affiliation: "NVIDIA / UT Austin"
      note: "VLA, robot manipulation, foundation models"
    - name: "Jim Fan"
      affiliation: "NVIDIA GEAR"
      note: "VLA, foundation models, simulation, embodied AI"
    - name: "Chelsea Finn"
      affiliation: "Stanford"
      note: "Imitation learning, VLA, robot manipulation"
    - name: "Sergey Levine"
      affiliation: "UC Berkeley"
      note: "RL for robotics, manipulation, locomotion"
    - name: "Pieter Abbeel"
      affiliation: "UC Berkeley"
      note: "RL, imitation learning, robot learning"
    - name: "Mohit Shridhar"
      affiliation: "Google DeepMind"
      note: "VLA, language-conditioned manipulation, RT系列"
    - name: "Katerina Fragkiadaki"
      affiliation: "CMU"
      note: "VLA, learning from video, 3D vision for robotics"
    - name: "Dinesh Jayaraman"
      affiliation: "UPenn GRASP"
      note: "Robot learning, visual representation for manipulation"
    - name: "Lerrel Pinto"
      affiliation: "NYU"
      note: "Robot learning, self-supervised, real-world RL"

    # ── Manipulation / Grasping ──
    - name: "Ken Goldberg"
      affiliation: "UC Berkeley"
      note: "Robot manipulation, grasping, surgical robotics"
    - name: "Jeannette Bohg"
      affiliation: "Stanford"
      note: "Robot manipulation, perception, contact-rich"
    - name: "Animesh Garg"
      affiliation: "Georgia Tech / NVIDIA"
      note: "VLA, simulation, dexterous manipulation"
    - name: "Shuran Song"
      affiliation: "Stanford"
      note: "Robot perception, manipulation, one-shot learning"
    - name: "Dieter Fox"
      affiliation: "UW / NVIDIA"
      note: "Robot perception, manipulation, RGB-D"
    - name: "Edward Johns"
      affiliation: "Imperial College London"
      note: "Robot manipulation, learning from demonstration"

    # ── Navigation / Planning ──
    - name: "Deepak Pathak"
      affiliation: "CMU"
      note: "RL, locomotion, curiousity-driven exploration, navigation"
    - name: "Pulkit Agrawal"
      affiliation: "MIT"
      note: "RL, locomotion, robot learning, curiosity"
    - name: "Abhinav Gupta"
      affiliation: "CMU"
      note: "Robot learning, self-supervised, manipulation"

    # ── Human-Robot Interaction / Learning ──
    - name: "Dorsa Sadigh"
      affiliation: "Stanford"
      note: "Human-robot interaction, learning from human feedback"
    - name: "Georgia Chalvatzaki"
      affiliation: "TU Darmstadt"
      note: "Robot learning, human-robot interaction, manipulation"
    - name: "Sonia Chernova"
      affiliation: "Georgia Tech"
      note: "Robot learning, HRI, semantic reasoning"
    - name: "Jan Peters"
      affiliation: "TU Darmstadt"
      note: "Robot learning, RL, motor skills"

    # ── 中国学者 ──
    - name: "Huazhe Xu"
      affiliation: "Tsinghua"
      note: "RL for robotics, manipulation, sim-to-real"
    - name: "Hang Zhao"
      affiliation: "Tsinghua / Shanghai AI Lab"
      note: "Embodied AI, VLA, autonomous driving"
    - name: "He Wang"
      affiliation: "Peking University"
      note: "Robot manipulation, sim-to-real, RL"
    - name: "Jianlan Luo"
      affiliation: "Tsinghua"
      note: "Robot manipulation, tactile sensing"
    - name: "Xiaolong Wang"
      affiliation: "UC San Diego"
      note: "Robot learning, video-based manipulation, VLA"
    - name: "Yunzhu Li"
      affiliation: "UIUC"
      note: "Robot learning, dynamics models, tactile sensing"
    - name: "Chuang Gan"
      affiliation: "UMass Amherst / MIT-IBM"
      note: "Embodied AI, VLA, robot simulation"
    - name: "Hao Su"
      affiliation: "UC San Diego"
      note: "Robot learning, dexterous manipulation, sim-to-real"
    - name: "Shaojie Bai"
      affiliation: "CMU"
      note: "Robot learning, RL, transformer methods"
    # ─── 可自行增删 ───
```

### 3.2 AI 相关性过滤 `ai/filter.py`

#### 设计原则

- **复用已有数据**：在 AI 摘要之后执行，可利用 `tldr` + `motivation` + `method` 做更准确的相关性判断
- **独立可配置**：切换子方向只需修改 `config/topics.yaml`，无需重新抓取或重新摘要
- **低开销**：filter 是一个轻量分类任务，可以用更便宜的模型（如 `deepseek-chat`），也可以和摘要共用模型
- **关注列表优先**：命中 `watched.labs` 或 `watched.authors` 的论文自动标记为 relevant，不依赖 topic 关键词匹配

#### 过滤逻辑（两阶段）

```
阶段 1：简单匹配（无 LLM 开销）
  - 检查论文作者是否命中 config/topics.yaml 中 watched.authors[*].name
  - 检查论文作者/机构是否命中 watched.labs[*].keywords
  - 命中 → 直接标记 is_relevant=true, from_watchlist=true
  - 此阶段可批量执行，零 LLM 成本

阶段 2：LLM 判断（阶段 1 未命中时）
  - 将 topic 定义 + watched labs/authors 提示传给 LLM
  - LLM 综合判断论文是否属于目标方向或值得关注
  - 输出 matched_topics, confidence, reason
```

#### 输入

```
JSONL (AI enhanced)  +  config/topics.yaml
```

每行包含：`id`, `title`, `authors`, `summary`（原始摘要）, `AI.tldr`, `AI.motivation`, `AI.method`

#### LLM 结构输出

```python
class RelevanceFilter(BaseModel):
    is_relevant: bool          # 是否与任一目标子方向相关
    matched_topics: List[str]  # 匹配的子方向 id 列表，如 ["vla", "navigation"]
    from_watchlist: bool       # 是否来自关注列表（阶段1命中 or LLM判定为名组工作）
    confidence: float          # 0-1 置信度
    reason: str                # 一句话理由，如 "来自NVIDIA GEAR Lab的VLA工作"
```

#### 过滤 Prompt 设计

```
你是一个机器人学论文审稿人。请根据以下论文信息，判断它是否属于给定的研究方向。

研究方向定义：
{topic_definitions}

关注列表（来自这些组/作者的工作优先推送）：
{watched_context}

论文信息：
- 标题：{title}
- 作者：{authors}
- 摘要：{summary}
- TL;DR：{tldr}
- 方法：{method}

请判断这篇论文是否与上述任一研究方向相关。注意：
1. 宽松匹配——如果论文的技术方法可能应用于某方向，也可标记
2. 一篇论文可以属于多个方向
3. 如果来自关注列表中的组/作者，标记 from_watchlist=true
4. 给出相关性理由
```

#### 输出文件

```
data/{date}_filtered.jsonl    # 仅包含相关论文（is_relevant=true）
data/{date}_AI_enhanced_{lang}.jsonl  # 全量（不变，包含 matched_topics 字段）
```

#### 执行模式

- 默认在 AI 摘要之后串行执行
- 使用 `ThreadPoolExecutor` 并行调用 LLM（和 enhancer 一致）
- max_workers 默认为 2（减少 API 压力）

### 3.3 推送模块 `push/`

#### 目录结构

```
push/
├── __init__.py
├── base.py            # AbstractPushChannel
├── wechat.py          # 微信推送（优先实现）
├── formatter.py       # 消息格式化
├── main.py            # 推送入口
└── (future)           # feishu.py / dingtalk.py 后续扩展
```

#### 抽象基类

```python
class AbstractPushChannel(ABC):
    @abstractmethod
    def send(self, papers: List[Dict], date: str) -> bool:
        """发送推送，返回是否成功"""
        ...

    @abstractmethod
    def channel_name(self) -> str:
        """渠道名称，用于日志"""
        ...
```

#### 消息格式（Markdown 卡片）

以飞书为例：

```markdown
📌 **Daily Robotics Papers | 2026-06-21**

🔥 **VLA**（3 篇）
- ⭐ [RT-3: Scaling VLA Models](https://arxiv.org/abs/2501.xxx)
  *TL;DR: 来自 Google DeepMind，大规模 VLA 训练范式*
- [另一篇论文标题](https://arxiv.org/abs/2501.xxx)
  *一句话 TL;DR*

🚗 **Navigation**（5 篇）
- ⭐ [论文标题](https://arxiv.org/abs/2501.xxx)  ← ⭐ = 关注列表/大组

🤖 **Whole Body Control**（2 篇）
- ...

---
📊 今日抓取 187 篇 | 相关 15 篇 | ⭐关注列表 4 篇
[查看全部](https://xxx.github.io/daily-arXiv-ai-enhanced/)
```

**配置项：**
- `PUSH_TOP_N`: 每个子方向最多推送几篇（默认 5）
- `PUSH_MIN_CONFIDENCE`: 最低置信度阈值（默认 0.6）
- `PUSH_SUMMARY_LENGTH`: 摘要截断长度（默认 120 字符）

#### 微信推送实现（优先）

微信推送有多种方式，按推荐优先级排列：

**方案 A：企业微信机器人 Webhook（推荐）**
- 免费，支持 Markdown 消息
- 单条消息限制 4096 字节，需分段
- 配置方式：企业微信 → 群机器人 → 获取 Webhook URL

**方案 B：Server 酱 / PushPlus（备选）**
- 个人微信接收，无需企业微信
- 消息格式有限制
- 配置方式：`PUSH_WECHAT_METHOD=pushplus`, `PUSH_WECHAT_KEY=xxx`

```python
class WeChatPushChannel(AbstractPushChannel):
    def __init__(self, webhook_url: str = None, method: str = "wecom_bot", key: str = None):
        self.webhook_url = webhook_url
        self.method = method       # "wecom_bot" | "pushplus" | "serverchan"
        self.key = key

    def send(self, papers, date):
        if self.method == "wecom_bot":
            return self._send_wecom(papers, date)
        elif self.method == "pushplus":
            return self._send_pushplus(papers, date)
        elif self.method == "serverchan":
            return self._send_serverchan(papers, date)

    def _send_wecom(self, papers, date):
        """企业微信机器人 Markdown 消息，超长则分段"""
        messages = formatter.build_wecom_messages(papers, date)
        success = True
        for msg in messages:
            resp = requests.post(
                self.webhook_url,
                json={"msgtype": "markdown", "markdown": {"content": msg}},
                timeout=10
            )
            if resp.status_code != 200 or resp.json().get("errcode") != 0:
                success = False
        return success

    def _send_pushplus(self, papers, date):
        """PushPlus 推送（个人微信）"""
        content = formatter.build_text_digest(papers, date)
        resp = requests.post(
            "https://www.pushplus.plus/send",
            json={"token": self.key, "title": f"Daily Robotics Papers | {date}",
                  "content": content, "template": "markdown"},
            timeout=10
        )
        return resp.status_code == 200
```

#### 推送入口 `push/main.py`

```python
def main():
    # 1. 读取过滤后的 papers
    # 2. 按 topic 分组、按 confidence 排序
    # 3. 对每个配置的 channel 发送
    # 4. 记录推送日志
    channels = []
    # 微信优先
    if os.environ.get("WECHAT_WEBHOOK_URL"):
        channels.append(WeChatPushChannel(
            webhook_url=os.environ["WECHAT_WEBHOOK_URL"],
            method=os.environ.get("PUSH_WECHAT_METHOD", "wecom_bot"),
            key=os.environ.get("PUSH_WECHAT_KEY")
        ))
    # 后续可选扩展
    if os.environ.get("FEISHU_WEBHOOK_URL"):
        channels.append(FeishuPushChannel(os.environ["FEISHU_WEBHOOK_URL"]))
    if os.environ.get("DINGTALK_WEBHOOK_URL"):
        channels.append(DingTalkPushChannel(os.environ["DINGTALK_WEBHOOK_URL"]))

    for ch in channels:
        try:
            ch.send(papers, today)
        except Exception as e:
            print(f"Push [{ch.channel_name()}] failed: {e}", file=sys.stderr)
```

---

## 4. 数据流

### 4.1 文件流转

```
data/{date}.jsonl                    # Scrapy 原始爬取（仅 id + categories）
    │
    ▼ 去重 (check_stats.py)
data/{date}.jsonl                    # 去重后（同文件覆盖）
    │
    ▼ AI 摘要 (ai/enhance.py)
data/{date}_AI_enhanced_Chinese.jsonl # 带结构化摘要
    │
    ▼ AI 过滤 (ai/filter.py)
data/{date}_filtered.jsonl           # 仅相关论文（新增）
data/{date}_AI_enhanced_Chinese.jsonl # 全量（追回 matched_topics 字段）
    │
    ├──▶ Markdown (to_md/convert.py) → GitHub Pages
    └──▶ push/main.py → 微信推送
```

### 4.2 JSONL 数据格式

**原始爬取：**
```json
{"id": "2501.12345", "categories": ["cs.RO", "cs.AI"]}
```

**AI 增强 + 过滤后：**
```json
{
  "id": "2501.12345",
  "categories": ["cs.RO", "cs.AI"],
  "title": "RT-3: Scaling VLA Models",
  "authors": "...",
  "summary": "...",
  "AI": {
    "tldr": "...",
    "motivation": "...",
    "method": "...",
    "result": "...",
    "conclusion": "...",
    "is_relevant": true,
    "matched_topics": ["vla"],
    "from_watchlist": true,
    "confidence": 0.92,
    "reason": "来自Google DeepMind，提出大规模VLA模型训练范式"
  }
}
```

---

## 5. 部署配置

### 5.1 GitHub Secrets（新增）

| Secret | 说明 | 必填 |
|--------|------|------|
| `OPENAI_API_KEY` | LLM API Key | ✅ |
| `OPENAI_BASE_URL` | API Base URL | ✅ |
| `WECHAT_WEBHOOK_URL` | 企业微信机器人 Webhook | ✅ |
| `PUSH_WECHAT_METHOD` | 微信推送方式：`wecom_bot` / `pushplus` / `serverchan` | ❌ (默认 wecom_bot) |
| `PUSH_WECHAT_KEY` | PushPlus/Server酱 的 token（仅非 wecom_bot 时需要） | ❌ |
| `FEISHU_WEBHOOK_URL` | 飞书机器人 Webhook（扩展） | ❌ |
| `DINGTALK_WEBHOOK_URL` | 钉钉机器人 Webhook（扩展） | ❌ |
| `TOKEN_GITHUB` | GitHub Token（用于代码链接检测） | ❌ |
| `ACCESS_PASSWORD` | 网页访问密码 | ❌ |

### 5.2 GitHub Variables

| Variable | 说明 | 默认值 |
|----------|------|--------|
| `CATEGORIES` | arXiv 分类，逗号分隔 | `cs.RO, cs.AI, cs.LG, cs.CV` |
| `LANGUAGE` | 摘要语言 | `Chinese` |
| `MODEL_NAME` | LLM 模型 | `deepseek-chat` |
| `FILTER_MODEL_NAME` | 过滤用 LLM（可选，默认同 MODEL_NAME） | `deepseek-chat` |
| `EMAIL` / `NAME` | Git commit 身份 | — |
| `PUSH_TOP_N` | 每子方向推送论文数上限 | `5` |
| `PUSH_MIN_CONFIDENCE` | 最低置信度 | `0.6` |

### 5.3 GitHub Actions 流程更新

在现有 `.github/workflows/run.yml` 中新增两个 step：

```yaml
# Step: AI Filtering（在 AI Enhancement 之后）
- name: AI Relevance Filtering
  if: steps.dedup_check.outputs.has_new_content == 'true'
  run: |
    source .venv/bin/activate
    today=${{ steps.crawl_step.outputs.crawl_date }}
    cd ai
    python filter.py --data ../data/${today}_AI_enhanced_${LANGUAGE}.jsonl \
                     --topics ../config/topics.yaml

# Step: Push to IM channels（在 Markdown 转换之后）
- name: Push to IM Channels
  if: steps.dedup_check.outputs.has_new_content == 'true'
  run: |
    source .venv/bin/activate
    export WECHAT_WEBHOOK_URL="${{ secrets.WECHAT_WEBHOOK_URL }}"
    export PUSH_WECHAT_METHOD="${{ vars.PUSH_WECHAT_METHOD }}"
    export PUSH_WECHAT_KEY="${{ secrets.PUSH_WECHAT_KEY }}"
    # 后续可选扩展
    export FEISHU_WEBHOOK_URL="${{ secrets.FEISHU_WEBHOOK_URL }}"
    export DINGTALK_WEBHOOK_URL="${{ secrets.DINGTALK_WEBHOOK_URL }}"
    cd push
    python main.py --data ../data/${today}_filtered.jsonl
```

---

## 6. 项目目录结构（改造后）

```
daily-arXiv-ai-enhanced/
├── ai/
│   ├── enhance.py          # AI 结构化摘要（已有，不改）
│   ├── structure.py         # Pydantic 模型（已有）
│   ├── filter.py            # 🆕 AI 相关性过滤
│   ├── filter_structure.py  # 🆕 Filter 的 Pydantic 模型
│   ├── template.txt         # 已有
│   └── system.txt           # 已有
├── config/
│   └── topics.yaml          # 🆕 子方向配置
├── push/
│   ├── __init__.py
│   ├── base.py              # 🆕 抽象推送基类
│   ├── feishu.py            # 🆕 飞书推送
│   ├── wechat.py            # 🆕 企业微信推送
│   ├── dingtalk.py          # 🆕 钉钉推送
│   ├── formatter.py         # 🆕 消息格式化
│   └── main.py              # 🆕 推送入口
├── daily_arxiv/              # 已有（不改）
│   └── ...
├── to_md/                    # 已有（不改）
│   └── ...
├── docs/
│   └── specs/
│       └── SPEC.md           # 🆕 本文档
├── .github/workflows/
│   └── run.yml               # 修改：新增 filter + push steps
└── ...
```

---

## 7. 测试策略

### 7.1 单元测试

| 模块 | 测试内容 | 工具 |
|------|---------|------|
| `ai/filter.py` | Filter 模型正确解析 LLM 输出 | mock LLM 响应 |
| `push/formatter.py` | 消息格式化正确分组、截断 | pytest |
| `push/feishu.py` | Webhook payload 格式正确 | mock requests |
| `push/wechat.py` | 长消息分段逻辑 | pytest |
| `config/topics.yaml` | YAML 格式有效、字段完整 | pytest + jsonschema |

### 7.2 集成测试

- **端到端测试**：在 test 分支上手动触发 workflow，验证全流程
- **推送测试**：先用测试 webhook URL 验证消息格式
- **过滤准确性抽样**：随机抽 20 篇论文，人工校验 LLM 过滤结果

### 7.3 本地调试

```bash
# 1. 仅爬取（快速）
cd daily_arxiv && CATEGORIES="cs.RO" scrapy crawl arxiv -o ../data/test.jsonl

# 2. 测试过滤（已有增强数据的情况下）
cd ai && python filter.py --data ../data/2026-06-21_AI_enhanced_Chinese.jsonl --topics ../config/topics.yaml

# 3. 测试推送
cd push && python main.py --data ../data/2026-06-21_filtered.jsonl --dry-run
```

---

## 8. 边界与约束

### 8.1 必须遵守

- ✅ GitHub Actions 单次运行不超过 6 小时（当前预估 30-60 分钟）
- ✅ 遵守 arXiv 爬取 rate limit（Scrapy 默认设置已满足）
- ✅ API Key 通过 GitHub Secrets 管理，不硬编码
- ✅ 推送频率：每天最多 1 次

### 8.2 需要确认

- ⚠️ 每天 200-350 篇论文的 LLM API 费用（约 1-2 元/天），是否可接受？
- ⚠️ 如果某天 cs.CV 论文量过大（如 CVPR 截稿日），是否需要临时缩小分类范围？
- ⚠️ IM 推送可能有消息条数/长度限制，是否需要拆分为多条？

### 8.3 明确不做

- ❌ 不做论文全文下载和深度解析（版权 + 成本考虑）
- ❌ 不支持自定义定时（固定每天 UTC 1:30 运行）
- ❌ 不做多用户订阅系统（保持单用户/单团队）
- ❌ 不修改已有的 `SKILL` 系统（保持兼容）

---

## 9. 实施计划

### Phase 1：配置先行（0.5h）
- [ ] Fork 仓库到个人 GitHub
- [ ] 配置 Secrets: `OPENAI_API_KEY`, `OPENAI_BASE_URL`
- [ ] 配置 Variables: `CATEGORIES=cs.RO, cs.AI, cs.LG, cs.CV`, `LANGUAGE=Chinese`, `MODEL_NAME=deepseek-chat`
- [ ] 手动触发一次 workflow，验证爬取 + 摘要流程可走通
- [ ] 确认 GitHub Pages 正常显示

### Phase 2：AI 过滤模块（1-2h）
- [ ] 创建 `config/topics.yaml`
- [ ] 创建 `ai/filter_structure.py`（Pydantic 模型）
- [ ] 实现 `ai/filter.py`
- [ ] 本地用已有数据测试过滤效果
- [ ] 接入 GitHub Actions

### Phase 3：微信推送模块（1-2h）
- [ ] 实现 `push/base.py`
- [ ] 实现 `push/formatter.py`
- [ ] 实现 `push/wechat.py`（企业微信机器人 + PushPlus 双模式）
- [ ] 本地 dry-run 测试消息格式
- [ ] 接入 GitHub Actions

### Phase 4：完善（0.5h）
- [ ] 优化子方向定义和 prompt，提升过滤准确率
- [ ] 扩展飞书/钉钉 channel（按需）
- [ ] 文档完善

---

*最后更新：2026-06-21*
