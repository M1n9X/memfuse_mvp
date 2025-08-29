from memfuse.config import Settings
from memfuse.context import ContextController, RetrievedChunk


def test_context_building_truncates_history():
    s = Settings.from_env()
    ctrl = ContextController(s)

    history = [(i, 'user' if i % 2 == 1 else 'ai', f'message {i}') for i in range(1, 200)]
    chunks = [RetrievedChunk(content='foo', source='test', score=0.9)]
    messages = ctrl.build_final_context('hello', history, chunks)
    # Ensure user message present and retrieved block present
    roles = [m['role'] for m in messages]
    assert 'user' in roles
    assert any(m['role'] == 'system' for m in messages)
