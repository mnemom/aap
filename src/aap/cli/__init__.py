"""AAP Command Line Interface.

Provides CLI tools for working with the Agent Alignment Protocol:
- aap init: Create a new Alignment Card
- aap verify: Verify traces against an Alignment Card
- aap check-coherence: Check compatibility between two Alignment Cards
- aap drift: Detect behavioral drift from declared alignment
"""

from aap.cli.main import main

__all__ = ["main"]
