"""
配置管理模块
"""
import os
import yaml
from typing import Any, Dict

DEFAULT_CONFIG: Dict[str, Any] = {
    "app": {
        "name": "Bilibili-AutoOps",
        "version": "1.0.0",
        "log_level": "INFO",
        "data_dir": "./data",
        "inbox_dir": "./inbox",
        "archive_dir": "./archive",
        "reports_dir": "./reports",
    },
    "auth": {
        "credential_file": "./data/credentials.json",
        "auto_refresh": True,
        "refresh_interval_hours": 24,
    },
    "uploader": {
        "default_tid": 17,
        "default_copyright": 1,
        "default_source": "AI运营自动化",
        "default_tags": ["AI", "科技", "自动化"],
        "watch_interval_seconds": 60,
        "auto_archive": True,
    },
    "interaction": {
        "enabled": True,
        "check_interval_seconds": 300,
        "recent_videos_count": 5,
        "auto_like_positive": True,
        "reply_mode": "rule",
        "rules": [
            {
                "keywords": ["求更新", "催更", "快更新"],
                "replies": ["催更收到！正在快马加鞭制作中，下一期马上就来！🔥", "已经在生产流水线上了，关注不迷路！✨"]
            },
            {
                "keywords": ["厉害", "666", "牛", "太强了", "好活"],
                "replies": ["感谢小伙伴的支持与认可！会继续加油的！🎉", "谢谢夸奖！记得一键三连支持一下哦~ 💖"]
            }
        ],
        "default_replies": [
            "感谢支持！欢迎在评论区多多交流~ 🌟",
            "收到你的反馈啦，感谢观看！❤️"
        ],
        "llm": {
            "api_base": "https://api.openai.com/v1",
            "api_key": "",
            "model": "gpt-4o-mini",
            "prompt": "你是B站UP主的AI运营助手，请用友善、风趣且接地气的B站用户口吻简短回复粉丝评论（50字以内）："
        }
    },
    "analytics": {
        "enabled": True,
        "collect_interval_hours": 6,
        "generate_daily_report": True,
        "report_hour": 8,
    }
}

class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self._data = self._load()

    def _deep_merge(self, base: dict, update: dict) -> dict:
        result = base.copy()
        for k, v in update.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    def _load(self) -> Dict[str, Any]:
        data = DEFAULT_CONFIG.copy()
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    user_cfg = yaml.safe_load(f) or {}
                    data = self._deep_merge(data, user_cfg)
            except Exception as e:
                print(f"加载配置文件 {self.config_path} 失败，使用默认配置: {e}")
        elif os.path.exists("config.example.yaml"):
            try:
                with open("config.example.yaml", "r", encoding="utf-8") as f:
                    example_cfg = yaml.safe_load(f) or {}
                    data = self._deep_merge(data, example_cfg)
            except Exception:
                pass
        return data

    def get(self, *keys, default=None):
        curr = self._data
        for k in keys:
            if isinstance(curr, dict) and k in curr:
                curr = curr[k]
            else:
                return default
        return curr

    @property
    def data(self) -> Dict[str, Any]:
        return self._data
