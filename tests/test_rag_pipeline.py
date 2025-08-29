from unittest import mock

from memfuse.config import Settings
from memfuse.rag import RAGService


def test_rag_chat_pipeline_smoke():
    s = Settings.from_env()
    service = RAGService.from_settings(s)

    # Mock external interactions: DB, embeddings, LLM
    with mock.patch.object(service.db, 'fetch_conversation_history', return_value=[(1, 'user', 'hi'), (1, 'ai', 'hello')]):
        with mock.patch.object(service.embedder, 'embed', return_value=[[0.1, 0.2, 0.3]]):
            with mock.patch.object(service.db, 'search_similar_chunks', return_value=[('content', 'src', 0.9)]):
                with mock.patch.object(service.llm, 'chat', return_value='answer'):
                    with mock.patch.object(service.db, 'insert_conversation_message') as insert_mock:
                        answer = service.chat('s1', 'query')
                        assert answer == 'answer'
                        assert insert_mock.call_count == 2
