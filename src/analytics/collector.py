"""
数据采集模块
定期拉取 UP 主全景运营指标与所有已发布视频的播放、互动详细数据并存库。
"""
import asyncio
from typing import Dict, Any, List, Optional
from bilibili_api import Credential, user, video
from src.analytics.storage import StorageManager
from src.utils.logger import logger

class DataCollector:
    def __init__(self, credential: Credential, storage: StorageManager):
        self.credential = credential
        self.storage = storage
        self.self_mid = int(credential.dedeuserid) if credential.dedeuserid else None

    async def collect_account_stats(self) -> Optional[Dict[str, Any]]:
        """采集 UP 主账号总体数据"""
        if not self.self_mid:
            logger.warning("未配置 dedeuserid，无法采集账号数据")
            return None

        try:
            u = user.User(uid=self.self_mid, credential=self.credential)
            
            # 1. 基础信息
            user_info = await u.get_user_info()
            name = user_info.get("name", "")
            coins = user_info.get("coins", 0)

            # 2. 粉丝与关注数
            relation = await u.get_relation_stat()
            followers = relation.get("follower", 0)
            following = relation.get("following", 0)

            # 3. 总获赞与总播放量
            up_stat = await u.get_up_stat()
            likes = up_stat.get("likes", 0)
            archive_data = up_stat.get("archive", {})
            total_views = archive_data.get("view", 0)

            account_data = {
                "mid": self.self_mid,
                "name": name,
                "followers": followers,
                "following": following,
                "likes": likes,
                "coins": coins,
                "total_views": total_views
            }

            await self.storage.record_account_stat(account_data)
            logger.info(f"账号数据采集成功: 粉丝 {followers} | 获赞 {likes} | 总播放 {total_views}")
            return account_data

        except Exception as e:
            logger.error(f"采集账号总体数据失败: {e}")
            return None

    async def collect_video_stats(self, page_size: int = 30) -> List[Dict[str, Any]]:
        """采集 UP 主已发布视频的详细指标"""
        if not self.self_mid:
            return []

        collected_videos = []
        try:
            u = user.User(uid=self.self_mid, credential=self.credential)
            video_data = await u.get_videos(pn=1, ps=page_size)
            vlist = video_data.get("list", {}).get("vlist", [])

            for v in vlist:
                bvid = v.get("bvid")
                title = v.get("title", "")
                if not bvid:
                    continue

                try:
                    v_obj = video.Video(bvid=bvid, credential=self.credential)
                    info = await v_obj.get_info()
                    stat = info.get("stat", {})

                    v_stat = {
                        "bvid": bvid,
                        "title": title,
                        "views": stat.get("view", 0),
                        "danmaku": stat.get("danmaku", 0),
                        "reply": stat.get("reply", 0),
                        "favorite": stat.get("favorite", 0),
                        "coin": stat.get("coin", 0),
                        "share": stat.get("share", 0),
                        "like": stat.get("like", 0)
                    }

                    await self.storage.record_video_stat(v_stat)
                    collected_videos.append(v_stat)
                    await asyncio.sleep(1)  # 礼貌延迟

                except Exception as e:
                    logger.warning(f"获取视频《{title}》({bvid}) 指标失败: {e}")

            logger.info(f"成功采集并记录了 {len(collected_videos)} 个视频的运行指标")
            return collected_videos

        except Exception as e:
            logger.error(f"采集视频数据失败: {e}")
            return []

    async def run_once(self) -> Dict[str, Any]:
        """执行一次全量数据指标采集"""
        account = await self.collect_account_stats()
        videos = await self.collect_video_stats()
        return {
            "account": account,
            "videos": videos
        }
