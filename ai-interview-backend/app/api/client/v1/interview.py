import io
from urllib.parse import quote

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.client.deps import get_current_user
from app.api.rate_limit import check_ai_rate_limit
from app.schemas.client.interview import InterviewStart, AnswerSubmit
from app.models.interview import Interview
from app.services.client.document_export_service import DOCX_MEDIA_TYPE, document_export_service
from app.services.client.interview_service import interview_service
from app.schemas.response import ApiResponse
from app.models.user import User
from app.utils.utils import safe_parse_json

router = APIRouter()


def _safe_filename(value: str, fallback: str) -> str:
    cleaned = "".join(
        char for char in (value or "")
        if char not in '\\/:*?"<>|' and ord(char) >= 32 and ord(char) != 127
    ).strip()
    return cleaned or fallback


def _content_disposition(filename: str) -> str:
    ascii_name = "".join(char if ord(char) < 128 else "_" for char in filename)
    ascii_name = ascii_name.replace('"', "'") or "download"
    return f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(filename)}'


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
    await check_ai_rate_limit(current_user)
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
    await check_ai_rate_limit(current_user)
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
    await check_ai_rate_limit(current_user)
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


@router.post("/{interview_id}/report/regenerate")
async def regenerate_report(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """重新生成面试报告（报告页在生成失败/长时间未就绪时的兜底入口）。"""
    await check_ai_rate_limit(current_user)
    result = await interview_service.regenerate_report(
        db=db,
        user_id=current_user.id,
        interview_id=interview_id
    )
    return ApiResponse.success(data=result)


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


@router.get("/{interview_id}/report/export-docx")
async def export_report_docx(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """导出面试评估报告为 DOCX 文件。"""
    query = select(Interview).where(
        Interview.id == interview_id,
        Interview.user_id == current_user.id,
    )
    result = await db.execute(query)
    interview = result.scalar_one_or_none()
    if not interview:
        return ApiResponse.failed(message="面试记录不存在", body_code=404, http_code=status.HTTP_404_NOT_FOUND)
    if interview.status != "completed":
        return ApiResponse.failed(message="面试尚未完成，无法导出报告", body_code=400, http_code=status.HTTP_400_BAD_REQUEST)
    # 报告由后台生成：status=completed 不再等于报告可读，未就绪时导出会得到空文档
    if (interview.report_status or "ready") != "ready":
        return ApiResponse.failed(message="报告仍在生成中，请稍后再试", body_code=400, http_code=status.HTTP_400_BAD_REQUEST)

    report = safe_parse_json(interview.report, {})
    content = document_export_service.build_interview_report_docx(interview, report)
    report_name = interview.target_position or "AI面试"
    filename = f"{_safe_filename(f'{report_name} 面试报告', f'interview_{interview_id}_report')}.docx"
    return StreamingResponse(
        io.BytesIO(content),
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": _content_disposition(filename)},
    )


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
    """面试历史对比分析 - 增强版"""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
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
            "weakest_dimension_details": [],
            "improvement_rate": 0,
            "recent_scores": [],
            "company_stats": [],
            "position_stats": [],
            "score_distribution": {"low": 0, "mid": 0, "high": 0},
            "time_distribution": {"weekday": 0, "weekend": 0},
            "recent_activity": []
        })

    # ========== 分数趋势 ==========
    score_trend = []
    for i in interviews:
        if i.overall_score:
            score_trend.append({
                "date": i.created_at.strftime("%Y-%m-%d"),
                "score": float(i.overall_score),
                "position": i.target_position or "未知"
            })

    # ========== 维度分析（从报告中提取真实维度） ==========
    dimension_scores = {}
    for i in interviews:
        report = safe_parse_json(i.report, {})
        if report:
            # 尝试从 dimension_scores 获取
            dims = report.get("dimension_scores", {})
            if dims:
                for dim_name, dim_score in dims.items():
                    dimension_scores.setdefault(dim_name, []).append(float(dim_score))
            else:
                # 回退到 question_scores 按类别聚合
                question_scores = report.get("question_scores", [])
                for qs in question_scores:
                    category = qs.get("category") or qs.get("question", "")[:20]
                    score = qs.get("score", 0)
                    if category:
                        dimension_scores.setdefault(category, []).append(float(score))

    # 计算维度平均分
    dimension_avg = {}
    for dim, scores in dimension_scores.items():
        dimension_avg[dim] = round(sum(scores) / len(scores), 1) if scores else 0

    # 最弱维度
    weakest = min(dimension_avg, key=dimension_avg.get) if dimension_avg else None

    # ========== 按难度统计 ==========
    difficulty_map = {}
    for i in interviews:
        difficulty = i.difficulty or "未知"
        if difficulty not in difficulty_map:
            difficulty_map[difficulty] = {"count": 0, "scores": []}
        difficulty_map[difficulty]["count"] += 1
        if i.overall_score:
            difficulty_map[difficulty]["scores"].append(float(i.overall_score))

    difficulty_labels = {"easy": "简单", "medium": "中等", "hard": "困难"}
    company_stats = [
        {
            "company": difficulty_labels.get(name, name),
            "count": info["count"],
            "avg_score": round(sum(info["scores"]) / len(info["scores"]), 1) if info["scores"] else 0
        }
        for name, info in sorted(difficulty_map.items(), key=lambda x: x[1]["count"], reverse=True)
    ]

    # ========== 按岗位统计 ==========
    position_map = {}
    for i in interviews:
        position = i.target_position or "未知"
        if position not in position_map:
            position_map[position] = {"count": 0, "scores": []}
        position_map[position]["count"] += 1
        if i.overall_score:
            position_map[position]["scores"].append(float(i.overall_score))

    position_stats = [
        {
            "position": name,
            "count": info["count"],
            "avg_score": round(sum(info["scores"]) / len(info["scores"]), 1) if info["scores"] else 0
        }
        for name, info in sorted(position_map.items(), key=lambda x: x[1]["count"], reverse=True)
    ]

    # ========== 分数段分布（10 分制） ==========
    score_distribution = {"low": 0, "mid": 0, "high": 0}
    for i in interviews:
        if i.overall_score:
            s = float(i.overall_score)
            if s >= 8:
                score_distribution["high"] += 1
            elif s >= 6:
                score_distribution["mid"] += 1
            else:
                score_distribution["low"] += 1

    # ========== 时间分布（工作日 vs 周末） ==========
    weekday_count = 0
    weekend_count = 0
    for i in interviews:
        if i.created_at.weekday() < 5:
            weekday_count += 1
        else:
            weekend_count += 1

    # ========== 最近活跃度（最近 7 天每天的面试次数） ==========
    now = datetime.now(timezone.utc)
    recent_activity = []
    for days_ago in range(6, -1, -1):
        day = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        count = sum(1 for i in interviews if i.created_at.strftime("%Y-%m-%d") == day)
        recent_activity.append({"date": day, "count": count})

    # ========== 进步率（10 分制，首末对比，限幅 -100% ~ +200%） ==========
    # 改进：用最早与最近面试对比，避免对半切分导致的小样本放大；
    # 仅当面试数 >= 2 时计算，并限制在合理区间，杜绝 +276% 这类失真值。
    improvement_rate = 0
    if len(score_trend) >= 2:
        first = score_trend[0]["score"]
        last = score_trend[-1]["score"]
        if first > 0:
            raw_rate = (last - first) / first
            improvement_rate = round(max(-1.0, min(2.0, raw_rate)), 2)

    # ========== 薄弱维度详情（供详情页展示具体表现） ==========
    weakest_dimension_details = []
    if weakest and weakest in dimension_scores:
        details = []
        for idx, sc in enumerate(dimension_scores[weakest]):
            # 关联回对应面试，便于在详情页跳转
            interview_ref = interviews[idx] if idx < len(interviews) else None
            details.append({
                "score": round(sc, 1),
                "date": interview_ref.created_at.strftime("%Y-%m-%d") if interview_ref else None,
                "interview_id": interview_ref.id if interview_ref else None,
                "position": interview_ref.target_position if interview_ref else None,
            })
        weakest_dimension_details = details

    # ========== 最近得分历史（点击"最近得分"查看最近 N 次得分） ==========
    recent_scores = [
        {
            "date": s["date"],
            "score": s["score"],
            "position": s["position"],
        }
        for s in reversed(score_trend[-10:])
    ]

    return ApiResponse.success(data={
        "total_interviews": len(interviews),
        "completed_interviews": len(interviews),
        "score_trend": score_trend,
        "dimension_avg": dimension_avg,
        "weakest_dimension": weakest,
        "weakest_dimension_details": weakest_dimension_details,
        "improvement_rate": improvement_rate,
        "recent_scores": recent_scores,
        "company_stats": company_stats,
        "position_stats": position_stats,
        "score_distribution": score_distribution,
        "time_distribution": {"weekday": weekday_count, "weekend": weekend_count},
        "recent_activity": recent_activity
    })

