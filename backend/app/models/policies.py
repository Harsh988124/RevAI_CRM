
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


VALID_STAGES = (
    "'qualification', 'discovery', 'proposal', "
    "'negotiation', 'closed_won', 'closed_lost'"
)


class SalesPolicyVersion(Base):
    __tablename__ = "sales_policy_versions"

    __table_args__ = (
        UniqueConstraint(
            "policy_key",
            "version",
            name="uq_sales_policy_key_version",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_sales_policy_version_positive",
        ),
        CheckConstraint(
            f"to_stage IN ({VALID_STAGES})",
            name="ck_sales_policy_to_stage",
        ),
        CheckConstraint(
            f"from_stage IS NULL OR from_stage IN ({VALID_STAGES})",
            name="ck_sales_policy_from_stage",
        ),
        CheckConstraint(
            "min_amount IS NULL OR min_amount >= 0",
            name="ck_sales_policy_min_amount",
        ),
        CheckConstraint(
            "min_probability IS NULL OR "
            "(min_probability >= 0 AND min_probability <= 100)",
            name="ck_sales_policy_min_probability",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # All versions of the same logical policy share the same key.
    policy_key: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    from_stage: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    to_stage: Mapped[str] = mapped_column(String(50), nullable=False)

    required_fields: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )

    min_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    min_probability: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    require_open_task: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # New versions are drafts until explicitly activated.
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    created_by: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class PolicyEvaluation(Base):
    __tablename__ = "policy_evaluations"

    __table_args__ = (
        CheckConstraint(
            "status IN ('allowed', 'blocked', 'overridden')",
            name="ck_policy_evaluation_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    deal_id: Mapped[int] = mapped_column(
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    from_stage: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    to_stage: Mapped[str] = mapped_column(
        String(50), nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )

    # Snapshot the policy versions used at evaluation time.
    policy_versions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    violations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )

    override_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    evaluated_by: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
    )
