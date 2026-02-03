"""
Gestionnaire de verrous pour les fichiers CSV
Gestion de la concurrence et prévention des corruptions de données
"""

import os
import time
import threading
from filelock import FileLock
from contextlib import contextmanager
from typing import Dict, Optional
import logging


class FileLockManager:
    """
    Gestionnaire centralisé des verrous de fichiers
    Thread-safe et prévient les corruptions de données
    """
    
    def __init__(self, lock_dir: str = "locks", timeout: float = 30.0):
        """
        Initialise le gestionnaire de verrous
        
        Args:
            lock_dir (str): Répertoire pour les fichiers de verrous
            timeout (float): Timeout en secondes pour l'acquisition des verrous
        """
        self.lock_dir = lock_dir
        self.timeout = timeout
        self.locks: Dict[str, FileLock] = {}
        self.lock_creation_lock = threading.Lock()
        
        # Créer le répertoire des verrous
        os.makedirs(lock_dir, exist_ok=True)
        
        # Configuration du logging
        self.logger = logging.getLogger(__name__)
    
    def _get_lock_for_file(self, filepath: str) -> FileLock:
        """
        Récupère ou crée un verrou pour un fichier donné
        Thread-safe avec lazy loading
        
        Args:
            filepath (str): Chemin du fichier à verrouiller
            
        Returns:
            FileLock: Instance de verrou pour le fichier
        """
        normalized_path = os.path.abspath(filepath)
        
        # Utiliser un verrou pour la création des verrous (évite les race conditions)
        with self.lock_creation_lock:
            if normalized_path not in self.locks:
                # Créer le nom du fichier de verrou
                lock_filename = os.path.basename(normalized_path) + '.lock'
                lock_filepath = os.path.join(self.lock_dir, lock_filename)
                
                # Créer le verrou
                self.locks[normalized_path] = FileLock(lock_filepath, timeout=self.timeout)
                self.logger.debug(f"Créé verrou pour {normalized_path}")
            
            return self.locks[normalized_path]
    
    @contextmanager
    def acquire_lock(self, filepath: str, operation: str = "unknown"):
        """
        Context manager pour acquérir un verrou de fichier
        
        Args:
            filepath (str): Chemin du fichier à verrouiller
            operation (str): Description de l'opération (pour logging)
            
        Yields:
            None: Le verrou est acquis dans le bloc
            
        Raises:
            TimeoutError: Si le verrou ne peut pas être acquis dans le timeout
        """
        file_lock = self._get_lock_for_file(filepath)
        
        try:
            self.logger.debug(f"Tentative d'acquisition verrou pour {filepath} ({operation})")
            start_time = time.time()
            
            with file_lock:
                acquisition_time = time.time() - start_time
                self.logger.debug(f"Verrou acquis pour {filepath} en {acquisition_time:.3f}s")
                yield
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'acquisition du verrou pour {filepath}: {e}")
            raise
        finally:
            self.logger.debug(f"Verrou relâché pour {filepath}")
    
    def is_locked(self, filepath: str) -> bool:
        """
        Vérifie si un fichier est actuellement verrouillé
        
        Args:
            filepath (str): Chemin du fichier à vérifier
            
        Returns:
            bool: True si le fichier est verrouillé
        """
        try:
            file_lock = self._get_lock_for_file(filepath)
            return file_lock.is_locked
        except Exception:
            return False
    
    def cleanup_locks(self):
        """
        Nettoie les verrous non utilisés et les fichiers de verrous obsolètes
        """
        with self.lock_creation_lock:
            # Nettoyer les verrous en mémoire
            active_locks = {path: lock for path, lock in self.locks.items() if lock.is_locked}
            released_count = len(self.locks) - len(active_locks)
            self.locks = active_locks
            
            if released_count > 0:
                self.logger.info(f"Nettoyé {released_count} verrous inactifs")
            
            # Nettoyer les fichiers de verrous orphelins
            try:
                for filename in os.listdir(self.lock_dir):
                    if filename.endswith('.lock'):
                        lock_path = os.path.join(self.lock_dir, filename)
                        try:
                            # Tenter de supprimer les fichiers de verrous non actifs
                            os.remove(lock_path)
                            self.logger.debug(f"Supprimé fichier de verrou orphelin: {filename}")
                        except OSError:
                            # Fichier probablement encore en cours d'utilisation
                            pass
            except OSError as e:
                self.logger.warning(f"Erreur lors du nettoyage des verrous: {e}")
    
    def get_lock_stats(self) -> Dict[str, any]:
        """
        Retourne des statistiques sur l'utilisation des verrous
        
        Returns:
            dict: Statistiques des verrous
        """
        with self.lock_creation_lock:
            total_locks = len(self.locks)
            active_locks = sum(1 for lock in self.locks.values() if lock.is_locked)
            
            return {
                'total_locks': total_locks,
                'active_locks': active_locks,
                'inactive_locks': total_locks - active_locks,
                'lock_dir': self.lock_dir,
                'timeout': self.timeout
            }


# Instance globale du gestionnaire de verrous
_lock_manager: Optional[FileLockManager] = None


def get_lock_manager() -> FileLockManager:
    """
    Récupère l'instance globale du gestionnaire de verrous (Singleton)
    
    Returns:
        FileLockManager: Instance du gestionnaire de verrous
    """
    global _lock_manager
    if _lock_manager is None:
        _lock_manager = FileLockManager()
    return _lock_manager


@contextmanager
def file_operation_lock(filepath: str, operation: str = "file_operation"):
    """
    Context manager simplifié pour les opérations de fichiers
    
    Args:
        filepath (str): Chemin du fichier
        operation (str): Description de l'opération
    """
    lock_manager = get_lock_manager()
    with lock_manager.acquire_lock(filepath, operation):
        yield


# Décorateur pour les méthodes nécessitant un verrou de fichier
def requires_file_lock(filepath_param: str = 'filepath'):
    """
    Décorateur pour automatiquement acquérir un verrou de fichier
    
    Args:
        filepath_param (str): Nom du paramètre contenant le chemin du fichier
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extraire le chemin du fichier des arguments
            if filepath_param in kwargs:
                filepath = kwargs[filepath_param]
            elif hasattr(args[0], 'data_dir') and len(args) > 1:
                # Pour les méthodes de classe avec data_dir
                filepath = os.path.join(args[0].data_dir, args[1])
            else:
                # Fallback - pas de protection par verrou
                return func(*args, **kwargs)
            
            # Acquérir le verrou et exécuter la fonction
            with file_operation_lock(filepath, func.__name__):
                return func(*args, **kwargs)
                
        return wrapper
    return decorator