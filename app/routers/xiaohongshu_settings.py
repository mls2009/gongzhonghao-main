from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from models.database import get_db, XiaohongshuSettings, XiaohongshuMaterial
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import text
import json
import os
import platform
import subprocess
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/xiaohongshu-settings", tags=["xiaohongshu-settings"])

class XiaohongshuSettingsUpdate(BaseModel):
    materials_path: str
    region_account_mapping: dict = {}
    auto_publish_time: Optional[str] = None  # HH:MM
    publish_days_window: Optional[int] = None
    window1_start: Optional[str] = None
    window1_end: Optional[str] = None
    window2_start: Optional[str] = None
    window2_end: Optional[str] = None
    window3_start: Optional[str] = None
    window3_end: Optional[str] = None

class AutoPublishToggle(BaseModel):
    enabled: bool

def _ensure_settings_columns(db: Session):
    """确保 xiaohongshu_settings 新增列存在（SQLite 迁移兼容）"""
    try:
        rows = db.execute(text("PRAGMA table_info(xiaohongshu_settings)")).fetchall()
        cols = {r[1] for r in rows}
        if 'auto_publish_time' not in cols:
            db.execute(text("ALTER TABLE xiaohongshu_settings ADD COLUMN auto_publish_time TEXT"))
        if 'auto_publish_enabled' not in cols:
            db.execute(text("ALTER TABLE xiaohongshu_settings ADD COLUMN auto_publish_enabled INTEGER DEFAULT 0"))
        if 'add_product_enabled' not in cols:
            db.execute(text("ALTER TABLE xiaohongshu_settings ADD COLUMN add_product_enabled INTEGER DEFAULT 0"))
        if 'default_mode' not in cols:
            db.execute(text("ALTER TABLE xiaohongshu_settings ADD COLUMN default_mode TEXT DEFAULT 'random'"))
        if 'publish_days_window' not in cols:
            db.execute(text("ALTER TABLE xiaohongshu_settings ADD COLUMN publish_days_window INTEGER DEFAULT 2"))
        # time windows
        for col in ['window1_start','window1_end','window2_start','window2_end','window3_start','window3_end']:
            if col not in cols:
                db.execute(text(f"ALTER TABLE xiaohongshu_settings ADD COLUMN {col} TEXT"))
        db.commit()
    except Exception as e:
        # 不阻断主流程，记录日志
        logging.getLogger(__name__).warning(f"确保设置列存在时出错: {e}")

@router.get("/config")
async def get_xiaohongshu_config(db: Session = Depends(get_db)):
    """获取小红书配置"""
    _ensure_settings_columns(db)
    settings = db.query(XiaohongshuSettings).first()
    if not settings:
        return {
            "materials_path": "",
            "total_folders": 0,
            "last_scan": None,
            "region_account_mapping": {}
        }
    
    try:
        region_mapping = json.loads(settings.region_account_mapping) if settings.region_account_mapping else {}
    except:
        region_mapping = {}
    
    return {
        "materials_path": settings.materials_path or "",
        "total_folders": settings.total_folders,
        "last_scan": settings.last_scan.isoformat() if settings.last_scan else None,
        "region_account_mapping": region_mapping,
        "auto_publish_time": settings.auto_publish_time,
        "auto_publish_enabled": getattr(settings, 'auto_publish_enabled', False),
        "add_product_enabled": getattr(settings, 'add_product_enabled', False)
        ,"default_mode": getattr(settings, 'default_mode', 'random')
        ,"publish_days_window": getattr(settings, 'publish_days_window', 2)
        ,"window1_start": settings.window1_start
        ,"window1_end": settings.window1_end
        ,"window2_start": settings.window2_start
        ,"window2_end": settings.window2_end
        ,"window3_start": settings.window3_start
        ,"window3_end": settings.window3_end
    }

