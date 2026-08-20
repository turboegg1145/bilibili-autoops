"""
智能回复引擎
支持基于规则与关键词匹配的快速回复，以及基于大语言模型（LLM）的拟人化回复。
"""
import random
import aiohttp
from typing import Dict, Any, List, Optional, Tuple
from src.utils.logger import logger

POSITIVE_KEYWORDS = [
    "好", "棒", "牛", "厉害", "强", "赞", "支持", "喜欢", "666", 
    "加油", "感谢", "谢谢", "学到了", "神作", "爱了", "收藏了", "投币", "一键三连"
]

class ReplyEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.reply_mode = config.get("reply_mode", "rule")
        self.rules = config.get("rules", [])
        self.default_replies = config.get("default_replies", [
            "感谢小伙伴的评论与支持！💖",
            "收到你的反馈啦，祝你每天开心！✨"
        ])
        self.llm_cfg = config.get("llm", {})

    def is_positive_comment(self, text: str) -> bool:
        """判断评论是否包含正向夸奖/支持情感"""
        text_lower = text.lower()
        for kw in POSITIVE_KEYWORDS:
            if kw in text_lower:
                return True
        return False

    async def generate_reply(self, comment_text: str, user_name: str = "") -> Tuple[str, bool]:
        """
        生成回复文本并判断是否应当点赞
        :return: (reply_text, should_like)
        """
        should_like = self.is_positive_comment(comment_text)

        # 1. 规则匹配优先检查
        for rule in self.rules:
            keywords = rule.get("keywords", [])
            for kw in keywords:
                if kw.lower() in comment_text.lower():
                    replies = rule.get("replies", [])
                    if replies:
                        return random.choice(replies), should_like

        # 2. 如果开启了 LLM 模式且配置了 API
        if self.reply_mode == "llm" and self.llm_cfg.get("api_key"):
            llm_reply = await self._call_llm(comment_text, user_name)
            if llm_reply:
                return llm_reply, should_like

        # 3. 兜底默认回复
        if self.default_replies:
            return random.choice(self.default_replies), should_like
        return "感谢支持与关注！✨", should_like

    async def _call_llm(self, comment_text: str, user_name: str) -> Optional[str]:
        """调用大模型接口生成个性化回复"""
        api_base = self.llm_cfg.get("api_base", "https://api.openai.com/v1").rstrip("/")
        api_key = self.llm_cfg.get("api_key", "")
        model = self.llm_cfg.get("model", "gpt-4o-mini")
        prompt = self.llm_cfg.get("prompt", "你是B站UP主的AI运营助手，请用友善、风趣且接地气的B站用户口吻简短回复粉丝评论（50字以内）：")

        url = f"{api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"粉丝【{user_name}】说：{comment_text}"}
            ],
            "max_tokens": 100,
            "temperature": 0.7
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        content = data["choices"][0]["message"]["content"].strip()
                        return content
                    else:
                        logger.warning(f"LLM 接口返回非 200 状态: {resp.status}")
        except Exception as e:
            logger.warning(f"调用 LLM 生成回复失败，退化为默认回复: {e}")
        return None
