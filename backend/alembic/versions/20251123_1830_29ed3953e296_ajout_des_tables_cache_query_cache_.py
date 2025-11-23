"""Ajout des tables cache (query_cache, cache_document_map, cache_statistics)

Revision ID: 29ed3953e296
Revises: 89edb19b24f3
Create Date: 2025-11-23 18:30:34.194568

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '29ed3953e296'
down_revision = '89edb19b24f3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Applique les modifications de la migration.
    Crée les tables de cache et leurs index.
    """
    
    # =========================================================================
    # Table: query_cache
    # =========================================================================
    op.create_table(
        'query_cache',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
            comment='Identifiant unique du cache'
        ),
        sa.Column(
            'query_text',
            sa.Text(),
            nullable=False,
            comment='Texte original de la question posée'
        ),
        sa.Column(
            'query_hash',
            sa.String(64),
            nullable=False,
            unique=True,
            comment='Hash SHA-256 de la question pour correspondance exacte'
        ),
        sa.Column(
            'query_embedding',
            postgresql.JSONB(),
            nullable=True,
            comment='Vecteur embedding de la question pour recherche par similarité'
        ),
        sa.Column(
            'response',
            sa.Text(),
            nullable=False,
            comment='Réponse générée par le LLM'
        ),
        sa.Column(
            'sources',
            postgresql.JSONB(),
            nullable=True,
            server_default='[]',
            comment='Liste des sources utilisées (document_id, title, page, chunk_index)'
        ),
        sa.Column(
            'token_count',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Nombre de tokens de la réponse'
        ),
        sa.Column(
            'cost_saved_usd',
            sa.Numeric(10, 6),
            nullable=False,
            server_default='0.0',
            comment='Coût économisé en USD par hit cache'
        ),
        sa.Column(
            'cost_saved_xaf',
            sa.Numeric(12, 2),
            nullable=False,
            server_default='0.0',
            comment='Coût économisé en XAF par hit cache'
        ),
        sa.Column(
            'hit_count',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Nombre de fois que ce cache a été utilisé'
        ),
        sa.Column(
            'last_hit_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Date et heure du dernier hit cache'
        ),
        sa.Column(
            'expires_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW() + INTERVAL '7 days'"),
            comment='Date d expiration du cache (TTL 7 jours)'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('NOW()'),
            comment='Date de création'
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('NOW()'),
            comment='Date de dernière modification'
        ),
        comment='Cache des questions/réponses pour le chatbot RAG'
    )
    
    # Index pour query_cache
    op.create_index(
        'idx_query_cache_hash',
        'query_cache',
        ['query_hash'],
        unique=True
    )
    op.create_index(
        'idx_query_cache_expires_at',
        'query_cache',
        ['expires_at']
    )
    op.create_index(
        'idx_query_cache_created_at',
        'query_cache',
        ['created_at']
    )
    
    # =========================================================================
    # Table: cache_document_map
    # =========================================================================
    op.create_table(
        'cache_document_map',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
            comment='Identifiant unique du mapping'
        ),
        sa.Column(
            'cache_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('query_cache.id', ondelete='CASCADE'),
            nullable=False,
            comment='Référence vers l entrée de cache'
        ),
        sa.Column(
            'document_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('documents.id', ondelete='CASCADE'),
            nullable=False,
            comment='Référence vers le document utilisé'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('NOW()'),
            comment='Date de création du mapping'
        ),
        comment='Mapping entre entrées de cache et documents utilisés'
    )
    
    # Index pour cache_document_map
    op.create_index(
        'idx_cache_document_map_cache_id',
        'cache_document_map',
        ['cache_id']
    )
    op.create_index(
        'idx_cache_document_map_document_id',
        'cache_document_map',
        ['document_id']
    )
    op.create_index(
        'idx_cache_document_map_unique',
        'cache_document_map',
        ['cache_id', 'document_id'],
        unique=True
    )
    
    # =========================================================================
    # Table: cache_statistics
    # =========================================================================
    op.create_table(
        'cache_statistics',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
            comment='Identifiant unique des statistiques'
        ),
        sa.Column(
            'date',
            sa.Date(),
            nullable=False,
            unique=True,
            comment='Date des statistiques (format YYYY-MM-DD)'
        ),
        sa.Column(
            'total_requests',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Nombre total de requêtes chatbot pour la journée'
        ),
        sa.Column(
            'cache_hits',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Nombre de requêtes servies depuis le cache'
        ),
        sa.Column(
            'cache_misses',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Nombre de requêtes nécessitant le pipeline RAG complet'
        ),
        sa.Column(
            'hit_rate',
            sa.Numeric(5, 2),
            nullable=False,
            server_default='0.0',
            comment='Taux de hit cache en pourcentage'
        ),
        sa.Column(
            'tokens_saved',
            sa.BigInteger(),
            nullable=False,
            server_default='0',
            comment='Nombre total de tokens économisés'
        ),
        sa.Column(
            'cost_saved_usd',
            sa.Numeric(10, 4),
            nullable=False,
            server_default='0.0',
            comment='Économies totales en USD'
        ),
        sa.Column(
            'cost_saved_xaf',
            sa.Numeric(12, 2),
            nullable=False,
            server_default='0.0',
            comment='Économies totales en XAF'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('NOW()'),
            comment='Date de création de l enregistrement'
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('NOW()'),
            comment='Date de dernière mise à jour'
        ),
        comment='Statistiques journalières agrégées du cache'
    )
    
    # Index pour cache_statistics
    op.create_index(
        'idx_cache_statistics_date',
        'cache_statistics',
        ['date'],
        unique=True
    )


def downgrade() -> None:
    """
    Annule les modifications de la migration.
    Supprime les tables de cache dans l'ordre inverse.
    """
    
    # Suppression des index et tables dans l'ordre inverse
    
    # cache_statistics
    op.drop_index('idx_cache_statistics_date', table_name='cache_statistics')
    op.drop_table('cache_statistics')
    
    # cache_document_map
    op.drop_index('idx_cache_document_map_unique', table_name='cache_document_map')
    op.drop_index('idx_cache_document_map_document_id', table_name='cache_document_map')
    op.drop_index('idx_cache_document_map_cache_id', table_name='cache_document_map')
    op.drop_table('cache_document_map')
    
    # query_cache
    op.drop_index('idx_query_cache_created_at', table_name='query_cache')
    op.drop_index('idx_query_cache_expires_at', table_name='query_cache')
    op.drop_index('idx_query_cache_hash', table_name='query_cache')
    op.drop_table('query_cache')
