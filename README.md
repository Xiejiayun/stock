# A股交易决策支持系统

中国A股市场交易信息与决策支持工具，基于 AKShare 免费数据源。

## 功能

- **市场概览**: 主要指数行情、涨跌家数统计、涨跌幅分布图
- **个股搜索**: 按代码/名称搜索，显示K线图+均线
- **技术指标**: MACD、RSI、KDJ 指标图表
- **交易信号**: 多指标综合评分，生成买入/卖出/观望信号
- **板块排名**: 行业板块涨跌排名

## 快速启动

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

前端启动在 http://localhost:5173

## 技术栈

- **后端**: Python + FastAPI + AKShare + Pandas + NumPy
- **前端**: React + Vite + lightweight-charts + Recharts
- **数据源**: AKShare（免费，无需注册）

## 免责声明

本系统提供的交易信号仅供学习参考，不构成投资建议。股市有风险，投资需谨慎。
