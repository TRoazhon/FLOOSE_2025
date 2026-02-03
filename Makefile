# Makefile pour FLOOSE - Gestionnaire de Budget Professionnel

.PHONY: help install run test clean dev prod init-demo lint coverage security

# Variables
PYTHON = python3
PIP = pip3
VENV = venv
PORT = 5002

# Aide par défaut
help:
	@echo "🚀 FLOOSE - Gestionnaire de Budget Professionnel"
	@echo "================================================"
	@echo ""
	@echo "Commandes disponibles:"
	@echo ""
	@echo "📦 Installation:"
	@echo "  make install      - Installer les dépendances"
	@echo "  make venv         - Créer l'environnement virtuel"
	@echo "  make init-demo    - Initialiser avec des données de demo"
	@echo ""
	@echo "🚀 Lancement:"
	@echo "  make run          - Lancer en mode développement"
	@echo "  make dev          - Lancer en mode développement avec debug"
	@echo "  make prod         - Lancer en mode production"
	@echo ""
	@echo "🧪 Tests et Qualité:"
	@echo "  make test         - Lancer tous les tests"
	@echo "  make test-fast    - Lancer les tests rapides uniquement"
	@echo "  make coverage     - Tests avec rapport de couverture"
	@echo "  make lint         - Vérification du style de code"
	@echo "  make security     - Analyse de sécurité"
	@echo ""
	@echo "🔧 Utilitaires:"
	@echo "  make clean        - Nettoyer les fichiers temporaires"
	@echo "  make logs         - Afficher les logs récents"
	@echo "  make backup       - Sauvegarder les données"
	@echo "  make reset        - Réinitialiser les données"

# Installation des dépendances
install:
	$(PIP) install -r requirements.txt
	@echo "✅ Dépendances installées"

# Création de l'environnement virtuel
venv:
	$(PYTHON) -m venv $(VENV)
	@echo "✅ Environnement virtuel créé dans ./$(VENV)"
	@echo "Activer avec: source $(VENV)/bin/activate (Linux/Mac) ou $(VENV)\\Scripts\\activate (Windows)"

# Lancement en développement
run:
	$(PYTHON) run.py --env development --port $(PORT)

# Lancement en développement avec debug
dev:
	$(PYTHON) run.py --env development --debug --port $(PORT)

# Lancement en production
prod:
	$(PYTHON) run.py --env production --port $(PORT)

# Initialiser avec des données de démonstration
init-demo:
	$(PYTHON) run.py --init --env development

# Tests complets
test:
	pytest -v --tb=short

# Tests rapides (sans les tests lents)
test-fast:
	pytest -v -m "not slow"

# Tests avec couverture
coverage:
	pytest --cov=. --cov-report=html --cov-report=term
	@echo "📊 Rapport de couverture disponible dans htmlcov/index.html"

# Vérification style de code
lint:
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# Analyse de sécurité
security:
	bandit -r . -f json -o security-report.json
	@echo "🔒 Rapport de sécurité disponible dans security-report.json"

# Nettoyage des fichiers temporaires
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage
	rm -f security-report.json
	@echo "🧹 Fichiers temporaires supprimés"

# Afficher les logs récents
logs:
	@if [ -f "logs/floose.log" ]; then \
		tail -50 logs/floose.log; \
	else \
		echo "Aucun fichier de log trouvé"; \
	fi

# Sauvegarder les données
backup:
	@mkdir -p backups
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	tar -czf "backups/floose_backup_$$timestamp.tar.gz" data/; \
	echo "💾 Sauvegarde créée: backups/floose_backup_$$timestamp.tar.gz"

# Réinitialiser les données (ATTENTION: supprime toutes les données)
reset:
	@echo "⚠️  ATTENTION: Cette commande va supprimer toutes les données!"
	@read -p "Êtes-vous sûr? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -rf data/*.csv; \
		rm -rf locks/*; \
		echo "🗑️  Données supprimées. Relancer l'application pour recréer les fichiers."; \
	else \
		echo "❌ Opération annulée"; \
	fi

# Vérifier que Python est installé
check-python:
	@$(PYTHON) --version > /dev/null 2>&1 || { \
		echo "❌ Python 3 n'est pas installé ou pas dans le PATH"; \
		exit 1; \
	}

# Installation complète pour développement
dev-setup: check-python venv install
	@echo ""
	@echo "🎉 Installation terminée!"
	@echo ""
	@echo "Prochaines étapes:"
	@echo "1. Activer l'environnement virtuel:"
	@echo "   source $(VENV)/bin/activate    # Linux/Mac"
	@echo "   $(VENV)\\Scripts\\activate       # Windows"
	@echo ""
	@echo "2. Lancer l'application:"
	@echo "   make run"
	@echo ""

# Déployement en production (exemple)
deploy-prod:
	@echo "🚀 Déployement en production..."
	$(PYTHON) -m gunicorn --bind 0.0.0.0:$(PORT) --workers 4 app:app
	@echo "✅ Application déployée sur le port $(PORT)"