"""
私信互动机器人
拉取未读会话与私信，进行自动智能答复与防重处理。
严格黑名单过滤（包括 Antigravy 本人、UP主小助手、自动打招呼号等）。
"""
import asyncio
import json
from typing import Dict, Any, List
from bilibili_api import Credential, session
from bilibili_api.session import EventType
from src.interaction.reply_engine import ReplyEngine
from src.analytics.storage import StorageManager
from src.utils.logger import logger

class MessageBot:
    def __init__(self, credential: Credential, config: Dict[str, Any], storage: StorageManager):
        self.credential = credential
        self.config = config or {}
        self.storage = storage
        self.reply_engine = ReplyEngine(self.config)
        self.self_mid = int(credential.dedeuserid) if credential.dedeuserid else None

        # 黑名单 UID 与用户名
        self.blacklist_uids = set(str(x) for x in self.config.get("blacklist_uids", []))
        if self.self_mid:
            self.blacklist_uids.add(str(self.self_mid))

        self.blacklist_unames = set(str(x).lower() for x in self.config.get("blacklist_unames", [
            "antigravy", "up主小助手", "哔哩哔哩智能机", "社区中心", "哔哩哔哩活动", "系统通知"
        ]))
        self.blacklist_unames.add("antigravy")

    def is_blacklisted(self, talker_id: Any) -> bool:
        """检查会话对象是否在黑名单中"""
        if not talker_id or talker_id <= 0:
            return True
        if str(talker_id) in self.blacklist_uids:
            return True
        return False

    async def run_once(self) -> int:
        """执行一次私信扫描与自动回复"""
        logger.info("开始巡检粉丝私信会话...")
        replied_count = 0

        try:
            sessions_data = await session.get_sessions(credential=self.credential, session_type=1)
            session_list = sessions_data.get("session_list") or []

            for sess in session_list:
                talker_id = sess.get("talker_id")
                unread_count = sess.get("unread_count", 0)
                last_msg = sess.get("last_msg", {})

                # 1. 严格过滤黑名单与本人
                if self.is_blacklisted(talker_id):
                    continue

                msg_key = str(last_msg.get("msg_key") or f"{talker_id}_{last_msg.get('msg_seq')}")
                sender_uid = last_msg.get("sender_uid")

                # 如果最后一条消息是自己发的，跳过
                if str(sender_uid) == str(self.self_mid):
                    continue

                # 2. 检查是否已回复过
                if await self.storage.is_message_replied(msg_key):
                    continue

                # 3. 解析消息文本
                msg_content = ""
                content_raw = last_msg.get("content", "")
                if isinstance(content_raw, str):
                    try:
                        parsed = json.loads(content_raw)
                        msg_content = parsed.get("content", content_raw)
                    except Exception:
                        msg_content = content_raw

                if not msg_content:
                    continue

                # 4. 忽略常见的互关自动打招呼模板，避免对自动回复进行死循环
                if "感谢关注" in msg_content or "自动回复" in msg_content or "欢迎关注" in msg_content:
                    logger.debug(f"跳过自动打招呼模板私信: UID【{talker_id}】")
                    continue

                # 5. 生成回复
                reply_text, _ = await self.reply_engine.generate_reply(msg_content, user_name=f"UID_{talker_id}")

                try:
                    logger.info(f"正在向 UID【{talker_id}】发送私信回复: \"{msg_content[:20]}\" -> \"{reply_text}\"")
                    await session.send_msg(
                        credential=self.credential,
                        receiver_id=talker_id,
                        msg_type=EventType.TEXT,
                        content=reply_text
                    )
                    await self.storage.record_replied_message(
                        msg_key=msg_key,
                        sender_uid=talker_id,
                        msg_text=msg_content,
                        reply_text=reply_text
                    )
                    replied_count += 1
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"向 UID【{talker_id}】发送私信失败: {e}")

            logger.info(f"本轮私信巡检完成，共回复 {replied_count} 位粉丝")
            return replied_count

        except Exception as e:
            logger.error(f"巡检私信时发生异常: {e}")
            return 0
