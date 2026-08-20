"""
Inbox 目录监听与自动投稿处理
监听其他 Antigravity Agent 输出到 inbox/ 目录的视频与元数据包，自动执行上传并归档。
"""
import os
import json
import shutil
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from bilibili_api import Credential
from src.uploader.publisher import VideoPublisher
from src.utils.logger import logger

class InboxWatcher:
    def __init__(
        self,
        credential: Credential,
        inbox_dir: str = "./inbox",
        archive_dir: str = "./archive",
        default_tid: int = 17,
        default_copyright: int = 1,
        default_source: str = "AI运营自动化",
        default_tags: Optional[List[str]] = None
    ):
        self.credential = credential
        self.inbox_dir = inbox_dir
        self.archive_dir = archive_dir
        self.default_tid = default_tid
        self.default_copyright = default_copyright
        self.default_source = default_source
        self.default_tags = default_tags or ["AI", "科技", "自动化"]
        self.publisher = VideoPublisher(credential)

        os.makedirs(self.inbox_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)

    def _find_video_file(self, folder: str) -> Optional[str]:
        """在文件夹中查找视频文件"""
        video_exts = (".mp4", ".mkv", ".flv", ".mov", ".avi", ".wmv")
        for f in os.listdir(folder):
            if f.lower().endswith(video_exts):
                return os.path.join(folder, f)
        return None

    def _find_cover_file(self, folder: str) -> Optional[str]:
        """在文件夹中查找封面图片"""
        img_exts = (".jpg", ".jpeg", ".png", ".webp")
        for f in os.listdir(folder):
            if f.lower().endswith(img_exts) and not f.startswith("."):
                return os.path.join(folder, f)
        return None

    def scan_inbox(self) -> List[str]:
        """扫描 inbox 目录中的待处理任务包（子目录）"""
        tasks = []
        if not os.path.exists(self.inbox_dir):
            return tasks

        for item in os.listdir(self.inbox_dir):
            if item.startswith(".") or item == ".gitkeep":
                continue
            item_path = os.path.join(self.inbox_dir, item)
            if os.path.isdir(item_path):
                # 检查是否已有 .lock 或 .processing 标记
                if not os.path.exists(os.path.join(item_path, ".processing")):
                    tasks.append(item_path)
        return tasks

    async def process_task(self, task_dir: str) -> Optional[Dict[str, Any]]:
        """处理单个待投稿任务包"""
        logger.info(f"发现待发布任务包: {task_dir}")
        lock_file = os.path.join(task_dir, ".processing")

        try:
            with open(lock_file, "w") as f:
                f.write("locked")

            meta_file = os.path.join(task_dir, "meta.json")
            meta = {}
            if os.path.exists(meta_file):
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)

            # 寻找视频文件
            video_file_name = meta.get("video_file")
            video_path = os.path.join(task_dir, video_file_name) if video_file_name else self._find_video_file(task_dir)

            if not video_path or not os.path.exists(video_path):
                logger.error(f"任务包中未找到有效的视频文件: {task_dir}")
                return None

            # 寻找封面文件
            cover_file_name = meta.get("cover_file")
            cover_path = os.path.join(task_dir, cover_file_name) if cover_file_name else self._find_cover_file(task_dir)

            title = meta.get("title") or os.path.splitext(os.path.basename(video_path))[0]
            desc = meta.get("desc") or f"本视频由自动化运营系统协助发布。\n#AI #自动化"
            tid = meta.get("tid", self.default_tid)
            tags = meta.get("tags", self.default_tags)
            copyright = meta.get("copyright", self.default_copyright)
            source = meta.get("source", self.default_source)
            dynamic = meta.get("dynamic")

            # 执行发布
            result = await self.publisher.publish(
                video_path=video_path,
                title=title,
                desc=desc,
                tid=tid,
                tags=tags,
                cover_path=cover_path,
                copyright=copyright,
                source=source,
                dynamic=dynamic
            )

            # 归档处理
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = os.path.basename(task_dir)
            archive_target = os.path.join(self.archive_dir, f"{timestamp}_{folder_name}")

            if os.path.exists(lock_file):
                os.remove(lock_file)

            shutil.move(task_dir, archive_target)
            logger.info(f"任务包已成功发布并归档至: {archive_target}")

            return {
                "status": "success",
                "result": result,
                "archive_path": archive_target,
                "title": title
            }

        except Exception as e:
            logger.error(f"处理任务包 {task_dir} 失败: {e}", exc_info=True)
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except Exception:
                    pass
            return None

    async def scan_and_process_once(self) -> int:
        """执行单次 inbox 扫描与处理"""
        tasks = self.scan_inbox()
        if not tasks:
            logger.debug("inbox/ 暂无待处理任务")
            return 0

        success_count = 0
        for task_dir in tasks:
            res = await self.process_task(task_dir)
            if res:
                success_count += 1
            await asyncio.sleep(2)
        return success_count
