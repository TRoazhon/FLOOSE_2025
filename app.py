"""
Application Web Flask pour le Gestionnaire de Budget
Interface simple et efficace avec sécurité renforcée et optimisations
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from config import get_config, setup_logging, get_app_info
from services import (
    BudgetManager,
    get_auth_manager,
    require_auth,
    get_current_user,
    get_performance_manager,
    performance_monitor,
    get_lock_manager,
    calculate_financial_health,
    get_health_level,
    generate_ai_analysis,
    generate_recommendations,
    generate_analytics_report,
    get_credit_agricole_service,
    init_credit_agricole_service,
    CreditAgricoleError,
    init_banking_service,
    get_banking_service
)
from routes import banking_bp, auth_bp
import io
import logging
from datetime import datetime

# Configuration et initialisation de l'application Flask
config = get_config()
app = Flask(__name__)
config.init_app(app)

# Configuration du logging
setup_logging(config)
logger = logging.getLogger(__name__)

# Instance globale du gestionnaire avec configuration
manager = BudgetManager()

# Gestionnaires pour sécurité et performance
auth_manager = get_auth_manager()
perf_manager = get_performance_manager()

# Initialisation du service Crédit Agricole si activé
ca_service = None
if config.CA_ENABLED and config.CA_CLIENT_ID and config.CA_CLIENT_SECRET:
    ca_service = init_credit_agricole_service(
        client_id=config.CA_CLIENT_ID,
        client_secret=config.CA_CLIENT_SECRET,
        redirect_uri=config.CA_REDIRECT_URI,
        environment=config.CA_ENVIRONMENT
    )
    logger.info("Service Crédit Agricole initialisé")
else:
    logger.info("Service Crédit Agricole désactivé (CA_ENABLED=False ou identifiants manquants)")

logger.info("Application FLOOSE initialisée avec configuration renforcée")

# Initialisation du service bancaire (utilise le mock par défaut)
banking_service = init_banking_service()
logger.info("Service bancaire initialisé avec MockBankAPIProvider")

# Enregistrement des blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(banking_bp)
logger.info("Blueprints auth et banking enregistrés")

# Les utilisateurs sont maintenant gérés par AuthManager
# Utilisateurs de démonstration configurés dans auth_manager.py
# Routes d'authentification gérées par le blueprint auth_bp

@app.route('/')
@require_auth
def index():
    """
    Page d'accueil - Vue d'ensemble des budgets
    Principe : Interface visuelle et efficace
    """
    projets = manager.get_tous_projets()
    stats = manager.get_statistiques()
    comptes = manager.get_tous_comptes_bancaires()
    stats_comptes = manager.get_statistiques_comptes()
    
    user_data = {
        'name': session.get('user_name', 'User'),
        'avatar': session.get('user_avatar', 'U'),
        'email': session.get('user_email', '')
    }
    
    return render_template('index.html', projets=projets, stats=stats,
                         comptes=comptes, stats_comptes=stats_comptes, user=user_data)


@app.route('/banking')
@require_auth
def banking_dashboard():
    """
    Dashboard des comptes bancaires
    Affiche les comptes connectes et transactions
    """
    user_data = {
        'name': session.get('user_name', 'User'),
        'avatar': session.get('user_avatar', 'U'),
        'email': session.get('user_email', '')
    }

    return render_template('banking_dashboard.html', user=user_data)


@app.route('/ajouter_projet', methods=['POST'])
def ajouter_projet():
    """
    Route pour ajouter un nouveau projet
    Principe : Moins de clics, efficacité
    """
    # Récupération des données du formulaire
    nom = request.form.get('nom')
    budget = float(request.form.get('budget', 0))
    categorie = request.form.get('categorie', 'Général')
    
    # Validation basique
    if not nom or budget <= 0:
        return jsonify({'success': False, 'message': 'Données invalides'}), 400
    
    # Ajout du projet
    projet = manager.ajouter_projet(nom, budget, categorie)
    
    return redirect(url_for('index'))

@app.route('/ajouter_depense/<int:projet_id>', methods=['POST'])
def ajouter_depense(projet_id):
    """
    Route pour ajouter une dépense à un projet
    Principe : Cohérence des données
    """
    # Récupération des données
    montant = float(request.form.get('montant', 0))
    description = request.form.get('description', '')
    categorie_id = request.form.get('categorie_id')
    date_depense = request.form.get('date_depense')
    commentaire = request.form.get('commentaire', '')
    compte_id = request.form.get('compte_id')
    
    # Validation
    if montant <= 0:
        return jsonify({'success': False, 'message': 'Montant invalide'}), 400
    
    if not categorie_id:
        return jsonify({'success': False, 'message': 'Catégorie requise'}), 400
    
    # Si un compte est sélectionné, vérifier le solde et débiter
    if compte_id:
        compte_id = int(compte_id)
        compte = manager.get_compte_bancaire(compte_id)
        if compte and compte.solde < montant:
            return jsonify({'success': False, 'message': 'Solde insuffisant sur le compte bancaire'}), 400
    
    # Ajout de la dépense
    success = manager.ajouter_depense(projet_id, montant, description, int(categorie_id), date_depense, commentaire)
    
    if not success:
        return jsonify({'success': False, 'message': 'Budget dépassé ou projet inexistant'}), 400
    
    # Si un compte est sélectionné, débiter le montant
    if compte_id:
        manager.effectuer_operation_bancaire(compte_id, montant, f"Dépense: {description}", 'débit')
    
    return redirect(url_for('index'))

@app.route('/modifier_depense/<int:projet_id>/<int:depense_id>', methods=['POST'])
@require_auth
def modifier_depense(projet_id, depense_id):
    """
    Route pour modifier une dépense existante
    """
    
    try:
        # Récupération des données du formulaire
        nouveau_montant = float(request.form.get('montant', 0))
        nouvelle_description = request.form.get('description', '').strip()
        
        # Validations renforcées
        if nouveau_montant <= 0:
            return jsonify({'success': False, 'message': 'Le montant doit être positif'}), 400
        
        if not nouvelle_description:
            return jsonify({'success': False, 'message': 'La description est requise'}), 400
        
        if len(nouvelle_description) > 200:
            return jsonify({'success': False, 'message': 'La description est trop longue (max 200 caractères)'}), 400
        
        # Vérifier que la dépense existe et appartient au projet
        depense_existante = manager.get_depense(depense_id)
        if not depense_existante:
            return jsonify({'success': False, 'message': 'Dépense non trouvée'}), 404
        
        if depense_existante['projet_id'] != projet_id:
            return jsonify({'success': False, 'message': 'Cette dépense n\'appartient pas à ce projet'}), 403
        
        # Modification de la dépense
        success = manager.modifier_depense(projet_id, depense_id, nouveau_montant, nouvelle_description)
        
        if not success:
            return jsonify({'success': False, 'message': 'Impossible de modifier la dépense (budget dépassé)'}), 400
        
        return redirect(url_for('index'))
        
    except ValueError:
        return jsonify({'success': False, 'message': 'Montant invalide'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur interne: {str(e)}'}), 500

@app.route('/supprimer_depense/<int:projet_id>/<int:depense_id>', methods=['POST'])
@require_auth
def supprimer_depense(projet_id, depense_id):
    """
    Route pour supprimer une dépense
    """
    
    try:
        # Vérifier que la dépense existe et appartient au projet
        depense_existante = manager.get_depense(depense_id)
        if not depense_existante:
            return jsonify({'success': False, 'message': 'Dépense non trouvée'}), 404
        
        if depense_existante['projet_id'] != projet_id:
            return jsonify({'success': False, 'message': 'Cette dépense n\'appartient pas à ce projet'}), 403
        
        # Suppression de la dépense
        success = manager.supprimer_depense(projet_id, depense_id)
        
        if not success:
            return jsonify({'success': False, 'message': 'Impossible de supprimer la dépense'}), 500
        
        return redirect(url_for('index'))
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur interne: {str(e)}'}), 500

@app.route('/api/depense/<int:depense_id>')
def api_get_depense(depense_id):
    """
    API pour récupérer les détails d'une dépense
    """
    depense = manager.get_depense(depense_id)
    if depense is None:
        return jsonify({'error': 'Dépense non trouvée'}), 404
    return jsonify(depense)

@app.route('/api/projet/<int:projet_id>/depenses')
def api_get_depenses_projet(projet_id):
    """
    API pour récupérer toutes les dépenses d'un projet
    """
    depenses = manager.get_depenses_projet(projet_id)
    return jsonify({'depenses': depenses})

@app.route('/api/categories')
def api_categories():
    """
    API pour récupérer toutes les catégories
    """
    type_filter = request.args.get('type')  # 'projet' ou 'depense'
    categories = manager.get_categories(type_filter)
    return jsonify({'categories': categories})

@app.route('/api/categories/<int:categorie_id>')
def api_get_categorie(categorie_id):
    """
    API pour récupérer une catégorie par son ID
    """
    categorie = manager.get_categorie(categorie_id)
    if categorie is None:
        return jsonify({'error': 'Catégorie non trouvée'}), 404
    return jsonify(categorie)

@app.route('/ajouter_categorie', methods=['POST'])
@require_auth
def ajouter_categorie():
    """
    Route pour ajouter une nouvelle catégorie
    """
    
    nom = request.form.get('nom', '').strip()
    couleur = request.form.get('couleur', '#F5F5F5').strip()
    type_categorie = request.form.get('type', 'projet').strip()
    description = request.form.get('description', '').strip()
    
    # Validation
    if not nom:
        return jsonify({'success': False, 'message': 'Le nom de la catégorie est requis'}), 400
    
    if type_categorie not in ['projet', 'depense']:
        return jsonify({'success': False, 'message': 'Type de catégorie invalide'}), 400
    
    # Validation couleur hex
    if not couleur.startswith('#') or len(couleur) != 7:
        return jsonify({'success': False, 'message': 'Format de couleur invalide'}), 400
    
    try:
        categorie_id = manager.ajouter_categorie(nom, couleur, type_categorie, description)
        return jsonify({'success': True, 'categorie_id': categorie_id})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur lors de la création: {str(e)}'}), 500

@app.route('/modifier_categorie/<int:categorie_id>', methods=['POST'])
@require_auth
def modifier_categorie(categorie_id):
    """
    Route pour modifier une catégorie existante
    """
    
    nom = request.form.get('nom', '').strip()
    couleur = request.form.get('couleur', '#F5F5F5').strip()
    description = request.form.get('description', '').strip()
    
    # Validation
    if not nom:
        return jsonify({'success': False, 'message': 'Le nom de la catégorie est requis'}), 400
    
    if not couleur.startswith('#') or len(couleur) != 7:
        return jsonify({'success': False, 'message': 'Format de couleur invalide'}), 400
    
    try:
        success = manager.modifier_categorie(categorie_id, nom, couleur, description)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Catégorie non trouvée'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur lors de la modification: {str(e)}'}), 500

@app.route('/supprimer_categorie/<int:categorie_id>', methods=['POST'])
@require_auth
def supprimer_categorie(categorie_id):
    """
    Route pour supprimer une catégorie
    """
    
    try:
        success = manager.supprimer_categorie(categorie_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Impossible de supprimer : catégorie utilisée ou non trouvée'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur lors de la suppression: {str(e)}'}), 500

@app.route('/api/stats')
def api_stats():
    """
    API pour récupérer les statistiques
    Principe : Intelligence des données
    """
    stats = manager.get_statistiques()
    return jsonify(stats)

@app.route('/api/projet/<int:projet_id>')
def api_projet(projet_id):
    """
    API pour récupérer les détails d'un projet
    Principe : Modularité
    """
    projet = manager.get_projet(projet_id)
    if projet is None:
        return jsonify({'error': 'Projet non trouvé'}), 404
    return jsonify(projet)

@app.route('/api/historique_projets')
def api_historique_projets():
    """
    API pour récupérer l'historique d'évolution de tous les projets
    """
    historique = manager.get_historique_tous_projets_avec_categories()
    return jsonify(historique)

# === ROUTES POUR LES COMPTES BANCAIRES ===

@app.route('/ajouter_compte', methods=['POST'])
def ajouter_compte():
    """
    Route pour ajouter un nouveau compte bancaire
    """
    nom = request.form.get('nom')
    banque = request.form.get('banque')
    solde_initial = float(request.form.get('solde_initial', 0))
    type_compte = request.form.get('type_compte', 'Courant')
    
    if not nom or not banque:
        return jsonify({'success': False, 'message': 'Nom et banque requis'}), 400
    
    compte = manager.ajouter_compte_bancaire(nom, banque, solde_initial, type_compte)
    return redirect(url_for('index'))

@app.route('/operation_bancaire/<int:compte_id>', methods=['POST'])
def operation_bancaire(compte_id):
    """
    Route pour effectuer une opération bancaire
    """
    montant = float(request.form.get('montant', 0))
    description = request.form.get('description', '')
    type_operation = request.form.get('type_operation', 'débit')
    
    if montant <= 0:
        return jsonify({'success': False, 'message': 'Montant invalide'}), 400
    
    success = manager.effectuer_operation_bancaire(compte_id, montant, description, type_operation)
    
    if not success:
        message = 'Solde insuffisant' if type_operation == 'débit' else 'Compte inexistant'
        return jsonify({'success': False, 'message': message}), 400
    
    return redirect(url_for('index'))

@app.route('/api/comptes')
def api_comptes():
    """
    API pour récupérer tous les comptes bancaires
    """
    comptes = manager.get_tous_comptes_bancaires()
    return jsonify(comptes)

@app.route('/api/compte/<int:compte_id>')
def api_compte(compte_id):
    """
    API pour récupérer les détails d'un compte bancaire
    """
    compte = manager.get_compte_bancaire(compte_id)
    if compte is None:
        return jsonify({'error': 'Compte non trouvé'}), 404
    return jsonify(compte.to_dict())

# === ROUTES ANALYTICS AVANCEES ===

@app.route('/api/analytics/predictions')
def api_predictions():
    """
    API pour récupérer les prévisions budgétaires
    """
    # Simulation de prédictions avec algorithme simple
    projets = manager.get_tous_projets()
    predictions = []
    
    for projet in projets:
        if projet['budget_depense'] > 0:
            # Calcul de tendance basique
            progression_rate = projet['budget_depense'] / projet['budget_alloue']
            if progression_rate > 0.8:
                risk_level = 'high'
                predicted_overspend = projet['budget_depense'] * 0.15
            elif progression_rate > 0.6:
                risk_level = 'medium'
                predicted_overspend = projet['budget_depense'] * 0.08
            else:
                risk_level = 'low'
                predicted_overspend = 0
            
            predictions.append({
                'projet_id': projet['id'],
                'projet_nom': projet['nom'],
                'risk_level': risk_level,
                'predicted_overspend': predicted_overspend,
                'completion_probability': min(100, (progression_rate * 120))
            })
    
    return jsonify({'predictions': predictions})

@app.route('/api/analytics/timeline')
def api_timeline():
    """
    API pour récupérer les données temporelles
    """
    # Simulation de données temporelles
    import datetime
    from datetime import timedelta
    
    end_date = datetime.datetime.now()
    timeline_data = []
    
    for i in range(30):  # 30 derniers jours
        date = end_date - timedelta(days=i)
        # Simulation de dépenses avec variation
        base_amount = 1000
        variation = (i % 7) * 200 + (i % 3) * 100
        amount = base_amount + variation
        
        timeline_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'amount': amount,
            'cumulative': sum([d['amount'] for d in timeline_data]) + amount
        })
    
    timeline_data.reverse()  # Ordre chronologique
    return jsonify({'timeline': timeline_data})

@app.route('/api/analytics/heatmap')
def api_heatmap():
    """
    API pour récupérer les données de heatmap
    """
    # Simulation de heatmap des dépenses par jour/catégorie
    categories = ['Formation', 'Marketing', 'Équipement', 'Frais', 'Autres']
    days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    
    heatmap_data = []
    for day_idx, day in enumerate(days):
        for cat_idx, category in enumerate(categories):
            # Simulation de valeurs
            value = ((day_idx + 1) * (cat_idx + 1) * 50) % 500
            heatmap_data.append({
                'day': day,
                'category': category,
                'value': value,
                'intensity': min(1.0, value / 500)
            })
    
    return jsonify({'heatmap': heatmap_data})

@app.route('/api/analytics/alerts')
def api_alerts():
    """
    API pour récupérer les alertes intelligentes
    """
    projets = manager.get_tous_projets()
    alerts = []
    
    for projet in projets:
        progression = (projet['budget_depense'] / projet['budget_alloue']) * 100 if projet['budget_alloue'] > 0 else 0
        
        if progression > 90:
            alerts.append({
                'type': 'danger',
                'title': 'Budget Dépassé',
                'message': f"Le projet '{projet['nom']}' a dépassé 90% de son budget.",
                'project_id': projet['id'],
                'timestamp': 'Il y a 2 heures'
            })
        elif progression > 75:
            alerts.append({
                'type': 'warning',
                'title': 'Attention Budget',
                'message': f"Le projet '{projet['nom']}' approche de la limite budgétaire.",
                'project_id': projet['id'],
                'timestamp': 'Il y a 4 heures'
            })
    
    # Ajout d'alertes positives
    if len([p for p in projets if p['budget_depense'] < p['budget_alloue'] * 0.5]) > 0:
        alerts.append({
            'type': 'success',
            'title': 'Économies Réalisées',
            'message': 'Plusieurs projets sont sous budget. Excellent travail!',
            'timestamp': 'Hier'
        })
    
    return jsonify({'alerts': alerts})

@app.route('/api/database/stats')
def api_database_stats():
    """
    API pour récupérer les statistiques de la base de données CSV
    """
    db_stats = manager.get_database_stats()
    return jsonify({
        'database_stats': db_stats,
        'persistence_type': 'CSV avec clés relationnelles',
        'tables': ['projets', 'depenses', 'comptes', 'transactions'],
        'total_records': sum(db_stats.values())
    })

@app.route('/api/analytics/kpis')
def api_kpis():
    """
    API pour récupérer les KPIs avancés
    """
    stats = manager.get_statistiques()
    projets = manager.get_tous_projets()
    
    # Calculs KPI avancés
    completed_projects = len([p for p in projets if p['budget_depense'] >= p['budget_alloue'] * 0.9])
    total_projects = len(projets)
    completion_rate = (completed_projects / total_projects * 100) if total_projects > 0 else 0
    
    risky_projects = len([p for p in projets if (p['budget_depense'] / p['budget_alloue'] * 100) > 90])
    
    # Simulation ROI
    total_investment = stats['budget_total']
    estimated_return = total_investment * 1.15  # 15% ROI simulé
    roi_percentage = 15.2
    
    kpis = {
        'monthly_trend': '+12.5%',
        'completion_rate': round(completion_rate, 1),
        'risky_projects': risky_projects,
        'avg_roi': f'+{roi_percentage}%',
        'performance_score': min(100, max(0, 100 - (risky_projects * 10) + (completion_rate * 0.5))),
        'budget_efficiency': round((stats['total_depense'] / stats['budget_total'] * 100), 1) if stats['budget_total'] > 0 else 0
    }
    
    return jsonify({'kpis': kpis})

# === NOUVEAUX ANALYTICS SIMPLIFIÉS ===

@app.route('/api/analytics/simple-stats')
def api_simple_stats():
    """
    Statistiques ultra-simples pour widgets rapides
    """
    stats = manager.get_statistiques()
    projets = manager.get_tous_projets()
    comptes = manager.get_tous_comptes_bancaires()
    
    # Indicateurs simples
    total_disponible = sum(compte['solde'] for compte in comptes)
    budget_restant = stats['total_restant']
    
    # Projet le plus/moins rentable
    if projets:
        projets_efficiency = []
        for p in projets:
            if p['budget_alloue'] > 0:
                efficiency = (p['budget_alloue'] - p['budget_depense']) / p['budget_alloue'] * 100
                projets_efficiency.append({'nom': p['nom'], 'efficiency': efficiency, 'id': p['id']})
        
        projets_efficiency.sort(key=lambda x: x['efficiency'], reverse=True)
        best_project = projets_efficiency[0] if projets_efficiency else None
        worst_project = projets_efficiency[-1] if projets_efficiency else None
    else:
        best_project = worst_project = None
    
    return jsonify({
        'total_cash': total_disponible,
        'budget_left': budget_restant,
        'projects_count': len(projets),
        'avg_spending': stats['depense_moyenne'],
        'best_project': best_project,
        'worst_project': worst_project,
        'health_score': calculate_financial_health(stats, projets, comptes)
    })

@app.route('/api/analytics/spending-velocity')
def api_spending_velocity():
    """
    Vélocité de dépenses - tendance rapide
    """
    # Simulation de données de vélocité sur 7 derniers jours
    velocity_data = []
    base_spending = 500
    
    for i in range(7):
        day_spending = base_spending + (i * 50) + ((i % 3) * 100)
        velocity_data.append({
            'day': f'J-{6-i}',
            'spending': day_spending,
            'trend': 'up' if day_spending > base_spending else 'down'
        })
    
    # Calcul tendance générale
    recent_avg = sum(d['spending'] for d in velocity_data[-3:]) / 3
    older_avg = sum(d['spending'] for d in velocity_data[:3]) / 3
    velocity_trend = 'acceleration' if recent_avg > older_avg else 'deceleration'
    
    return jsonify({
        'daily_velocity': velocity_data,
        'trend': velocity_trend,
        'weekly_total': sum(d['spending'] for d in velocity_data),
        'avg_daily': sum(d['spending'] for d in velocity_data) / 7
    })

@app.route('/api/analytics/category-breakdown')
def api_category_breakdown():
    """
    Répartition simple par catégories avec couleurs
    """
    projets = manager.get_tous_projets()
    categories = manager.get_categories()
    
    # Grouper par catégorie
    category_stats = {}
    for projet in projets:
        cat_id = projet.get('categorie_id')
        if cat_id:
            cat = next((c for c in categories if c['id'] == cat_id), None)
            if cat:
                cat_name = cat['nom']
                if cat_name not in category_stats:
                    category_stats[cat_name] = {
                        'total_budget': 0,
                        'total_spent': 0,
                        'projects_count': 0,
                        'color': cat['couleur'],
                        'efficiency': 0
                    }
                
                category_stats[cat_name]['total_budget'] += projet['budget_alloue']
                category_stats[cat_name]['total_spent'] += projet['budget_depense']
                category_stats[cat_name]['projects_count'] += 1
    
    # Calculer efficacité par catégorie
    for cat_data in category_stats.values():
        if cat_data['total_budget'] > 0:
            cat_data['efficiency'] = round(
                (cat_data['total_budget'] - cat_data['total_spent']) / cat_data['total_budget'] * 100, 1
            )
    
    return jsonify({'categories': category_stats})

@app.route('/api/analytics/financial-health')
def api_financial_health():
    """
    Score de santé financière global avec IA basique
    """
    stats = manager.get_statistiques()
    projets = manager.get_tous_projets()
    comptes = manager.get_tous_comptes_bancaires()
    
    health_score = calculate_financial_health(stats, projets, comptes)
    
    # Analyse IA simple basée sur des règles
    analysis = generate_ai_analysis(stats, projets, comptes, health_score)
    
    return jsonify({
        'health_score': health_score,
        'level': get_health_level(health_score),
        'analysis': analysis,
        'recommendations': generate_recommendations(stats, projets, health_score)
    })

@app.route('/api/analytics/cash-flow-forecast')
def api_cash_flow_forecast():
    """
    Prévision de trésorerie simple sur 3 mois
    """
    stats = manager.get_statistiques()
    comptes = manager.get_tous_comptes_bancaires()
    
    current_cash = sum(compte['solde'] for compte in comptes)
    monthly_burn = stats['total_depense'] / max(stats['nombre_projets'], 1)  # Burn rate estimé
    
    forecast = []
    for month in range(1, 4):
        projected_cash = current_cash - (monthly_burn * month)
        runway_months = current_cash / monthly_burn if monthly_burn > 0 else float('inf')
        
        forecast.append({
            'month': f'M+{month}',
            'projected_cash': max(0, projected_cash),
            'runway_status': 'safe' if projected_cash > 0 else 'warning',
            'runway_months': round(runway_months, 1) if runway_months != float('inf') else 'infinite'
        })
    
    return jsonify({
        'current_cash': current_cash,
        'monthly_burn': monthly_burn,
        'forecast': forecast,
        'runway_alert': runway_months < 6 if runway_months != float('inf') else False
    })

@app.route('/api/analytics/project-efficiency')
def api_project_efficiency():
    """
    Efficacité comparative des projets
    """
    projets = manager.get_tous_projets()
    
    efficiency_data = []
    for projet in projets:
        if projet['budget_alloue'] > 0:
            spent_ratio = projet['budget_depense'] / projet['budget_alloue']
            remaining_ratio = 1 - spent_ratio
            
            # Score d'efficacité simple
            if spent_ratio <= 0.7:
                efficiency_level = 'excellent'
                score = 90 + (remaining_ratio * 10)
            elif spent_ratio <= 0.9:
                efficiency_level = 'good'
                score = 70 + (remaining_ratio * 20)
            else:
                efficiency_level = 'warning'
                score = max(10, 60 - (spent_ratio * 50))
            
            efficiency_data.append({
                'id': projet['id'],
                'nom': projet['nom'],
                'budget_alloue': projet['budget_alloue'],
                'budget_depense': projet['budget_depense'],
                'spent_ratio': round(spent_ratio * 100, 1),
                'efficiency_score': round(score, 1),
                'efficiency_level': efficiency_level,
                'categorie': projet.get('categorie', 'Non catégorisé'),
                'categorie_couleur': projet.get('categorie_couleur', '#6b7280')
            })
    
    # Trier par efficacité
    efficiency_data.sort(key=lambda x: x['efficiency_score'], reverse=True)
    
    return jsonify({
        'projects': efficiency_data,
        'avg_efficiency': sum(p['efficiency_score'] for p in efficiency_data) / len(efficiency_data) if efficiency_data else 0
    })


# === WIDGETS DASHBOARD SIMPLIFIÉ ===

@app.route('/api/widgets/quick-numbers')
def api_quick_numbers():
    """
    Nombres rapides pour affichage widget
    """
    stats = manager.get_statistiques()
    projets = manager.get_tous_projets()
    comptes = manager.get_tous_comptes_bancaires()
    
    # Calculs ultra-rapides
    total_cash = sum(compte['solde'] for compte in comptes)
    projects_on_track = len([p for p in projets if p['budget_depense'] / p['budget_alloue'] <= 0.8])
    avg_project_size = stats['budget_moyen']
    
    return jsonify({
        'total_budget': stats['budget_total'],
        'spent_today': stats['total_depense'],  # Simulation
        'cash_available': total_cash,
        'projects_count': len(projets),
        'projects_on_track': projects_on_track,
        'avg_project_size': avg_project_size,
        'burn_rate': stats['depense_moyenne']
    })

@app.route('/api/widgets/status-indicators')
def api_status_indicators():
    """
    Indicateurs de statut visuels simples
    """
    stats = manager.get_statistiques()
    projets = manager.get_tous_projets()
    comptes = manager.get_tous_comptes_bancaires()
    
    # Status budget global
    if stats['pourcentage_utilise'] > 90:
        budget_status = {'level': 'danger', 'message': 'Budget critique', 'icon': '🚨'}
    elif stats['pourcentage_utilise'] > 75:
        budget_status = {'level': 'warning', 'message': 'Attention budget', 'icon': '⚠️'}
    else:
        budget_status = {'level': 'success', 'message': 'Budget sain', 'icon': '✅'}
    
    # Status cash-flow
    total_cash = sum(compte['solde'] for compte in comptes)
    monthly_burn = stats['total_depense'] / max(len(projets), 1)
    months_runway = total_cash / monthly_burn if monthly_burn > 0 else 12
    
    if months_runway < 3:
        cash_status = {'level': 'danger', 'message': 'Trésorerie critique', 'icon': '💸', 'months': months_runway}
    elif months_runway < 6:
        cash_status = {'level': 'warning', 'message': 'Attention trésorerie', 'icon': '💰', 'months': months_runway}
    else:
        cash_status = {'level': 'success', 'message': 'Trésorerie confortable', 'icon': '💎', 'months': months_runway}
    
    # Status projets
    risky_projects = len([p for p in projets if p['budget_depense'] / p['budget_alloue'] > 0.9])
    if risky_projects > len(projets) / 2:
        projects_status = {'level': 'danger', 'message': f'{risky_projects} projets à risque', 'icon': '📊'}
    elif risky_projects > 0:
        projects_status = {'level': 'warning', 'message': f'{risky_projects} projet(s) à surveiller', 'icon': '📈'}
    else:
        projects_status = {'level': 'success', 'message': 'Tous projets sous contrôle', 'icon': '🎯'}
    
    return jsonify({
        'budget_status': budget_status,
        'cash_status': cash_status,
        'projects_status': projects_status,
        'last_update': datetime.now().strftime('%H:%M')
    })

@app.route('/api/widgets/trending')
def api_trending():
    """
    Tendances simples pour widgets
    """
    stats = manager.get_statistiques()
    projets = manager.get_tous_projets()
    
    # Simulation de tendances (en production, utiliser vraies données historiques)
    trends = {
        'spending_trend': {
            'value': '+12%',
            'direction': 'up',
            'color': 'red',
            'description': 'vs mois dernier'
        },
        'efficiency_trend': {
            'value': '+5%',
            'direction': 'up', 
            'color': 'green',
            'description': 'efficacité projets'
        },
        'cash_trend': {
            'value': '-3%',
            'direction': 'down',
            'color': 'orange',
            'description': 'réserves liquides'
        }
    }
    
    # Top/Bottom performers
    if projets:
        performers = []
        for p in projets:
            if p['budget_alloue'] > 0:
                efficiency = (1 - p['budget_depense'] / p['budget_alloue']) * 100
                performers.append({
                    'nom': p['nom'],
                    'efficiency': round(efficiency, 1),
                    'spent': p['budget_depense'],
                    'categorie_couleur': p.get('categorie_couleur', '#6b7280')
                })
        
        performers.sort(key=lambda x: x['efficiency'], reverse=True)
        top_performer = performers[0] if performers else None
        bottom_performer = performers[-1] if len(performers) > 1 else None
    else:
        top_performer = bottom_performer = None
    
    return jsonify({
        'trends': trends,
        'top_performer': top_performer,
        'bottom_performer': bottom_performer
    })

@app.route('/api/widgets/alerts-summary')
def api_alerts_summary():
    """
    Résumé d'alertes ultra-simple
    """
    stats = manager.get_statistiques()
    projets = manager.get_tous_projets()
    comptes = manager.get_tous_comptes_bancaires()
    
    alerts = []
    
    # Alerte budget global
    if stats['pourcentage_utilise'] > 85:
        alerts.append({
            'type': 'budget',
            'severity': 'high' if stats['pourcentage_utilise'] > 95 else 'medium',
            'message': f"Budget utilisé à {stats['pourcentage_utilise']:.1f}%",
            'action': 'Réviser allocation'
        })
    
    # Alerte projets à risque
    risky_count = len([p for p in projets if p['budget_depense'] / p['budget_alloue'] > 0.9])
    if risky_count > 0:
        alerts.append({
            'type': 'projects',
            'severity': 'medium',
            'message': f"{risky_count} projet(s) proche(s) de la limite",
            'action': 'Contrôler dépenses'
        })
    
    # Alerte trésorerie
    total_cash = sum(compte['solde'] for compte in comptes)
    if total_cash < stats['total_depense']:
        alerts.append({
            'type': 'cash',
            'severity': 'high',
            'message': "Trésorerie inférieure aux dépenses",
            'action': 'Améliorer cash-flow'
        })
    
    # Opportunités
    efficient_projects = [p for p in projets if p['budget_depense'] / p['budget_alloue'] < 0.5]
    if len(efficient_projects) > 0:
        alerts.append({
            'type': 'opportunity',
            'severity': 'info',
            'message': f"{len(efficient_projects)} projet(s) sous-utilisé(s)",
            'action': 'Augmenter investissement'
        })
    
    return jsonify({
        'alerts_count': len([a for a in alerts if a['severity'] in ['high', 'medium']]),
        'opportunities_count': len([a for a in alerts if a['severity'] == 'info']),
        'alerts': alerts[:5]  # Limite à 5 alertes
    })

@app.route('/api/widgets/mini-charts')
def api_mini_charts():
    """
    Données pour mini-graphiques ultra-simples
    """
    projets = manager.get_tous_projets()
    categories = manager.get_categories()
    
    # Répartition budget par catégorie (pour pie chart)
    category_distribution = {}
    for projet in projets:
        cat_id = projet.get('categorie_id')
        if cat_id:
            cat = next((c for c in categories if c['id'] == cat_id), None)
            if cat:
                cat_name = cat['nom']
                if cat_name not in category_distribution:
                    category_distribution[cat_name] = {
                        'budget': 0,
                        'color': cat['couleur']
                    }
                category_distribution[cat_name]['budget'] += projet['budget_alloue']
    
    # Évolution des dépenses (simulation pour demo)
    spending_evolution = []
    base = 1000
    for i in range(7):
        spending_evolution.append({
            'day': f'J{i+1}',
            'amount': base + (i * 150) + ((i % 3) * 200)
        })
    
    # Efficacité par projet (pour bar chart)
    efficiency_data = []
    for projet in projets[:5]:  # Top 5 projets
        if projet['budget_alloue'] > 0:
            efficiency = ((projet['budget_alloue'] - projet['budget_depense']) / projet['budget_alloue']) * 100
            efficiency_data.append({
                'name': projet['nom'][:15] + '...' if len(projet['nom']) > 15 else projet['nom'],
                'efficiency': round(max(0, efficiency), 1),
                'color': projet.get('categorie_couleur', '#6b7280')
            })
    
    return jsonify({
        'category_pie': [
            {'name': name, 'value': data['budget'], 'color': data['color']} 
            for name, data in category_distribution.items()
        ],
        'spending_line': spending_evolution,
        'efficiency_bar': efficiency_data
    })

@app.route('/api/analytics/burn-rate')
def api_burn_rate():
    """
    API pour le taux de burn rate détaillé
    """
    stats = manager.get_statistiques()
    projets = manager.get_tous_projets()
    comptes = manager.get_tous_comptes_bancaires()

    total_cash = sum(compte['solde'] for compte in comptes)

    # Burn rate mensuel (estimation basée sur les dépenses actuelles)
    monthly_burn = stats['total_depense'] / max(stats['nombre_projets'], 1)
    daily_burn = monthly_burn / 30
    weekly_burn = daily_burn * 7

    # Runway en mois
    runway_months = total_cash / monthly_burn if monthly_burn > 0 else float('inf')

    # Tendance du burn rate (simulation basée sur progression)
    burn_trend = 'stable'
    if stats['pourcentage_utilise'] > 70:
        burn_trend = 'increasing'
    elif stats['pourcentage_utilise'] < 40:
        burn_trend = 'decreasing'

    return jsonify({
        'daily_burn': round(daily_burn, 2),
        'weekly_burn': round(weekly_burn, 2),
        'monthly_burn': round(monthly_burn, 2),
        'runway_months': round(runway_months, 1) if runway_months != float('inf') else 999,
        'runway_days': round(runway_months * 30, 0) if runway_months != float('inf') else 9999,
        'burn_trend': burn_trend,
        'burn_rate_percentage': round((monthly_burn / total_cash * 100), 1) if total_cash > 0 else 0,
        'sustainability_score': min(100, max(0, runway_months * 10)) if runway_months != float('inf') else 100
    })


@app.route('/api/analytics/variance')
def api_variance():
    """
    API pour l'analyse de variance budgétaire
    """
    projets = manager.get_tous_projets()

    variance_data = []
    total_planned = 0
    total_actual = 0

    for projet in projets:
        budget = projet['budget_alloue']
        spent = projet['budget_depense']

        # Calcul de ce qui était prévu à ce stade (simulation linéaire)
        # En production, utiliser les dates réelles du projet
        expected_at_this_point = budget * 0.6  # Estimation 60% du temps écoulé

        variance_amount = expected_at_this_point - spent
        variance_percentage = (variance_amount / expected_at_this_point * 100) if expected_at_this_point > 0 else 0

        status = 'on_track'
        if variance_percentage < -20:
            status = 'over_budget'
        elif variance_percentage < -5:
            status = 'at_risk'
        elif variance_percentage > 20:
            status = 'under_budget'

        variance_data.append({
            'projet_id': projet['id'],
            'projet_nom': projet['nom'],
            'budget_total': budget,
            'budget_spent': spent,
            'expected_spent': round(expected_at_this_point, 2),
            'variance_amount': round(variance_amount, 2),
            'variance_percentage': round(variance_percentage, 1),
            'status': status,
            'categorie': projet.get('categorie', 'Non catégorisé'),
            'categorie_couleur': projet.get('categorie_couleur', '#6b7280')
        })

        total_planned += expected_at_this_point
        total_actual += spent

    global_variance = total_planned - total_actual
    global_variance_pct = (global_variance / total_planned * 100) if total_planned > 0 else 0

    return jsonify({
        'projects': variance_data,
        'global_variance': round(global_variance, 2),
        'global_variance_percentage': round(global_variance_pct, 1),
        'over_budget_count': len([v for v in variance_data if v['status'] == 'over_budget']),
        'at_risk_count': len([v for v in variance_data if v['status'] == 'at_risk']),
        'on_track_count': len([v for v in variance_data if v['status'] == 'on_track']),
        'under_budget_count': len([v for v in variance_data if v['status'] == 'under_budget'])
    })


@app.route('/api/analytics/roi-by-category')
def api_roi_by_category():
    """
    API pour le ROI par catégorie
    """
    projets = manager.get_tous_projets()
    categories = manager.get_categories()

    category_roi = {}

    for projet in projets:
        cat_id = projet.get('categorie_id')
        if cat_id:
            cat = next((c for c in categories if c['id'] == cat_id), None)
            if cat:
                cat_name = cat['nom']
                if cat_name not in category_roi:
                    category_roi[cat_name] = {
                        'invested': 0,
                        'spent': 0,
                        'projects_count': 0,
                        'color': cat['couleur'],
                        'efficiency_sum': 0
                    }

                category_roi[cat_name]['invested'] += projet['budget_alloue']
                category_roi[cat_name]['spent'] += projet['budget_depense']
                category_roi[cat_name]['projects_count'] += 1

                # Efficacité du projet
                if projet['budget_alloue'] > 0:
                    efficiency = (projet['budget_alloue'] - projet['budget_depense']) / projet['budget_alloue'] * 100
                    category_roi[cat_name]['efficiency_sum'] += efficiency

    # Calcul du ROI estimé par catégorie
    roi_data = []
    for cat_name, data in category_roi.items():
        avg_efficiency = data['efficiency_sum'] / data['projects_count'] if data['projects_count'] > 0 else 0

        # ROI simulé basé sur l'efficacité (en production, utiliser données réelles)
        estimated_roi = 10 + (avg_efficiency * 0.15)  # Base 10% + bonus efficacité

        roi_data.append({
            'category': cat_name,
            'color': data['color'],
            'invested': data['invested'],
            'spent': data['spent'],
            'remaining': data['invested'] - data['spent'],
            'projects_count': data['projects_count'],
            'avg_efficiency': round(avg_efficiency, 1),
            'estimated_roi': round(estimated_roi, 1),
            'roi_status': 'excellent' if estimated_roi > 20 else ('good' if estimated_roi > 10 else 'low')
        })

    # Trier par ROI
    roi_data.sort(key=lambda x: x['estimated_roi'], reverse=True)

    return jsonify({
        'categories': roi_data,
        'best_performer': roi_data[0] if roi_data else None,
        'worst_performer': roi_data[-1] if len(roi_data) > 1 else None,
        'avg_roi': round(sum(c['estimated_roi'] for c in roi_data) / len(roi_data), 1) if roi_data else 0
    })


@app.route('/api/analytics/pareto')
def api_pareto():
    """
    API pour l'analyse Pareto (80/20) des dépenses
    """
    projets = manager.get_tous_projets()

    # Trier les projets par dépenses (décroissant)
    projets_sorted = sorted(projets, key=lambda x: x['budget_depense'], reverse=True)

    total_spent = sum(p['budget_depense'] for p in projets)

    pareto_data = []
    cumulative_spent = 0
    cumulative_percentage = 0

    for i, projet in enumerate(projets_sorted):
        cumulative_spent += projet['budget_depense']
        cumulative_percentage = (cumulative_spent / total_spent * 100) if total_spent > 0 else 0

        pareto_data.append({
            'rank': i + 1,
            'projet_id': projet['id'],
            'projet_nom': projet['nom'],
            'spent': projet['budget_depense'],
            'percentage_of_total': round((projet['budget_depense'] / total_spent * 100), 1) if total_spent > 0 else 0,
            'cumulative_spent': cumulative_spent,
            'cumulative_percentage': round(cumulative_percentage, 1),
            'is_top_80': cumulative_percentage <= 80,
            'categorie': projet.get('categorie', 'Non catégorisé'),
            'categorie_couleur': projet.get('categorie_couleur', '#6b7280')
        })

    # Identifier les projets qui représentent 80% des dépenses
    top_80_projects = [p for p in pareto_data if p['is_top_80']]

    return jsonify({
        'pareto': pareto_data,
        'total_spent': total_spent,
        'top_80_count': len(top_80_projects),
        'top_80_percentage': round(len(top_80_projects) / len(projets) * 100, 1) if projets else 0,
        'pareto_ratio': f"{len(top_80_projects)}/{len(projets)}",
        'concentration_score': round(100 - (len(top_80_projects) / len(projets) * 100), 1) if projets else 0
    })


@app.route('/api/analytics/comparison')
def api_comparison():
    """
    API pour la comparaison période sur période
    """
    stats = manager.get_statistiques()
    projets = manager.get_tous_projets()

    # Simulation de données comparatives (en production, utiliser historique réel)
    current_period = {
        'total_budget': stats['budget_total'],
        'total_spent': stats['total_depense'],
        'projects_count': len(projets),
        'avg_efficiency': round(sum(
            (p['budget_alloue'] - p['budget_depense']) / p['budget_alloue'] * 100
            for p in projets if p['budget_alloue'] > 0
        ) / len(projets), 1) if projets else 0
    }

    # Période précédente simulée (en production, calculer à partir de l'historique)
    previous_period = {
        'total_budget': current_period['total_budget'] * 0.85,
        'total_spent': current_period['total_spent'] * 0.78,
        'projects_count': max(1, current_period['projects_count'] - 2),
        'avg_efficiency': current_period['avg_efficiency'] * 0.92
    }

    # Calcul des variations
    def calc_change(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round((current - previous) / previous * 100, 1)

    comparison = {
        'current_period': current_period,
        'previous_period': previous_period,
        'changes': {
            'budget_change': calc_change(current_period['total_budget'], previous_period['total_budget']),
            'spent_change': calc_change(current_period['total_spent'], previous_period['total_spent']),
            'projects_change': current_period['projects_count'] - previous_period['projects_count'],
            'efficiency_change': round(current_period['avg_efficiency'] - previous_period['avg_efficiency'], 1)
        },
        'trends': {
            'budget': 'up' if current_period['total_budget'] > previous_period['total_budget'] else 'down',
            'spent': 'up' if current_period['total_spent'] > previous_period['total_spent'] else 'down',
            'efficiency': 'up' if current_period['avg_efficiency'] > previous_period['avg_efficiency'] else 'down'
        }
    }

    return jsonify(comparison)


@app.route('/api/analytics/budget-vs-actuals')
def api_budget_vs_actuals():
    """
    API pour Budget vs Réel par projet
    """
    projets = manager.get_tous_projets()

    bva_data = []
    for projet in projets:
        budget = projet['budget_alloue']
        actual = projet['budget_depense']
        variance = budget - actual
        variance_pct = (variance / budget * 100) if budget > 0 else 0

        # Statut basé sur la variance
        if variance_pct < -10:
            status = 'over'
            status_label = 'Dépassement'
        elif variance_pct < 0:
            status = 'slight_over'
            status_label = 'Léger dépassement'
        elif variance_pct < 20:
            status = 'on_track'
            status_label = 'Dans les clous'
        else:
            status = 'under'
            status_label = 'Sous budget'

        bva_data.append({
            'projet_id': projet['id'],
            'projet_nom': projet['nom'],
            'budget': budget,
            'actual': actual,
            'variance': round(variance, 2),
            'variance_percentage': round(variance_pct, 1),
            'completion': round((actual / budget * 100), 1) if budget > 0 else 0,
            'status': status,
            'status_label': status_label,
            'categorie': projet.get('categorie', 'Non catégorisé'),
            'categorie_couleur': projet.get('categorie_couleur', '#6b7280')
        })

    # Totaux
    total_budget = sum(p['budget'] for p in bva_data)
    total_actual = sum(p['actual'] for p in bva_data)

    return jsonify({
        'projects': bva_data,
        'summary': {
            'total_budget': total_budget,
            'total_actual': total_actual,
            'total_variance': round(total_budget - total_actual, 2),
            'overall_completion': round((total_actual / total_budget * 100), 1) if total_budget > 0 else 0
        },
        'counts': {
            'over': len([p for p in bva_data if p['status'] == 'over']),
            'slight_over': len([p for p in bva_data if p['status'] == 'slight_over']),
            'on_track': len([p for p in bva_data if p['status'] == 'on_track']),
            'under': len([p for p in bva_data if p['status'] == 'under'])
        }
    })


@app.route('/api/analytics/consolidated-kpis')
def api_consolidated_kpis():
    """
    API pour tous les KPIs consolidés en une seule requête
    """
    stats = manager.get_statistiques()
    projets = manager.get_tous_projets()
    comptes = manager.get_tous_comptes_bancaires()

    total_cash = sum(compte['solde'] for compte in comptes)
    monthly_burn = stats['total_depense'] / max(stats['nombre_projets'], 1)
    runway_months = total_cash / monthly_burn if monthly_burn > 0 else float('inf')

    # Calculs avancés
    efficient_projects = len([p for p in projets if p['budget_alloue'] > 0 and p['budget_depense'] / p['budget_alloue'] < 0.7])
    risky_projects = len([p for p in projets if p['budget_alloue'] > 0 and p['budget_depense'] / p['budget_alloue'] > 0.9])

    health_score = calculate_financial_health(stats, projets, comptes)

    return jsonify({
        'financial': {
            'total_budget': stats['budget_total'],
            'total_spent': stats['total_depense'],
            'total_remaining': stats['total_restant'],
            'total_cash': total_cash,
            'monthly_burn': round(monthly_burn, 2),
            'runway_months': round(runway_months, 1) if runway_months != float('inf') else 999
        },
        'efficiency': {
            'budget_utilization': round(stats['pourcentage_utilise'], 1),
            'efficient_projects': efficient_projects,
            'risky_projects': risky_projects,
            'health_score': health_score,
            'avg_project_efficiency': round(sum(
                (1 - p['budget_depense'] / p['budget_alloue']) * 100
                for p in projets if p['budget_alloue'] > 0
            ) / len(projets), 1) if projets else 0
        },
        'portfolio': {
            'total_projects': len(projets),
            'active_accounts': len(comptes),
            'avg_project_size': round(stats['budget_moyen'], 2),
            'largest_project': max(projets, key=lambda x: x['budget_alloue'])['nom'] if projets else None,
            'most_spent': max(projets, key=lambda x: x['budget_depense'])['nom'] if projets else None
        },
        'risk': {
            'over_budget_count': stats['projets_en_depassement'],
            'at_risk_count': risky_projects,
            'cash_coverage_ratio': round(total_cash / stats['total_depense'], 2) if stats['total_depense'] > 0 else 999,
            'concentration_risk': round(max(p['budget_alloue'] for p in projets) / stats['budget_total'] * 100, 1) if projets and stats['budget_total'] > 0 else 0
        }
    })


@app.route('/api/dashboard/layout', methods=['GET', 'POST'])
@require_auth
def api_dashboard_layout():
    """
    API pour sauvegarder/charger la configuration du dashboard
    """
    user_email = session.get('user_email', 'default')
    layout_file = f'data/dashboard_layouts.csv'

    if request.method == 'POST':
        # Sauvegarder la configuration
        layout_data = request.json

        try:
            import csv
            import os

            # Lire les layouts existants
            layouts = {}
            if os.path.exists(layout_file):
                with open(layout_file, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        layouts[row['user_email']] = row['layout']

            # Mettre à jour le layout de l'utilisateur
            import json
            layouts[user_email] = json.dumps(layout_data)

            # Écrire tous les layouts
            with open(layout_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['user_email', 'layout'])
                writer.writeheader()
                for email, layout in layouts.items():
                    writer.writerow({'user_email': email, 'layout': layout})

            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    else:
        # Charger la configuration
        try:
            import csv
            import os
            import json

            if os.path.exists(layout_file):
                with open(layout_file, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['user_email'] == user_email:
                            return jsonify({'layout': json.loads(row['layout'])})

            # Layout par défaut
            return jsonify({'layout': None})
        except Exception as e:
            return jsonify({'layout': None, 'error': str(e)})


@app.route('/dashboard-analytics')
@require_auth
def dashboard_analytics():
    """
    Page dashboard analytics simplifiée
    """

    user_data = {
        'name': session.get('user_name', 'User'),
        'avatar': session.get('user_avatar', 'U'),
        'email': session.get('user_email', '')
    }

    return render_template('analytics_dashboard.html', user=user_data)

@app.route('/api/export/pdf')
def export_pdf():
    """
    API pour exporter les analytics en PDF
    """
    try:
        # Génération du rapport avec les données actuelles
        stats = manager.get_statistiques()
        projets = manager.get_tous_projets()
        comptes = manager.get_tous_comptes_bancaires()
        report_content = generate_analytics_report(stats, projets, comptes)
        
        # Création d'un buffer en mémoire
        buffer = io.BytesIO()
        buffer.write(report_content.encode('utf-8'))
        buffer.seek(0)
        
        filename = f"analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain'
        )
    except Exception as e:
        return jsonify({'error': f'Erreur lors de l\'export: {str(e)}'}), 500


# === ROUTES INTÉGRATION CRÉDIT AGRICOLE ===

@app.route('/api/ca/status')
@require_auth
def api_ca_status():
    """
    Vérifie le statut de connexion au Crédit Agricole
    """
    ca_service = get_credit_agricole_service()
    if not ca_service:
        return jsonify({
            'enabled': False,
            'message': 'Intégration Crédit Agricole non configurée'
        })

    user_email = session.get('user_email')
    status = ca_service.get_connection_status(user_email)
    status['enabled'] = True

    return jsonify(status)


@app.route('/api/ca/connect')
@require_auth
def api_ca_connect():
    """
    Initie la connexion OAuth2 avec le Crédit Agricole
    Redirige vers la page d'autorisation de la banque
    """
    ca_service = get_credit_agricole_service()
    if not ca_service:
        return jsonify({
            'success': False,
            'error': 'Intégration Crédit Agricole non configurée'
        }), 400

    user_email = session.get('user_email')

    try:
        auth_data = ca_service.build_authorize_url(
            user_id=user_email,
            scopes=['openid', 'profile', 'accounts', 'transactions']
        )

        # Stocker le state en session pour vérification
        session['ca_oauth_state'] = auth_data['state']

        logger.info(f"Redirection OAuth2 CA pour {user_email}")
        return redirect(auth_data['url'])

    except Exception as e:
        logger.error(f"Erreur lors de l'initiation OAuth2 CA: {e}")
        return jsonify({
            'success': False,
            'error': 'Erreur lors de la connexion'
        }), 500


@app.route('/api/ca/callback')
def api_ca_callback():
    """
    Callback OAuth2 du Crédit Agricole
    Reçoit le code d'autorisation et l'échange contre des tokens
    """
    ca_service = get_credit_agricole_service()
    if not ca_service:
        return redirect(url_for('index') + '?ca_error=not_configured')

    # Récupérer les paramètres
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    error_description = request.args.get('error_description')

    # Vérifier les erreurs OAuth
    if error:
        logger.error(f"Erreur OAuth2 CA: {error} - {error_description}")
        return redirect(url_for('index') + f'?ca_error={error}')

    # Vérifier le state
    expected_state = session.get('ca_oauth_state')
    if not state or state != expected_state:
        logger.error("State OAuth2 invalide")
        return redirect(url_for('index') + '?ca_error=invalid_state')

    try:
        # Échanger le code contre des tokens
        result = ca_service.exchange_code_for_token(code, state)

        # Nettoyer le state de la session
        session.pop('ca_oauth_state', None)

        logger.info(f"Connexion CA réussie pour {result['user_id']}")
        return redirect(url_for('index') + '?ca_connected=true')

    except CreditAgricoleError as e:
        logger.error(f"Erreur échange token CA: {e}")
        return redirect(url_for('index') + f'?ca_error={e.error_code}')
    except Exception as e:
        logger.error(f"Erreur inattendue callback CA: {e}")
        return redirect(url_for('index') + '?ca_error=unknown')


@app.route('/api/ca/disconnect', methods=['POST'])
@require_auth
def api_ca_disconnect():
    """
    Déconnecte l'utilisateur du Crédit Agricole
    """
    ca_service = get_credit_agricole_service()
    if not ca_service:
        return jsonify({'success': False, 'error': 'Service non configuré'}), 400

    user_email = session.get('user_email')
    success = ca_service.disconnect(user_email)

    return jsonify({
        'success': success,
        'message': 'Déconnecté du Crédit Agricole' if success else 'Non connecté'
    })


@app.route('/api/ca/accounts')
@require_auth
def api_ca_accounts():
    """
    Récupère les comptes bancaires depuis le Crédit Agricole
    """
    ca_service = get_credit_agricole_service()
    if not ca_service:
        return jsonify({'success': False, 'error': 'Service non configuré'}), 400

    user_email = session.get('user_email')

    if not ca_service.is_connected(user_email):
        return jsonify({
            'success': False,
            'error': 'Non connecté au Crédit Agricole',
            'redirect': '/api/ca/connect'
        }), 401

    try:
        accounts = ca_service.get_accounts(user_email)
        return jsonify({
            'success': True,
            'accounts': accounts,
            'count': len(accounts)
        })
    except CreditAgricoleError as e:
        logger.error(f"Erreur récupération comptes CA: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_code': e.error_code
        }), 500


@app.route('/api/ca/accounts/<account_id>/transactions')
@require_auth
def api_ca_transactions(account_id):
    """
    Récupère les transactions d'un compte Crédit Agricole
    """
    ca_service = get_credit_agricole_service()
    if not ca_service:
        return jsonify({'success': False, 'error': 'Service non configuré'}), 400

    user_email = session.get('user_email')

    if not ca_service.is_connected(user_email):
        return jsonify({
            'success': False,
            'error': 'Non connecté au Crédit Agricole'
        }), 401

    # Paramètres optionnels de filtrage par date
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    try:
        transactions = ca_service.get_transactions(
            user_email, account_id, date_from, date_to
        )
        return jsonify({
            'success': True,
            'transactions': transactions,
            'count': len(transactions)
        })
    except CreditAgricoleError as e:
        logger.error(f"Erreur récupération transactions CA: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_code': e.error_code
        }), 500


@app.route('/api/ca/sync', methods=['POST'])
@require_auth
@performance_monitor('ca_sync')
def api_ca_sync():
    """
    Synchronise les comptes et transactions CA avec FLOOSE
    Importe automatiquement les comptes et leurs transactions récentes
    """
    ca_service = get_credit_agricole_service()
    if not ca_service:
        return jsonify({'success': False, 'error': 'Service non configuré'}), 400

    user_email = session.get('user_email')

    if not ca_service.is_connected(user_email):
        return jsonify({
            'success': False,
            'error': 'Non connecté au Crédit Agricole'
        }), 401

    try:
        # Récupérer les comptes CA
        ca_accounts = ca_service.get_accounts(user_email)

        synced_accounts = []
        synced_transactions = 0

        for ca_account in ca_accounts:
            # Vérifier si le compte existe déjà dans FLOOSE (par IBAN)
            existing = None
            for compte in manager.get_tous_comptes_bancaires():
                if compte.get('iban') == ca_account.get('iban'):
                    existing = compte
                    break

            if not existing:
                # Créer le compte dans FLOOSE
                nouveau_compte = manager.ajouter_compte_bancaire(
                    nom=ca_account['nom'],
                    banque=ca_account['banque'],
                    solde_initial=ca_account['solde'],
                    type_compte=ca_account['type']
                )
                if nouveau_compte:
                    synced_accounts.append({
                        'nom': ca_account['nom'],
                        'action': 'créé',
                        'solde': ca_account['solde']
                    })
            else:
                # Mettre à jour le solde si différent
                if existing.get('solde') != ca_account['solde']:
                    # Calculer la différence et créer une transaction d'ajustement
                    diff = ca_account['solde'] - existing.get('solde', 0)
                    if diff != 0:
                        operation_type = 'crédit' if diff > 0 else 'débit'
                        manager.effectuer_operation_bancaire(
                            existing['id'],
                            abs(diff),
                            'Synchronisation Crédit Agricole',
                            operation_type
                        )
                        synced_accounts.append({
                            'nom': ca_account['nom'],
                            'action': 'mis à jour',
                            'ajustement': diff
                        })

            # Récupérer les transactions récentes (30 derniers jours)
            from datetime import timedelta
            date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

            try:
                transactions = ca_service.get_transactions(
                    user_email,
                    ca_account['id_externe'],
                    date_from=date_from
                )
                synced_transactions += len(transactions)
            except Exception as e:
                logger.warning(f"Impossible de récupérer les transactions pour {ca_account['nom']}: {e}")

        logger.info(f"Synchronisation CA terminée: {len(synced_accounts)} comptes, {synced_transactions} transactions")

        return jsonify({
            'success': True,
            'synced_accounts': synced_accounts,
            'total_transactions': synced_transactions,
            'message': f'Synchronisation réussie: {len(synced_accounts)} compte(s)'
        })

    except CreditAgricoleError as e:
        logger.error(f"Erreur synchronisation CA: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_code': e.error_code
        }), 500
    except Exception as e:
        logger.error(f"Erreur inattendue synchronisation CA: {e}")
        return jsonify({
            'success': False,
            'error': 'Erreur lors de la synchronisation'
        }), 500


@app.route('/api/ca/userinfo')
@require_auth
def api_ca_userinfo():
    """
    Récupère les informations de l'utilisateur connecté au CA
    """
    ca_service = get_credit_agricole_service()
    if not ca_service:
        return jsonify({'success': False, 'error': 'Service non configuré'}), 400

    user_email = session.get('user_email')

    if not ca_service.is_connected(user_email):
        return jsonify({
            'success': False,
            'error': 'Non connecté au Crédit Agricole'
        }), 401

    try:
        userinfo = ca_service.get_user_info(user_email)
        return jsonify({
            'success': True,
            'userinfo': userinfo
        })
    except CreditAgricoleError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# === ROUTES D'ADMINISTRATION ET DE MONITORING ===

@app.route('/admin/stats')
@require_auth
def admin_stats():
    """
    Statistiques d'administration (performance, cache, etc.)
    """
    current_user = get_current_user()
    if not current_user or 'admin' not in current_user.get('email', ''):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    # Récupérer les statistiques
    performance_stats = perf_manager.get_performance_stats()
    lock_stats = get_lock_manager().get_lock_stats()
    app_info = get_app_info()
    db_stats = manager.get_database_stats()
    
    stats = {
        'app_info': app_info,
        'performance': performance_stats,
        'file_locks': lock_stats,
        'database': db_stats,
        'timestamp': datetime.now().isoformat()
    }
    
    return jsonify(stats)

@app.route('/api/health')
def health_check():
    """
    Point de contrôle de santé de l'application
    """
    try:
        # Vérifications de base
        db_stats = manager.get_database_stats()
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': get_app_info()['version'],
            'database_records': sum(db_stats.values()),
            'cache_size': perf_manager.file_cache.get_stats()['size']
        }
        return jsonify(health_status)
    except Exception as e:
        logger.error(f"Erreur lors du health check: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


# ============================================================================
# API IA - MISTRAL KPI GENERATION
# ============================================================================

@app.route('/api/ai/generate-kpi', methods=['POST'])
@require_auth
def api_ai_generate_kpi():
    """
    Génère une configuration KPI à partir d'un prompt en langage naturel via Mistral API.

    Request body:
    {
        "prompt": "Description du KPI souhaité en langage naturel",
        "system_prompt": "Instructions système (optionnel)",
        "user_prompt_template": "Template du prompt utilisateur (optionnel)"
    }

    Response:
    {
        "content": "JSON string de la configuration KPI",
        "model": "mistral-small-latest",
        "usage": {...}
    }
    """
    import os
    import requests

    data = request.get_json()
    if not data or not data.get('prompt'):
        return jsonify({'error': 'Le champ "prompt" est requis'}), 400

    user_prompt = data['prompt'].strip()
    if len(user_prompt) < 3:
        return jsonify({'error': 'Le prompt est trop court'}), 400

    if len(user_prompt) > 2000:
        return jsonify({'error': 'Le prompt est trop long (max 2000 caractères)'}), 400

    # Configuration Mistral API
    mistral_api_key = os.environ.get('MISTRAL_API_KEY')
    if not mistral_api_key:
        logger.warning("MISTRAL_API_KEY non configurée, utilisation du mode simulation")
        # Mode simulation pour développement
        return _simulate_mistral_response(user_prompt)

    # System prompt
    system_prompt = data.get('system_prompt', _get_default_system_prompt())

    # User prompt template
    user_prompt_template = data.get('user_prompt_template', 'Demande: "{USER_PROMPT}"')
    full_user_prompt = user_prompt_template.replace('{USER_PROMPT}', user_prompt)

    try:
        # Appel à l'API Mistral
        response = requests.post(
            'https://api.mistral.ai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {mistral_api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'mistral-small-latest',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': full_user_prompt}
                ],
                'temperature': 0.1,  # Low temperature for consistent JSON output
                'max_tokens': 1000,
                'response_format': {'type': 'json_object'}
            },
            timeout=30
        )

        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            logger.error(f"Erreur Mistral API: {response.status_code} - {error_data}")
            return jsonify({
                'error': f"Erreur API Mistral: {error_data.get('message', response.status_code)}"
            }), 502

        result = response.json()
        content = result['choices'][0]['message']['content']

        # Log pour debugging
        logger.info(f"Mistral KPI generation: prompt='{user_prompt[:50]}...', response_length={len(content)}")

        return jsonify({
            'content': content,
            'model': result.get('model', 'mistral-small-latest'),
            'usage': result.get('usage', {})
        })

    except requests.Timeout:
        logger.error("Timeout lors de l'appel Mistral API")
        return jsonify({'error': 'La requête a expiré. Veuillez réessayer.'}), 504
    except requests.RequestException as e:
        logger.error(f"Erreur réseau Mistral API: {e}")
        return jsonify({'error': 'Erreur de connexion au service IA'}), 502
    except Exception as e:
        logger.error(f"Erreur inattendue génération KPI: {e}")
        return jsonify({'error': 'Erreur interne lors de la génération'}), 500


def _get_default_system_prompt():
    """Retourne le system prompt par défaut pour la génération de KPI"""
    return """Tu es un assistant expert en Business Intelligence.
