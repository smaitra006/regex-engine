from dataclasses import dataclass
from typing import Optional

@dataclass
class Token:
    type: TokenType
    value: Optional[str] = None
    position: int = 0
