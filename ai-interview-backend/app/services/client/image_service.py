import os
import uuid
import base64
import logging
from datetime import datetime
from typing import Dict, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.models.image_task import ImageTask
from app.exceptions.http_exceptions import NotFoundError

logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"
GENERATED_IMAGE_DIR = os.path.join(UPLOAD_DIR, "generated-images")
POLLINATIONS_API_URL = "https://apihub.agnes-ai.com/v1/images/generations"


class ImageService:

    @staticmethod
    async def create_task(
        db: AsyncSession,
        user_id: int,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        cfg_scale: int = 7,
    ) -> Dict:
        task = ImageTask(
            user_id=user_id,
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale,
            status="pending",
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return {
            "task_id": task.id,
            "status": task.status,
            "message": "图片生成任务已提交",
        }

    @staticmethod
    async def get_tasks(
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        size: int = 20,
    ) -> Dict:
        offset = (page - 1) * size
        count_result = await db.execute(
            select(func.count(ImageTask.id)).where(ImageTask.user_id == user_id)
        )
        total = count_result.scalar()

        result = await db.execute(
            select(ImageTask)
            .where(ImageTask.user_id == user_id)
            .order_by(ImageTask.created_at.desc())
            .offset(offset)
            .limit(size)
        )
        tasks = result.scalars().all()

        items = [
            {
                "id": t.id,
                "prompt": t.prompt,
                "negative_prompt": t.negative_prompt,
                "width": t.width,
                "height": t.height,
                "steps": t.steps,
                "cfg_scale": t.cfg_scale,
                "status": t.status,
                "image_url": t.image_url,
                "error_message": t.error_message,
                "created_at": t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else None,
            }
            for t in tasks
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "has_more": (page * size) < total,
        }

    @staticmethod
    async def get_task(db: AsyncSession, task_id: int, user_id: int) -> Dict:
        result = await db.execute(
            select(ImageTask).where(ImageTask.id == task_id, ImageTask.user_id == user_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise NotFoundError(message="任务不存在")
        return {
            "id": task.id,
            "prompt": task.prompt,
            "negative_prompt": task.negative_prompt,
            "width": task.width,
            "height": task.height,
            "steps": task.steps,
            "cfg_scale": task.cfg_scale,
            "status": task.status,
            "image_url": task.image_url,
            "error_message": task.error_message,
            "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S") if task.created_at else None,
        }

    @staticmethod
    async def mark_task_failed(db: AsyncSession, task_id: int, user_id: int, message: str) -> None:
        result = await db.execute(
            select(ImageTask).where(ImageTask.id == task_id, ImageTask.user_id == user_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise NotFoundError(message="任务不存在")
        task.status = "failed"
        task.error_message = message[:500]
        await db.commit()

    @staticmethod
    async def delete_task(db: AsyncSession, task_id: int, user_id: int) -> None:
        result = await db.execute(
            select(ImageTask).where(ImageTask.id == task_id, ImageTask.user_id == user_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise NotFoundError(message="任务不存在")

        # 删除图片文件
        if task.image_url:
            file_path = task.image_url.removeprefix("/uploads/")
            full_path = os.path.join(UPLOAD_DIR, file_path)
            if os.path.exists(full_path):
                os.remove(full_path)

        await db.delete(task)
        await db.commit()

    @staticmethod
    async def generate_image(
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 512,
        height: int = 512,
    ) -> bytes:
        """调用 Pollinations API 生成图片，返回图片二进制数据"""
        api_key = settings.POLLINATIONS_API_KEY or os.getenv("POLLINATIONS_API_KEY", "")
        if not api_key:
            raise RuntimeError("图片生成服务未配置，请检查 POLLINATIONS_API_KEY")

        payload = {
            "model": "agnes-image-2.1-flash",
            "prompt": prompt,
            "size": f"{width}x{height}",
            "return_base64": True,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                POLLINATIONS_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text[:200] if exc.response is not None else str(exc)
                raise RuntimeError(f"图片生成接口请求失败（HTTP {exc.response.status_code}）：{detail}") from exc
            result = response.json()
            data_item = result["data"][0]
            # API 可能返回 base64 或 URL
            if data_item.get("b64_json"):
                return base64.b64decode(data_item["b64_json"])
            elif data_item.get("url"):
                img_resp = await client.get(data_item["url"])
                img_resp.raise_for_status()
                return img_resp.content
            else:
                raise ValueError("API 未返回图片数据")

    @staticmethod
    def save_image(image_data: bytes, task_id: int) -> str:
        """保存图片到本地文件系统，返回 URL 路径"""
        date_dir = datetime.now().strftime("%Y%m%d")
        save_dir = os.path.join(GENERATED_IMAGE_DIR, date_dir)
        os.makedirs(save_dir, exist_ok=True)

        filename = f"img_{task_id}_{uuid.uuid4().hex[:8]}.png"
        file_path = os.path.join(save_dir, filename)

        with open(file_path, "wb") as f:
            f.write(image_data)

        return f"/uploads/generated-images/{date_dir}/{filename}"


image_service = ImageService()
