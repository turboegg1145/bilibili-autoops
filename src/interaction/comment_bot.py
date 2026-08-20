"""
评论区互动机器人
自动获取近期视频评论，识别未回复内容并进行智能回复与点赞。
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
        self.config = config
        self.storage = storage
        self.reply_engine = ReplyEngine(config)
        self.recent_videos_count = config.get("recent_videos_count", 5)
        self.auto_like_positive = config.get("auto_like_positive", True)
        self.self_mid = int(credential.dedeuserid) if credential.dedeuserid else None

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

                # 忽略 UP 主自己的发言
                if author_mid == self.self_mid:
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
