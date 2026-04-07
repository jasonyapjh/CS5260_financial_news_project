"""
base_agent.py
-------------
Abstract base class for all agents in the pipeline.
Each agent must implement the `run()` method.
"""

from abc import ABC, abstractmethod
from utils.logger import get_logger


class BaseAgent(ABC):
    """
    All pipeline agents inherit from this class.

    Subclasses must implement:
        run(self, input_data) -> output_data
    """

    def __init__(self, config: dict):
        self.config = config
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def run(self, input_data):
        """Execute the agent's core logic."""
        raise NotImplementedError

    def log_start(self, msg: str = ""):
        self.logger.info(f"[{self.__class__.__name__}] Starting. {msg}")

    def log_done(self, msg: str = ""):
        self.logger.info(f"[{self.__class__.__name__}] Done. {msg}")
