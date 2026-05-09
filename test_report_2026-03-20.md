# 测试覆盖率报告

**日期**: 2026-03-20
**测试框架**: pytest
**运行命令**: `pytest tests/ -v --tb=short --cov=app --cov-report=term-missing`

---

## 总体覆盖率

| 指标 | 数值 |
|------|------|
| **总覆盖率** | **80%** |
| 总语句数 | 412 |
| 未覆盖语句 | 83 |
| 通过测试 | 41 |

---

## 各模块覆盖率

| 模块 | 覆盖率 | 未覆盖行 | 说明 |
|------|--------|----------|------|
| `app/main.py` | 97% | 27 | static 目录不存在时跳过 |
| `app/models.py` | 100% | - | 完全覆盖 |
| `app/routers/__init__.py` | 100% | - | 完全覆盖 |
| `app/routers/api.py` | 95% | 21, 42 | 少量辅助函数 |
| `app/routers/auth.py` | 81% | 31-32, 69-108 | SMTP 发送逻辑 |
| `app/routers/billing.py` | 46% | 83-164 | Stripe webhook 签名验证 |
| `app/routers/tokens.py` | 100% | - | 完全覆盖 |
| `app/utils/db.py` | 68% | 9-10, 29-33 | MySQL 特定连接代码 |

---

## 测试分布

| 测试文件 | 测试数 | 覆盖内容 |
|----------|--------|----------|
| `test_api.py` | 8 | API 认证、数据查询、日期过滤 |
| `test_auth.py` | 12 | 邮箱验证码登录、session 管理 |
| `test_billing.py` | 6 | 订阅页面、Stripe checkout |
| `test_main.py` | 2 | 首页、仪表盘 |
| `test_tokens.py` | 13 | Token CRUD 操作 |

---

## 未覆盖代码说明

### 1. SMTP 发送逻辑 (`auth.py:69-108`)
- `send_verification_email()` 函数依赖真实 SMTP 服务器
- 当前测试验证了"未配置 SMTP 时日志输出"
- 如需完全覆盖，需使用 `unittest.mock` 模拟 `smtplib.SMTP`

### 2. Stripe Webhook 签名验证 (`billing.py:83-164`)
- Webhook 处理函数需要 `stripe_signature` header 验证
- `stripe.Webhook.construct_event()` 需要真实的 webhook secret
- 建议: 使用 [Stripe CLI](https://docs.stripe.com/stripe-cli) 进行本地集成测试

### 3. MySQL 特定代码 (`utils/db.py:9-10, 29-33`)
- 测试使用 `sqlite:///:memory:` 而非 MySQL
- `config/db.py` 中的硬编码凭据路径未执行
- 生产环境使用 MySQL，该代码会被执行

### 4. Static 文件挂载 (`main.py:27`)
- `static` 目录在测试环境中不存在
- 该代码只在目录存在时执行

---

## 提升覆盖率建议

1. **Stripe Webhook**: 使用 Stripe CLI 转发 webhook 到本地测试服务器
2. **SMTP**: 添加 `unittest.mock.patch` 模拟 `smtplib.SMTP`
3. **MySQL**: 添加单独的集成测试套件使用真实 MySQL

---

## 运行测试

```bash
# 构建测试环境
./build.sh

# 运行测试（带覆盖率）
./test.sh

# 启动真实服务器（手动测试）
./start.sh

# 停止服务器
./stop.sh
```
