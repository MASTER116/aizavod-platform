"""Add work_plans table for workload planning.

Revision ID: 002
Revises: 001
Create Date: 2026-03-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enums
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE workplanstatus AS ENUM (
                'backlog','todo','in_progress','review','done','cancelled'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE workplancategory AS ENUM (
                'development','business','marketing','operations',
                'finance','legal','content','sales','other'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    op.create_table(
        "work_plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column(
            "category",
            sa.Enum(
                "development", "business", "marketing", "operations",
                "finance", "legal", "content", "sales", "other",
                name="workplancategory", create_type=False,
            ),
            server_default="development",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "backlog", "todo", "in_progress", "review", "done", "cancelled",
                name="workplanstatus", create_type=False,
            ),
            server_default="backlog",
            index=True,
        ),
        sa.Column(
            "priority",
            sa.Enum(
                "critical", "high", "normal", "low",
                name="taskpriority", create_type=False,
            ),
            server_default="normal",
            index=True,
        ),
        sa.Column("assignee", sa.String(100), server_default="founder", index=True),
        sa.Column("conductor_task_id", sa.Integer(), sa.ForeignKey("conductor_tasks.id"), nullable=True),
        sa.Column("planned_date", sa.Date(), nullable=True, index=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("estimated_hours", sa.Float(), server_default="0"),
        sa.Column("actual_hours", sa.Float(), server_default="0"),
        sa.Column("progress", sa.Integer(), server_default="0"),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_index("ix_work_plans_category", "work_plans", ["category"])


def downgrade() -> None:
    op.drop_table("work_plans")
    op.execute("DROP TYPE IF EXISTS workplanstatus")
    op.execute("DROP TYPE IF EXISTS workplancategory")
