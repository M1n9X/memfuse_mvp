from unittest import mock

from memfuse.config import Settings
from memfuse.rag import RAGService


def test_retrieval_fallback_uses_topk_when_vector_empty():
    s = Settings.from_env()
    service = RAGService.from_settings(s)

    with mock.patch.object(service.embedder, 'embed', return_value=[[]]):
        with mock.patch.object(service.db, 'search_similar_chunks', return_value=[]):
            with mock.patch.object(service.db, 'count_session_chunks', return_value=0):
                with mock.patch.object(service.db, 'fetch_top_k_chunks', return_value=[('c1','src1',0.0), ('c2','src2',0.0), ('c3','src3',0.0)]) as topk_mock:
                    with mock.patch.object(service.llm, 'chat', return_value='ok'):
                        ans = service.chat('s', 'q')
                        assert ans == 'ok'
                        topk_mock.assert_called_once()
