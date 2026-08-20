"""
Bilibili 账号认证与凭据管理
支持二维码扫码登录、凭据持久化、有效性校验与自动刷新。
"""
import os
import json
import asyncio
from typing import Optional, Dict, Any
from bilibili_api import Credential, login_v2
from bilibili_api.login_v2 import QrCodeLoginEvents
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
            cred = Credential(
                sessdata=data.get("sessdata"),
                bili_jct=data.get("bili_jct"),
                dedeuserid=data.get("dedeuserid"),
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
                "sessdata": cred.sessdata,
                "bili_jct": cred.bili_jct,
                "dedeuserid": cred.dedeuserid,
                "buvid3": cred.buvid3,
                "ac_time_value": cred.ac_time_value
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
        if cred is None:
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
        if cred is None:
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
        终端扫码登录流程
        在终端打印二维码字符画，同时可选将二维码保存为 qrcode.png 方便查看
        """
        logger.info("正在生成 B 站登录二维码...")
        qr = login_v2.QrCodeLogin()
        await qr.generate_qrcode()

        # 输出终端字符画二维码
        print("\n" + "=" * 40)
        print("请使用 Bilibili 手机客户端扫码登录：")
        print("=" * 40)
        qr.get_qrcode_terminal()
        print("=" * 40 + "\n")

        if save_qr_img:
            qr_img_path = "./data/login_qrcode.png"
            try:
                img = qr.get_qrcode_picture()
                img.save(qr_img_path)
                logger.info(f"二维码图片已保存至: {qr_img_path} (可直接双击打开扫码)")
            except Exception as e:
                logger.debug(f"保存二维码图片略过: {e}")

        logger.info("等待扫码中...")
        while not qr.has_done():
            state = await qr.check_state()
            if state == QrCodeLoginEvents.SCAN:
                logger.info("二维码已扫描，请在手机上点击【确认登录】")
            elif state == QrCodeLoginEvents.TIMEOUT:
                logger.error("二维码已超时失效，请重新执行登录命令！")
                return None
            await asyncio.sleep(2)

        cred = qr.get_credential()
        if cred:
            logger.info("登录成功！正在保存凭据...")
            self.save_credential(cred)
            # 清理临时二维码图片
            if os.path.exists("./data/login_qrcode.png"):
                try:
                    os.remove("./data/login_qrcode.png")
                except Exception:
                    pass
            return cred
        else:
            logger.error("未能获取到凭据，登录失败！")
            return None
