"""
SQLAlchemy Models for FLOOSE
Complete relational schema for budget management system
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey,
    Index, UniqueConstraint, CheckConstraint, Enum as SQLEnum, JSON
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
import enum

Base = declarative_base()


# ============================================================================
# ENUMS
# ============================================================================

class UserRole(enum.Enum):
    USER = "user"
    ADMIN = "admin"


class AccountType(enum.Enum):
    COURANT = "courant"
    EPARGNE = "epargne"
    TITRE = "titre"
    CREDIT = "credit"


class TransactionType(enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class WidgetVisualization(enum.Enum):
    NUMBER = "number"
    GAUGE = "gauge"
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    TABLE = "table"
    SPARKLINE = "sparkline"


class KPIAggregation(enum.Enum):
    SUM = "sum"
    AVG = "avg"
    COUNT = "count"
    MIN = "min"
    MAX = "max"


# ============================================================================
# USER MANAGEMENT
# ============================================================================

class User(Base):
    """User accounts with authentication data"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    avatar = Column(String(500), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    dashboards = relationship("Dashboard", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    accounts = relationship("BankAccount", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_users_email_active', 'email', 'is_active'),
    )


# ============================================================================
# DASHBOARD & WIDGETS
# ============================================================================

class Dashboard(Base):
    """User dashboards containing widgets"""
    __tablename__ = 'dashboards'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), default='Dashboard Principal', nullable=False)
    is_default = Column(Boolean, default=False)
    settings = Column(JSONB, default={})  # Dashboard-level settings
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="dashboards")
    widgets = relationship("Widget", back_populates="dashboard", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_dashboards_user', 'user_id'),
        Index('idx_dashboards_user_default', 'user_id', 'is_default'),
    )


class Widget(Base):
    """Dashboard widgets with KPI configuration"""
    __tablename__ = 'widgets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    dashboard_id = Column(Integer, ForeignKey('dashboards.id', ondelete='CASCADE'), nullable=False)
    widget_type = Column(String(50), nullable=False)  # 'ai-kpi', 'pie-chart', etc.
    kpi_config = Column(JSONB, nullable=True)  # Full KPI configuration
    ai_prompt = Column(Text, nullable=True)  # Original AI prompt if AI-generated
    ai_response = Column(Text, nullable=True)  # Raw AI response for debugging
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    dashboard = relationship("Dashboard", back_populates="widgets")
    layout = relationship("WidgetLayout", back_populates="widget", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_widgets_dashboard', 'dashboard_id'),
        Index('idx_widgets_type', 'widget_type'),
    )


class WidgetLayout(Base):
    """Widget position and size in dashboard grid"""
    __tablename__ = 'widget_layouts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    widget_id = Column(Integer, ForeignKey('widgets.id', ondelete='CASCADE'), nullable=False, unique=True)
    x = Column(Integer, default=0, nullable=False)
    y = Column(Integer, default=0, nullable=False)
    width = Column(Integer, default=4, nullable=False)
    height = Column(Integer, default=3, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    widget = relationship("Widget", back_populates="layout")

    __table_args__ = (
        CheckConstraint('width > 0', name='check_width_positive'),
        CheckConstraint('height > 0', name='check_height_positive'),
        CheckConstraint('x >= 0', name='check_x_non_negative'),
        CheckConstraint('y >= 0', name='check_y_non_negative'),
    )


class KPIDefinition(Base):
    """Reusable KPI definitions (templates)"""
    __tablename__ = 'kpi_definitions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    metric = Column(String(100), nullable=False)
    aggregation = Column(SQLEnum(KPIAggregation), default=KPIAggregation.SUM)
    visualization = Column(SQLEnum(WidgetVisualization), default=WidgetVisualization.NUMBER)
    default_config = Column(JSONB, default={})
    is_system = Column(Boolean, default=False)  # System-defined vs user-defined
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_kpi_definitions_metric', 'metric'),
    )


# ============================================================================
# CATEGORIES
# ============================================================================

class Category(Base):
    """Categories for projects and expenses"""
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    color = Column(String(7), default='#D97757')  # Hex color
    category_type = Column(String(20), nullable=False)  # 'projet' or 'depense'
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    projects = relationship("Project", back_populates="category")
    expenses = relationship("Expense", back_populates="category")

    __table_args__ = (
        Index('idx_categories_type', 'category_type'),
        UniqueConstraint('name', 'category_type', name='uq_category_name_type'),
    )


# ============================================================================
# PROJECTS & EXPENSES
# ============================================================================

class Project(Base):
    """Budget projects"""
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    name = Column(String(255), nullable=False)
    budget_allocated = Column(Float, default=0, nullable=False)
    budget_spent = Column(Float, default=0, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="projects")
    category = relationship("Category", back_populates="projects")
    expenses = relationship("Expense", back_populates="project", cascade="all, delete-orphan")
    history = relationship("ProjectHistory", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_projects_user', 'user_id'),
        Index('idx_projects_category', 'category_id'),
        Index('idx_projects_created', 'created_at'),
        CheckConstraint('budget_allocated >= 0', name='check_budget_allocated_positive'),
        CheckConstraint('budget_spent >= 0', name='check_budget_spent_positive'),
    )

    @property
    def budget_remaining(self) -> float:
        return self.budget_allocated - self.budget_spent

    @property
    def utilization_percentage(self) -> float:
        if self.budget_allocated == 0:
            return 0
        return (self.budget_spent / self.budget_allocated) * 100


class Expense(Base):
    """Individual expenses linked to projects"""
    __tablename__ = 'expenses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    expense_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="expenses")
    category = relationship("Category", back_populates="expenses")

    __table_args__ = (
        Index('idx_expenses_project', 'project_id'),
        Index('idx_expenses_date', 'expense_date'),
        Index('idx_expenses_category', 'category_id'),
        Index('idx_expenses_project_date', 'project_id', 'expense_date'),
        CheckConstraint('amount > 0', name='check_expense_amount_positive'),
    )


class ProjectHistory(Base):
    """Audit trail for project changes"""
    __tablename__ = 'project_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    action = Column(String(50), nullable=False)  # 'creation', 'expense_added', 'updated', etc.
    budget_allocated_snapshot = Column(Float, nullable=True)
    budget_spent_snapshot = Column(Float, nullable=True)
    expense_count_snapshot = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="history")

    __table_args__ = (
        Index('idx_project_history_project', 'project_id'),
        Index('idx_project_history_date', 'created_at'),
        Index('idx_project_history_action', 'action'),
    )


# ============================================================================
# BANK ACCOUNTS & TRANSACTIONS
# ============================================================================

class BankAccount(Base):
    """Internal bank account tracking"""
    __tablename__ = 'bank_accounts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    bank_name = Column(String(255), nullable=True)
    account_type = Column(SQLEnum(AccountType), default=AccountType.COURANT)
    balance = Column(Float, default=0, nullable=False)
    currency = Column(String(3), default='EUR')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="accounts")
    transactions = relationship("BankTransaction", back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_bank_accounts_user', 'user_id'),
        Index('idx_bank_accounts_type', 'account_type'),
    )


class BankTransaction(Base):
    """Transaction history for bank accounts"""
    __tablename__ = 'bank_transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('bank_accounts.id', ondelete='CASCADE'), nullable=False)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    balance_after = Column(Float, nullable=False)
    transaction_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    account = relationship("BankAccount", back_populates="transactions")

    __table_args__ = (
        Index('idx_bank_transactions_account', 'account_id'),
        Index('idx_bank_transactions_date', 'transaction_date'),
        Index('idx_bank_transactions_account_date', 'account_id', 'transaction_date'),
        CheckConstraint('amount > 0', name='check_transaction_amount_positive'),
    )


# ============================================================================
# EXTERNAL BANKING (Open Banking)
# ============================================================================

class BankConnection(Base):
    """Open Banking connections"""
    __tablename__ = 'bank_connections'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    bank_id = Column(String(100), nullable=False)
    status = Column(String(20), default='pending')  # connected, disconnected, pending, error, expired
    consent_id = Column(String(255), nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    connected_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    last_sync = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_bank_connections_user', 'user_id'),
        Index('idx_bank_connections_status', 'status'),
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_all_tables(engine):
    """Create all tables in the database"""
    Base.metadata.create_all(engine)


def drop_all_tables(engine):
    """Drop all tables (use with caution!)"""
    Base.metadata.drop_all(engine)
