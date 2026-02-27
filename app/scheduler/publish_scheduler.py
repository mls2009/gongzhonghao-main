from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.database import Material, Account, Settings, get_db, XiaohongshuSettings, XiaohongshuMaterial, TemplateState
import logging
from routers.materials import publish_to_wechat_direct, publish_to_toutiao
import asyncio
import os
import re
import random
from typing import Optional
import traceback

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def run_async(coro):
    """Helper function to run async code in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def sync_check_scheduled_materials():
    """同步包装器，用于调度器调用"""
    logger.info("开始检查预约发布任务...")
    try:
        run_async(check_scheduled_materials())
    except Exception as e:
        logger.error(f"执行预约发布检查时出错: {str(e)}")
        logger.error(traceback.format_exc())

async def check_scheduled_materials():
    """检查并处理预约发布的素材"""
    try:
        db = next(get_db())
        current_time = datetime.now()
        
        # 查找所有预约时间早于当前时间的素材
        scheduled_materials = db.query(Material).filter(
            Material.status == "scheduled",
            Material.schedule_status == "scheduled",
            Material.schedule_time <= current_time
        ).all()
        
        if scheduled_materials:
            logger.info(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}, 找到 {len(scheduled_materials)} 个需要发布的预约素材")
            
            for material in scheduled_materials:
                try:
                    logger.info(f"开始处理预约素材: {material.title} (ID: {material.id}), 预约时间: {material.schedule_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # 更新状态为处理中
                    material.schedule_status = "processing"
                    db.commit()
                    
                    # 获取账号信息
                    account = db.query(Account).get(material.account_id)
                    if not account:
                        raise Exception("找不到关联的账号")
                    
                    # 获取文件路径
                    settings = db.query(Settings).first()
                    if not settings or not settings.materials_path:
                        raise Exception("未设置素材库路径")
                    
                    file_path = os.path.join(settings.materials_path, f"{material.original_title}.docx")
                    if not os.path.exists(file_path):
                        # 在子目录中查找
                        found = False
                        for root, dirs, files in os.walk(settings.materials_path):
                            if f"{material.original_title}.docx" in files:
                                file_path = os.path.join(root, f"{material.original_title}.docx")
                                found = True
                                break
                        if not found:
                            raise Exception(f"找不到文件: {material.original_title}.docx")
                    
                    # 根据账号类型执行不同的发布流程
                    success = False
                    if account.account_type == "头条号":
                        success = await publish_to_toutiao(
                            browser_id=account.browser_id,
                            content_file=file_path,
                            author=account.author_name,
                            title=material.title
                        )
                    else:
                        success = await publish_to_wechat_direct(
                            browser_id=account.browser_id,
                            content_file=file_path,
                            author=account.author_name
                        )
                    
                    # 更新发布结果
                    material.status = "published"
                    material.publish_status = "success" if success else "failed"
                    material.publish_time = datetime.now()
                    material.schedule_status = None
                    material.schedule_time = None
                    
                    if not success:
                        material.error_message = "发布失败，请查看日志获取详细信息"
                    
                    db.commit()
                    logger.info(f"预约素材处理完成: {material.title} (ID: {material.id}) - {'成功' if success else '失败'}")
                    
                except Exception as e:
                    logger.error(f"处理预约素材时出错: {str(e)}")
                    logger.error(traceback.format_exc())
                    try:
                        material.status = "published"
                        material.publish_status = "failed"
                        material.publish_time = datetime.now()
                        material.schedule_status = None
                        material.schedule_time = None
                        material.error_message = str(e)
                        db.commit()
                    except:
                        logger.error("更新素材状态失败")
        
        # 检查完成后更新检查间隔
        update_check_interval()
        
    except Exception as e:
        logger.error(f"检查预约发布任务时出错: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        db.close()

def start_scheduler():
    """启动定时任务"""
    if not scheduler.running:
        scheduler.start()
        update_check_interval()
        logger.info("调度器已启动")

def stop_scheduler():
    """停止定时任务"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("调度器已停止")

