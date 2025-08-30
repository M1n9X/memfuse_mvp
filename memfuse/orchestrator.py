from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
from uuid import uuid4

from .config import Settings
from .db import Database
from .embeddings import JinaEmbeddingClient
from .llm import ChatLLM
from .rag import RAGService


@dataclass
class PlanStep:
    agent: str
    input: Dict[str, Any]


class Planner:
    def __init__(self, settings: Settings, llm: ChatLLM) -> None:
        self.settings = settings
        self.llm = llm

    def plan(self, user_goal: str) -> List[PlanStep]:
        system = (
            "You are a task planner. Decompose the high-level goal into ordered steps.\n"
            "Available agents: RAGQueryAgent, DatabaseQueryAgent, WebSearchAgent, ShellCommandAgent, ReportGenerationAgent.\n"
            "Return strict JSON: {\"steps\":[{\"agent\":<name>,\"input\":{...}}]}\n"
            "Rules: Keep 3-6 steps. Use RAG for internal/external indexed knowledge, WebSearch for the live web, DB for SQL, Report for final summarization.\n"
        )
        user = f"Goal: {user_goal}\nProduce steps now."
        try:
            raw = self.llm.completion_json(system, user)
            data = json.loads(raw or '{}')
            steps = data.get('steps', [])
            plan: List[PlanStep] = []
            for st in steps:
                agent = str(st.get('agent', '')).strip()
                if not agent:
                    continue
                payload = st.get('input') or {}
                if not isinstance(payload, dict):
                    payload = {}
                plan.append(PlanStep(agent=agent, input=payload))
            if plan:
                return plan
        except Exception:
            pass
        # Fallback default plan when planner LLM is unavailable
        return [
            PlanStep(agent="WebSearchAgent", input={"query": user_goal, "sources": ["duckduckgo"]}),
            PlanStep(agent="RAGQueryAgent", input={"query": user_goal}),
            PlanStep(agent="ReportGenerationAgent", input={}),
        ]


