"""方案2 第一步:一次性扫码登录。
打开一个全新浏览器,你在里面登录小红书(扫码/手机号),
脚本检测到登录后把登录态保存到 .secrets/xhs_storage_state.json 供后续复用。

运行(在你自己的终端):
    python scripts/pw_login.py
"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

STATE = Path(".secrets/xhs_storage_state.json")
USER_ME = "https://edith.xiaohongshu.com/api/sns/web/v2/user/me"
TIMEOUT_S = 300


def _is_logged_in(ctx) -> bool:
    """真正判断登录:调 user/me,guest==False 且有 user_id 才算登录。
    (注意: 匿名也有 web_session cookie,不能用 cookie 判断。)"""
    try:
        resp = ctx.request.get(USER_ME)
        data = (resp.json() or {}).get("data") or {}
        return data.get("guest") is False and bool(data.get("user_id") or data.get("red_id"))
    except Exception:
        return False


def main() -> int:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto("https://www.xiaohongshu.com/", wait_until="domcontentloaded")
        print("请在弹出的浏览器里完成登录(扫码或手机号)。")
        print("脚本会持续检测真实登录态(user/me),登录成功后自动保存,请勿手动关闭浏览器…")

        deadline = time.time() + TIMEOUT_S
        logged_in = False
        while time.time() < deadline:
            if _is_logged_in(ctx):
                logged_in = True
                break
            remaining = int(deadline - time.time())
            print(f"  等待登录中… 还剩 {remaining}s", end="\r")
            time.sleep(3)

        if not logged_in:
            print(f"\n超时({TIMEOUT_S}s)仍未检测到真实登录。请重跑并完成扫码。")
            browser.close()
            return 1

        ctx.storage_state(path=str(STATE))
        print(f"\n登录成功(已验证 user/me)!登录态已保存到 {STATE}")
        browser.close()
        return 0


if __name__ == "__main__":
    sys.exit(main())