@router.post("/config")
async def update_xiaohongshu_config(
    config: XiaohongshuSettingsUpdate,
    db: Session = Depends(get_db)
):
    """更新小红书配置"""
    _ensure_settings_columns(db)
    settings = db.query(XiaohongshuSettings).first()
    
    # 确保新列存在（迁移兼容）
    try:
        db.execute(text("PRAGMA table_info(xiaohongshu_settings)"))
    except Exception:
        pass

    if not settings:
        settings = XiaohongshuSettings(
            materials_path=config.materials_path,
            region_account_mapping=json.dumps(config.region_account_mapping, ensure_ascii=False),
            auto_publish_time=config.auto_publish_time,
            publish_days_window=(config.publish_days_window if config.publish_days_window is not None else 2),
            window1_start=config.window1_start,
            window1_end=config.window1_end,
            window2_start=config.window2_start,
            window2_end=config.window2_end,
            window3_start=config.window3_start,
            window3_end=config.window3_end,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(settings)
    else:
        settings.materials_path = config.materials_path
        settings.region_account_mapping = json.dumps(config.region_account_mapping, ensure_ascii=False)
        if config.auto_publish_time is not None:
            settings.auto_publish_time = config.auto_publish_time
        if config.publish_days_window is not None:
            settings.publish_days_window = config.publish_days_window
        # update windows if provided
        for k in ['window1_start','window1_end','window2_start','window2_end','window3_start','window3_end']:
            v = getattr(config, k, None)
            if v is not None:
                setattr(settings, k, v)
        settings.updated_at = datetime.now()
    
    db.commit()

    # 立即根据新规则重分配所有素材的账号，使“保存设置”即时生效
    try:
        logger.info("保存设置完成，开始根据新的地区映射规则立即重分配素材账号")
        region_account_mapping = config.region_account_mapping or {}

        # 如果外部未传映射（例如仅保存路径或时间），则使用数据库中的最新映射
        if not region_account_mapping and settings and settings.region_account_mapping:
            try:
                region_account_mapping = json.loads(settings.region_account_mapping) or {}
            except Exception:
                region_account_mapping = {}

        # 重分配
        all_materials = db.query(XiaohongshuMaterial).all()
        updated_count = 0
        for material in all_materials:
            old_account_id = material.account_id
            material.account_id = None

            # 按规则顺序匹配；支持多关键词（英文/中文逗号分隔）
            for regions, account_id in (region_account_mapping.items() if isinstance(region_account_mapping, dict) else []):
                try:
                    import re
                    keywords = [k.strip() for k in re.split(r"[,，]", str(regions)) if k.strip()]
                except Exception:
                    keywords = [str(regions)]
                if any(k and k in material.title for k in keywords):
                    material.account_id = account_id
                    updated_count += 1
                    logger.info(f"[保存设置-重分配] 素材 '{material.title}' 命中 {keywords} → 账号ID: {account_id}")
                    break

        db.commit()
        return {"success": True, "message": f"小红书配置已更新，并立即重分配 {updated_count} 个素材账号"}
    except Exception as e:
        logger.error(f"保存设置后的重分配失败: {e}")
        db.rollback()
    return {"success": True, "message": "小红书配置已更新（重分配失败，请在设置中使用‘添加新规则’触发重分配）"}

@router.post("/add-product/toggle")
async def toggle_add_product(request: dict, db: Session = Depends(get_db)):
    """从小红书素材页的开关持久化全局添加商品状态"""
    _ensure_settings_columns(db)
    enabled = bool(request.get("enabled", False))
    settings = db.query(XiaohongshuSettings).first()
    if not settings:
        settings = XiaohongshuSettings(
            materials_path="",
            add_product_enabled=enabled,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(settings)
    else:
        settings.add_product_enabled = enabled
        settings.updated_at = datetime.now()
    db.commit()
    logger.info(f"已更新全局添加商品设置: {settings.add_product_enabled}")
    return {"success": True, "add_product_enabled": settings.add_product_enabled}

@router.post("/default-mode")
async def set_default_mode(request: dict, db: Session = Depends(get_db)):
    """持久化默认模式：insert/overlay/random"""
    _ensure_settings_columns(db)
    mode = str(request.get('mode', 'random')).lower()
    if mode not in ['insert','overlay','random']:
        raise HTTPException(status_code=400, detail="invalid mode")
    settings = db.query(XiaohongshuSettings).first()
    if not settings:
        settings = XiaohongshuSettings(
            materials_path="",
            default_mode=mode,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(settings)
    else:
        settings.default_mode = mode
        settings.updated_at = datetime.now()
    db.commit()
    return {"success": True, "default_mode": settings.default_mode}

@router.post("/auto-publish/toggle")
async def toggle_auto_publish(toggle: AutoPublishToggle, db: Session = Depends(get_db)):
    """开启/关闭自动发布，后端将根据设置的时间每天触发一次获取邮箱素材"""
    _ensure_settings_columns(db)
    settings = db.query(XiaohongshuSettings).first()
    if not settings:
        raise HTTPException(status_code=400, detail="请先保存小红书素材库设置")
    if not settings.auto_publish_time:
        raise HTTPException(status_code=400, detail="请先在设置页配置自动发布时间")

    settings.auto_publish_enabled = bool(toggle.enabled)
    settings.updated_at = datetime.now()
    db.commit()
    
    # 强制刷新以获取最新状态，防止会话缓存导致读取到旧的 add_product_enabled
    db.refresh(settings)

    # Log the status for user visibility
    add_product_status = "开启" if settings.add_product_enabled else "关闭"
    logger.info(f"自动发布已{'开启' if settings.auto_publish_enabled else '关闭'}，当前添加商品设置状态: {add_product_status}")

    # 更新调度器
    try:
        from scheduler.publish_scheduler import update_xhs_auto_job
        update_xhs_auto_job()
    except Exception:
        pass

    return {"success": True, "enabled": settings.auto_publish_enabled}

@router.get("/auto-events")
async def xhs_auto_events(request: Request):
    """Server-Sent Events endpoint: pushes auto-fetch results to clients."""
    from utils.event_bus import subscribe, unsubscribe
    import asyncio, json

    q = subscribe()

    async def event_generator():
        try:
            while True:
                # Disconnect check
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=15.0)
                    data = json.dumps(msg, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    # keep-alive comment
                    yield ": keep-alive\n\n"
        finally:
            unsubscribe(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/stats")
async def get_xiaohongshu_stats(db: Session = Depends(get_db)):
    """获取小红书素材统计"""
    settings = db.query(XiaohongshuSettings).first()
    if not settings or not settings.materials_path:
        return {
            "total_folders": 0,
            "last_scan": None
        }
    
    # 简化版本 - 返回基础统计
    folder_count = 0
    if os.path.exists(settings.materials_path):
        try:
            folder_count = len([d for d in os.listdir(settings.materials_path) 
                              if os.path.isdir(os.path.join(settings.materials_path, d))])
        except:
            folder_count = 0
    
    return {
        "total_folders": folder_count,
        "last_scan": settings.last_scan.isoformat() if settings.last_scan else None
    }

@router.post("/scan")
async def scan_materials_folder(db: Session = Depends(get_db)):
    """扫描素材文件夹 - 扫描子文件夹作为素材"""
    settings = db.query(XiaohongshuSettings).first()
    if not settings or not settings.materials_path:
        logger.error("小红书素材库路径未配置")
        raise HTTPException(status_code=400, detail="请先配置小红书素材库路径")
    
    if not os.path.exists(settings.materials_path):
        logger.error(f"小红书素材库路径不存在: {settings.materials_path}")
        raise HTTPException(status_code=400, detail="素材库路径不存在")
    
    logger.info(f"开始扫描小红书素材库: {settings.materials_path}")
    
    try:
        # 获取地区账号映射配置
        region_mapping = {}
        if settings.region_account_mapping:
            try:
                region_mapping = json.loads(settings.region_account_mapping)
                logger.info(f"地区账号映射配置: {region_mapping}")
            except:
                logger.warning("解析地区账号映射配置失败")
        
        # 获取已存在的素材，避免重复添加
        existing_materials = {material.title: material for material in 
                            db.query(XiaohongshuMaterial).all()}
        logger.info(f"数据库中已有 {len(existing_materials)} 个素材记录")
        
        added_count = 0
        updated_count = 0
        error_count = 0
        
        # 扫描素材库中的所有子文件夹
        all_items = os.listdir(settings.materials_path)
        logger.info(f"素材库中共有 {len(all_items)} 个项目")
        
        for item in all_items:
            folder_path = os.path.join(settings.materials_path, item)
            
            # 跳过文件，只处理文件夹
            if not os.path.isdir(folder_path):
                logger.debug(f"跳过文件: {item}")
                continue
            
            try:
                # 文件夹名称作为素材标题
                folder_name = item
                logger.debug(f"处理文件夹: {folder_name}")
                
                # 统计文件夹中的图片数量
                image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
                image_count = 0
                
                for file in os.listdir(folder_path):
                    file_ext = os.path.splitext(file.lower())[1]
                    if file_ext in image_extensions:
                        image_count += 1
                
                logger.debug(f"文件夹 {folder_name} 包含 {image_count} 个图片")
                
                # 根据地区映射自动分配账号（支持多关键词，以逗号或中文逗号分隔）
                assigned_account_id = None
                for regions, account_id in region_mapping.items():
                    try:
                        import re
                        keywords = [k.strip() for k in re.split(r"[,，]", str(regions)) if k.strip()]
                    except Exception:
                        keywords = [str(regions)]
                    if any(k in folder_name for k in keywords):
                        assigned_account_id = account_id
                        logger.info(f"素材 '{folder_name}' 匹配地区关键词 '{keywords}', 自动分配账号ID: {account_id}")
                        break
                
                # 检查是否已存在该素材
                if folder_name in existing_materials:
                    # 更新现有素材的图片数量、路径和账号分配
                    material = existing_materials[folder_name]
                    material.folder_path = folder_path
                    material.image_count = image_count
                    if assigned_account_id is not None:
                        material.account_id = assigned_account_id
                        logger.info(f"更新素材账号分配: {folder_name} -> 账号ID: {assigned_account_id}")
                    updated_count += 1
                    logger.info(f"更新素材: {folder_name}")
                else:
                    # 创建新素材记录
                    new_material = XiaohongshuMaterial(
                        title=folder_name,
                        folder_path=folder_path,
                        image_count=image_count,
                        status="unpublished",
                        account_id=assigned_account_id,
                        created_at=datetime.now()
                    )
                    db.add(new_material)
                    added_count += 1
                    if assigned_account_id is not None:
                        logger.info(f"添加新素材: {folder_name}, 自动分配账号ID: {assigned_account_id}")
                    else:
                        logger.info(f"添加新素材: {folder_name}")
                
            except Exception as e:
                logger.error(f"处理文件夹 {folder_path} 时出错: {str(e)}")
                error_count += 1
                continue
        
        # 更新文件夹总数和扫描时间
        total_folders = len([d for d in os.listdir(settings.materials_path) 
                           if os.path.isdir(os.path.join(settings.materials_path, d))])
        settings.total_folders = total_folders
        settings.last_scan = datetime.now()
        
        db.commit()
        
        logger.info(f"扫描完成 - 新增: {added_count}, 更新: {updated_count}, 错误: {error_count}, 总计: {total_folders}")
        
        return {
            "success": True, 
            "message": f"扫描完成：新增 {added_count} 个素材，更新 {updated_count} 个素材",
            "total_files": total_folders,
            "new_count": added_count,  # 添加这个字段以匹配前端显示
            "updated_count": updated_count,
            "stats": {
                "added": added_count,
                "updated": updated_count,
                "errors": error_count,
                "total_folders": total_folders
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"扫描素材文件夹时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"扫描失败: {str(e)}")

@router.post("/select-folder")
async def select_folder():
    """选择文件夹对话框"""
    try:
        if platform.system() == "Darwin":  # macOS
            # 使用AppleScript的文件夹选择对话框
            applescript = '''
            tell application "System Events"
                activate
                set folderPath to choose folder with prompt "选择小红书素材库文件夹"
                return POSIX path of folderPath
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", applescript],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                folder_path = result.stdout.strip().rstrip('/')
                return {"success": True, "path": folder_path}
        
        elif platform.system() == "Windows":
            # 使用PowerShell的文件夹选择对话框
            ps_script = '''
            Add-Type -AssemblyName System.Windows.Forms
            $folderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
            $folderBrowser.Description = "选择小红书素材库文件夹"
            $folderBrowser.RootFolder = [System.Environment+SpecialFolder]::Desktop
            $folderBrowser.ShowNewFolderButton = $true
            if ($folderBrowser.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
                $folderBrowser.SelectedPath
            }
            '''
            
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                folder_path = result.stdout.strip().replace('\\', '/')
                return {"success": True, "path": folder_path}
        
        else:
            # Linux 或其他系统，使用 tkinter
            try:
                import tkinter as tk
                from tkinter import filedialog
                
                root = tk.Tk()
                root.withdraw()  # 隐藏主窗口
                folder_path = filedialog.askdirectory(title="选择小红书素材库文件夹")
                root.destroy()
                
                if folder_path:
                    return {"success": True, "path": folder_path}
            except ImportError:
                return {"success": False, "message": "当前系统不支持图形化文件夹选择"}
        
        return {"success": False, "message": "未选择文件夹"}
            
    except Exception as e:
        print(f"Error in select_folder: {str(e)}")  # 添加日志输出
        return {"success": False, "message": f"选择文件夹时出错: {str(e)}"}

# API路径别名 - 让前端调用的路径指向现有实现
@router.post("/save-path")
async def save_path_alias(request_data: dict, db: Session = Depends(get_db)):
    """保存路径 - 别名端点，指向 /config"""
    materials_path = request_data.get("materials_path", "")
    
    # 调用现有的config更新逻辑
    config = XiaohongshuSettingsUpdate(
        materials_path=materials_path,
        region_account_mapping={}
    )
    
    # 获取现有的地区映射关系
    settings = db.query(XiaohongshuSettings).first()
    if settings and settings.region_account_mapping:
        try:
            existing_mapping = json.loads(settings.region_account_mapping)
            config.region_account_mapping = existing_mapping
        except:
            pass
    
    return await update_xiaohongshu_config(config, db)

@router.post("/region-account-mapping")
async def save_region_mapping_alias(request_data: dict, db: Session = Depends(get_db)):
    """保存地区账号映射 - 别名端点，指向 /config"""
    region_account_mapping = request_data.get("region_account_mapping", {})
    
    # 调用现有的config更新逻辑
    config = XiaohongshuSettingsUpdate(
        materials_path="",  # 保持现有路径
        region_account_mapping=region_account_mapping
    )
    
    # 获取现有的路径设置
    settings = db.query(XiaohongshuSettings).first()
    if settings and settings.materials_path:
        config.materials_path = settings.materials_path
    
    # 保存配置
    result = await update_xiaohongshu_config(config, db)
    
    # 立即重新分配所有素材的账号
    try:
        logger.info("开始根据新的地区映射规则重新分配素材账号")
        
        # 获取所有素材
        all_materials = db.query(XiaohongshuMaterial).all()
        updated_count = 0
        
        for material in all_materials:
            # 先重置 account_id
            old_account_id = material.account_id
            material.account_id = None
            
            # 根据新的地区映射分配账号
            for regions, account_id in region_account_mapping.items():
                try:
                    import re
                    keywords = [k.strip() for k in re.split(r"[,，]", str(regions)) if k.strip()]
                except Exception:
                    keywords = [str(regions)]
                if any(k and k in material.title for k in keywords):
                    material.account_id = account_id
                    updated_count += 1
                    logger.info(f"素材 '{material.title}' 匹配地区关键词 '{keywords}', 分配账号ID: {account_id}")
                    break
            
            # 如果没有匹配的规则，记录日志
            if material.account_id is None and old_account_id is not None:
                logger.info(f"素材 '{material.title}' 不匹配任何地区规则, 清除账号分配")
        
        db.commit()
        logger.info(f"重新分配完成，共更新 {updated_count} 个素材的账号分配")
        
        # 更新返回消息
        result["message"] = f"地区映射规则已保存并立即生效，共重新分配 {updated_count} 个素材"
        
    except Exception as e:
        logger.error(f"重新分配素材账号时出错: {str(e)}")
        db.rollback()
        return {"success": False, "message": f"保存成功但重新分配失败: {str(e)}"}
    
    return result

@router.post("/scan-materials")
async def scan_materials_alias(db: Session = Depends(get_db)):
    """扫描素材 - 别名端点，指向 /scan"""
    return await scan_materials_folder(db)