def update_check_interval():
    """更新检查间隔"""
    if not scheduler.running:
        return

    db = next(get_db())
    try:
        scheduled_count = db.query(Material).filter(
            Material.status == "scheduled",
            Material.schedule_status == "scheduled"
        ).count()
        
        # 移除现有的检查任务
        try:
            scheduler.remove_job('check_scheduled_materials')
        except:
            pass
        
        # 根据是否有预约任务设置检查间隔
        if scheduled_count > 0:
            scheduler.add_job(
                sync_check_scheduled_materials,
                CronTrigger(minute='*'),  # 每分钟检查
                id='check_scheduled_materials',
                replace_existing=True
            )
            logger.info(f"设置为每分钟检查模式，发现 {scheduled_count} 个预约任务")
        else:
            scheduler.add_job(
                sync_check_scheduled_materials,
                CronTrigger(minute='*/30'),  # 每30分钟检查
                id='check_scheduled_materials',
                replace_existing=True
            )
            logger.info("设置为每30分钟检查模式")
    except Exception as e:
        logger.error(f"更新检查间隔时出错: {str(e)}")
    finally:
        db.close()

def init_scheduler():
    """初始化定时任务"""
    if not scheduler.running:
        start_scheduler()
        # 初始化小红书自动发布任务
        try:
            update_xhs_auto_job()
        except Exception as e:
            logger.error(f"初始化小红书自动发布任务失败: {e}")

# ===================== 小红书自动发布（获取邮箱素材） =====================

