"""
Routes d'authentification FLOOSE
Login, Register, Logout, Sign in with Apple
"""

from flask import Blueprint, jsonify, request, session, redirect, url_for, render_template
import logging
import jwt
import time
import hashlib
import os

from services import (
    get_auth_manager,
    performance_monitor
)

logger = logging.getLogger(__name__)

# Blueprint pour les routes d'authentification
auth_bp = Blueprint('auth', __name__)

# Configuration Apple Sign In (a configurer dans .env)
APPLE_CLIENT_ID = os.environ.get('APPLE_CLIENT_ID', 'com.floose.app')
APPLE_TEAM_ID = os.environ.get('APPLE_TEAM_ID', '')
APPLE_KEY_ID = os.environ.get('APPLE_KEY_ID', '')
APPLE_REDIRECT_URI = os.environ.get('APPLE_REDIRECT_URI', 'http://localhost:5003/auth/apple/callback')


# ============================================================
# PAGES
# ============================================================

@auth_bp.route('/login')
def login_page():
    """
    Page de connexion
    """
    if 'user_email' in session:
        return redirect(url_for('index'))

    # Generer un state pour Apple Sign In (protection CSRF)
    apple_state = hashlib.sha256(os.urandom(32)).hexdigest()
    session['apple_auth_state'] = apple_state

    return render_template('login.html', apple_state=apple_state)


@auth_bp.route('/register')
def register_page():
    """
    Page de creation de compte
    """
    if 'user_email' in session:
        return redirect(url_for('index'))
    return render_template('register.html')


# ============================================================
# LOGIN / LOGOUT
# ============================================================

@auth_bp.route('/login', methods=['POST'])
@performance_monitor('login_attempt')
def login():
    """
    Traitement de la connexion

    Accepts both form data and JSON
    """
    # Support JSON ou form data
    if request.is_json:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
    else:
        email = request.form.get('email')
        password = request.form.get('password')

    ip_address = request.environ.get('REMOTE_ADDR', 'unknown')

    auth_manager = get_auth_manager()
    result = auth_manager.authenticate_user(email, password, ip_address)

    if result['success']:
        # Creer la session
        user_data = result['user']
        session.permanent = True
        session['user_email'] = user_data['email']
        session['user_name'] = user_data['name']
        session['user_avatar'] = user_data['avatar']
        session['jwt_token'] = result['token']
        session['login_provider'] = 'email'
        session['login_time'] = time.time()

        logger.info(f"Connexion reussie pour {email}")

        if request.is_json:
            return jsonify({
                'success': True,
                'user': user_data,
                'token': result['token'],
                'redirect': url_for('index')
            })

        return redirect(url_for('index'))

    else:
        error_message = result['error']
        if 'remaining_attempts' in result and result['remaining_attempts'] > 0:
            error_message += f" ({result['remaining_attempts']} tentatives restantes)"

        logger.warning(f"Echec de connexion pour {email}: {result.get('error_code')}")

        if request.is_json:
            return jsonify({
                'success': False,
                'error': error_message,
                'error_code': result.get('error_code')
            }), 401

        return render_template('login.html', error=error_message)


@auth_bp.route('/logout')
def logout():
    """
    Deconnexion de l'utilisateur
    Nettoie completement la session
    """
    user_email = session.get('user_email', 'unknown')
    provider = session.get('login_provider', 'unknown')

    # Nettoyer completement la session
    session.clear()

    logger.info(f"Deconnexion: {user_email} (provider: {provider})")

    # Rediriger vers la page de login
    return redirect(url_for('auth.login_page'))


@auth_bp.route('/logout', methods=['POST'])
def logout_api():
    """
    Deconnexion via API (pour les appels AJAX)
    """
    user_email = session.get('user_email', 'unknown')
    session.clear()

    logger.info(f"Deconnexion API: {user_email}")

    return jsonify({
        'success': True,
        'message': 'Deconnexion reussie',
        'redirect': url_for('auth.login_page')
    })


# ============================================================
# REGISTER
# ============================================================

@auth_bp.route('/register', methods=['POST'])
@performance_monitor('register_attempt')
def register():
    """
    Creation d'un nouveau compte
    """
    if request.is_json:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        password_confirm = data.get('password_confirm')
        name = data.get('name')
    else:
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        name = request.form.get('name')

    # Validations
    errors = []

    if not email or '@' not in email:
        errors.append('Email invalide')

    if not name or len(name) < 2:
        errors.append('Nom requis (minimum 2 caracteres)')

    if not password or len(password) < 8:
        errors.append('Mot de passe requis (minimum 8 caracteres)')

    if password != password_confirm:
        errors.append('Les mots de passe ne correspondent pas')

    if errors:
        error_message = '. '.join(errors)
        if request.is_json:
            return jsonify({
                'success': False,
                'error': error_message,
                'errors': errors
            }), 400
        return render_template('register.html', error=error_message)

    # Creer l'utilisateur
    auth_manager = get_auth_manager()
    result = auth_manager.create_user(email, password, name)

    if result['success']:
        logger.info(f"Nouveau compte cree: {email}")

        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Compte cree avec succes',
                'redirect': url_for('auth.login_page')
            })

        return render_template('login.html',
                             success='Compte cree avec succes. Vous pouvez vous connecter.')

    else:
        logger.warning(f"Echec creation compte {email}: {result.get('error')}")

        if request.is_json:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400

        return render_template('register.html', error=result['error'])


# ============================================================
# SIGN IN WITH APPLE
# ============================================================

