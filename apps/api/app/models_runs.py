"""ORM-model for workerens kørselslog."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class WorkerRun(Base):
    __tablename__ = "worker_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # RunTrigger: schedule | manual | cli
    trigger: Mapped[str] = mapped_column(Text, nullable=False)
    # True: alle aktive kilder hentes nu, uanset frekvens og næste kontrol.
    force_all: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # RunStatus: running | succeeded | failed
    status: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Null ved planlagte og CLI-kørsler.
    started_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    sources_checked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    documents_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    documents_unchanged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fetch_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    documents_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processing_skipped_no_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message_safe: Mapped[str | None] = mapped_column(Text)
