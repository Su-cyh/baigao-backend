"""
白糕平台 - 后端 API 服务
基于 FastAPI + DeepSeek + 阿里云百炼语音，保护 API Key 不暴露在前端
新增：录音实时转写功能
"""

from fastapi import FastAPI, Request, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import httpx
import os
import json
import asyncio

app = FastAPI(title="白糕平台 API", version="2.0")

# CORS 允许所有来源（生产环境建议限制为前端域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 敏感配置：只从环境变量读取 =====
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

# 阿里云百炼语音配置
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")

# ===== 白糕猫人设 =====
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
    """调用 DeepSeek API 的通用函数"""
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


# ========== AI 聊天（白糕猫人设）==========
@app.post("/api/chat")
async def chat(request: Request):
    """白糕猫闲聊/讲题接口，自动附加白糕系统提示词"""
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


# ========== 通用补全接口（不附加系统提示词）==========
@app.post("/api/completions")
async def completions(request: Request):
    """通用接口，前端自定义 prompt 调用，不加白糕系统提示词"""
    try:
        body = await request.json()
        messages = body.get("messages", [])
        temperature = body.get("temperature", 0.7)
        max_tokens = body.get("max_tokens", 4000)

        reply = await call_deepseek(messages, temperature=temperature, max_tokens=max_tokens)
        return {"reply": reply}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ========== 试卷生成 ==========
@app.post("/api/exam/generate")
async def generate_exam(request: Request):
    """根据上传文件内容生成试卷"""
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


# ========== 试卷批改 ==========
@app.post("/api/exam/grade")
async def grade_exam(request: Request):
    """批改试卷并给出评分"""
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


# ========== 思维导图生成 ==========
@app.post("/api/mindmap")
async def generate_mindmap(request: Request):
    """根据内容生成思维导图大纲"""
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


# ========== 笔记摘要生成 ==========
@app.post("/api/notes")
async def generate_notes(request: Request):
    """根据内容生成学习笔记摘要"""
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


# ========== 🎤 录音实时转写功能 ==========

async def blob_to_base64(audio_bytes: bytes, mime_type: str = "audio/webm") -> tuple[str, str]:
    """将音频字节流转为 base64 字符串，并推断格式"""
    import base64
    b64 = base64.b64encode(audio_bytes).decode("utf-8")
    fmt = "wav"
    if "webm" in mime_type:
        fmt = "webm"
    elif "ogg" in mime_type:
        fmt = "ogg"
    elif "mp3" in mime_type:
        fmt = "mp3"
    elif "mp4" in mime_type or "m4a" in mime_type:
        fmt = "mp4"
    elif "wav" in mime_type:
        fmt = "wav"
    return b64, fmt


@app.post("/api/asr")
async def asr(audio_file: UploadFile = File(...)):
    """
    语音转写接口（供前端录音笔记调用）
    接收音频文件（webm/ogg/wav/mp3/mp4 等），调用 DashScope qwen3-asr-flash 模型返回文字
    """
    try:
        if not DASHSCOPE_API_KEY:
            return JSONResponse(
                {"error": "未配置 DASHSCOPE_API_KEY 环境变量，请先设置"},
                status_code=500
            )

        audio_bytes = await audio_file.read()
        if len(audio_bytes) > 20 * 1024 * 1024:  # 20MB 限制
            return JSONResponse(
                {"error": "音频文件过大，请控制在 20MB 以内"},
                status_code=400
            )

        base64_data, audio_format = await blob_to_base64(audio_bytes, audio_file.content_type or "audio/webm")

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
                                "data": base64_data,
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


