# -*- coding: utf-8 -*-
"""
Service Audit Logs - Gestion des logs d'audit.

Fournit les méthodes pour récupérer, filtrer et analyser
les logs d'audit du système.

Sprint 13 - Complément : Service Audit Logs Admin
Auteur: IroBot Team
Date: 2025-12-02
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy import func, and_, or_, cast, String
from sqlalchemy.orm import Session, joinedload

from app.models.audit_log import AuditLog
from app.models.user import User

logger = logging.getLogger(__name__)


class AuditLogService:
    """Service pour la gestion des logs d'audit."""
    
    # ==========================================================================
    # MÉTHODES DE RÉCUPÉRATION
    # ==========================================================================
    
    @staticmethod
    def get_logs(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        user_id: Optional[UUID] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
        include_user: bool = True
    ) -> Tuple[List[AuditLog], int]:
        """
        Récupère les logs d'audit avec pagination et filtrage.
        
        Args:
            db: Session de base de données
            page: Numéro de la page (1-indexed)
            page_size: Nombre d'éléments par page
            user_id: Filtrer par ID utilisateur
            action: Filtrer par type d'action
            entity_type: Filtrer par type d'entité
            start_date: Date de début (incluse)
            end_date: Date de fin (incluse)
            search: Recherche textuelle dans les détails
            include_user: Inclure les informations utilisateur
            
        Returns:
            Tuple (liste des logs, nombre total)
        """
        try:
            # Construction de la requête de base
            query = db.query(AuditLog)
            
            # Jointure avec User si demandé
            if include_user:
                query = query.options(joinedload(AuditLog.user))
            
            # Application des filtres
            filters = []
            
            if user_id:
                filters.append(AuditLog.user_id == user_id)
                
            if action:
                filters.append(AuditLog.action == action)
                
            if entity_type:
                filters.append(AuditLog.entity_type == entity_type)
                
            if start_date:
                # Début de journée
                start_datetime = datetime.combine(start_date, datetime.min.time())
                filters.append(AuditLog.created_at >= start_datetime)
                
            if end_date:
                # Fin de journée (23:59:59)
                end_datetime = datetime.combine(end_date, datetime.max.time())
                filters.append(AuditLog.created_at <= end_datetime)
                
            if search:
                # Recherche dans les détails JSONB (cast en string)
                search_pattern = f"%{search}%"
                filters.append(
                    cast(AuditLog.details, String).ilike(search_pattern)
                )
            
            # Appliquer les filtres
            if filters:
                query = query.filter(and_(*filters))
            
            # Compter le total
            total = query.count()
            
            # Pagination et tri
            offset = (page - 1) * page_size
            logs = query.order_by(
                AuditLog.created_at.desc()
            ).offset(offset).limit(page_size).all()
            
            logger.info(
                f"📋 Récupération logs d'audit: page={page}, "
                f"page_size={page_size}, total={total}"
            )
            
            return logs, total
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération logs d'audit: {e}")
            raise
    
    @staticmethod
    def get_log_by_id(
        db: Session,
        log_id: UUID,
        include_user: bool = True
    ) -> Optional[AuditLog]:
        """
        Récupère un log d'audit par son ID.
        
        Args:
            db: Session de base de données
            log_id: UUID du log
            include_user: Inclure les informations utilisateur
            
        Returns:
            Log d'audit ou None
        """
        try:
            query = db.query(AuditLog)
            
            if include_user:
                query = query.options(joinedload(AuditLog.user))
                
            return query.filter(AuditLog.id == log_id).first()
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération log {log_id}: {e}")
            raise
    
    # ==========================================================================
    # MÉTHODES DE STATISTIQUES
    # ==========================================================================
    
    @staticmethod
    def get_stats(db: Session) -> Dict[str, Any]:
        """
        Récupère les statistiques globales des logs d'audit.
        
        Args:
            db: Session de base de données
            
        Returns:
            Dictionnaire de statistiques
        """
        try:
            now = datetime.utcnow()
            today_start = datetime.combine(now.date(), datetime.min.time())
            week_start = today_start - timedelta(days=now.weekday())
            month_start = today_start.replace(day=1)
            
            # Total des logs
            total_logs = db.query(func.count(AuditLog.id)).scalar() or 0
            
            # Logs aujourd'hui
            logs_today = db.query(func.count(AuditLog.id)).filter(
                AuditLog.created_at >= today_start
            ).scalar() or 0
            
            # Logs cette semaine
            logs_this_week = db.query(func.count(AuditLog.id)).filter(
                AuditLog.created_at >= week_start
            ).scalar() or 0
            
            # Logs ce mois
            logs_this_month = db.query(func.count(AuditLog.id)).filter(
                AuditLog.created_at >= month_start
            ).scalar() or 0
            
            # Par type d'action
            action_counts = db.query(
                AuditLog.action,
                func.count(AuditLog.id)
            ).group_by(AuditLog.action).all()
            
            by_action = {action: count for action, count in action_counts if action}
            
            # Par type d'entité
            entity_counts = db.query(
                AuditLog.entity_type,
                func.count(AuditLog.id)
            ).group_by(AuditLog.entity_type).all()
            
            by_entity_type = {
                entity: count for entity, count in entity_counts if entity
            }
            
            # Dernière activité
            last_log = db.query(AuditLog).order_by(
                AuditLog.created_at.desc()
            ).first()
            
            last_activity = last_log.created_at if last_log else None
            
            logger.info(f"📊 Statistiques logs: total={total_logs}, today={logs_today}")
            
            return {
                "total_logs": total_logs,
                "logs_today": logs_today,
                "logs_this_week": logs_this_week,
                "logs_this_month": logs_this_month,
                "by_action": by_action,
                "by_entity_type": by_entity_type,
                "last_activity": last_activity
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur statistiques logs: {e}")
            raise
    
    @staticmethod
    def get_activity_by_date(
        db: Session,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Récupère l'activité des logs par date sur une période.
        
        Args:
            db: Session de base de données
            start_date: Date de début
            end_date: Date de fin
            
        Returns:
            Liste d'activité par date
        """
        try:
            # Requête pour compter par date
            daily_counts = db.query(
                func.date(AuditLog.created_at).label('log_date'),
                func.count(AuditLog.id).label('count')
            ).filter(
                AuditLog.created_at >= datetime.combine(start_date, datetime.min.time()),
                AuditLog.created_at <= datetime.combine(end_date, datetime.max.time())
            ).group_by(
                func.date(AuditLog.created_at)
            ).order_by(
                func.date(AuditLog.created_at)
            ).all()
            
            # Construire le résultat avec toutes les dates
            result = []
            current_date = start_date
            counts_dict = {str(row.log_date): row.count for row in daily_counts}
            
            while current_date <= end_date:
                date_str = str(current_date)
                result.append({
                    "date": current_date,
                    "count": counts_dict.get(date_str, 0)
                })
                current_date += timedelta(days=1)
            
            logger.info(
                f"📈 Activité logs: {start_date} → {end_date}, "
                f"{len(result)} jours"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur activité par date: {e}")
            raise
    
    # ==========================================================================
    # MÉTHODES UTILITAIRES
    # ==========================================================================
    
    @staticmethod
    def get_distinct_actions(db: Session) -> List[str]:
        """
        Récupère la liste des actions distinctes.
        
        Args:
            db: Session de base de données
            
        Returns:
            Liste des types d'actions
        """
        try:
            actions = db.query(AuditLog.action).distinct().all()
            return sorted([a[0] for a in actions if a[0]])
        except Exception as e:
            logger.error(f"❌ Erreur récupération actions: {e}")
            raise
    
    @staticmethod
    def get_distinct_entity_types(db: Session) -> List[str]:
        """
        Récupère la liste des types d'entités distincts.
        
        Args:
            db: Session de base de données
            
        Returns:
            Liste des types d'entités
        """
        try:
            types = db.query(AuditLog.entity_type).distinct().all()
            return sorted([t[0] for t in types if t[0]])
        except Exception as e:
            logger.error(f"❌ Erreur récupération entity types: {e}")
            raise
    
    @staticmethod
    def get_user_activity(
        db: Session,
        user_id: UUID,
        limit: int = 50
    ) -> List[AuditLog]:
        """
        Récupère les dernières actions d'un utilisateur.
        
        Args:
            db: Session de base de données
            user_id: UUID de l'utilisateur
            limit: Nombre maximum de résultats
            
        Returns:
            Liste des logs de l'utilisateur
        """
        try:
            return db.query(AuditLog).filter(
                AuditLog.user_id == user_id
            ).order_by(
                AuditLog.created_at.desc()
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"❌ Erreur activité utilisateur {user_id}: {e}")
            raise
    
    # ==========================================================================
    # MÉTHODES DE NETTOYAGE
    # ==========================================================================
    
    @staticmethod
    def cleanup_old_logs(
        db: Session,
        days_to_keep: int = 90
    ) -> int:
        """
        Supprime les logs plus anciens que la période spécifiée.
        
        Args:
            db: Session de base de données
            days_to_keep: Nombre de jours à conserver
            
        Returns:
            Nombre de logs supprimés
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            deleted = db.query(AuditLog).filter(
                AuditLog.created_at < cutoff_date
            ).delete(synchronize_session=False)
            
            db.commit()
            
            logger.info(
                f"🧹 Nettoyage logs d'audit: {deleted} logs supprimés "
                f"(antérieurs à {cutoff_date.date()})"
            )
            
            return deleted
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Erreur nettoyage logs: {e}")
            raise