"""
Tests pour le DataManager
"""

import pytest
import os
import csv
from services import DataManager


def test_data_manager_initialization(temp_data_dir):
    """Test l'initialisation du DataManager"""
    dm = DataManager(data_dir=temp_data_dir)
    
    # Vérifier que le répertoire existe
    assert os.path.exists(temp_data_dir)
    
    # Vérifier que tous les fichiers CSV sont créés
    for filename in dm.files_structure.keys():
        filepath = os.path.join(temp_data_dir, filename)
        assert os.path.exists(filepath)


def test_save_and_load_projet(test_data_manager):
    """Test la sauvegarde et le chargement de projets"""
    dm = test_data_manager
    
    projet_data = {
        'nom': 'Test Projet',
        'budget_alloue': 5000,
        'budget_depense': 1000,
        'categorie_id': 1
    }
    
    # Sauvegarder
    projet_id = dm.save_projet(projet_data)
    assert projet_id == 1
    
    # Charger
    projets = dm.load_projets()
    assert len(projets) == 1
    assert projets[0]['nom'] == 'Test Projet'
    assert projets[0]['budget_alloue'] == 5000


def test_save_and_load_depense(test_data_manager):
    """Test la sauvegarde et le chargement de dépenses"""
    dm = test_data_manager
    
    # Créer d'abord un projet
    projet_data = {'nom': 'Test', 'budget_alloue': 5000}
    projet_id = dm.save_projet(projet_data)
    
    # Créer une dépense
    depense_data = {
        'montant': 500,
        'description': 'Test dépense',
        'categorie_id': 1
    }
    
    depense_id = dm.save_depense(depense_data, projet_id)
    assert depense_id == 1
    
    # Vérifier le chargement
    depenses = dm.load_depenses_by_projet(projet_id)
    assert len(depenses) == 1
    assert depenses[0]['description'] == 'Test dépense'


def test_categories_creation(test_data_manager):
    """Test la création automatique des catégories par défaut"""
    dm = test_data_manager
    
    categories = dm.load_categories()
    assert len(categories) > 0
    
    # Vérifier qu'il y a des catégories projet et dépense
    categories_projet = dm.load_categories('projet')
    categories_depense = dm.load_categories('depense')
    
    assert len(categories_projet) > 0
    assert len(categories_depense) > 0


def test_update_operations(test_data_manager):
    """Test les opérations de mise à jour"""
    dm = test_data_manager
    
    # Créer un projet
    projet_data = {'nom': 'Test', 'budget_alloue': 5000, 'budget_depense': 0}
    projet_id = dm.save_projet(projet_data)
    
    # Mettre à jour le budget dépensé
    dm.update_projet_budget_depense(projet_id, 1500)
    
    # Vérifier la mise à jour
    projets = dm.load_projets()
    assert projets[0]['budget_depense'] == 1500


def test_concurrent_file_access(test_data_manager):
    """Test basique de gestion d'accès concurrentiel"""
    dm = test_data_manager
    
    # Simuler des opérations simultanées
    projet_data1 = {'nom': 'Projet 1', 'budget_alloue': 1000}
    projet_data2 = {'nom': 'Projet 2', 'budget_alloue': 2000}
    
    id1 = dm.save_projet(projet_data1)
    id2 = dm.save_projet(projet_data2)
    
    # Vérifier que les IDs sont uniques
    assert id1 != id2
    
    # Vérifier que les deux projets sont sauvegardés
    projets = dm.load_projets()
    assert len(projets) == 2


def test_database_stats(test_data_manager):
    """Test les statistiques de la base de données"""
    dm = test_data_manager
    
    # Ajouter quelques données
    dm.save_projet({'nom': 'Test 1', 'budget_alloue': 1000})
    dm.save_projet({'nom': 'Test 2', 'budget_alloue': 2000})
    
    stats = dm.get_database_stats()
    assert stats['projets'] == 2
    assert stats['categories'] > 0  # Catégories par défaut