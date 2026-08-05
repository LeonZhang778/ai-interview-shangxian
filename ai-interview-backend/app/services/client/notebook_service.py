import logging
from typing import Optional, Dict, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notebook import Notebook
from app.models.learning_note import LearningNote
from app.exceptions.http_exceptions import NotFoundError

logger = logging.getLogger(__name__)


class NotebookService:

    @staticmethod
    async def get_tree(db: AsyncSession, user_id: int) -> Dict:
        """获取笔记本树，返回嵌套结构 + 扁平列表"""
        query = (
            select(Notebook)
            .where(Notebook.user_id == user_id)
            .order_by(Notebook.sort_order, Notebook.id)
        )
        result = await db.execute(query)
        notebooks = result.scalars().all()

        # 构建字典
        notebook_map: Dict[int, Dict] = {}
        for n in notebooks:
            notebook_map[n.id] = {
                "id": n.id,
                "name": n.name,
                "parent_id": n.parent_id,
                "sort_order": n.sort_order,
                "icon": n.icon,
                "children": [],
                "note_count": 0,
            }

        # 统计每个笔记本的笔记数
        count_query = (
            select(
                LearningNote.notebook_id,
                func.count(LearningNote.id),
            )
            .where(
                LearningNote.user_id == user_id,
                LearningNote.notebook_id.isnot(None),
            )
            .group_by(LearningNote.notebook_id)
        )
        count_result = await db.execute(count_query)
        for nb_id, count in count_result:
            if nb_id in notebook_map:
                notebook_map[nb_id]["note_count"] = count

        # 组装树
        tree = []
        for n_id, item in notebook_map.items():
            parent_id = item["parent_id"]
            if parent_id and parent_id in notebook_map:
                notebook_map[parent_id]["children"].append(item)
            else:
                tree.append(item)

        return {"tree": tree, "flat": list(notebook_map.values())}

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: int,
        name: str,
        parent_id: Optional[int] = None,
        icon: Optional[str] = None,
    ) -> Dict:
        """创建笔记本"""
        if parent_id is not None:
            parent = await db.get(Notebook, parent_id)
            if not parent or parent.user_id != user_id:
                raise NotFoundError(message="父级笔记本不存在")

        notebook = Notebook(
            user_id=user_id,
            name=name.strip(),
            parent_id=parent_id,
            icon=icon,
        )
        db.add(notebook)
        await db.commit()
        await db.refresh(notebook)
        return {"id": notebook.id, "name": notebook.name}

    @staticmethod
    async def update(
        db: AsyncSession,
        user_id: int,
        notebook_id: int,
        **kwargs,
    ) -> Dict:
        """更新笔记本名称/图标/排序"""
        notebook = await db.get(Notebook, notebook_id)
        if not notebook or notebook.user_id != user_id:
            raise NotFoundError(message="笔记本不存在")
        for key, value in kwargs.items():
            if value is not None and hasattr(notebook, key):
                setattr(notebook, key, value)
        await db.commit()
        return {"id": notebook.id, "message": "更新成功"}

    @staticmethod
    async def delete(db: AsyncSession, user_id: int, notebook_id: int) -> Dict:
        """删除笔记本，子笔记本和笔记迁移到父级"""
        notebook = await db.get(Notebook, notebook_id)
        if not notebook or notebook.user_id != user_id:
            raise NotFoundError(message="笔记本不存在")

        target_parent_id = notebook.parent_id

        # 子笔记本移到父级
        sub_query = select(Notebook).where(
            Notebook.user_id == user_id,
            Notebook.parent_id == notebook_id,
        )
        sub_result = await db.execute(sub_query)
        for sub in sub_result.scalars():
            sub.parent_id = target_parent_id

        # 笔记移到父级
        note_query = select(LearningNote).where(
            LearningNote.user_id == user_id,
            LearningNote.notebook_id == notebook_id
        )
        note_result = await db.execute(note_query)
        for note in note_result.scalars():
            note.notebook_id = target_parent_id

        await db.delete(notebook)
        await db.commit()
        return {"message": "笔记本已删除"}


notebook_service = NotebookService()
