from pydantic_settings import BaseSettings


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

    # API 限流
    RATE_LIMIT_REQUESTS: int = 30
    RATE_LIMIT_WINDOW: int = 60

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
