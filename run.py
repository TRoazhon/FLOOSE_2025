#!/usr/bin/env python3
"""
Script de démarrage pour FLOOSE
Facilite le lancement avec différentes configurations
"""

import os
import sys
import argparse
from config import get_config, setup_logging

def main():
    """Script principal de démarrage"""
    parser = argparse.ArgumentParser(description='Démarrer FLOOSE')
    parser.add_argument('--env', choices=['development', 'production', 'testing'], 
                       default='development', help='Environnement de démarrage')
    parser.add_argument('--host', default='0.0.0.0', help='Host d\'écoute')
    parser.add_argument('--port', type=int, default=None, help='Port d\'écoute')
    parser.add_argument('--debug', action='store_true', help='Mode debug forcé')
    parser.add_argument('--init', action='store_true', help='Initialiser les données de demo')
    
    args = parser.parse_args()
    
    # Configuration de l'environnement
    os.environ['FLASK_ENV'] = args.env
    if args.debug:
        os.environ['DEBUG'] = 'True'
    
    # Import de l'application après configuration
    from app import app, logger, manager
    
    # Initialisation des données de demo si demandée
    if args.init:
        logger.info("Initialisation des données de démonstration...")
        init_demo_data(manager)
    
    # Configuration du démarrage
    config = get_config(args.env)
    host = args.host
    port = args.port or int(os.environ.get('PORT', 5003))
    debug = args.debug or config.DEBUG
    
    logger.info(f"Démarrage de FLOOSE v1.0.0")
    logger.info(f"Environnement: {args.env}")
    logger.info(f"URL: http://{host}:{port}")
    logger.info(f"Debug: {debug}")
    
    # Affichage des comptes de démonstration
    print("\n" + "="*60)
    print("🚀 FLOOSE - Gestionnaire de Budget Professionnel")
    print("="*60)
    print(f"URL: http://{host}:{port}")
    print("\n📋 Comptes de démonstration:")
    print("  • Email: demo@floose.com     | Password: Demo123!")
    print("  • Email: admin@floose.com    | Password: Admin123!")  
    print("  • Email: john.doe@example.com     | Password: Password123!")
    print("\n💡 Fonctionnalités disponibles:")
    print("  • Gestion budgets et projets")
    print("  • Comptes bancaires multi-devises")
    print("  • Analytics et prévisions")
    print("  • Export PDF des rapports")
    print("  • Dashboard admin (/admin/stats)")
    print("="*60)
    print()
    
    # Démarrage du serveur
    try:
        app.run(debug=debug, host=host, port=port)
    except KeyboardInterrupt:
        logger.info("Arrêt de l'application par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur lors du démarrage: {e}")
        sys.exit(1)


def init_demo_data(manager):
    """Initialise des données de démonstration"""
    try:
        # Vérifier s'il y a déjà des données
        projets_existants = manager.get_tous_projets()
        if len(projets_existants) > 0:
            print(f"Données existantes détectées ({len(projets_existants)} projets)")
            return
        
        print("Création des données de démonstration...")
        
        # Projets de démonstration
        projets_demo = [
            {'nom': 'Application Mobile E-commerce', 'budget': 25000, 'categorie': 'IT & Tech'},
            {'nom': 'Campagne Marketing Digital', 'budget': 15000, 'categorie': 'Marketing'},
            {'nom': 'Formation Équipe DevOps', 'budget': 8000, 'categorie': 'Formation'},
            {'nom': 'Serveurs Cloud Infrastructure', 'budget': 12000, 'categorie': 'Infrastructure'},
            {'nom': 'Recherche & Développement IA', 'budget': 30000, 'categorie': 'Recherche'}
        ]
        
        # Créer les projets
        projets_crees = []
        for projet_data in projets_demo:
            projet = manager.ajouter_projet(
                projet_data['nom'], 
                projet_data['budget'], 
                projet_data['categorie']
            )
            projets_crees.append(projet)
            print(f"  ✓ Projet créé: {projet['nom']}")
        
        # Ajouter quelques dépenses
        depenses_demo = [
            (0, 3500, "Développement interface utilisateur"),
            (0, 2200, "Tests et debugging"),
            (1, 4500, "Publicité Google Ads"),
            (1, 2800, "Création contenus visuels"),
            (2, 1500, "Certification AWS"),
            (3, 8500, "Serveurs production"),
            (4, 12000, "Licences logiciels IA")
        ]
        
        for i, (projet_idx, montant, description) in enumerate(depenses_demo):
            if projet_idx < len(projets_crees):
                manager.ajouter_depense(
                    projets_crees[projet_idx]['id'], 
                    montant, 
                    description
                )
                print(f"  ✓ Dépense ajoutée: {description} ({montant}€)")
        
        # Comptes bancaires de démonstration
        comptes_demo = [
            {'nom': 'Compte Principal', 'banque': 'BNP Paribas', 'solde': 85000, 'type': 'Courant'},
            {'nom': 'Compte Épargne', 'banque': 'Crédit Agricole', 'solde': 45000, 'type': 'Épargne'},
            {'nom': 'Compte Investissement', 'banque': 'Société Générale', 'solde': 120000, 'type': 'Investissement'}
        ]
        
        for compte_data in comptes_demo:
            manager.ajouter_compte_bancaire(
                compte_data['nom'],
                compte_data['banque'],
                compte_data['solde'],
                compte_data['type']
            )
            print(f"  ✓ Compte créé: {compte_data['nom']} ({compte_data['solde']:,}€)")
        
        print(f"\n✅ Données de démonstration créées avec succès!")
        print(f"   • {len(projets_demo)} projets")
        print(f"   • {len(depenses_demo)} dépenses")  
        print(f"   • {len(comptes_demo)} comptes bancaires")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation des données: {e}")


if __name__ == '__main__':
    main()