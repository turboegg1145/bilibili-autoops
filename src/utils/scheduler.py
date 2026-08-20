"""
后台任务调度器 (基于 APScheduler / AsyncIO)
集中管理自动投稿监听、粉丝互动巡检、数据采集与报表生成的定时轮询。
"""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.config import Config
from src.auth.login import AuthManager
from src.uploader.watcher import InboxWatcher
from src.interaction.comment_bot import CommentBot
from src.interaction.message_bot import MessageBot
from src.analytics.storage import StorageManager
from src.analytics.collector import DataCollector
from src.analytics.reporter import AnalyticsReporter
from src.utils.logger import logger

class AutoOpsScheduler:
    def __init__(self, config: Config):
        self.config = config
        self.auth_mgr = AuthManager(config.get("auth", "credential_file", default="./data/credentials.json"))
        self.storage = StorageManager(f"{config.get('app', 'data_dir', default='./data')}/bilibili.db")
        self.scheduler = AsyncIOScheduler()

    async def setup(self):
        """初始化数据库与组件"""
        await self.storage.init_db()
        cred = self.auth_mgr.load_credential()
        if not cred:
            logger.warning("未检测到登录凭据，请先执行 `python main.py login` 扫码登录！")
            return False

        # 1. 自动投稿监听
        watch_sec = self.config.get("uploader", "watch_interval_seconds", default=60)
        self.watcher = InboxWatcher(
            credential=cred,
            inbox_dir=self.config.get("app", "inbox_dir", default="./inbox"),
            archive_dir=self.config.get("app", "archive_dir", default="./archive"),
            default_tid=self.config.get("uploader", "default_tid", default=17),
            default_copyright=self.config.get("uploader", "default_copyright", default=1),
            default_source=self.config.get("uploader", "default_source", default="AI运营自动化"),
            default_tags=self.config.get("uploader", "default_tags", default=["AI", "科技"])
        )
        self.scheduler.add_job(
            self.watcher.scan_and_process_once,
            "interval",
            seconds=watch_sec,
            id="inbox_watch_job",
            name="Inbox 目录自动投稿扫描"
        )
        logger.info(f"已注册定时任务: Inbox 投稿监听 (每 {watch_sec} 秒)")

        # 2. 粉丝互动监听 (评论与私信)
        if self.config.get("interaction", "enabled", default=True):
            interact_sec = self.config.get("interaction", "check_interval_seconds", default=300)
            self.comment_bot = CommentBot(cred, self.config.get("interaction"), self.storage)
            self.message_bot = MessageBot(cred, self.config.get("interaction"), self.storage)

            async def interact_task():
                await self.comment_bot.run_once()
                await self.message_bot.run_once()

            self.scheduler.add_job(
                interact_task,
                "interval",
                seconds=interact_sec,
                id="interaction_job",
                name="粉丝评论与私信互动巡检"
            )
            logger.info(f"已注册定时任务: 粉丝互动巡检 (每 {interact_sec} 秒)")

        # 3. 数据监控与报表生成
        if self.config.get("analytics", "enabled", default=True):
            collect_hours = self.config.get("analytics", "collect_interval_hours", default=6)
            self.collector = DataCollector(cred, self.storage)
            self.reporter = AnalyticsReporter(self.storage, self.config.get("app", "reports_dir", default="./reports"))

            async def analytics_task():
                data = await self.collector.run_once()
                await self.reporter.generate_markdown_report(data)

            self.scheduler.add_job(
                analytics_task,
                "interval",
                hours=collect_hours,
                id="analytics_job",
                name="数据采集与报表生成"
            )
            logger.info(f"已注册定时任务: 数据采集与报表生成 (每 {collect_hours} 小时)")

        # 4. 凭据保活与自动刷新
        if self.config.get("auth", "auto_refresh", default=True):
            self.scheduler.add_job(
                self.auth_mgr.refresh_if_needed,
                "interval",
                hours=24,
                id="auth_refresh_job",
                name="Cookie 凭据自动刷新"
            )
            logger.info("已注册定时任务: 凭据自动保活刷新 (每 24 小时)")

        return True

    def start(self):
        """启动后台调度器"""
        self.scheduler.start()
        logger.info("🚀 自动化运营调度中心已启动，所有守护任务开始运行...")
