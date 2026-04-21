# PCEC / Dream / Heartbeat 职责划分

## 三组件定位

| 组件 | 定位 | 核心职责 | 频率 |
|------|------|---------|------|
| **PCEC** | 受控进化引擎 | Cron 健康 + **Skill 质量评估**（双轨） | 每天 1 次 (05:00) |
| **Dream 🌙** | 记忆整合引擎 | T1 日志扫描 → T0 四动作 → T2 Wiki 维护 | 每天 1 次 (03:00) |
| **Heartbeat** | 系统健康巡检 | Cron 运维面（存活/错误/资源）— 轻量高频 | 每 30 分钟 |

## PCEC vs Heartbeat：关键区分

这两个组件都看 Cron，但视角完全不同：

| 维度 | Heartbeat | PCEC |
|------|-----------|------|
| 关心的是 | 服务可用性 | 执行质量 + Skill 表现 |
| 数据源 | `cron action=list` 元数据 | Session Transcript 内容 |
| 对 Cron 的态度 | 挂了没？为什么挂？ | 跑得好不好？Skill 有没有被正确使用？ |
| 正常时输出 | "全绿"摘要 | 静默（或轻量 Skill 评分） |
| 对 Skill 的态度 | **不管** | **核心关注** |
| 深度 | 浅（秒级） | 深（读完整 session） |

**简单说：Heartbeat 是监控报警器，PCEC 是体检医生。**

## 职责边界

### PCEC 管什么
- Cron job 的执行质量（成功率、耗时趋势、token 效率）
- **Skill 调用质量评估**（遵循度、输出质量、效率、模式化问题）
- 增量采样：扫描上次运行后新增的、调用了 skill 工具的 session
- 修复方案草案的生成与追踪（Level 2）
- 低风险自主行动（Level 1）：参数调优、知识沉淀、数据维护
- 系统级异常趋势预警

### PCEC 不管什么
- 记忆文件维护（Dream 的地盘）
- T0 注入层审计（Dream 的四动作之一）
- 实时系统资源监控（Heartbeat 的地盘）
- 纯运维类 job 的瞬态失败诊断（Heartbeat 已覆盖）

### Dream 管什么
- memory/ 日志扫描与高价值信号提取
- T0 文件的四动作操作（整合/遗忘/纠正/洞察）
- T2 Wiki Vault 的知识条目维护
- 梦境自我记忆（dream/ 目录）

### Dream 不管什么
- Skill/Cron 健康诊断（PCEC 的地盘）
- 系统资源状态（Heartbeat 的地盘）
- HEARTBEAT.md 维护（明确排除）

### Heartbeat 管什么
- 磁盘使用率、内存占用
- Cron job 成功率概览（不深入诊断）
- 网关错误计数
- 异常时告警投递

### Heartbeat 不管什么
- 深度问题诊断（PCEC 的地盘）
- 文件修改（谁都不在心跳里改东西）
- Skill 质量（PCEC 的地盘）
- 长期趋势分析

## 信号共享

三个组件可以共享以下信号源，但处理方式和目标不同：

| 信号源 | PCEC 用途 | Dream 用途 | Heartbeat 用途 |
|--------|-----------|-----------|---------------|
| memory/ 日志 | 人工干预模式、行为漂移 | 主数据源，逐条扫描 | 不读 |
| Cron 执行数据 | 退化检测、效率分析 | 不关心 | 成功率概览 |
| Session Transcript | **核心数据源**：Cron 诊断 + Skill 质量评估 | 不读 | 不读 |
| sessions_list | **增量采样**：找调用 skill 的 session | 不读 | 不读 |
| 系统资源指标 | 不关心 | 不关心 | 主要数据源 |

## 互不侵犯原则

- PCEC 不修改 Dream 的目标文件（memory/, dream/, T0 文件, Wiki 条目）
- Dream 不修改 PCEC 的目标文件（SKILL.md, scripts/, cron prompts, gep/）
- Heartbeat 不修改任何文件（只读 + 投递告警）
- 任何组件都可以**读取**其他组件的数据作为信号，但修改必须在自己的职责范围内
