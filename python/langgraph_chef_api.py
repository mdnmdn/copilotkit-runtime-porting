"""Demo"""

import os

from dotenv import load_dotenv

load_dotenv()

# pylint: disable=wrong-import-position
import uvicorn
from fastapi import FastAPI

from agui_runtime.runtime_py import CopilotRuntime
from agui_runtime.runtime_py.core.provider import AgentProvider
from langgraph_chef_agent import graph

app = FastAPI()
runtime = CopilotRuntime()

# Mount the runtime to FastAPI
runtime.mount_to_fastapi(app, path="/api/agui")


# add new route for health check
@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}


def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("langgraph_chef_api:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
