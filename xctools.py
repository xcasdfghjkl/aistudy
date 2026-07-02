import requests
import re
from typing import Dict, Any
from datetime import datetime
from xcconfig import settings


def query_weather(city: str) -> Dict[str, Any]:
    """🔥 彻底修复：查询天气信息 - 改进城市名称处理"""
    try:
        # 🔥 关键修复1：清理和验证城市名称
        if "天气" in city:
            # 从"北京天气"中提取"北京"
            city = re.sub(r'天气$', '', city) # 移除字符串末尾的天气二字
        
        city = re.sub(r'[^\u4e00-\u9fa5]', '', city) # 移除字符串中所有的非中文字符
        if len(city) < 2:
            return {
                "success": False,
                "error": "城市名称无效",
                "suggestions": ["请提供完整的城市名称如'北京天气'"]
            }
        if settings.AMAP_API_KEY and settings.AMAP_API_KEY != "您的高德地图API密钥":
            return _query_real_weather(city)
        else:
            return _get_fallback_weather(city)
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "city": city
        }

def _query_real_weather(city: str) -> Dict[str, Any]:
    """查询真实天气API"""
    try:
        api_url = "https://restapi.amap.com/v3/weather/weatherInfo"
        params = {
            "key": settings.AMAP_API_KEY,
            "city": city,
            "extensions": "base",
            "output": "JSON"
        }
        
        response = requests.get(api_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("status") == "1" and data.get("infocode") == "10000": # 判断高德api调用是否成功
                if data.get("lives") and len(data["lives"]) > 0: # 检查高德api返回数据有效性的安全验证
                    weather_data = data["lives"][0] # 从高德api响应中提取第一条天气数据
                    
                    return {
                        "success": True,
                        "city": weather_data.get("city", city),
                        "data": {
                            "天气": weather_data.get("weather", "未知"),
                            "温度": f"{weather_data.get('temperature', 'N/A')}°C",
                            "湿度": f"{weather_data.get('humidity', 'N/A')}%",
                            "风向": weather_data.get('winddirection', '未知'),
                            "风力": f"{weather_data.get('windpower', 'N/A')}级",
                            "更新时间": weather_data.get('reporttime', '未知')
                        },
                        "source": "高德地图实时天气"
                    }
                else:
                    return _get_fallback_weather(city)
            else:
                return _get_fallback_weather(city)
        else:
            return _get_fallback_weather(city)
            
    except Exception:
        return _get_fallback_weather(city)
    
def _get_fallback_weather(city: str) -> Dict[str, Any]:
    """备用天气数据"""
    weather_db = {
        "北京": {"天气": "晴", "温度": "25°C", "湿度": "40%", "风向": "北风", "风力": "3级"},
        "上海": {"天气": "多云", "温度": "28°C", "湿度": "65%", "风向": "东南风", "风力": "2级"},
        "天津": {"天气": "晴", "温度": "26°C", "湿度": "50%", "风向": "西南风", "风力": "3级"}
    }
    
    if city in weather_db:
        return {
            "success": True,
            "city": city,
            "data": weather_db[city],
            "source": "模拟数据"
        }
    else:
        return {
            "success": True,
            "city": city,
            "data": {"天气": "数据更新中", "温度": "N/A", "湿度": "N/A"},
            "warning": f"暂无{city}的详细天气数据"
        }

def get_all_tools() -> list:
    """获取所有工具配置"""
    return [
        {
            "name": "queryWeather",
            "func": query_weather,
            "description": "查询城市天气信息",
            "args_schema": {"city": "城市名称"}
        }
    ]