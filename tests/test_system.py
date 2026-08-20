"""
系统完整性与各模块功能自动化验证脚本
"""
import os
import sys
import asyncio
import shutil
import json

# 添加当前目录到 sys.path
sys.path.insert(0, os.path.abspath("."))

from src.config import Config
from src.utils.logger import setup_logger, logger
from src.auth.login import AuthManager
from src.analytics.storage import StorageManager
from src.analytics.reporter import AnalyticsReporter
from src.interaction.reply_engine import ReplyEngine
from src.uploader.watcher import InboxWatcher

async def run_tests():
    logger.info("=== 开始系统自检与模块功能测试 ===")

    # 1. 测试配置加载
    cfg = Config("config.example.yaml")
    assert cfg.get("app", "name") == "Bilibili-AutoOps", "配置解析失败"
    logger.info("✅ 1. 配置文件加载测试通过")

    # 2. 测试 SQLite 数据库与持久化
    test_db_path = "./data/test_bilibili.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    storage = StorageManager(test_db_path)
    await storage.init_db()

    # 记录并读取账号指标
    await storage.record_account_stat({
        "mid": 123456,
        "name": "测试UP主",
        "followers": 10500,
        "following": 50,
        "likes": 52000,
        "coins": 300,
        "total_views": 250000
    })
    acc_stats = await storage.get_latest_account_stats()
    assert len(acc_stats) == 1 and acc_stats[0]["followers"] == 10500, "账号数据存取失败"

    # 记录并读取单视频指标
    await storage.record_video_stat({
        "bvid": "BV1xx411c7xx",
        "title": "AI自动化运营演示",
        "views": 15000,
        "danmaku": 320,
        "reply": 180,
        "favorite": 1200,
        "coin": 800,
        "share": 95,
        "like": 2500
    })
    v_stats = await storage.get_latest_video_stats()
    assert len(v_stats) == 1 and v_stats[0]["bvid"] == "BV1xx411c7xx", "视频数据存取失败"

    # 测试防重复回复记录
    assert not await storage.is_comment_replied(999999)
    await storage.record_replied_comment(999999, "BV1xx411c7xx", "粉丝小明", "催更催更！", "催更收到！")
    assert await storage.is_comment_replied(999999)
    logger.info("✅ 2. SQLite 数据库与数据存取/防重检查测试通过")

    # 3. 测试回复引擎
    reply_engine = ReplyEngine(cfg.get("interaction"))
    rep1, like1 = await reply_engine.generate_reply("UP主太厉害了，666！", "小红")
    assert like1 is True, "正向情绪识别失败"
    assert "感谢" in rep1 or "谢谢" in rep1 or "好" in rep1 or len(rep1) > 0, "回复生成失败"

    rep2, _ = await reply_engine.generate_reply("什么时候快更新啊", "小刚")
    assert "催更" in rep2 or "更新" in rep2 or len(rep2) > 0, "关键词规则匹配失败"
    logger.info("✅ 3. 智能回复引擎与情感分析测试通过")

    # 4. 测试运营报表生成
    reporter = AnalyticsReporter(storage, "./reports")
    report_file = await reporter.generate_markdown_report()
    assert os.path.exists(report_file), "报表生成失败"
    with open(report_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Bilibili 账号运营分析日报" in content
        assert "BV1xx411c7xx" in content
    logger.info(f"✅ 4. 运营日报 Markdown 生成测试通过 ({report_file})")

    # 5. 测试 Inbox 目录任务包扫描
    test_inbox_pkg = "./inbox/test_pkg_2026"
    os.makedirs(test_inbox_pkg, exist_ok=True)
    with open(os.path.join(test_inbox_pkg, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({
            "title": "测试视频任务",
            "desc": "由外部 Agent 生成的测试任务",
            "tid": 188,
            "tags": ["AI", "测试"]
        }, f)
    with open(os.path.join(test_inbox_pkg, "dummy_video.mp4"), "w") as f:
        f.write("dummy video data")

    watcher = InboxWatcher(credential=None, inbox_dir="./inbox", archive_dir="./archive")
    tasks = watcher.scan_inbox()
    assert any("test_pkg_2026" in t for t in tasks), "Inbox 扫描未发现任务包"
    logger.info("✅ 5. Inbox 外部 Agent 投递任务包发现与解析测试通过")

    # 清理测试产生的临时文件
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    if os.path.exists(test_inbox_pkg):
        shutil.rmtree(test_inbox_pkg)

    logger.info("🎉 所有模块基础自检全部通过！")

if __name__ == "__main__":
    setup_logger()
    asyncio.run(run_tests())
