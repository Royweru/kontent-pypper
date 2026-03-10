import json
import asyncio
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.api.deps import get_current_user
from app.models.user import User

from app.services.workflow.langgraph_pipeline import langgraph_pipeline

router = APIRouter()

@router.post("/run")
async def run_workflow(current_user: User = Depends(get_current_user)):
    """
    Executes the LangGraph automated content generation pipeline
    and streams back the state changes so the frontend can update live.
    """
    
    async def event_generator():
        # INITIAL STATE
        initial_state = {
            "user_id": current_user.id,
            "niche": "Technology and AI",  # We can pull this from User later
            "articles": [],
            "selected_article": None,
            "scripts": {},
            "video_asset": None,
            "status": "Starting pipeline..."
        }
        
        yield f"data: {json.dumps(initial_state)}\n\n"
        
        # We run the graph node by node so we can stream the state
        # langgraph_pipeline is a CompiledGraph
        async for state in langgraph_pipeline.astream(initial_state):
            # state is a dict where keys are the nodes that just ran, and values are the new state
            for node_name, updated_state in state.items():
                print(f"[Workflow] Finished node: {node_name}")
                # We yield the latest state to the frontend
                yield f"data: {json.dumps(updated_state)}\n\n"
                await asyncio.sleep(0.5) # small delay for UX visual feel
                
        # Send a final 'done' signal
        yield f"data: {json.dumps({'status': 'DONE'})}\n\n"
        
    return StreamingResponse(event_generator(), media_type="text/event-stream")
