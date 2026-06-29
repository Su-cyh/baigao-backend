"""
白糕平台 - Vercel Serverless Backend
适配 Vercel 的 Python serverless functions
"""

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import os
import json
import base64

app = FastAPI(title="白糕平台 API", version="2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")

# 白糕猫人设
SYSTEM_PROMPT = """你是「白糕」，白糕平台的AI猫咪助手。你是一只聪明、可爱、偶尔有点调皮的白猫。你有两种模式：
1. 闲聊模式：用户可以跟你聊天、吐槽、倾诉、讲笑话，你可以用轻松可爱的语气回应，偶尔用猫咪的方式表达（比如"喵～这道题确实有点难呢"），但不要每句话都加喵，自然一点。
2. 讲题模式：用户问你学科问题、作业、考试、知识点时，你要切换成专业的学习助手，清晰准确地解答，可以分步骤讲解，用通俗易懂的语言。
规则：
- 用户没明确问学科问题时，默认用闲聊风格
- 回答要简洁，不要太长，像朋友聊天一样
- 可以适当用emoji但别太多
- 你叫白糕，是一只白色的猫
- 用中文回答"""


async def call_deepseek(messages, temperature=0.7, max_tokens=2000):
    """调用 DeepSeek API"""
    if not DEEPSEEK_API_KEY:
        raise Exception("未配置 DEEPSEEK_API_KEY 环境变量")
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            DEEPSEEK_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        data = resp.json()
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"]
        raise Exception(data.get("error", {}).get("message", "未知错误"))


@app.get("/")
async def root():
    return {"status": "ok", "service": "白糕平台 API", "version": "2.0"}


@app.post("/api/chat")
async def chat(request: Request):
    """白糕猫闲聊/讲题接口"""
    try:
        body = await request.json()
        user_message = body.get("message", "")
        history = body.get("history", [])

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history[-10:]:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        messages.append({"role": "user", "content": user_message})

        reply = await call_deepseek(messages)
        return {"reply": reply}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/completions")
async def completions(request: Request):
    """通用补全接口"""
    try:
        body = await request.json()
        messages = body.get("messages", [])
        temperature = body.get("temperature", 0.7)
        max_tokens = body.get("max_tokens", 4000)

        reply = await call_deepseek(messages, temperature=temperature, max_tokens=max_tokens)
        return {"reply": reply}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/exam/generate")
async def generate_exam(request: Request):
    """根据内容生成试卷"""
    try:
        body = await request.json()
        content = body.get("content", "")
        subject = body.get("subject", "综合")

        prompt = f"""请根据以下内容生成一份完整的考试试卷。
科目：{subject}
内容范围：
{content[:3000]}

要求：
1. 包含选择题（单选+多选）、填空题、简答题
2. 题目难度分布合理（易30%、中50%、难20%）
3. 每道题附上参考答案和评分标准
4. 格式清晰，题号连续
5. 总分100分"""

        reply = await call_deepseek(
            [{"role": "user", "content": prompt}], temperature=0.3, max_tokens=4000
        )
        return {"exam": reply}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/exam/grade")
async def grade_exam(request: Request):
    """批改试卷"""
    try:
        body = await request.json()
        questions = body.get("questions", "")
        answers = body.get("answers", "")

        prompt = f"""请批改以下试卷，给出每道题的得分和总评。

题目：
{questions}

学生答案：
{answers}

请：
1. 逐题判断对错
2. 给出每题得分
3. 计算总分（满分100）
4. 给出整体评价和改进建议"""

        reply = await call_deepseek(
            [{"role": "user", "content": prompt}], temperature=0.2, max_tokens=3000
        )
        return {"result": reply}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/mindmap")
async def generate_mindmap(request: Request):
    """生成思维导图大纲"""
    try:
        body = await request.json()
        content = body.get("content", "")

        prompt = f"""请根据以下内容生成思维导图的大纲结构，用层级列表表示：

{content[:3000]}

要求：
1. 中心主题明确
2. 分支层次分明（最多3层）
3. 每个节点简洁（不超过10个字）
4. 覆盖主要知识点"""

        reply = await call_deepseek(
            [{"role": "user", "content": prompt}], temperature=0.3, max_tokens=2000
        )
        return {"mindmap": reply}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/notes")
async def generate_notes(request: Request):
    """生成学习笔记"""
    try:
        body = await request.json()
        content = body.get("content", "")

        prompt = f"""请根据以下内容生成精炼的学习笔记摘要：

{content[:3000]}

要求：
1. 提取关键知识点
2. 用简洁的要点列出
3. 标注重点和易错点
4. 给出复习建议"""

        reply = await call_deepseek(
            [{"role": "user", "content": prompt}], temperature=0.3, max_tokens=2000
        )
        return {"notes": reply}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/asr")
async def asr(request: Request):
    """
    语音转写接口
    接收 base64 编码的音频数据，调用 DashScope qwen3-asr-flash
    """
    try:
        if not DASHSCOPE_API_KEY:
            return JSONResponse(
                {"error": "未配置 DASHSCOPE_API_KEY 环境变量"},
                status_code=500
            )

        body = await request.json()
        audio_base64 = body.get("audio", "")
        audio_format = body.get("format", "webm")

        if not audio_base64:
            return JSONResponse({"error": "缺少音频数据"}, status_code=400)

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "qwen3-asr-flash",
                    "messages": [{
                        "role": "user",
                        "content": [{
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_base64,
                                "format": audio_format
                            }
                        }]
                    }]
                }
            )

            data = resp.json()
            if not resp.is_success:
                return JSONResponse(
                    {"error": data.get("error", {}).get("message", f"HTTP {resp.status_code}")},
                    status_code=500
                )

            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"text": text}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/voice/status")
async def voice_status():
    """检查语音服务状态"""
    return {
        "service": "阿里云百炼语音转写",
        "configured": bool(DASHSCOPE_API_KEY),
        "models": ["qwen3-asr-flash", "paraformer-v2"]
    }
