"""
Service d'Analytics pour FLOOSE
Logique métier pour les calculs financiers et recommandations
"""

from datetime import datetime
from typing import Dict, List, Any


def calculate_financial_health(stats: Dict, projets: List[Dict], comptes: List[Dict]) -> int:
    """
    Calcule un score de santé financière de 0 à 100

    Args:
        stats: Statistiques globales du budget
        projets: Liste des projets
        comptes: Liste des comptes bancaires

    Returns:
        int: Score de santé financière (0-100)
    """
    score = 100

    # Facteur 1: Utilisation du budget (30%)
    budget_usage = stats['pourcentage_utilise']
    if budget_usage > 90:
        score -= 30
    elif budget_usage > 80:
        score -= 20
    elif budget_usage > 70:
        score -= 10

    # Facteur 2: Projets en dépassement (25%)
    if stats['projets_en_depassement'] > 0:
        score -= min(25, stats['projets_en_depassement'] * 10)

    # Facteur 3: Diversification (15%)
    if len(projets) < 3:
        score -= 15

    # Facteur 4: Liquidités (20%)
    total_cash = sum(compte['solde'] for compte in comptes)
    if total_cash < stats['total_depense'] * 0.5:
        score -= 20
    elif total_cash < stats['total_depense']:
        score -= 10

    # Facteur 5: Tendance (10%)
    # Score bonus pour efficacité
    if stats['pourcentage_utilise'] < 50:
        score += 10

    return max(0, min(100, score))


def get_health_level(score: int) -> str:
    """
    Convertit le score en niveau lisible

    Args:
        score: Score de santé financière

    Returns:
        str: Niveau ('excellent', 'good', 'warning', 'critical')
    """
    if score >= 80:
        return 'excellent'
    elif score >= 60:
        return 'good'
    elif score >= 40:
        return 'warning'
    else:
        return 'critical'


def generate_ai_analysis(stats: Dict, projets: List[Dict], comptes: List[Dict], health_score: int) -> List[str]:
    """
    Génère une analyse textuelle simple basée sur les données

    Args:
        stats: Statistiques globales
        projets: Liste des projets
        comptes: Liste des comptes bancaires
        health_score: Score de santé financière

    Returns:
        list: Liste des analyses textuelles
    """
    analysis = []

    # Analyse budget
    if stats['pourcentage_utilise'] > 85:
        analysis.append("Utilisation budgétaire élevée - surveillance recommandée")
    elif stats['pourcentage_utilise'] < 50:
        analysis.append("Excellente maîtrise budgétaire - opportunité d'investissement")

    # Analyse projets
    if stats['projets_en_depassement'] > 0:
        analysis.append(f"{stats['projets_en_depassement']} projet(s) en dépassement")

    # Analyse liquidités
    total_cash = sum(compte['solde'] for compte in comptes)
    if total_cash > stats['total_depense'] * 2:
        analysis.append("Trésorerie confortable - position financière solide")
    elif total_cash < stats['total_depense']:
        analysis.append("Trésorerie limitée - attention au cash-flow")

    # Analyse performance
    if health_score >= 80:
        analysis.append("Performance financière excellente")
    elif health_score < 60:
        analysis.append("Marge d'amélioration dans la gestion financière")

    return analysis


def generate_recommendations(stats: Dict, projets: List[Dict], health_score: int) -> List[Dict[str, str]]:
    """
    Génère des recommandations intelligentes

    Args:
        stats: Statistiques globales
        projets: Liste des projets
        health_score: Score de santé financière

    Returns:
        list: Liste des recommandations avec type, priorité, action et impact
    """
    recommendations = []

    if stats['pourcentage_utilise'] > 80:
        recommendations.append({
            'type': 'budget',
            'priority': 'high',
            'action': 'Réviser les budgets des projets en cours',
            'impact': 'Éviter les dépassements'
        })

    if len(projets) < 3:
        recommendations.append({
            'type': 'diversification',
            'priority': 'medium',
            'action': 'Diversifier le portefeuille de projets',
            'impact': 'Réduire les risques'
        })

    if health_score < 70:
        recommendations.append({
            'type': 'optimization',
            'priority': 'high',
            'action': 'Optimiser l\'allocation des ressources',
            'impact': 'Améliorer la performance globale'
        })

    efficient_projects = [p for p in projets if p['budget_alloue'] > 0 and p['budget_depense'] / p['budget_alloue'] < 0.7]
    if len(efficient_projects) > 0:
        recommendations.append({
            'type': 'investment',
            'priority': 'low',
            'action': f'Augmenter l\'investissement sur les {len(efficient_projects)} projets performants',
            'impact': 'Maximiser le retour sur investissement'
        })

    return recommendations


def generate_analytics_report(stats: Dict, projets: List[Dict], comptes: List[Dict]) -> str:
    """
    Génère un rapport d'analytics en format texte

    Args:
        stats: Statistiques globales
        projets: Liste des projets
        comptes: Liste des comptes bancaires

    Returns:
        str: Rapport formaté en texte
    """
    report = f"""
=== RAPPORT D'ANALYTICS FLOOSE ===
Généré le : {datetime.now().strftime('%d/%m/%Y à %H:%M')}

=== STATISTIQUES GLOBALES ===
Budget Total : {stats['budget_total']:,.2f}€
Total Dépensé : {stats['total_depense']:,.2f}€
Total Restant : {stats['total_restant']:,.2f}€
Pourcentage Utilisé : {stats['pourcentage_utilise']:.1f}%
Nombre de Projets : {stats['nombre_projets']}

=== DÉTAIL DES PROJETS ===
"""

    for projet in projets:
        progression = (projet['budget_depense'] / projet['budget_alloue'] * 100) if projet['budget_alloue'] > 0 else 0
        report += f"""
Projet : {projet['nom']}
  - Catégorie : {projet.get('categorie', 'Non catégorisé')}
  - Budget Alloué : {projet['budget_alloue']:,.2f}€
  - Budget Dépensé : {projet['budget_depense']:,.2f}€
  - Progression : {progression:.1f}%
  - Nombre de Dépenses : {len(projet.get('depenses', []))}
"""

    report += f"""
=== COMPTES BANCAIRES ===
Nombre de Comptes : {len(comptes)}
"""

    for compte in comptes:
        report += f"""
Compte : {compte['nom']} ({compte['banque']})
  - Type : {compte['type_compte']}
  - Solde : {compte['solde']:,.2f}€
  - Transactions : {len(compte.get('historique', []))}
"""

    # Ajout d'analyses
    risky_projects = [p for p in projets if p['budget_alloue'] > 0 and (p['budget_depense'] / p['budget_alloue'] * 100) > 80]
    completed_projects = [p for p in projets if p['budget_alloue'] > 0 and (p['budget_depense'] / p['budget_alloue'] * 100) > 90]

    report += f"""
=== ANALYSES ===
Projets à Risque (>80% budget) : {len(risky_projects)}
Projets Quasi-Terminés (>90% budget) : {len(completed_projects)}

=== RECOMMANDATIONS ===
"""

    if len(risky_projects) > 0:
        report += "- Attention : Certains projets approchent de la limite budgétaire.\n"

    if stats['pourcentage_utilise'] < 50:
        report += "- Excellent contrôle budgétaire. Possibilité d'investir dans de nouveaux projets.\n"
    elif stats['pourcentage_utilise'] > 85:
        report += "- Budget global fortement utilisé. Surveillance recommandée.\n"

    report += f"""
=== FIN DU RAPPORT ===
Rapport généré par Floose Analytics
"""

    return report
