from langgraph.graph import StateGraph,END # 创建一个有状态的工作流图，以及终止节点
# from langchain.agents import Tool # 外部工具类扩展agent的能力
from langchain_core.tools import Tool
from typing import TypedDict, Optional, Dict, Any, List # Python的类型注解    可以使用内置
from pydantic import BaseModel, Field
import re # 正则表达式
import sys  # 系统相关参数和功能
import os   # 操作系统系统交互的模块 文件 路径 环境变量
import sqlite3 # 轻量级嵌入式数据库
from datetime import datetime # 日期和时间处理
from xcmemory import HybridMemory
from xctools import query_weather
from xcollama_client import ollama_client

class WeatherInput(BaseModel):
    city: str = Field(description="城市名称")

class AgentState(TypedDict): # 规范agent运行时状态的数据结构
    """Agent状态类型定义"""
    user_id: str
    input: str
    memory: str
    current_tool: Optional[str]
    tool_params: Dict[str, Any]
    tool_result: Optional[Dict[str, Any]]
    response: str
    error: Optional[str]

class HybridAgent:
    """结合API大模型和工具的智能Agent - 彻底修复版"""
    
    def __init__(self):
        self.memory = HybridMemory()
        self.llm = ollama_client
        self.tools = self._register_tools()
        self.workflow = self._build_workflow()
    
    def _register_tools(self) -> List[Tool]:
        """注册工具函数"""
        return [
            Tool(
                name="queryWeather",
                func=query_weather,
                description="查询城市天气信息",
                args_schema=WeatherInput
            )
        ]
    
    def _build_workflow(self):
        """构建LangGraph工作流"""
        workflow = StateGraph(AgentState)
        
        # 添加节点
        workflow.add_node("preprocess", self._preprocess_input) # 预处理用户输入
        workflow.add_node("analyze_intent", self._analyze_intent) # 分析用户意图    
        workflow.add_node("call_tool", self._call_tool)       # 调用外部工具
        workflow.add_node("generate_response", self._generate_response) # 生成最终响应
        
        # 🔥 关键修复1：设置明确入口点
        workflow.set_entry_point("preprocess")
        
        # 添加边
        workflow.add_edge("preprocess", "analyze_intent")
        
        # 🔥 关键修复2：添加条件路由
        workflow.add_conditional_edges(   # 判断使用什么工具
            "analyze_intent",
            self._route_based_on_intent,   
            {
                "tool": "call_tool",
                "direct": "generate_response",
                "error": "generate_response"
            }
        )
        
        workflow.add_edge("call_tool", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    def _preprocess_input(self, state: AgentState) -> AgentState:
        """🔥 彻底修复：重写预处理逻辑"""
        try:
            user_id = state["user_id"]
            original_input = state["input"]
            session_id = self._get_session_id(user_id) # 生成会话id，用于区分同一用户的不同对话
            
            # 🔥 关键修复3：强制提取并保存当前查询中的地点
            current_locations = self._extract_locations(original_input)
            if current_locations:
                for location in current_locations:
                    self._force_save_location(user_id, session_id, location, original_input)
            
            # 🔥 关键修复4：使用改进的指代消解
            resolved_input = self.memory.resolve_reference(user_id, original_input) # 将模糊指定转为具体对象
            
            
            state["input"] = resolved_input # 状态更新操作 指定消解和预处理后的用户输入
            
            # 🔥 关键修复5：获取正确的上下文
            recent_context = self.memory.get_context(user_id, session_id, limit=2) # 获取最近两轮对话历史
            context_info = self._analyze_context(recent_context, resolved_input) # 分析上下文获取关键信息
            state["memory"] = context_info.get("summary", "无历史对话") # 将摘要信息存入状态
            
        except Exception as e:
            state["error"] = f"预处理失败: {str(e)}"
        
        return state
    
    def _force_save_location(self, user_id: str, session_id: str, location: str, context: str):
        """🔥 新增：强制保存地点实体"""
        with sqlite3.connect(self.memory.db_path) as conn: # 连接数据库
            cursor = conn.cursor()  # 创建游标用于执行sql语句和获取结果
            cursor.execute("""
                    INSERT OR REPLACE INTO entity_tracking 
                    (user_id, session_id, entity_name, entity_type, context, mention_count, last_mentioned) 
                    VALUES (?, ?, ?, ?, ?, COALESCE((SELECT mention_count FROM entity_tracking WHERE user_id=? AND session_id=? AND entity_name=?), 0) + 1, CURRENT_TIMESTAMP)
                """, (user_id, session_id, location, "location", context, user_id, session_id, location))
            conn.commit() # 提交事务
    
    def _analyze_context(self, context: List[Dict], current_input: str) -> Dict[str, Any]:
        """🔥 彻底修复：改进上下文分析"""
        info = {     # 初始化一个包括上下文的信息字典
            "location": None,
            "current_locations": [],
            "summary": "无历史对话",
            "has_relevant_context": False
        }
        
        if not context:
            return info
        
        # 🔥 关键修复6：优先分析当前对话（最新的对话）
        current_chat = context[0] # 从对话历史中获取最新一轮的对话
        current_text = f"{current_chat.get('user_input', '')} {current_chat.get('assistant_response', '')}"# 合并用户输入和助手响应判断用户询问的对象
        
        # 提取当前对话中的地点
        current_locations = self._extract_locations(current_text)
        info["current_locations"] = current_locations# 提取到的地点信息存入上下文信息字典中
        
        if current_locations:
            info["location"] = current_locations[0]  # 🔥 优先使用当前对话的地点
        
        # 构建上下文摘要
        summary_parts = []  # 准备存储每轮对话摘要片段
        for i, chat in enumerate(context[-2:], 1):  # 遍历最近对话，取最后两轮
            user_msg = chat.get("user_input", "")[:30] + "..." if len(chat.get("user_input", "")) > 30 else chat.get("user_input", "") #处理用户消息，使用的截断逻辑，nlp的输入token有限制
            assistant_msg = chat.get("assistant_response", "")[:40] + "..." if len(chat.get("assistant_response", "")) > 40 else chat.get("assistant_response", "")
            
            summary_parts.append(f"{i}. 用户: {user_msg}") # 记录用户信息
            summary_parts.append(f"   助手: {assistant_msg}") # 记录ai助手响应
        
        if summary_parts:
            info["summary"] = "最近对话:\n" + "\n".join(summary_parts)
            info["has_relevant_context"] = self._is_context_relevant(context, current_input) # 判断当前用户输入是否与历史对话有关
        
        return info
    def _analyze_intent(self, state: AgentState) -> AgentState:
        """分析用户意图"""
        try:
            query = state["input"]
            
            if "天气" in query:
                city = self._extract_city(query)
                state["current_tool"] = "queryWeather"
                state["tool_params"] = {"city": city}
                
                
            else:
                state["current_tool"] = None
                
                
        except Exception as e:
            state["error"] = f"意图分析失败: {str(e)}"
        
        return state
    
    
    def _route_based_on_intent(self, state: AgentState) -> str:
        """路由决策"""
        if state.get("error"):
            return "error"
        return "tool" if state.get("current_tool") else "direct"
    
    def _call_tool(self, state: AgentState) -> AgentState:
        """调用工具"""
        try:
            tool_name = state["current_tool"]
            tool = next(t for t in self.tools if t.name == tool_name) # 从工具列表中查找到指定名称的工具对象
            result = tool.run(state["tool_params"]) # 执行指定工具并传入参数
            state["tool_result"] = result # 将工具调用结果存储到对话状态
        except Exception as e:
            state["error"] = f"工具调用失败: {str(e)}"
        return state
    
    def _generate_response(self, state: AgentState) -> AgentState:
        """🔥 彻底修复：生成最终响应"""
        try:
            if state.get("error"):
                state["response"] = f"[错误] {state['error']}"
            elif state.get("tool_result"):
                tool_response = self._format_tool_response(state["tool_result"]) # 将工具返回的原始数据转换为适合用户阅读的文本格式
                
                # 🔥 关键修复7：结合上下文生成更自然的响应
                if state["memory"] != "无历史对话":
                    prompt = f"基于之前的对话，{tool_response}。请用自然的中文表达这个信息，考虑上下文连贯性。"
                    state["response"] = self.llm.generate(prompt)
                else:
                    state["response"] = tool_response
            else:
                # 🔥 关键修复8：直接对话时也结合上下文
                prompt = self._build_context_aware_prompt(state["input"], state["memory"])
                state["response"] = self.llm.generate(prompt)
            
            # 🔥 关键修复9：保存对话到记忆
            self.memory.save_context(
                {"user_id": state["user_id"], "input": state["input"]},
                {"output": state["response"]}
            )
            
        except Exception as e:
            state["response"] = f"[错误] 生成响应失败: {str(e)}"
        
        return state
    
    def _build_context_aware_prompt(self, query: str, context: str) -> str:# 构建结合上下文的提示词模板
        """构建结合上下文的提示词"""
        if context and context != "无历史对话":
            return f"""请基于以下对话历史和当前问题，用自然的中文进行回答：

{context}

当前问题: {query}

要求:
1. 回答要简洁专业，考虑上下文连贯性
2. 如果问题涉及之前提到的地方或事物，请自然引用
3. 用中文回答

请回答:"""
        else:
            return f"用户问: {query}\n\n请用自然的中文回答:"
    
    def _format_tool_response(self, result: Dict[str, Any]) -> str:
        """格式化工具响应"""
        if isinstance(result, dict):
            if result.get("success"):
                data = result.get("data", {})
                if isinstance(data, dict):
                    items = [f"{k}: {v}" for k, v in data.items()]
                    return "，".join(items)
                return str(result.get("message", "操作成功"))
            return f"操作失败: {result.get('error', '未知错误')}"
        return str(result)
    
    # ===================== 辅助方法 =====================
    def _extract_city(self, query: str) -> str:
        """🔥 彻底修复：改进城市提取算法"""
        try:
            # 🔥 关键修复10：使用更精确的匹配模式
            patterns = [
                r'([京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]{1,2}[省市县区]?)天气',
                r'([\u4e00-\u9fa5]{2,4}?(?:市|省|区|县))天气',
                r'在?([\u4e00-\u9fa5]{2,4})的?天气'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, query)
                if match:
                    city = match.group(1)
                    if len(city) >= 2:
                        return city
            
            # 🔥 关键修复11：从常见城市列表中匹配
            common_cities = ["北京", "上海", "天津", "重庆", "广州", "深圳", "杭州", "南京", "武汉", "成都"]
            for city in common_cities:
                if city in query:
                    return city
            
            # 🔥 关键修复12：使用默认值
            return "北京"
            
        except Exception as e:
            return "北京"
    
    def _get_session_id(self, user_id: str) -> str:
        """生成会话ID"""
        current_hour = datetime.now().strftime("%Y%m%d%H")
        return f"{user_id}_{current_hour}"
    
    def _extract_locations(self, text: str) -> List[str]:
        """🔥 彻底修复：改进地点提取算法"""
        if not text:
            return []
        
        # 🔥 关键修复13：使用更精确的正则表达式
        patterns = [
            # 匹配城市+天气模式（如"北京天气"）
            r'([京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]{1,2}[省市县区]?)天气',
            # 匹配单独的城市名称
            r'([京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]{1,2}[省市县区]?)',
            # 匹配常见城市列表
            r'(北京|上海|天津|重庆|广州|深圳|杭州|南京|武汉|成都|西安|苏州|厦门|青岛|大连|沈阳|长春|哈尔滨|石家庄|郑州|长沙|合肥|福州|南昌|南宁|昆明|贵阳|兰州|银川|西宁|乌鲁木齐|呼和浩特|拉萨|海口)'
        ]
        
        locations = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # 🔥 关键修复14：确保是有效城市名称
                if len(match) >= 2 and match not in locations:
                    locations.append(match)
        
        return list(set(locations))  # 去重
    
    def _is_context_relevant(self, context: List[Dict], current_input: str) -> bool:
        """检查上下文是否相关"""
        if not context:
            return False
        
        recent_text = " ".join([chat.get("user_input", "") + " " + chat.get("assistant_response", "") for chat in context[-2:]])
        
        common_keywords = ["天气", "旅游"] # 业务关键词库
        current_keywords = [kw for kw in common_keywords if kw in current_input] # 当前输入中的关键词
        context_keywords = [kw for kw in common_keywords if kw in recent_text] # 历史对话中的关键词
        
        return bool(set(current_keywords) & set(context_keywords)) #​ ​通过集合交集运算判断当前输入和历史对话是否存在共同的关键词​​
    
    def process(self, user_id: str, query: str) -> Dict[str, Any]:  # AI Agent 处理用户请求的核心入口函数​
        """处理用户查询 - 主入口"""
        try:
            initial_state = AgentState(
                user_id=user_id,
                input=query,
                memory="",
                current_tool=None,
                tool_params={},
                tool_result=None,
                response="",
                error=None
            )
            
            final_state = self.workflow.invoke(initial_state)
            
            # 🔥 关键修复15：获取解析后的查询
            resolved_query = self.memory.resolve_reference(user_id, query)
            
            return {
                "success": final_state.get("error") is None,
                "user_id": user_id,
                "query": query,
                "resolved_query": resolved_query,
                "response": final_state["response"],
                "tool_used": final_state.get("current_tool"),
                "context_used": final_state.get("memory", "") != "无历史对话"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": "系统处理请求时出错"
            }
    
    def debug_memory(self, user_id: str):
        """调试记忆状态"""
        self.memory.debug_entities(user_id)

# 全局实例
agent = HybridAgent()