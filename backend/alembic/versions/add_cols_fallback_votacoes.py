"""adicionar colunas fallback votacoes

Revision ID: add_cols_fallback_votacoes
Revises: criar_tabela_blocos_partidarios
Create Date: 2025-10-25 01:37:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_cols_fallback_votacoes'
down_revision = 'criar_tabela_blocos_partidarios'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar colunas à tabela votacoes
    op.add_column('votacoes', sa.Column('sigla_orgao', sa.String(20), nullable=True))
    op.add_column('votacoes', sa.Column('uri_orgao', sa.String(500), nullable=True))
    op.add_column('votacoes', sa.Column('data_hora_registro', sa.TIMESTAMP(), nullable=True))
    op.add_column('votacoes', sa.Column('descricao_tipo_votacao', sa.String(100), nullable=True))
    op.add_column('votacoes', sa.Column('descricao_resultado', sa.String(200), nullable=True))
    op.add_column('votacoes', sa.Column('aprovacao', sa.Boolean(), nullable=True))
    op.add_column('votacoes', sa.Column('uri_votacao', sa.String(500), nullable=True))
    
    # Criar tabelas auxiliares para fallback
    op.create_table('votacoes_objetos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('votacao_id', sa.Integer(), nullable=False),
        sa.Column('proposicao_id', sa.Integer(), nullable=False),
        sa.Column('descricao_efeito', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['proposicao_id'], ['proposicoes.id'], ),
        sa.ForeignKeyConstraint(['votacao_id'], ['votacoes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('votacao_id', 'proposicao_id', name='_votacao_objeto_uc')
    )
    
    op.create_table('votacoes_proposicoes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('votacao_id', sa.Integer(), nullable=False),
        sa.Column('proposicao_id', sa.Integer(), nullable=False),
        sa.Column('descricao_efeito', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['proposicao_id'], ['proposicoes.id'], ),
        sa.ForeignKeyConstraint(['votacao_id'], ['votacoes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('votacao_id', 'proposicao_id', name='_votacao_proposicao_uc')
    )
    
    op.create_table('orientacoes_bancada',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('votacao_id', sa.Integer(), nullable=False),
        sa.Column('partido_id', sa.Integer(), nullable=True),
        sa.Column('bloco_id', sa.Integer(), nullable=True),
        sa.Column('orientacao', sa.String(50), nullable=True),
        sa.Column('tipo_bancada', sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(['bloco_id'], ['blocos_partidarios.id'], ),
        sa.ForeignKeyConstraint(['partido_id'], ['partidos.id'], ),
        sa.ForeignKeyConstraint(['votacao_id'], ['votacoes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('votacao_id', 'partido_id', 'tipo_bancada', name='_orientacao_bancada_uc')
    )


def downgrade():
    # Remover tabelas auxiliares
    op.drop_table('orientacoes_bancada')
    op.drop_table('votacoes_proposicoes')
    op.drop_table('votacoes_objetos')
    
    # Remover colunas da tabela votacoes
    op.drop_column('votacoes', 'uri_votacao')
    op.drop_column('votacoes', 'aprovacao')
    op.drop_column('votacoes', 'descricao_resultado')
    op.drop_column('votacoes', 'descricao_tipo_votacao')
    op.drop_column('votacoes', 'data_hora_registro')
    op.drop_column('votacoes', 'uri_orgao')
    op.drop_column('votacoes', 'sigla_orgao')
