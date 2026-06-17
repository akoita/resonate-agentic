"""WorkflowAgent wrapper class for ADK 2.0.

Enables graph-based Workflows to be wrapped as standard BaseAgents so they
can be registered as sub-agents in LLM orchestrator agents.
"""

from typing import Any, AsyncGenerator
from google.adk.agents.base_agent import BaseAgent
from google.adk.workflow import Workflow
from google.adk.events.event import Event
from google.adk.agents.invocation_context import InvocationContext
from google.adk.runners import InMemoryRunner
from google.adk.apps import App

class WorkflowAgent(BaseAgent):
    """Wraps a Workflow to be used as a BaseAgent."""
    workflow: Workflow

    def __init__(self, workflow: Workflow, **data: Any):
        data["name"] = workflow.name
        data["description"] = workflow.description or f"Workflow Agent for {workflow.name}"
        data["workflow"] = workflow
        super().__init__(**data)
        self.workflow = workflow

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # Wrap the workflow in a sub-app and runner to run it dynamically
        app = App(name=self.workflow.name + "_app", root_agent=self.workflow)
        runner = InMemoryRunner(app=app)
        
        session = await runner.session_service.create_session(
            app_name=app.name, user_id=ctx.session.user_id
        )
        
        async for event in runner.run_async(
            user_id=ctx.session.user_id,
            session_id=session.id,
            new_message=ctx.user_content,
        ):
            yield event
