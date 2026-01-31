"""Agent Alignment Protocol (AAP) - The missing alignment layer for the agent protocol stack."""

from aap.alignment_card import AlignmentCard
from aap.ap_trace import APTrace
from aap.handshake import ValueCoherenceHandshake

__version__ = "0.1.0"
__all__ = [
    "AlignmentCard",
    "APTrace",
    "ValueCoherenceHandshake",
]
