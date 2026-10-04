"""请求相关的公共工具。"""

from typing import Optional

from fastapi import Request


def get_client_ip(request: Request) -> Optional[str]:
    """提取真实客户端 IP，兼容反向代理。

    信任顺序：X-Real-IP -> X-Forwarded-For 的最后一段 -> socket 对端地址。

    为什么不取 X-Forwarded-For 的第一段：nginx 用 `$proxy_add_x_forwarded_for` 时会把
    真实 IP **追加在末尾**，而客户端自己发来的 X-Forwarded-For 会被原样保留在前面 ——
    也就是说第一段完全由请求方控制。拿它做限流/锁定，攻击者每次换一个伪造值即可绕过。
    本项目的 nginx 额外用 `proxy_set_header X-Real-IP $remote_addr` 覆盖式写入该头，
    请求方无法伪造，因此优先采用。
    """
    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        return x_real_ip.strip()

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        parts = [part.strip() for part in forwarded.split(",") if part.strip()]
        if parts:
            # 只信任最后一个：它由最近的可信代理写入
            return parts[-1]

    if request.client and request.client.host:
        return request.client.host
    return None
