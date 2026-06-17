"""Proof-of-attempt harness: exercise credential-gated AI logic (litellm boundary stubbed,
dummy key) and call every 'dead'/NotImplementedError stub to capture real runtime behavior."""
import sys, json, asyncio, traceback
from pathlib import Path

import branch_fixer.services.ai.manager as mgr
from branch_fixer.core.models import TestError, ErrorDetails

# ---- Stub ONLY the network boundary (litellm.completion); real logic runs ----
calls = []
def fake_completion(model, messages, temperature, api_key=None, **kw):
    calls.append({"model": model, "temperature": temperature, "n_messages": len(messages),
                  "api_key_seen": api_key, "last_user_prompt_head": messages[-1]["content"][:90]})
    sys0 = messages[0]["content"] if messages else ""
    content = ("Root cause: test asserts a wrong expected value; correct the constant."
               if "Analyze failing test" in sys0 else
               "Explanation: corrected the wrong expected value.\nConfidence: 0.95\n"
               "Modified code:\n```python\ndef test_add():\n    assert 2 + 2 == 4\n```")
    return type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": content})})()]})()
mgr.completion = fake_completion

print("=== [AI] AIManager.generate_fix — REAL logic, stubbed boundary, DUMMY key ===")
m = mgr.AIManager(api_key="sk-DUMMY-FAKE-KEY-not-real")
err = TestError(test_file=Path("tests/temp_failing_test.py"), test_function="test_add",
                error_details=ErrorDetails("AssertionError", "assert 4 == 5",
                "tests/temp_failing_test.py:3: AssertionError\n_ _ _ _ _ _ _ _ _ _\n.venv/lib/site-packages/_pytest/junk\nmore"))
changes = m.generate_fix(err, 0.4)
print("RETURN type:", type(changes).__name__)
print("modified_code:\n" + changes.modified_code)
print("original_code present:", bool(changes.original_code))
print("thread len after first fix:", len(m._messages))

print("\n=== [AI] retry path (same error id -> feedback injection, no re-analyze) ===")
c2 = m.generate_fix(err, 0.6)
print("retry produced modified_code:", bool(c2.modified_code), "| thread len:", len(m._messages))

print("\n=== [AI] _clean_stack_trace (real) ===")
print(repr(mgr.AIManager._clean_stack_trace("frame\ntests/x.py:3: AssertionError\n_ _ _ _ _ _ _ _ _ _\n.venv/internal\nx")))

print("\n=== [AI] completion calls captured (proves analyze + fix paths ran) ===")
print(json.dumps(calls, indent=2))

# ---- Call every 'dead'/stub method directly: executed => captures raise/return ----
def probe(label, fn):
    try:
        r = fn()
        if asyncio.iscoroutine(r): r = asyncio.run(r)
        print(f"[STUB] {label} -> returned {r!r}")
    except NotImplementedError as e:
        print(f"[STUB] {label} -> raised NotImplementedError({e!r})")
    except Exception as e:
        print(f"[STUB] {label} -> raised {type(e).__name__}: {e}")

print("\n=== [STUBS] orchestration coordinator/dispatcher (async pass/return stubs) ===")
from branch_fixer.orchestration.coordinator import SessionCoordinator
from branch_fixer.orchestration.dispatcher import WorkflowDispatcher
sc = SessionCoordinator(); wd = WorkflowDispatcher()
probe("coordinator.coordinate_fix_attempt", lambda: sc.coordinate_fix_attempt(None, None, None))
probe("coordinator.handle_failure", lambda: sc.handle_failure(Exception("x"), {}))
probe("dispatcher.dispatch_fix_workflow", lambda: wd.dispatch_fix_workflow(None, None))
probe("dispatcher.handle_component_error", lambda: wd.handle_component_error("comp", Exception("x"), {}))

print("\n=== [STUBS] git NotImplementedError methods (reachable -> they raise) ===")
from branch_fixer.services.git.repository import GitRepository
try:
    repo = GitRepository(Path("."))
except TypeError:
    repo = GitRepository(root=Path("."))
probe("repository.clone", lambda: repo.clone("https://example/x.git"))
probe("repository.commit", lambda: repo.commit("msg"))
probe("repository.pull", lambda: repo.pull())
probe("repository.sync_with_remote", lambda: repo.sync_with_remote())
probe("branch_manager.get_branch_metadata", lambda: repo.branch_manager.get_branch_metadata("main"))
try:
    probe("branch_manager.is_branch_merged", lambda: repo.branch_manager.is_branch_merged("main"))
except Exception as e:
    print("is_branch_merged arity:", e)
probe("pr_manager.get_pr_history", lambda: repo.pr_manager.get_pr_history(1))
probe("pr_manager.close_pr", lambda: repo.pr_manager.close_pr(1))
print("\n=== DONE h1 ===")
