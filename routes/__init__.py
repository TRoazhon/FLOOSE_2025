"""
Routes FLOOSE
"""

from .banking import banking_bp
from .auth import auth_bp

__all__ = ['banking_bp', 'auth_bp']
