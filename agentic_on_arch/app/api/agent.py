"""Agent management API."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.schemas.agent import AgentCreate, AgentUpdate
from app.models.agent import Agent
from app.utils.response import ok
from app.utils.errors import NotFoundError

router = APIRouter()


@router.get("/")
async def list_agents(db: AsyncSession = Depends(get_db)):
    """List all agents."""
    result = await db.execute(select(Agent).where(Agent.is_active == 1))
    agents = result.scalars().all()
    return ok(data=[{"id": a.id, "name": a.name, "type": a.agent_type, "llm": a.llm_provider, "description": a.description} for a in agents])


@router.post("/")
async def create_agent(req: AgentCreate, db: AsyncSession = Depends(get_db)):
    """Create a new agent."""
    agent = Agent(
        name=req.name, description=req.description, agent_type=req.agent_type,
        llm_provider=req.llm_provider, llm_model=req.llm_model,
        system_prompt=req.system_prompt, skills=req.skills, config=req.config,
        owner_id=1,  # TODO: from JWT
    )
    db.add(agent)
    await db.flush()
    return ok(data={"id": agent.id, "name": agent.name})


@router.get("/{agent_id}")
async def get_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    """Get agent by ID."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise NotFoundError("Agent 不存在")
    return ok(data={"id": agent.id, "name": agent.name, "type": agent.agent_type, "llm": agent.llm_provider, "system_prompt": agent.system_prompt, "skills": agent.skills})
