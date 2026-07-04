"""存储接口。默认实现是本地 SQLite（见 local.py）；

将来要上云（Supabase pgvector / 独立向量库），实现同样的方法即可，
Agent 与路由层不用改动。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from app.shared.schemas.document import Chunk, DocumentRecord


class Storage(Protocol):
    def add_document(
        self,
        record: DocumentRecord,
        chunks: List[Chunk],
        embeddings: List[List[float]],
    ) -> None: ...

    def get_document(self, doc_id: str) -> Optional[DocumentRecord]: ...

    def list_documents(self, workspace_id: str) -> List[DocumentRecord]: ...

    def search(
        self,
        workspace_id: str,
        query_embedding: List[float],
        k: int,
        doc_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]: ...
