# 本地运行和Stripe配置指南

## 1. 环境准备

### 1.1 安装依赖

```bash
pip install -r requirements.txt
```

### 1.2 配置环境变量

创建 `.env` 文件并添加以下环境变量：

```env
# Session/签名用的随机字符串
SECRET_KEY=your_secret_key_here

# Stripe 配置
STRIPE_API_KEY=your_stripe_secret_key
STRIPE_PRICE_ID=your_stripe_price_id

# 本服务对外访问的基础 URL
BASE_URL=http://localhost:8000
```

## 2. Stripe 配置步骤

### 2.1 创建 Stripe 账户

1. 访问 [Stripe 官网](https://stripe.com/) 并注册账户
2. 完成邮箱验证和账户设置

### 2.2 获取 API 密钥

1. 登录 Stripe 后台
2. 导航到 **开发工具** > **API 密钥**
3. 复制 **测试密钥** 中的 `sk_test_` 开头的密钥，粘贴到 `.env` 文件的 `STRIPE_API_KEY` 字段

### 2.3 创建产品和价格

1. 导航到 **产品** > **添加产品**
2. 填写产品信息：
   - 产品名称：SP500 数据服务
   - 产品类型：订阅
   - 价格：10 美元/年
   - 计费周期：每年
3. 点击 **创建产品**
4. 复制生成的价格 ID（格式类似 `price_123456789`），粘贴到 `.env` 文件的 `STRIPE_PRICE_ID` 字段

### 2.4 配置 webhook（可选）

1. 导航到 **开发工具** > **Webhook**
2. 点击 **添加端点**
3. 输入端点 URL：`http://localhost:8000/billing/webhook`
4. 选择事件：
   - `checkout.session.completed`
   - `invoice.payment_succeeded`
   - `customer.subscription.updated`
5. 点击 **添加端点**
6. 复制 webhook 签名密钥并保存（用于生产环境）

## 3. 数据库配置

### 3.1 MySQL 数据库准备

1. 确保 MySQL 8.4 已安装并运行
2. 创建数据库：

```sql
CREATE DATABASE sp500 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

3. 创建用户并授权：

```sql
CREATE USER 'admin'@'localhost' IDENTIFIED BY 'passw0rd';
GRANT ALL PRIVILEGES ON sp500.* TO 'admin'@'localhost';
FLUSH PRIVILEGES;
```

### 3.2 数据库初始化

启动服务时，系统会自动创建所需的表结构。

## 4. 本地运行步骤

### 4.1 启动开发服务器

```bash
uvicorn app.main:app --reload
```

服务将在 `http://localhost:8000` 启动。

### 4.2 同步 SP500 数据（可选）

创建 `scripts/sync_sp500.py` 文件并运行以下命令同步数据：

```bash
python scripts/sync_sp500.py
```

### 4.3 启动 MCP 服务器（可选）

创建 `scripts/mcp_server.py` 文件并运行以下命令启动 MCP 服务：

```bash
python scripts/mcp_server.py
```

## 5. 功能测试

### 5.1 访问首页

打开浏览器访问 `http://localhost:8000`，查看首页介绍。

### 5.2 测试登录功能

1. 访问 `http://localhost:8000/auth/login`
2. 输入邮箱并点击「发送验证码」
3. 在终端查看生成的验证码
4. 输入验证码并点击「验证登录」
5. 成功登录后会跳转到仪表盘

### 5.3 测试订阅功能

1. 访问 `http://localhost:8000/billing/subscribe`
2. 输入邮箱并点击「立即订阅」
3. 被重定向到 Stripe 支付页面
4. 使用测试卡号（4242 4242 4242 4242）完成支付
5. 支付成功后会跳转到成功页面

### 5.4 测试令牌管理

1. 访问 `http://localhost:8000/tokens`
2. 创建新令牌并查看生成的令牌
3. 测试拷贝和删除令牌功能

### 5.5 测试 API 接口

使用生成的令牌访问 API：

```bash
curl -H "Authorization: Bearer your_token_here" http://localhost:8000/api/sp500/2024-01-01
```

## 6. 生产环境部署注意事项

1. 使用真实的 Stripe API 密钥（从测试模式切换到生产模式）
2. 配置真实的 BASE_URL
3. 设置强密码的数据库用户
4. 使用 HTTPS 协议
5. 配置适当的日志记录
6. 设置定期数据同步任务

## 7. 常见问题排查

### 7.1 数据库连接失败

- 检查 MySQL 服务是否运行
- 验证数据库配置是否正确
- 确认用户权限是否正确

### 7.2 Stripe 支付失败

- 检查 Stripe API 密钥是否正确
- 确认价格 ID 是否有效
- 查看 Stripe 后台的错误日志

### 7.3 API 访问被拒绝

- 检查令牌是否有效
- 确认用户是否已订阅
- 验证请求头中的 Authorization 格式是否正确

### 7.4 服务启动失败

- 检查端口是否被占用
- 验证环境变量是否配置正确
- 查看终端输出的错误信息

## 8. 技术支持

如果遇到任何问题，请参考以下资源：

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Stripe 文档](https://stripe.com/docs)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
