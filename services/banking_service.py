"""
Service Bancaire FLOOSE
Couche métier pour la gestion des comptes et transactions bancaires
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from .models import (
    Bank, BankAccount, Transaction, BankConnection,
    TransactionCategory, ConnectionStatus, generate_id
)
from .bank_providers import get_bank_provider, BankAPIProvider

logger = logging.getLogger(__name__)


class BankingService:
    """
    Service de gestion des opérations bancaires
    Interface entre l'application et les providers bancaires
    """

    def __init__(self, provider_name: str = None):
        """
        Initialise le service bancaire

        Args:
            provider_name: Nom du provider à utiliser (None = défaut/mock)
        """
        self._provider: BankAPIProvider = get_bank_provider(provider_name)
        self._user_connections: Dict[str, Dict[str, BankConnection]] = {}

        logger.info(f"BankingService initialisé avec provider: {self._provider.provider_name}")

    # ============================================================
    # BANKS
    # ============================================================

    def get_available_banks(self) -> List[Dict[str, Any]]:
        """
        Retourne la liste des banques disponibles

        Returns:
            List[dict]: Liste des banques avec leurs informations
        """
        banks = self._provider.get_available_banks()
        return [bank.to_dict() for bank in banks]

    def get_bank_by_id(self, bank_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une banque par son ID

        Args:
            bank_id: Identifiant de la banque

        Returns:
            dict ou None: Informations de la banque
        """
        banks = self._provider.get_available_banks()
        bank = next((b for b in banks if b.id == bank_id), None)
        return bank.to_dict() if bank else None

    # ============================================================
    # CONNECTIONS
    # ============================================================

    def connect_bank(self, user_id: str, bank_id: str) -> Dict[str, Any]:
        """
        Connecte un utilisateur à une banque

        Args:
            user_id: Identifiant de l'utilisateur
            bank_id: Identifiant de la banque

        Returns:
            dict: Résultat de la connexion
        """
        try:
            connection = self._provider.connect_bank(user_id, bank_id)

            # Stocker la connexion localement
            if user_id not in self._user_connections:
                self._user_connections[user_id] = {}
            self._user_connections[user_id][bank_id] = connection

            logger.info(f"Connexion établie: {user_id} -> {bank_id}")

            return {
                'success': True,
                'connection': connection.to_dict(),
                'message': 'Connexion établie avec succès'
            }

        except ValueError as e:
            logger.error(f"Erreur de connexion: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'INVALID_BANK'
            }
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la connexion: {e}")
            return {
                'success': False,
                'error': 'Erreur lors de la connexion à la banque',
                'error_code': 'CONNECTION_ERROR'
            }

    def disconnect_bank(self, user_id: str, bank_id: str) -> Dict[str, Any]:
        """
        Déconnecte un utilisateur d'une banque

        Args:
            user_id: Identifiant de l'utilisateur
            bank_id: Identifiant de la banque

        Returns:
            dict: Résultat de la déconnexion
        """
        success = self._provider.disconnect_bank(user_id, bank_id)

        if success:
            if user_id in self._user_connections:
                self._user_connections[user_id].pop(bank_id, None)

            logger.info(f"Déconnexion réussie: {user_id} -> {bank_id}")

        return {
            'success': success,
            'message': 'Déconnexion réussie' if success else 'Erreur lors de la déconnexion'
        }

    def get_user_connections(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Récupère toutes les connexions bancaires d'un utilisateur

        Args:
            user_id: Identifiant de l'utilisateur

        Returns:
            List[dict]: Liste des connexions avec statut
        """
        connections = []

        for bank in self._provider.get_available_banks():
            connection = self._provider.get_connection_status(user_id, bank.id)
            if connection.status == ConnectionStatus.CONNECTED:
                connections.append({
                    'bank': bank.to_dict(),
                    'connection': connection.to_dict()
                })

        return connections

    def get_connection_status(self, user_id: str, bank_id: str) -> Dict[str, Any]:
        """
        Vérifie le statut de connexion à une banque

        Args:
            user_id: Identifiant de l'utilisateur
            bank_id: Identifiant de la banque

        Returns:
            dict: Statut de la connexion
        """
        connection = self._provider.get_connection_status(user_id, bank_id)
        bank = self.get_bank_by_id(bank_id)

        return {
            'connected': connection.status == ConnectionStatus.CONNECTED,
            'status': connection.status.value,
            'bank': bank,
            'expires_at': connection.expires_at.isoformat() if connection.expires_at else None
        }

    # ============================================================
    # ACCOUNTS
    # ============================================================

    def get_accounts(self, user_id: str, bank_id: str = None) -> List[Dict[str, Any]]:
        """
        Récupère les comptes bancaires d'un utilisateur

        Args:
            user_id: Identifiant de l'utilisateur
            bank_id: Optionnel - filtrer par banque

        Returns:
            List[dict]: Liste des comptes
        """
        try:
            accounts = self._provider.fetch_accounts(user_id, bank_id)
            result = []

            for account in accounts:
                account_dict = account.to_dict()

                # Ajouter les infos de la banque
                bank = self.get_bank_by_id(account.bank_id)
                if bank:
                    account_dict['bank'] = bank

                result.append(account_dict)

            return result

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des comptes: {e}")
            return []

    def get_account_by_id(self, user_id: str, account_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un compte par son ID

        Args:
            user_id: Identifiant de l'utilisateur
            account_id: Identifiant du compte

        Returns:
            dict ou None: Informations du compte
        """
        accounts = self._provider.fetch_accounts(user_id)
        account = next((a for a in accounts if a.id == account_id), None)

        if account:
            account_dict = account.to_dict()
            bank = self.get_bank_by_id(account.bank_id)
            if bank:
                account_dict['bank'] = bank
            return account_dict

        return None

    def get_accounts_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Récupère un résumé des comptes de l'utilisateur

        Args:
            user_id: Identifiant de l'utilisateur

        Returns:
            dict: Résumé avec totaux et statistiques
        """
        accounts = self._provider.fetch_accounts(user_id)

        total_balance = sum(a.balance for a in accounts)
        total_checking = sum(a.balance for a in accounts if a.account_type.value == 'checking')
        total_savings = sum(a.balance for a in accounts if a.account_type.value == 'savings')

        # Grouper par banque
        by_bank = {}
        for account in accounts:
            if account.bank_id not in by_bank:
                by_bank[account.bank_id] = {
                    'bank': self.get_bank_by_id(account.bank_id),
                    'accounts': [],
                    'total': 0
                }
            by_bank[account.bank_id]['accounts'].append(account.to_dict())
            by_bank[account.bank_id]['total'] += account.balance

        return {
            'total_balance': round(total_balance, 2),
            'total_checking': round(total_checking, 2),
            'total_savings': round(total_savings, 2),
            'accounts_count': len(accounts),
            'banks_count': len(by_bank),
            'by_bank': list(by_bank.values())
        }

    # ============================================================
    # TRANSACTIONS
    # ============================================================

    def get_transactions(self, user_id: str, account_id: str,
                        date_from: datetime = None,
                        date_to: datetime = None,
                        category: str = None,
                        limit: int = 50) -> List[Dict[str, Any]]:
        """
        Récupère les transactions d'un compte

        Args:
            user_id: Identifiant de l'utilisateur
            account_id: Identifiant du compte
            date_from: Date de début (optionnel)
            date_to: Date de fin (optionnel)
            category: Filtrer par catégorie (optionnel)
            limit: Nombre maximum de transactions

        Returns:
            List[dict]: Liste des transactions
        """
        try:
            transactions = self._provider.fetch_transactions(
                user_id, account_id, date_from, date_to
            )

            # Filtrer par catégorie si spécifié
            if category:
                try:
                    cat = TransactionCategory(category)
                    transactions = [t for t in transactions if t.category == cat]
                except ValueError:
                    pass  # Ignorer si catégorie invalide

            # Limiter le nombre
            transactions = transactions[:limit]

            return [t.to_dict() for t in transactions]

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des transactions: {e}")
            return []

    def get_recent_transactions(self, user_id: str, days: int = 30,
                               limit: int = 20) -> List[Dict[str, Any]]:
        """
        Récupère les transactions récentes de tous les comptes

        Args:
            user_id: Identifiant de l'utilisateur
            days: Nombre de jours à considérer
            limit: Nombre maximum de transactions

        Returns:
            List[dict]: Liste des transactions récentes
        """
        accounts = self._provider.fetch_accounts(user_id)
        all_transactions = []

        date_from = datetime.now() - timedelta(days=days)

        for account in accounts:
            transactions = self._provider.fetch_transactions(
                user_id, account.id, date_from
            )
            for tx in transactions:
                tx_dict = tx.to_dict()
                tx_dict['account_name'] = account.name
                tx_dict['bank_id'] = account.bank_id
                all_transactions.append(tx_dict)

        # Trier par date décroissante
        all_transactions.sort(key=lambda x: x['date'], reverse=True)

        return all_transactions[:limit]

    def get_spending_by_category(self, user_id: str,
                                 days: int = 30) -> Dict[str, Any]:
        """
        Calcule les dépenses par catégorie

        Args:
            user_id: Identifiant de l'utilisateur
            days: Période en jours

        Returns:
            dict: Dépenses par catégorie
        """
        accounts = self._provider.fetch_accounts(user_id)
        date_from = datetime.now() - timedelta(days=days)

        categories = {}
        total_expenses = 0
        total_income = 0

        for account in accounts:
            transactions = self._provider.fetch_transactions(
                user_id, account.id, date_from
            )

            for tx in transactions:
                if tx.amount < 0:  # Dépense
                    cat_name = tx.category.value
                    if cat_name not in categories:
                        categories[cat_name] = {
                            'category': cat_name,
                            'total': 0,
                            'count': 0,
                            'transactions': []
                        }
                    categories[cat_name]['total'] += abs(tx.amount)
                    categories[cat_name]['count'] += 1
                    total_expenses += abs(tx.amount)
                else:  # Revenu
                    total_income += tx.amount

        # Calculer les pourcentages
        for cat in categories.values():
            cat['total'] = round(cat['total'], 2)
            cat['percentage'] = round((cat['total'] / total_expenses * 100) if total_expenses > 0 else 0, 1)

        # Trier par montant décroissant
        sorted_categories = sorted(categories.values(), key=lambda x: x['total'], reverse=True)

        return {
            'period_days': days,
            'total_expenses': round(total_expenses, 2),
            'total_income': round(total_income, 2),
            'net': round(total_income - total_expenses, 2),
            'categories': sorted_categories
        }

    # ============================================================
    # SYNC
    # ============================================================

    def sync_all_accounts(self, user_id: str) -> Dict[str, Any]:
        """
        Synchronise tous les comptes d'un utilisateur

        Args:
            user_id: Identifiant de l'utilisateur

        Returns:
            dict: Résultat de la synchronisation
        """
        try:
            result = self._provider.sync_accounts(user_id)

            logger.info(f"Synchronisation effectuée pour {user_id}: {result}")

            return {
                'success': True,
                **result
            }

        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation: {e}")
            return {
                'success': False,
                'error': 'Erreur lors de la synchronisation',
                'error_code': 'SYNC_ERROR'
            }


# ============================================================
# INSTANCE GLOBALE
# ============================================================

_banking_service: Optional[BankingService] = None


def get_banking_service() -> BankingService:
    """Retourne l'instance globale du service bancaire"""
    global _banking_service
    if _banking_service is None:
        _banking_service = BankingService()
    return _banking_service


def init_banking_service(provider_name: str = None) -> BankingService:
    """Initialise le service bancaire avec un provider spécifique"""
    global _banking_service
    _banking_service = BankingService(provider_name)
    return _banking_service
