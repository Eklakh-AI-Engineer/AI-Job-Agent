from abc import ABC, abstractmethod
from typing import List

class JobSource(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier for this source, e.g. 'greenhouse', 'apify', 'fixture'."""
        pass

    @abstractmethod
    def fetch(self) -> List[dict]:
        """Fetch raw job records. Returns list of raw dicts (source-specific format)."""
        pass
