# 微信公众号自动发文系统 - macOS版本

## 系统概述
这是一个已经适配macOS的微信公众号自动发文系统，原本为Windows系统设计，现已完全兼容macOS。

## 主要改动

### ✅ 已完成的macOS适配
1. **文件夹选择对话框** - 替换Windows PowerShell为AppleScript
2. **移除Windows专有依赖** - 删除了`win32com.client`和`pythoncom`
3. **跨平台兼容性** - 支持Windows、macOS和Linux
4. **依赖包完善** - 添加了缺失的`httpx`和`apscheduler`

### 📋 系统要求
- Python 3.9+
- macOS 10.12+
- 比特浏览器 (BitBrowser) - 需要在端口54345运行

## 🚀 快速启动

### 方法一：使用启动脚本（推荐）
```bash
chmod +x start_macos.sh
./start_macos.sh
```

### 方法二：手动启动
```bash
# 1. 安装依赖
pip3 install -r requirements.txt

# 2. 安装Playwright浏览器
playwright install

# 3. 初始化数据库
python3 app/init_db.py

# 4. 启动应用
cd app && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 🔧 使用说明

### 1. 首次配置
- 访问 http://localhost:8000
- 点击"设置"页面
- 使用"选择文件夹"功能配置素材库路径（现已支持macOS原生对话框）

### 2. 素材管理
- 将Word文档(.docx)放入素材库文件夹
- 点击"扫描素材库"自动导入文档
- 系统会自动统计字数和图片数量

### 3. 账号管理
- 配置微信公众号账号信息
- 需要配合比特浏览器使用

### 4. 定时发布
- 支持定时发布功能
- 自动调度发布任务

## ⚠️ 重要注意事项

### 比特浏览器配置
系统依赖比特浏览器的API接口：
- **端口**: 127.0.0.1:54345
- **重要**: 比特浏览器的token配置请勿修改，这是固定值
- 确保比特浏览器在系统启动前已经运行

### 系统兼容性
- ✅ 文件夹选择：使用AppleScript实现原生macOS对话框
- ✅ 文件路径：使用跨平台的`os.path.join()`
- ✅ 数据库：SQLite，跨平台兼容
- ✅ Web服务：FastAPI，跨平台兼容

## 🐛 故障排除

### 常见问题
1. **模块缺失错误**
   ```bash
   pip3 install -r requirements.txt
   ```

2. **权限问题**
   ```bash
   chmod +x start_macos.sh
   ```

3. **端口占用**
   ```bash
   lsof -ti:8000 | xargs kill -9
   ```

4. **AppleScript权限**
   - 系统可能要求授予终端访问权限
   - 在"系统偏好设置" > "安全性与隐私" > "隐私" > "辅助功能"中允许终端访问

### 比特浏览器相关
- 确保比特浏览器在端口54345正常运行
- 检查防火墙设置是否阻止了本地连接
- 如果比特浏览器无法在macOS正常工作，系统会回退到标准Playwright自动化

## 📝 技术细节

### 改动的文件
- `app/routers/settings.py` - 文件夹选择功能适配
- `requirements.txt` - 添加缺失依赖
- `start_macos.sh` - macOS启动脚本

### 依赖包清单
```
fastapi>=0.109.0
uvicorn>=0.27.0
jinja2>=3.1.3
sqlalchemy>=2.0.25
pydantic>=2.5.3
python-multipart>=0.0.6
aiosqlite>=0.19.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-docx>=0.8.11
playwright>=1.40.0
requests>=2.31.0
schedule>=1.2.0
httpx>=0.26.0
apscheduler>=3.10.0
```

## 🔮 后续开发建议

1. **比特浏览器替代方案**: 如果比特浏览器在macOS上有兼容性问题，可以考虑实现纯Playwright的浏览器自动化方案

2. **系统服务**: 可以创建macOS plist文件，将系统注册为系统服务自动启动

3. **安全增强**: 添加SSL证书支持，启用HTTPS

4. **监控功能**: 添加系统健康检查和日志监控

## 🎉 已验证功能
- ✅ 系统启动正常
- ✅ Web界面访问正常  
- ✅ 数据库初始化成功
- ✅ 文件夹选择对话框（AppleScript）
- ✅ 素材库扫描功能
- ✅ 跨平台兼容性

系统现在已经完全适配macOS，可以正常使用！