Tu convertis des descriptions en langage naturel en configurations KPI JSON.
Réponds UNIQUEMENT avec du JSON valide selon ce schéma:
{
  "kpi_name": "string",
  "metric": "budget_total|budget_spent|budget_remaining|expense_count|project_count|account_balance",
  "aggregation": "sum|avg|count|min|max",
  "time_range": "this_month|last_month|this_year",
  "filters": [],
  "dimensions": [],
  "visualization": "number|gauge|line|bar|pie",
  "refresh_rate": 60
}"""


def _simulate_mistral_response(user_prompt):
    """
    Simule une réponse Mistral pour le développement sans clé API.
    Analyse basique du prompt pour générer une configuration plausible.
    """
    import json
    import re

    prompt_lower = user_prompt.lower()

    # Détection du type de métrique
    metric = 'budget_total'
    if any(word in prompt_lower for word in ['dépense', 'spent', 'dépensé', 'consommé']):
        metric = 'budget_spent'
    elif any(word in prompt_lower for word in ['restant', 'remaining', 'disponible']):
        metric = 'budget_remaining'
    elif any(word in prompt_lower for word in ['projet', 'project']):
        metric = 'project_count'
    elif any(word in prompt_lower for word in ['compte', 'account', 'solde', 'balance']):
        metric = 'account_balance'

    # Détection de la visualisation
    visualization = 'number'
    if any(word in prompt_lower for word in ['évolution', 'tendance', 'trend', 'temps', 'timeline']):
        visualization = 'line'
    elif any(word in prompt_lower for word in ['comparaison', 'compare', 'répartition', 'distribution']):
        visualization = 'bar'
    elif any(word in prompt_lower for word in ['pourcentage', 'percent', 'ratio', 'taux']):
        visualization = 'gauge'
    elif any(word in prompt_lower for word in ['camembert', 'pie', 'parts']):
        visualization = 'pie'

    # Détection de l'agrégation
    aggregation = 'sum'
    if any(word in prompt_lower for word in ['moyenne', 'average', 'avg']):
        aggregation = 'avg'
    elif any(word in prompt_lower for word in ['nombre', 'count', 'combien']):
        aggregation = 'count'
    elif any(word in prompt_lower for word in ['maximum', 'max', 'plus élevé']):
        aggregation = 'max'
    elif any(word in prompt_lower for word in ['minimum', 'min', 'plus bas']):
        aggregation = 'min'

    # Génération du nom
    kpi_name = user_prompt[:50].strip()
    if len(kpi_name) > 40:
        kpi_name = kpi_name[:40] + '...'

    config = {
        "kpi_name": kpi_name.title(),
        "metric": metric,
        "aggregation": aggregation,
        "time_range": "this_month",
        "filters": [],
        "dimensions": [],
        "visualization": visualization,
        "refresh_rate": 60
    }

    logger.info(f"Simulation Mistral: {user_prompt[:30]}... -> {metric}/{visualization}")

    return jsonify({
        'content': json.dumps(config),
        'model': 'simulation',
        'usage': {'prompt_tokens': len(user_prompt.split()), 'completion_tokens': 50}
    })


@app.route('/api/ai/kpi-schema')
def api_ai_kpi_schema():
    """
    Retourne le schéma disponible pour la configuration manuelle de KPI.
    """
    return jsonify({
        'metrics': [
            {'id': 'budget_total', 'name': 'Budget Total', 'description': 'Somme des budgets alloués'},
            {'id': 'budget_spent', 'name': 'Budget Dépensé', 'description': 'Somme des dépenses'},
            {'id': 'budget_remaining', 'name': 'Budget Restant', 'description': 'Budget total - dépenses'},
            {'id': 'expense_count', 'name': 'Nombre de Dépenses', 'description': 'Compte des dépenses'},
            {'id': 'expense_amount', 'name': 'Montant Dépense', 'description': 'Montant individuel des dépenses'},
            {'id': 'project_count', 'name': 'Nombre de Projets', 'description': 'Compte des projets'},
            {'id': 'project_budget', 'name': 'Budget Projet', 'description': 'Budget par projet'},
            {'id': 'account_balance', 'name': 'Solde Compte', 'description': 'Solde des comptes bancaires'},
            {'id': 'burn_rate', 'name': 'Burn Rate', 'description': 'Taux de consommation mensuel'},
            {'id': 'budget_utilization', 'name': 'Utilisation Budget', 'description': 'Pourcentage du budget utilisé'}
        ],
        'aggregations': ['sum', 'avg', 'count', 'min', 'max'],
        'visualizations': ['number', 'gauge', 'line', 'bar', 'pie', 'table', 'sparkline'],
        'time_ranges': ['today', 'yesterday', 'last_7_days', 'last_30_days', 'this_month', 'last_month', 'this_quarter', 'this_year'],
        'dimensions': ['project', 'category', 'account', 'month', 'week', 'day', 'type'],
        'operators': ['=', '!=', '>', '<', '>=', '<=', 'in', 'contains']
    })


@app.route('/api/ai/compute-kpi', methods=['POST'])
@require_auth
def api_ai_compute_kpi():
    """
    Calcule les données d'un KPI à partir de sa configuration.

    Request body: KPIConfig object
    Response: Computed data for the widget
    """
    config = request.get_json()
    if not config:
        return jsonify({'error': 'Configuration KPI requise'}), 400

    metric = config.get('metric', 'budget_total')
    aggregation = config.get('aggregation', 'sum')
    time_range = config.get('time_range', 'this_month')
    dimensions = config.get('dimensions', [])
    filters = config.get('filters', [])

    try:
        # Récupération des données
        stats = manager.get_statistiques()
        projets = manager.get_tous_projets()
        comptes = manager.get_tous_comptes_bancaires()

        # Calcul selon la métrique
        value = 0
        trend = None
        breakdown = []

        if metric == 'budget_total':
            value = stats.get('budget_total', 0)
            trend = {'direction': 'up', 'value': 5.2}  # Simulation
        elif metric == 'budget_spent':
            value = stats.get('total_depense', 0)
            trend = {'direction': 'up', 'value': 12.3}
        elif metric == 'budget_remaining':
            value = stats.get('total_restant', 0)
            trend = {'direction': 'down', 'value': 8.1}
        elif metric == 'project_count':
            value = len(projets)
        elif metric == 'account_balance':
            value = sum(c.get('solde', 0) for c in comptes)
        elif metric == 'expense_count':
            value = sum(len(p.get('depenses', [])) for p in projets)
        elif metric == 'burn_rate':
            value = stats.get('depense_moyenne', 0)
        elif metric == 'budget_utilization':
            value = stats.get('pourcentage_utilise', 0)

        # Calcul des dimensions (breakdown)
        if 'category' in dimensions:
            categories = {}
            for projet in projets:
                cat = projet.get('categorie', 'Autre')
                if cat not in categories:
                    categories[cat] = 0
                categories[cat] += projet.get('budget_depense', 0)
            breakdown = [{'label': k, 'value': v} for k, v in categories.items()]

        if 'project' in dimensions:
            breakdown = [{'label': p['nom'], 'value': p.get('budget_depense', 0)} for p in projets[:10]]

        return jsonify({
            'value': value,
            'formatted_value': f"{value:,.0f}€" if 'budget' in metric or 'balance' in metric else str(value),
            'trend': trend,
            'breakdown': breakdown,
            'last_updated': datetime.now().isoformat(),
            'metric': metric,
            'aggregation': aggregation
        })

    except Exception as e:
        logger.error(f"Erreur calcul KPI: {e}")
        return jsonify({'error': 'Erreur lors du calcul du KPI'}), 500


@app.errorhandler(404)
def not_found_error(error):
    """Gestionnaire d'erreur 404"""
    return render_template('login.html', error='Page non trouvée'), 404

@app.errorhandler(500)
def internal_error(error):
    """Gestionnaire d'erreur 500"""
    logger.error(f"Erreur interne: {error}")
    return render_template('login.html', error='Erreur interne du serveur'), 500