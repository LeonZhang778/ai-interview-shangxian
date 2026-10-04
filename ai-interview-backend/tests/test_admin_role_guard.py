"""管理员角色入参化 + 「最后一个超管」保护的行为锁定。

背景（两个互相掩盖的真实缺陷）：
1. AdminService.create_admin 把 role 硬编码成 "superadmin" —— 永远创建不出低权限账号。
2. 路由 admin.py:111 读取 admin_data.role，但 AdminUpdate 里没有该字段 —— 只要当前
   登录者不是超管（也就是真的存在低权限账号时），这一行必然 AttributeError → 500。
   缺陷 1 让系统里只有超管，于是缺陷 2 从未被触发过。

另外补上「最后一个超管」保护：把最后一个超管降级或删除，后台将无人能再管理
管理员，只能直连数据库才能恢复 —— 必须拦住。
"""

import asyncio

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy.sql.elements import BindParameter

from app.exceptions.http_exceptions import APIException
from app.models.admin import Admin, UserRole
from app.schemas.backoffice.admin import AdminCreate, AdminUpdate
from app.services.backoffice.admin import admin_service


def _iter_leaf_criteria(clause):
    """把 WHERE 子句拍平成叶子条件（兼容 and_ 组合与单个条件）。"""
    if clause is None:
        return []
    children = getattr(clause, "clauses", None)
    if children is None:
        return [clause]
    leaves = []
    for child in children:
        leaves.extend(_iter_leaf_criteria(child))
    return leaves


def _eq_filters(query):
    """提取 WHERE 中的等值条件，让假库像真库一样按条件过滤。"""
    filters = {}
    for leaf in _iter_leaf_criteria(getattr(query, "whereclause", None)):
        column = getattr(getattr(leaf, "left", None), "key", None)
        right = getattr(leaf, "right", None)
        if column and isinstance(right, BindParameter):
            filters[column] = right.value
    return filters


def _matches(admin, filters):
    return all(getattr(admin, key, None) == value for key, value in filters.items())


class _CountResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _RowResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class _AdminDb:
    """最小假库：只实现 admin service 用到的 count 与等值行查询。"""

    def __init__(self, admins):
        self.admins = list(admins)

    async def execute(self, query):
        filters = _eq_filters(query)
        if "count(" in str(query).lower():
            return _CountResult(len([a for a in self.admins if _matches(a, filters)]))
        return _RowResult([a for a in self.admins if _matches(a, filters)])


def _mk_admin(admin_id=1, role="superadmin", email="a@example.com"):
    now = datetime.now(timezone.utc)
    return Admin(
        id=admin_id,
        role=role,
        email=email,
        password="hashed",
        is_active=True,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# schema 契约
# ---------------------------------------------------------------------------

def test_admin_create_defaults_to_superadmin():
    """默认仍为超管：管理端暂无角色选择 UI，改默认会造成无提示的行为变更。"""
    assert AdminCreate(email="a@example.com", password="p" * 8).role == UserRole.SUPERADMIN


def test_admin_create_accepts_explicit_admin_role():
    data = AdminCreate(email="a@example.com", password="p" * 8, role="admin")
    assert data.role == UserRole.ADMIN


def test_admin_create_rejects_unknown_role():
    with pytest.raises(ValidationError):
        AdminCreate(email="a@example.com", password="p" * 8, role="root")


def test_admin_update_accepts_role_field():
    """回归：AdminUpdate 此前缺 role 字段，而路由会读取它并直接 AttributeError。"""
    assert AdminUpdate(role="admin").role == "admin"
    assert AdminUpdate().role is None


def test_admin_update_omits_role_when_not_provided():
    """未显式传 role 时不得进入更新字段，否则会把角色悄悄改掉。"""
    dumped = AdminUpdate(email="a@example.com").model_dump(exclude_unset=True)
    assert "role" not in dumped


# ---------------------------------------------------------------------------
# 「最后一个超管」保护
# ---------------------------------------------------------------------------

def test_guard_blocks_when_only_one_superadmin():
    db = _AdminDb([_mk_admin(1, "superadmin")])
    with pytest.raises(APIException):
        asyncio.run(admin_service._assert_not_last_superadmin(db, action="降级"))


def test_guard_allows_when_multiple_superadmins():
    db = _AdminDb([
        _mk_admin(1, "superadmin"),
        _mk_admin(2, "superadmin", "b@example.com"),
    ])
    # 不抛异常即为通过
    asyncio.run(admin_service._assert_not_last_superadmin(db, action="降级"))


def test_update_admin_blocks_demoting_last_superadmin():
    db = _AdminDb([_mk_admin(1, "superadmin")])
    with pytest.raises(APIException):
        asyncio.run(admin_service.update_admin(db, 1, {"role": "admin"}))


def test_delete_admin_blocks_removing_last_superadmin():
    db = _AdminDb([_mk_admin(1, "superadmin")])
    with pytest.raises(APIException):
        asyncio.run(admin_service.delete_admin(db, 1))


def test_update_admin_allows_demoting_when_another_superadmin_exists():
    """还有别的超管时，降级应当放行 —— 保护只针对「最后一个」。"""
    db = _AdminDb([
        _mk_admin(1, "superadmin"),
        _mk_admin(2, "superadmin", "b@example.com"),
    ])
    result = asyncio.run(admin_service.update_admin(db, 1, {"role": "admin"}))
    assert result is not None
