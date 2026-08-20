# 📺 Bilibili-AutoOps (B 站自动化运营中台)

一套轻量、稳定、模块化的 B 站账号自动化运营系统。专为与 **负责内容生产的 Antigravity Agent** 协同设计，覆盖 **自动投稿**、**粉丝互动（评论/私信）**、**全景数据监控与运营报表** 三大核心场景。

---

## 🌟 核心功能

1. **🚀 自动投稿流水线 (Uploader)**
   - **收件箱监听**：监控 `inbox/` 目录，其他负责视频剪辑/文案生成的 Antigravity Agent 投递任务包后自动排队发布。
   - **分片断点续传**：基于官方推荐的多分片并发上传协议，支持封面图自动上传、分区设置、标签、简介与关联动态。
   - **发布后归档**：发布成功的任务包自动转移至 `archive/` 目录并生成记录。

2. **💬 智能粉丝互动 (Interaction)**
   - **评论区巡检**：定时扫描近期视频评论，记录已回复 ID（SQLite 严格防重复回复）。
   - **正向情感点赞**：自动识别夸奖、支持等正向评论并点赞。
   - **双模回复引擎**：
     - **规则引擎**：基于关键词快速响应催更、教程、支持等提问。
     - **LLM 引擎**：支持接入 OpenAI / DeepSeek / 任何兼容 API 生成高情商拟人化回复。
   - **私信（DM）监听**：自动过滤并回复未读粉丝私信。

3. **📊 全景数据监控与报表 (Analytics)**
   - **账号宏观指标**：粉丝数、获赞总数、播放总量、硬币、关注数历史时序监控。
   - **单视频表现追踪**：播放量、点赞、投币、收藏、分享、弹幕数及互动率综合计算。
   - **自动日报/周报**：生成漂亮的 Markdown 与 JSON 运营报表（存放于 `reports/`）。

4. **🔄 自动化守护调度 (Daemon)**
   - 集中定时调度器，挂机即可自动执行投稿检测、互动回复与报表生成。
   - 自动检测 Cookie 有效性并在即将过期时触发刷新保活。

---

## 📁 目录结构

```
bilibili/
├── inbox/                     # 📥 投稿收件箱 (外部 Agent 投递目录)
├── archive/                   # 📦 已发布视频归档
├── data/                      # 💾 运行数据 (凭据、SQLite 数据库、日志)
├── reports/                   # 📊 自动生成的 Markdown 运营日报
├── src/
│   ├── auth/                  # 🔑 认证与二维码登录
│   ├── uploader/              # 🚀 投稿与 Inbox 监听
│   ├── interaction/           # 💬 评论/私信互动与回复引擎
│   ├── analytics/             # 📊 数据采集、SQLite 存储与报表
│   └── utils/                 # ⚙️ 日志与调度器
├── config.example.yaml        # ⚙️ 配置文件模版
├── main.py                    # 🎯 统一 CLI 入口
└── requirements.txt           # 📦 依赖列表
```

---

## 🛠️ 与其他 Antigravity Agent 协同规范

当其他负责内容生成的 Antigravity Agent 完成视频与素材制作后，只需在 `inbox/` 目录下创建一个独立的子文件夹，并放入以下文件：

### 任务包规范 (`inbox/YYYYMMDD_my_video/`)：
1. 视频文件（如 `video.mp4`）
2. 封面图片（如 `cover.jpg`，可选）
3. `meta.json` 元数据配置文件（如下所示）：

```json
{
  "title": "【AI实战】如何用Python打造全自动B站运营助手",
  "desc": "本视频由 AI 自动化流程全流程驱动制作。\n关注我，了解更多硬核 AI 玩法！\n\n#AI #自动化 #Python",
  "tid": 188,
  "tags": ["人工智能", "Python", "自动化", "科技", "开源"],
  "video_file": "video.mp4",
  "cover_file": "cover.jpg",
  "copyright": 1,
  "source": "原创",
  "dynamic": "新视频上线啦！带大家看看全自动运营的魅力~ 欢迎一键三连！"
}
```

> **注意**：系统监听到新任务包后会自动锁定、分片上传，发布成功后会自动转移到 `archive/` 目录，无需外部 Agent 额外清理。

---

## 🚀 快速上手

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 复制配置文件

```bash
cp config.example.yaml config.yaml
```

### 3. 扫码登录 B 站账号

在终端运行：
```bash
python main.py login
```
终端将输出二维码字符画（并在 `./data/login_qrcode.png` 生成图片），使用 B 站手机客户端扫码并确认登录即可。

### 4. 常用 CLI 命令

```bash
# 1. 检查当前凭据是否有效
python main.py check-auth

# 2. 扫描 inbox/ 目录并自动发布所有待投稿包
python main.py upload --inbox

# 3. 手动上传单个指定视频
python main.py upload --video ./test.mp4 --title "测试视频" --tid 17 --tags "AI,测试"

# 4. 执行一次粉丝互动巡检 (回复评论与私信)
python main.py interact

# 5. 采集最新数据并生成 Markdown 运营分析日报
python main.py stats

# 6. 启动全自动挂机守护进程 (自动执行上述所有任务)
python main.py daemon
```

---

## ⚙️ 配置文件说明 (`config.yaml`)

```yaml
# 投稿默认配置
uploader:
  default_tid: 17             # 默认分区 ID (17: 游戏, 122: 野生技术协会, 188: 计算机技术)
  default_copyright: 1        # 1: 原创, 2: 转载
  watch_interval_seconds: 60  # inbox 扫描间隔 (秒)

# 粉丝互动配置
interaction:
  check_interval_seconds: 300 # 互动巡检间隔 (秒)
  auto_like_positive: true    # 自动给好评点赞
  reply_mode: "rule"          # "rule" (规则匹配) 或 "llm" (大模型回复)
  rules:
    - keywords: ["催更", "求更新"]
      replies: ["催更收到！已经在快马加鞭制作中！🔥"]

# 数据监控配置
analytics:
  collect_interval_hours: 6   # 数据采集间隔 (小时)
  generate_daily_report: true # 自动生成 Markdown 报表
```

---

## 🛡️ 安全与隐私

- 所有账号凭据保存于 `data/credentials.json`，且已加入 `.gitignore`，不会泄漏到代码仓库。
- 视频上传与互动请求遵循平台频控保护策略（内置延时与防重复回复机制）。
