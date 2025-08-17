"""Demo"""

import os

from dotenv import load_dotenv

load_dotenv()

# pylint: disable=wrong-import-position
import uvicorn
from fastapi import FastAPI

from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from langgraph_chef_agent import graph

app = FastAPI()
sdk = CopilotKitRemoteEndpoint(
    agents=[
        LangGraphAgent(
            name="Chef",
            description="Chef agent.",
            graph=graph,
        ),
    ],
)

add_fastapi_endpoint(app, sdk, "/copilotkit")


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
