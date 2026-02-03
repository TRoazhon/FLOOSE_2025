"""
Services FLOOSE - Logique métier
"""

from .budget_manager import BudgetManager, CompteBancaire
from .data_manager import DataManager
from .auth_manager import AuthManager, get_auth_manager, require_auth, get_current_user
from .analytics_service import (
    calculate_financial_health,
    get_health_level,
    generate_ai_analysis,
    generate_recommendations,
    generate_analytics_report
)
from .file_lock_manager import FileLockManager, get_lock_manager, file_operation_lock
from .performance_manager import (
    PerformanceManager,
    get_performance_manager,
    performance_monitor
)
from .db import (
    get_db,
    init_db,
    DatabaseManager
)
from .credit_agricole_service import (
    CreditAgricoleService,
    CreditAgricoleError,
    get_credit_agricole_service,
    init_credit_agricole_service
)
from .models import (
    User,
    Bank,
    BankAccount,
    Transaction,
    BankConnection,
    AccountType,
    TransactionCategory,
    ConnectionStatus,
    UserRole,
    generate_id,
    get_category_label,
    get_category_color,
    get_account_type_label
)
from .bank_providers import (
    BankAPIProvider,
    MockBankAPIProvider,
    BankProviderManager,
    get_bank_provider_manager,
    get_bank_provider
)
from .banking_service import (
    BankingService,
    get_banking_service,
    init_banking_service
)

__all__ = [
    # Budget Manager
    'BudgetManager',
    'CompteBancaire',
    'DataManager',
    # Auth
    'AuthManager',
    'get_auth_manager',
    'require_auth',
    'get_current_user',
    # Analytics
    'calculate_financial_health',
    'get_health_level',
    'generate_ai_analysis',
    'generate_recommendations',
    'generate_analytics_report',
    # File & Performance
    'FileLockManager',
    'get_lock_manager',
    'file_operation_lock',
    'PerformanceManager',
    'get_performance_manager',
    'performance_monitor',
    # Database
    'get_db',
    'init_db',
    'DatabaseManager',
    # Credit Agricole
    'CreditAgricoleService',
    'CreditAgricoleError',
    'get_credit_agricole_service',
    'init_credit_agricole_service',
    # Models
    'User',
    'Bank',
    'BankAccount',
    'Transaction',
    'BankConnection',
    'AccountType',
    'TransactionCategory',
    'ConnectionStatus',
    'UserRole',
    'generate_id',
    'get_category_label',
    'get_category_color',
    'get_account_type_label',
    # Bank Providers
    'BankAPIProvider',
    'MockBankAPIProvider',
    'BankProviderManager',
    'get_bank_provider_manager',
    'get_bank_provider',
    # Banking Service
    'BankingService',
    'get_banking_service',
    'init_banking_service',
]
