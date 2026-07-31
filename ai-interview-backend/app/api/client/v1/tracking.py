from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Optional
from app.models.page_view import PageView
from app.schemas.response import ApiResponse
import logging
import httpx

router = APIRouter()
logger = logging.getLogger(__name__)


class PageViewRequest(BaseModel):
    page_path: str
    session_id: Optional[str] = None


@router.post("/pageview")
async def track_pageview(
    body: PageViewRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """记录页面浏览（公开接口，支持匿名）"""
    client_ip = _get_client_ip(request)
    background_tasks.add_task(
        _save_pageview, body.page_path, body.session_id, client_ip
    )
    return ApiResponse.success(data=None)


def _get_client_ip(request: Request) -> Optional[str]:
    """从请求头/客户端提取真实 IP（兼容反向代理）"""
    # 优先取 X-Forwarded-For（nginx/Cloudflare 透传）
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # 取第一个（最原始客户端）
        return xff.split(",")[0].strip()
    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        return x_real_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return None


async def _save_pageview(
    page_path: str,
    session_id: Optional[str],
    client_ip: Optional[str],
):
    from app.db.session import async_session
    country = None
    province = None
    # 异步解析地理位置（仅对公网 IP；内网/回环跳过）
    if client_ip and not _is_private_ip(client_ip):
        country, province = await _resolve_geo(client_ip)
    try:
        async with async_session() as db:
            pv = PageView(
                page_path=page_path,
                session_id=session_id,
                ip=client_ip,
                country=country,
                province=province,
            )
            db.add(pv)
            await db.commit()
    except Exception as e:
        logger.warning(f"Failed to save pageview: {e}")


def _is_private_ip(ip: str) -> bool:
    """判断是否为内网/回环地址（无需 geo 解析）"""
    if not ip:
        return True
    try:
        parts = ip.split(".")
        if len(parts) != 4:
            return ":" in ip  # IPv6 本地
        first = int(parts[0])
        if first == 10:
            return True
        if first == 172 and 16 <= int(parts[1]) <= 31:
            return True
        if first == 192 and int(parts[1]) == 168:
            return True
        if ip.startswith("127.") or ip.startswith("169.254."):
            return True
    except (ValueError, IndexError):
        pass
    return False


async def _resolve_geo(ip: str):
    """通过 ip-api.com 解析国家/省份，失败返回 (None, None)"""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "status,country,regionName,countryCode"},
            )
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == "success":
                    return data.get("country"), data.get("regionName")
    except Exception as e:
        logger.debug(f"Geo resolve failed for {ip}: {e}")
    return None, None
