"""Drive the server over the real MCP stdio transport: initialize, list tools, call one.

Uses whatever CHIRON_MCP_* environment you already have, so it exercises the same
configuration your MCP client will use.

    CHIRON_MCP_USERNAME=<user> .venv/bin/python -m tests.protocol
"""

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

VENV_PY = os.path.join(".venv", "bin", "python")


async def main() -> int:
    if not os.environ.get("CHIRON_MCP_USERNAME"):
        print("Set CHIRON_MCP_USERNAME first.", file=sys.stderr)
        return 1

    params = StdioServerParameters(
        command=VENV_PY if os.path.exists(VENV_PY) else sys.executable,
        args=["-m", "chiron_mcp.server"],
        env=dict(os.environ),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print(f"{len(names)} tools registered:")
            for n in names:
                print("  -", n)

            # Discover a dataset rather than assuming one exists.
            res = await session.call_tool("chiron_datasets", {})
            payload = json.loads(res.content[0].text)
            usable = [d for d in payload.get("datasets", []) if d.get("accessible")]
            print(f"\nidentity: {payload.get('identity')} "
                  f"| ceiling: {payload.get('access_ceiling')}")
            if not usable:
                print("No dataset reachable by this identity; "
                      "grant one with scripts/grant_access.py")
                return 1

            ds = usable[0]["dataset_id"]
            res = await session.call_tool(
                "chiron_count_cohort", {"dataset_id": ds, "cohort_def": []}
            )
            print(f"\nchiron_count_cohort({ds}) -> {res.content[0].text[:200]}")
            return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
