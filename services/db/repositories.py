"""
Repository Layer for FLOOSE
Data Access Objects (DAO) for all entities
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, and_, or_

from .models import (
    User, UserRole,
    Dashboard, Widget, WidgetLayout, KPIDefinition,
    Category, Project, Expense, ProjectHistory,
    BankAccount, BankTransaction, AccountType, TransactionType
)


# ============================================================================
# BASE REPOSITORY
# ============================================================================

class BaseRepository:
    """Base repository with common CRUD operations"""

    def __init__(self, session: Session):
        self.session = session

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()

    def flush(self):
        self.session.flush()


# ============================================================================
# USER REPOSITORY
# ============================================================================

class UserRepository(BaseRepository):
    """Repository for User operations"""

    def create(self, email: str, name: str, password_hash: str,
               role: UserRole = UserRole.USER) -> User:
        user = User(
            email=email,
            name=name,
            password_hash=password_hash,
            role=role
        )
        self.session.add(user)
        self.session.flush()
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.session.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.session.query(User).filter(User.email == email).first()

    def get_all(self, active_only: bool = True) -> List[User]:
        query = self.session.query(User)
        if active_only:
            query = query.filter(User.is_active == True)
        return query.all()

    def update(self, user_id: int, **kwargs) -> Optional[User]:
        user = self.get_by_id(user_id)
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            user.updated_at = datetime.utcnow()
            self.session.flush()
        return user

    def update_login_attempts(self, user_id: int, attempts: int, locked_until: datetime = None):
        user = self.get_by_id(user_id)
        if user:
            user.login_attempts = attempts
            user.locked_until = locked_until
            self.session.flush()

    def record_login(self, user_id: int):
        user = self.get_by_id(user_id)
        if user:
            user.last_login = datetime.utcnow()
            user.login_attempts = 0
            user.locked_until = None
            self.session.flush()

    def delete(self, user_id: int) -> bool:
        user = self.get_by_id(user_id)
        if user:
            self.session.delete(user)
            return True
        return False


# ============================================================================
# CATEGORY REPOSITORY
# ============================================================================

class CategoryRepository(BaseRepository):
    """Repository for Category operations"""

    def create(self, name: str, category_type: str, color: str = '#D97757',
               description: str = None) -> Category:
        category = Category(
            name=name,
            category_type=category_type,
            color=color,
            description=description
        )
        self.session.add(category)
        self.session.flush()
        return category

    def get_by_id(self, category_id: int) -> Optional[Category]:
        return self.session.query(Category).filter(Category.id == category_id).first()

    def get_all(self, category_type: str = None) -> List[Category]:
        query = self.session.query(Category)
        if category_type:
            query = query.filter(Category.category_type == category_type)
        return query.order_by(Category.name).all()

    def get_by_name(self, name: str, category_type: str = None) -> Optional[Category]:
        query = self.session.query(Category).filter(Category.name == name)
        if category_type:
            query = query.filter(Category.category_type == category_type)
        return query.first()

    def update(self, category_id: int, **kwargs) -> Optional[Category]:
        category = self.get_by_id(category_id)
        if category:
            for key, value in kwargs.items():
                if hasattr(category, key):
                    setattr(category, key, value)
            self.session.flush()
        return category

    def delete(self, category_id: int) -> bool:
        category = self.get_by_id(category_id)
        if category:
            self.session.delete(category)
            return True
        return False

    def ensure_defaults(self):
        """Create default categories if none exist"""
        if self.session.query(Category).count() == 0:
            defaults = [
                ('IT & Tech', 'projet', '#3B82F6'),
                ('Marketing', 'projet', '#22C55E'),
                ('Formation', 'projet', '#F59E0B'),
                ('Infrastructure', 'projet', '#8B5CF6'),
                ('Recherche', 'projet', '#EC4899'),
                ('Autre', 'projet', '#6B7280'),
                ('Matériel', 'depense', '#D97757'),
                ('Logiciel', 'depense', '#3B82F6'),
                ('Services', 'depense', '#22C55E'),
                ('Transport', 'depense', '#F59E0B'),
                ('Restauration', 'depense', '#EF4444'),
            ]
            for name, cat_type, color in defaults:
                self.create(name, cat_type, color)
            self.commit()


# ============================================================================
# PROJECT REPOSITORY
# ============================================================================

class ProjectRepository(BaseRepository):
    """Repository for Project operations"""

    def create(self, user_id: int, name: str, budget_allocated: float,
               category_id: int = None, description: str = None) -> Project:
        project = Project(
            user_id=user_id,
            name=name,
            budget_allocated=budget_allocated,
            category_id=category_id,
            description=description
        )
        self.session.add(project)
        self.session.flush()
        return project

    def get_by_id(self, project_id: int, with_relations: bool = False) -> Optional[Project]:
        query = self.session.query(Project)
        if with_relations:
            query = query.options(
                joinedload(Project.category),
                joinedload(Project.expenses)
            )
        return query.filter(Project.id == project_id).first()

    def get_all(self, user_id: int = None, active_only: bool = True) -> List[Project]:
        query = self.session.query(Project).options(
            joinedload(Project.category),
            joinedload(Project.expenses)
        )
        if user_id:
            query = query.filter(Project.user_id == user_id)
        if active_only:
            query = query.filter(Project.is_active == True)
        return query.order_by(desc(Project.created_at)).all()

    def update(self, project_id: int, **kwargs) -> Optional[Project]:
        project = self.get_by_id(project_id)
        if project:
            for key, value in kwargs.items():
                if hasattr(project, key):
                    setattr(project, key, value)
            project.updated_at = datetime.utcnow()
            self.session.flush()
        return project

    def update_budget_spent(self, project_id: int, amount: float):
        project = self.get_by_id(project_id)
        if project:
            project.budget_spent = amount
            project.updated_at = datetime.utcnow()
            self.session.flush()

    def recalculate_budget_spent(self, project_id: int):
        """Recalculate budget_spent from expenses"""
        total = self.session.query(func.sum(Expense.amount))\
            .filter(Expense.project_id == project_id).scalar() or 0
        self.update_budget_spent(project_id, total)

    def delete(self, project_id: int) -> bool:
        project = self.get_by_id(project_id)
        if project:
            self.session.delete(project)
            return True
        return False

    def get_statistics(self, user_id: int = None) -> Dict[str, Any]:
        """Get aggregate statistics for projects"""
        query = self.session.query(Project)
        if user_id:
            query = query.filter(Project.user_id == user_id)

        projects = query.filter(Project.is_active == True).all()

        total_budget = sum(p.budget_allocated for p in projects)
        total_spent = sum(p.budget_spent for p in projects)
        total_remaining = total_budget - total_spent

        return {
            'project_count': len(projects),
            'total_budget': total_budget,
            'total_spent': total_spent,
            'total_remaining': total_remaining,
            'average_budget': total_budget / len(projects) if projects else 0,
            'utilization_percentage': (total_spent / total_budget * 100) if total_budget > 0 else 0
        }


# ============================================================================
# EXPENSE REPOSITORY
# ============================================================================

class ExpenseRepository(BaseRepository):
    """Repository for Expense operations"""

    def create(self, project_id: int, amount: float, description: str = None,
               category_id: int = None, expense_date: datetime = None) -> Expense:
        expense = Expense(
            project_id=project_id,
            amount=amount,
            description=description,
            category_id=category_id,
            expense_date=expense_date or datetime.utcnow()
        )
        self.session.add(expense)
        self.session.flush()
        return expense

    def get_by_id(self, expense_id: int) -> Optional[Expense]:
        return self.session.query(Expense).filter(Expense.id == expense_id).first()

    def get_by_project(self, project_id: int) -> List[Expense]:
        return self.session.query(Expense)\
            .filter(Expense.project_id == project_id)\
            .order_by(desc(Expense.expense_date)).all()

    def get_all(self, user_id: int = None, limit: int = None) -> List[Expense]:
        query = self.session.query(Expense).join(Project)
        if user_id:
            query = query.filter(Project.user_id == user_id)
        query = query.order_by(desc(Expense.expense_date))
        if limit:
            query = query.limit(limit)
        return query.all()

    def update(self, expense_id: int, **kwargs) -> Optional[Expense]:
        expense = self.get_by_id(expense_id)
        if expense:
            for key, value in kwargs.items():
                if hasattr(expense, key):
                    setattr(expense, key, value)
            self.session.flush()
        return expense

    def delete(self, expense_id: int) -> bool:
        expense = self.get_by_id(expense_id)
        if expense:
            self.session.delete(expense)
            return True
        return False

    def get_by_date_range(self, start_date: datetime, end_date: datetime,
                          user_id: int = None) -> List[Expense]:
        query = self.session.query(Expense).join(Project)\
            .filter(Expense.expense_date >= start_date)\
            .filter(Expense.expense_date <= end_date)
        if user_id:
            query = query.filter(Project.user_id == user_id)
        return query.order_by(Expense.expense_date).all()

    def get_by_category(self, category_id: int) -> List[Expense]:
        return self.session.query(Expense)\
            .filter(Expense.category_id == category_id)\
            .order_by(desc(Expense.expense_date)).all()


# ============================================================================
# PROJECT HISTORY REPOSITORY
# ============================================================================

class ProjectHistoryRepository(BaseRepository):
    """Repository for Project audit trail"""

    def create(self, project_id: int, action: str, description: str = None,
               budget_allocated: float = None, budget_spent: float = None,
               expense_count: int = None) -> ProjectHistory:
        history = ProjectHistory(
            project_id=project_id,
            action=action,
            description=description,
            budget_allocated_snapshot=budget_allocated,
            budget_spent_snapshot=budget_spent,
            expense_count_snapshot=expense_count
        )
        self.session.add(history)
        self.session.flush()
        return history

    def get_by_project(self, project_id: int, limit: int = None) -> List[ProjectHistory]:
        query = self.session.query(ProjectHistory)\
            .filter(ProjectHistory.project_id == project_id)\
            .order_by(desc(ProjectHistory.created_at))
        if limit:
            query = query.limit(limit)
        return query.all()

    def get_all(self, limit: int = None) -> List[ProjectHistory]:
        query = self.session.query(ProjectHistory)\
            .order_by(desc(ProjectHistory.created_at))
        if limit:
            query = query.limit(limit)
        return query.all()


# ============================================================================
# BANK ACCOUNT REPOSITORY
# ============================================================================

class BankAccountRepository(BaseRepository):
    """Repository for Bank Account operations"""

    def create(self, user_id: int, name: str, bank_name: str = None,
               account_type: AccountType = AccountType.COURANT,
               balance: float = 0, currency: str = 'EUR') -> BankAccount:
        account = BankAccount(
            user_id=user_id,
            name=name,
            bank_name=bank_name,
            account_type=account_type,
            balance=balance,
            currency=currency
        )
        self.session.add(account)
        self.session.flush()
        return account

    def get_by_id(self, account_id: int, with_transactions: bool = False) -> Optional[BankAccount]:
        query = self.session.query(BankAccount)
        if with_transactions:
            query = query.options(joinedload(BankAccount.transactions))
        return query.filter(BankAccount.id == account_id).first()

    def get_all(self, user_id: int = None, active_only: bool = True) -> List[BankAccount]:
        query = self.session.query(BankAccount)
        if user_id:
            query = query.filter(BankAccount.user_id == user_id)
        if active_only:
            query = query.filter(BankAccount.is_active == True)
        return query.order_by(BankAccount.name).all()

    def update_balance(self, account_id: int, new_balance: float):
        account = self.get_by_id(account_id)
        if account:
            account.balance = new_balance
            account.updated_at = datetime.utcnow()
            self.session.flush()

    def update(self, account_id: int, **kwargs) -> Optional[BankAccount]:
        account = self.get_by_id(account_id)
        if account:
            for key, value in kwargs.items():
                if hasattr(account, key):
                    setattr(account, key, value)
            account.updated_at = datetime.utcnow()
            self.session.flush()
        return account

    def delete(self, account_id: int) -> bool:
        account = self.get_by_id(account_id)
        if account:
            self.session.delete(account)
            return True
        return False

    def get_total_balance(self, user_id: int = None) -> float:
        query = self.session.query(func.sum(BankAccount.balance))\
            .filter(BankAccount.is_active == True)
        if user_id:
            query = query.filter(BankAccount.user_id == user_id)
        return query.scalar() or 0


# ============================================================================
# BANK TRANSACTION REPOSITORY
# ============================================================================

class BankTransactionRepository(BaseRepository):
    """Repository for Bank Transaction operations"""

    def create(self, account_id: int, transaction_type: TransactionType,
               amount: float, balance_after: float, description: str = None,
               transaction_date: datetime = None) -> BankTransaction:
        transaction = BankTransaction(
            account_id=account_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=balance_after,
            description=description,
            transaction_date=transaction_date or datetime.utcnow()
        )
        self.session.add(transaction)
        self.session.flush()
        return transaction

    def get_by_account(self, account_id: int, limit: int = None) -> List[BankTransaction]:
        query = self.session.query(BankTransaction)\
            .filter(BankTransaction.account_id == account_id)\
            .order_by(desc(BankTransaction.transaction_date))
        if limit:
            query = query.limit(limit)
        return query.all()

    def get_by_date_range(self, account_id: int, start_date: datetime,
                          end_date: datetime) -> List[BankTransaction]:
        return self.session.query(BankTransaction)\
            .filter(BankTransaction.account_id == account_id)\
            .filter(BankTransaction.transaction_date >= start_date)\
            .filter(BankTransaction.transaction_date <= end_date)\
            .order_by(BankTransaction.transaction_date).all()


# ============================================================================
# DASHBOARD REPOSITORY
# ============================================================================

class DashboardRepository(BaseRepository):
    """Repository for Dashboard operations"""

    def create(self, user_id: int, name: str = 'Dashboard Principal',
               is_default: bool = False, settings: dict = None) -> Dashboard:
        dashboard = Dashboard(
            user_id=user_id,
            name=name,
            is_default=is_default,
            settings=settings or {}
        )
        self.session.add(dashboard)
        self.session.flush()
        return dashboard

    def get_by_id(self, dashboard_id: int, with_widgets: bool = False) -> Optional[Dashboard]:
        query = self.session.query(Dashboard)
        if with_widgets:
            query = query.options(
                joinedload(Dashboard.widgets).joinedload(Widget.layout)
            )
        return query.filter(Dashboard.id == dashboard_id).first()

    def get_default(self, user_id: int) -> Optional[Dashboard]:
        return self.session.query(Dashboard)\
            .filter(Dashboard.user_id == user_id)\
            .filter(Dashboard.is_default == True).first()

    def get_or_create_default(self, user_id: int) -> Dashboard:
        dashboard = self.get_default(user_id)
        if not dashboard:
            dashboard = self.create(user_id, is_default=True)
            self.commit()
        return dashboard

    def get_all(self, user_id: int) -> List[Dashboard]:
        return self.session.query(Dashboard)\
            .filter(Dashboard.user_id == user_id)\
            .order_by(desc(Dashboard.is_default), Dashboard.name).all()

    def update(self, dashboard_id: int, **kwargs) -> Optional[Dashboard]:
        dashboard = self.get_by_id(dashboard_id)
        if dashboard:
            for key, value in kwargs.items():
                if hasattr(dashboard, key):
                    setattr(dashboard, key, value)
            dashboard.updated_at = datetime.utcnow()
            self.session.flush()
        return dashboard

    def delete(self, dashboard_id: int) -> bool:
        dashboard = self.get_by_id(dashboard_id)
        if dashboard:
            self.session.delete(dashboard)
            return True
        return False


# ============================================================================
# WIDGET REPOSITORY
# ============================================================================

class WidgetRepository(BaseRepository):
    """Repository for Widget operations"""

    def create(self, dashboard_id: int, widget_type: str,
               kpi_config: dict = None, ai_prompt: str = None,
               ai_response: str = None) -> Widget:
        widget = Widget(
            dashboard_id=dashboard_id,
            widget_type=widget_type,
            kpi_config=kpi_config,
            ai_prompt=ai_prompt,
            ai_response=ai_response
        )
        self.session.add(widget)
        self.session.flush()
        return widget

    def get_by_id(self, widget_id: int, with_layout: bool = False) -> Optional[Widget]:
        query = self.session.query(Widget)
        if with_layout:
            query = query.options(joinedload(Widget.layout))
        return query.filter(Widget.id == widget_id).first()

    def get_by_dashboard(self, dashboard_id: int) -> List[Widget]:
        return self.session.query(Widget)\
            .options(joinedload(Widget.layout))\
            .filter(Widget.dashboard_id == dashboard_id).all()

    def update(self, widget_id: int, **kwargs) -> Optional[Widget]:
        widget = self.get_by_id(widget_id)
        if widget:
            for key, value in kwargs.items():
                if hasattr(widget, key):
                    setattr(widget, key, value)
            widget.updated_at = datetime.utcnow()
            self.session.flush()
        return widget

    def delete(self, widget_id: int) -> bool:
        widget = self.get_by_id(widget_id)
        if widget:
            self.session.delete(widget)
            return True
        return False


# ============================================================================
# WIDGET LAYOUT REPOSITORY
# ============================================================================

class WidgetLayoutRepository(BaseRepository):
    """Repository for Widget Layout operations"""

    def create_or_update(self, widget_id: int, x: int, y: int,
                         width: int, height: int) -> WidgetLayout:
        layout = self.session.query(WidgetLayout)\
            .filter(WidgetLayout.widget_id == widget_id).first()

        if layout:
            layout.x = x
            layout.y = y
            layout.width = width
            layout.height = height
            layout.updated_at = datetime.utcnow()
        else:
            layout = WidgetLayout(
                widget_id=widget_id,
                x=x, y=y,
                width=width, height=height
            )
            self.session.add(layout)

        self.session.flush()
        return layout

    def get_by_widget(self, widget_id: int) -> Optional[WidgetLayout]:
        return self.session.query(WidgetLayout)\
            .filter(WidgetLayout.widget_id == widget_id).first()

    def batch_update(self, layouts: List[Dict[str, Any]]):
        """Update multiple layouts at once"""
        for layout_data in layouts:
            widget_id = layout_data.get('widget_id')
            if widget_id:
                self.create_or_update(
                    widget_id=widget_id,
                    x=layout_data.get('x', 0),
                    y=layout_data.get('y', 0),
                    width=layout_data.get('width', 4),
                    height=layout_data.get('height', 3)
                )


# ============================================================================
# KPI DEFINITION REPOSITORY
# ============================================================================

class KPIDefinitionRepository(BaseRepository):
    """Repository for KPI Definition templates"""

    def create(self, name: str, metric: str, aggregation: str = 'sum',
               visualization: str = 'number', description: str = None,
               default_config: dict = None, is_system: bool = False) -> KPIDefinition:
        from .models import KPIAggregation, WidgetVisualization

        kpi = KPIDefinition(
            name=name,
            description=description,
            metric=metric,
            aggregation=KPIAggregation(aggregation),
            visualization=WidgetVisualization(visualization),
            default_config=default_config or {},
            is_system=is_system
        )
        self.session.add(kpi)
        self.session.flush()
        return kpi

    def get_all(self, include_system: bool = True) -> List[KPIDefinition]:
        query = self.session.query(KPIDefinition)
        if not include_system:
            query = query.filter(KPIDefinition.is_system == False)
        return query.order_by(KPIDefinition.name).all()

    def get_by_metric(self, metric: str) -> List[KPIDefinition]:
        return self.session.query(KPIDefinition)\
            .filter(KPIDefinition.metric == metric).all()

    def ensure_defaults(self):
        """Create default KPI definitions"""
        if self.session.query(KPIDefinition).filter(KPIDefinition.is_system == True).count() == 0:
            defaults = [
                ('Budget Total', 'budget_total', 'sum', 'number', 'Somme des budgets alloués'),
                ('Budget Dépensé', 'budget_spent', 'sum', 'number', 'Total des dépenses'),
                ('Utilisation Budget', 'budget_utilization', 'avg', 'gauge', 'Pourcentage moyen d\'utilisation'),
                ('Nombre de Projets', 'project_count', 'count', 'number', 'Nombre total de projets'),
                ('Évolution Dépenses', 'expense_amount', 'sum', 'line', 'Évolution des dépenses dans le temps'),
                ('Répartition par Catégorie', 'category_spending', 'sum', 'pie', 'Dépenses par catégorie'),
            ]
            for name, metric, agg, viz, desc in defaults:
                self.create(name, metric, agg, viz, desc, is_system=True)
            self.commit()
