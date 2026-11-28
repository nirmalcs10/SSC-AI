"""
High-Probability Option Trading Pattern Engine (Root Bridge).
Exposes PatternDetector from engine.pattern_detector for backward compatibility.
"""
from engine.pattern_detector import PatternDetector, PatternEngine

__all__ = ["PatternDetector", "PatternEngine"]