@auth_bp.route('/auth/apple')
def apple_auth_start():
    """
    Demarre le flux Sign in with Apple
    Redirige vers la page d'autorisation Apple
    """
    # Generer un state pour protection CSRF
    state = hashlib.sha256(os.urandom(32)).hexdigest()
    session['apple_auth_state'] = state

    # Construire l'URL d'autorisation Apple
    apple_auth_url = (
        "https://appleid.apple.com/auth/authorize?"
        f"client_id={APPLE_CLIENT_ID}&"
        f"redirect_uri={APPLE_REDIRECT_URI}&"
        "response_type=code id_token&"
        "scope=name email&"
        "response_mode=form_post&"
        f"state={state}"
    )

    logger.info("Redirection vers Apple Sign In")
    return redirect(apple_auth_url)


@auth_bp.route('/auth/apple/callback', methods=['GET', 'POST'])
def apple_auth_callback():
    """
    Callback Apple Sign In
    Recoit le code d'autorisation et le token ID d'Apple
    """
    # Apple envoie les donnees en POST (form_post)
    if request.method == 'POST':
        code = request.form.get('code')
        id_token = request.form.get('id_token')
        state = request.form.get('state')
        user_data = request.form.get('user')  # Donnees utilisateur (premier login seulement)
        error = request.form.get('error')
    else:
        # Fallback GET pour les tests
        code = request.args.get('code')
        id_token = request.args.get('id_token')
        state = request.args.get('state')
        user_data = request.args.get('user')
        error = request.args.get('error')

    # Verifier les erreurs
    if error:
        logger.error(f"Erreur Apple Sign In: {error}")
        return render_template('login.html', error=f"Erreur Apple: {error}")

    # Verifier le state (protection CSRF)
    expected_state = session.get('apple_auth_state')
    if state and expected_state and state != expected_state:
        logger.error("State Apple invalide - possible attaque CSRF")
        return render_template('login.html', error="Erreur de securite. Veuillez reessayer.")

    # Decoder le token ID pour obtenir les infos utilisateur
    if id_token:
        try:
            # Decoder sans verification (en prod, verifier avec la cle publique Apple)
            decoded = jwt.decode(id_token, options={"verify_signature": False})

            apple_user_id = decoded.get('sub')
            email = decoded.get('email', f"{apple_user_id}@privaterelay.appleid.com")
            email_verified = decoded.get('email_verified', False)

            # Extraire le nom si disponible (premier login seulement)
            name = "Utilisateur Apple"
            if user_data:
                import json
                try:
                    user_info = json.loads(user_data)
                    first_name = user_info.get('name', {}).get('firstName', '')
                    last_name = user_info.get('name', {}).get('lastName', '')
                    if first_name or last_name:
                        name = f"{first_name} {last_name}".strip()
                except (json.JSONDecodeError, TypeError):
                    pass

            # Creer ou connecter l'utilisateur
            auth_manager = get_auth_manager()

            # Verifier si l'utilisateur existe
            existing_user = auth_manager.users.get(email.lower())

            if not existing_user:
                # Creer un nouveau compte pour cet utilisateur Apple
                import secrets
                temp_password = secrets.token_urlsafe(32)
                result = auth_manager.create_user(
                    email=email,
                    password=temp_password,
                    name=name,
                    avatar=name[:2].upper() if name else "AP"
                )
                if not result['success']:
                    logger.error(f"Erreur creation compte Apple: {result.get('error')}")
                    return render_template('login.html', error="Erreur lors de la creation du compte")

            # Creer la session
            session.permanent = True
            session['user_email'] = email
            session['user_name'] = name
            session['user_avatar'] = name[:2].upper() if name else "AP"
            session['login_provider'] = 'apple'
            session['apple_user_id'] = apple_user_id
            session['login_time'] = time.time()

            # Nettoyer le state
            session.pop('apple_auth_state', None)

            logger.info(f"Connexion Apple reussie: {email}")
            return redirect(url_for('index'))

        except jwt.DecodeError as e:
            logger.error(f"Erreur decodage token Apple: {e}")
            return render_template('login.html', error="Erreur de verification Apple")

    # Fallback: mode demo/test
    if request.args.get('demo') == 'true' or request.args.get('user') == 'apple_demo':
        session.permanent = True
        session['user_email'] = 'apple.user@privaterelay.appleid.com'
        session['user_name'] = 'Apple User'
        session['user_avatar'] = 'AU'
        session['login_provider'] = 'apple'
        session['login_time'] = time.time()

        logger.info("Connexion Apple demo reussie")
        return redirect(url_for('index'))

    return render_template('login.html', error="Erreur lors de la connexion Apple")


# ============================================================
# API STATUS
# ============================================================

@auth_bp.route('/api/auth/status')
def auth_status():
    """
    Verifie le statut d'authentification
    """
    if 'user_email' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'email': session.get('user_email'),
                'name': session.get('user_name'),
                'avatar': session.get('user_avatar'),
                'provider': session.get('login_provider', 'email')
            },
            'login_time': session.get('login_time')
        })

    return jsonify({
        'authenticated': False
    })


@auth_bp.route('/api/auth/validate-token', methods=['POST'])
def validate_token():
    """
    Valide un token JWT
    """
    data = request.get_json()
    token = data.get('token')

    if not token:
        return jsonify({
            'valid': False,
            'error': 'Token manquant'
        }), 400

    auth_manager = get_auth_manager()
    user_data = auth_manager.validate_session_token(token)

    if user_data:
        return jsonify({
            'valid': True,
            'user': user_data
        })

    return jsonify({
        'valid': False,
        'error': 'Token invalide ou expire'
    }), 401
