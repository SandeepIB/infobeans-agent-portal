from __future__ import annotations
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserAppPermission(Base):
    __tablename__ = "user_app_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "app_id", name="uq_user_app"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    app_id: Mapped[int] = mapped_column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    granted_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="permissions", foreign_keys=[user_id])  # noqa: F821
    application: Mapped["Application"] = relationship("Application", back_populates="permissions")  # noqa: F821
    granted_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[granted_by])  # noqa: F821
