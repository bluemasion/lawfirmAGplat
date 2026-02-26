"""Chat API with SSE streaming."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.chat import ChatRequest
from app.core.llm import get_llm
from app.core.ner.masker import NERMasker
from app.core.ner.demasker import NERDemasker
from app.utils.response import ok
from app.utils.logger import logger
import json

router = APIRouter()


@router.post("/completions")
async def chat_completions(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Chat endpoint — returns SSE stream or JSON based on req.stream flag."""

    # Step 1: NER de-identification
    masker = NERMasker()
    masked_message, mapping = masker.mask(req.message)
    logger.info(f"NER masked: {len(mapping)} entities detected")

    # Step 2: Get LLM
    llm = get_llm()

    if req.stream:
        # SSE streaming response
        async def event_generator():
            demasker = NERDemasker()
            buffer = ""
            async for chunk in llm.stream(masked_message):
                # Re-identify entities in streamed chunks
                buffer += chunk
                restored = demasker.demask(buffer, mapping)
                yield f"data: {json.dumps({'content': restored, 'done': False}, ensure_ascii=False)}\n\n"
                buffer = ""
            yield f"data: {json.dumps({'content': '', 'done': True}, ensure_ascii=False)}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        # Non-streaming response
        response = await llm.generate(masked_message)
        demasker = NERDemasker()
        restored = demasker.demask(response, mapping)
        return ok(data={"content": restored})
