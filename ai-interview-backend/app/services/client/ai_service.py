import json
import logging
import asyncio
from typing import Dict, List, Optional
from openai import AsyncOpenAI
from app.core.config import settings
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_not_exception_type,
    before_sleep_log,
)
from app.prompts.interview import (
    RESUME_PARSE_PROMPT,
    RESUME_ANALYZE_PROMPT,
    INTERN_LEVEL_HINT,
    NORMAL_LEVEL_HINT,
    GENERATE_QUESTIONS_PROMPT,
    JOB_GAP_ANALYSIS_PROMPT,
    INTERN_POSITION_HINT,
    NORMAL_POSITION_HINT,
    GENERATE_QUESTIONS_FROM_EXPERIENCE_PROMPT,
    EVALUATE_PROMPT,
    EVALUATE_STREAM_PROMPT,
    REPORT_PROMPT,
)

logger = logging.getLogger(__name__)

# 使用 OpenAI 兼容 API
# - client：默认通道（现为 DeepSeek），供全部业务调用
# - qwen_client：历史千问 DashScope 槽位，已停用。AI_QWEN_API_KEY 留空时
#   所有 provider="qwen" 的调用自动落回默认通道，无需改调用点。
client = AsyncOpenAI(
    api_key=settings.AI_API_KEY,
    base_url=settings.AI_BASE_URL
)

qwen_client = AsyncOpenAI(
    api_key=settings.AI_QWEN_API_KEY,
    base_url=settings.AI_QWEN_BASE_URL
)


def _resolve_provider(provider: str):
    """
    按通道名解析出 (client, model)。

    千问通道未配置 key 时降级到默认通道，避免整块功能不可用。
    当前生产已将 AI_QWEN_API_KEY 置空，历史 provider="qwen" 调用统一走默认通道。

    Args:
        provider: "qwen" 走历史千问槽位，其它值走默认通道

    Returns:
        (AsyncOpenAI 客户端, 模型名称)
    """
    if provider == "qwen":
        if settings.AI_QWEN_API_KEY:
            return qwen_client, settings.AI_QWEN_MODEL
        # 预期行为（千问通道已停用），用 debug 避免每道题刷一条 warning
        logger.debug("AI_QWEN_API_KEY 未配置，改用默认通道")
    return client, settings.AI_MODEL


