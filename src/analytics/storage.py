"""
数据持久化存储模块 (SQLite + aiosqlite)
存储账号全景指标、单视频历史数据、评论/私信已回复记录与投稿流水。
"""
import os
import aiosqlite
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.utils.logger import logger

DB_PATH = "./data/bilibili.db"

class StorageManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

    async def init_db(self):
        """初始化数据库表结构"""
        async with aiosqlite.connect(self.db_path) as db:
            # 1. 账号全景指标表
            await db.execute("""
            CREATE TABLE IF NOT EXISTS account_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                mid INTEGER,
                name TEXT,
                followers INTEGER,
                following INTEGER,
                likes INTEGER,
                coins REAL,
                total_views INTEGER
            );
            """)

            # 2. 单视频指标表
            await db.execute("""
            CREATE TABLE IF NOT EXISTS video_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                bvid TEXT NOT NULL,
                title TEXT,
                views INTEGER,
                danmaku INTEGER,
                reply INTEGER,
                favorite INTEGER,
                coin INTEGER,
                share INTEGER,
                like INTEGER
            );
            """)

            # 3. 已回复评论表
            await db.execute("""
            CREATE TABLE IF NOT EXISTS replied_comments (
                rpid INTEGER PRIMARY KEY,
                bvid TEXT,
                user_name TEXT,
                comment_text TEXT,
                reply_text TEXT,
                replied_at TEXT NOT NULL
            );
            """)

            # 4. 已回复私信表
            await db.execute("""
            CREATE TABLE IF NOT EXISTS replied_messages (
                msg_key TEXT PRIMARY KEY,
                sender_uid INTEGER,
                msg_text TEXT,
                reply_text TEXT,
                replied_at TEXT NOT NULL
            );
            """)

            # 5. 投稿历史表
            await db.execute("""
            CREATE TABLE IF NOT EXISTS upload_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                title TEXT NOT NULL,
                bvid TEXT,
                archive_path TEXT,
                status TEXT
            );
            """)
            await db.commit()
            logger.debug(f"SQLite 数据库已初始化: {self.db_path}")

    async def record_account_stat(self, data: Dict[str, Any]):
        """记录账号总体数据"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
            INSERT INTO account_stats (timestamp, mid, name, followers, following, likes, coins, total_views)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now,
                data.get("mid"),
                data.get("name"),
                data.get("followers", 0),
                data.get("following", 0),
                data.get("likes", 0),
                data.get("coins", 0),
                data.get("total_views", 0)
            ))
            await db.commit()

    async def record_video_stat(self, data: Dict[str, Any]):
        """记录视频指标快照"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
            INSERT INTO video_stats (timestamp, bvid, title, views, danmaku, reply, favorite, coin, share, like)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now,
                data.get("bvid"),
                data.get("title"),
                data.get("views", 0),
                data.get("danmaku", 0),
                data.get("reply", 0),
                data.get("favorite", 0),
                data.get("coin", 0),
                data.get("share", 0),
                data.get("like", 0)
            ))
            await db.commit()

    async def is_comment_replied(self, rpid: int) -> bool:
        """检查评论是否已被回复"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT 1 FROM replied_comments WHERE rpid = ?", (rpid,)) as cursor:
                row = await cursor.fetchone()
                return row is not None

    async def record_replied_comment(self, rpid: int, bvid: str, user_name: str, comment_text: str, reply_text: str):
        """记录已回复的评论"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
            INSERT OR REPLACE INTO replied_comments (rpid, bvid, user_name, comment_text, reply_text, replied_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (rpid, bvid, user_name, comment_text, reply_text, now))
            await db.commit()

    async def is_message_replied(self, msg_key: str) -> bool:
        """检查私信是否已回复"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT 1 FROM replied_messages WHERE msg_key = ?", (msg_key,)) as cursor:
                row = await cursor.fetchone()
                return row is not None

    async def record_replied_message(self, msg_key: str, sender_uid: int, msg_text: str, reply_text: str):
        """记录已回复的私信"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
            INSERT OR REPLACE INTO replied_messages (msg_key, sender_uid, msg_text, reply_text, replied_at)
            VALUES (?, ?, ?, ?, ?)
            """, (msg_key, sender_uid, msg_text, reply_text, now))
            await db.commit()

    async def get_latest_account_stats(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近账号指标记录"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM account_stats ORDER BY id DESC LIMIT ?", (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_latest_video_stats(self, bvid: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """获取视频最新指标记录"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if bvid:
                async with db.execute("SELECT * FROM video_stats WHERE bvid = ? ORDER BY id DESC LIMIT ?", (bvid, limit)) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with db.execute("SELECT * FROM video_stats ORDER BY id DESC LIMIT ?", (limit,)) as cursor:
                    rows = await cursor.fetchall()
            return [dict(r) for r in rows]
