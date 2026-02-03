"""
Routes API pour les opérations bancaires
Prêtes pour l'intégration Open Banking
"""

from flask import Blueprint, jsonify, request, session
from datetime import datetime, timedelta
import logging

from services import (
    require_auth,
    get_banking_service,
    performance_monitor,
    get_category_label,
    get_category_color
)

logger = logging.getLogger(__name__)

# Blueprint pour les routes bancaires
banking_bp = Blueprint('banking', __name__, url_prefix='/api/banking')


# ============================================================
# BANKS
# ============================================================

@banking_bp.route('/banks', methods=['GET'])
@require_auth
def get_banks():
    """
    Liste les banques disponibles pour connexion

    Returns:
        JSON: Liste des banques avec leurs informations
    """
    service = get_banking_service()
    banks = service.get_available_banks()

    return jsonify({
        'success': True,
        'banks': banks,
        'count': len(banks)
    })


@banking_bp.route('/banks/<bank_id>', methods=['GET'])
@require_auth
def get_bank(bank_id: str):
    """
    Récupère les détails d'une banque

    Args:
        bank_id: Identifiant de la banque

    Returns:
        JSON: Informations de la banque
    """
    service = get_banking_service()
    bank = service.get_bank_by_id(bank_id)

    if not bank:
        return jsonify({
            'success': False,
            'error': 'Banque non trouvée'
        }), 404

    return jsonify({
        'success': True,
        'bank': bank
    })


# ============================================================
# CONNECTIONS
# ============================================================

@banking_bp.route('/connect/<bank_id>', methods=['POST'])
@require_auth
@performance_monitor('bank_connect')
def connect_bank(bank_id: str):
    """
    Connecte l'utilisateur à une banque

    Args:
        bank_id: Identifiant de la banque

    Returns:
        JSON: Résultat de la connexion
    """
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Non authentifié'}), 401

    service = get_banking_service()
    result = service.connect_bank(user_email, bank_id)

    status_code = 200 if result['success'] else 400
    return jsonify(result), status_code


@banking_bp.route('/disconnect/<bank_id>', methods=['POST'])
@require_auth
def disconnect_bank(bank_id: str):
    """
    Déconnecte l'utilisateur d'une banque

    Args:
        bank_id: Identifiant de la banque

    Returns:
        JSON: Résultat de la déconnexion
    """
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Non authentifié'}), 401

    service = get_banking_service()
    result = service.disconnect_bank(user_email, bank_id)

    return jsonify(result)


@banking_bp.route('/connections', methods=['GET'])
@require_auth
def get_connections():
    """
    Liste les connexions bancaires de l'utilisateur

    Returns:
        JSON: Liste des banques connectées
    """
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Non authentifié'}), 401

    service = get_banking_service()
    connections = service.get_user_connections(user_email)

    return jsonify({
        'success': True,
        'connections': connections,
        'count': len(connections)
    })


@banking_bp.route('/connections/<bank_id>/status', methods=['GET'])
@require_auth
def get_connection_status(bank_id: str):
    """
    Vérifie le statut de connexion à une banque

    Args:
        bank_id: Identifiant de la banque

    Returns:
        JSON: Statut de la connexion
    """
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Non authentifié'}), 401

    service = get_banking_service()
    status = service.get_connection_status(user_email, bank_id)

    return jsonify({
        'success': True,
        **status
    })


# ============================================================
# ACCOUNTS
# ============================================================

@banking_bp.route('/accounts', methods=['GET'])
@require_auth
def get_accounts():
    """
    Liste tous les comptes bancaires de l'utilisateur

    Query params:
        bank_id (optional): Filtrer par banque

    Returns:
        JSON: Liste des comptes
    """
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Non authentifié'}), 401

    bank_id = request.args.get('bank_id')

    service = get_banking_service()
    accounts = service.get_accounts(user_email, bank_id)

    return jsonify({
        'success': True,
        'accounts': accounts,
        'count': len(accounts)
    })


@banking_bp.route('/accounts/<account_id>', methods=['GET'])
@require_auth
def get_account(account_id: str):
    """
    Récupère les détails d'un compte

    Args:
        account_id: Identifiant du compte

    Returns:
        JSON: Informations du compte
    """
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Non authentifié'}), 401

    service = get_banking_service()
    account = service.get_account_by_id(user_email, account_id)

    if not account:
        return jsonify({
            'success': False,
            'error': 'Compte non trouvé'
        }), 404

    return jsonify({
        'success': True,
        'account': account
    })


