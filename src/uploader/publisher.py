"""
视频发布核心模块
基于 bilibili-api-python 的 VideoUploader 实现分片并发断点续传与发布。
"""
import os
import asyncio
from typing import Dict, Any, Optional, List
from bilibili_api import Credential, video_uploader, Picture
from bilibili_api.video_uploader import VideoUploader, VideoUploaderPage, VideoMeta, VideoUploaderEvents
from src.utils.logger import logger

class VideoPublisher:
    def __init__(self, credential: Credential):
        self.credential = credential

    async def publish(
        self,
        video_path: str,
        title: str,
        desc: str,
        tid: int = 17,
        tags: Optional[List[str]] = None,
        cover_path: Optional[str] = None,
        copyright: int = 1,
        source: str = "原创",
        dynamic: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        发布单个视频
        :param video_path: 视频文件本地绝对/相对路径
        :param title: 视频标题 (80字以内)
        :param desc: 视频简介 (2000字以内)
        :param tid: 分区 ID (如 17 游戏, 122 野生技术协会, 188 计算机技术, etc.)
        :param tags: 视频标签列表 (最多12个)
        :param cover_path: 封面图片路径 (jpg/png)
        :param copyright: 1 为原创, 2 为转载
        :param source: 转载来源 (copyright 为 2 时必填)
        :param dynamic: 关联发布的 B 站动态内容 (可选)
        :return: 发布结果字典
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        if tags is None:
            tags = ["AI", "科技", "自动化"]
        elif isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        logger.info(f"开始准备发布视频: 《{title}》 | 路径: {video_path}")

        # 1. 准备封面
        cover_pic = None
        if cover_path and os.path.exists(cover_path):
            try:
                logger.info(f"正在上传封面: {cover_path}")
                cover_pic = Picture.from_file(cover_path)
            except Exception as e:
                logger.warning(f"读取封面失败，将使用自动截取封面: {e}")
                cover_pic = None

        # 2. 准备分P列表
        page_title = os.path.splitext(os.path.basename(video_path))[0]
        pages = [VideoUploaderPage(path=video_path, title=page_title)]

        # 3. 构造元数据
        meta_dict = {
            "tid": int(tid),
            "title": title[:80],
            "desc": desc[:2000],
            "tags": tags[:12],
            "original": True if int(copyright) == 1 else False,
            "source": source if int(copyright) != 1 else "",
            "dynamic": dynamic if dynamic else f"发布了新视频《{title}》，欢迎观看！"
        }

        # 4. 创建上传器
        uploader = VideoUploader(
            pages=pages,
            meta=meta_dict,
            credential=self.credential,
            cover=cover_pic if cover_pic else ""
        )

        # 5. 绑定事件监听器
        last_pct = 0
        @uploader.on(VideoUploaderEvents.PROGRESS)
        async def on_progress(data):
            nonlocal last_pct
            pct = int(data.get("progress", 0) * 100) if isinstance(data, dict) else 0
            if pct >= last_pct + 10 or pct == 100:
                last_pct = pct
                logger.info(f"上传进度: {pct}%")

        logger.info("开始分片上传视频数据...")
        result = await uploader.start()
        logger.info(f"视频发布成功！返回结果: {result}")
        return result