class AIService:
    """OpenAI 兼容 AI 服务 - 面试模拟核心"""

    # 诚实跳过的关键词（坦诚说不会，应该给机会）
    HONEST_SKIP_KEYWORDS = ["不知道", "不会", "不清楚", "不太了解", "不太清楚", "没学过", "没接触过", "不记得", "跳过"]
    # 胡说八道的关键词（空洞回答）
    EMPTY_TALK_KEYWORDS = ["嗯", "对", "是的", "好的", "知道了"]
    # 关键词预判只对短回答生效。超过此长度一律视为「正常作答」，不再做关键词判定。
    # 因为「不会 / 跳过 / 不清楚」在正常技术表述里极其常见
    #（如"session 不会长期持有连接""跳过已过期的 key"），对长回答做子串匹配会误判。
    MAX_SKIP_KEYWORD_LEN = 40

    @staticmethod
    def pre_score(answer: str) -> Optional[tuple]:
        """
        预判断：分级评分，区分诚实跳过和胡说八道。

        仅用于 AI 不可用时的降级路径（_fallback_evaluate）；
        主评估路径不做关键词短路，评分语义统一交给 AI 按提示词判断
        （坦诚跳过的 4-5 / 2-3 分分档规则已写入 EVALUATE_STREAM_SYSTEM）。

        Returns:
            None: 继续 AI 评估 / 走兜底
            (score, skip_type): 直接返回分数和类型
        """
        text = answer.strip()

        # 空回答 → 1 分
        if not text:
            return (1.0, "empty")

        # 长回答不做关键词判定，避免误伤正常技术表述
        if len(text) > AIService.MAX_SKIP_KEYWORD_LEN:
            return None

        # 空洞回答（只有"嗯"、"对"等）→ 1 分
        if text in AIService.EMPTY_TALK_KEYWORDS:
            return (1.0, "empty_talk")

        # 诚实跳过：只有"不知道"没有其他内容 → 3 分（给机会，不重罚）
        for kw in AIService.HONEST_SKIP_KEYWORDS:
            if kw in text and len(text) < 15:
                return (3.0, "honest_skip")

        # 诚实跳过但尝试解释："不太清楚，但我觉得应该是..." → 4 分
        for kw in AIService.HONEST_SKIP_KEYWORDS:
            if kw in text and len(text) >= 15:
                return (4.0, "partial_attempt")

        # 太短（< 3 字）→ 1 分。放在诚实跳过之后，避免“不会”被误判为过短。
        if len(text) < 3:
            return (1.0, "too_short")

        return None  # 继续 AI 评估

    @staticmethod
    def pre_score_feedback(skip_type: str) -> str:
        """预判断评分的用户可见反馈。"""
        feedback_map = {
            "empty": "回答为空，请尽量给出你的理解和思路。",
            "too_short": "回答内容过短，请尽量补充关键思路、技术细节或项目例子。",
            "empty_talk": "回答内容过于空泛，请尝试说明你的判断依据和解决思路。",
            "honest_skip": "已记录为坦诚跳过，这类回答会给基础分；后续题目可以继续补充你的思路。",
            "partial_attempt": "已记录为部分尝试回答，建议继续补充技术细节、取舍依据或项目例子。",
        }
        return feedback_map.get(skip_type, "已使用基础评分，请继续完成后续题目。")

    @staticmethod
    def post_process_score(score: float, answer: str, skip_type: str = None) -> float:
        """
        对 AI 返回的分数做合理性校验

        Args:
            score: AI 返回的分数
            answer: 候选人回答
            skip_type: pre_score 返回的跳过类型
        """
        text = answer.strip()

        # 诚实跳过的分数保护：不低于 3 分
        if skip_type == "honest_skip":
            return max(3.0, min(5.0, score))
        if skip_type == "partial_attempt":
            return max(4.0, min(6.0, score))

        # 胡说八道（很短但没说不会）→ 低分
        if len(text) < 10 and score > 4:
            return min(score, 3.0)

        return max(1.0, min(10.0, round(score, 1)))

    @staticmethod
    @retry(
        # 超时不重试：单次已等满 timeout，再重试只会把总耗时成倍放大。
        # 实测 DeepSeek-V4 推理模型一次岗位差距分析约 27-38s，重试 3 次把
        # /interviews/start 拖到 105s，前端 60s 先超时并显示「题目生成失败」。
        retry=retry_if_exception_type(Exception)
        & retry_if_not_exception_type((TimeoutError, asyncio.TimeoutError)),
        stop=stop_after_attempt(settings.AI_MAX_RETRIES),
        wait=wait_exponential(min=settings.AI_RETRY_MIN_WAIT, max=settings.AI_RETRY_MAX_WAIT),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _call_model(
        messages: list,
        temperature: float,
        model: str,
        provider: str = "default",
        *,
        max_tokens: int = 4096,
        reasoning_effort: Optional[str] = None,
        response_format: Optional[dict] = None,
        timeout: Optional[float] = None,
    ) -> str:
        """底层单次模型调用（含超时与空响应处理），供主/备模型复用。

        Args:
            provider: "qwen" 走千问通道，其它值走默认通道
            max_tokens: 输出上限。推理模型会把额度消耗在 reasoning 上，过小会导致
                content 为空（DeepSeek-V4 默认 effort=high 时实测如此，只剩 reasoning_content）
            reasoning_effort: 透传 low/high/max，降低推理模型耗时
            response_format: 透传给上游，如 {"type": "json_object"} 强约束返回对象
            timeout: 单次调用超时秒数，默认取 settings.AI_TIMEOUT
        """
        active_client, _ = _resolve_provider(provider)
        request_kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            request_kwargs["response_format"] = response_format
        if reasoning_effort:
            # 用 extra_body 透传，不依赖 openai SDK 对 reasoning_effort 的版本支持
            request_kwargs["extra_body"] = {"reasoning_effort": reasoning_effort}
        try:
            response = await asyncio.wait_for(
                active_client.chat.completions.create(**request_kwargs),
                timeout=timeout or settings.AI_TIMEOUT,
            )
            msg = response.choices[0].message
            content = msg.content
            # GLM 推理模型可能把内容放在 reasoning_content 里
            if not content or not content.strip():
                reasoning = getattr(msg, "reasoning_content", None)
                if reasoning and reasoning.strip():
                    logger.warning("content 为空，使用 reasoning_content")
                    return reasoning.strip()
                logger.error(f"AI API 返回空响应 model={model}: {response}")
                raise ValueError("AI API 返回了空响应，请稍后重试")
            result = content.strip()
            logger.info(f"AI 响应前 200 字: {result[:200]}")
            return result
        except asyncio.TimeoutError:
            logger.error(f"AI API 调用超时 ({timeout or settings.AI_TIMEOUT}s) model={model}")
            raise TimeoutError("AI API 调用超时")
        except Exception as e:
            logger.error(f"AI API 调用失败 model={model}: {e}")
            raise

    @staticmethod
    async def _call_model_stream(
        messages: list, temperature: float, model: str, provider: str = "default"
    ):
        """底层流式模型调用，供主/备模型复用。

        Args:
            provider: "qwen" 走千问通道，其它值走默认通道
        """
        active_client, _ = _resolve_provider(provider)
        connect_timeout = getattr(settings, "AI_STREAM_CONNECT_TIMEOUT", 20)
        idle_timeout = getattr(settings, "AI_STREAM_IDLE_TIMEOUT", 30)
        try:
            # 建连超时：只覆盖“拿到响应对象”这一步
            stream = await asyncio.wait_for(
                active_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=4096,
                    stream=True,
                ),
                timeout=connect_timeout,
            )
            # 空闲超时：等待每个后续 chunk，若超过 idle_timeout 没有新 token 则判定流已死。
            # 之前这里完全无保护，上游中转断连会导致永久挂起（表现为前端光标一直闪烁）。
            stream_iter = stream.__aiter__()
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        stream_iter.__anext__(), timeout=idle_timeout
                    )
                except StopAsyncIteration:
                    break
                except asyncio.TimeoutError:
                    logger.error(
                        f"AI 流式 API 空闲超时（{idle_timeout}s 无新 token）model={model}"
                    )
                    raise TimeoutError(f"AI 流式 API 空闲超时（{idle_timeout}s 无新 token）")
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except asyncio.TimeoutError:
            logger.error(f"AI 流式 API 建连超时 ({connect_timeout}s) model={model}")
            raise TimeoutError("AI 流式 API 调用超时")
        except Exception as e:
            logger.error(f"AI 流式 API 调用失败 model={model}: {e}")
            raise

    @staticmethod
    async def _chat(
        messages: list, temperature: float = 0.7, provider: str = "default", **kwargs
    ) -> str:
        """基础对话补全调用：按 provider 选通道，主模型失败自动降级到备用模型
        （动态路由 / 模型降级，与三级容错呼应）。

        Args:
            provider: "qwen" 走千问通道，其它值走默认通道
            **kwargs: 透传给 _call_model（max_tokens / reasoning_effort /
                response_format / timeout），主备两次调用使用同一组参数
        """
        _, active_model = _resolve_provider(provider)
        try:
            return await AIService._call_model(
                messages, temperature, active_model, provider, **kwargs
            )
        except Exception as e:
            fallback = getattr(settings, "AI_MODEL_FALLBACK", "")
            if fallback and fallback != active_model:
                logger.warning(
                    f"[模型降级] 主模型 {active_model} 失败，切换备用模型 {fallback}: {e}"
                )
                return await AIService._call_model(
                    messages, temperature, fallback, provider, **kwargs
                )
            raise

    @staticmethod
    async def _chat_stream(messages: list, temperature: float = 0.7, provider: str = "default"):
        """流式对话补全调用：按 provider 选通道，主模型失败自动降级到备用模型（动态路由 / 模型降级）。

        Args:
            provider: "qwen" 走千问通道，其它值走默认通道
        """
        _, active_model = _resolve_provider(provider)
        fallback = getattr(settings, "AI_MODEL_FALLBACK", "")
        use_fallback = bool(fallback) and fallback != active_model
        try:
            async for chunk in AIService._call_model_stream(messages, temperature, active_model, provider):
                yield chunk
        except Exception as e:
            if use_fallback:
                logger.warning(
                    f"[模型降级-stream] 主模型 {active_model} 失败，切换备用模型 {fallback}: {e}"
                )
                async for chunk in AIService._call_model_stream(messages, temperature, fallback, provider):
                    yield chunk
            else:
                raise

    @staticmethod
    def _extract_json(text: str) -> dict:
        """从 AI 响应中提取 JSON，处理各种非标准格式"""
        import re
        text = text.strip()
        if not text:
            raise ValueError("AI 返回了空内容，无法解析为 JSON")
        # 1. 处理 markdown 代码块
        code_block = re.search(r'```(?:json)?\s*\n?([\s\S]*?)```', text)
        if code_block:
            text = code_block.group(1).strip()
        elif text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        # 2. 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # 3. 用 raw_decode 从第一个 { 或 [ 提取
        decoder = json.JSONDecoder()
        for i, ch in enumerate(text):
            if ch in ('{', '['):
                try:
                    obj, end = decoder.raw_decode(text, i)
                    return obj
                except json.JSONDecodeError:
                    continue
        logger.error(f"JSON 提取失败，AI 响应前 300 字: {text[:300]}")
        raise ValueError(f"无法从 AI 响应中提取 JSON")

    @staticmethod
    def _format_history(chat_history: list) -> str:
        """格式化对话历史"""
        history_text = ""
        for msg in chat_history[-6:]:  # 保留最近6条消息，控制 token 用量
            role = "面试官" if msg["role"] == "interviewer" else "候选人"
            history_text += f"{role}: {msg['content']}\n"
        return history_text

    @staticmethod
    async def summarize_history(history: list) -> str:
        """对较早的面试对话历史做 LLM 摘要压缩（记忆压缩），控制注入 prompt 的 token 量。

        Args:
            history: 待压缩的历史消息列表（已剔除近期保留部分）
        Returns:
            压缩后的中文摘要；失败时返回空串（由调用方退回完整历史）。
        """
        if not history:
            return ""
        text = "\n".join(
            f"{'面试官' if m.get('role') == 'interviewer' else '候选人'}: {m.get('content', '')}"
            for m in history
        )
        messages = [
            {
                "role": "system",
                "content": "你是面试对话摘要助手。请压缩下面的面试对话历史，保留关键问答要点、"
                "已确认的能力与已暴露的薄弱点，用简洁中文列出，不超过 200 字。",
            },
            {"role": "user", "content": text},
        ]
        try:
            return (await AIService._chat(messages, temperature=0.2)).strip()
        except Exception as e:
            logger.warning(f"summarize_history 失败: {e}")
            return ""

    @staticmethod
    async def parse_resume(resume_text: str) -> dict:
        """解析简历文本，提取结构化信息（姓名、学历、技能、经历等），带 LLM 缓存"""
        from app.services.common.redis import redis_client

        # 检查缓存
        cache_key = f"parse:{resume_text[:500]}"
        cached = await redis_client.get_llm_cache("parse", cache_key)
        if cached:
            return cached

        messages = [
            {"role": "system", "content": RESUME_PARSE_PROMPT["system"]},
            {"role": "user", "content": RESUME_PARSE_PROMPT["user"].format(resume_text=resume_text)},
        ]
        result = await AIService._chat(messages, temperature=0.3, provider="qwen")
        parsed = AIService._extract_json(result)

        # 写入缓存（TTL 1 小时）
        await redis_client.set_llm_cache("parse", cache_key, parsed, ttl=3600)
        return parsed

    @staticmethod
    async def ocr_image(image_bytes: bytes, model: str, provider: str = "qwen") -> str:
        """多模态 OCR：把图片字节（PNG）交给视觉模型识别，返回文本。
        用于扫描件简历的兜底解析（见 document_parser.ocr_pdf_with_vlm）。

        Args:
            model: 支持视觉的模型名（如 qwen-vl-plus）
            provider: 视觉模型所在通道，默认走千问 DashScope 通道
        """
        import base64

        b64 = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:image/png;base64,{b64}"
        messages = [
            {
                "role": "system",
                "content": "你是文档 OCR 引擎。请准确识别图片中的文字、表格与排版，按阅读顺序输出；"
                           "表格用 Markdown 表示，无明显内容时返回空字符串。",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "请识别这张简历/文档图片的全部内容。"},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ]
        try:
            return await AIService._call_model(messages, 0.2, model, provider)
        except Exception as e:
            logger.error(f"多模态 OCR 失败 model={model}: {e}")
            raise

    @staticmethod
    async def analyze_resume(parsed_resume: dict, target_position: str) -> dict:
        """分析简历质量，给出评分、优劣势和改进建议"""
        is_intern = any(kw in target_position.lower() for kw in ["实习", "intern"])
        level_hint = INTERN_LEVEL_HINT if is_intern else NORMAL_LEVEL_HINT

        messages = [
            {
                "role": "system",
                "content": RESUME_ANALYZE_PROMPT["system"].format(
                    target_position=target_position,
                    level_hint=level_hint,
                ),
            },
            {
                "role": "user",
                "content": RESUME_ANALYZE_PROMPT["user"].format(
                    target_position=target_position,
                    resume_json=json.dumps(parsed_resume, ensure_ascii=False),
                ),
            },
        ]
        result = await AIService._chat(messages, temperature=0.4, provider="qwen")
        return AIService._extract_json(result)

    @staticmethod
    async def analyze_job_gap(
        parsed_resume: dict, target_position: str, job_description: str
    ) -> dict:
        """比较岗位描述和简历，返回可用于出题及报告的结构化差距分析。"""
        messages = [
            {"role": "system", "content": JOB_GAP_ANALYSIS_PROMPT["system"]},
            {
                "role": "user",
                "content": JOB_GAP_ANALYSIS_PROMPT["user"].format(
                    target_position=target_position,
                    job_description=job_description,
                    resume_json=json.dumps(parsed_resume or {}, ensure_ascii=False),
                ),
            },
        ]
        # DeepSeek-V4 默认 effort=high 时会把 4096 tokens 全用在 reasoning 上，
        # 导致 content 为空、只剩 reasoning_content（思考过程），解析出的结构不可用；
        # 单次耗时也贴着 30s 超时线。这里降 effort、提高输出上限、强约束 JSON 对象。
        result = await AIService._chat(
            messages,
            temperature=0.2,
            provider="qwen",
            max_tokens=8192,
            reasoning_effort="low",
            response_format={"type": "json_object"},
            timeout=max(settings.AI_TIMEOUT, 60),
        )
        return AIService._extract_json(result)

    @staticmethod
    async def generate_questions(
        parsed_resume: dict,
        target_position: str,
        difficulty: str,
        count: int,
        gap_analysis: Optional[dict] = None,
    ) -> list:
        """根据简历和目标岗位生成面试题目，带 LLM 缓存"""
        from app.services.common.redis import redis_client

        difficulty_map = {
            "easy": "初级，侧重基础知识和简单项目经验",
            "medium": "中级，涵盖技术深度和项目设计思路",
            "hard": "高级，深入系统设计、性能优化和技术原理"
        }
        difficulty_desc = difficulty_map.get(difficulty, difficulty_map["medium"])

        is_intern = any(kw in target_position for kw in ["实习", "intern", "Intern"])
        position_hint = INTERN_POSITION_HINT if is_intern else NORMAL_POSITION_HINT

        # 检查缓存
        cache_key = json.dumps(
            {
                "version": 2,
                "target_position": target_position,
                "difficulty": difficulty,
                "count": count,
                "resume": parsed_resume or {},
                "gap_analysis": gap_analysis or {},
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        cached = await redis_client.get_llm_cache("questions", cache_key)
        if cached:
            return cached

        messages = [
            {
                "role": "system",
                "content": GENERATE_QUESTIONS_PROMPT["system"].format(
                    target_position=target_position,
                    difficulty_desc=difficulty_desc,
                    position_hint=position_hint,
                    gap_hint=(
                        "请优先验证岗位差距分析中 priority=high 的必备技能，"
                        "并追问简历证据不足的部分。"
                        if gap_analysis else "没有岗位描述差距分析，请按简历和岗位名称正常出题。"
                    ),
                ),
            },
            {
                "role": "user",
                "content": GENERATE_QUESTIONS_PROMPT["user"].format(
                    resume_json=json.dumps(parsed_resume, ensure_ascii=False),
                    target_position=target_position,
                    count=count,
                    gap_analysis=json.dumps(gap_analysis or {}, ensure_ascii=False),
                ),
            },
        ]
        # 出题契约必须是裸 JSON 数组，不能加 response_format=json_object；
        # 仅提高输出上限，避免推理模型把额度烧在 reasoning 上导致 content 为空。
        result = await AIService._chat(
            messages, temperature=0.7, provider="qwen", max_tokens=8192
        )
        questions = AIService._extract_json(result)

        # 写入缓存（TTL 1 小时）
        await redis_client.set_llm_cache("questions", cache_key, questions, ttl=3600)
        return questions

    @staticmethod
    async def generate_questions_from_experience(
        title: str,
        company: str,
        position: str,
        content: str,
        count: int = 5
    ) -> list:
        """根据面经内容生成同类型面试题，带 LLM 缓存"""
        from app.services.common.redis import redis_client

        cache_key = f"exp_questions:{company}:{position}:{count}"
        cached = await redis_client.get_llm_cache("exp_questions", cache_key)
        if cached:
            return cached

        messages = [
            {
                "role": "system",
                "content": GENERATE_QUESTIONS_FROM_EXPERIENCE_PROMPT["system"].format(
                    company=company,
                    position=position,
                ),
            },
            {
                "role": "user",
                "content": GENERATE_QUESTIONS_FROM_EXPERIENCE_PROMPT["user"].format(
                    title=title,
                    company=company,
                    position=position,
                    content=content[:3000],
                    count=count,
                ),
            },
        ]
        result = await AIService._chat(messages, temperature=0.7, provider="qwen")
        questions = AIService._extract_json(result)

        # 写入缓存（TTL 1 小时）
        await redis_client.set_llm_cache("exp_questions", cache_key, questions, ttl=3600)
        return questions

    @staticmethod
    async def evaluate_answer(
        question: str,
        answer: str,
        resume_context: dict,
        chat_history: list,
        next_question: Optional[str] = None,
        history_summary: Optional[str] = None,
        rubric: Optional[dict] = None,
        question_metadata: Optional[dict] = None,
    ) -> dict:
        """评估候选人的回答，返回评分和反馈，带 LLM 缓存"""
        from app.services.common.redis import redis_client
        from app.services.client.evaluation_service import evaluation_service

        rubric = rubric or await evaluation_service.get_current_rubric()
        question_metadata = question_metadata or {}

        # 检查缓存
        cache_key = json.dumps(
            {
                "version": 2,
                "rubric_version": rubric.get("version"),
                "question": question,
                "question_metadata": question_metadata,
                "answer": answer,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        cached = await redis_client.get_llm_cache("evaluate", cache_key)
        if cached:
            return cached

        history_text = AIService._format_history(chat_history)
        if history_summary:
            history_text = f"[历史摘要]\n{history_summary}\n\n[近期对话]\n{history_text}"
        messages = [
            {"role": "system", "content": EVALUATE_PROMPT["system"]},
            {
                "role": "user",
                "content": EVALUATE_PROMPT["user"].format(
                    rubric_json=json.dumps(rubric, ensure_ascii=False),
                    question_metadata=json.dumps(question_metadata, ensure_ascii=False),
                    resume_context=json.dumps(resume_context, ensure_ascii=False),
                    history_text=history_text,
                    question=question,
                    answer=answer,
                ),
            },
        ]
        result = await AIService._chat(messages, temperature=0.1, provider="qwen")
        evaluation = AIService._extract_json(result)

        # 写入缓存（TTL 30 分钟）
        await redis_client.set_llm_cache("evaluate", cache_key, evaluation, ttl=1800)
        return evaluation

    @staticmethod
    def _fallback_evaluate(answer: str) -> dict:
        """
        评估降级逻辑（预判断 → 兜底），供 evaluate_node 和 evaluate_answer_with_fallback 共用。

        Returns:
            {"score": float, "feedback": str, "follow_up": False, "skip_type": str}
        """
        # Level 2: 预判断降级
        pre_result = AIService.pre_score(answer)
        if pre_result is not None:
            score, skip_type = pre_result
            logger.info(f"[Level 2] 降级到预判断评分: {skip_type}")
            feedback = {
                "honest_skip": "AI 暂时不可用，已使用基础评分。坦诚说会不会被重罚。",
                "partial_attempt": "AI 暂时不可用，已使用基础评分。",
            }.get(skip_type, "AI 暂时不可用，已使用基础评分。")
            return {
                "score": score,
                "feedback": feedback,
                "follow_up": False,
                "skip_type": skip_type,
                "fallback_level": 2,
            }

        # Level 3: 兜底
        logger.warning("[Level 3] 所有评估方案失败，使用兜底分数")
        return {
            "score": 5.0,
            "feedback": "评估服务暂时不可用，请稍后查看详细反馈。",
            "follow_up": False,
            "skip_type": None,
            "fallback_level": 3,
        }

    @staticmethod
    async def evaluate_answer_with_fallback(
        question: str,
        answer: str,
        resume_context: dict,
        chat_history: list,
        rubric: Optional[dict] = None,
        question_metadata: Optional[dict] = None,
    ) -> dict:
        """评估回答（带三级容错：正常调用 → 预判断降级 → 兜底分数）"""

        # Level 0: 尝试正常调用（带缓存）
        try:
            result = await AIService.evaluate_answer(
                question=question,
                answer=answer,
                resume_context=resume_context,
                chat_history=chat_history,
                rubric=rubric,
                question_metadata=question_metadata,
            )
            return result
        except Exception as e:
            logger.warning(f"[Level 1] AI 评估失败: {e}")

        # Level 2-3: 共享降级逻辑
        return AIService._fallback_evaluate(answer)

    @staticmethod
    async def evaluate_answer_stream(
        question: str,
        answer: str,
        resume_context: dict,
        chat_history: list,
        history_summary: Optional[str] = None,
        rubric: Optional[dict] = None,
        question_metadata: Optional[dict] = None,
    ):
        """流式版本：评估回答并逐块输出评语，最后输出 JSON 评分"""
        from app.services.client.evaluation_service import evaluation_service

        rubric = rubric or await evaluation_service.get_current_rubric()
        question_metadata = question_metadata or {}
        history_text = AIService._format_history(chat_history)
        if history_summary:
            history_text = f"[历史摘要]\n{history_summary}\n\n[近期对话]\n{history_text}"
        messages = [
            {"role": "system", "content": EVALUATE_STREAM_PROMPT["system"]},
            {
                "role": "user",
                "content": EVALUATE_STREAM_PROMPT["user"].format(
                    rubric_json=json.dumps(rubric, ensure_ascii=False),
                    question_metadata=json.dumps(question_metadata, ensure_ascii=False),
                    resume_context=json.dumps(resume_context, ensure_ascii=False),
                    history_text=history_text,
                    question=question,
                    answer=answer,
                ),
            },
        ]
        async for chunk in AIService._chat_stream(messages, temperature=0.1, provider="qwen"):
            yield chunk

    @staticmethod
    def extract_structured_evaluation(text: str) -> tuple[str, dict]:
        """提取 marker 后的结构化评估 JSON，兼容少数未输出 marker 的模型响应。"""
        marker = "__EVALUATION_JSON__"
        if marker in text:
            feedback, payload = text.split(marker, 1)
            parsed = AIService._extract_json(payload)
            if not isinstance(parsed, dict):
                raise ValueError("结构化评估结果必须是 JSON 对象")
            return feedback.strip(), parsed

        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                parsed, _ = decoder.raw_decode(text, index)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and "dimension_scores" in parsed:
                return text[:index].strip(), parsed
            if isinstance(parsed, dict) and "score" in parsed:
                return text[:index].strip(), parsed
        raise ValueError("模型响应缺少 __EVALUATION_JSON__ 或结构化评分对象")

    @staticmethod
    async def generate_report(
        parsed_resume: dict,
        target_position: str,
        questions_and_scores: list
    ) -> dict:
        """根据面试记录生成综合评估报告，带 LLM 缓存"""
        from app.services.common.redis import redis_client

        qa_text = ""
        for item in questions_and_scores:
            qa_text += (
                f"问题：{item['question']}\n"
                f"回答：{item.get('answer', '未回答')}\n"
                f"得分：{item.get('score', 'N/A')}\n\n"
            )

        cache_key = f"report:{target_position}:{qa_text}"
        cached = await redis_client.get_llm_cache("report", cache_key)
        if cached:
            return cached

        messages = [
            {"role": "system", "content": REPORT_PROMPT["system"]},
            {
                "role": "user",
                "content": REPORT_PROMPT["user"].format(
                    resume_context=json.dumps(parsed_resume, ensure_ascii=False),
                    target_position=target_position,
                    qa_text=qa_text,
                ),
            },
        ]
        result = await AIService._chat(messages, temperature=0.5, provider="qwen")
        report = AIService._extract_json(result)

        # 写入缓存（TTL 1 小时）
        await redis_client.set_llm_cache("report", cache_key, report, ttl=3600)
        return report
