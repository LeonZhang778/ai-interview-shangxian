from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel


class Notebook(BaseModel):
    __tablename__ = "notebooks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=True, index=True)
    sort_order = Column(Integer, default=0)
    icon = Column(String(20), nullable=True)

    # 自引用关系
    children = relationship(
        "Notebook", backref="parent", remote_side=[id],
        order_by="Notebook.sort_order", lazy="selectin",
    )
    user = relationship("User", backref="notebooks")