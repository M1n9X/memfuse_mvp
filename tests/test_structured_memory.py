from unittest import mock

from memfuse.config import Settings
from memfuse.rag import RAGService


def test_extractor_runs_and_inserts_records():
    s = Settings.from_env()
    # Enable extractor and structured retrieval for test
    object.__setattr__(s, 'extractor_enabled', True)
    object.__setattr__(s, 'structured_enabled', True)
    service = RAGService.from_settings(s)

    # Mock LLM extractor returning a JSON object
    extractor_json = '{"items":[{"type":"Decision","content":"We rejected Plan A due to cost overruns","metadata":{"confidence":0.92}}]}'

    # Wire mocks across db, llm, embedder
    with mock.patch.object(service.db, 'fetch_conversation_history', return_value=[(1,'user','hello'), (1,'ai','hi')]):
        with mock.patch.object(service.indexer, 'ensure_built', return_value=0):
            with mock.patch.object(service.embedder, 'embed', return_value=[[0.1,0.2,0.3]]):
                with mock.patch.object(service.db, 'search_similar_chunks', return_value=[('x','src',0.9)]):
                    with mock.patch.object(service.llm, 'chat', return_value='ok'):
                        with mock.patch.object(service.llm, 'completion_json', return_value=extractor_json):
                            with mock.patch.multiple(service.db,
                                                     insert_structured_records=mock.DEFAULT,
                                                     fetch_unextracted_rounds=mock.DEFAULT,
                                                     mark_rounds_extracted=mock.DEFAULT) as m:
                                m['insert_structured_records'].return_value = 1
                                m['fetch_unextracted_rounds'].return_value = []
                                m['mark_rounds_extracted'].return_value = 1
                                ans = service.chat('s1', 'Why not Plan A?')
                                assert ans == 'ok'
                                m['insert_structured_records'].assert_called_once()


def test_structured_retrieval_merges_results_first():
    s = Settings.from_env()
    object.__setattr__(s, 'structured_enabled', True)
    service = RAGService.from_settings(s)

    history = [(1,'user','h1'), (1,'ai','h2')]
    with mock.patch.object(service.db, 'fetch_conversation_history', return_value=history):
        with mock.patch.object(service.indexer, 'ensure_built', return_value=0):
            with mock.patch.object(service.db, 'query_structured_by_keywords', return_value=[('Because cost exceeded budget','structured:Decision#round=1', 2.0)]):
                with mock.patch.object(service.embedder, 'embed', return_value=[[0.1,0.2,0.3]]):
                    with mock.patch.object(service.db, 'search_similar_chunks', return_value=[('other','doc',0.5)]):
                        with mock.patch.object(service.llm, 'chat', return_value='answer') as chat_mock:
                            with mock.patch.object(service.db, 'insert_conversation_message'):
                                with mock.patch.object(service.db, 'fetch_unextracted_rounds', return_value=[(2,'u','a')]):
                                    with mock.patch.object(service.db, 'fetch_top_k_chunks_for_session', return_value=[('c','session:s1',0.0)]):
                                        with mock.patch.object(service.db, 'query_structured_by_keywords', return_value=[('s','structured:Fact#round=1',2.0)]):
                                            with mock.patch.object(service.db, 'mark_rounds_extracted', return_value=1):
                                                with mock.patch.object(service.llm, 'completion_json', return_value='{"items":[]}'):
                                                    ans = service.chat('s1', 'Why did we reject A?')
                                                    assert ans == 'answer'
                                                    chat_mock.assert_called()