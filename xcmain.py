#!/usr/bin/env python3
"""
AI Agent智能体系统 - 增强版 (带完整上下文支持)
"""

import logging
from datetime import datetime
from xcagent import agent

def setup_logging():
    """配置日志系统"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('agent.log')
        ]
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)  # 减少HTTP请求日志

def print_welcome_banner():
    """打印欢迎信息"""
    print("=" * 60)
    print("🤖 AI Agent 智能对话系统".center(50))
    print("=" * 60)
    print("✨ 功能特点:")
    print("  - 上下文记忆 (自动记住对话历史)")
    print("  - 智能指代消解 (理解'那'、'这里'等指代词)")
    print("  - 多工具集成 (天气、订单、旅行建议等)")
    print("=" * 60)
    print("📝 使用说明:")
    print("  输入 'quit' 或 '退出' 结束对话")
    print("  输入 'clear' 清除当前对话记忆")
    print("=" * 60)

def get_session_id(user_id: str) -> str:
    """生成会话ID (每小时新建一个会话)"""
    return f"{user_id}_{datetime.now().strftime('%Y%m%d%H')}"

def interactive_mode():
    """增强的交互模式 - 完整上下文支持"""
    print_welcome_banner()
    
    user_id = "demo_user"
    session_id = get_session_id(user_id)
    
    while True:
        try:
            user_input = input("\n👤 用户: ").strip()
            
            # 处理特殊命令
            if user_input.lower() in ['quit', '退出', 'exit']:
                print("\n🛑 对话已结束")
                break
                
            if user_input.lower() == 'clear':
                agent.memory.clear_context(user_id, session_id)
                print("\n🧹 已清除当前对话记忆")
                continue
                
            if not user_input:
                continue
                
            # 处理用户输入
            result = agent.process(user_id, user_input)
            
            # 显示处理结果
            print("\n" + "=" * 50)
            if result["success"]:
                print(f"🤖 助手: {result['response']}")
                
                # 调试信息 (仅在DEBUG模式显示)
                if logging.getLogger().level == logging.DEBUG:
                    if result.get("resolved_query") and result["resolved_query"] != result["query"]:
                        print(f"🔍 指代解析: '{result['query']}' → '{result['resolved_query']}'")
                    if result.get("tool_used"):
                        print(f"🛠️ 使用工具: {result['tool_used']}")
                    if result.get("context_used"):
                        print("💾 使用上下文记忆")
            else:
                print(f"❌ 错误: {result['response']}")
                
            print("=" * 50)
            
        except KeyboardInterrupt:
            print("\n\n👋 检测到中断指令，正在退出...")
            break
        except Exception as e:
            logging.error(f"系统错误: {e}")
            print("\n⚠️ 系统遇到错误，请稍后再试")

if __name__ == "__main__":
    setup_logging()
    interactive_mode()