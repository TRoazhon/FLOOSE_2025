"""
Gestionnaire d'Authentification pour FLOOSE
Avec stockage SQL, hachage bcrypt et tokens JWT
"""

import os
import jwt
import bcrypt
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from functools import wraps
from flask import session, request, jsonify, redirect, url_for

from .data_manager import DataManager

logger = logging.getLogger(__name__)


class AuthManager:
    """
    Gestionnaire d'authentification securise avec stockage SQL
    """

    def __init__(self, secret_key: str = None, jwt_expiry_hours: int = 24):
        """
        Initialise le gestionnaire d'authentification

        Args:
            secret_key: Cle secrete pour JWT
            jwt_expiry_hours: Duree d'expiration des tokens JWT en heures
        """
        self.secret_key = secret_key or os.environ.get('JWT_SECRET_KEY', 'dev-secret-key')
        self.jwt_expiry_hours = jwt_expiry_hours
        self.max_login_attempts = 5
        self.lockout_duration = timedelta(minutes=30)

        # Data manager for user operations
        self.data_manager = DataManager()

        # Compatibilite avec l'ancien code (acces direct aux users)
        self._users_cache = {}

        # Initialiser les utilisateurs de demo
        self._initialize_demo_users()

        logger.info("AuthManager initialise avec SQLAlchemy")

    @property
    def users(self) -> Dict[str, Any]:
        """Compatibilite avec l'ancien code - retourne un dict-like"""
        return self._UsersProxy(self.data_manager)

    class _UsersProxy:
        """Proxy pour acceder aux utilisateurs comme un dict"""
        def __init__(self, data_manager: DataManager):
            self.dm = data_manager

        def get(self, email: str, default=None):
            user = self.dm.get_user_by_email(email)
            if user:
                return self._to_user_object(user)
            return default

        def __contains__(self, email: str) -> bool:
            return self.dm.get_user_by_email(email) is not None

        def _to_user_object(self, user_dict: Dict) -> Any:
            """Convertit un dict en objet User-like"""
            class UserObject:
                pass
            obj = UserObject()
            for k, v in user_dict.items():
                setattr(obj, k, v)
            return obj

    def _initialize_demo_users(self):
        """Initialise les utilisateurs de demonstration"""
        demo_users = [
            {
                'email': 'demo@floose.com',
                'password': 'Demo123!',
                'name': 'Demo User',
                'avatar': 'DU'
            },
            {
                'email': 'admin@floose.com',
                'password': 'Admin123!',
                'name': 'Administrator',
                'avatar': 'AD'
            },
            {
                'email': 'john.doe@example.com',
                'password': 'Password123!',
                'name': 'John Doe',
                'avatar': 'JD'
            }
        ]

        count = 0
        for user_data in demo_users:
            existing = self.user_repo.get_by_email(user_data['email'])
            if not existing:
                password_hash = self._hash_password(user_data['password'])
                self.user_repo.create(
                    id=user_data['email'],
                    email=user_data['email'],
                    name=user_data['name'],
                    password_hash=password_hash,
                    avatar=user_data['avatar']
                )
                count += 1

        if count > 0:
            logger.info(f"Initialise {count} utilisateurs de demonstration")

    def _hash_password(self, password: str) -> str:
        """Hache un mot de passe avec bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verifie un mot de passe contre son hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception as e:
            logger.error(f"Erreur lors de la verification du mot de passe: {e}")
            return False

    def _generate_jwt_token(self, user: Dict) -> str:
        """Genere un token JWT pour un utilisateur"""
        payload = {
            'user_id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'avatar': user.get('avatar', 'U'),
            'exp': datetime.utcnow() + timedelta(hours=self.jwt_expiry_hours),
            'iat': datetime.utcnow(),
            'type': 'access_token'
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')

    def _validate_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Valide et decode un token JWT"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])

            # Verifier que l'utilisateur existe toujours
            user = self.user_repo.get_by_id(payload['user_id'])
            if not user:
                return None

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token JWT expire")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token JWT invalide: {e}")
            return None

    def _is_user_locked_out(self, user: Dict) -> bool:
        """Verifie si un utilisateur est verrouille"""
        if user.get('login_attempts', 0) >= self.max_login_attempts:
            last_login = user.get('last_login')
            if last_login:
                if isinstance(last_login, str):
                    last_login = datetime.fromisoformat(last_login)
                time_since_last_attempt = datetime.now() - last_login
                return time_since_last_attempt < self.lockout_duration
            return True
        return False

    def authenticate_user(self, email: str, password: str, ip_address: str = None) -> Dict[str, Any]:
        """
        Authentifie un utilisateur

        Args:
            email: Email de l'utilisateur
            password: Mot de passe
            ip_address: Adresse IP pour le logging

        Returns:
            dict: Resultat de l'authentification
        """
        if not email or not password:
            return {
                'success': False,
                'error': 'Email et mot de passe requis',
                'error_code': 'MISSING_CREDENTIALS'
            }

        # Recuperer l'utilisateur
        user = self.user_repo.get_by_email(email.lower())
        if not user:
            logger.warning(f"Tentative de connexion avec email inexistant: {email} depuis {ip_address}")
            return {
                'success': False,
                'error': 'Identifiants incorrects',
                'error_code': 'INVALID_CREDENTIALS'
            }

        # Verifier si l'utilisateur est verrouille
        if self._is_user_locked_out(user):
            logger.warning(f"Tentative de connexion sur compte verrouille: {email}")
            return {
                'success': False,
                'error': 'Compte temporairement verrouille. Reessayez plus tard.',
                'error_code': 'ACCOUNT_LOCKED'
            }

        # Verifier le mot de passe
        if not self._verify_password(password, user['password_hash']):
            # Incrementer les tentatives echouees
            new_attempts = user.get('login_attempts', 0) + 1
            self.user_repo.update_login_attempts(user['id'], new_attempts, datetime.now())

            logger.warning(f"Mot de passe incorrect pour {email} (tentative {new_attempts})")

            return {
                'success': False,
                'error': 'Identifiants incorrects',
                'error_code': 'INVALID_CREDENTIALS',
                'remaining_attempts': max(0, self.max_login_attempts - new_attempts)
            }

        # Connexion reussie
        self.user_repo.update_login_attempts(user['id'], 0, datetime.now())

        # Generer le token JWT
        token = self._generate_jwt_token(user)

        logger.info(f"Connexion reussie pour {email} depuis {ip_address}")

        return {
            'success': True,
            'token': token,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'avatar': user.get('avatar', 'U')
            }
        }

    def validate_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Valide un token de session"""
        payload = self._validate_jwt_token(token)
        if payload:
            return {
                'user_id': payload['user_id'],
                'email': payload['email'],
                'name': payload['name'],
                'avatar': payload['avatar']
            }
        return None

    def create_user(self, email: str, password: str, name: str, avatar: str = None) -> Dict[str, Any]:
        """
        Cree un nouvel utilisateur

        Args:
            email: Email de l'utilisateur
            password: Mot de passe
            name: Nom complet
            avatar: Avatar/initiales

        Returns:
            dict: Resultat de la creation
        """
        if not email or not password or not name:
            return {
                'success': False,
                'error': 'Email, mot de passe et nom requis'
            }

        # Verifier si l'utilisateur existe deja
        existing = self.user_repo.get_by_email(email.lower())
        if existing:
            return {
                'success': False,
                'error': 'Un utilisateur avec cet email existe deja'
            }

        # Validation du mot de passe
        if not self._is_password_strong(password):
            return {
                'success': False,
                'error': 'Mot de passe trop faible. Minimum 8 caracteres avec majuscule, minuscule, chiffre et caractere special.'
            }

        # Creer l'utilisateur
        password_hash = self._hash_password(password)
        avatar = avatar or name[:2].upper()

        success = self.user_repo.create(
            id=email.lower(),
            email=email.lower(),
            name=name,
            password_hash=password_hash,
            avatar=avatar
        )

        if success:
            logger.info(f"Nouvel utilisateur cree: {email}")
            return {
                'success': True,
                'user_id': email.lower()
            }

        return {
            'success': False,
            'error': 'Erreur lors de la creation du compte'
        }

    def _is_password_strong(self, password: str) -> bool:
        """Verifie la force d'un mot de passe"""
        if len(password) < 8:
            return False

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)

        return has_upper and has_lower and has_digit and has_special

    def logout_user(self, token: str = None) -> bool:
        """Deconnecte un utilisateur"""
        logger.info("Utilisateur deconnecte")
        return True

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Recupere un utilisateur par email"""
        return self.user_repo.get_by_email(email)

    def get_all_users(self):
        """Recupere tous les utilisateurs"""
        return self.user_repo.get_all()


# Instance globale
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Recupere l'instance globale du gestionnaire d'authentification"""
    global _auth_manager
    if _auth_manager is None:
        secret_key = os.environ.get('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
        _auth_manager = AuthManager(secret_key)
    return _auth_manager


def require_auth(func):
    """Decorateur pour proteger les routes necessitant une authentification"""
    @wraps(func)
    def decorated_function(*args, **kwargs):
        # Verifier le token dans les headers
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            auth_manager = get_auth_manager()
            user_data = auth_manager.validate_session_token(token)

            if user_data:
                request.current_user = user_data
                return func(*args, **kwargs)

        # Verifier la session Flask traditionnelle
        if 'user_email' in session:
            return func(*args, **kwargs)

        # Redirection vers login pour les routes web
        if request.endpoint and not request.endpoint.startswith('api'):
            return redirect(url_for('auth.login_page'))

        # Erreur JSON pour les routes API
        return jsonify({'error': 'Authentification requise'}), 401

    return decorated_function


def get_current_user() -> Optional[Dict[str, Any]]:
    """Recupere l'utilisateur actuellement connecte"""
    # Depuis le token JWT
    if hasattr(request, 'current_user'):
        return request.current_user

    # Depuis la session Flask
    if 'user_email' in session:
        return {
            'email': session.get('user_email'),
            'name': session.get('user_name'),
            'avatar': session.get('user_avatar')
        }

    return None
