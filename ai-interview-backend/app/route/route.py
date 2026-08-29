from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
# 路由导入已移动到路由注册中心统一管理
from app.core.config import settings
from app.configs.docs_apps import create_client_app, create_backoffice_app
from fastapi.exceptions import RequestValidationError
from app.exceptions.http_exceptions import APIException
from app.schemas.response import ApiResponse
from contextlib import asynccontextmanager
from app.core.log_config import setup_logging, shutdown_logging, is_master_process
from app.services.common.redis import redis_client
from app.services.common.thread_pool import thread_pool_service
from app.db.base import close_db_engine
from app.schedule.schedule import setup_scheduler, shutdown_scheduler
from app.services.common.setting_service import get_setting_bool
import logging
from app.common.log_consumer import consume_logs_forever
import threading
import asyncio

logger = logging.getLogger(__name__)

# 根据环境设置CORS来源
if settings.ENV in ("development", "preview"):
    ALLOWED_ORIGINS = ["*"]
else:
    # 生产环境: 从 FRONTEND_URL 解析允许的来源
    _frontend = settings.FRONTEND_URL.rstrip("/")
    ALLOWED_ORIGINS = [_frontend]
    # 如果有额外的管理后台域名, 可以在这里添加


@asynccontextmanager
async def lifespan(application: FastAPI):
    # 启动时执行
    setup_logging()
    logger.info("Application starting up")

    # 日志消费线程（仅主进程启动，防止多进程重复）
    if is_master_process():
        try:
            # 创建一个包装函数在线程中运行异步函数
            def run_log_consumer():
                asyncio.run(consume_logs_forever())
                
            log_thread = threading.Thread(target=run_log_consumer, daemon=True)
            log_thread.start()
            logger.info("[LogConsumer] 日志消费线程已启动（主进程）")
        except Exception as e:
            logger.warning(f"[LogConsumer] 启动日志消费线程失败: {e}")

    # 单进程运行定时任务是打开下面的代码，多进程运行定时任务是关闭下面的代码使用celery_worker来运行
    # 初始化定时任务调度器（仅主进程启动）
    # if is_master_process():
    #     setup_scheduler(application)
    #     logger.info("任务调度器已初始化（主进程）")
    # else:
    #     logger.debug("当前为工作进程，跳过任务调度器初始化")

    yield  # 应用运行期间

    # 关闭时执行
    if is_master_process():
        shutdown_logging()  # 关闭日志
        # shutdown_scheduler()  # 关闭定时任务调度器
    await close_db_engine()  # 清理数据库引擎
    await redis_client.close()  # 关闭Redis连接
    thread_pool_service.shutdown()  # 关闭邮件线程池
    logger.info("Application shutting down")

