from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Union, Literal, Optional
from xcagent import agent
import uvicorn
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Agent API",
    version="1.0",
    description="基于本地大模型的智能Agent系统"
)

class ChatRequest(BaseModel):
    user_id: str = Field(..., example="user123")
    query: str = Field(..., example="查询订单1024的状态")

class SuccessResponse(BaseModel):
    status: Literal["success"] = "success"
    data: str = Field(..., description="响应内容")
    tool_used: Optional[str] = Field(None, description="使用的工具")

class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    message: str = Field(..., description="错误信息")
    detail: Optional[str] = Field(None, description="详细错误")

class ChatResponse(BaseModel):
    result: Union[SuccessResponse, ErrorResponse]
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """处理聊天请求"""
    try:
        result = agent.process(request.user_id, request.query)
        
        if result["success"]:
            return ChatResponse(
                result=SuccessResponse(
                    data=result["response"],
                    tool_used=result.get("tool_used")
                )
            )
        else:
            return ChatResponse(
                result=ErrorResponse(
                    message=result["response"],
                    detail=result.get("error")
                )
            )
    except Exception as e:
        logger.error(f"API处理异常: {str(e)}")
        return ChatResponse(
            result=ErrorResponse(
                message="Internal Server Error",
                detail=str(e)
            )
        )

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )