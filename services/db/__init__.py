"""
Database Module for FLOOSE
SQLAlchemy-based persistence layer
"""

from .connection import DatabaseManager, get_db, init_db
from .models import (
    Base,
    User, UserRole,
    Dashboard, Widget, WidgetLayout, KPIDefinition,
    Category, Project, Expense, ProjectHistory,
    BankAccount, BankTransaction, AccountType, TransactionType,
    WidgetVisualization, KPIAggregation
)
from .repositories import (
    BaseRepository,
    UserRepository,
    CategoryRepository,
    ProjectRepository,
    ExpenseRepository,
    ProjectHistoryRepository,
    BankAccountRepository,
    BankTransactionRepository,
    DashboardRepository,
    WidgetRepository,
    WidgetLayoutRepository,
    KPIDefinitionRepository
)

__all__ = [
    # Connection
    'DatabaseManager', 'get_db', 'init_db',
    # Base
    'Base',
    # Models
    'User', 'UserRole',
    'Dashboard', 'Widget', 'WidgetLayout', 'KPIDefinition',
    'Category', 'Project', 'Expense', 'ProjectHistory',
    'BankAccount', 'BankTransaction', 'AccountType', 'TransactionType',
    'WidgetVisualization', 'KPIAggregation',
    # Repositories
    'BaseRepository',
    'UserRepository',
    'CategoryRepository',
    'ProjectRepository',
    'ExpenseRepository',
    'ProjectHistoryRepository',
    'BankAccountRepository',
    'BankTransactionRepository',
    'DashboardRepository',
    'WidgetRepository',
    'WidgetLayoutRepository',
    'KPIDefinitionRepository',
]
