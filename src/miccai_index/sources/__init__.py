"""External source adapters.

Each adapter implements the ``SourceAdapter`` contract:

* ``id``            stable identifier
* ``fetch(query)``  return ``(records, source_metadata)`` or raise
* ``is_enabled()``  honour runtime enable/disable flags
"""

from .arxiv_source import ArxivSource, ArxivRecord

__all__ = ["ArxivSource", "ArxivRecord"]