from typing import Optional
from ..config import Config
from ..mcp import XiaohongshuHTTPClient
from ..agents.orchestrator import ResearchOrchestrator

class AppContext:
    _instance = None
    
    def __init__(self):
        self.config: Optional[Config] = None
        self.mcp_client: Optional[XiaohongshuHTTPClient] = None
        self.orchestrator: Optional[ResearchOrchestrator] = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AppContext()
        return cls._instance

global_context = AppContext.get_instance()
