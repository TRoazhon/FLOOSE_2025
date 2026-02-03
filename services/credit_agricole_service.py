"""
Service d'intégration Crédit Agricole
Gestion de l'authentification OAuth2 et récupération des données bancaires
Conforme à la directive DSP2/PSD2
"""

import base64
import hashlib
import secrets
import urllib.parse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests
from functools import wraps

logger = logging.getLogger(__name__)


class CreditAgricoleError(Exception):
    """Exception personnalisée pour les erreurs Crédit Agricole"""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class CreditAgricoleService:
    """
    Service d'intégration avec l'API Crédit Agricole
    Implémente le flux OAuth2 et les appels API DSP2
    """

    # Endpoints de l'API (pré-production par défaut)
    ENVIRONMENTS = {
        'sandbox': {
            'auth_base': 'https://usignon.pre.ca-cib.com',
            'api_base': 'https://api.pre.ca-cib.com'
        },
        'production': {
            'auth_base': 'https://usignon.ca-cib.com',
            'api_base': 'https://api.ca-cib.com'
        }
    }

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str,
                 environment: str = 'sandbox'):
        """
        Initialise le service Crédit Agricole

        Args:
            client_id: Identifiant client OAuth2
            client_secret: Secret client OAuth2
            redirect_uri: URI de redirection après authentification
            environment: Environnement ('sandbox' ou 'production')
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.environment = environment

        env_config = self.ENVIRONMENTS.get(environment, self.ENVIRONMENTS['sandbox'])
        self.auth_base_url = env_config['auth_base']
        self.api_base_url = env_config['api_base']

        # Stockage des tokens en mémoire (à remplacer par un stockage persistant en prod)
        self._tokens: Dict[str, Dict] = {}

        # État PKCE pour sécurité renforcée
        self._pkce_states: Dict[str, Dict] = {}

        logger.info(f"CreditAgricoleService initialisé en mode {environment}")

    def _generate_pkce_verifier(self) -> tuple:
        """
        Génère un code verifier et challenge PKCE pour sécuriser le flux OAuth2

        Returns:
            tuple: (code_verifier, code_challenge)
        """
        code_verifier = secrets.token_urlsafe(64)[:128]
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        return code_verifier, code_challenge

    def build_authorize_url(self, user_id: str, scopes: List[str] = None) -> Dict[str, str]:
        """
        Construit l'URL d'autorisation OAuth2

        Args:
            user_id: Identifiant de l'utilisateur dans FLOOSE
            scopes: Liste des scopes demandés

        Returns:
            dict: Contenant 'url' et 'state' pour vérification ultérieure
        """
        if scopes is None:
            scopes = ['openid', 'profile', 'accounts', 'transactions']

        state = secrets.token_urlsafe(32)
        code_verifier, code_challenge = self._generate_pkce_verifier()

        # Stocker l'état pour vérification lors du callback
        self._pkce_states[state] = {
            'user_id': user_id,
            'code_verifier': code_verifier,
            'created_at': datetime.now(),
            'scopes': scopes
        }

        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(scopes),
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }

        url = f"{self.auth_base_url}/IdPOAuth2/authorize/idp1?" + urllib.parse.urlencode(params)

        logger.info(f"URL d'autorisation générée pour l'utilisateur {user_id}")

        return {
            'url': url,
            'state': state
        }

    def exchange_code_for_token(self, code: str, state: str) -> Dict[str, Any]:
        """
        Échange le code d'autorisation contre des tokens d'accès

        Args:
            code: Code d'autorisation reçu du callback
            state: État pour vérification CSRF

        Returns:
            dict: Tokens d'accès et informations associées

        Raises:
            CreditAgricoleError: Si l'échange échoue
        """
        # Vérifier l'état PKCE
        pkce_data = self._pkce_states.get(state)
        if not pkce_data:
            raise CreditAgricoleError(
                "État invalide ou expiré",
                error_code="INVALID_STATE"
            )

        # Vérifier l'expiration (15 minutes max)
        if datetime.now() - pkce_data['created_at'] > timedelta(minutes=15):
            del self._pkce_states[state]
            raise CreditAgricoleError(
                "Session d'autorisation expirée",
                error_code="STATE_EXPIRED"
            )

        url = f"{self.auth_base_url}/IdPOAuth2/token/idp1"

        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'code_verifier': pkce_data['code_verifier']
        }

        # Authentification Basic pour le client
        auth_string = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        headers = {
            'Authorization': f'Basic {auth_string}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        try:
            response = requests.post(url, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            token_data = response.json()

            # Stocker les tokens pour l'utilisateur
            user_id = pkce_data['user_id']
            self._tokens[user_id] = {
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'token_type': token_data.get('token_type', 'Bearer'),
                'expires_at': datetime.now() + timedelta(
                    seconds=token_data.get('expires_in', 3600)
                ),
                'scopes': pkce_data['scopes']
            }

            # Nettoyer l'état PKCE
            del self._pkce_states[state]

            logger.info(f"Tokens obtenus avec succès pour l'utilisateur {user_id}")

            return {
                'success': True,
                'user_id': user_id,
                'expires_in': token_data.get('expires_in', 3600),
                'scopes': pkce_data['scopes']
            }

        except requests.exceptions.HTTPError as e:
            logger.error(f"Erreur HTTP lors de l'échange de token: {e}")
            raise CreditAgricoleError(
                "Erreur lors de l'authentification",
                error_code="TOKEN_EXCHANGE_FAILED",
                details={'http_error': str(e)}
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur réseau lors de l'échange de token: {e}")
            raise CreditAgricoleError(
                "Erreur de connexion au serveur Crédit Agricole",
                error_code="NETWORK_ERROR",
                details={'error': str(e)}
            )

    def refresh_token(self, user_id: str) -> bool:
        """
        Rafraîchit le token d'accès

        Args:
            user_id: Identifiant de l'utilisateur

        Returns:
            bool: True si le rafraîchissement a réussi
        """
        token_data = self._tokens.get(user_id)
        if not token_data or not token_data.get('refresh_token'):
            return False

        url = f"{self.auth_base_url}/IdPOAuth2/token/idp1"

        data = {
            'grant_type': 'refresh_token',
            'refresh_token': token_data['refresh_token'],
            'client_id': self.client_id
        }

        auth_string = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        headers = {
            'Authorization': f'Basic {auth_string}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        try:
            response = requests.post(url, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            new_token_data = response.json()

            self._tokens[user_id].update({
                'access_token': new_token_data.get('access_token'),
                'expires_at': datetime.now() + timedelta(
                    seconds=new_token_data.get('expires_in', 3600)
                )
            })

            if new_token_data.get('refresh_token'):
                self._tokens[user_id]['refresh_token'] = new_token_data['refresh_token']

            logger.info(f"Token rafraîchi pour l'utilisateur {user_id}")
            return True

        except Exception as e:
            logger.error(f"Erreur lors du rafraîchissement du token: {e}")
            return False

    def _get_access_token(self, user_id: str) -> Optional[str]:
        """
        Récupère un token d'accès valide pour l'utilisateur

        Args:
            user_id: Identifiant de l'utilisateur

        Returns:
            str: Token d'accès ou None
        """
        token_data = self._tokens.get(user_id)
        if not token_data:
            return None

        # Vérifier si le token est expiré
        if datetime.now() >= token_data['expires_at']:
            if not self.refresh_token(user_id):
                return None
            token_data = self._tokens.get(user_id)

        return token_data.get('access_token')

    def _api_request(self, user_id: str, method: str, endpoint: str,
                     params: dict = None, data: dict = None) -> Dict[str, Any]:
        """
        Effectue une requête à l'API Crédit Agricole

        Args:
            user_id: Identifiant de l'utilisateur
            method: Méthode HTTP (GET, POST, etc.)
            endpoint: Endpoint de l'API
            params: Paramètres de requête
            data: Corps de la requête

        Returns:
            dict: Réponse de l'API
        """
        access_token = self._get_access_token(user_id)
        if not access_token:
            raise CreditAgricoleError(
                "Non authentifié auprès du Crédit Agricole",
                error_code="NOT_AUTHENTICATED"
            )

        url = f"{self.api_base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # Token expiré, essayer de rafraîchir
                if self.refresh_token(user_id):
                    return self._api_request(user_id, method, endpoint, params, data)
            logger.error(f"Erreur API: {e}")
            raise CreditAgricoleError(
                "Erreur lors de l'appel à l'API",
                error_code="API_ERROR",
                details={'status_code': e.response.status_code}
            )

    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        Récupère les informations de l'utilisateur connecté

        Args:
            user_id: Identifiant de l'utilisateur FLOOSE

        Returns:
            dict: Informations utilisateur
        """
        access_token = self._get_access_token(user_id)
        if not access_token:
            raise CreditAgricoleError(
                "Non authentifié",
                error_code="NOT_AUTHENTICATED"
            )

        url = f"{self.auth_base_url}/IdPOAuth2/userinfo/idp1"
        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des infos utilisateur: {e}")
            raise CreditAgricoleError(
                "Impossible de récupérer les informations utilisateur",
                error_code="USERINFO_ERROR"
            )

    def get_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Récupère la liste des comptes bancaires de l'utilisateur

        Args:
            user_id: Identifiant de l'utilisateur FLOOSE

        Returns:
            list: Liste des comptes bancaires
        """
        try:
            response = self._api_request(user_id, 'GET', '/psd2/v1/accounts')
            accounts = response.get('accounts', [])

            # Formater les comptes pour FLOOSE
            formatted_accounts = []
            for account in accounts:
                formatted_accounts.append({
                    'id_externe': account.get('resourceId'),
                    'iban': account.get('iban'),
                    'nom': account.get('name', 'Compte Crédit Agricole'),
                    'type': self._map_account_type(account.get('cashAccountType')),
                    'devise': account.get('currency', 'EUR'),
                    'solde': self._get_account_balance(account),
                    'banque': 'Crédit Agricole',
                    'statut': account.get('status', 'enabled')
                })

            logger.info(f"Récupéré {len(formatted_accounts)} comptes pour l'utilisateur {user_id}")
            return formatted_accounts

        except CreditAgricoleError:
            raise
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des comptes: {e}")
            raise CreditAgricoleError(
                "Impossible de récupérer les comptes",
                error_code="ACCOUNTS_ERROR"
            )

    def _map_account_type(self, ca_type: str) -> str:
        """Mappe le type de compte CA vers le type FLOOSE"""
        mapping = {
            'CACC': 'Courant',
            'SVGS': 'Épargne',
            'INVS': 'Investissement',
            'LOAN': 'Crédit'
        }
        return mapping.get(ca_type, 'Courant')

    def _get_account_balance(self, account: dict) -> float:
        """Extrait le solde d'un compte"""
        balances = account.get('balances', [])
        for balance in balances:
            if balance.get('balanceType') in ['closingBooked', 'expected']:
                return float(balance.get('balanceAmount', {}).get('amount', 0))
        return 0.0

    def get_transactions(self, user_id: str, account_id: str,
                        date_from: str = None, date_to: str = None) -> List[Dict[str, Any]]:
        """
        Récupère les transactions d'un compte

        Args:
            user_id: Identifiant de l'utilisateur FLOOSE
            account_id: Identifiant externe du compte (resourceId)
            date_from: Date de début (format YYYY-MM-DD)
            date_to: Date de fin (format YYYY-MM-DD)

        Returns:
            list: Liste des transactions
        """
        params = {}
        if date_from:
            params['dateFrom'] = date_from
        if date_to:
            params['dateTo'] = date_to

        try:
            response = self._api_request(
                user_id, 'GET',
                f'/psd2/v1/accounts/{account_id}/transactions',
                params=params
            )

            transactions = response.get('transactions', {})
            booked = transactions.get('booked', [])
            pending = transactions.get('pending', [])

            # Formater les transactions pour FLOOSE
            formatted = []

            for tx in booked:
                formatted.append(self._format_transaction(tx, 'validée'))

            for tx in pending:
                formatted.append(self._format_transaction(tx, 'en_attente'))

            # Trier par date décroissante
            formatted.sort(key=lambda x: x['date'], reverse=True)

            logger.info(f"Récupéré {len(formatted)} transactions pour le compte {account_id}")
            return formatted

        except CreditAgricoleError:
            raise
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des transactions: {e}")
            raise CreditAgricoleError(
                "Impossible de récupérer les transactions",
                error_code="TRANSACTIONS_ERROR"
            )

    def _format_transaction(self, tx: dict, statut: str) -> Dict[str, Any]:
        """Formate une transaction CA pour FLOOSE"""
        amount_data = tx.get('transactionAmount', {})
        amount = float(amount_data.get('amount', 0))

        return {
            'id_externe': tx.get('transactionId'),
            'date': tx.get('bookingDate') or tx.get('valueDate'),
            'montant': abs(amount),
            'type': 'crédit' if amount > 0 else 'débit',
            'description': tx.get('remittanceInformationUnstructured',
                                 tx.get('creditorName', 'Transaction')),
            'categorie': self._guess_category(tx),
            'statut': statut,
            'devise': amount_data.get('currency', 'EUR'),
            'reference': tx.get('endToEndId')
        }

    def _guess_category(self, tx: dict) -> str:
        """Tente de deviner la catégorie d'une transaction"""
        description = (tx.get('remittanceInformationUnstructured', '') or '').lower()
        creditor = (tx.get('creditorName', '') or '').lower()

        # Règles simples de catégorisation
        categories = {
            'Alimentation': ['carrefour', 'leclerc', 'auchan', 'lidl', 'intermarche', 'monoprix'],
            'Transport': ['sncf', 'ratp', 'uber', 'bolt', 'essence', 'total', 'shell'],
            'Logement': ['loyer', 'edf', 'engie', 'veolia', 'eau', 'electricite'],
            'Santé': ['pharmacie', 'medecin', 'hopital', 'mutuelle'],
            'Loisirs': ['netflix', 'spotify', 'cinema', 'amazon', 'fnac'],
            'Restauration': ['restaurant', 'mcdo', 'deliveroo', 'uber eats'],
        }

        combined = f"{description} {creditor}"
        for category, keywords in categories.items():
            if any(keyword in combined for keyword in keywords):
                return category

        return 'Autre'

    def is_connected(self, user_id: str) -> bool:
        """
        Vérifie si l'utilisateur est connecté au Crédit Agricole

        Args:
            user_id: Identifiant de l'utilisateur

        Returns:
            bool: True si connecté avec un token valide
        """
        token_data = self._tokens.get(user_id)
        if not token_data:
            return False

        # Vérifier si le token est encore valide (avec marge de 5 minutes)
        if datetime.now() >= token_data['expires_at'] - timedelta(minutes=5):
            # Essayer de rafraîchir
            return self.refresh_token(user_id)

        return True

    def disconnect(self, user_id: str) -> bool:
        """
        Déconnecte l'utilisateur du Crédit Agricole

        Args:
            user_id: Identifiant de l'utilisateur

        Returns:
            bool: True si la déconnexion a réussi
        """
        if user_id in self._tokens:
            del self._tokens[user_id]
            logger.info(f"Utilisateur {user_id} déconnecté du Crédit Agricole")
            return True
        return False

    def get_connection_status(self, user_id: str) -> Dict[str, Any]:
        """
        Retourne le statut de connexion détaillé

        Args:
            user_id: Identifiant de l'utilisateur

        Returns:
            dict: Informations sur le statut de connexion
        """
        token_data = self._tokens.get(user_id)

        if not token_data:
            return {
                'connected': False,
                'bank': 'Crédit Agricole',
                'message': 'Non connecté'
            }

        expires_at = token_data['expires_at']
        is_valid = datetime.now() < expires_at

        return {
            'connected': is_valid,
            'bank': 'Crédit Agricole',
            'expires_at': expires_at.isoformat() if is_valid else None,
            'scopes': token_data.get('scopes', []),
            'message': 'Connecté' if is_valid else 'Session expirée'
        }


# Instance globale du service (initialisée par l'application)
_ca_service: Optional[CreditAgricoleService] = None


def get_credit_agricole_service() -> Optional[CreditAgricoleService]:
    """Retourne l'instance globale du service Crédit Agricole"""
    return _ca_service


def init_credit_agricole_service(client_id: str, client_secret: str,
                                  redirect_uri: str, environment: str = 'sandbox'):
    """
    Initialise l'instance globale du service Crédit Agricole

    Args:
        client_id: Identifiant client OAuth2
        client_secret: Secret client OAuth2
        redirect_uri: URI de redirection
        environment: Environnement ('sandbox' ou 'production')
    """
    global _ca_service
    _ca_service = CreditAgricoleService(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        environment=environment
    )
    logger.info("Service Crédit Agricole initialisé globalement")
    return _ca_service
