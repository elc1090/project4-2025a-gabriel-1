"""Implementa sistema de lousas com propriedade e acesso

Revision ID: a6e6ff6eada7
Revises: 
Create Date: 2025-06-17 15:08:48.098829

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a6e6ff6eada7'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
    sa.Column('id', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('profile_pic', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('whiteboards',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nickname', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('owner_id', sa.String(length=255), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stroke',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('whiteboard_id', sa.Integer(), nullable=False),
    sa.Column('color', sa.String(length=7), nullable=False),
    sa.Column('line_width', sa.Float(), nullable=False),
    sa.Column('points_json', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['whiteboard_id'], ['whiteboards.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('whiteboard_access',
    sa.Column('user_id', sa.String(length=255), nullable=False),
    sa.Column('whiteboard_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['whiteboard_id'], ['whiteboards.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'whiteboard_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('whiteboard_access')
    op.drop_table('stroke')
    op.drop_table('whiteboards')
    op.drop_table('users')
    # ### end Alembic commands ###
