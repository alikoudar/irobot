"""Migration seed pour les configurations système

Revision ID: 89edb19b24f3
Revises: dad4713e1aa3
Create Date: 2025-11-23 10:06:34.600382

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime
import uuid
import json

# revision identifiers, used by Alembic.
revision = '89edb19b24f3'
down_revision = 'dad4713e1aa3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Insérer les configurations système par défaut."""
    
    # Connexion pour exécuter les inserts
    connection = op.get_bind()
    
    # Date actuelle pour updated_at
    now = datetime.utcnow()
    
    # ==========================================================================
    # CONFIGURATIONS À INSÉRER
    # ==========================================================================
    
    configs = [
        # ======================================================================
        # TARIFS MISTRAL
        # ======================================================================
        {
            "key": "mistral.pricing.embed",
            "value": {
                "model": "mistral-embed",
                "price_per_million_input": 0.10,
                "price_per_million_output": 0.0,
                "unit": "tokens",
                "description": "Tarif embedding Mistral"
            },
            "description": "Tarif pour le modèle mistral-embed (embedding)",
            "category": "pricing",
            "is_sensitive": False
        },
        {
            "key": "mistral.pricing.small",
            "value": {
                "model": "mistral-small-latest",
                "price_per_million_input": 0.10,
                "price_per_million_output": 0.30,
                "unit": "tokens",
                "description": "Tarif Mistral Small (reranking, titres)"
            },
            "description": "Tarif pour le modèle mistral-small (reranking, génération titres)",
            "category": "pricing",
            "is_sensitive": False
        },
        {
            "key": "mistral.pricing.medium",
            "value": {
                "model": "mistral-medium-latest",
                "price_per_million_input": 0.40,
                "price_per_million_output": 2.00,
                "unit": "tokens",
                "description": "Tarif Mistral Medium (génération)"
            },
            "description": "Tarif pour le modèle mistral-medium (génération de réponses)",
            "category": "pricing",
            "is_sensitive": False
        },
        {
            "key": "mistral.pricing.large",
            "value": {
                "model": "mistral-large-latest",
                "price_per_million_input": 2.00,
                "price_per_million_output": 6.00,
                "unit": "tokens",
                "description": "Tarif Mistral Large (génération avancée)"
            },
            "description": "Tarif pour le modèle mistral-large (génération avancée)",
            "category": "pricing",
            "is_sensitive": False
        },
        {
            "key": "mistral.pricing.ocr",
            "value": {
                "model": "mistral-ocr-latest",
                "price_per_thousand_pages": 1.00,
                "unit": "pages",
                "description": "Tarif Mistral OCR"
            },
            "description": "Tarif pour le modèle mistral-ocr (extraction texte images)",
            "category": "pricing",
            "is_sensitive": False
        },
        
        # ======================================================================
        # MODÈLES PAR DÉFAUT
        # ======================================================================
        {
            "key": "models.embedding",
            "value": {
                "model_name": "mistral-embed",
                "dimension": 1024,
                "max_tokens_per_text": 8192,
                "description": "Modèle d'embedding par défaut"
            },
            "description": "Configuration du modèle d'embedding",
            "category": "models",
            "is_sensitive": False
        },
        {
            "key": "models.reranking",
            "value": {
                "model_name": "mistral-small-latest",
                "top_k": 20,
                "description": "Modèle de reranking par défaut"
            },
            "description": "Configuration du modèle de reranking",
            "category": "models",
            "is_sensitive": False
        },
        {
            "key": "models.generation",
            "value": {
                "model_name": "mistral-medium-latest",
                "max_tokens": 2048,
                "temperature": 0.7,
                "description": "Modèle de génération par défaut"
            },
            "description": "Configuration du modèle de génération LLM",
            "category": "models",
            "is_sensitive": False
        },
        {
            "key": "models.title_generation",
            "value": {
                "model_name": "mistral-small-latest",
                "max_tokens": 50,
                "temperature": 0.5,
                "description": "Modèle pour génération des titres de conversation"
            },
            "description": "Configuration du modèle de génération de titres",
            "category": "models",
            "is_sensitive": False
        },
        {
            "key": "models.ocr",
            "value": {
                "model_name": "mistral-ocr-latest",
                "description": "Modèle OCR par défaut"
            },
            "description": "Configuration du modèle OCR",
            "category": "models",
            "is_sensitive": False
        },
        
        # ======================================================================
        # PARAMÈTRES CHUNKING
        # ======================================================================
        {
            "key": "chunking.size",
            "value": {
                "value": 512,
                "unit": "tokens",
                "description": "Taille cible des chunks en tokens"
            },
            "description": "Taille des chunks pour le découpage des documents",
            "category": "chunking",
            "is_sensitive": False
        },
        {
            "key": "chunking.overlap",
            "value": {
                "value": 51,
                "unit": "tokens",
                "percentage": 10,
                "description": "Chevauchement entre chunks (10% recommandé)"
            },
            "description": "Chevauchement entre les chunks",
            "category": "chunking",
            "is_sensitive": False
        },
        {
            "key": "chunking.min_size",
            "value": {
                "value": 50,
                "unit": "tokens",
                "description": "Taille minimum d'un chunk"
            },
            "description": "Taille minimum d'un chunk",
            "category": "chunking",
            "is_sensitive": False
        },
        {
            "key": "chunking.max_size",
            "value": {
                "value": 1024,
                "unit": "tokens",
                "description": "Taille maximum d'un chunk"
            },
            "description": "Taille maximum d'un chunk",
            "category": "chunking",
            "is_sensitive": False
        },
        
        # ======================================================================
        # PARAMÈTRES EMBEDDING
        # ======================================================================
        {
            "key": "embedding.batch_size",
            "value": {
                "value": 30,
                "description": "Nombre de textes par appel API embedding"
            },
            "description": "Taille des batches pour l'embedding",
            "category": "embedding",
            "is_sensitive": False
        },
        
        # ======================================================================
        # PARAMÈTRES RECHERCHE
        # ======================================================================
        {
            "key": "search.top_k",
            "value": {
                "value": 10,
                "description": "Nombre de résultats à retourner par recherche"
            },
            "description": "Nombre de résultats de recherche",
            "category": "search",
            "is_sensitive": False
        },
        {
            "key": "search.hybrid_alpha",
            "value": {
                "value": 0.75,
                "description": "Poids semantic vs BM25 (0=BM25, 1=semantic)"
            },
            "description": "Alpha pour la recherche hybride",
            "category": "search",
            "is_sensitive": False
        },
        {
            "key": "search.rerank_enabled",
            "value": {
                "value": True,
                "description": "Activer le reranking des résultats"
            },
            "description": "Activation du reranking",
            "category": "search",
            "is_sensitive": False
        },
        
        # ======================================================================
        # PARAMÈTRES UPLOAD
        # ======================================================================
        {
            "key": "upload.max_file_size_mb",
            "value": {
                "value": 50,
                "unit": "MB",
                "description": "Taille maximum d'un fichier uploadé"
            },
            "description": "Taille max par fichier en MB",
            "category": "upload",
            "is_sensitive": False
        },
        {
            "key": "upload.max_batch_size_mb",
            "value": {
                "value": 500,
                "unit": "MB",
                "description": "Taille maximum totale d'un batch d'upload"
            },
            "description": "Taille max totale d'un batch en MB",
            "category": "upload",
            "is_sensitive": False
        },
        {
            "key": "upload.max_files_per_batch",
            "value": {
                "value": 10,
                "description": "Nombre maximum de fichiers par upload"
            },
            "description": "Nombre max de fichiers par batch",
            "category": "upload",
            "is_sensitive": False
        },
        {
            "key": "upload.allowed_extensions",
            "value": {
                "value": ["pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt", "rtf", "txt", "md", "png", "jpg", "jpeg", "webp"],
                "description": "Extensions de fichiers autorisées"
            },
            "description": "Extensions de fichiers autorisées",
            "category": "upload",
            "is_sensitive": False
        },
        
        # ======================================================================
        # PARAMÈTRES RATE LIMITING
        # ======================================================================
        {
            "key": "rate_limit.per_minute",
            "value": {
                "value": 50,
                "description": "Nombre de requêtes par minute par utilisateur"
            },
            "description": "Rate limit par minute",
            "category": "rate_limit",
            "is_sensitive": False
        },
        {
            "key": "rate_limit.per_hour",
            "value": {
                "value": 500,
                "description": "Nombre de requêtes par heure par utilisateur"
            },
            "description": "Rate limit par heure",
            "category": "rate_limit",
            "is_sensitive": False
        },
        
        # ======================================================================
        # PARAMÈTRES CACHE
        # ======================================================================
        {
            "key": "cache.query_ttl_seconds",
            "value": {
                "value": 3600,
                "unit": "seconds",
                "description": "Durée de vie du cache des requêtes (1 heure)"
            },
            "description": "TTL du cache des requêtes",
            "category": "cache",
            "is_sensitive": False
        },
        {
            "key": "cache.config_ttl_seconds",
            "value": {
                "value": 300,
                "unit": "seconds",
                "description": "Durée de vie du cache des configurations (5 minutes)"
            },
            "description": "TTL du cache des configurations",
            "category": "cache",
            "is_sensitive": False
        },
        
        # ======================================================================
        # PARAMÈTRES TAUX DE CHANGE
        # ======================================================================
        {
            "key": "exchange_rate.default_usd_xaf",
            "value": {
                "value": 655.957,
                "description": "Taux par défaut USD/XAF (fallback)"
            },
            "description": "Taux de change par défaut USD vers XAF",
            "category": "exchange_rate",
            "is_sensitive": False
        },
        {
            "key": "exchange_rate.api_enabled",
            "value": {
                "value": True,
                "description": "Activer la mise à jour automatique depuis l'API"
            },
            "description": "Activation de l'API de taux de change",
            "category": "exchange_rate",
            "is_sensitive": False
        },
        {
            "key": "exchange_rate.update_frequency_hours",
            "value": {
                "value": 24,
                "unit": "hours",
                "description": "Fréquence de mise à jour du taux"
            },
            "description": "Fréquence de mise à jour du taux de change",
            "category": "exchange_rate",
            "is_sensitive": False
        },
    ]
    
    # Insérer les configurations avec SQL raw et json.dumps()
    for config in configs:
        # Convertir la valeur en JSON string
        value_json = json.dumps(config["value"])
        
        # Utiliser CAST() au lieu de :: pour éviter conflit avec les paramètres SQLAlchemy
        # Générer l'ID avec gen_random_uuid() de PostgreSQL
        connection.execute(
            sa.text("""
                INSERT INTO system_configs (id, key, value, description, category, is_sensitive, created_at, updated_at)
                VALUES (gen_random_uuid(), :key, CAST(:value AS jsonb), :description, :category, :is_sensitive, :created_at, :updated_at)
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    description = EXCLUDED.description,
                    category = EXCLUDED.category,
                    updated_at = EXCLUDED.updated_at
            """),
            {
                "key": config["key"],
                "value": value_json,
                "description": config["description"],
                "category": config["category"],
                "is_sensitive": config["is_sensitive"],
                "created_at": now,
                "updated_at": now
            }
        )
    
    # Insérer le taux de change initial
    connection.execute(
        sa.text("""
            INSERT INTO exchange_rates (id, currency_from, currency_to, rate, fetched_at)
            VALUES (:id, :currency_from, :currency_to, :rate, :fetched_at)
            ON CONFLICT DO NOTHING
        """),
        {
            "id": str(uuid.uuid4()),
            "currency_from": "USD",
            "currency_to": "XAF",
            "rate": 655.957,
            "fetched_at": now
        }
    )


def downgrade() -> None:
    """Supprimer les configurations système."""
    connection = op.get_bind()
    
    # Supprimer toutes les configs insérées
    connection.execute(
        sa.text("DELETE FROM system_configs WHERE category IN ('pricing', 'models', 'chunking', 'embedding', 'search', 'upload', 'rate_limit', 'cache', 'exchange_rate')")
    )