"""
lifespan函数定义了应用的生命周期管理逻辑：
应用启动时：执行初始化操作（只执行一次）
连接数据库
加载配置 / 模型
初始化缓存、消息队列
创建全局资源
应用关闭时：执行清理操作（只执行一次）
关闭数据库连接
释放资源、关闭文件句柄
断开消息队列连接
它是一个上下文管理器，会在应用整个生命周期内生效。"""
def create_app():
    app = FastAPI(
        lifespan=lifespan,
        title=settings.PROJECT_NAME,
        description="FastAPI Template - 统一入口",
        version="1.0.0",
        docs_url=None,  # 禁用默认文档
        redoc_url=None,  # 禁用默认ReDoc
        openapi_url=None,  # 禁用默认OpenAPI
    )

    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,  # 在生产环境中应该设置具体的域名
        allow_credentials=True,  #是否带 cookie
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 用户活跃度追踪中间件
    class ActivityTrackingMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            # 仅追踪客户端 API 请求
            path = request.url.path
            if not path.startswith("/api/v1/") or path.startswith("/api/v1/backoffice"):
                return response
            # 提取 token
            auth_header = request.headers.get("authorization", "")
            if not auth_header.startswith("Bearer "):
                return response
            token = auth_header[7:]
            try:
                from app.core.security import AuthBase as _Auth
                payload = _Auth.verify_token(token, scope="client")
                if not payload:
                    return response
                user_id = payload.get("sub")
                if not user_id:
                    return response
                # Redis 节流：每用户每 5 分钟才写一次 DB
                throttle_key = f"activity:{user_id}"
                exists = await redis_client.get(throttle_key)
                if not exists:
                    await redis_client.set_with_ttl(throttle_key, "1", ttl_seconds=300)
                    # 异步更新 last_active_at（不阻塞响应）
                    from app.db.session import async_session
                    from sqlalchemy import update
                    from app.models.user import User
                    from datetime import datetime, UTC
                    async with async_session() as session:
                        await session.execute(
                            update(User).where(User.id == int(user_id)).values(last_active_at=datetime.now(UTC))
                        )
                        await session.commit()
            except Exception:
                pass  # 不影响正常请求
            return response

    app.add_middleware(ActivityTrackingMiddleware)

    # 维护模式 & 功能开关中间件
    @app.middleware("http")
    async def feature_toggle_middleware(request: Request, call_next):
        path = request.url.path
        # 仅拦截客户端 API，放行后台、健康检查、站点配置、文档
        if (
            path.startswith("/api/v1/")
            and not path.startswith("/api/v1/backoffice")
            and not path.startswith("/api/v1/config/health")
            and not path.startswith("/api/v1/config/site-info")
            and not path.startswith("/api/v1/config/release")
            and not path.startswith("/client/")
            and not path.startswith("/backoffice/")
            and not path.startswith("/api-docs/")
            and not path.startswith("/uploads/")
        ):
            try:
                # 维护模式：拦截所有客户端 API
                if await get_setting_bool("maintenance_mode", False):
                    return ApiResponse.failed(
                        message="系统维护中，请稍后再试",
                        body_code=503,
                        http_code=status.HTTP_503_SERVICE_UNAVAILABLE
                    )
                # 注册开关：拦截注册相关接口
                if path in ("/api/v1/auth/register", "/api/v1/auth/send-verification-code"):
                    if not await get_setting_bool("register_enabled", True):
                        return ApiResponse.failed(
                            message="注册功能已关闭",
                            body_code=403,
                            http_code=status.HTTP_403_FORBIDDEN
                        )
                # 游客模式开关：拦截游客登录
                if path == "/api/v1/auth/guest":
                    if not await get_setting_bool("guest_enabled", True):
                        return ApiResponse.failed(
                            message="游客模式已关闭",
                            body_code=403,
                            http_code=status.HTTP_403_FORBIDDEN
                        )
            except Exception:
                pass  # settings 读取失败时放行，不阻塞正常请求
        return await call_next(request)

    # 开发环境提供文档访问指引，生产环境隐藏
    if settings.ENV in ["development", "preview"]:
        @app.get("/", tags=["文档导航"])
        async def swagger_navigation():
            """
            开发环境 Swagger 文档导航
            """
            return {
                "message": "FastAPI Template - 开发环境",
                "environment": settings.ENV,
                "documentation": {
                    "client_api": {
                        "swagger": "/client/docs",
                        "redoc": "/client/redoc",
                        "openapi": "/client/openapi.json",
                        "description": "客户端API文档（无需认证）"
                    },
                    "backoffice_api": {
                        "swagger": "/backoffice/docs",
                        "redoc": "/backoffice/redoc",
                        "openapi": "/backoffice/openapi.json",
                        "description": "后台管理API文档（需要JWT认证）"
                    }
                },
                "api_exports": {
                    "client_json": "/api-docs/client.json",
                    "backoffice_json": "/api-docs/backoffice.json",
                    "info": "/api-docs/"
                },
                "health_check": "/api/v1/config/health"
            }

    # 使用路由注册中心统一注册所有路由
    from app.route.router_registry import register_routes, get_client_routes, get_backoffice_routes, get_common_routes

    # 注册客户端路由
    register_routes(app, get_client_routes())

    # 注册后台路由
    register_routes(app, get_backoffice_routes())

    # 注册公共路由
    register_routes(app, get_common_routes())

    # 挂载分离的文档应用
    client_docs_app = create_client_app()
    backoffice_docs_app = create_backoffice_app()
    
    app.mount("/client", client_docs_app)
    app.mount("/backoffice", backoffice_docs_app)

    # 仅公开可安全直链访问的上传子目录，简历和媒体文件必须走鉴权接口。
    from fastapi.staticfiles import StaticFiles
    import os
    os.makedirs("uploads/avatars", exist_ok=True)
    os.makedirs("uploads/notes", exist_ok=True)
    os.makedirs("uploads/generated-images", exist_ok=True)
    app.mount("/uploads/avatars", StaticFiles(directory="uploads/avatars"), name="uploads_avatars")
    app.mount("/uploads/notes", StaticFiles(directory="uploads/notes"), name="uploads_notes")
    app.mount("/uploads/generated-images", StaticFiles(directory="uploads/generated-images"), name="uploads_generated_images")

    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        logger.error(f"API Exception: {exc.status_code} - {exc.code} - {exc.detail}",
                    extra={"request": f"{request.method} {request.url}"})
        return ApiResponse.failed(
            message=exc.detail,
            body_code=exc.code,  # 业务错误码
            http_code=exc.status_code,
            data=exc.data
        )
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}",
                    extra={"request": f"{request.method} {request.url}"})
        return ApiResponse.failed(
            message=exc.detail,
            body_code=exc.status_code,  # 回落使用 HTTP 状态码
            http_code=exc.status_code,
            data=None
        )
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation Error: {exc.errors()}",
                    extra={"request": f"{request.method} {request.url}"})
        errors = exc.errors()
        if errors:
            first = errors[0]
            msg = first.get('msg', '')
            if msg.startswith('Value error, '):
                msg = msg[len('Value error, '):]
            if not msg:
                msg = '参数验证错误'
        else:
            msg = '参数验证错误'
        return ApiResponse.failed(
            message=msg,
            body_code=1001,
            http_code=status.HTTP_400_BAD_REQUEST,
            data=errors
        )
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled Exception: {str(exc)}",
                        extra={"request": f"{request.method} {request.url}"})
        return ApiResponse.failed(
            message="服务器内部错误",
            body_code=1005,
            http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    return app
