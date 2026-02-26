"""投标文件生成 API — 上传解析 + Qwen 生成标书框架，全链路打通。"""

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json, zipfile, io, re
import xml.etree.ElementTree as ET

from app.core.llm import get_llm
from app.utils.logger import logger

router = APIRouter()

# ─────────────────────────────────────────────
#  1. 上传解析端点：提取招标文件关键信息
# ─────────────────────────────────────────────

PARSE_SYSTEM_PROMPT = """你是一位专业的招标文件分析专家。给你一份招标文件的原文内容，你需要从中提取以下结构化信息并以 JSON 格式返回。

请严格按照以下 JSON 格式返回，不要返回其他任何内容：
{
  "project_name": "项目名称",
  "client_name": "招标人/采购人名称",
  "project_id": "项目编号",
  "budget": "预算金额/最高限价",
  "guarantee_amount": "投标保证金金额",
  "validity_days": "投标有效期(天数)",
  "bid_method": "招标方式(公开/邀请)",
  "evaluation_method": "评标方法(最低价/综合评分等)",
  "submission_deadline": "投标截止时间",
  "requirements": ["关键资质/技术要求1", "关键资质/技术要求2"],
  "key_terms": ["重要商务条款1", "重要商务条款2"],
  "disqualification_risks": ["否决条件1", "否决条件2"]
}

注意:
- 如果某个字段在文件中找不到，填写 "未明确" 
- 金额保留原文单位
- requirements 提取最关键的 3-5 条
- disqualification_risks 提取可能导致投标被否决的条件"""


def extract_text_from_docx(file_bytes: bytes) -> str:
    """从 docx 文件字节中提取纯文本（不依赖 python-docx）"""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            xml_content = zf.read("word/document.xml")
        
        root = ET.fromstring(xml_content)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        
        paragraphs = []
        for p in root.findall('.//w:p', ns):
            texts = [t.text for t in p.findall('.//w:t', ns) if t.text]
            line = ''.join(texts).strip()
            if line:
                paragraphs.append(line)
        
        return '\n'.join(paragraphs)
    except Exception as e:
        logger.error(f"DOCX extraction error: {e}")
        return ""


@router.post("/parse")
async def parse_bidding_document(file: UploadFile = File(...)):
    """上传招标文件 → AI 解析提取关键信息"""
    
    try:
        # 1. 读取文件内容
        file_bytes = await file.read()
        filename = file.filename or "unknown"
        logger.info(f"Parsing bidding document: {filename} ({len(file_bytes)} bytes)")
        
        # 2. 提取文本
        if filename.endswith('.docx'):
            text = extract_text_from_docx(file_bytes)
        elif filename.endswith('.txt'):
            text = file_bytes.decode('utf-8', errors='ignore')
        else:
            return {"success": False, "message": f"不支持的文件格式: {filename}，请上传 .docx 或 .txt 文件"}
        
        if not text or len(text) < 50:
            return {"success": False, "message": "文件内容提取失败或内容过少"}
        
        # 截取前 8000 字符避免超出上下文限制
        text_truncated = text[:8000]
        logger.info(f"Extracted {len(text)} chars, using first {len(text_truncated)} for parsing")
        
        # 3. 调用 Qwen 解析
        llm = get_llm()
        prompt = f"请分析以下招标文件内容，提取关键信息：\n\n{text_truncated}"
        
        response = await llm.generate(prompt, system=PARSE_SYSTEM_PROMPT)
        
        # 4. 尝试解析 JSON
        try:
            # 提取 JSON 块（处理可能包含 markdown 代码块的情况）
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                parsed = json.loads(response)
        except json.JSONDecodeError:
            logger.warning(f"JSON parse failed, returning raw: {response[:200]}")
            parsed = {"raw_response": response, "parse_error": True}
        
        return {
            "success": True,
            "data": {
                "parsed": parsed,
                "text_length": len(text),
                "filename": filename,
                "model": llm.get_model_name(),
            }
        }
        
    except Exception as e:
        logger.error(f"Parse error: {e}")
        return {"success": False, "message": str(e)}


# ─────────────────────────────────────────────
#  2. 生成端点：基于解析结果 + 律师信息生成标书
# ─────────────────────────────────────────────

