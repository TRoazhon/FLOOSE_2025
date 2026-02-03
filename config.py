"""
Configuration de l'application FLOOSE
Gestion des variables d'environnement et paramètres
"""

import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv


class Config:
    """Configuration de base"""
    
    # Charger les variables d'environnement
    load_dotenv()
    
    # Configuration Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    FLASK_ENV = os.environ.get('FLASK_ENV') or 'development'
    DEBUG = os.environ.get('DEBUG', 'False').lower() in ['true', '1', 'on']
    
    # Configuration base de données
    DATA_DIR = os.environ.get('DATA_DIR') or 'data'
    BACKUP_DIR = os.environ.get('BACKUP_DIR') or 'backups'
    LOCK_DIR = os.environ.get('LOCK_DIR') or 'locks'
    
    # Configuration authentification
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', '24'))
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', '5'))
    LOCKOUT_DURATION_MINUTES = int(os.environ.get('LOCKOUT_DURATION_MINUTES', '30'))
    
    # Configuration performance
    CSV_CACHE_SIZE = int(os.environ.get('CSV_CACHE_SIZE', '1000'))
    FILE_LOCK_TIMEOUT = float(os.environ.get('FILE_LOCK_TIMEOUT', '30.0'))
    ENABLE_PERFORMANCE_LOGGING = os.environ.get('ENABLE_PERFORMANCE_LOGGING', 'False').lower() in ['true', '1']
    
    # Configuration logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
    LOG_FILE = os.environ.get('LOG_FILE', 'floose.log')
    ENABLE_FILE_LOGGING = os.environ.get('ENABLE_FILE_LOGGING', 'True').lower() in ['true', '1']
    
    # Configuration sécurité
    ENABLE_CSRF = os.environ.get('ENABLE_CSRF', 'True').lower() in ['true', '1']
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ['true', '1']
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configuration export
    MAX_EXPORT_RECORDS = int(os.environ.get('MAX_EXPORT_RECORDS', '10000'))
    EXPORT_TIMEOUT_SECONDS = int(os.environ.get('EXPORT_TIMEOUT_SECONDS', '300'))

    # Configuration Crédit Agricole API (DSP2/Open Banking)
    CA_CLIENT_ID = os.environ.get('CA_CLIENT_ID', '')
    CA_CLIENT_SECRET = os.environ.get('CA_CLIENT_SECRET', '')
    CA_REDIRECT_URI = os.environ.get('CA_REDIRECT_URI', 'http://localhost:5002/api/ca/callback')
    CA_ENVIRONMENT = os.environ.get('CA_ENVIRONMENT', 'sandbox')  # 'sandbox' ou 'production'
    CA_ENABLED = os.environ.get('CA_ENABLED', 'False').lower() in ['true', '1', 'on']
    
    @staticmethod
    def init_app(app):
        """Initialise la configuration Flask"""
        app.config.from_object(Config)
        
        # Configuration des cookies de session
        app.config['SESSION_COOKIE_SECURE'] = Config.SESSION_COOKIE_SECURE
        app.config['SESSION_COOKIE_HTTPONLY'] = Config.SESSION_COOKIE_HTTPONLY
        app.config['SESSION_COOKIE_SAMESITE'] = Config.SESSION_COOKIE_SAMESITE


class DevelopmentConfig(Config):
    """Configuration de développement"""
    DEBUG = True
    ENABLE_PERFORMANCE_LOGGING = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Configuration de production"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    ENABLE_CSRF = True
    LOG_LEVEL = 'WARNING'
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Configuration spécifique à la production
        import logging
        from logging.handlers import RotatingFileHandler
        
        # Configuration logging avec rotation
        if not app.debug and not app.testing:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            
            file_handler = RotatingFileHandler(
                'logs/floose.log', 
                maxBytes=10240000, 
                backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            
            app.logger.setLevel(logging.INFO)
            app.logger.info('FLOOSE startup')


class TestingConfig(Config):
    """Configuration de test"""
    TESTING = True
    DEBUG = True
    DATA_DIR = 'test_data'
    LOCK_DIR = 'test_locks'
    ENABLE_CSRF = False
    JWT_EXPIRY_HOURS = 1  # Expiration rapide pour les tests


# Mapping des configurations
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: str = None) -> Config:
    """
    Récupère la configuration selon l'environnement
    
    Args:
        config_name (str): Nom de la configuration
        
    Returns:
        Config: Instance de configuration
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    return config_map.get(config_name, DevelopmentConfig)


def setup_logging(config: Config):
    """
    Configure le système de logging
    
    Args:
        config (Config): Configuration de l'application
    """
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configuration du niveau de log
    level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    
    # Configuration de base
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Logging vers fichier si activé
    if config.ENABLE_FILE_LOGGING:
        try:
            os.makedirs('logs', exist_ok=True)
            file_handler = logging.FileHandler(f'logs/{config.LOG_FILE}')
            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(log_format))
            
            # Ajouter le handler au logger racine
            root_logger = logging.getLogger()
            root_logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"Erreur lors de la configuration du logging fichier: {e}")
    
    # Réduire la verbosité des logs externes
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def get_app_info() -> Dict[str, Any]:
    """
    Retourne les informations de l'application
    
    Returns:
        dict: Informations sur la configuration actuelle
    """
    config = get_config()
    
    return {
        'app_name': 'FLOOSE',
        'version': '1.0.0',
        'environment': os.environ.get('FLASK_ENV', 'development'),
        'debug': config.DEBUG,
        'data_dir': config.DATA_DIR,
        'log_level': config.LOG_LEVEL,
        'jwt_expiry_hours': config.JWT_EXPIRY_HOURS,
        'max_login_attempts': config.MAX_LOGIN_ATTEMPTS,
        'csv_cache_size': config.CSV_CACHE_SIZE,
        'performance_logging': config.ENABLE_PERFORMANCE_LOGGING
    }