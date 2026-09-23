from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from pkdb_server.db.models.base import Base


class WorkLease(Base):
    __tablename__ = "work_leases"
    request_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    bucket: Mapped[str] = mapped_column(String(100), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
