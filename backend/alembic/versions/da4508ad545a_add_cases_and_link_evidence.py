"""add cases and link evidence

Revision ID: da4508ad545a
Revises: 9518428d1b72
Create Date: 2026-08-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "da4508ad545a"
down_revision: Union[str, Sequence[str], None] = "9518428d1b72"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # 1. Create PostgreSQL enum type
    # ---------------------------------------------------------

    case_status = postgresql.ENUM(
        "OPEN",
        "CLOSED",
        name="casestatus",
    )

    case_status.create(
        op.get_bind(),
        checkfirst=True,
    )

    # ---------------------------------------------------------
    # 2. Create cases table
    # ---------------------------------------------------------

    case_status_column = postgresql.ENUM(
        "OPEN",
        "CLOSED",
        name="casestatus",
        create_type=False,
    )

    op.create_table(
        "cases",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "status",
            case_status_column,
            nullable=False,
            server_default="OPEN",
        ),
        sa.Column(
            "created_by",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ---------------------------------------------------------
    # 3. Add case_id to existing evidence table
    # ---------------------------------------------------------

    op.add_column(
        "evidence",
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # ---------------------------------------------------------
    # 4. Create index
    # ---------------------------------------------------------

    op.create_index(
        "ix_evidence_case_id",
        "evidence",
        ["case_id"],
    )

    # ---------------------------------------------------------
    # 5. Create foreign key
    # ---------------------------------------------------------

    op.create_foreign_key(
        "fk_evidence_case_id_cases",
        "evidence",
        "cases",
        ["case_id"],
        ["id"],
    )


def downgrade() -> None:
    # ---------------------------------------------------------
    # 1. Remove foreign key
    # ---------------------------------------------------------

    op.drop_constraint(
        "fk_evidence_case_id_cases",
        "evidence",
        type_="foreignkey",
    )

    # ---------------------------------------------------------
    # 2. Remove index
    # ---------------------------------------------------------

    op.drop_index(
        "ix_evidence_case_id",
        table_name="evidence",
    )

    # ---------------------------------------------------------
    # 3. Remove case_id
    # ---------------------------------------------------------

    op.drop_column(
        "evidence",
        "case_id",
    )

    # ---------------------------------------------------------
    # 4. Remove cases table
    # ---------------------------------------------------------

    op.drop_table("cases")

    # ---------------------------------------------------------
    # 5. Remove enum type
    # ---------------------------------------------------------

    case_status = postgresql.ENUM(
        "OPEN",
        "CLOSED",
        name="casestatus",
    )

    case_status.drop(
        op.get_bind(),
        checkfirst=True,
    )
