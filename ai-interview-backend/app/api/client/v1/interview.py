from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.client.deps import get_current_user
from app.schemas.client.interview import InterviewStart, AnswerSubmit
from app.services.client.interview_service import interview_service
from app.schemas.response import ApiResponse
from app.models.user import User

router = APIRouter()


@router.post("/{interview_id}/share")
async def share_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """生成面试分享链接"""
    result = await interview_service.share_interview(
        db=db,
        user_id=current_user.id,
        interview_id=interview_id
    )
    return ApiResponse.success(data=result)


@router.delete("/{interview_id}/share")
async def unshare_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取消面试分享"""
    result = await interview_service.unshare_interview(
        db=db,
        user_id=current_user.id,
        interview_id=interview_id
    )
    return ApiResponse.success(data=result)


@router.post("/start")
async def start_interview(
    data: InterviewStart,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """开始新的 AI 面试会话"""
    result = await interview_service.start_interview(
        db=db,
        user_id=current_user.id,
        resume_id=data.resume_id,
        target_position=data.target_position,
        difficulty=data.difficulty,
        total_questions=data.total_questions
    )
    return ApiResponse.success(data=result)


@router.post("/{interview_id}/answer")
async def submit_answer(
    interview_id: int,
    data: AnswerSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """提交当前题目的回答"""
    result = await interview_service.submit_answer(
        db=db,
        user_id=current_user.id,
        interview_id=interview_id,
        answer=data.answer
    )
    return ApiResponse.success(data=result)


@router.post("/{interview_id}/answer/stream")
async def submit_answer_stream(
    interview_id: int,
    data: AnswerSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """提交回答并通过 SSE 流式返回 AI 评估"""
    generator = interview_service.submit_answer_stream(
        db=db,
        user_id=current_user.id,
        interview_id=interview_id,
        answer=data.answer
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/{interview_id}/report")
async def get_report(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取面试评估报告"""
    result = await interview_service.get_report(
        db=db,
        user_id=current_user.id,
        interview_id=interview_id
    )
    return ApiResponse.success(data=result)


@router.get("/{interview_id}/messages")
async def get_messages(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取面试的所有对话消息"""
    result = await interview_service.get_interview_messages(
        db=db,
        user_id=current_user.id,
        interview_id=interview_id
    )
    return ApiResponse.success(data=result)


@router.get("")
async def get_interviews(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户的所有面试记录"""
    result = await interview_service.get_interviews(
        db=db,
        user_id=current_user.id
    )
    return ApiResponse.success(data=result)


@router.delete("/{interview_id}")
async def delete_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除面试记录"""
    result = await interview_service.delete_interview(
        db=db,
        user_id=current_user.id,
        interview_id=interview_id
    )
    return ApiResponse.success(data=result)


@router.get("/analysis")
async def get_analysis(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """面试历史对比分析"""
    import json
    from sqlalchemy import select, func
    from app.models.interview import Interview

    # 查询已完成的面试
    query = (
        select(Interview)
        .where(Interview.user_id == current_user.id, Interview.status == "completed")
        .order_by(Interview.created_at.asc())
    )
    result = await db.execute(query)
    interviews = result.scalars().all()

    if not interviews:
        return ApiResponse.success(data={
            "total_interviews": 0,
            "completed_interviews": 0,
            "score_trend": [],
            "dimension_avg": {},
            "weakest_dimension": None,
            "improvement_rate": 0
        })

    # 分数趋势
    score_trend = []
    for i in interviews:
        if i.overall_score:
            score_trend.append({
                "date": i.created_at.strftime("%Y-%m-%d"),
                "score": float(i.overall_score),
                "position": i.target_position or "未知"
            })

    # 维度分析（从报告中提取）
    dimension_scores = {}
    for i in interviews:
        if i.report:
            try:
                report = json.loads(i.report)
                question_scores = report.get("question_scores", [])
                for qs in question_scores:
                    category = qs.get("question", "")[:20]
                    score = qs.get("score", 0)
                    if category:
                        dimension_scores.setdefault(category, []).append(float(score))
            except (json.JSONDecodeError, TypeError):
                pass

    # 计算维度平均分
    dimension_avg = {}
    for dim, scores in dimension_scores.items():
        dimension_avg[dim] = round(sum(scores) / len(scores), 1) if scores else 0

    # 最弱维度
    weakest = min(dimension_avg, key=dimension_avg.get) if dimension_avg else None

    # 进步率（最后3次 vs 前3次）
    improvement_rate = 0
    if len(score_trend) >= 4:
        first_half = [s["score"] for s in score_trend[:len(score_trend)//2]]
        second_half = [s["score"] for s in score_trend[len(score_trend)//2:]]
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        if avg_first > 0:
            improvement_rate = round((avg_second - avg_first) / avg_first, 2)

    return ApiResponse.success(data={
        "total_interviews": len(interviews),
        "completed_interviews": len(interviews),
        "score_trend": score_trend,
        "dimension_avg": dimension_avg,
        "weakest_dimension": weakest,
        "improvement_rate": improvement_rate
    })

