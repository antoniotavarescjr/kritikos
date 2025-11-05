"""criar_tabelas_analise_scores

Revision ID: criar_tabelas_analise_scores
Revises: f7a3a485f036
Create Date: 2025-11-02 21:17:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'criar_tabelas_analise_scores'
down_revision = 'f7a3a485f036'
branch_labels = None
depends_on = None


def upgrade():
    # Criar tabela analise_proposicoes
    op.create_table('analise_proposicoes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('proposicao_id', sa.Integer(), nullable=True),
        sa.Column('resumo_texto', sa.Text(), nullable=True),
        sa.Column('data_resumo', sa.DateTime(), nullable=True),
        sa.Column('is_trivial', sa.Boolean(), nullable=True),
        sa.Column('data_filtro_trivial', sa.DateTime(), nullable=True),
        sa.Column('par_score', sa.Integer(), nullable=True),
        sa.Column('escopo_impacto', sa.Integer(), nullable=True),
        sa.Column('alinhamento_ods', sa.Integer(), nullable=True),
        sa.Column('inovacao_eficiencia', sa.Integer(), nullable=True),
        sa.Column('sustentabilidade_fiscal', sa.Integer(), nullable=True),
        sa.Column('penalidade_oneracao', sa.Integer(), nullable=True),
        sa.Column('ods_identificados', sa.ARRAY(sa.Integer()), nullable=True),
        sa.Column('resumo_analise', sa.Text(), nullable=True),
        sa.Column('data_analise', sa.DateTime(), nullable=True),
        sa.Column('versao_analise', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['proposicao_id'], ['proposicoes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analise_proposicoes_id'), 'analise_proposicoes', ['id'], unique=False)
    op.create_index(op.f('ix_analise_proposicoes_proposicao_id'), 'analise_proposicoes', ['proposicao_id'], unique=False)

    # Criar tabela scores_deputados
    op.create_table('scores_deputados',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('deputado_id', sa.Integer(), nullable=True),
        sa.Column('desempenho_legislativo', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('relevancia_social', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('responsabilidade_fiscal', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('etica_legalidade', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('score_final', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('total_proposicoes', sa.Integer(), nullable=True),
        sa.Column('props_analisadas', sa.Integer(), nullable=True),
        sa.Column('props_triviais', sa.Integer(), nullable=True),
        sa.Column('props_relevantes', sa.Integer(), nullable=True),
        sa.Column('data_calculo', sa.DateTime(), nullable=True),
        sa.Column('versao_metodologia', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['deputado_id'], ['deputados.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scores_deputados_deputado_id'), 'scores_deputados', ['deputado_id'], unique=False)
    op.create_index(op.f('ix_scores_deputados_id'), 'scores_deputados', ['id'], unique=False)

    # Criar tabela logs_processamento
    op.create_table('logs_processamento',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tipo_processo', sa.String(length=50), nullable=True),
        sa.Column('proposicao_id', sa.Integer(), nullable=True),
        sa.Column('deputado_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('mensagem', sa.Text(), nullable=True),
        sa.Column('dados_entrada', sa.JSON(), nullable=True),
        sa.Column('dados_saida', sa.JSON(), nullable=True),
        sa.Column('data_inicio', sa.DateTime(), nullable=True),
        sa.Column('data_fim', sa.DateTime(), nullable=True),
        sa.Column('duracao_segundos', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['deputado_id'], ['deputados.id'], ),
        sa.ForeignKeyConstraint(['proposicao_id'], ['proposicoes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_logs_processamento_id'), 'logs_processamento', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_logs_processamento_id'), table_name='logs_processamento')
    op.drop_table('logs_processamento')
    op.drop_index(op.f('ix_scores_deputados_id'), table_name='scores_deputados')
    op.drop_index(op.f('ix_scores_deputados_deputado_id'), table_name='scores_deputados')
    op.drop_table('scores_deputados')
    op.drop_index(op.f('ix_analise_proposicoes_proposicao_id'), table_name='analise_proposicoes')
    op.drop_index(op.f('ix_analise_proposicoes_id'), table_name='analise_proposicoes')
    op.drop_table('analise_proposicoes')
