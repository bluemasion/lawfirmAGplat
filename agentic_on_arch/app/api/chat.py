"""Chat API with SSE streaming — connects to real LLM."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest
from app.core.llm import get_llm
from app.core.ner.masker import NERMasker
from app.core.ner.demasker import NERDemasker
from app.utils.response import ok
from app.utils.logger import logger
import json
import traceback

router = APIRouter()

# 律所 AI 助手系统提示
SYSTEM_PROMPT = """你是一家顶级律师事务所的 AI 法律助手，名称为 Legal-AI。你部署在律所私有化环境内（VPC 隔离），所有对话内容均经过 NER 脱敏网关处理。

你的核心能力：
1. 法律知识问答 — 中国法律法规、司法解释、案例检索
2. 合同审查 — 条款风险识别、修改建议
3. 投标管理 — 标书起草、合规审核、竞争分析
4. 利益冲突检查 — 关联方穿透、回避建议
5. 文书起草 — 法律意见书、代理词、答辩状

回答风格要求：
- 专业、简洁、结构化（使用序号和要点）
- 必须引用相关法条（如适用）
- 涉及敏感操作时提醒用户注意合规
- 用中文回答"""


@router.post("/completions")
async def chat_completions(req: ChatRequest):
    """Chat endpoint — returns SSE stream or JSON."""

    try:
        # Step 1: NER de-identification
        masker = NERMasker()
        masked_message, mapping = masker.mask(req.message)
        ner_count = len(mapping)
        if ner_count > 0:
            logger.info(f"NER masked: {ner_count} entities detected")

        # Step 2: Get LLM
        llm = get_llm()
        logger.info(f"LLM provider: {llm.get_model_name()}")

        if req.stream:
            # SSE streaming response
            async def event_generator():
                try:
                    logger.info("SSE event_generator started")
                    demasker = NERDemasker()
                    chunk_count = 0
                    async for chunk in llm.stream(masked_message, system=SYSTEM_PROMPT):
                        # Re-identify entities in streamed chunks
                        restored = demasker.demask(chunk, mapping) if mapping else chunk
                        chunk_count += 1
                        if chunk_count <= 3:
                            logger.info(f"SSE chunk #{chunk_count}: [{restored[:30]}]")
                        yield f"data: {json.dumps({'content': restored, 'done': False}, ensure_ascii=False)}\n\n"
                    logger.info(f"SSE complete: {chunk_count} chunks total")
                    yield f"data: {json.dumps({'content': '', 'done': True}, ensure_ascii=False)}\n\n"
                except Exception as e:
                    logger.error(f"Stream error: {traceback.format_exc()}")
                    yield f"data: {json.dumps({'content': f'[错误] {str(e)}', 'done': True}, ensure_ascii=False)}\n\n"

            return StreamingResponse(event_generator(), media_type="text/event-stream")
        else:
            # Non-streaming response
            response = await llm.generate(masked_message, system=SYSTEM_PROMPT)
            demasker = NERDemasker()
            restored = demasker.demask(response, mapping) if mapping else response
            return ok(data={"content": restored, "model": llm.get_model_name()})

    except Exception as e:
        logger.error(f"Chat error: {traceback.format_exc()}")
        return ok(data={"content": f"[系统错误] {str(e)}", "model": "error"})
