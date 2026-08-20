"""
Bilibili 账号认证与凭据管理
支持二维码扫码登录、凭据持久化、有效性校验与自动刷新。
"""
import os
import json
import asyncio
import urllib.parse
from typing import Optional, Dict, Any
import aiohttp
import qrcode
from bilibili_api import Credential, get_buvid
from src.utils.logger import logger

CREDENTIAL_PATH = "./data/credentials.json"

class AuthManager:
    def __init__(self, cred_file: str = CREDENTIAL_PATH):
        self.cred_file = cred_file
        os.makedirs(os.path.dirname(os.path.abspath(self.cred_file)), exist_ok=True)

    def load_credential(self) -> Optional[Credential]:
        """从本地文件加载凭据"""
        if not os.path.exists(self.cred_file):
            return None
        try:
            with open(self.cred_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            sessdata = data.get("sessdata", "").strip()
            if not sessdata:
                return None

            cred = Credential(
                sessdata=sessdata,
                bili_jct=data.get("bili_jct", "").strip(),
                dedeuserid=data.get("dedeuserid", "").strip(),
                buvid3=data.get("buvid3"),
                ac_time_value=data.get("ac_time_value")
            )
            return cred
        except Exception as e:
            logger.error(f"读取凭据文件失败: {e}")
            return None

    def save_credential(self, cred: Credential) -> bool:
        """保存凭据到本地文件"""
        try:
            data = {
                "sessdata": cred.sessdata or "",
                "bili_jct": cred.bili_jct or "",
                "dedeuserid": str(cred.dedeuserid or ""),
                "buvid3": cred.buvid3 or "",
                "ac_time_value": cred.ac_time_value or ""
            }
            with open(self.cred_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"凭据已安全持久化至: {self.cred_file}")
            return True
        except Exception as e:
            logger.error(f"保存凭据失败: {e}")
            return False

    async def check_valid(self, cred: Optional[Credential] = None) -> bool:
        """检查凭据是否有效"""
        if cred is None:
            cred = self.load_credential()
        if cred is None or not cred.sessdata:
            return False
        try:
            is_valid = await cred.check_valid()
            return is_valid
        except Exception as e:
            logger.warning(f"校验凭据时出错: {e}")
            return False

    async def refresh_if_needed(self, cred: Optional[Credential] = None) -> Optional[Credential]:
        """如果 Cookie 即将过期，尝试自动刷新"""
        if cred is None:
            cred = self.load_credential()
        if cred is None or not cred.sessdata:
            return None
        try:
            need_refresh = await cred.check_refresh()
            if need_refresh:
                logger.info("检测到凭据需要刷新，正在执行自动刷新...")
                await cred.refresh()
                self.save_credential(cred)
                logger.info("凭据刷新成功并已更新存储！")
            return cred
        except Exception as e:
            logger.warning(f"自动刷新凭据失败: {e}")
            return cred

    async def login_with_qrcode(self, save_qr_img: bool = True) -> Optional[Credential]:
        """
        全功能二维码扫码登录
        直接从 B站官方响应中同时提取 Set-Cookie 与 CrossDomain 参数，彻底杜绝字段为空的问题。
        """
        logger.info("正在生成 B 站登录二维码...")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/"
        }

        # 禁用系统错误代理
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector, headers=headers, trust_env=False) as session:
            # 1. 获取二维码密钥
            gen_url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
            async with session.get(gen_url) as resp:
                if resp.status != 200:
                    logger.error(f"请求二维码失败，HTTP 状态码: {resp.status}")
                    return None
                gen_data = await resp.json()

            data_obj = gen_data.get("data", {})
            qr_url = data_obj.get("url", "")
            qrcode_key = data_obj.get("qrcode_key", "")

            if not qr_url or not qrcode_key:
                logger.error("未能获取到二维码 URL 或 Key")
                return None

            # 2. 终端打印二维码
            print("\n" + "=" * 50)
            print("请使用 Bilibili 手机客户端扫码登录：")
            print("=" * 50)
            qr_gen = qrcode.QRCode(border=2)
            qr_gen.add_data(qr_url)
            qr_gen.print_ascii(invert=True)
            print("=" * 50 + "\n")

            # 3. 保存二维码图片并尝试打开
            qr_img_path = "./data/login_qrcode.png"
            if save_qr_img:
                try:
                    img = qr_gen.make_image()
                    img.save(qr_img_path)
                    logger.info(f"二维码图片已保存至: {qr_img_path}")
                    if hasattr(os, "startfile"):
                        try:
                            os.startfile(os.path.abspath(qr_img_path))
                        except Exception:
                            pass
                except Exception as e:
                    logger.debug(f"保存二维码图片略过: {e}")

            # 4. 轮询登录状态
            logger.info("等待扫码中... (请在手机B站App点击【确认登录】)")
            poll_url = f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={qrcode_key}"

            while True:
                await asyncio.sleep(2)
                async with session.get(poll_url) as poll_resp:
                    if poll_resp.status != 200:
                        continue

                    res_json = await poll_resp.json()
                    poll_data = res_json.get("data", {})
                    code = poll_data.get("code")

                    if code == 86101:
                        # 未扫码
                        continue
                    elif code == 86090:
                        logger.info("📱 二维码已扫描，请在手机上点击【确认登录】")
                    elif code == 86038:
                        logger.error("❌ 二维码已过期，请重新发起登录！")
                        return None
                    elif code == 0:
                        # 登录成功！
                        logger.info("🎉 扫码确认成功！正在提取凭据信息...")

                        # 优先从 HTTP Set-Cookie 提取
                        cookies = {c.key: c.value for c in session.cookie_jar}
                        sessdata = cookies.get("SESSDATA", "")
                        bili_jct = cookies.get("bili_jct", "")
                        dedeuserid = cookies.get("DedeUserID", "")
                        buvid3 = cookies.get("buvid3", "")
                        refresh_token = poll_data.get("refresh_token", "")

                        # 如果 Cookie 里没有，从 crossDomain URL query 中解析
                        redirect_url = poll_data.get("url", "")
                        if redirect_url and "?" in redirect_url:
                            query_params = urllib.parse.parse_qs(redirect_url.split("?", 1)[1])
                            if not sessdata and "SESSDATA" in query_params:
                                sessdata = query_params["SESSDATA"][0]
                            if not bili_jct and "bili_jct" in query_params:
                                bili_jct = query_params["bili_jct"][0]
                            if not dedeuserid and "DedeUserID" in query_params:
                                dedeuserid = query_params["DedeUserID"][0]

                        # 补充 buvid3 指纹
                        if not buvid3:
                            try:
                                b3, _ = await get_buvid()
                                buvid3 = b3
                            except Exception:
                                pass

                        if not sessdata:
                            logger.error("未能成功解析到 SESSDATA 凭据！")
                            return None

                        cred = Credential(
                            sessdata=sessdata,
                            bili_jct=bili_jct,
                            dedeuserid=dedeuserid,
                            buvid3=buvid3,
                            ac_time_value=refresh_token
                        )

                        # 保存并验证
                        self.save_credential(cred)
                        if os.path.exists(qr_img_path):
                            try:
                                os.remove(qr_img_path)
                            except Exception:
                                pass
                        return cred

    def manual_set_cookie(self, sessdata: str, bili_jct: str = "", dedeuserid: str = "", buvid3: str = "") -> Credential:
        """手动设置 Cookie 凭据"""
        cred = Credential(
            sessdata=sessdata.strip(),
            bili_jct=bili_jct.strip(),
            dedeuserid=dedeuserid.strip(),
            buvid3=buvid3.strip()
        )
        self.save_credential(cred)
        return cred