class RAGQueryAgent:
    def __init__(self, rag: RAGService) -> None:
        self.rag = rag

    def execute(self, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        query = str(payload.get('query') or payload.get('question') or '')
        if not query:
            raise ValueError('RAGQueryAgent requires query')
        try:
            answer = self.rag.chat(session_id, query)
            return {"answer": answer}
        except Exception as e:
            return {"error": str(e)}


class DatabaseQueryAgent:
    def __init__(self, settings: Settings, db: Database, llm: ChatLLM) -> None:
        self.settings = settings
        self.db = db
        self.llm = llm

    def _nl_to_sql(self, request: str, schema_hint: str = "") -> str:
        system = (
            "You translate natural language to PostgreSQL SQL.\n"
            "Constraints: SELECT-only, safe, no writes. Output SQL only.\n"
            f"Schema hint: {schema_hint}\n"
        )
        sql = self.llm.completion_json(system, f"NL: {request}\nReturn JSON {{\"sql\": ""<SQL>""}}")
        try:
            obj = json.loads(sql)
            return str(obj.get('sql', '')).strip()
        except Exception:
            return ""

    def execute(self, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        request: str = str(payload.get('request') or payload.get('query') or '')
        schema_hint: str = str(payload.get('schema_hint') or '')
        if not request:
            return {"error": 'DatabaseQueryAgent requires request'}
        sql = self._nl_to_sql(request, schema_hint)
        if not sql or not sql.lower().strip().startswith('select'):
            return {"error": 'Generated SQL invalid', "sql": sql}
        # Execute read-only SQL securely
        try:
            with self.db.connect() as conn, conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                headers = [d.name for d in cur.description] if cur.description else []
            return {"sql": sql, "headers": headers, "rows": rows}
        except Exception as e:
            return {"sql": sql, "error": str(e)}


class ReportGenerationAgent:
    def __init__(self, llm: ChatLLM) -> None:
        self.llm = llm

    def execute(self, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        points = payload.get('points') or payload.get('data') or payload
        text = json.dumps(points, ensure_ascii=False)
        system = (
            "You are a precise report writer. Summarize inputs into a concise, well-formatted brief."
        )
        try:
            res = self.llm.chat(system, [{"role": "user", "content": text}])
            return {"report": res}
        except Exception as e:
            # Fallback: simple local formatting
            try:
                obj = json.loads(text)
            except Exception:
                obj = {"content": text}
            lines = ["Report (offline fallback):"]
            for k, v in (obj.items() if isinstance(obj, dict) else enumerate(obj)):
                lines.append(f"- {k}: {str(v)[:200]}")
            return {"report": "\n".join(lines), "note": str(e)}


class WebSearchAgent:
    def __init__(self) -> None:
        pass

    def _duckduckgo(self, query: str) -> Dict[str, Any]:
        import requests
        try:
            resp = requests.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_redirect": 1, "no_html": 1},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            abstract = data.get("AbstractText") or data.get("Abstract") or ""
            related = [t.get("Text", "") for t in data.get("RelatedTopics", []) if isinstance(t, dict)]
            return {"engine": "duckduckgo", "abstract": abstract, "related": related[:5]}
        except Exception as e:
            return {"engine": "duckduckgo", "error": str(e)}

    def _arxiv(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        import xml.etree.ElementTree as ET
        import requests
        try:
            url = "http://export.arxiv.org/api/query"
            params = {"search_query": query, "start": 0, "max_results": max_results}
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = []
            for e in root.findall("atom:entry", ns):
                title = (e.findtext("atom:title", default="", namespaces=ns) or "").strip()
                summary = (e.findtext("atom:summary", default="", namespaces=ns) or "").strip()
                entries.append({"title": title, "summary": summary})
            return {"engine": "arxiv", "entries": entries}
        except Exception as e:
            return {"engine": "arxiv", "error": str(e)}

    def execute(self, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        query = str(payload.get("query") or payload.get("q") or "").strip()
        sources = payload.get("sources") or ["duckduckgo", "arxiv"]
        if not query:
            return {"error": "WebSearchAgent requires query"}
        results: Dict[str, Any] = {}
        if "duckduckgo" in sources:
            results["duckduckgo"] = self._duckduckgo(query)
        if "arxiv" in sources:
            results["arxiv"] = self._arxiv(query)
        return results


class ShellCommandAgent:
    """Run a limited, read-only shell command such as ripgrep (rg)."""

    def execute(self, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        import shutil
        import subprocess
        cmd = str(payload.get("cmd") or "rg").strip()
        if cmd not in {"rg"}:
            return {"error": "Only 'rg' (ripgrep) is allowed"}
        if shutil.which("rg") is None:
            return {"error": "ripgrep (rg) not installed"}
        pattern = str(payload.get("pattern") or payload.get("query") or "").strip()
        if not pattern:
            return {"error": "pattern required"}
        path = str(payload.get("path") or ".")
        max_count = int(payload.get("max", 200))
        try:
            proc = subprocess.run([
                "rg", "-n", "--no-heading", "-S", "-m", str(max_count), pattern, path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            out = proc.stdout
            return {"engine": "rg", "pattern": pattern, "path": path, "exit": proc.returncode, "output": out}
        except Exception as e:
            return {"engine": "rg", "error": str(e)}


class LearningAgent:
    def __init__(self, settings: Settings, db: Database, embedder: JinaEmbeddingClient):
        self.settings = settings
        self.db = db
        self.embedder = embedder

    def learn(self, user_goal: str, plan: List[PlanStep], final_result: Dict[str, Any]) -> str:
        try:
            trig_vec = self.embedder.embed([user_goal])[0]
        except Exception:
            return ""
        workflow = {
            "goal": user_goal,
            "plan": [
                {"agent": s.agent, "input": s.input} for s in plan
            ],
            "result_keys": list(final_result.keys()),
        }
        wid = str(uuid4())
        try:
            self.db.upsert_procedural_workflow(wid, trig_vec, workflow)
        except Exception:
            return ""
        return wid


@dataclass
class Orchestrator:
    settings: Settings
    db: Database
    embedder: JinaEmbeddingClient
    llm: ChatLLM
    rag: RAGService

    planner: Planner
    agents: dict
    learner: LearningAgent

    @classmethod
    def from_settings(cls, settings: Settings) -> "Orchestrator":
        db = Database.from_settings(settings)
        embedder = JinaEmbeddingClient(settings)
        llm = ChatLLM(settings)
        rag = RAGService.from_settings(settings)
        planner = Planner(settings, llm)
        learner = LearningAgent(settings, db, embedder)
        agents = {
            "RAGQueryAgent": RAGQueryAgent(rag),
            "DatabaseQueryAgent": DatabaseQueryAgent(settings, db, llm),
            "ReportGenerationAgent": ReportGenerationAgent(llm),
            "WebSearchAgent": WebSearchAgent(),
            "ShellCommandAgent": ShellCommandAgent(),
        }
        return cls(settings, db, embedder, llm, rag, planner, agents, learner)

    def _reuse_from_m3(self, user_goal: str) -> Tuple[str | None, List[PlanStep] | None]:
        if not getattr(self.settings, 'm3_enabled', False):
            return None, None
        try:
            vec = self.embedder.embed([user_goal])[0]
            recs = self.db.query_procedural_similar(vec, max(5, self.settings.procedural_top_k))
        except Exception:
            return None, None
        if not recs:
            return None, None
        # Pick best by score
        best = recs[0]
        wid, wf, score = best
        if score < self.settings.procedural_reuse_threshold:
            return None, None
        try:
            steps = [PlanStep(agent=s.get('agent',''), input=s.get('input') or {}) for s in wf.get('plan', [])]
            steps = [s for s in steps if s.agent]
            return wid, steps
        except Exception:
            return None, None

    def handle_request(self, session_id: str, user_goal: str, verbose: bool = False) -> str:
        # Step 0: try reuse
        wid, steps = self._reuse_from_m3(user_goal)
        reused = False
        if steps:
            reused = True
        else:
            steps = self.planner.plan(user_goal)
        if not steps:
            # fall back to a simple RAG answer
            return self.rag.chat(session_id, user_goal)

        # Execute plan
        context: Dict[str, Any] = {}
        for i, step in enumerate(steps, 1):
            agent = self.agents.get(step.agent)
            if agent is None:
                raise ValueError(f"Unknown agent: {step.agent}")
            # Merge previous results into payload under context
            payload = dict(step.input)
            payload.setdefault('context', context)
            out = agent.execute(session_id, payload)
            context[f"step_{i}_{step.agent}"] = out

        # Synthesize final report
        final_text = json.dumps(context, ensure_ascii=False, indent=2)

        # Learning (if not reused)
        if not reused and getattr(self.settings, 'm3_enabled', False):
            try:
                self.learner.learn(user_goal, steps, context)
            except Exception:
                pass

        # Bump usage if reused
        if reused and wid:
            try:
                self.db.bump_procedural_usage(wid, 1)
            except Exception:
                pass

        return final_text
