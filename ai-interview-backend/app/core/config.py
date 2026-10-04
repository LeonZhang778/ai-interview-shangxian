from pydantic import model_validator
from pydantic_settings import BaseSettings

# 被视为「未配置」的占位密钥集合。生产环境命中其一即拒绝启动。
# 背景：config.py 曾长期以 "your-secret-key-change-in-production" 作为默认值，
# 而部署脚本写入的 .env 不含也不校验 SECRET_KEY —— 一旦服务器 .env 缺这一行，
# 全站 JWT 就可用这个公开常量伪造（security.py / waiting_list.py 共 4 处共用）。
WEAK_SECRET_KEYS = {
    "",
    "your-secret-key-change-in-production",
    "change-me",
    "changeme",
    "secret",
    "secret-key",
    "dev",
    "development",
}

# 生产环境 SECRET_KEY 的最小长度（字符）。token_urlsafe(64) 约 86 字符。
MIN_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    # 环境配置
    ENV: str = "development"  # 默认值为 "development"

    # 基础配置
    PROJECT_NAME: str = "FastAPI Template"
    API_V1_STR: str = "/api/v1"
    API_PORT: int = 8006
    FRONTEND_URL: str = "http://localhost:3000"
    # API worker 数量通过环境变量配置。生产环境默认单 worker，避免小规格服务器

    API_WORKERS: int = 1

    NGINX_HTTP_PORT: int = 8086
    NGINX_HTTPS_PORT: int = 8446
    FLOWER_PORT: int = 5556

    # 数据库配置
    POSTGRES_USER: str = "demo"
    POSTGRES_PASSWORD: str = "demo123"
    POSTGRES_HOST: str = "192.168.110.90"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "demo"

    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    # Celery 配置
    CELERY_BROKER_URL: str = ""  # 在 __init__ 中设置
    CELERY_RESULT_BACKEND: str = ""  # 在 __init__ 中设置

    # HTTP 代理配置 - 仅在测试环境使用
    USE_HTTP_PROXY: bool = False  # 默认不使用代理
    HTTP_PROXY: str = "http://127.0.0.1:7890"
    HTTPS_PROXY: str = "http://127.0.0.1:7890"

    # 邮件配置
    MAIL_MAILER: str = "smtp"
    MAIL_HOST: str = "localhost"
    MAIL_PORT: int = 1025
    MAIL_USERNAME: str = "user"
    MAIL_PASSWORD: str = "password"
    MAIL_FROM_ADDRESS: str = "noreply@example.com"
    MAIL_FROM_NAME: str = "Seiki"
    MAIL_ENCRYPTION: str = "none"

    # Brevo 配置
    BREVO_API_KEY: str = "dummy-api-key"
    BREVO_EMAIL_FROM: str = "noreply@example.com"
    BREVO_EMAIL_FROM_NAME: str = "Seiki"

    # 管理员邮箱
    ADMIN_EMAIL: str = "dev@zetos.fr"

    # JWT 配置
    # ⚠️ 此默认值仅供本地开发使用。ENV=production 时若仍为该值（或空、或长度不足），
    #    应用会在启动阶段直接抛错拒绝启动，详见下方 _validate_secret_key。
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # S3 配置
    AWS_ACCESS_KEY_ID: str = "your-access-key"
    AWS_SECRET_ACCESS_KEY: str = "your-secret-key"
    AWS_REGION: str = "us-east-1"
    AWS_BUCKET_NAME: str = "your-bucket-name"
    AWS_ENDPOINT: str = "https://s3.amazonaws.com"

    # OpenAI 配置
    OPENAI_API_KEY: str = "your-openai-api-key"

    # 图片生成服务配置
    POLLINATIONS_API_KEY: str = ""

    # AI 配置（OpenAI 兼容接口，默认使用 Grok 中转站）
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://sub.anzhiyu.com/v1"
    AI_MODEL: str = "grok-4.3"
    # 备用模型：主模型不可用时的降级模型，留空则不降级（与 LangGraph 三级容错呼应）
    AI_MODEL_FALLBACK: str = ""
    XAI_API_KEY: str = ""
    GROK_MODELS_BASE_URL: str = ""
    GROK_MODEL: str = "grok-4.3"
    AI_TIMEOUT: int = 30
    # 流式调用的“建连超时”：仅覆盖建立连接/拿到首个响应对象，通常几百毫秒内完成。
    AI_STREAM_CONNECT_TIMEOUT: int = 20
    # 流式调用的“空闲超时”：已建连后，若超过该秒数没有新的 token 到达则判定流已死。
    # 用于避免上游中转断连后僵死（此前只保护建连、token 循环无限等待）。
    AI_STREAM_IDLE_TIMEOUT: int = 30
    AI_MAX_RETRIES: int = 3
    AI_RETRY_MIN_WAIT: int = 1
    AI_RETRY_MAX_WAIT: int = 10

    # 千问 DashScope 通道（供简历解析 / 模拟面试使用）
    # 申请：https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen
    AI_QWEN_API_KEY: str = ""
    AI_QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    AI_QWEN_MODEL: str = "qwen-plus"

    # 会话记忆压缩阈值：对话历史超过该条数时，对较早部分做 LLM 摘要压缩以控制 token
    AI_MEMORY_SUMMARY_THRESHOLD: int = 8

    # 多模态 OCR（扫描件兜底）：留空则禁用；需同时 AI_OCR_ENABLED=True 且环境安装
    # PyMuPDF(fitz) 或 pdf2image + poppler，并配置一个支持视觉的模型（如 qwen-vl-plus）
    AI_VISION_MODEL: str = ""
    AI_OCR_ENABLED: bool = False
    # 扫描件判定阈值：抽取文本低于该字符数且含图片，视为扫描件
    DOC_PARSER_MIN_TEXT_CHARS: int = 30

    # LLM 缓存 TTL（秒）
    LLM_CACHE_TTL_PARSE: int = 3600
    LLM_CACHE_TTL_EVALUATE: int = 1800
    LLM_CACHE_TTL_QUESTIONS: int = 3600
    LLM_CACHE_TTL_REPORT: int = 3600

    # 搜索与重排序配置
    SEARCH_BACKEND: str = "postgres"
    OPENSEARCH_URL: str = ""
    OPENSEARCH_INDEX: str = "learning_notes"
    OPENSEARCH_USERNAME: str = ""
    OPENSEARCH_PASSWORD: str = ""
    RERANKER_URL: str = ""
    RERANKER_TIMEOUT: int = 5

    # 面试会话缓存
    INTERVIEW_SESSION_TTL: int = 7200

    # API 限流（每个用户的滑动窗口）。按单次调用的成本分档 —— 成本越高、窗口越严。
    # 成本参考：简历解析要跑长文本、可能还要 OCR 兜底；生图要消耗外部服务配额；
    # 面试答题 / 笔记摘要 / 标签推荐 / 面经出题各自只跑一次 LLM。
    RATE_LIMIT_REQUESTS: int = 30        # 常规档
    RATE_LIMIT_WINDOW: int = 60          # 所有档位共用的窗口长度（秒）
    RATE_LIMIT_HEAVY_REQUESTS: int = 10  # 高成本档：简历解析
    RATE_LIMIT_IMAGE_REQUESTS: int = 5   # 生图档：消耗外部 API 配额

    # 登录失败锁定：按「邮箱」与「来源 IP」两个维度独立计数，固定窗口。
    # 此前登录失败没有任何次数限制，可以无限次爆破密码。
    # 说明：成功登录只清零邮箱维度 —— IP 维度可能承载着别人的失败尝试，
    # 若成功一次就清空，爆破者只要用自己的账号登录成功即可重置 IP 计数。
    LOGIN_FAIL_MAX_PER_EMAIL: int = 10   # 同一邮箱累计失败上限
    LOGIN_FAIL_MAX_PER_IP: int = 30      # 同一来源 IP 累计失败上限（跨邮箱撞库）
    LOGIN_FAIL_WINDOW: int = 600         # 计数窗口（秒），窗口滑过后自动解锁

    # 媒体工具配置
    MEDIA_UPLOAD_DIR: str = "uploads/media"
    MEDIA_MAX_FILE_SIZE_MB: int = 500
    MEDIA_TEMP_DIR: str = "uploads/media/tmp"
    MEDIA_RESULT_EXPIRY_HOURS: int = 24
    MEDIA_CELERY_QUEUE: str = "media_tasks"
    MEDIA_WORKER_CONCURRENCY: int = 2

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"  # 可选，指定编码

    @model_validator(mode="after")
    def _validate_secret_key(self):
        """生产环境必须持有独立的强随机 SECRET_KEY，否则拒绝启动。

        设计取舍：宁愿部署失败（可在 CI 日志里立刻看到原因），也不要带着
        可被公开常量伪造的密钥把服务跑起来——后者是完全静默的。
        """
        env = (self.ENV or "").strip().lower()
        if env not in {"production", "prod"}:
            return self

        key = (self.SECRET_KEY or "").strip()
        if key.lower() in WEAK_SECRET_KEYS:
            raise ValueError(
                "SECRET_KEY 未配置或仍为占位值，生产环境拒绝启动。"
                "请在部署机 .env 中设置独立强随机密钥，例如："
                'python3 -c "import secrets;print(secrets.token_urlsafe(64))"'
            )
        if len(key) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"SECRET_KEY 强度不足（当前 {len(key)} 字符，要求 >= "
                f"{MIN_SECRET_KEY_LENGTH}）。请更换为强随机密钥。"
            )
        return self

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.XAI_API_KEY:
            self.AI_API_KEY = self.XAI_API_KEY
        if self.GROK_MODELS_BASE_URL:
            self.AI_BASE_URL = self.GROK_MODELS_BASE_URL
        if (self.XAI_API_KEY or self.GROK_MODELS_BASE_URL) and self.AI_MODEL == "qwen-plus":
            self.AI_MODEL = self.GROK_MODEL
        # 在所有属性从 env 加载后设置 Celery URL
        if self.REDIS_PASSWORD:
            redis_url = (
                f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
            )
        else:
            redis_url = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        self.CELERY_BROKER_URL = redis_url
        self.CELERY_RESULT_BACKEND = redis_url


settings = Settings()
