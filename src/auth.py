# src/auth.py
class NotAuthenticated(Exception):
    pass


def ensure_authenticated(client) -> dict:
    """校验登录态;未登录则 fail loud 提示重登。返回 user dict。"""
    data = client.status_raw()
    if not data.get("authenticated"):
        raise NotAuthenticated("未登录,请运行 `xhs login`(或 `xhs login --qrcode`)后重试")
    return data.get("user", {})