def sync_xhs_auto_fetch():
    """同步包装器：执行小红书邮箱素材获取与数据库更新"""
    logger.info("[XHS-AUTO] 开始执行自动获取邮箱素材任务")
    db = next(get_db())
    try:
        settings = db.query(XiaohongshuSettings).first()
        if not settings or not settings.materials_path:
            logger.warning("[XHS-AUTO] 未配置小红书素材库路径，跳过")
            return

        # 读取地区映射
        region_mapping = {}
        if settings.region_account_mapping:
            try:
                import json
                region_mapping = json.loads(settings.region_account_mapping)
            except Exception:
                logger.warning("[XHS-AUTO] 地区映射解析失败，忽略")

        # 获取邮箱素材
        try:
            from utils.email_handler import fetch_qq_email_materials
            result = fetch_qq_email_materials(settings.materials_path)
            logger.info(f"[XHS-AUTO] 邮箱素材获取结果: {result}")
        except Exception as e:
            logger.error(f"[XHS-AUTO] 获取邮箱素材异常: {e}")
            result = {"success": False, "processed_count": 0, "messages": [str(e)]}

        # 无论成败，扫描素材库更新数据库（与接口逻辑一致，避免重复代码）
        try:
            total_folders = 0
            added_count = 0
            updated_count = 0
            skipped_count = 0
            
            # 计算30天截止时间（只处理最近一个月内的素材）
            cutoff_date = datetime.now() - timedelta(days=30)
            
            if os.path.exists(settings.materials_path):
                for item in os.listdir(settings.materials_path):
                    folder_path = os.path.join(settings.materials_path, item)
                    if not os.path.isdir(folder_path):
                        continue
                    total_folders += 1
                    
                    # 跳过超过30天未修改的文件夹
                    try:
                        folder_mtime = datetime.fromtimestamp(os.path.getmtime(folder_path))
                        if folder_mtime < cutoff_date:
                            logger.debug(f"[XHS-AUTO] 跳过30天前的文件夹: {item} (修改时间: {folder_mtime.strftime('%Y-%m-%d')})")
                            skipped_count += 1
                            continue
                    except Exception:
                        pass  # 无法获取修改时间时，照常处理

                    # 统计图片
                    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
                    image_count = 0
                    try:
                        for f in os.listdir(folder_path):
                            if os.path.splitext(f.lower())[1] in image_extensions:
                                image_count += 1
                    except Exception:
                        pass

                    folder_name = item

                    # 自动分配账号（根据地区规则，支持多关键词，以逗号或中文逗号分隔）
                    assigned_account_id = None
                    for regions, account_id in region_mapping.items():
                        try:
                            keywords = [k.strip() for k in re.split(r"[,，]", str(regions)) if k.strip()]
                        except Exception:
                            keywords = [str(regions)]
                        if any(k in folder_name for k in keywords):
                            assigned_account_id = account_id
                            break

                    existing = db.query(XiaohongshuMaterial).filter(XiaohongshuMaterial.title == folder_name).first()
                    if existing:
                        existing.folder_path = folder_path
                        existing.image_count = image_count
                        if assigned_account_id is not None:
                            existing.account_id = assigned_account_id
                        updated_count += 1
                    else:
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

            settings.total_folders = total_folders
            settings.last_scan = datetime.now()
            db.commit()
            logger.info(f"[XHS-AUTO] 扫描完成：新增 {added_count}，更新 {updated_count}，跳过(>30天) {skipped_count}，总数 {total_folders}")
            # 推送SSE事件
            try:
                from utils.event_bus import publish as sse_publish
                sse_publish({
                    "type": "xhs_auto_fetch",
                    "added": added_count,
                    "updated": updated_count,
                    "total": total_folders,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"[XHS-AUTO] 推送事件失败: {e}")
        except Exception as e:
            logger.error(f"[XHS-AUTO] 扫描与数据库更新异常: {e}")
            db.rollback()

        # 扫描完成后基于设置计划自动发布
        try:
            plan_xhs_auto_publish()
        except Exception as e:
            logger.error(f"[XHS-AUTO] 计划自动发布失败: {e}")

    except Exception as e:
        logger.error(f"[XHS-AUTO] 任务异常: {e}")
    finally:
        db.close()

def update_xhs_auto_job():
    """根据设置更新小红书自动任务（每天指定时间）"""
    # 先移除旧任务
    try:
        scheduler.remove_job('xhs_auto_fetch')
    except Exception:
        pass

    db = next(get_db())
    try:
        settings = db.query(XiaohongshuSettings).first()
        if not settings or not getattr(settings, 'auto_publish_enabled', False):
            logger.info("[XHS-AUTO] 自动发布未开启，不创建任务")
            return
        time_str = settings.auto_publish_time or '09:00'
        try:
            hour, minute = [int(x) for x in time_str.split(':')]
        except Exception:
            hour, minute = 9, 0

        scheduler.add_job(
            sync_xhs_auto_fetch,
            CronTrigger(hour=hour, minute=minute),
            id='xhs_auto_fetch',
            replace_existing=True
        )
        logger.info(f"[XHS-AUTO] 已设置每天 {hour:02d}:{minute:02d} 自动获取邮箱素材")
    except Exception as e:
        logger.error(f"[XHS-AUTO] 更新任务失败: {e}")
    finally:
        db.close()

# ===================== 小红书自动发布（筛选&调度） =====================

def _parse_date_from_title(title: str) -> Optional[datetime]:
    try:
        m = re.search(r"(\d{1,2})月(\d{1,2})日", title)
        if not m:
            return None
        y = datetime.now().year
        return datetime(y, int(m.group(1)), int(m.group(2)))
    except Exception:
        return None

def _random_time_in_window(base_date: datetime, start_hm: str, end_hm: str) -> datetime:
    sh, sm = [int(x) for x in start_hm.split(":")]
    eh, em = [int(x) for x in end_hm.split(":")]
    start = base_date.replace(hour=sh, minute=sm, second=0, microsecond=0)
    end = base_date.replace(hour=eh, minute=em, second=0, microsecond=0)
    if end <= start:
        end = start + timedelta(minutes=1)
    seconds = int((end - start).total_seconds())
    rnd = random.randint(0, max(0, seconds-1))
    return start + timedelta(seconds=rnd)

def plan_xhs_auto_publish():
    db = next(get_db())
    try:
        settings = db.query(XiaohongshuSettings).first()
        if not settings:
            return
        days = getattr(settings, 'publish_days_window', 4) or 4  # 默认取4天内的素材，覆盖周末
        add_product = getattr(settings, 'add_product_enabled', False) or False
        default_mode = getattr(settings, 'default_mode', 'random') or 'random'
        # 收集已配置的时间段
        windows = []
        for i in [1,2,3]:
            s = getattr(settings, f'window{i}_start', None)
            e = getattr(settings, f'window{i}_end', None)
            if s and e:
                windows.append((s,e))
        if not windows:
            logger.info("[XHS-AUTO] 无有效时间段，跳过计划")
            return

        today = datetime.now()
        
        # 根据星期决定使用几个时间窗口：周一和周日发3条（消化周末积累），其他工作日发2条
        weekday = today.weekday()  # 0=周一, 6=周日
        if weekday in [0, 6]:  # 周一或周日
            max_per_account = min(3, len(windows))
            day_name = "周一" if weekday == 0 else "周日"
            logger.info(f"[XHS-AUTO] 今天是{day_name}，每账号最多安排3条素材")
        else:
            max_per_account = min(2, len(windows))
            logger.info(f"[XHS-AUTO] 今天是周{weekday+1}，每账号最多安排2条素材")
        
        # 候选素材：未发布 + 有账号 + 未预约 + 日期在范围内
        candidates = []
        for m in db.query(XiaohongshuMaterial).filter(XiaohongshuMaterial.status=='unpublished').all():
            if not m.account_id or m.schedule_time is not None:
                continue
            dt = _parse_date_from_title(m.title or '')
            if not dt:
                continue
            delta = (today.date() - dt.date()).days
            if 0 <= delta <= days:
                candidates.append((dt, m))
        # 日期更早优先
        candidates.sort(key=lambda x: x[0])

        # 每账号最多取 max_per_account 个
        per_acc = {}
        for dt, m in candidates:
            per_acc.setdefault(m.account_id, []).append((dt, m))

        scheduled = []
        for acc_id, items in per_acc.items():
            pick = items[:max_per_account]
            for idx, (dt, m) in enumerate(pick):
                if idx >= len(windows):
                    break
                w = windows[idx]
                run = _random_time_in_window(today, w[0], w[1])
                if run <= today:
                    run = _random_time_in_window(today + timedelta(days=1), w[0], w[1])
                scheduled.append((m, run))

        # 创建date任务并标记数据库
        for m, run_at in scheduled:
            job_id = f"xhs_pub_{m.id}"
            try:
                try:
                    scheduler.remove_job(job_id)
                except Exception:
                    pass

                def _job(material_id=m.id):
                    run_async(_run_xhs_publish(material_id))

                scheduler.add_job(_job, 'date', run_date=run_at, id=job_id, replace_existing=True)
                m.schedule_time = run_at
                m.schedule_status = 'scheduled'
                db.commit()
                logger.info(f"[XHS-AUTO] 已预约素材 {m.id} 于 {run_at}")
            except Exception as e:
                logger.error(f"[XHS-AUTO] 创建任务失败: {e}")

    finally:
        db.close()

async def _run_xhs_publish(material_id: int, add_product: bool = False, default_mode: str = 'random'):
    db = next(get_db())
    try:
        m = db.query(XiaohongshuMaterial).get(material_id)
        if not m:
            return
        acc = db.query(Account).get(m.account_id)
        if not acc:
            return
        # 每次执行前从设置读取最新的添加商品开关
        try:
            s = db.query(XiaohongshuSettings).first()
            if s:
                # 直接读取属性，如果是 None 则视为 False
                db_setting = s.add_product_enabled
                add_product = bool(db_setting) if db_setting is not None else False
                logger.info(f"[XHS-AUTO] 实时读取添加商品设置: {add_product} (DB值: {db_setting})")
            else:
                logger.warning("[XHS-AUTO] 未找到设置记录，使用计划时的默认值")
        except Exception as e:
            logger.error(f"[XHS-AUTO] 读取设置失败: {e}")
            # 出错时保留原值，但记录错误

        logger.info(f"[XHS-AUTO] 本次发布最终 add_product={add_product} material_id={material_id}")
        # 模板状态
        tstate = db.query(TemplateState).first()
        # 内容模板
        content = ''
        topics = []
        try:
            from routers.xiaohongshu_materials import apply_content_template_to_material
            res = await apply_content_template_to_material(m, tstate, db)
            if res.get('success'):
                content = res.get('content', '')
                topics = res.get('topics', [])
        except Exception as e:
            logger.error(f"[XHS-AUTO] 内容模板异常: {e}")
        # 图片模板（后端以无头浏览器渲染 Canvas，生成覆盖/插入图片）
        try:
            from routers.xiaohongshu_materials import apply_image_template_to_material
            img_res = await apply_image_template_to_material(m, tstate, db)
            if img_res.get('success'):
                cfg = img_res.get('template_config') or {}
                mode = img_res.get('mode') or 'insert'
                lines = img_res.get('text_lines') or []
                # 确保覆盖模式背景为 data URL
                if mode == 'overlay':
                    bg = cfg.get('custom_background_path')
                    if bg and not str(bg).startswith('data:') and os.path.exists(str(bg)):
                        with open(str(bg), 'rb') as f:
                            import base64
                            b64 = base64.b64encode(f.read()).decode('utf-8')
                        ext = os.path.splitext(str(bg))[-1].lower()
                        mime = 'image/png' if ext == '.png' else 'image/jpeg'
                        cfg['custom_background_path'] = f"data:{mime};base64,{b64}"

                from utils.canvas_headless import render_image_dataurl, save_dataurl_to_file
                data_url = await render_image_dataurl(cfg, lines, mode)
                if not isinstance(data_url, str) or not data_url.startswith('data:image'):
                    raise Exception('Headless canvas render failed: invalid data URL')
                # 保存
                if mode == 'overlay':
                    # 修改为非破坏式：复制第一张为背景，生成覆盖图片作为新的第一张
                    folder = m.folder_path
                    out = os.path.join(folder, '00_template_generated.png')
                    save_dataurl_to_file(data_url, out)
                    try:
                        sz = os.path.getsize(out)
                        logger.info(f"[XHS-AUTO] 覆盖图片已保存为新首图: {out} size={sz}")
                        if sz <= 0:
                            raise Exception('saved overlay image size=0')
                    except Exception as e:
                        raise Exception(f'overlay save verify failed: {e}')
                else:
                    folder = img_res.get('target_path') or m.folder_path
                    out = os.path.join(folder, '00_template_generated.png')
                    save_dataurl_to_file(data_url, out)
                    try:
                        sz = os.path.getsize(out)
                        logger.info(f"[XHS-AUTO] 插入图片已保存: {out} size={sz}")
                        if sz <= 0:
                            raise Exception('saved insert image size=0')
                    except Exception as e:
                        raise Exception(f'insert save verify failed: {e}')
            else:
                logger.warning(f"[XHS-AUTO] 图片模板未应用: {img_res.get('message')}")
        except Exception as e:
            logger.error(f"[XHS-AUTO] 图片模板异常: {e}")

        # 发布
        try:
            from utils.xiaohongshu_publisher import publish_xiaohongshu_material
            result = await publish_xiaohongshu_material(
                material_id=m.id,
                material_title=m.title,
                folder_path=m.folder_path,
                account_id=m.account_id,
                browser_id=acc.browser_id,
                content=content,
                topics=topics,
                add_product=add_product
            )
            if result.get('success'):
                m.status = 'published'
                m.publish_status = 'success'
                m.publish_time = datetime.now()
                m.error_message = None
            else:
                m.publish_status = 'failed'
                m.error_message = result.get('message')
        except Exception as e:
            m.publish_status = 'failed'
            m.error_message = str(e)
        finally:
            m.schedule_time = None
            m.schedule_status = None
            db.commit()
            # 推送发布完成事件（SSE）
            try:
                from utils.event_bus import publish as sse_publish
                sse_publish({
                    "type": "xhs_publish_done",
                    "material_id": m.id,
                    "title": m.title,
                    "success": m.publish_status == 'success',
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as _:
                pass
    finally:
        db.close()
