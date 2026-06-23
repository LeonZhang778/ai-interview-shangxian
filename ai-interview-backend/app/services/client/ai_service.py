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
    before_sleep_log,
)
from app.prompts.interview import (
    RESUME_PARSE_PROMPT,
    RESUME_ANALYZE_PROMPT,
    INTERN_LEVEL_HINT,
    NORMAL_LEVEL_HINT,
    GENERATE_QUESTIONS_PROMPT,
    INTERN_POSITION_HINT,
    NORMAL_POSITION_HINT,
    GENERATE_QUESTIONS_FROM_EXPERIENCE_PROMPT,
    EVALUATE_PROMPT,
    EVALUATE_STREAM_PROMPT,
    REPORT_PROMPT,
)

logger = logging.getLogger(__name__)

# 智谱 GLM 使用 OpenAI 兼容 API
client = AsyncOpenAI(
    api_key=settings.AI_API_KEY,
    base_url=settings.AI_BASE_URL
)


class AIService:
    """智谱 GLM AI 服务 - 面试模拟核心"""

    # 诚实跳过的关键词（坦诚说不会，应该给机会）
    HONEST_SKIP_KEYWORDS = ["不知道", "不会", "不清楚", "不太了解", "不太清楚", "没学过", "没接触过", "不记得", "跳过"]
    # 胡说八道的关键词（空洞回答）
    EMPTY_TALK_KEYWORDS = ["嗯", "对", "是的", "好的", "知道了"]

    @staticmethod
    def pre_score(answer: str) -> Optional[tuple]:
        """
        预判断：分级评分，区分诚实跳过和胡说八道

        Returns:
            None: 继续 AI 评估
            (score, skip_type): 直接返回分数和类型
        """
        text = answer.strip()

        # 空回答 → 1 分
        if not text:
            return (1.0, "empty")

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
        retry=retry_if_exception_type((ConnectionError, TimeoutError, Exception)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _chat(messages: list, temperature: float = 0.7) -> str:
        """基础对话补全调用，带 tenacity 重试 + 超时保护"""
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=settings.AI_MODEL,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=4096
                ),
                timeout=30.0,
            )
            msg = response.choices[0].message
            content = msg.content
            # GLM 推理模型可能把内容放在 reasoning_content 里
            if not content or not content.strip():
                reasoning = getattr(msg, 'reasoning_content', None)
                if reasoning and reasoning.strip():
                    logger.warning("content 为空，使用 reasoning_content")
                    return reasoning.strip()
                logger.error(f"AI API 返回空响应: {response}")
                raise ValueError("AI API 返回了空响应，请稍后重试")
            result = content.strip()
            logger.info(f"AI 响应前 200 字: {result[:200]}")
            return result
        except asyncio.TimeoutError:
            logger.error("AI API 调用超时 (30s)")
            raise TimeoutError("AI API 调用超时")
        except Exception as e:
            logger.error(f"AI API 调用失败: {e}")
            raise

    @staticmethod
    async def _chat_stream(messages: list, temperature: float = 0.7):
        """流式对话补全调用，逐块返回文本，带超时保护"""
        try:
            stream = await asyncio.wait_for(
                client.chat.completions.create(
                    model=settings.AI_MODEL,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=4096,
                    stream=True
                ),
                timeout=30.0,
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except asyncio.TimeoutError:
            logger.error("AI 流式 API 调用超时 (30s)")
            raise TimeoutError("AI 流式 API 调用超时")
        except Exception as e:
            logger.error(f"AI 流式 API 调用失败: {e}")
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
        result = await AIService._chat(messages, temperature=0.3)
        parsed = AIService._extract_json(result)

        # 写入缓存（TTL 1 小时）
        await redis_client.set_llm_cache("parse", cache_key, parsed, ttl=3600)
        return parsed

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
        result = await AIService._chat(messages, temperature=0.4)
        return AIService._extract_json(result)

    @staticmethod
    async def generate_questions(
        parsed_resume: dict,
        target_position: str,
        difficulty: str,
        count: int
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
        cache_key = f"questions:{target_position}:{difficulty}:{count}:{json.dumps(parsed_resume, ensure_ascii=False)[:200]}"
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
                ),
            },
            {
                "role": "user",
                "content": GENERATE_QUESTIONS_PROMPT["user"].format(
                    resume_json=json.dumps(parsed_resume, ensure_ascii=False),
                    target_position=target_position,
                    count=count,
                ),
            },
        ]
        result = await AIService._chat(messages, temperature=0.7)
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
        result = await AIService._chat(messages, temperature=0.7)
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
        next_question: Optional[str] = None
    ) -> dict:
        """评估候选人的回答，返回评分和反馈，带 LLM 缓存"""
        from app.services.common.redis import redis_client

        # 检查缓存
        cache_key = f"evaluate:{question}:{answer}"
        cached = await redis_client.get_llm_cache("evaluate", cache_key)
        if cached:
            return cached

        history_text = AIService._format_history(chat_history)
        messages = [
            {"role": "system", "content": EVALUATE_PROMPT["system"]},
            {
                "role": "user",
                "content": EVALUATE_PROMPT["user"].format(
                    resume_context=json.dumps(resume_context, ensure_ascii=False),
                    history_text=history_text,
                    question=question,
                    answer=answer,
                ),
            },
        ]
        result = await AIService._chat(messages, temperature=0.1)
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
            return {"score": score, "feedback": feedback, "follow_up": False, "skip_type": skip_type}

        # Level 3: 兜底
        logger.warning("[Level 3] 所有评估方案失败，使用兜底分数")
        return {"score": 5.0, "feedback": "评估服务暂时不可用，请稍后查看详细反馈。", "follow_up": False, "skip_type": None}

    @staticmethod
    async def evaluate_answer_with_fallback(
        question: str,
        answer: str,
        resume_context: dict,
        chat_history: list
    ) -> dict:
        """评估回答（带三级容错：正常调用 → 预判断降级 → 兜底分数）"""

        # Level 0: 尝试正常调用（带缓存）
        try:
            result = await AIService.evaluate_answer(
                question=question,
                answer=answer,
                resume_context=resume_context,
                chat_history=chat_history,
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
        chat_history: list
    ):
        """流式版本：评估回答并逐块输出评语，最后输出 JSON 评分"""
        history_text = AIService._format_history(chat_history)
        messages = [
            {"role": "system", "content": EVALUATE_STREAM_PROMPT["system"]},
            {
                "role": "user",
                "content": EVALUATE_STREAM_PROMPT["user"].format(
                    resume_context=json.dumps(resume_context, ensure_ascii=False),
                    history_text=history_text,
                    question=question,
                    answer=answer,
                ),
            },
        ]
        async for chunk in AIService._chat_stream(messages, temperature=0.1):
            yield chunk

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
        result = await AIService._chat(messages, temperature=0.5)
        report = AIService._extract_json(result)

        # 写入缓存（TTL 1 小时）
        await redis_client.set_llm_cache("report", cache_key, report, ttl=3600)
        return report
