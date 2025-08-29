from unittest import mock

from memfuse.config import Settings
from memfuse.rag import RAGService


def test_session_indexer_builds_and_queries_session_chunks():
    s = Settings.from_env()
    service = RAGService.from_settings(s)

    # Fake a small history and embeddings
    history = [(1, 'user', 'hello world'), (1, 'ai', 'hi there')]
    with mock.patch.object(service.db, 'fetch_conversation_history', return_value=history):
        with mock.patch.object(service.indexer, 'ensure_built', return_value=2) as ensure_mock:
            with mock.patch.object(service.embedder, 'embed', side_effect=[[0.1,0.2,0.3], [0.4,0.5,0.6]]):
                with mock.patch.object(service.db, 'count_session_chunks', return_value=2):
                    with mock.patch.object(service.db, 'search_similar_chunks_for_session', return_value=[('h1','session:x',0.9)]):
                        with mock.patch.object(service.llm, 'chat', return_value='ok'):
                            ans = service.chat('x', 'q')
                            assert ans == 'ok'
                            ensure_mock.assert_called_once()
