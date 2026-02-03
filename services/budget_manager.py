"""
Gestionnaire de Budget Personnel - Classe Principale
Pretotype pour tester le concept de gestion budgétaire personnalisée
Avec persistance CSV et système de clés relationnelles
"""

from .data_manager import DataManager

class CompteBancaire:
    """
    Classe pour représenter un compte bancaire
    """
    
    def __init__(self, nom, banque, solde_initial=0, type_compte="Courant"):
        """
        Initialise un compte bancaire
        
        Args:
            nom (str): Nom du compte
            banque (str): Nom de la banque
            solde_initial (float): Solde initial du compte
            type_compte (str): Type de compte (Courant, Épargne, etc.)
        """
        self.id = None  # Sera défini par le gestionnaire
        self.nom = nom
        self.banque = banque
        self.solde = solde_initial
        self.type_compte = type_compte
        self.historique = []
    
    def crediter(self, montant, description="Crédit", data_manager=None):
        """
        Crédite le compte et sauvegarde la transaction
        
        Args:
            montant (float): Montant à créditer
            description (str): Description de l'opération
            data_manager: Gestionnaire de données pour la sauvegarde
        """
        self.solde += montant
        transaction = {
            'type': 'crédit',
            'montant': montant,
            'description': description,
            'solde_apres': self.solde
        }
        
        # Sauvegarde de la transaction si data_manager fourni
        if data_manager and self.id:
            transaction['id'] = data_manager.save_transaction(transaction, self.id)
            data_manager.update_compte_solde(self.id, self.solde)
        
        self.historique.append(transaction)
    
    def debiter(self, montant, description="Débit", data_manager=None):
        """
        Débite le compte et sauvegarde la transaction
        
        Args:
            montant (float): Montant à débiter
            description (str): Description de l'opération
            data_manager: Gestionnaire de données pour la sauvegarde
            
        Returns:
            bool: True si succès, False si solde insuffisant
        """
        if self.solde >= montant:
            self.solde -= montant
            transaction = {
                'type': 'débit',
                'montant': montant,
                'description': description,
                'solde_apres': self.solde
            }
            
            # Sauvegarde de la transaction si data_manager fourni
            if data_manager and self.id:
                transaction['id'] = data_manager.save_transaction(transaction, self.id)
                data_manager.update_compte_solde(self.id, self.solde)
            
            self.historique.append(transaction)
            return True
        return False
    
    def to_dict(self):
        """
        Convertit le compte en dictionnaire
        
        Returns:
            dict: Représentation du compte
        """
        return {
            'id': self.id,
            'nom': self.nom,
            'banque': self.banque,
            'solde': self.solde,
            'type_compte': self.type_compte,
            'historique': self.historique
        }

