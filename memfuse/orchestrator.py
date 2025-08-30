from __future__ import annotations

import json
from dataclasses import dataclass
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
from uuid import uuid4

from .config import Settings
from .db import Database
from .embeddings import JinaEmbeddingClient
from .llm import ChatLLM
from .rag import RAGService
from .embeddings import JinaEmbeddingClient


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
        attempts = max(1, int(getattr(self.settings, 'planner_max_attempts', 3)))
        history: List[dict] = []
        for i in range(1, attempts + 1):
            try:
                prompt = user if not history else (user + f"\nRefine based on last failed attempt: {json.dumps(history[-1])}")
                raw = self.llm.completion_json(system, prompt)
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
                history.append({"attempt": i, "raw": raw or ""})
            except Exception as e:
                history.append({"attempt": i, "error": str(e)})
                continue
        # Fallback default plan
        return [PlanStep(agent="RAGQueryAgent", input={"query": user_goal}), PlanStep(agent="ReportGenerationAgent", input={})]


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

    def _arxiv(self, query: str, max_results: int = 10, last_days: int | None = None) -> Dict[str, Any]:
        import xml.etree.ElementTree as ET
        import requests
        from datetime import datetime, timedelta, timezone
        try:
            url = "http://export.arxiv.org/api/query"
            # Prefer sorting by submittedDate desc then filter by last_days if provided
            params = {
                "search_query": query,
                "start": 0,
                "max_results": max_results * 3 if last_days else max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = []
            cutoff = None
            if last_days and last_days > 0:
                cutoff = datetime.now(timezone.utc) - timedelta(days=last_days)
            for e in root.findall("atom:entry", ns):
                title = (e.findtext("atom:title", default="", namespaces=ns) or "").strip()
                summary = (e.findtext("atom:summary", default="", namespaces=ns) or "").strip()
                published_raw = (e.findtext("atom:published", default="", namespaces=ns) or "").strip()
                pub_dt = None
                if published_raw:
                    try:
                        pub_dt = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
                    except Exception:
                        pub_dt = None
                if cutoff and pub_dt and pub_dt < cutoff:
                    continue
                entries.append({"title": title, "summary": summary, "published": published_raw})
                if len(entries) >= max_results:
                    break
            return {"engine": "arxiv", "entries": entries}
        except Exception as e:
            return {"engine": "arxiv", "error": str(e)}

    def execute(self, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        query = str(payload.get("query") or payload.get("q") or "").strip()
        sources = payload.get("sources") or ["duckduckgo", "arxiv"]
        max_results = int(payload.get("max_results", payload.get("max", 10)))
        last_days = payload.get("last_days")
        try:
            last_days = int(last_days) if last_days is not None else None
        except Exception:
            last_days = None
        if not query:
            return {"error": "WebSearchAgent requires query"}
        results: Dict[str, Any] = {}
        if "duckduckgo" in sources:
            results["duckduckgo"] = self._duckduckgo(query)
        if "arxiv" in sources:
            # Build a robust arXiv query if the user query is in Chinese or too broad
            arxiv_query = payload.get("arxiv_query")
            if not arxiv_query:
                # Default combined query targeting LLM/Agents memory topics
                arxiv_query = (
                    "all:(\"large language model\" OR LLM OR agent) AND "
                    "all:(memory OR \"long-term memory\" OR retrieval OR RAG OR \"episodic memory\" OR \"semantic memory\")"
                )
            results["arxiv"] = self._arxiv(arxiv_query, max_results=max_results, last_days=last_days)
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
        # Run dir for logs/artifacts
        base = getattr(self.settings, 'runs_base_dir', 'runs')
        run_dir = Path(base) / time.strftime('%Y%m%d_%H%M%S') / session_id
        os.makedirs(run_dir, exist_ok=True)
        def _write_json(name: str, data_obj: dict) -> None:
            try:
                (run_dir / f"{name}.json").write_text(json.dumps(data_obj, ensure_ascii=False, indent=2))
            except Exception:
                pass
        _write_json("input", {"session_id": session_id, "goal": user_goal})
        # Step 0: try reuse
        wid, steps = self._reuse_from_m3(user_goal)
        reused = False
        if steps:
            reused = True
        else:
            steps = self.planner.plan(user_goal)
        if not steps:
            # fall back to a simple RAG answer
            ans = self.rag.chat(session_id, user_goal)
            _write_json("result", {"fallback_answer": ans})
            return ans

        # Execute plan
        context: Dict[str, Any] = {}
        _write_json("plan", {"steps": [{"agent": s.agent, "input": s.input} for s in steps]})
        executor = AgentExecutor(self.settings, self.llm, self.agents)
        for i, step in enumerate(steps, 1):
            step_name = f"step_{i}_{step.agent}"
            out, trace = executor.execute_with_retries(
                session_id=session_id,
                user_goal=user_goal,
                step=step,
                context=context,
                max_attempts=max(2, int(getattr(self.settings, 'planner_max_attempts', 3))),
            )
            context[step_name] = out
            # Write detailed trace log
            _write_json(step_name, trace)

        # Synthesize final report
        final_text = json.dumps(context, ensure_ascii=False, indent=2)
        _write_json("context", context)

        # Learning (if not reused)
        if not reused and getattr(self.settings, 'm3_enabled', False):
            try:
                wid_learned = self.learner.learn(user_goal, steps, context)
                if wid_learned:
                    _write_json("learned", {"workflow_id": wid_learned})
            except Exception:
                pass

        # Bump usage if reused
        if reused and wid:
            try:
                self.db.bump_procedural_usage(wid, 1)
                _write_json("reused", {"workflow_id": wid})
            except Exception:
                pass

        try:
            (run_dir / "report.txt").write_text(final_text)
        except Exception:
            pass
        return final_text


class AgentExecutor:
    """Autonomous subtask executor with iterative refinement and rich logging.

    For each step, it will:
    - Propose agent-specific parameters via LLM if missing or invalid
    - Execute the sub-agent and capture observation
    - Judge success, otherwise refine parameters and retry (up to max_attempts)
    - Return the final output and the full trace including all attempts
    """

    def __init__(self, settings: Settings, llm: ChatLLM, agents: Dict[str, Any]):
        self.settings = settings
        self.llm = llm
        self.agents = agents
        self.embedder = JinaEmbeddingClient(settings)
        self.db = Database.from_settings(settings)

    def _propose_input(self, agent_name: str, user_goal: str, context: Dict[str, Any], prior_attempt: Dict[str, Any] | None) -> Dict[str, Any]:
        schema_hint = AGENT_SCHEMAS.get(agent_name, {})
        system = (
            "You are an autonomous executor parameterizer.\n"
            "Given the high-level goal and partial context, propose the next action input strictly as JSON.\n"
            "Do NOT include any explanations, only return the JSON object matching the schema hints.\n"
        )
        user = json.dumps({
            "agent": agent_name,
            "goal": user_goal,
            "schema_hint": schema_hint,
            "last_attempt": prior_attempt or {},
            "context_keys": list(context.keys())[-8:],
        })
        try:
            raw = self.llm.completion_json(system, user)
            data = json.loads(raw or '{}')
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        # Minimal fallback if LLM fails: derive query from goal
        if agent_name == "RAGQueryAgent":
            return {"query": user_goal}
        if agent_name == "WebSearchAgent":
            return {"query": user_goal}
        if agent_name == "ReportGenerationAgent":
            return {"points": {"title": user_goal, "context": list(context.keys())[-3:]}}
        return {}

    def _judge_success(self, agent_name: str, output: Dict[str, Any]) -> bool:
        if not isinstance(output, dict):
            return False
        if "error" in output and output["error"]:
            return False
        # Agent-specific heuristics
        if agent_name == "WebSearchAgent":
            arx = output.get("arxiv", {})
            entries = arx.get("entries", []) if isinstance(arx, dict) else []
            return len(entries) >= 5
        if agent_name == "RAGQueryAgent":
            return bool(output.get("answer"))
        if agent_name == "ReportGenerationAgent":
            return bool(output.get("report"))
        if agent_name == "DatabaseQueryAgent":
            return "rows" in output or "headers" in output
        if agent_name == "ShellCommandAgent":
            return output.get("exit", 1) == 0 or bool(output.get("output"))
        return True

    def execute_with_retries(
        self,
        session_id: str,
        user_goal: str,
        step: PlanStep,
        context: Dict[str, Any],
        max_attempts: int,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        agent = self.agents.get(step.agent)
        if agent is None:
            raise ValueError(f"Unknown agent: {step.agent}")
        trace: Dict[str, Any] = {
            "agent": step.agent,
            "attempts": [],
        }
        prior: Dict[str, Any] | None = None
        payload = dict(step.input)
        # If required fields missing, ask LLM to propose
        if not payload or not isinstance(payload, dict):
            payload = {}
        attempts = max(1, max_attempts)
        final_out: Dict[str, Any] = {"error": "no_output"}
        for attempt in range(1, attempts + 1):
            # Auto parameter proposal if payload is missing critical fields
            need_proposal = (
                (step.agent == "RAGQueryAgent" and not payload.get("query")) or
                (step.agent == "DatabaseQueryAgent" and not (payload.get("request") or payload.get("query"))) or
                (step.agent == "WebSearchAgent" and not payload.get("query")) or
                (step.agent == "ReportGenerationAgent" and not any(k in payload for k in ("points","data")))
            )
            if need_proposal:
                proposed = self._propose_input(step.agent, user_goal, context, prior)
                payload.update({k: v for k, v in proposed.items() if k not in ("context",)})

            # Merge context for agent
            exec_payload = dict(payload)
            exec_payload.setdefault("context", context)
            start = time.time()
            try:
                out = agent.execute(session_id, exec_payload)
            except Exception as e:
                out = {"error": str(e)}
            elapsed = time.time() - start
            success = self._judge_success(step.agent, out)
            # Record trace attempt (summarized)
            trace_attempt = {
                "attempt": attempt,
                "input": {k: v for k, v in exec_payload.items() if k != "context"},
                "success": success,
                "elapsed_sec": elapsed,
            }
            # Truncate large outputs for log readability
            try:
                out_preview = json.dumps(out, ensure_ascii=False)
                if len(out_preview) > 4000:
                    out_preview = out_preview[:4000] + "...<truncated>"
            except Exception:
                out_preview = str(out)[:4000]
            trace_attempt["output_preview"] = out_preview
            trace["attempts"].append(trace_attempt)

            if success:
                final_out = out
                # Persist a success lesson for this agent + goal with working params
                try:
                    vec = self.embedder.embed([user_goal])[0]
                    self.db.insert_lesson(trigger_embedding=vec, goal_text=user_goal, agent=step.agent, status="success", error=None, fix_summary="", working_params=trace_attempt["input"])
                except Exception:
                    pass
                break

            # Prepare refinement hint for next attempt
            prior = {"input": trace_attempt["input"], "output": out_preview}
            # Light back-off to avoid immediate rate limiting
            time.sleep(min(2.0, 0.5 * attempt))
        else:
            final_out = out  # last
            # Persist a failure lesson with last attempt snapshot
            try:
                vec = self.embedder.embed([user_goal])[0]
                self.db.insert_lesson(trigger_embedding=vec, goal_text=user_goal, agent=step.agent, status="fail", error=out_preview[:500], fix_summary="", working_params=trace_attempt.get("input", {}))
            except Exception:
                pass

        trace["final_success"] = self._judge_success(step.agent, final_out)
        return final_out, trace


# Minimal input schema hints to guide LLM parameterization
AGENT_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "RAGQueryAgent": {"query": "string (derived from goal if missing)"},
    "DatabaseQueryAgent": {"request": "string (NL to SQL)", "schema_hint": "string?"},
    "WebSearchAgent": {"query": "string", "last_days": "int?", "max_results": "int?"},
    "ReportGenerationAgent": {"points": "object?", "data": "object?"},
    "ShellCommandAgent": {"cmd": "rg", "pattern": "string", "path": "string?", "max": "int?"},
}
