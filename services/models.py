"""
Modèles de données FLOOSE
Centralise toutes les entités de l'application
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid


# ============================================================
# ENUMS
# ============================================================

class AccountType(Enum):
    """Types de comptes bancaires"""
    CHECKING = "checking"      # Compte courant
    SAVINGS = "savings"        # Compte épargne
    INVESTMENT = "investment"  # Compte titre
    LOAN = "loan"              # Crédit


class TransactionCategory(Enum):
    """Catégories de transactions"""
    INCOME = "income"          # Revenus
    FOOD = "food"              # Alimentation
    TRANSPORT = "transport"    # Transport
    HOUSING = "housing"        # Logement
    HEALTH = "health"          # Santé
    LEISURE = "leisure"        # Loisirs
    SHOPPING = "shopping"      # Shopping
    BILLS = "bills"            # Factures
    TRANSFER = "transfer"      # Virements
    OTHER = "other"            # Autre


class ConnectionStatus(Enum):
    """Statuts de connexion bancaire"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    PENDING = "pending"
    ERROR = "error"
    EXPIRED = "expired"


class UserRole(Enum):
    """Rôles utilisateur"""
    USER = "user"
    ADMIN = "admin"


# ============================================================
# USER MODEL
# ============================================================

@dataclass
class User:
    """
    Représente un utilisateur de l'application
    """
    id: str
    email: str
    name: str
    password_hash: str
    avatar: str = "U"
    role: UserRole = UserRole.USER
    is_active: bool = True
    login_attempts: int = 0
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if not self.avatar:
            self.avatar = self.name[:2].upper() if self.name else "U"

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        data = {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'avatar': self.avatar,
            'role': self.role.value,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_sensitive:
            data['password_hash'] = self.password_hash
            data['login_attempts'] = self.login_attempts
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Crée une instance depuis un dictionnaire"""
        role = data.get('role', 'user')
        if isinstance(role, str):
            role = UserRole(role)

        return cls(
            id=data['id'],
            email=data['email'],
            name=data['name'],
            password_hash=data.get('password_hash', ''),
            avatar=data.get('avatar', ''),
            role=role,
            is_active=data.get('is_active', True),
            login_attempts=data.get('login_attempts', 0),
            last_login=datetime.fromisoformat(data['last_login']) if data.get('last_login') else None,
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
        )


# ============================================================
# BANK MODEL
# ============================================================

@dataclass
class Bank:
    """
    Représente une banque disponible pour connexion
    """
    id: str
    name: str
    logo_url: str
    country: str = "FR"
    supported: bool = True
    bic: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Bank':
        return cls(**data)


# ============================================================
# BANK ACCOUNT MODEL
# ============================================================

@dataclass
class BankAccount:
    """
    Représente un compte bancaire lié à un utilisateur
    """
    id: str
    user_id: str
    bank_id: str
    iban: str
    name: str
    balance: float
    currency: str = "EUR"
    account_type: AccountType = AccountType.CHECKING
    last_sync_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    is_active: bool = True

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if isinstance(self.account_type, str):
            self.account_type = AccountType(self.account_type)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'bank_id': self.bank_id,
            'iban': self.iban,
            'name': self.name,
            'balance': self.balance,
            'currency': self.currency,
            'account_type': self.account_type.value,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BankAccount':
        account_type = data.get('account_type', 'checking')
        if isinstance(account_type, str):
            account_type = AccountType(account_type)

        return cls(
            id=data['id'],
            user_id=data['user_id'],
            bank_id=data['bank_id'],
            iban=data['iban'],
            name=data['name'],
            balance=float(data['balance']),
            currency=data.get('currency', 'EUR'),
            account_type=account_type,
            last_sync_at=datetime.fromisoformat(data['last_sync_at']) if data.get('last_sync_at') else None,
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            is_active=data.get('is_active', True)
        )

    @property
    def masked_iban(self) -> str:
        """Retourne l'IBAN masqué pour l'affichage"""
        if len(self.iban) > 8:
            return f"{self.iban[:4]}****{self.iban[-4:]}"
        return "****"


# ============================================================
# TRANSACTION MODEL
# ============================================================

@dataclass
class Transaction:
    """
    Représente une transaction bancaire
    """
    id: str
    account_id: str
    amount: float
    label: str
    date: datetime
    category: TransactionCategory = TransactionCategory.OTHER
    merchant: Optional[str] = None
    reference: Optional[str] = None
    pending: bool = False
    notes: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.category, str):
            self.category = TransactionCategory(self.category)
        if isinstance(self.date, str):
            self.date = datetime.fromisoformat(self.date)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'account_id': self.account_id,
            'amount': self.amount,
            'label': self.label,
            'date': self.date.isoformat(),
            'category': self.category.value,
            'merchant': self.merchant,
            'reference': self.reference,
            'pending': self.pending,
            'notes': self.notes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        category = data.get('category', 'other')
        if isinstance(category, str):
            category = TransactionCategory(category)

        date = data['date']
        if isinstance(date, str):
            date = datetime.fromisoformat(date)

        return cls(
            id=data['id'],
            account_id=data['account_id'],
            amount=float(data['amount']),
            label=data['label'],
            date=date,
            category=category,
            merchant=data.get('merchant'),
            reference=data.get('reference'),
            pending=data.get('pending', False),
            notes=data.get('notes')
        )

    @property
    def is_credit(self) -> bool:
        """Retourne True si c'est un crédit"""
        return self.amount > 0

    @property
    def is_debit(self) -> bool:
        """Retourne True si c'est un débit"""
        return self.amount < 0


# ============================================================
# BANK CONNECTION MODEL
# ============================================================

@dataclass
class BankConnection:
    """
    Représente une connexion entre un utilisateur et une banque
    """
    id: str
    user_id: str
    bank_id: str
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    connected_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_error: Optional[str] = None
    consent_id: Optional[str] = None  # Pour Open Banking

    def __post_init__(self):
        if isinstance(self.status, str):
            self.status = ConnectionStatus(self.status)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'bank_id': self.bank_id,
            'status': self.status.value,
            'connected_at': self.connected_at.isoformat() if self.connected_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_error': self.last_error,
            'consent_id': self.consent_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BankConnection':
        status = data.get('status', 'disconnected')
        if isinstance(status, str):
            status = ConnectionStatus(status)

        return cls(
            id=data['id'],
            user_id=data['user_id'],
            bank_id=data['bank_id'],
            status=status,
            connected_at=datetime.fromisoformat(data['connected_at']) if data.get('connected_at') else None,
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
            last_error=data.get('last_error'),
            consent_id=data.get('consent_id')
        )

    @property
    def is_valid(self) -> bool:
        """Vérifie si la connexion est valide"""
        if self.status != ConnectionStatus.CONNECTED:
            return False
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def generate_id() -> str:
    """Génère un identifiant unique"""
    return str(uuid.uuid4())


def get_category_label(category: TransactionCategory) -> str:
    """Retourne le label français d'une catégorie"""
    labels = {
        TransactionCategory.INCOME: "Revenus",
        TransactionCategory.FOOD: "Alimentation",
        TransactionCategory.TRANSPORT: "Transport",
        TransactionCategory.HOUSING: "Logement",
        TransactionCategory.HEALTH: "Santé",
        TransactionCategory.LEISURE: "Loisirs",
        TransactionCategory.SHOPPING: "Shopping",
        TransactionCategory.BILLS: "Factures",
        TransactionCategory.TRANSFER: "Virements",
        TransactionCategory.OTHER: "Autre",
    }
    return labels.get(category, "Autre")


def get_category_color(category: TransactionCategory) -> str:
    """Retourne la couleur associée à une catégorie"""
    colors = {
        TransactionCategory.INCOME: "#22c55e",      # Vert
        TransactionCategory.FOOD: "#f97316",        # Orange
        TransactionCategory.TRANSPORT: "#3b82f6",   # Bleu
        TransactionCategory.HOUSING: "#8b5cf6",     # Violet
        TransactionCategory.HEALTH: "#ef4444",      # Rouge
        TransactionCategory.LEISURE: "#ec4899",     # Rose
        TransactionCategory.SHOPPING: "#eab308",    # Jaune
        TransactionCategory.BILLS: "#6b7280",       # Gris
        TransactionCategory.TRANSFER: "#14b8a6",    # Cyan
        TransactionCategory.OTHER: "#9ca3af",       # Gris clair
    }
    return colors.get(category, "#9ca3af")


def get_account_type_label(account_type: AccountType) -> str:
    """Retourne le label français d'un type de compte"""
    labels = {
        AccountType.CHECKING: "Compte courant",
        AccountType.SAVINGS: "Compte épargne",
        AccountType.INVESTMENT: "Compte titre",
        AccountType.LOAN: "Crédit",
    }
    return labels.get(account_type, "Compte")
