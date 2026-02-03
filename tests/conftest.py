"""
Configuration des tests pytest pour FLOOSE
"""

import pytest
import tempfile
import shutil
import os
from app import app
from services import BudgetManager, DataManager


@pytest.fixture
def client():
    """Client de test Flask"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def temp_data_dir():
    """Répertoire temporaire pour les tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_data_manager(temp_data_dir):
    """DataManager de test avec répertoire temporaire"""
    return DataManager(data_dir=temp_data_dir)


@pytest.fixture
def test_budget_manager(temp_data_dir):
    """BudgetManager de test avec répertoire temporaire"""
    # Créer temporairement un BudgetManager de test
    original_data_dir = None
    manager = BudgetManager()
    original_data_dir = manager.data_manager.data_dir
    
    # Remplacer par le répertoire de test
    manager.data_manager = DataManager(data_dir=temp_data_dir)
    manager.projets = []
    manager.budget_total = 0
    manager.comptes_bancaires = []
    manager.load_data_from_csv()
    
    yield manager


@pytest.fixture
def sample_project_data():
    """Données de test pour un projet"""
    return {
        'nom': 'Projet Test',
        'budget_alloue': 10000,
        'categorie': 'IT & Tech'
    }


@pytest.fixture
def sample_expense_data():
    """Données de test pour une dépense"""
    return {
        'montant': 1500,
        'description': 'Dépense de test',
        'categorie_id': 1
    }


@pytest.fixture
def sample_account_data():
    """Données de test pour un compte bancaire"""
    return {
        'nom': 'Compte Test',
        'banque': 'Banque Test',
        'solde_initial': 5000,
        'type_compte': 'Courant'
    }