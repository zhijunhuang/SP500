## SP500 数据服务（Python / FastAPI）

一个基于维基百科的标普 500 成分股历史数据服务，功能包括：

- 用户登录（邮箱验证码，自动注册）
- 用户订阅（每年 \$10，Stripe 收款）
- 令牌管理（创建 / 拷贝 / 删除访问令牌）
- HTTP 接口 & MCP 服务：按日期返回当天真实的标普 500 成分股列表
- 首页介绍：引用《Stocks on the Move》关于历史真实成分数据重要性的观点

### 技术栈

- 后端框架：FastAPI
- 数据库：MySQL 8.4 + SQLAlchemy
- 前端：FastAPI + Jinja2 模板渲染简单页面
- 支付：Stripe Python SDK
- MCP：基于 `mcp` Python SDK 的 MCP Server

### 快速开始（开发环境）

1. 安装依赖：

   ```bash
   pip install -r requirements.txt
   ```

2. 配置环境变量（可以放在 `.env`，也可以直接导出）：

   - `SECRET_KEY`：Session/签名用的随机字符串
   - `STRIPE_API_KEY`：Stripe 后台的 Secret key
   - `STRIPE_PRICE_ID`：一年 \$10 的订阅价格 ID
   - `BASE_URL`：本服务对外访问的基础 URL（例如 `https://sp500.example.com`）

3. 初始化数据库并运行开发服务器（后续会补充脚本）：

   ```bash
   uvicorn app.main:app --reload
   ```

4. 同步一次维基百科标普 500 成分数据（后续脚本名暂定为 `scripts/sync_sp500.py`）：

   ```bash
   python scripts/sync_sp500.py
   ```

5. MCP 服务器（后续实现后补充命令）：

   ```bash
   python scripts/mcp_server.py
   ```

> 注意：本项目整理的数据并非标普道琼斯指数公司官方数据，仅用于研究和回测，不构成任何投资建议。使用前请阅读 `license.html`。

