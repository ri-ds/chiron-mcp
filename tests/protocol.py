"""Drive the server over real MCP stdio: initialize, list tools, call one."""
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    env = dict(os.environ, CHIRON_MCP_USERNAME="demouser")
    params = StdioServerParameters(
        command=".venv/bin/python", args=["-m", "chiron_mcp.server"], env=env)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            names = [t.name for t in tools.tools]
            print(f"{len(names)} tools registered:")
            for n in names: print("  -", n)
            res = await s.call_tool("chiron_count_cohort",
                                    {"dataset_id": "dataset1_stored", "cohort_def": []})
            print("\ncall chiron_count_cohort ->", str(res.content[0].text)[:200])
            res2 = await s.call_tool("chiron_datasets", {})
            print("call chiron_datasets ->", str(res2.content[0].text)[:160])

asyncio.run(main())
