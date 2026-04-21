# PCEC / Dream / Heartbeat 职责划分

## 三组件定位

| 组件 | 定位 | 核心职责 | 频率 |
|------|------|---------|------|
| **PCEC** | Wiki-Native 进化引擎 | 信号检测→经验召回→策略选择→执行→验证→**Wiki固化** | 每天 1 次 (05:00) |
| **Dream 🌙** | 记忆整合引擎 | T1 日志扫描 → T0 四动作 → T2 Wiki 维护 | 每天 1 次 (03:00) |
| **Heartbeat** | 系统健康巡检 | Cron 运维面（存活/错误/资源）— 轻量高频 | 每 30 分钟 |

## PCEC 的独特价值

三个组件都写 Wiki，但写的内容和目的不同：

| 维度 | Heartbeat | Dream | PCEC |
|------|-----------|-------|---------|
| 写 Wiki 吗 | ❌ 不写 | ✅ 知识条目（T2 归档） | ✅ **Gene + Capsule**（进化资产） |
| 读 Wiki 吗 | ❌ 不读 | ✅ 读 T0/T2 做整合决策 | ✅ **Recall：每次行动前必查** |
| 数据源 | cron 元数据 | memory/ 日志 | Session Transcript + Wiki 历史 |
| 正常时输出 | "全绿"摘要 | 整合报告或静默 | Explore 或静默 |
| 深度 | 浅（秒级） | 中（读日志） | 深（读 transcript + 搜索 Wiki） |

## PCEC vs Heartbeat：关键区分

| 维度 | Heartbeat | PCEC |
|------|-----------|---------|
| 关心的是 | 服务可用性 | 执行质量 + Skill 表现 + **经验积累** |
| 数据源 | `cron action=list` 元数据 | Session Transcript + **Wiki Recall** |
| 对 Cron 的态度 | 挂了没？ | 跑得好不好？Skill 有没有被正确使用？ |
| 对 Wiki 的态度 | **不读写** | **核心依赖：Read + Write** |
| 正常时输出 | "全绿"摘要 | Explore 主动突破 或 静默 |

**Heartbeat = 监控报警器。PCEC = 体检医生 + 学习系统。**

## 职责边界

### PCEC 管什么
- Cron job 执行质量（成功率、耗时趋势、token 效率）
- **Skill 调用质量评估**（遵循度、输出质量、效率、模式化问题）
- **Gene 全生命周期管理**（创建、复用、升级、废弃）
- **Capsule 审计记录**（每次行动的完整记录）
- **Memory Graph 维护**（通过 Wiki 搜索实现隐式图谱）
- **Distillation**（从 Capsule 提炼/升级 Gene）
- **Explore**（无信号时的主动发现：内部技术债、外部新模式）
- 低风险自主行动（L1）：参数调优、Wiki 写入、数据维护
- 高风险变更草案（L2）

### PCEC 不管什么
- 记忆文件维护（Dream 的地盘）
- T0 注入层审计（Dream 的四动作之一）
- 实时系统资源监控（Heartbeat 的地盘）
- 纯运维类 job 的瞬态失败诊断

### Dream 管什么
- memory/ 日志扫描与高价值信号提取
- T0 文件的四动作操作（整合/遗忘/纠正/洞察）
- T2 Wiki Vault 的知识条目维护
- 梦境自我记忆（dream/ 目录）
- **Dream 也写 Wiki，但写的是"知识条目"，不是 Gene/Capsule**

### Dream 不管什么
- Skill/Cron 健康诊断（PCEC 的地盘）
- 系统资源状态（Heartbeat 的地盘）
- Gene/Capsule/L2 草案（PCEC 的地盘）
- HEARTBEAT.md 维护

### Heartbeat 管什么
- 磁盘使用率、内存占用
- Cron job 成功率概览（不深入诊断）
- 网关错误计数
- 异常时告警投递

### Heartbeat 不管什么
- 深度问题诊断（PCEC 的地盘）
- 文件修改（谁都不在心跳里改东西）
- Skill 质量（PCEC 的地盘）
- Wiki 读写（Heartbeat 不碰 Wiki）

## Wiki 写入分工

三个组件写入 Wiki 的内容类型不同，互不冲突：

| 写入者 | 内容类型 | Wiki 页面标题格式 | 示例 |
|--------|---------|-------------------|------|
| **PCEC** | Gene（策略模板） | `Gene: <信号> — <策略名>` | `Gene: GLM超时重试 — 指数退避策略` |
| **PCEC** | Capsule（修复记录） | `Capsule: YYYY-MM-DD <目标> <摘要>` | `Capsule: 2026-04-21 feed-score timeout调优` |
| **Dream** | 知识条目 | `<主题>` （synthesis） | `Cron Git 安全规范`、`Prompt 设计原则` |

**互不侵犯原则扩展：**
- PCEC 不修改 Dream 写的知识条目（但可以 **读取** 作为信号来源）
- Dream 不修改 PCEC 的 Gene/Capsule
- Heartbeat 不修改任何 Wiki 页面
- 任何组件都可以 **读取** 其他组件的 Wiki 页面作为信号

## 信号共享

| 信号源 | PCEC 用途 | Dream 用途 | Heartbeat 用途 |
|--------|-----------|-----------|---------------|
| memory/ 日志 | 行为漂移检测 | 主数据源 | 不读 |
| Cron 执行数据 | 退化检测+效率分析 | 不关心 | 成功率概览 |
| Session Transcript | **核心**：Cron 诊断 + Skill 质量 | 不读 | 不读 |
| sessions_list | 增量采样找 skill 调用 | 不读 | 不读 |
| **Wiki (Gene/Capsule)** | **核心**：Recall 经验召回 | 可读知识条目 | 不读 |
| **Wiki (知识条目)** | 可读作为上下文 | 写入+维护 | 不读 |
| 系统资源指标 | 不关心 | 不关心 | 主要数据源 |
