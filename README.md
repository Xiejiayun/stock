# A股交易决策支持系统

中国A股市场交易信息与决策支持工具，基于 AKShare 免费数据源。

## 功能

- **市场概览**: 主要指数行情、涨跌家数统计、涨跌幅分布图
- **个股搜索**: 按代码/名称搜索，显示K线图+均线
- **技术指标**: MACD、RSI、KDJ 指标图表
- **交易信号**: 多指标综合评分，生成买入/卖出/观望信号
- **板块排名**: 行业板块涨跌排名

## 快速启动（开发模式）

### 后端

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

后端启动在 http://localhost:8000

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端启动在 http://localhost:5173（自动代理 API 到后端）

## 生产部署（Azure App Service）

### 一键构建

```bash
chmod +x build.sh
./build.sh
```

这会把前端 build 产物放到 `backend/static/`，然后 FastAPI 同时 serve API 和静态文件。

### 部署到 Azure App Service

1. **创建 App Service**:
   - Azure Portal → App Services → Create
   - Runtime: Python 3.11, Linux
   - Region: East Asia（香港）
   - Plan: B1（$13/月）或更高

2. **配置启动命令**:
   - Configuration → General Settings → Startup Command:
   ```
   cd /home/site/wwwroot/backend && PYTHONPATH=/home/site/wwwroot/.python_packages/lib/site-packages python -m gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

   GitHub Actions 会自动把依赖安装到 `.python_packages/`，并设置 `SCM_DO_BUILD_DURING_DEPLOYMENT=false`，避免 Azure Oryx 在 App Service 上重复构建。

3. **连接 GitHub 自动部署**:
   - Deployment Center → Source: GitHub → 选择此 repo
   - 或使用已配置的 GitHub Actions（`.github/workflows/main_stock.yml`）

4. **GitHub Actions 配置**（如使用 CI/CD）:
   - Repo Settings → Secrets: 添加 Azure OIDC 登录所需的 `AZUREAPPSERVICE_CLIENTID_*`、`AZUREAPPSERVICE_TENANTID_*`、`AZUREAPPSERVICE_SUBSCRIPTIONID_*`

部署完成后访问 `https://<你的app名>.azurewebsites.net`

## 技术栈

- **后端**: Python + FastAPI + AKShare + Pandas + NumPy
- **前端**: React + Vite + lightweight-charts + Recharts
- **数据源**: AKShare（免费，无需注册，从东方财富等获取数据）
- **部署**: Azure App Service (Python) + GitHub Actions CI/CD

## 免责声明

本系统提供的交易信号仅供学习参考，不构成投资建议。股市有风险，投资需谨慎。
