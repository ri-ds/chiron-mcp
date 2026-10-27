"""The page may pick the model that answers, among the ones the deployment lists.

Offline: no database, no model. CHIRON_MCP_ASK_MODELS lists ids with labels; the page's
pick is honoured only when it is on the list, the default follows ANTHROPIC_MODEL, the
CLI gets --model and every model slot pinned, and no list means no switcher.

    .venv/bin/python tests/ask_models.py
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
tmp = tempfile.mkdtemp()
OPUS, SONNET, HAIKU = ("us.anthropic.claude-opus-5-5", "us.anthropic.claude-sonnet-5-5",
                       "us.anthropic.claude-haiku-5-5")
os.environ.update(CHIRON_MCP_USERNAME="tester", CHIRON_MCP_STATE_DIR=os.path.join(tmp, "state"),
                  CHIRON_MCP_TRACE="0",
                  CHIRON_MCP_ASK_MODELS=f" {OPUS}=Opus 5.5, {SONNET} = Sonnet 5.5 ,{HAIKU},,{OPUS}=again",
                  ANTHROPIC_MODEL=HAIKU)

from chiron_mcp import webapp as W  # noqa: E402

fails: list[str] = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:200])
    if not ok:
        fails.append(name)


check("the list keeps ids with labels, trims, and drops blanks and repeats",
      [(m["id"], m["label"]) for m in W.ASK_MODELS] ==
      [(OPUS, "Opus 5.5"), (SONNET, "Sonnet 5.5"), (HAIKU, HAIKU)], str(W.ASK_MODELS))
check("ANTHROPIC_MODEL on the list is the default", W.default_model() == HAIKU, W.default_model())
check("a listed pick is honoured", W.pick_model(SONNET) == SONNET)
check("a pick off the list falls back to the default", W.pick_model("gpt-5") == HAIKU)
check("no pick is the default", W.pick_model(None) == HAIKU and W.pick_model("  ") == HAIKU)

cmd = W._claude_command("claude", "How many?", ["--session-id", "t1"], Path("/tmp/x.json"), SONNET)
i = cmd.index("--model") if "--model" in cmd else -1
check("the CLI is told the model", i > 0 and cmd[i + 1] == SONNET, " ".join(cmd[:8]))
cmd = W._claude_command("claude", "How many?", ["--session-id", "t1"], Path("/tmp/x.json"))
check("no model, no flag", "--model" not in cmd)

env = W.model_env(SONNET)
check("every model slot is pinned to the pick",
      all(env.get(s) == SONNET for s in W._MODEL_SLOTS) and env.get("CHIRON_MCP_USERNAME") == "tester",
      str({s: env.get(s) for s in W._MODEL_SLOTS}))
check("no model keeps the server's environment", W.model_env(None) is None)

# Without a list there is nothing to pick from: the CLI's own model answers, as before.
W.ASK_MODELS = []
check("no list: no default and any pick is ignored",
      W.default_model() is None and W.pick_model(OPUS) is None)

check("a Bedrock refusal of a model gets a plain message",
      "AWS role" in W.explain_claude_error("AccessDeniedException: You don't have access to the model"))

print("\nALL PASS" if not fails else f"\nFAILED: {', '.join(fails)}")
sys.exit(1 if fails else 0)
