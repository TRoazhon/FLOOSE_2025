"""
DataManager - Unified data access layer using SQLAlchemy
Replaces all CSV-based operations with SQL database queries
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from .db import (
    get_db, init_db,
    UserRepository, CategoryRepository, ProjectRepository,
    ExpenseRepository, ProjectHistoryRepository,
    BankAccountRepository, BankTransactionRepository,
    DashboardRepository, WidgetRepository, WidgetLayoutRepository,
    KPIDefinitionRepository,
    AccountType, TransactionType, UserRole
)

logger = logging.getLogger(__name__)


class DataManager:
    """
    Centralized data access manager using SQLAlchemy.
    All operations are transactional and type-safe.
    """

    def __init__(self):
        """Initialize DataManager with database connection"""
        self.db = get_db()
        self._ensure_schema()
        self._ensure_defaults()
        logger.info("DataManager initialized with SQL backend")

    def _ensure_schema(self):
        """Ensure database schema exists"""
        self.db.create_tables()

    def _ensure_defaults(self):
        """Ensure default categories and KPI definitions exist"""
        with self.db.session_scope() as session:
            CategoryRepository(session).ensure_defaults()
            KPIDefinitionRepository(session).ensure_defaults()

    # =========================================================================
    # USER OPERATIONS
    # =========================================================================

    def create_user(self, email: str, name: str, password_hash: str,
                    role: str = 'user') -> Dict[str, Any]:
        """Create a new user"""
        with self.db.session_scope() as session:
            repo = UserRepository(session)
            user_role = UserRole.ADMIN if role == 'admin' else UserRole.USER
            user = repo.create(email, name, password_hash, user_role)
            return self._user_to_dict(user)

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        with self.db.session_scope() as session:
            repo = UserRepository(session)
            user = repo.get_by_email(email)
            return self._user_to_dict(user) if user else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        with self.db.session_scope() as session:
            repo = UserRepository(session)
            user = repo.get_by_id(user_id)
            return self._user_to_dict(user) if user else None

    def update_user(self, user_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Update user fields"""
        with self.db.session_scope() as session:
            repo = UserRepository(session)
            user = repo.update(user_id, **kwargs)
            return self._user_to_dict(user) if user else None

    def update_login_attempts(self, user_id: int, attempts: int, locked_until: datetime = None):
        """Update user login attempts"""
        with self.db.session_scope() as session:
            repo = UserRepository(session)
            repo.update_login_attempts(user_id, attempts, locked_until)

    def record_user_login(self, user_id: int):
        """Record successful login"""
        with self.db.session_scope() as session:
            repo = UserRepository(session)
            repo.record_login(user_id)

    # =========================================================================
    # CATEGORY OPERATIONS
    # =========================================================================

    def load_categories(self, type_filter: str = None) -> List[Dict[str, Any]]:
        """Load all categories, optionally filtered by type"""
        with self.db.session_scope() as session:
            repo = CategoryRepository(session)
            categories = repo.get_all(type_filter)
            return [self._category_to_dict(c) for c in categories]

    def get_category(self, category_id: int) -> Optional[Dict[str, Any]]:
        """Get category by ID"""
        with self.db.session_scope() as session:
            repo = CategoryRepository(session)
            category = repo.get_by_id(category_id)
            return self._category_to_dict(category) if category else None

    def get_category_by_name(self, name: str, category_type: str = None) -> Optional[Dict[str, Any]]:
        """Get category by name"""
        with self.db.session_scope() as session:
            repo = CategoryRepository(session)
            category = repo.get_by_name(name, category_type)
            return self._category_to_dict(category) if category else None

    def save_category(self, name: str, category_type: str, color: str = '#D97757',
                      description: str = None) -> Dict[str, Any]:
        """Create a new category"""
        with self.db.session_scope() as session:
            repo = CategoryRepository(session)
            category = repo.create(name, category_type, color, description)
            return self._category_to_dict(category)

    def update_category(self, category_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Update category fields"""
        with self.db.session_scope() as session:
            repo = CategoryRepository(session)
            category = repo.update(category_id, **kwargs)
            return self._category_to_dict(category) if category else None

    def delete_category(self, category_id: int) -> bool:
        """Delete a category"""
        with self.db.session_scope() as session:
            repo = CategoryRepository(session)
            return repo.delete(category_id)

    # =========================================================================
    # PROJECT OPERATIONS
    # =========================================================================

    def save_projet(self, nom: str, budget_alloue: float, categorie_id: int = None,
                    user_id: int = 1, description: str = None) -> Dict[str, Any]:
        """Create a new project"""
        with self.db.session_scope() as session:
            repo = ProjectRepository(session)
            history_repo = ProjectHistoryRepository(session)

            project = repo.create(user_id, nom, budget_alloue, categorie_id, description)

            # Record creation in history
            history_repo.create(
                project_id=project.id,
                action='creation',
                description=f"Création du projet avec budget de {budget_alloue}€",
                budget_allocated=budget_alloue,
                budget_spent=0,
                expense_count=0
            )

            return self._project_to_dict(project)

    def load_projets(self, user_id: int = None) -> List[Dict[str, Any]]:
        """Load all projects with their expenses"""
        with self.db.session_scope() as session:
            repo = ProjectRepository(session)
            projects = repo.get_all(user_id)
            return [self._project_to_dict(p) for p in projects]

    def get_projet(self, projet_id: int) -> Optional[Dict[str, Any]]:
        """Get project by ID with expenses"""
        with self.db.session_scope() as session:
            repo = ProjectRepository(session)
            project = repo.get_by_id(projet_id, with_relations=True)
            return self._project_to_dict(project) if project else None

    def update_projet(self, projet_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Update project fields"""
        with self.db.session_scope() as session:
            repo = ProjectRepository(session)

            # Map legacy field names
            if 'nom' in kwargs:
                kwargs['name'] = kwargs.pop('nom')
            if 'budget_alloue' in kwargs:
                kwargs['budget_allocated'] = kwargs.pop('budget_alloue')
            if 'categorie_id' in kwargs:
                kwargs['category_id'] = kwargs.pop('categorie_id')

            project = repo.update(projet_id, **kwargs)
            return self._project_to_dict(project) if project else None

    def update_projet_budget_depense(self, projet_id: int, montant: float):
        """Update project's spent budget"""
        with self.db.session_scope() as session:
            repo = ProjectRepository(session)
            repo.update_budget_spent(projet_id, montant)

    def delete_projet(self, projet_id: int) -> bool:
        """Delete a project and its expenses"""
        with self.db.session_scope() as session:
            repo = ProjectRepository(session)
            return repo.delete(projet_id)

    def get_statistiques_projets(self, user_id: int = None) -> Dict[str, Any]:
        """Get aggregate project statistics"""
        with self.db.session_scope() as session:
            repo = ProjectRepository(session)
            stats = repo.get_statistics(user_id)
            return {
                'nombre_projets': stats['project_count'],
                'budget_total': stats['total_budget'],
                'total_depense': stats['total_spent'],
                'total_restant': stats['total_remaining'],
                'budget_moyen': stats['average_budget'],
                'pourcentage_utilise': stats['utilization_percentage'],
                'depense_moyenne': stats['total_spent'] / stats['project_count'] if stats['project_count'] > 0 else 0
            }

    # =========================================================================
    # EXPENSE OPERATIONS
    # =========================================================================

    def save_depense(self, projet_id: int, montant: float, description: str = None,
                     categorie_id: int = None) -> Dict[str, Any]:
        """Create a new expense"""
        with self.db.session_scope() as session:
            expense_repo = ExpenseRepository(session)
            project_repo = ProjectRepository(session)
            history_repo = ProjectHistoryRepository(session)

            # Create expense
            expense = expense_repo.create(projet_id, montant, description, categorie_id)

            # Update project budget_spent
            project_repo.recalculate_budget_spent(projet_id)

            # Get updated project for history
            project = project_repo.get_by_id(projet_id, with_relations=True)

            # Record in history
            history_repo.create(
                project_id=projet_id,
                action='expense_added',
                description=f"Dépense ajoutée: {montant}€ - {description or 'Sans description'}",
                budget_allocated=project.budget_allocated,
                budget_spent=project.budget_spent,
                expense_count=len(project.expenses)
            )

            return self._expense_to_dict(expense)

    def load_depenses(self, projet_id: int = None, user_id: int = None) -> List[Dict[str, Any]]:
        """Load expenses, optionally filtered by project"""
        with self.db.session_scope() as session:
            repo = ExpenseRepository(session)
            if projet_id:
                expenses = repo.get_by_project(projet_id)
            else:
                expenses = repo.get_all(user_id)
            return [self._expense_to_dict(e) for e in expenses]

    def get_depense(self, depense_id: int) -> Optional[Dict[str, Any]]:
        """Get expense by ID"""
        with self.db.session_scope() as session:
            repo = ExpenseRepository(session)
            expense = repo.get_by_id(depense_id)
            return self._expense_to_dict(expense) if expense else None

    def update_depense(self, depense_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Update expense fields"""
        with self.db.session_scope() as session:
            expense_repo = ExpenseRepository(session)
            project_repo = ProjectRepository(session)

            # Map legacy field names
            if 'montant' in kwargs:
                kwargs['amount'] = kwargs.pop('montant')
            if 'categorie_id' in kwargs:
                kwargs['category_id'] = kwargs.pop('categorie_id')

            expense = expense_repo.update(depense_id, **kwargs)
            if expense:
                # Recalculate project budget
                project_repo.recalculate_budget_spent(expense.project_id)

            return self._expense_to_dict(expense) if expense else None

    def delete_depense(self, depense_id: int) -> bool:
        """Delete an expense"""
        with self.db.session_scope() as session:
            expense_repo = ExpenseRepository(session)
            project_repo = ProjectRepository(session)

            expense = expense_repo.get_by_id(depense_id)
            if expense:
                project_id = expense.project_id
                expense_repo.delete(depense_id)
                project_repo.recalculate_budget_spent(project_id)
                return True
            return False

    # =========================================================================
    # PROJECT HISTORY OPERATIONS
    # =========================================================================

    def save_historique(self, projet_id: int, action: str, description: str = None,
                        budget_alloue: float = None, budget_depense: float = None,
                        nombre_depenses: int = None) -> Dict[str, Any]:
        """Record project history entry"""
        with self.db.session_scope() as session:
            repo = ProjectHistoryRepository(session)
            history = repo.create(
                project_id=projet_id,
                action=action,
                description=description,
                budget_allocated=budget_alloue,
                budget_spent=budget_depense,
                expense_count=nombre_depenses
            )
            return self._history_to_dict(history)

    def load_historique(self, projet_id: int = None, limit: int = None) -> List[Dict[str, Any]]:
        """Load project history"""
        with self.db.session_scope() as session:
            repo = ProjectHistoryRepository(session)
            if projet_id:
                history = repo.get_by_project(projet_id, limit)
            else:
                history = repo.get_all(limit)
            return [self._history_to_dict(h) for h in history]

    # =========================================================================
    # BANK ACCOUNT OPERATIONS
    # =========================================================================

    def save_compte(self, nom: str, banque: str = None, solde: float = 0,
                    type_compte: str = 'courant', user_id: int = 1) -> Dict[str, Any]:
        """Create a new bank account"""
        with self.db.session_scope() as session:
            repo = BankAccountRepository(session)
            account_type = AccountType(type_compte.lower()) if type_compte else AccountType.COURANT
            account = repo.create(user_id, nom, banque, account_type, solde)
            return self._account_to_dict(account)

    def load_comptes(self, user_id: int = None) -> List[Dict[str, Any]]:
        """Load all bank accounts"""
        with self.db.session_scope() as session:
            repo = BankAccountRepository(session)
            accounts = repo.get_all(user_id)
            return [self._account_to_dict(a) for a in accounts]

    def get_compte(self, compte_id: int) -> Optional[Dict[str, Any]]:
        """Get bank account by ID"""
        with self.db.session_scope() as session:
            repo = BankAccountRepository(session)
            account = repo.get_by_id(compte_id, with_transactions=True)
            return self._account_to_dict(account) if account else None

    def update_compte_solde(self, compte_id: int, nouveau_solde: float):
        """Update account balance"""
        with self.db.session_scope() as session:
            repo = BankAccountRepository(session)
            repo.update_balance(compte_id, nouveau_solde)

    def delete_compte(self, compte_id: int) -> bool:
        """Delete a bank account"""
        with self.db.session_scope() as session:
            repo = BankAccountRepository(session)
            return repo.delete(compte_id)

    def get_total_solde(self, user_id: int = None) -> float:
        """Get total balance across all accounts"""
        with self.db.session_scope() as session:
            repo = BankAccountRepository(session)
            return repo.get_total_balance(user_id)

    # =========================================================================
    # BANK TRANSACTION OPERATIONS
    # =========================================================================

    def save_transaction(self, compte_id: int, type_transaction: str, montant: float,
                         description: str = None, solde_apres: float = None) -> Dict[str, Any]:
        """Create a bank transaction"""
        with self.db.session_scope() as session:
            repo = BankTransactionRepository(session)
            account_repo = BankAccountRepository(session)

            # Get current balance if not provided
            if solde_apres is None:
                account = account_repo.get_by_id(compte_id)
                if type_transaction.lower() == 'credit':
                    solde_apres = account.balance + montant
                else:
                    solde_apres = account.balance - montant

            trans_type = TransactionType.CREDIT if type_transaction.lower() == 'credit' else TransactionType.DEBIT
            transaction = repo.create(compte_id, trans_type, montant, solde_apres, description)

            # Update account balance
            account_repo.update_balance(compte_id, solde_apres)

            return self._transaction_to_dict(transaction)

    def load_transactions(self, compte_id: int = None, limit: int = None) -> List[Dict[str, Any]]:
        """Load bank transactions"""
        with self.db.session_scope() as session:
            repo = BankTransactionRepository(session)
            if compte_id:
                transactions = repo.get_by_account(compte_id, limit)
            else:
                transactions = []  # No global transaction list without account
            return [self._transaction_to_dict(t) for t in transactions]

    # =========================================================================
    # DASHBOARD OPERATIONS
    # =========================================================================

    def get_or_create_default_dashboard(self, user_id: int) -> Dict[str, Any]:
        """Get or create default dashboard for user"""
        with self.db.session_scope() as session:
            repo = DashboardRepository(session)
            dashboard = repo.get_or_create_default(user_id)
            return self._dashboard_to_dict(dashboard)

    def get_dashboard(self, dashboard_id: int) -> Optional[Dict[str, Any]]:
        """Get dashboard by ID with widgets"""
        with self.db.session_scope() as session:
            repo = DashboardRepository(session)
            dashboard = repo.get_by_id(dashboard_id, with_widgets=True)
            return self._dashboard_to_dict(dashboard, include_widgets=True) if dashboard else None

    def save_widget(self, dashboard_id: int, widget_type: str, kpi_config: dict = None,
                    ai_prompt: str = None, ai_response: str = None,
                    x: int = 0, y: int = 0, width: int = 4, height: int = 3) -> Dict[str, Any]:
        """Create a new widget with layout"""
        with self.db.session_scope() as session:
            widget_repo = WidgetRepository(session)
            layout_repo = WidgetLayoutRepository(session)

            widget = widget_repo.create(dashboard_id, widget_type, kpi_config, ai_prompt, ai_response)
            layout_repo.create_or_update(widget.id, x, y, width, height)

            return self._widget_to_dict(widget)

    def update_widget_layout(self, widget_id: int, x: int, y: int, width: int, height: int):
        """Update widget position and size"""
        with self.db.session_scope() as session:
            repo = WidgetLayoutRepository(session)
            repo.create_or_update(widget_id, x, y, width, height)

    def delete_widget(self, widget_id: int) -> bool:
        """Delete a widget"""
        with self.db.session_scope() as session:
            repo = WidgetRepository(session)
            return repo.delete(widget_id)

    def batch_update_layouts(self, layouts: List[Dict[str, Any]]):
        """Update multiple widget layouts at once"""
        with self.db.session_scope() as session:
            repo = WidgetLayoutRepository(session)
            repo.batch_update(layouts)

    # =========================================================================
    # DATABASE STATISTICS
    # =========================================================================

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return self.db.get_stats()

    def health_check(self) -> bool:
        """Check database health"""
        return self.db.health_check()

    # =========================================================================
    # CONVERSION HELPERS
    # =========================================================================

    def _user_to_dict(self, user) -> Dict[str, Any]:
        if not user:
            return None
        return {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'password_hash': user.password_hash,
            'avatar': user.avatar,
            'role': user.role.value if user.role else 'user',
            'is_active': user.is_active,
            'login_attempts': user.login_attempts,
            'locked_until': user.locked_until.isoformat() if user.locked_until else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'created_at': user.created_at.isoformat() if user.created_at else None
        }

    def _category_to_dict(self, category) -> Dict[str, Any]:
        if not category:
            return None
        return {
            'id': category.id,
            'nom': category.name,
            'couleur': category.color,
            'type': category.category_type,
            'description': category.description,
            'date_creation': category.created_at.isoformat() if category.created_at else None
        }

    def _project_to_dict(self, project) -> Dict[str, Any]:
        if not project:
            return None
        return {
            'id': project.id,
            'nom': project.name,
            'budget_alloue': project.budget_allocated,
            'budget_depense': project.budget_spent,
            'budget_restant': project.budget_remaining,
            'categorie_id': project.category_id,
            'categorie': project.category.name if project.category else None,
            'categorie_couleur': project.category.color if project.category else '#D97757',
            'description': project.description,
            'is_active': project.is_active,
            'depenses': [self._expense_to_dict(e) for e in project.expenses] if project.expenses else [],
            'date_creation': project.created_at.isoformat() if project.created_at else None
        }

    def _expense_to_dict(self, expense) -> Dict[str, Any]:
        if not expense:
            return None
        return {
            'id': expense.id,
            'projet_id': expense.project_id,
            'montant': expense.amount,
            'description': expense.description,
            'categorie_id': expense.category_id,
            'date': expense.expense_date.isoformat() if expense.expense_date else None,
            'date_creation': expense.created_at.isoformat() if expense.created_at else None
        }

    def _history_to_dict(self, history) -> Dict[str, Any]:
        if not history:
            return None
        return {
            'id': history.id,
            'projet_id': history.project_id,
            'action': history.action,
            'budget_alloue': history.budget_allocated_snapshot,
            'budget_depense': history.budget_spent_snapshot,
            'nombre_depenses': history.expense_count_snapshot,
            'description': history.description,
            'date_snapshot': history.created_at.isoformat() if history.created_at else None
        }

    def _account_to_dict(self, account) -> Dict[str, Any]:
        if not account:
            return None
        return {
            'id': account.id,
            'nom': account.name,
            'banque': account.bank_name,
            'solde': account.balance,
            'type_compte': account.account_type.value if account.account_type else 'courant',
            'devise': account.currency,
            'is_active': account.is_active,
            'transactions': [self._transaction_to_dict(t) for t in account.transactions] if hasattr(account, 'transactions') and account.transactions else [],
            'date_creation': account.created_at.isoformat() if account.created_at else None
        }

    def _transaction_to_dict(self, transaction) -> Dict[str, Any]:
        if not transaction:
            return None
        return {
            'id': transaction.id,
            'compte_id': transaction.account_id,
            'type': transaction.transaction_type.value if transaction.transaction_type else 'debit',
            'montant': transaction.amount,
            'description': transaction.description,
            'solde_apres': transaction.balance_after,
            'date': transaction.transaction_date.isoformat() if transaction.transaction_date else None
        }

    def _dashboard_to_dict(self, dashboard, include_widgets: bool = False) -> Dict[str, Any]:
        if not dashboard:
            return None
        result = {
            'id': dashboard.id,
            'user_id': dashboard.user_id,
            'name': dashboard.name,
            'is_default': dashboard.is_default,
            'settings': dashboard.settings,
            'created_at': dashboard.created_at.isoformat() if dashboard.created_at else None
        }
        if include_widgets and dashboard.widgets:
            result['widgets'] = [self._widget_to_dict(w) for w in dashboard.widgets]
        return result

    def _widget_to_dict(self, widget) -> Dict[str, Any]:
        if not widget:
            return None
        layout = widget.layout if hasattr(widget, 'layout') else None
        return {
            'id': widget.id,
            'dashboard_id': widget.dashboard_id,
            'widget_type': widget.widget_type,
            'kpi_config': widget.kpi_config,
            'ai_prompt': widget.ai_prompt,
            'layout': {
                'x': layout.x if layout else 0,
                'y': layout.y if layout else 0,
                'width': layout.width if layout else 4,
                'height': layout.height if layout else 3
            },
            'created_at': widget.created_at.isoformat() if widget.created_at else None
        }
