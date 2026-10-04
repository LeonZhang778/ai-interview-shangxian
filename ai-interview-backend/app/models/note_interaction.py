from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import BaseModel


class PublicNoteLike(BaseModel):
    __tablename__ = "public_note_likes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    note_id = Column(Integer, ForeignKey("learning_notes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("note_id", "user_id", name="uq_public_note_like_user"),
    )


class PublicNoteCollection(BaseModel):
    __tablename__ = "public_note_collections"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    note_id = Column(Integer, ForeignKey("learning_notes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("note_id", "user_id", name="uq_public_note_collection_user"),
    )


class PublicNoteComment(BaseModel):
    __tablename__ = "public_note_comments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    note_id = Column(Integer, ForeignKey("learning_notes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("public_note_comments.id", ondelete="CASCADE"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    like_count = Column(Integer, nullable=False, default=0, server_default="0")

    author = relationship("User", lazy="joined")
    replies = relationship(
        "PublicNoteComment",
        backref="parent",
        remote_side="PublicNoteComment.id",
        lazy="selectin",
    )
