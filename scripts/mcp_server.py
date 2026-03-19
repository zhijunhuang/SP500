#!/usr/bin/env python3
"""
启动MCP服务器，提供标普500成分股数据服务
"""

import os
import sys
import datetime
import hashlib
from mcp import Server, Module, route

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.utils.db import SessionLocal
from app.models import SP500Constituent, APIToken, User


def hash_token(token: str) -> str:
    """Hash token for comparison."""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_api_token(token: str, db) -> tuple:
    """Verify API token and return (api_token, user) if valid, (None, None) otherwise."""
    if not token:
        return None, None

    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]

    token_hash = hash_token(token)

    api_token = db.query(APIToken).filter(
        APIToken.token_hash == token_hash,
        APIToken.revoked == False
    ).first()

    if not api_token:
        return None, None

    user = db.query(User).filter(User.id == api_token.user_id).first()
    return api_token, user


class SP500Module(Module):
    """标普500数据MCP模块"""

    @route
    def get_constituents(self, date, api_token: str = None):
        """
        获取指定日期的标普500成分股

        Args:
            date (str): 日期，格式为YYYY-MM-DD
            api_token (str): API令牌，格式为"Bearer <token>"

        Returns:
            dict: 包含成分股列表的字典
        """
        # 验证API令牌
        if not api_token:
            return {"error": "缺少API令牌，请提供api_token参数"}

        db = SessionLocal()
        try:
            api_token_obj, user = verify_api_token(api_token, db)
            if not api_token_obj:
                return {"error": "无效的API令牌"}

            if not user or user.subscription_status != "active":
                return {"error": "订阅已过期，请续订后继续使用"}

            # 解析日期
            try:
                target_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                return {"error": "日期格式错误，请使用YYYY-MM-DD格式"}

            # 查询指定日期的SP500成分股
            constituents = db.query(SP500Constituent).filter(
                SP500Constituent.effective_from <= target_date,
                (SP500Constituent.effective_to.is_(None)) | (SP500Constituent.effective_to > target_date)
            ).all()

            # 格式化返回数据
            result = {
                "date": date,
                "constituents": [
                    {
                        "code": c.code,
                        "company_name": c.company_name,
                        "sector": c.sector,
                        "industry": c.industry
                    }
                    for c in constituents
                ]
            }

            return result
        except Exception as e:
            return {"error": f"获取数据失败: {str(e)}"}
        finally:
            db.close()

def main():
    """主函数"""
    print("启动MCP服务器...")
    
    # 创建MCP服务器
    server = Server()
    
    # 注册SP500模块
    server.register(SP500Module(), "sp500")
    
    # 启动服务器
    server.start()
    
    print("MCP服务器已启动，监听默认端口")
    print("可以通过MCP客户端连接使用")

if __name__ == "__main__":
    main()
