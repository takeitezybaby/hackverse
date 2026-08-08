"""
app/personalization package — Layer 3 Personalization & Recommendation Engine.
"""

from .profile import get_user_profile
from .allocator import generate_user_recommendations

__all__ = ["get_user_profile", "generate_user_recommendations"]
