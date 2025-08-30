from unittest import mock

from memfuse.config import Settings
from memfuse.orchestrator import Orchestrator


def test_planner_and_agents_flow_smoke():
    s = Settings.from_env()
    # Ensure M3 disabled for this test
    object.__setattr__(s, 'm3_enabled', False)
    orch = Orchestrator.from_settings(s)

    # Mock planner to return a fixed plan
    plan = [
        {"agent": "RAGQueryAgent", "input": {"query": "What is MemFuse?"}},
        {"agent": "ReportGenerationAgent", "input": {"points": {"a": 1}}},
    ]
    with mock.patch.object(orch.planner, 'plan', return_value=[type('S', (), {'agent': p['agent'], 'input': p['input']}) for p in plan]):
        with mock.patch.object(orch.rag, 'chat', return_value='MemFuse is a system'):
            with mock.patch.object(orch.llm, 'chat', return_value='report'):
                out = orch.handle_request('s1', 'Explain MemFuse briefly')
                assert 'step_1_RAGQueryAgent' in out
                assert 'step_2_ReportGenerationAgent' in out


def test_m3_reuse_path_threshold_gate():
    s = Settings.from_env()
    object.__setattr__(s, 'm3_enabled', True)
    object.__setattr__(s, 'procedural_reuse_threshold', 0.5)
    orch = Orchestrator.from_settings(s)

    # Force embedder to return a vec
    with mock.patch.object(orch.embedder, 'embed', return_value=[[0.1, 0.2, 0.3]]):
        # First, no records: fall back to plan -> rag
        with mock.patch.object(orch.db, 'query_procedural_similar', return_value=[]):
            with mock.patch.object(orch.planner, 'plan', return_value=[]):
                with mock.patch.object(orch.rag, 'chat', return_value='fallback'):
                    out = orch.handle_request('s1', 'goal1')
                    assert out == 'fallback'
