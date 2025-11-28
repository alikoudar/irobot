# app/schemas/manager_dashboard_schemas.py
"""
Schémas Pydantic pour le dashboard manager.
Version simplifiée des schemas admin (sans coûts).
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict
from datetime import datetime


class ManagerDocumentStats(BaseModel):
    """Statistiques des documents du manager."""
    
    total: int = Field(..., description="Nombre total de documents uploadés par le manager")
    completed: int = Field(..., description="Nombre de documents traités avec succès")
    processing: int = Field(..., description="Nombre de documents en cours de traitement")
    failed: int = Field(..., description="Nombre de documents échoués")
    total_chunks: int = Field(..., description="Nombre total de chunks créés")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "total": 45,
                "completed": 42,
                "processing": 2,
                "failed": 1,
                "total_chunks": 1250
            }
        }
    )


class ManagerMessageStats(BaseModel):
    """Statistiques des messages utilisant les documents du manager."""
    
    total: int = Field(..., description="Nombre total de messages générés")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "total": 320
            }
        }
    )


class DocumentByCategory(BaseModel):
    """Nombre de documents par catégorie."""
    
    category: str = Field(..., description="Nom de la catégorie")
    count: int = Field(..., description="Nombre de documents dans cette catégorie")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "category": "Lettres Circulaires",
                "count": 15
            }
        }
    )


class DateRange(BaseModel):
    """Plage de dates pour les statistiques."""
    
    start: str = Field(..., description="Date de début au format ISO")
    end: str = Field(..., description="Date de fin au format ISO")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start": "2025-11-01T00:00:00",
                "end": "2025-11-28T23:59:59"
            }
        }
    )


class ManagerDashboardOverviewResponse(BaseModel):
    """Réponse complète du dashboard manager (sans coûts, sans feedbacks)."""
    
    documents: ManagerDocumentStats
    messages: ManagerMessageStats
    documents_by_category: List[DocumentByCategory]
    date_range: DateRange
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "documents": {
                    "total": 45,
                    "completed": 42,
                    "processing": 2,
                    "failed": 1,
                    "total_chunks": 1250
                },
                "messages": {
                    "total": 320
                },
                "documents_by_category": [
                    {"category": "Lettres Circulaires", "count": 15},
                    {"category": "Décisions du Gouverneur", "count": 12},
                    {"category": "Procédures et Modes Opératoires", "count": 10},
                    {"category": "Clauses et Conditions Générales", "count": 8}
                ],
                "date_range": {
                    "start": "2025-11-01T00:00:00",
                    "end": "2025-11-28T23:59:59"
                }
            }
        }
    )


class ManagerTopDocument(BaseModel):
    """Document avec son nombre d'utilisations."""
    
    document_id: str = Field(..., description="UUID du document")
    title: str = Field(..., description="Nom du fichier")
    category: Optional[str] = Field(None, description="Catégorie du document")
    usage_count: int = Field(..., description="Nombre d'utilisations (chunks)")
    total_chunks: int = Field(..., description="Nombre total de chunks")
    uploaded_at: Optional[str] = Field(None, description="Date d'upload au format ISO")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Lettre_Circulaire_2025_001.pdf",
                "category": "Lettres Circulaires",
                "usage_count": 45,
                "total_chunks": 28,
                "uploaded_at": "2025-11-15T10:30:00"
            }
        }
    )


class ManagerTopDocumentsResponse(BaseModel):
    """Liste des top documents du manager."""
    
    documents: List[ManagerTopDocument]
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "documents": [
                    {
                        "document_id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "Lettre_Circulaire_2025_001.pdf",
                        "category": "Lettres Circulaires",
                        "usage_count": 45,
                        "total_chunks": 28,
                        "uploaded_at": "2025-11-15T10:30:00"
                    }
                ]
            }
        }
    )


class DocumentTimelineItem(BaseModel):
    """Item de la timeline des documents."""
    
    date: Optional[str] = Field(None, description="Date au format ISO")
    documents_count: int = Field(..., description="Nombre de documents uploadés ce jour")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "date": "2025-11-15",
                "documents_count": 3
            }
        }
    )


class ManagerDocumentsTimelineResponse(BaseModel):
    """Timeline des documents uploadés par le manager."""
    
    timeline: List[DocumentTimelineItem]
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "timeline": [
                    {"date": "2025-11-15", "documents_count": 3},
                    {"date": "2025-11-20", "documents_count": 5},
                    {"date": "2025-11-25", "documents_count": 2}
                ]
            }
        }
    )