BIDDING_SYSTEM_PROMPT = """你是一位资深的律所投标文书专家，专门为律师事务所生成投标文件框架。
你的任务是根据用户提供的投标人信息和项目背景，按照中国移动等大型央企的招标文件格式要求，生成完整的投标文件框架（商务分册部分）。

生成规范：
1. 使用正式的商务投标语言，严谨专业
2. 所有需要填写的具体数据用【 】标注占位
3. 涉及扫描件/附件的位置标注【此处附XX扫描件】
4. 金额单位统一为人民币元
5. 日期格式：XXXX年XX月XX日
6. 保持条目编号的层级结构清晰

你生成的文档应包含以下章节（根据提供的信息自动填充）：
1. 投标函（致招标人的正式承诺函）
2. 资格审查资料 — 基本情况表
3. 投标一览表
4. 企业信誉声明函
5. 非联合体投标及不存在任何形式的转包承诺函
6. 商务条款偏离表（注明全部无偏离）
7. 法定代表人身份证明
8. 法定代表人授权委托书（如有委托人）

注意：
- 根据投标人提供的信息尽可能填充内容
- 未提供的信息用【待填写】标注
- 格式要标准化，使用 Markdown 排版
- 如果提供了招标文件解析信息，要针对招标要求进行响应"""


class BiddingRequest(BaseModel):
    """投标文件生成请求"""
    company_name: str
    legal_representative: str
    project_name: str
    client_name: str
    project_id: Optional[str] = ""
    registered_capital: Optional[str] = ""
    established_date: Optional[str] = ""
    address: Optional[str] = ""
    contact_person: Optional[str] = ""
    contact_phone: Optional[str] = ""
    contact_email: Optional[str] = ""
    bid_amount: Optional[str] = ""
    guarantee_amount: Optional[str] = ""
    delegate_name: Optional[str] = ""
    validity_days: Optional[str] = "120"
    # 来自招标文件解析的额外上下文
    parsed_requirements: Optional[str] = ""
    parsed_risks: Optional[str] = ""
    budget: Optional[str] = ""
    stream: bool = True


@router.post("/generate")
async def generate_bidding_document(req: BiddingRequest):
    """生成投标文件框架 — SSE 流式输出"""

    # 构建 prompt
    user_prompt = f"""请根据以下信息，生成完整的投标文件框架（商务分册）：

## 投标基本信息

- **投标人名称**：{req.company_name}
- **法定代表人**：{req.legal_representative}
- **项目名称**：{req.project_name}
- **招标人名称**：{req.client_name}
- **项目编号**：{req.project_id or '【待填写】'}
- **注册资本**：{req.registered_capital or '【待填写】'}
- **成立时间**：{req.established_date or '【待填写】'}
- **注册地址**：{req.address or '【待填写】'}
- **联系人**：{req.contact_person or '【待填写】'}
- **联系电话**：{req.contact_phone or '【待填写】'}
- **电子邮箱**：{req.contact_email or '【待填写】'}
- **投标报价**：{req.bid_amount or '【待填写】'}
- **投标保证金**：{req.guarantee_amount or '【待填写】'}
- **委托代理人**：{req.delegate_name or '无（法定代表人直接投标）'}
- **投标有效期**：{req.validity_days}天
- **项目预算/最高限价**：{req.budget or '【待填写】'}"""

    # 如果有从招标文件中解析出的要求，加入 prompt
    if req.parsed_requirements:
        user_prompt += f"\n\n## 招标文件关键要求\n\n{req.parsed_requirements}"
    
    if req.parsed_risks:
        user_prompt += f"\n\n## 否决条件（务必在投标文件中避免）\n\n{req.parsed_risks}"

    user_prompt += "\n\n请按照标准格式生成完整的投标文件框架，已知信息直接填入，未知信息用【待填写】标注。"

    try:
        llm = get_llm()
        logger.info(f"Bidding generation: {req.company_name} → {req.project_name}")

        if req.stream:
            async def event_generator():
                try:
                    async for chunk in llm.stream(user_prompt, system=BIDDING_SYSTEM_PROMPT):
                        yield f"data: {json.dumps({'content': chunk, 'done': False}, ensure_ascii=False)}\n\n"
                    yield f"data: {json.dumps({'content': '', 'done': True}, ensure_ascii=False)}\n\n"
                except Exception as e:
                    logger.error(f"Bidding stream error: {e}")
                    yield f"data: {json.dumps({'content': f'[生成错误] {str(e)}', 'done': True}, ensure_ascii=False)}\n\n"

            return StreamingResponse(event_generator(), media_type="text/event-stream")
        else:
            response = await llm.generate(user_prompt, system=BIDDING_SYSTEM_PROMPT)
            return {"success": True, "data": {"content": response, "model": llm.get_model_name()}}

    except Exception as e:
        logger.error(f"Bidding generation error: {e}")
        return {"success": False, "message": str(e)}