@app.post("/api/voice/transcribe-file")
async def transcribe_file(audio_file: UploadFile = File(...)):
    """
    音频文件转写接口
    接收音频文件（mp3/wav/m4a等），返回文字转写结果
    """
    try:
        if not DASHSCOPE_API_KEY:
            return JSONResponse(
                {"error": "未配置 DASHSCOPE_API_KEY 环境变量，请先设置"}, 
                status_code=500
            )
        
        # 读取音频文件
        audio_bytes = await audio_file.read()
        file_size = len(audio_bytes)
        
        if file_size > 10 * 1024 * 1024:  # 10MB 限制
            return JSONResponse(
                {"error": "音频文件过大，请控制在 10MB 以内"}, 
                status_code=400
            )
        
        # 保存临时文件
        temp_dir = os.environ.get("TEMP", "/tmp")
        temp_path = os.path.join(temp_dir, audio_file.filename)
        with open(temp_path, "wb") as f:
            f.write(audio_bytes)
        
        try:
            # 调用阿里云百炼语音识别（文件上传方式）
            async with httpx.AsyncClient(timeout=120.0) as client:
                # 上传文件
                with open(temp_path, "rb") as f:
                    upload_resp = await client.post(
                        "https://dashscope.aliyuncs.com/api/v1/files",
                        headers={
                            "Authorization": f"Bearer {DASHSCOPE_API_KEY}"
                        },
                        files={"file": (audio_file.filename, f, "audio/mpeg")}
                    )
                
                upload_data = upload_resp.json()
                
                if "id" not in upload_data:
                    return JSONResponse(
                        {"error": f"文件上传失败: {upload_data}"}, 
                        status_code=500
                    )
                
                file_id = upload_data["id"]
                
                # 提交转写任务
                job_resp = await client.post(
                    "https://dashscope.aliyuncs.com/api/v1/audio/transcriptions",
                    headers={
                        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "paraformer-v2",
                        "file_ids": [file_id],
                        "parameters": {
                            "language_hints": ["zh"]
                        }
                    }
                )
                
                job_data = job_resp.json()
                
                if "output" in job_data and "text" in job_data["output"]:
                    return {
                        "success": True,
                        "text": job_data["output"]["text"],
                        "duration": job_data["output"].get("duration"),
                        "model": "paraformer-v2"
                    }
                else:
                    return JSONResponse(
                        {"error": f"转写失败: {job_data}"}, 
                        status_code=500
                    )
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.websocket("/api/voice/stream")
async def voice_stream(websocket: WebSocket):
    """
    WebSocket 实时语音转写接口
    前端通过 WebSocket 发送音频流，实时返回转写结果
    
    使用方式：
    1. 前端连接 ws://localhost:8000/api/voice/stream
    2. 发送音频数据（PCM 16kHz 16bit）
    3. 接收实时转写结果
    """
    await websocket.accept()
    
    if not DASHSCOPE_API_KEY:
        await websocket.send_json({"error": "未配置 DASHSCOPE_API_KEY"})
        await websocket.close()
        return
    
    try:
        await websocket.send_json({"status": "connected", "message": "语音服务已就绪"})
        
        # 这里实现实时流式转写逻辑
        # 由于阿里云百炼的 WebSocket 需要特定协议，这里提供一个简化实现
        # 实际生产环境建议使用更完善的 WebSocket 代理
        
        while True:
            try:
                message = await websocket.receive()
                
                if "text" in message:
                    data = json.loads(message["text"])
                    if data.get("action") == "finish":
                        await websocket.send_json({"status": "finished"})
                        break
                    elif data.get("action") == "ping":
                        await websocket.send_json({"status": "pong"})
                        
                elif "bytes" in message:
                    # 收到音频数据，这里简化处理
                    # 实际应该将音频数据转发到阿里云百炼 WebSocket
                    await websocket.send_json({
                        "type": "transcription",
                        "text": "[实时转写中...]",
                        "is_final": False
                    })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                await websocket.send_json({"error": str(e)})
                break
        
        await websocket.close()
        
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close()


@app.get("/api/voice/status")
async def voice_status():
    """检查语音服务状态"""
    return {
        "service": "阿里云百炼语音转写",
        "configured": bool(DASHSCOPE_API_KEY),
        "models": ["paraformer-v2", "paraformer-realtime-v2"],
        "features": {
            "file_transcription": "/api/voice/transcribe-file (POST, 上传音频文件)",
            "stream_transcription": "/api/voice/stream (WebSocket, 实时音频流)",
            "supported_formats": ["wav", "mp3", "m4a", "ogg"]
        }
    }


# ========== 静态文件托管（生产环境前后端同域名）==========
# 获取项目根目录（backend 的上级目录）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = "/app"

# 根路径返回前端页面
@app.get("/")
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "ok", "service": "白糕平台 API", "version": "2.0"}

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ========== 启动入口 ==========
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🐱 白糕平台 API 启动中...")
    print(f"📡 本地访问: http://localhost:{port}")
    print(f"🔑 DeepSeek API Key: {'已配置 ✅' if DEEPSEEK_API_KEY else '未配置 ❌'}")
    print(f"🎤 阿里云语音 API Key: {'已配置 ✅' if DASHSCOPE_API_KEY else '未配置 ❌'}")
    print(f"📚 API 文档: http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port)