class BudgetManager:
    """
    Classe principale pour gérer les budgets de projets personnels
    Principe : Cohérence et intelligence des données
    """
    
    def __init__(self):
        """
        Initialise le gestionnaire avec persistance CSV
        """
        # Initialisation du gestionnaire de données CSV
        self.data_manager = DataManager()
        
        # Chargement des données existantes depuis CSV
        self.projets = []
        self.budget_total = 0
        self.comptes_bancaires = []
        
        self.load_data_from_csv()
        self.migrate_existing_projects_to_history()
    
    def load_data_from_csv(self):
        """
        Charge toutes les données depuis les fichiers CSV
        """
        # Chargement des projets avec leurs dépenses
        self.projets = self.data_manager.load_projets()
        
        # Chargement des comptes bancaires avec leurs transactions
        comptes_data = self.data_manager.load_comptes()
        self.comptes_bancaires = []
        
        for compte_data in comptes_data:
            compte = CompteBancaire(
                compte_data['nom'],
                compte_data['banque'],
                compte_data['solde'],
                compte_data['type_compte']
            )
            compte.id = compte_data['id']
            compte.historique = compte_data['historique']
            self.comptes_bancaires.append(compte)
        
        # Recalcul du budget total
        self.budget_total = sum(p['budget_alloue'] for p in self.projets)
        
    def ajouter_projet(self, nom, budget_alloue, categorie="Général", categorie_id=None):
        """
        Ajoute un nouveau projet avec son budget et le sauvegarde en CSV
        
        Args:
            nom (str): Nom du projet
            budget_alloue (float): Budget alloué au projet
            categorie (str): Catégorie du projet (pour compatibilité)
            categorie_id (int, optional): ID de la catégorie
            
        Returns:
            dict: Le projet créé
        """
        # Si pas de categorie_id fourni, essayer de trouver une catégorie par défaut
        if categorie_id is None:
            categories_projet = self.get_categories('projet')
            if categories_projet:
                # Prendre la première catégorie disponible ou chercher par nom
                categorie_trouvee = next((cat for cat in categories_projet if cat['nom'].lower() == categorie.lower()), None)
                if categorie_trouvee:
                    categorie_id = categorie_trouvee['id']
                else:
                    categorie_id = categories_projet[0]['id']  # Première catégorie par défaut
        
        # Sauvegarde d'abord en CSV pour obtenir l'ID
        projet_data = {
            'nom': nom,
            'budget_alloue': budget_alloue,
            'budget_depense': 0,
            'categorie_id': categorie_id
        }
        
        projet_id = self.data_manager.save_projet(projet_data)
        
        # Création de l'objet projet en mémoire
        projet = {
            'id': projet_id,
            'nom': nom,
            'budget_alloue': budget_alloue,
            'budget_depense': 0,
            'categorie_id': categorie_id,
            'depenses': []
        }
        
        self.projets.append(projet)
        self.budget_total += budget_alloue
        
        # Sauvegarder un snapshot initial dans l'historique
        self.data_manager.save_historique_projet(
            projet_id=projet['id'],
            budget_alloue=budget_alloue,
            budget_depense=0.0,
            nombre_depenses=0,
            action='creation',
            description=f"Création du projet: {nom}"
        )
        
        return projet
    
    def _get_projet_raw(self, projet_id):
        """
        Récupère le projet original (sans copie) pour modifications internes

        Args:
            projet_id (int): ID du projet recherché

        Returns:
            dict ou None: Le projet original ou None
        """
        for projet in self.projets:
            if projet['id'] == projet_id:
                return projet
        return None

    def ajouter_depense(self, projet_id, montant, description, categorie_id=None, date_depense=None, commentaire=""):
        """
        Ajoute une dépense à un projet spécifique et la sauvegarde en CSV

        Args:
            projet_id (int): ID du projet
            montant (float): Montant de la dépense
            description (str): Description de la dépense
            categorie_id (int, optional): ID de la catégorie
            date_depense (str, optional): Date de la dépense (YYYY-MM-DD)
            commentaire (str, optional): Commentaire sur la dépense

        Returns:
            bool: True si succès, False sinon
        """
        # Utiliser _get_projet_raw pour modifier le projet original
        projet = self._get_projet_raw(projet_id)
        if projet is None:
            return False

        # Vérification cohérence : ne pas dépasser le budget
        if projet['budget_depense'] + montant > projet['budget_alloue']:
            return False

        # Sauvegarde de la dépense en CSV
        depense_data = {
            'montant': montant,
            'description': description,
            'categorie_id': categorie_id,
            'date_depense': date_depense,
            'commentaire': commentaire
        }

        depense_id = self.data_manager.save_depense(depense_data, projet_id)

        # Mise à jour en mémoire (modifie le projet original dans self.projets)
        depense = {
            'id': depense_id,
            'montant': montant,
            'description': description,
            'categorie_id': categorie_id,
            'date_depense': date_depense,
            'commentaire': commentaire
        }
        projet['depenses'].append(depense)
        projet['budget_depense'] += montant

        # Mise à jour du budget dépensé dans le CSV
        self.data_manager.update_projet_budget_depense(projet_id, projet['budget_depense'])
        
        # Sauvegarder un snapshot dans l'historique
        self.data_manager.save_historique_projet(
            projet_id=projet_id,
            budget_alloue=projet['budget_alloue'],
            budget_depense=projet['budget_depense'],
            nombre_depenses=len(projet['depenses']),
            action='depense_ajoutee',
            description=f"Dépense ajoutée: {description} ({montant}€)"
        )
        
        return True
    
    def get_projet(self, projet_id):
        """
        Récupère un projet par son ID enrichi avec les informations des catégories
        
        Args:
            projet_id (int): ID du projet recherché
            
        Returns:
            dict ou None: Le projet trouvé enrichi ou None
        """
        for projet in self.projets:
            if projet['id'] == projet_id:
                projet_enrichi = projet.copy()
                
                # Ajouter les informations de catégorie
                categories = self.get_categories()
                categories_dict = {cat['id']: cat for cat in categories}
                
                if projet.get('categorie_id'):
                    category = categories_dict.get(projet['categorie_id'])
                    if category:
                        projet_enrichi['categorie'] = category['nom']
                        projet_enrichi['categorie_couleur'] = category['couleur']
                    else:
                        projet_enrichi['categorie'] = 'Non catégorisé'
                        projet_enrichi['categorie_couleur'] = '#6b7280'
                else:
                    projet_enrichi['categorie'] = 'Non catégorisé'
                    projet_enrichi['categorie_couleur'] = '#6b7280'
                
                return projet_enrichi
        return None
    
    def get_statistiques(self):
        """
        Génère des statistiques globales (intelligence des données)
        
        Returns:
            dict: Statistiques sur l'ensemble des budgets
        """
        # Recalcul pour s'assurer que budget_total est à jour
        self.budget_total = sum(p['budget_alloue'] for p in self.projets)
        
        total_depense = sum(p['budget_depense'] for p in self.projets)
        total_restant = self.budget_total - total_depense
        
        # Calcul du pourcentage d'utilisation
        pourcentage_utilise = (total_depense / self.budget_total * 100) if self.budget_total > 0 else 0
        
        # Statistiques additionnelles
        projets_en_depassement = sum(1 for p in self.projets if p['budget_depense'] > p['budget_alloue'])
        depense_moyenne = total_depense / len(self.projets) if len(self.projets) > 0 else 0
        budget_moyen = self.budget_total / len(self.projets) if len(self.projets) > 0 else 0
        
        return {
            'budget_total': self.budget_total,
            'total_depense': total_depense,
            'total_restant': total_restant,
            'pourcentage_utilise': round(pourcentage_utilise, 2),
            'nombre_projets': len(self.projets),
            'projets_en_depassement': projets_en_depassement,
            'depense_moyenne': round(depense_moyenne, 2),
            'budget_moyen': round(budget_moyen, 2)
        }
    
    def get_tous_projets(self):
        """
        Retourne la liste de tous les projets enrichis avec les informations des catégories
        
        Returns:
            list: Liste des projets avec catégories
        """
        projets_enrichis = []
        categories = self.get_categories()
        categories_dict = {cat['id']: cat for cat in categories}
        
        for projet in self.projets:
            projet_enrichi = projet.copy()
            
            # Ajouter les informations de catégorie
            if projet.get('categorie_id'):
                category = categories_dict.get(projet['categorie_id'])
                if category:
                    projet_enrichi['categorie'] = category['nom']
                    projet_enrichi['categorie_couleur'] = category['couleur']
                else:
                    projet_enrichi['categorie'] = 'Non catégorisé'
                    projet_enrichi['categorie_couleur'] = '#6b7280'
            else:
                projet_enrichi['categorie'] = 'Non catégorisé'
                projet_enrichi['categorie_couleur'] = '#6b7280'
            
            projets_enrichis.append(projet_enrichi)
        
        return projets_enrichis
    
    def get_historique_projet(self, projet_id):
        """
        Récupère l'historique d'évolution d'un projet
        
        Args:
            projet_id (int): ID du projet
            
        Returns:
            list: Liste des snapshots historiques
        """
        return self.data_manager.load_historique_projet(projet_id)
    
    def get_historique_tous_projets_avec_categories(self):
        """
        Récupère l'historique de tous les projets enrichi avec les couleurs des catégories
        
        Returns:
            dict: Dictionnaire {projet_id: {'projet': data, 'historique': snapshots}}
        """
        historique_global = self.data_manager.load_historique_tous_projets()
        categories = self.get_categories()
        categories_dict = {cat['id']: cat for cat in categories}
        
        projets_avec_historique = {}
        
        for projet in self.projets:
            projet_id = projet['id']
            
            # Enrichir les informations du projet avec la catégorie
            projet_enrichi = projet.copy()
            if projet.get('categorie_id'):
                category = categories_dict.get(projet['categorie_id'])
                if category:
                    projet_enrichi['categorie'] = category['nom']
                    projet_enrichi['categorie_couleur'] = category['couleur']
                else:
                    projet_enrichi['categorie'] = 'Non catégorisé'
                    projet_enrichi['categorie_couleur'] = '#6b7280'
            else:
                projet_enrichi['categorie'] = 'Non catégorisé'
                projet_enrichi['categorie_couleur'] = '#6b7280'
            
            projets_avec_historique[projet_id] = {
                'projet': projet_enrichi,
                'historique': historique_global.get(projet_id, [])
            }
        
        return projets_avec_historique
    
    def migrate_existing_projects_to_history(self):
        """
        Migration pour ajouter les projets existants à l'historique s'ils n'y sont pas
        """
        for projet in self.projets:
            historique_existant = self.data_manager.load_historique_projet(projet['id'])
            
            # Si aucun historique, créer un snapshot initial
            if len(historique_existant) == 0:
                self.data_manager.save_historique_projet(
                    projet_id=projet['id'],
                    budget_alloue=projet['budget_alloue'],
                    budget_depense=projet['budget_depense'],
                    nombre_depenses=len(projet['depenses']),
                    action='migration',
                    description=f"Migration: état actuel du projet {projet['nom']}"
                )
    
    # === GESTION DES COMPTES BANCAIRES ===
    
    def ajouter_compte_bancaire(self, nom, banque, solde_initial=0, type_compte="Courant"):
        """
        Ajoute un nouveau compte bancaire et le sauvegarde en CSV
        
        Args:
            nom (str): Nom du compte
            banque (str): Nom de la banque
            solde_initial (float): Solde initial
            type_compte (str): Type de compte
            
        Returns:
            CompteBancaire: Le compte créé
        """
        # Sauvegarde en CSV d'abord pour obtenir l'ID
        compte_data = {
            'nom': nom,
            'banque': banque,
            'solde': solde_initial,
            'type_compte': type_compte
        }
        
        compte_id = self.data_manager.save_compte(compte_data)
        
        # Création de l'objet compte en mémoire
        compte = CompteBancaire(nom, banque, solde_initial, type_compte)
        compte.id = compte_id
        self.comptes_bancaires.append(compte)
        return compte
    
    def get_compte_bancaire(self, compte_id):
        """
        Récupère un compte bancaire par son ID
        
        Args:
            compte_id (int): ID du compte
            
        Returns:
            CompteBancaire ou None: Le compte trouvé ou None
        """
        for compte in self.comptes_bancaires:
            if compte.id == compte_id:
                return compte
        return None
    
    def get_tous_comptes_bancaires(self):
        """
        Retourne tous les comptes bancaires
        
        Returns:
            list: Liste des comptes bancaires (dict)
        """
        return [compte.to_dict() for compte in self.comptes_bancaires]
    
    def effectuer_operation_bancaire(self, compte_id, montant, description, type_operation):
        """
        Effectue une opération bancaire (crédit ou débit) avec sauvegarde CSV
        
        Args:
            compte_id (int): ID du compte
            montant (float): Montant de l'opération
            description (str): Description
            type_operation (str): 'crédit' ou 'débit'
            
        Returns:
            bool: True si succès, False sinon
        """
        compte = self.get_compte_bancaire(compte_id)
        if compte is None:
            return False
            
        if type_operation == 'crédit':
            compte.crediter(montant, description, self.data_manager)
            return True
        elif type_operation == 'débit':
            return compte.debiter(montant, description, self.data_manager)
        
        return False
    
    def get_statistiques_comptes(self):
        """
        Génère des statistiques sur les comptes bancaires
        
        Returns:
            dict: Statistiques des comptes
        """
        total_soldes = sum(compte.solde for compte in self.comptes_bancaires)
        nombre_comptes = len(self.comptes_bancaires)
        
        return {
            'total_soldes': total_soldes,
            'nombre_comptes': nombre_comptes,
            'solde_moyen': total_soldes / nombre_comptes if nombre_comptes > 0 else 0
        }
    
    def get_database_stats(self):
        """
        Retourne les statistiques de la base de données CSV
        
        Returns:
            dict: Statistiques de persistence
        """
        return self.data_manager.get_database_stats()
    
    def modifier_depense(self, projet_id: int, depense_id: int, nouveau_montant: float, nouvelle_description: str):
        """
        Modifie une dépense existante avec validation et mise à jour des totaux

        Args:
            projet_id (int): ID du projet
            depense_id (int): ID de la dépense à modifier
            nouveau_montant (float): Nouveau montant
            nouvelle_description (str): Nouvelle description

        Returns:
            bool: True si succès, False sinon
        """
        # Récupérer la dépense actuelle
        ancienne_depense = self.data_manager.get_depense_by_id(depense_id)
        if not ancienne_depense or ancienne_depense['projet_id'] != projet_id:
            return False

        # Récupérer le projet original (pas la copie)
        projet = self._get_projet_raw(projet_id)
        if not projet:
            return False

        # Calculer la différence de montant
        ancien_montant = ancienne_depense['montant']
        difference = nouveau_montant - ancien_montant

        # Vérifier que le nouveau budget ne dépasse pas la limite
        if projet['budget_depense'] + difference > projet['budget_alloue']:
            return False

        # Mettre à jour dans le CSV
        success = self.data_manager.update_depense(depense_id, nouveau_montant, nouvelle_description)
        if not success:
            return False

        # Mettre à jour en mémoire dans le projet original
        for depense in projet['depenses']:
            if depense.get('id') == depense_id:
                depense['montant'] = nouveau_montant
                depense['description'] = nouvelle_description
                break

        # Mettre à jour le budget dépensé du projet
        projet['budget_depense'] += difference

        # Mettre à jour le budget dépensé dans le CSV
        self.data_manager.update_projet_budget_depense(projet_id, projet['budget_depense'])

        return True

    def supprimer_depense(self, projet_id: int, depense_id: int):
        """
        Supprime une dépense et met à jour les totaux

        Args:
            projet_id (int): ID du projet
            depense_id (int): ID de la dépense à supprimer

        Returns:
            bool: True si succès, False sinon
        """
        # Récupérer le projet original (pas la copie)
        projet = self._get_projet_raw(projet_id)
        if not projet:
            return False

        # Supprimer du CSV et récupérer les infos de la dépense supprimée
        depense_supprimee = self.data_manager.delete_depense(depense_id)
        if not depense_supprimee or depense_supprimee['projet_id'] != projet_id:
            return False

        # Mettre à jour en mémoire dans le projet original
        projet['depenses'] = [d for d in projet['depenses'] if d.get('id') != depense_id]

        # Mettre à jour le budget dépensé du projet
        projet['budget_depense'] -= depense_supprimee['montant']

        # Mettre à jour le budget dépensé dans le CSV
        self.data_manager.update_projet_budget_depense(projet_id, projet['budget_depense'])

        return True
    
    def get_depense(self, depense_id: int):
        """
        Récupère une dépense par son ID
        
        Args:
            depense_id (int): ID de la dépense
            
        Returns:
            dict ou None: Dépense trouvée ou None
        """
        return self.data_manager.get_depense_by_id(depense_id)
    
    def get_depenses_projet(self, projet_id: int):
        """
        Récupère toutes les dépenses d'un projet
        
        Args:
            projet_id (int): ID du projet
            
        Returns:
            list: Liste des dépenses du projet
        """
        projet = self.get_projet(projet_id)
        if projet:
            return projet['depenses']
        return []
    
    # === GESTION DES CATÉGORIES ===
    
    def get_categories(self, type_filter: str = None):
        """
        Récupère toutes les catégories ou filtrées par type
        
        Args:
            type_filter (str, optional): 'projet' ou 'depense'
            
        Returns:
            list: Liste des catégories
        """
        return self.data_manager.load_categories(type_filter)
    
    def get_categorie(self, categorie_id: int):
        """
        Récupère une catégorie par son ID
        
        Args:
            categorie_id (int): ID de la catégorie
            
        Returns:
            dict ou None: Catégorie trouvée ou None
        """
        return self.data_manager.get_categorie_by_id(categorie_id)
    
    def ajouter_categorie(self, nom: str, couleur: str, type_categorie: str, description: str = ""):
        """
        Ajoute une nouvelle catégorie
        
        Args:
            nom (str): Nom de la catégorie
            couleur (str): Couleur (hex) de la catégorie
            type_categorie (str): Type ('projet' ou 'depense')
            description (str): Description de la catégorie
            
        Returns:
            int: ID de la catégorie créée
        """
        categorie_data = {
            'nom': nom,
            'couleur': couleur,
            'type': type_categorie,
            'description': description
        }
        
        return self.data_manager.save_categorie(categorie_data)
    
    def modifier_categorie(self, categorie_id: int, nom: str, couleur: str, description: str):
        """
        Modifie une catégorie existante
        
        Args:
            categorie_id (int): ID de la catégorie
            nom (str): Nouveau nom
            couleur (str): Nouvelle couleur
            description (str): Nouvelle description
            
        Returns:
            bool: True si succès, False sinon
        """
        return self.data_manager.update_categorie(categorie_id, nom, couleur, description)
    
    def supprimer_categorie(self, categorie_id: int):
        """
        Supprime une catégorie (seulement si non utilisée)
        
        Args:
            categorie_id (int): ID de la catégorie
            
        Returns:
            bool: True si succès, False sinon
        """
        return self.data_manager.delete_categorie(categorie_id)
    
    def get_categories_projets_avec_couleurs(self):
        """
        Récupère tous les projets avec leurs catégories et couleurs
        
        Returns:
            list: Liste des projets enrichie avec les infos de catégorie
        """
        projets = self.get_tous_projets()
        categories = {cat['id']: cat for cat in self.get_categories()}
        
        for projet in projets:
            categorie_id = projet.get('categorie_id')
            if categorie_id and categorie_id in categories:
                projet['categorie'] = categories[categorie_id]
            else:
                # Catégorie par défaut si pas trouvée
                projet['categorie'] = {
                    'id': 0,
                    'nom': 'Non catégorisé',
                    'couleur': '#F5F5F5',
                    'type': 'projet'
                }
        
        return projets
    
    def get_depenses_avec_couleurs(self, projet_id: int):
        """
        Récupère les dépenses d'un projet avec leurs catégories et couleurs
        
        Args:
            projet_id (int): ID du projet
            
        Returns:
            list: Liste des dépenses enrichie avec les infos de catégorie
        """
        depenses = self.get_depenses_projet(projet_id)
        categories = {cat['id']: cat for cat in self.get_categories('depense')}
        
        for depense in depenses:
            categorie_id = depense.get('categorie_id')
            if categorie_id and categorie_id in categories:
                depense['categorie'] = categories[categorie_id]
            else:
                # Catégorie par défaut si pas trouvée
                depense['categorie'] = {
                    'id': 0,
                    'nom': 'Non catégorisé',
                    'couleur': '#F5F5F5',
                    'type': 'depense'
                }
        
        return depenses