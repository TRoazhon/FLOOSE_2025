"""
Tests pour le BudgetManager
"""

import pytest
from services import BudgetManager


def test_budget_manager_initialization(test_budget_manager):
    """Test l'initialisation du BudgetManager"""
    bm = test_budget_manager
    
    assert bm.projets == []
    assert bm.budget_total == 0
    assert bm.comptes_bancaires == []


def test_ajouter_projet(test_budget_manager):
    """Test l'ajout d'un projet"""
    bm = test_budget_manager
    
    projet = bm.ajouter_projet('Projet Test', 5000, 'IT & Tech')
    
    assert projet['nom'] == 'Projet Test'
    assert projet['budget_alloue'] == 5000
    assert projet['budget_depense'] == 0
    assert len(bm.projets) == 1
    assert bm.budget_total == 5000


def test_ajouter_depense_valid(test_budget_manager):
    """Test l'ajout d'une dépense valide"""
    bm = test_budget_manager
    
    # Créer un projet
    projet = bm.ajouter_projet('Test', 5000)
    
    # Récupérer une catégorie de dépense valide
    categories = bm.get_categories('depense')
    categorie_id = categories[0]['id'] if categories else None
    
    # Ajouter une dépense avec catégorie
    result = bm.ajouter_depense(projet['id'], 1000, 'Dépense test', categorie_id)
    
    assert result is True
    
    # Forcer un rechargement des données depuis CSV pour s'assurer de la cohérence
    bm.load_data_from_csv()
    
    projet_updated = bm.get_projet(projet['id'])
    assert projet_updated['budget_depense'] == 1000
    assert len(projet_updated['depenses']) == 1


def test_ajouter_depense_depassement_budget(test_budget_manager):
    """Test l'ajout d'une dépense qui dépasse le budget"""
    bm = test_budget_manager
    
    # Créer un projet avec budget limité
    projet = bm.ajouter_projet('Test', 1000)
    
    # Tenter d'ajouter une dépense qui dépasse le budget
    result = bm.ajouter_depense(projet['id'], 1500, 'Dépense excessive')
    
    assert result is False
    projet_updated = bm.get_projet(projet['id'])
    assert projet_updated['budget_depense'] == 0


def test_statistiques(test_budget_manager):
    """Test le calcul des statistiques"""
    bm = test_budget_manager
    
    # Créer quelques projets
    projet1 = bm.ajouter_projet('Projet 1', 5000)
    projet2 = bm.ajouter_projet('Projet 2', 3000)
    
    # Récupérer une catégorie de dépense valide
    categories = bm.get_categories('depense')
    categorie_id = categories[0]['id'] if categories else None
    
    # Ajouter des dépenses avec catégorie
    bm.ajouter_depense(projet1['id'], 2000, 'Dépense 1', categorie_id)
    bm.ajouter_depense(projet2['id'], 1000, 'Dépense 2', categorie_id)
    
    stats = bm.get_statistiques()
    
    assert stats['budget_total'] == 8000
    assert stats['total_depense'] == 3000
    assert stats['total_restant'] == 5000
    assert stats['nombre_projets'] == 2
    assert stats['pourcentage_utilise'] == 37.5


def test_comptes_bancaires(test_budget_manager):
    """Test la gestion des comptes bancaires"""
    bm = test_budget_manager
    
    # Ajouter un compte
    compte = bm.ajouter_compte_bancaire('Compte Test', 'Banque Test', 5000)
    
    assert compte.nom == 'Compte Test'
    assert compte.solde == 5000
    assert len(bm.comptes_bancaires) == 1
    
    # Effectuer une opération
    result = bm.effectuer_operation_bancaire(compte.id, 1000, 'Test débit', 'débit')
    assert result is True
    assert compte.solde == 4000
    
    # Tentative de débit avec solde insuffisant
    result = bm.effectuer_operation_bancaire(compte.id, 5000, 'Débit impossible', 'débit')
    assert result is False
    assert compte.solde == 4000


def test_modifier_depense(test_budget_manager):
    """Test la modification d'une dépense"""
    bm = test_budget_manager
    
    # Créer un projet avec une dépense
    projet = bm.ajouter_projet('Test', 5000)
    
    # Récupérer une catégorie de dépense valide
    categories = bm.get_categories('depense')
    categorie_id = categories[0]['id'] if categories else None
    
    bm.ajouter_depense(projet['id'], 1000, 'Dépense originale', categorie_id)
    
    # Récupérer l'ID de la dépense
    projet_updated = bm.get_projet(projet['id'])
    depense_id = projet_updated['depenses'][0]['id']
    
    # Modifier la dépense
    result = bm.modifier_depense(projet['id'], depense_id, 1500, 'Dépense modifiée')
    
    assert result is True
    projet_final = bm.get_projet(projet['id'])
    assert projet_final['budget_depense'] == 1500
    assert projet_final['depenses'][0]['description'] == 'Dépense modifiée'


def test_supprimer_depense(test_budget_manager):
    """Test la suppression d'une dépense"""
    bm = test_budget_manager
    
    # Créer un projet avec une dépense
    projet = bm.ajouter_projet('Test', 5000)
    
    # Récupérer une catégorie de dépense valide
    categories = bm.get_categories('depense')
    categorie_id = categories[0]['id'] if categories else None
    
    bm.ajouter_depense(projet['id'], 1000, 'Dépense à supprimer', categorie_id)
    
    # Récupérer l'ID de la dépense
    projet_updated = bm.get_projet(projet['id'])
    depense_id = projet_updated['depenses'][0]['id']
    
    # Supprimer la dépense
    result = bm.supprimer_depense(projet['id'], depense_id)
    
    assert result is True
    projet_final = bm.get_projet(projet['id'])
    assert projet_final['budget_depense'] == 0
    assert len(projet_final['depenses']) == 0


def test_categories_management(test_budget_manager):
    """Test la gestion des catégories"""
    bm = test_budget_manager
    
    # Récupérer les catégories par défaut
    categories = bm.get_categories()
    assert len(categories) > 0
    
    # Ajouter une catégorie personnalisée
    categorie_id = bm.ajouter_categorie(
        'Test Catégorie',
        '#FF0000',
        'projet',
        'Description test'
    )
    
    assert categorie_id > 0
    
    # Vérifier que la catégorie a été ajoutée
    categories_updated = bm.get_categories()
    assert len(categories_updated) == len(categories) + 1
    
    # Modifier la catégorie
    result = bm.modifier_categorie(categorie_id, 'Catégorie Modifiée', '#00FF00', 'Nouvelle description')
    assert result is True
    
    # Supprimer la catégorie (possible car non utilisée)
    result = bm.supprimer_categorie(categorie_id)
    assert result is True


def test_historique_projets(test_budget_manager):
    """Test l'historique des projets"""
    bm = test_budget_manager
    
    # Créer un projet
    projet = bm.ajouter_projet('Projet Historique', 5000)
    
    # Ajouter une dépense pour créer de l'historique
    bm.ajouter_depense(projet['id'], 1000, 'Première dépense')
    
    # Récupérer l'historique
    historique = bm.get_historique_projet(projet['id'])
    
    assert len(historique) >= 2  # Au moins création + dépense
    assert historique[0]['action'] in ['creation', 'migration']
    assert historique[-1]['action'] == 'depense_ajoutee'