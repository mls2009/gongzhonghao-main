#!/bin/bash

# macOS启动脚本 - 微信公众号自动发文系统
# macOS Startup Script - WeChat Auto Publishing System

echo "🚀 启动微信公众号自动发文系统 (macOS版本)"
echo "🚀 Starting WeChat Auto Publishing System (macOS Version)"

# 检查Python版本
python_version=$(python3 --version 2>&1)
if [[ $? -eq 0 ]]; then
    echo "✅ Python版本: $python_version"
else
    echo "❌ 错误: 未找到Python3，请先安装Python3"
    echo "❌ Error: Python3 not found, please install Python3 first"
    exit 1
fi

# 检查是否存在虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔄 激活虚拟环境..."
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# 安装依赖
echo "📥 安装依赖包..."
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# 安装Playwright浏览器
echo "🌐 安装Playwright浏览器..."
echo "🌐 Installing Playwright browsers..."
playwright install

# 跳过数据库初始化 - 使用现有数据库
echo "⏭️ 跳过数据库初始化，使用现有数据库"
echo "⏭️ Skipping database initialization, using existing database"

# 启动应用
echo "🎯 启动FastAPI应用..."
echo "🎯 Starting FastAPI application..."
echo ""
echo "📱 应用将在以下地址启动:"
echo "📱 Application will be available at:"
echo "   http://localhost:8000"
echo ""
echo "📝 注意事项 (Important Notes):"
echo "   • 确保比特浏览器已安装并运行在端口54345"
echo "   • Make sure BitBrowser is installed and running on port 54345"
echo "   • 首次使用请配置素材库路径"
echo "   • Please configure materials path on first use"
echo ""

cd app && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload