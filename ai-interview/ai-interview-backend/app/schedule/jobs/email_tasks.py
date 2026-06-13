"""
邮件发送异步任务
"""
from app.core.celery_app import celery_app
from app.services.client.email_templates import client_email_service


def dispatch_email_task(task_func, *args, **kwargs):
    """通过 Celery 派发邮件任务"""
    task_func.delay(*args, **kwargs)


@celery_app.task(bind=True, max_retries=3)
def send_verification_email_task(self, email: str, verification_code: str, code_type: str, user_name: str = None):
    """异步发送验证码邮件"""
    try:
        import asyncio
        if code_type == "registration":
            asyncio.run(client_email_service.send_registration_verification(email, verification_code, user_name))
        elif code_type == "password-reset":
            asyncio.run(client_email_service.send_password_reset_code(email, verification_code, user_name))
        else:
            raise ValueError(f"不支持的 code_type: {code_type}")
        return {"status": "success", "email": email, "code_type": code_type}
    except Exception as exc:
        print(f"邮件发送失败: {str(exc)}")
        if self.request.retries < self.max_retries:
            countdown = 60 * (self.request.retries + 1)
            self.retry(countdown=countdown, exc=exc)
        raise exc


@celery_app.task
def send_welcome_email_task(email: str, user_name: str):
    """发送欢迎邮件任务（可选，未来扩展）"""
    print(f"欢迎邮件任务 {email} ({user_name}) - 尚未实现")
    return {"status": "not_implemented", "email": email, "user_name": user_name}


@celery_app.task(bind=True, max_retries=3)
def send_waiting_list_verification_task(self, email: str, verification_token: str, first_name: str = None):
    """异步发送等待列表验证邮件"""
    try:
        import asyncio
        asyncio.run(client_email_service.send_waiting_list_verification(email, verification_token, first_name))
        return {"status": "success", "email": email, "type": "waiting_list_verification"}
    except Exception as exc:
        print(f"等待列表验证邮件发送失败: {str(exc)}")
        if self.request.retries < self.max_retries:
            countdown = 60 * (self.request.retries + 1)
            self.retry(countdown=countdown, exc=exc)
        raise exc


@celery_app.task(bind=True, max_retries=3)
def send_waiting_list_admin_notification_task(self, submission_data: dict):
    """异步发送等待列表管理员通知邮件"""
    try:
        import asyncio
        asyncio.run(client_email_service.send_waiting_list_admin_notification(submission_data))
        return {"status": "success", "email": submission_data.get("email"), "type": "admin_notification"}
    except Exception as exc:
        print(f"管理员通知邮件发送失败: {str(exc)}")
        if self.request.retries < self.max_retries:
            countdown = 60 * (self.request.retries + 1)
            self.retry(countdown=countdown, exc=exc)
        raise exc
