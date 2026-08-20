"""
Bilibili 自动化运营中台 - 主入口与 CLI 工具
"""
import sys
import argparse
import asyncio
from src.config import Config
from src.utils.logger import setup_logger, logger
from src.auth.login import AuthManager
from src.uploader.publisher import VideoPublisher
from src.uploader.watcher import InboxWatcher
from src.interaction.comment_bot import CommentBot
from src.interaction.message_bot import MessageBot
from src.analytics.storage import StorageManager
from src.analytics.collector import DataCollector
from src.analytics.reporter import AnalyticsReporter
from src.utils.scheduler import AutoOpsScheduler

async def cmd_login(cfg: Config):
    """扫码登录"""
    auth_mgr = AuthManager(cfg.get("auth", "credential_file", default="./data/credentials.json"))
    cred = await auth_mgr.login_with_qrcode()
    if cred:
        logger.info("🎉 登录成功并已存储凭据！")
    else:
        logger.error("登录失败，请重试！")

async def cmd_check_auth(cfg: Config):
    """检查凭据状态"""
    auth_mgr = AuthManager(cfg.get("auth", "credential_file", default="./data/credentials.json"))
    cred = auth_mgr.load_credential()
    if not cred:
        logger.warning("未找到任何凭据文件，请先执行 `python main.py login`")
        return

    logger.info("正在验证凭据有效性...")
    is_valid = await auth_mgr.check_valid(cred)
    if is_valid:
        logger.info(f"✅ 凭据有效！当前 UID: {cred.dedeuserid}")
        # 尝试刷新
        await auth_mgr.refresh_if_needed(cred)
    else:
        logger.error("❌ 凭据已失效或过期，请重新登录！")

async def cmd_upload(cfg: Config, args):
    """视频投稿"""
    auth_mgr = AuthManager(cfg.get("auth", "credential_file", default="./data/credentials.json"))
    cred = auth_mgr.load_credential()
    if not cred:
        logger.error("请先登录！执行 `python main.py login`")
        return

    # 如果指定了 --inbox，则扫描收件箱
    if args.inbox:
        watcher = InboxWatcher(
            credential=cred,
            inbox_dir=cfg.get("app", "inbox_dir", default="./inbox"),
            archive_dir=cfg.get("app", "archive_dir", default="./archive"),
            default_tid=cfg.get("uploader", "default_tid", default=17),
            default_copyright=cfg.get("uploader", "default_copyright", default=1),
            default_source=cfg.get("uploader", "default_source", default="AI运营自动化"),
            default_tags=cfg.get("uploader", "default_tags", default=["AI", "科技"])
        )
        count = await watcher.scan_and_process_once()
        logger.info(f"Inbox 扫描与投稿完成，共发布 {count} 个视频包")
    elif args.video:
        publisher = VideoPublisher(cred)
        tags = args.tags.split(",") if args.tags else cfg.get("uploader", "default_tags")
        await publisher.publish(
            video_path=args.video,
            title=args.title or "AI 自动发布视频",
            desc=args.desc or "本视频由自动化运营系统协助发布。",
            tid=args.tid or cfg.get("uploader", "default_tid", default=17),
            tags=tags,
            cover_path=args.cover,
            copyright=args.copyright or 1,
            source=args.source or "原创",
            dynamic=args.dynamic
        )
    else:
        logger.error("请指定 --inbox 扫描投稿，或通过 --video 指定具体视频路径！")

async def cmd_interact(cfg: Config):
    """粉丝互动巡检"""
    auth_mgr = AuthManager(cfg.get("auth", "credential_file", default="./data/credentials.json"))
    cred = auth_mgr.load_credential()
    if not cred:
        logger.error("请先登录！执行 `python main.py login`")
        return

    storage = StorageManager(f"{cfg.get('app', 'data_dir', default='./data')}/bilibili.db")
    await storage.init_db()

    comment_bot = CommentBot(cred, cfg.get("interaction"), storage)
    message_bot = MessageBot(cred, cfg.get("interaction"), storage)

    c_count = await comment_bot.run_once()
    m_count = await message_bot.run_once()
    logger.info(f"互动巡检完成！共回复评论 {c_count} 条，回复私信 {m_count} 位粉丝。")

async def cmd_stats(cfg: Config):
    """数据采集与报表生成"""
    auth_mgr = AuthManager(cfg.get("auth", "credential_file", default="./data/credentials.json"))
    cred = auth_mgr.load_credential()
    if not cred:
        logger.error("请先登录！执行 `python main.py login`")
        return

    storage = StorageManager(f"{cfg.get('app', 'data_dir', default='./data')}/bilibili.db")
    await storage.init_db()

    collector = DataCollector(cred, storage)
    reporter = AnalyticsReporter(storage, cfg.get("app", "reports_dir", default="./reports"))

    logger.info("开始拉取最新数据...")
    data = await collector.run_once()
    report_file = await reporter.generate_markdown_report(data)
    logger.info(f"✅ 报表已生成: {report_file}")

async def cmd_daemon(cfg: Config):
    """启动全自动挂机守护进程"""
    scheduler = AutoOpsScheduler(cfg)
    ok = await scheduler.setup()
    if not ok:
        return

    scheduler.start()
    logger.info("守护进程运行中... 按 Ctrl+C 退出。")
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("收到退出信号，正在停止调度器...")

def main():
    parser = argparse.ArgumentParser(description="Bilibili 自动化运营中台 CLI")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # login
    subparsers.add_parser("login", help="终端扫码登录 B 站账号")

    # check-auth
    subparsers.add_parser("check-auth", help="验证当前登录凭据有效性")

    # upload
    upload_parser = subparsers.add_parser("upload", help="执行视频投稿")
    upload_parser.add_argument("--inbox", action="store_true", help="扫描 inbox/ 目录自动发布待投稿包")
    upload_parser.add_argument("--video", type=str, help="单个视频文件路径")
    upload_parser.add_argument("--title", type=str, help="视频标题")
    upload_parser.add_argument("--desc", type=str, help="视频简介")
    upload_parser.add_argument("--cover", type=str, help="封面图片路径")
    upload_parser.add_argument("--tid", type=int, help="分区 ID (如 17 游戏, 122 野生技术协会)")
    upload_parser.add_argument("--tags", type=str, help="标签，逗号分隔")
    upload_parser.add_argument("--copyright", type=int, choices=[1, 2], default=1, help="1 原创, 2 转载")
    upload_parser.add_argument("--source", type=str, default="原创", help="转载来源")
    upload_parser.add_argument("--dynamic", type=str, help="附加动态文本")

    # interact
    subparsers.add_parser("interact", help="执行一次粉丝评论与私信互动")

    # stats
    subparsers.add_parser("stats", help="拉取最新运营数据并生成日报")

    # daemon
    subparsers.add_parser("daemon", help="启动后台全自动挂机守护进程")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cfg = Config(args.config)
    setup_logger(cfg.get("app", "log_level", default="INFO"), cfg.get("app", "data_dir", default="./data"))

    if args.command == "login":
        asyncio.run(cmd_login(cfg))
    elif args.command == "check-auth":
        asyncio.run(cmd_check_auth(cfg))
    elif args.command == "upload":
        asyncio.run(cmd_upload(cfg, args))
    elif args.command == "interact":
        asyncio.run(cmd_interact(cfg))
    elif args.command == "stats":
        asyncio.run(cmd_stats(cfg))
    elif args.command == "daemon":
        asyncio.run(cmd_daemon(cfg))

if __name__ == "__main__":
    main()
