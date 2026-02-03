"""
Couche d'abstraction pour les providers bancaires
Architecture prête pour Open Banking / DSP2
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import random
import logging

logger = logging.getLogger(__name__)


# ============================================================
# ENUMS
# ============================================================

class AccountType(Enum):
    CHECKING = "checking"      # Compte courant
    SAVINGS = "savings"        # Compte épargne
    INVESTMENT = "investment"  # Compte titre
    LOAN = "loan"              # Crédit


class TransactionCategory(Enum):
    INCOME = "income"
    FOOD = "food"
    TRANSPORT = "transport"
    HOUSING = "housing"
    HEALTH = "health"
    LEISURE = "leisure"
    SHOPPING = "shopping"
    BILLS = "bills"
    TRANSFER = "transfer"
    OTHER = "other"


class ConnectionStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    PENDING = "pending"
    ERROR = "error"
    EXPIRED = "expired"


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class Bank:
    """Représente une banque disponible pour connexion"""
    id: str
    name: str
    logo_url: str
    country: str = "FR"
    supported: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BankAccount:
    """Représente un compte bancaire"""
    id: str
    user_id: str
    bank_id: str
    iban: str
    name: str
    balance: float
    currency: str = "EUR"
    account_type: AccountType = AccountType.CHECKING
    last_sync_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['account_type'] = self.account_type.value
        data['last_sync_at'] = self.last_sync_at.isoformat() if self.last_sync_at else None
        return data


@dataclass
class Transaction:
    """Représente une transaction bancaire"""
    id: str
    account_id: str
    amount: float
    label: str
    date: datetime
    category: TransactionCategory = TransactionCategory.OTHER
    merchant: Optional[str] = None
    reference: Optional[str] = None
    pending: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['category'] = self.category.value
        data['date'] = self.date.isoformat()
        return data


@dataclass
class BankConnection:
    """Représente une connexion à une banque pour un utilisateur"""
    id: str
    user_id: str
    bank_id: str
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    connected_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['status'] = self.status.value
        data['connected_at'] = self.connected_at.isoformat() if self.connected_at else None
        data['expires_at'] = self.expires_at.isoformat() if self.expires_at else None
        return data


# ============================================================
# ABSTRACT BANK PROVIDER
# ============================================================

class BankAPIProvider(ABC):
    """
    Interface abstraite pour les providers bancaires
    Toutes les implémentations (Mock, Crédit Agricole, Budget Insight, etc.)
    doivent implémenter cette interface
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nom du provider"""
        pass

    @abstractmethod
    def get_available_banks(self) -> List[Bank]:
        """
        Retourne la liste des banques disponibles via ce provider

        Returns:
            List[Bank]: Liste des banques supportées
        """
        pass

    @abstractmethod
    def connect_bank(self, user_id: str, bank_id: str, credentials: Dict[str, Any] = None) -> BankConnection:
        """
        Initie une connexion à une banque pour un utilisateur

        Args:
            user_id: Identifiant de l'utilisateur
            bank_id: Identifiant de la banque
            credentials: Identifiants optionnels (pour OAuth, peut être None)

        Returns:
            BankConnection: Objet de connexion avec statut et URL de redirection si OAuth
        """
        pass

    @abstractmethod
    def disconnect_bank(self, user_id: str, bank_id: str) -> bool:
        """
        Déconnecte un utilisateur d'une banque

        Args:
            user_id: Identifiant de l'utilisateur
            bank_id: Identifiant de la banque

        Returns:
            bool: True si déconnexion réussie
        """
        pass

    @abstractmethod
    def get_connection_status(self, user_id: str, bank_id: str) -> BankConnection:
        """
        Récupère le statut de connexion d'un utilisateur à une banque

        Args:
            user_id: Identifiant de l'utilisateur
            bank_id: Identifiant de la banque

        Returns:
            BankConnection: Statut de la connexion
        """
        pass

    @abstractmethod
    def fetch_accounts(self, user_id: str, bank_id: str = None) -> List[BankAccount]:
        """
        Récupère les comptes bancaires d'un utilisateur

        Args:
            user_id: Identifiant de l'utilisateur
            bank_id: Optionnel - filtrer par banque

        Returns:
            List[BankAccount]: Liste des comptes
        """
        pass

    @abstractmethod
    def fetch_transactions(self, user_id: str, account_id: str,
                          date_from: datetime = None,
                          date_to: datetime = None) -> List[Transaction]:
        """
        Récupère les transactions d'un compte

        Args:
            user_id: Identifiant de l'utilisateur
            account_id: Identifiant du compte
            date_from: Date de début (optionnel)
            date_to: Date de fin (optionnel)

        Returns:
            List[Transaction]: Liste des transactions
        """
        pass

    @abstractmethod
    def sync_accounts(self, user_id: str) -> Dict[str, Any]:
        """
        Synchronise tous les comptes d'un utilisateur

        Args:
            user_id: Identifiant de l'utilisateur

        Returns:
            dict: Résultat de la synchronisation
        """
        pass


# ============================================================
# MOCK BANK PROVIDER
# ============================================================

class MockBankAPIProvider(BankAPIProvider):
    """
    Implémentation mock pour le développement et les tests
    Utilise des données simulées réalistes
    """

    def __init__(self):
        self._connections: Dict[str, Dict[str, BankConnection]] = {}
        self._accounts: Dict[str, List[BankAccount]] = {}
        self._transactions: Dict[str, List[Transaction]] = {}

        # Banques disponibles (mock)
        self._banks = [
            Bank(
                id="ca",
                name="Crédit Agricole",
                logo_url="/static/img/banks/credit-agricole.png",
                country="FR"
            ),
            Bank(
                id="bnp",
                name="BNP Paribas",
                logo_url="/static/img/banks/bnp.png",
                country="FR"
            ),
            Bank(
                id="sg",
                name="Société Générale",
                logo_url="/static/img/banks/sg.png",
                country="FR"
            ),
            Bank(
                id="lcl",
                name="LCL",
                logo_url="/static/img/banks/lcl.png",
                country="FR"
            ),
            Bank(
                id="boursorama",
                name="Boursorama",
                logo_url="/static/img/banks/boursorama.png",
                country="FR"
            ),
            Bank(
                id="fortuneo",
                name="Fortuneo",
                logo_url="/static/img/banks/fortuneo.png",
                country="FR"
            ),
            Bank(
                id="revolut",
                name="Revolut",
                logo_url="/static/img/banks/revolut.png",
                country="EU"
            ),
            Bank(
                id="n26",
                name="N26",
                logo_url="/static/img/banks/n26.png",
                country="EU"
            ),
        ]

        logger.info("MockBankAPIProvider initialisé")

    @property
    def provider_name(self) -> str:
        return "Mock Provider"

    def get_available_banks(self) -> List[Bank]:
        return self._banks

    def connect_bank(self, user_id: str, bank_id: str, credentials: Dict[str, Any] = None) -> BankConnection:
        """Simule une connexion à une banque"""

        # Vérifier que la banque existe
        bank = next((b for b in self._banks if b.id == bank_id), None)
        if not bank:
            raise ValueError(f"Banque inconnue: {bank_id}")

        # Créer la connexion
        connection = BankConnection(
            id=str(uuid.uuid4()),
            user_id=user_id,
            bank_id=bank_id,
            status=ConnectionStatus.CONNECTED,
            connected_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=90)
        )

        # Stocker la connexion
        if user_id not in self._connections:
            self._connections[user_id] = {}
        self._connections[user_id][bank_id] = connection

        # Générer des comptes mock pour cet utilisateur
        self._generate_mock_accounts(user_id, bank_id, bank.name)

        logger.info(f"Connexion mock établie: {user_id} -> {bank.name}")
        return connection

    def disconnect_bank(self, user_id: str, bank_id: str) -> bool:
        if user_id in self._connections and bank_id in self._connections[user_id]:
            self._connections[user_id][bank_id].status = ConnectionStatus.DISCONNECTED

            # Supprimer les comptes associés
            if user_id in self._accounts:
                self._accounts[user_id] = [
                    acc for acc in self._accounts[user_id]
                    if acc.bank_id != bank_id
                ]

            logger.info(f"Déconnexion mock: {user_id} -> {bank_id}")
            return True
        return False

    def get_connection_status(self, user_id: str, bank_id: str) -> BankConnection:
        if user_id in self._connections and bank_id in self._connections[user_id]:
            return self._connections[user_id][bank_id]

        return BankConnection(
            id="",
            user_id=user_id,
            bank_id=bank_id,
            status=ConnectionStatus.DISCONNECTED
        )

    def fetch_accounts(self, user_id: str, bank_id: str = None) -> List[BankAccount]:
        if user_id not in self._accounts:
            return []

        accounts = self._accounts[user_id]

        if bank_id:
            accounts = [acc for acc in accounts if acc.bank_id == bank_id]

        return accounts

    def fetch_transactions(self, user_id: str, account_id: str,
                          date_from: datetime = None,
                          date_to: datetime = None) -> List[Transaction]:

        # Générer des transactions si pas encore fait
        if account_id not in self._transactions:
            self._generate_mock_transactions(account_id)

        transactions = self._transactions.get(account_id, [])

        # Filtrer par date si spécifié
        if date_from:
            transactions = [t for t in transactions if t.date >= date_from]
        if date_to:
            transactions = [t for t in transactions if t.date <= date_to]

        # Trier par date décroissante
        transactions.sort(key=lambda t: t.date, reverse=True)

        return transactions

    def sync_accounts(self, user_id: str) -> Dict[str, Any]:
        """Simule une synchronisation"""
        accounts = self.fetch_accounts(user_id)

        # Mettre à jour last_sync_at
        for account in accounts:
            account.last_sync_at = datetime.now()
            # Légère variation du solde pour simuler l'activité
            account.balance += random.uniform(-50, 100)
            account.balance = round(account.balance, 2)

        return {
            "success": True,
            "accounts_synced": len(accounts),
            "timestamp": datetime.now().isoformat()
        }

    def _generate_mock_accounts(self, user_id: str, bank_id: str, bank_name: str):
        """Génère des comptes mock réalistes"""

        if user_id not in self._accounts:
            self._accounts[user_id] = []

        # Compte courant
        checking = BankAccount(
            id=str(uuid.uuid4()),
            user_id=user_id,
            bank_id=bank_id,
            iban=self._generate_iban(),
            name=f"Compte Courant {bank_name}",
            balance=round(random.uniform(500, 5000), 2),
            currency="EUR",
            account_type=AccountType.CHECKING,
            last_sync_at=datetime.now()
        )
        self._accounts[user_id].append(checking)

        # Compte épargne (50% de chance)
        if random.random() > 0.5:
            savings = BankAccount(
                id=str(uuid.uuid4()),
                user_id=user_id,
                bank_id=bank_id,
                iban=self._generate_iban(),
                name=f"Livret A {bank_name}",
                balance=round(random.uniform(1000, 15000), 2),
                currency="EUR",
                account_type=AccountType.SAVINGS,
                last_sync_at=datetime.now()
            )
            self._accounts[user_id].append(savings)

    def _generate_iban(self) -> str:
        """Génère un IBAN français fictif"""
        bank_code = str(random.randint(10000, 99999))
        branch_code = str(random.randint(10000, 99999))
        account_num = str(random.randint(10000000000, 99999999999))
        return f"FR76{bank_code}{branch_code}{account_num}00"

    def _generate_mock_transactions(self, account_id: str):
        """Génère des transactions mock réalistes sur 3 mois"""

        transactions = []

        # Merchants et catégories réalistes
        merchants = {
            TransactionCategory.FOOD: [
                ("Carrefour", -45.67), ("Leclerc", -78.34), ("Auchan", -56.23),
                ("Lidl", -32.45), ("Monoprix", -28.90), ("Picard", -42.15)
            ],
            TransactionCategory.TRANSPORT: [
                ("SNCF", -67.00), ("RATP", -84.10), ("Total Essence", -65.00),
                ("Uber", -18.50), ("Bolt", -12.30), ("Blablacar", -25.00)
            ],
            TransactionCategory.HOUSING: [
                ("EDF", -85.00), ("Engie", -65.00), ("Veolia Eau", -45.00),
                ("SFR", -35.99), ("Orange", -49.99), ("Free", -19.99)
            ],
            TransactionCategory.LEISURE: [
                ("Netflix", -17.99), ("Spotify", -9.99), ("Amazon Prime", -6.99),
                ("UGC Cinéma", -12.50), ("Fnac", -34.99), ("Steam", -29.99)
            ],
            TransactionCategory.SHOPPING: [
                ("Amazon", -56.78), ("Zara", -89.00), ("H&M", -45.00),
                ("Decathlon", -67.50), ("IKEA", -123.45), ("Darty", -199.00)
            ],
            TransactionCategory.HEALTH: [
                ("Pharmacie", -23.45), ("Docteur Martin", -25.00),
                ("Laboratoire", -15.00), ("Mutuelle", -45.00)
            ],
            TransactionCategory.BILLS: [
                ("Assurance Auto", -65.00), ("Assurance Habitation", -25.00),
                ("Impôts", -150.00), ("Loyer", -850.00)
            ],
            TransactionCategory.INCOME: [
                ("Salaire", 2500.00), ("Virement reçu", 150.00),
                ("Remboursement", 45.00), ("Prime", 500.00)
            ]
        }

        # Générer 3 mois de transactions
        for days_ago in range(90):
            date = datetime.now() - timedelta(days=days_ago)

            # 1-4 transactions par jour
            num_transactions = random.randint(1, 4)

            for _ in range(num_transactions):
                category = random.choice(list(merchants.keys()))
                merchant_data = random.choice(merchants[category])
                merchant_name, base_amount = merchant_data

                # Variation du montant
                amount = base_amount * random.uniform(0.8, 1.2)
                amount = round(amount, 2)

                transaction = Transaction(
                    id=str(uuid.uuid4()),
                    account_id=account_id,
                    amount=amount,
                    label=merchant_name,
                    date=date,
                    category=category,
                    merchant=merchant_name,
                    reference=f"REF{random.randint(100000, 999999)}",
                    pending=(days_ago < 2 and random.random() > 0.7)
                )
                transactions.append(transaction)

        self._transactions[account_id] = transactions
        logger.debug(f"Généré {len(transactions)} transactions mock pour {account_id}")


# ============================================================
# BANK PROVIDER MANAGER
# ============================================================

class BankProviderManager:
    """
    Gestionnaire des providers bancaires
    Permet de basculer facilement entre mock et providers réels
    """

    def __init__(self):
        self._providers: Dict[str, BankAPIProvider] = {}
        self._default_provider: Optional[str] = None

    def register_provider(self, name: str, provider: BankAPIProvider, default: bool = False):
        """Enregistre un provider"""
        self._providers[name] = provider
        if default or self._default_provider is None:
            self._default_provider = name
        logger.info(f"Provider '{name}' enregistré (default: {default})")

    def get_provider(self, name: str = None) -> BankAPIProvider:
        """Récupère un provider par son nom"""
        if name is None:
            name = self._default_provider

        if name not in self._providers:
            raise ValueError(f"Provider inconnu: {name}")

        return self._providers[name]

    def list_providers(self) -> List[str]:
        """Liste les providers disponibles"""
        return list(self._providers.keys())


# ============================================================
# INSTANCE GLOBALE
# ============================================================

_provider_manager: Optional[BankProviderManager] = None


def get_bank_provider_manager() -> BankProviderManager:
    """Retourne l'instance globale du gestionnaire de providers"""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = BankProviderManager()
        # Enregistrer le provider mock par défaut
        _provider_manager.register_provider("mock", MockBankAPIProvider(), default=True)
    return _provider_manager


def get_bank_provider(name: str = None) -> BankAPIProvider:
    """Raccourci pour obtenir un provider"""
    return get_bank_provider_manager().get_provider(name)
