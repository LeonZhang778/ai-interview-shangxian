from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.utils import utils
from app.db.session import get_db
from app.api.backoffice.deps import get_current_admin
from app.models.admin import Admin
from app.exceptions.http_exceptions import APIException
from app.schemas.response import ApiResponse

router = APIRouter()


@router.get("/temporary-credentials")
async def get_temporary_credentials(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取S3临时访问凭证"""
    try:
        temporary_credentials = utils.get_temporary_credentials()
        return ApiResponse.success(data=temporary_credentials)
    except Exception as e:
        raise APIException(status_code=500, message=str(e))

