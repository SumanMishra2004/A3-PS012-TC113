"""
A3-PS012-TC113: Authorised DNS Resolver Exposure Assessment Tool

DNS probing tool to determine whether designated LAB DNS servers provide
recursion to an authorised external lab client. Classifies servers as
RECURSIVE, AUTHORITATIVE_ONLY, REFUSED, or INCONCLUSIVE.
"""

__version__ = "0.1.0"
__author__ = "AIORI-3 Hackathon Team"
__all__ = [
    "cli",
    "config",
    "ratelimit",
    "probes",
    "classifier",
    "groundtruth",
    "runner",
    "report",
    "models",
]
