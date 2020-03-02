"""empty message

Revision ID: bace615d47b5
Revises: 7b6727bd8be3
Create Date: 2020-03-02 15:34:54.085940

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "bace615d47b5"
down_revision = "7b6727bd8be3"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "checkpoints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column(
            "time",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("checkpoints")
    # ### end Alembic commands ###
