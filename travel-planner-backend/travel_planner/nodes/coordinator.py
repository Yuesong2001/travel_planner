"""
Coordinator V4
In this simplified architecture, the Coordinator's role is minimal.
The main routing logic is now handled by conditional edges within the graph itself,
making the system more modular and easier to debug. This class is kept for
structural consistency and to represent the entry point's conceptual role.
"""

from typing import Dict, Any

class Coordinator:
    """
    A simplified coordinator for the V4 graph.
    Its primary responsibility is to exist and be a conceptual entry point.
    The actual routing is defined in the graph's conditional edges.
    """
    def __init__(self):
        """Initializes the Coordinator."""
        pass

    # In V4, the complex routing logic previously in the coordinator
    # has been moved to the conditional edge functions in graph_builder.py.
    # This adheres to the principle of Separation of Concerns, where the graph
    # itself is responsible for flow control.

    # For example, the logic to decide between "chat" and "plan"
    # is now in the `coordinator_router` function in the graph builder.
    # This makes the data flow explicit and visible within the graph definition.
