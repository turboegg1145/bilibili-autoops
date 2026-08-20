"""
评论区互动机器人
自动获取近期视频评论，识别未回复内容并进行智能回复与点赞。
严格黑名单过滤（包括 Antigravy 本人与系统号），内置自动防分裂/去重机制。
"""
import asyncio
from typing import Dict, Any, List, Optional
from bilibili_api import Credential, user, comment
from bilibili_api.comment import CommentResourceType, OrderType, Comment
from src.interaction.reply_engine import ReplyEngine
from src.analytics.storage import StorageManager
from src.utils.logger import logger

class CommentBot:
    def __init__(self, credential: Credential, config: Dict[str, Any], storage: StorageManager):
        self.credential = credential
        self.config = config or {}
        self.storage = storage
        self.reply_engine = ReplyEngine(self.config)
        self.recent_videos_count = self.config.get("recent_videos_count", 5)
        self.auto_like_positive = self.config.get("auto_like_positive", True)
        self.self_mid = int(credential.dedeuserid) if credential.dedeuserid else None

        # 黑名单列表 (包含 Antigravy 本人 UID、名称及官方系统号)
        self.blacklist_uids = set(str(x) for x in self.config.get("blacklist_uids", []))
        if self.self_mid:
            self.blacklist_uids.add(str(self.self_mid))

        self.blacklist_unames = set(str(x).lower() for x in self.config.get("blacklist_unames", [
            "antigravy", "up主小助手", "哔哩哔哩智能机", "社区中心", "哔哩哔哩活动", "系统通知"
        ]))
        self.blacklist_unames.add("antigravy")

    def is_blacklisted(self, mid: Any, uname: str) -> bool:
        """检查用户是否在黑名单中 (严禁回复本人或系统号)"""
        if mid and str(mid) in self.blacklist_uids:
            return True
        if uname and uname.lower() in self.blacklist_unames:
            return True
        return False

    async def get_recent_videos(self) -> List[Dict[str, Any]]:
        """获取当前 UP 主最近发布的视频列表"""
        if not self.self_mid:
            logger.warning("未配置 dedeuserid，无法定位当前用户视频")
            return []
        try:
            u = user.User(uid=self.self_mid, credential=self.credential)
            video_data = await u.get_videos(pn=1, ps=self.recent_videos_count)
            vlist = video_data.get("list", {}).get("vlist", [])
            return vlist
        except Exception as e:
            logger.error(f"获取 UP 主近期视频失败: {e}")
            return []

    async def clean_duplicate_self_comments(self, aid: int):
        """自动检测并清理因 B 站接口 Bug 导致分裂的多余重复评论"""
        try:
            res = await comment.get_comments(
                oid=aid,
                type_=CommentResourceType.VIDEO,
                order=OrderType.TIME,
                credential=self.credential
            )
            replies = res.get("replies") or []
            top = res.get("top") or {}
            top_rpid = None
            if isinstance(top, dict):
                top_rpid = top.get("upper", {}).get("rpid")

            seen_messages = set()
            for r in replies:
                rpid = r.get("rpid")
                member = r.get("member", {})
                author_mid = member.get("mid")
                msg = r.get("content", {}).get("message", "").strip()

                # 只检测自己发送的评论
                if str(author_mid) == str(self.self_mid):
                    # 置顶评论绝对保留
                    if rpid == top_rpid:
                        seen_messages.add(msg)
                        continue

                    if msg in seen_messages:
                        logger.warning(f"检测到分裂重复评论 (rpid: {rpid})，正在自动删除清理...")
                        try:
                            c_obj = Comment(oid=aid, type_=CommentResourceType.VIDEO, rpid=rpid, credential=self.credential)
                            await c_obj.delete()
                            logger.info(f"已成功删除多余重复评论: {rpid}")
                        except Exception as e:
                            logger.error(f"删除重复评论失败: {e}")
                    else:
                        seen_messages.add(msg)

        except Exception as e:
            logger.debug(f"评论去重巡检异常 (可忽略): {e}")

    async def process_video_comments(self, aid: int, bvid: str, title: str) -> int:
        """处理单个视频的评论区"""
        logger.info(f"正在巡检视频《{title}》({bvid}) 的评论区...")
        replied_count = 0

        try:
            res = await comment.get_comments(
                oid=aid,
                type_=CommentResourceType.VIDEO,
                order=OrderType.TIME,
                credential=self.credential
            )
            replies = res.get("replies") or []
            if not replies:
                logger.debug(f"视频《{title}》暂无新评论")
                return 0

            for c_item in replies:
                rpid = c_item.get("rpid")
                member = c_item.get("member", {})
                author_mid = member.get("mid")
                user_name = member.get("uname", "粉丝")
                message = c_item.get("content", {}).get("message", "")

                # 严格黑名单与本人过滤
                if self.is_blacklisted(author_mid, user_name):
                    continue

                # 检查是否已回复过
                if await self.storage.is_comment_replied(rpid):
                    continue

                # 生成回复与点赞判断
                reply_text, should_like = await self.reply_engine.generate_reply(message, user_name)

                # 1. 自动点赞正向评论
                if self.auto_like_positive and should_like:
                    try:
                        c_obj = Comment(oid=aid, type_=CommentResourceType.VIDEO, rpid=rpid, credential=self.credential)
                        await c_obj.like(True)
                        logger.info(f"已为粉丝【{user_name}】的评论点赞: {message[:30]}...")
                    except Exception as e:
                        logger.debug(f"点赞失败 (可能已点过): {e}")

                # 2. 发送回复
                try:
                    logger.info(f"正在回复粉丝【{user_name}】: \"{message[:30]}\" -> \"{reply_text}\"")
                    await comment.send_comment(
                        text=reply_text,
                        oid=aid,
                        type_=CommentResourceType.VIDEO,
                        root=rpid,
                        parent=rpid,
                        credential=self.credential
                    )
                    await self.storage.record_replied_comment(
                        rpid=rpid,
                        bvid=bvid,
                        user_name=user_name,
                        comment_text=message,
                        reply_text=reply_text
                    )
                    replied_count += 1
                    # 避免触发 B 站频控
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"发送评论回复失败 (rpid={rpid}): {e}")

            # 3. 每次巡检回复后，自动执行一次去重清理，防止接口分裂
            await self.clean_duplicate_self_comments(aid)

            return replied_count

        except Exception as e:
            logger.error(f"拉取视频《{title}》评论失败: {e}")
            return 0

    async def run_once(self) -> int:
        """执行一次全量视频评论互动巡检"""
        videos = await self.get_recent_videos()
        if not videos:
            return 0

        total_replied = 0
        for v in videos:
            aid = v.get("aid")
            bvid = v.get("bvid")
            title = v.get("title", "")
            if aid and bvid:
                count = await self.process_video_comments(aid, bvid, title)
                total_replied += count
                await asyncio.sleep(2)

        logger.info(f"本轮评论巡检完成，共互动回复 {total_replied} 条评论")
        return total_replied
