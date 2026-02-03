"""
Tests pour l'application Flask
"""

import pytest
import json
from app import app


def test_app_configuration():
    """Test la configuration de l'application"""
    assert app.config['TESTING'] is False  # Par défaut
    

def test_login_page(client):
    """Test la page de login"""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Floose' in response.data


def test_login_redirect_if_authenticated(client):
    """Test la redirection si déjà authentifié"""
    # Simuler une session authentifiée
    with client.session_transaction() as sess:
        sess['user_email'] = 'test@example.com'
        sess['user_name'] = 'Test User'
    
    response = client.get('/login')
    assert response.status_code == 302  # Redirection


def test_valid_login(client):
    """Test une connexion valide"""
    response = client.post('/login', data={
        'email': 'demo@floose.com',
        'password': 'Demo123!'
    })
    
    assert response.status_code == 302  # Redirection après connexion


def test_invalid_login(client):
    """Test une connexion invalide"""
    response = client.post('/login', data={
        'email': 'invalid@example.com',
        'password': 'wrongpassword'
    })
    
    assert response.status_code == 200
    assert b'Identifiants incorrects' in response.data


def test_missing_credentials(client):
    """Test connexion avec identifiants manquants"""
    response = client.post('/login', data={
        'email': '',
        'password': ''
    })
    
    assert response.status_code == 200
    assert b'Email et mot de passe requis' in response.data


def test_logout(client):
    """Test la déconnexion"""
    # Se connecter d'abord
    with client.session_transaction() as sess:
        sess['user_email'] = 'test@example.com'
    
    response = client.get('/logout')
    assert response.status_code == 302  # Redirection vers login


def test_index_requires_auth(client):
    """Test que l'index nécessite une authentification"""
    response = client.get('/')
    assert response.status_code == 302  # Redirection vers login


def test_index_authenticated(client):
    """Test l'accès à l'index une fois authentifié"""
    with client.session_transaction() as sess:
        sess['user_email'] = 'demo@floose.com'
        sess['user_name'] = 'Demo User'
        sess['user_avatar'] = 'DU'
    
    response = client.get('/')
    assert response.status_code == 200
    assert b'Floose' in response.data


def test_api_stats_authenticated(client):
    """Test l'API des statistiques avec authentification"""
    with client.session_transaction() as sess:
        sess['user_email'] = 'demo@floose.com'
        sess['user_name'] = 'Demo User'
    
    response = client.get('/api/stats')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'budget_total' in data
    assert 'total_depense' in data


def test_api_categories(client):
    """Test l'API des catégories"""
    with client.session_transaction() as sess:
        sess['user_email'] = 'demo@floose.com'
    
    response = client.get('/api/categories')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'categories' in data
    assert isinstance(data['categories'], list)


def test_ajouter_projet_authenticated(client):
    """Test l'ajout d'un projet avec authentification"""
    with client.session_transaction() as sess:
        sess['user_email'] = 'demo@floose.com'
    
    response = client.post('/ajouter_projet', data={
        'nom': 'Projet Test API',
        'budget': '5000',
        'categorie': 'IT & Tech'
    })
    
    assert response.status_code == 302  # Redirection après ajout


def test_ajouter_projet_invalid_data(client):
    """Test l'ajout d'un projet avec données invalides"""
    with client.session_transaction() as sess:
        sess['user_email'] = 'demo@floose.com'
    
    response = client.post('/ajouter_projet', data={
        'nom': '',  # Nom vide
        'budget': '0',  # Budget invalide
        'categorie': 'Test'
    })
    
    assert response.status_code == 400


def test_ajouter_compte_authenticated(client):
    """Test l'ajout d'un compte bancaire"""
    with client.session_transaction() as sess:
        sess['user_email'] = 'demo@floose.com'
    
    response = client.post('/ajouter_compte', data={
        'nom': 'Compte Test API',
        'banque': 'Banque Test',
        'solde_initial': '10000',
        'type_compte': 'Courant'
    })
    
    assert response.status_code == 302  # Redirection après ajout


def test_api_comptes_authenticated(client):
    """Test l'API des comptes bancaires"""
    with client.session_transaction() as sess:
        sess['user_email'] = 'demo@floose.com'
    
    response = client.get('/api/comptes')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert isinstance(data, list)


def test_dashboard_analytics_authenticated(client):
    """Test la page dashboard analytics"""
    with client.session_transaction() as sess:
        sess['user_email'] = 'demo@floose.com'
        sess['user_name'] = 'Demo User'
        sess['user_avatar'] = 'DU'
    
    response = client.get('/dashboard-analytics')
    assert response.status_code == 200


def test_apple_login_callback(client):
    """Test le callback Apple login"""
    response = client.get('/login/apple/callback?user=apple_demo')
    assert response.status_code == 302  # Redirection


def test_export_pdf_authenticated(client):
    """Test l'export PDF"""
    with client.session_transaction() as sess:
        sess['user_email'] = 'demo@floose.com'
    
    response = client.get('/api/export/pdf')
    assert response.status_code == 200
    assert response.mimetype == 'text/plain'  # Simulation en texte


def test_security_headers(client):
    """Test basique des en-têtes de sécurité"""
    response = client.get('/login')
    
    # L'application devrait avoir des en-têtes de sécurité de base
    assert response.status_code == 200
    # Note: Des en-têtes de sécurité supplémentaires devraient être ajoutés