@banking_bp.route('/accounts/summary', methods=['GET'])
@require_auth
def get_accounts_summary():
    """
    Récupère un résumé des comptes de l'utilisateur

    Returns:
        JSON: Résumé avec totaux et statistiques
    """
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Non authentifié'}), 401

    service = get_banking_service()
    summary = service.get_accounts_summary(user_email)

    return jsonify({
        'success': True,
        **summary
    })


# ============================================================
# TRANSACTIONS
# ============================================================

@banking_bp.route('/accounts/<account_id>/transactions', methods=['GET'])
@require_auth
def get_transactions(account_id: str):
    """
    Récupère les transactions d'un compte

    Args:
        account_id: Identifiant du compte

    Query params:
        date_from (optional): Date de début (YYYY-MM-DD)
        date_to (optional): Date de fin (YYYY-MM-DD)
        category (optional): Filtrer par catégorie
        limit (optional): Nombre maximum (défaut: 50)

    Returns:
        JSON: Liste des transactions
    """
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Non authentifié'}), 401

    # Parser les paramètres
    date_from = None
    date_to = None
    if request.args.get('date_from'):
        try:
            date_from = datetime.strptime(request.args.get('date_from'), '%Y-%m-%d')
        except ValueError:
            pass

    if request.args.get('date_to'):
        try:
            date_to = datetime.strptime(request.args.get('date_to'), '%Y-%m-%d')
        except ValueError:
            pass

    category = request.args.get('category')
    limit = min(int(request.args.get('limit', 50)), 200)

    service = get_banking_service()
    transactions = service.get_transactions(
        user_email, account_id, date_from, date_to, category, limit
    )

    return jsonify({
        'success': True,
        'transactions': transactions,
        'count': len(transactions)
    })


@banking_bp.route('/transactions/recent', methods=['GET'])
@require_auth
def get_recent_transactions():
    """
    Récupère les transactions récentes de tous les comptes

    Query params:
        days (optional): Nombre de jours (défaut: 30)
        limit (optional): Nombre maximum (défaut: 20)

    Returns:
        JSON: Liste des transactions récentes
    """
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Non authentifié'}), 401

    days = min(int(request.args.get('days', 30)), 90)
    limit = min(int(request.args.get('limit', 20)), 100)

    service = get_banking_service()
    transactions = service.get_recent_transactions(user_email, days, limit)

    return jsonify({
        'success': True,
        'transactions': transactions,
        'count': len(transactions),
        'period_days': days
    })


# ============================================================
# ANALYTICS
# ============================================================

@banking_bp.route('/analytics/spending', methods=['GET'])
@require_auth
def get_spending_analytics():
    """
    Analyse des dépenses par catégorie

    Query params:
        days (optional): Période en jours (défaut: 30)

    Returns:
        JSON: Dépenses par catégorie avec statistiques
    """
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Non authentifié'}), 401

    days = min(int(request.args.get('days', 30)), 365)

    service = get_banking_service()
    analytics = service.get_spending_by_category(user_email, days)

    # Enrichir avec les labels et couleurs
    for cat in analytics['categories']:
        from services.models import TransactionCategory
        try:
            cat_enum = TransactionCategory(cat['category'])
            cat['label'] = get_category_label(cat_enum)
            cat['color'] = get_category_color(cat_enum)
        except ValueError:
            cat['label'] = cat['category']
            cat['color'] = '#9ca3af'

    return jsonify({
        'success': True,
        **analytics
    })


# ============================================================
# SYNC
# ============================================================

@banking_bp.route('/sync', methods=['POST'])
@require_auth
@performance_monitor('bank_sync')
def sync_accounts():
    """
    Synchronise tous les comptes de l'utilisateur

    Returns:
        JSON: Résultat de la synchronisation
    """
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Non authentifié'}), 401

    service = get_banking_service()
    result = service.sync_all_accounts(user_email)

    status_code = 200 if result['success'] else 500
    return jsonify(result), status_code


# ============================================================
# CATEGORIES
# ============================================================

@banking_bp.route('/categories', methods=['GET'])
@require_auth
def get_categories():
    """
    Liste toutes les catégories de transactions disponibles

    Returns:
        JSON: Liste des catégories avec labels et couleurs
    """
    from services.models import TransactionCategory

    categories = []
    for cat in TransactionCategory:
        categories.append({
            'id': cat.value,
            'label': get_category_label(cat),
            'color': get_category_color(cat)
        })

    return jsonify({
        'success': True,
        'categories': categories
    })
