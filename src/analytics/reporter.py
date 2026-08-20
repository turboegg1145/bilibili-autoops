"""
运营分析报表生成器
根据采集的历史数据，计算增长与互动率，自动生成格式化的 Markdown 与 JSON 报表。
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from tabulate import tabulate
from src.analytics.storage import StorageManager
from src.utils.logger import logger

class AnalyticsReporter:
    def __init__(self, storage: StorageManager, reports_dir: str = "./reports"):
        self.storage = storage
        self.reports_dir = reports_dir
        os.makedirs(self.reports_dir, exist_ok=True)

    async def generate_markdown_report(self, latest_data: Optional[Dict[str, Any]] = None) -> str:
        """生成 Markdown 格式的运营日报/周报"""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_tag = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. 提取账号数据
        acc_history = await self.storage.get_latest_account_stats(limit=2)
        curr_acc = acc_history[0] if acc_history else (latest_data.get("account") if latest_data else {})
        prev_acc = acc_history[1] if len(acc_history) > 1 else {}

        followers = curr_acc.get("followers", 0)
        followers_diff = followers - prev_acc.get("followers", followers)
        followers_diff_str = f"(+{followers_diff})" if followers_diff > 0 else (f"({followers_diff})" if followers_diff < 0 else "(-)")

        likes = curr_acc.get("likes", 0)
        likes_diff = likes - prev_acc.get("likes", likes)
        likes_diff_str = f"(+{likes_diff})" if likes_diff > 0 else (f"({likes_diff})" if likes_diff < 0 else "(-)")

        total_views = curr_acc.get("total_views", 0)
        views_diff = total_views - prev_acc.get("total_views", total_views)
        views_diff_str = f"(+{views_diff})" if views_diff > 0 else (f"({views_diff})" if views_diff < 0 else "(-)")

        # 2. 提取单视频表现数据
        videos = await self.storage.get_latest_video_stats(limit=30)
        # 去重，保留每个 bvid 的最新记录
        unique_videos = {}
        for v in videos:
            bvid = v.get("bvid")
            if bvid and bvid not in unique_videos:
                unique_videos[bvid] = v

        video_list = list(unique_videos.values())
        # 按播放量降序排序
        video_list.sort(key=lambda x: x.get("views", 0), reverse=True)

        # 构造表格
        table_rows = []
        for idx, v in enumerate(video_list[:10], start=1):
            title = v.get("title", "")[:20]
            views = v.get("views", 0)
            like = v.get("like", 0)
            coin = v.get("coin", 0)
            fav = v.get("favorite", 0)
            reply = v.get("reply", 0)
            bvid = v.get("bvid", "")
            # 计算互动率 (三连+评论 / 播放)
            engagement = round(((like + coin + fav + reply) / views * 100), 2) if views > 0 else 0
            table_rows.append([idx, f"[{title}](https://www.bilibili.com/video/{bvid})", views, like, coin, fav, reply, f"{engagement}%"])

        headers = ["#", "视频标题", "播放量", "点赞", "投币", "收藏", "评论", "互动率"]
        table_md = tabulate(table_rows, headers=headers, tablefmt="github")

        # 3. 构造完整报告
        report_content = f"""# 📊 Bilibili 账号运营分析日报

**生成时间**：{now_str}  
**UP 主昵称**：{curr_acc.get('name', 'B站创作者')} (MID: `{curr_acc.get('mid', '-')}`)

---

## 一、 账号全景概览

| 核心指标 | 当前数值 | 周期变化 |
| :--- | :--- | :--- |
| **粉丝总数 (Followers)** | {followers:,} | {followers_diff_str} |
| **获赞总数 (Likes)** | {likes:,} | {likes_diff_str} |
| **视频播放总量 (Views)** | {total_views:,} | {views_diff_str} |
| **硬币余额 (Coins)** | {curr_acc.get('coins', 0)} | - |
| **关注数 (Following)** | {curr_acc.get('following', 0)} | - |

---

## 二、 TOP 热门视频表现榜

{table_md if table_rows else "*暂无已发布视频数据*"}

---

## 三、 运营优化建议

1. **爆款内容复盘**：优先分析排名前列的视频，总结选题方向、标题命名方式和封面风格。
2. **粉丝互动提升**：对于互动率高于行业均值（>5%）的视频，增加置顶互动评论和置顶投票。
3. **内容发布节奏**：保持定期投递至 `inbox/` 目录，维持账号活跃度与权重。

---
*本报表由 Bilibili 自动化运营中台自动生成*
"""

        # 保存到文件
        report_file = os.path.join(self.reports_dir, f"report_{date_tag}.md")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_content)

        # 同时保存 JSON 摘要
        json_file = os.path.join(self.reports_dir, f"report_{date_tag}.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": now_str,
                "account": curr_acc,
                "top_videos": video_list[:10]
            }, f, indent=2, ensure_ascii=False)

        logger.info(f"运营分析报表已生成至: {report_file}")
        return report_file
