from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from models.database import get_db, Material, Account, Settings
from playwright.sync_api import sync_playwright
from multiprocessing import Process, Queue
import multiprocessing
import asyncio
import logging
import os
import requests
import json
import time
import traceback
import tempfile
import docx
from pydantic import BaseModel, validator

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# BitBrowser API 配置
BITBROWSER_API = "http://127.0.0.1:54345"

router = APIRouter(prefix="/api/materials", tags=["materials"])

class BatchPublishRequest(BaseModel):
    material_ids: List[int]
    toutiao_first: bool = False
    schedule_publish: bool = False
    schedule_time: Optional[datetime] = None

    @validator('schedule_time', pre=True)
    def parse_datetime(cls, value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            # 前端发送的是ISO格式的UTC时间，需要转换为本地时间
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            local_dt = dt + timedelta(hours=8)  # 转换为东八区时间
            logger.info(f"收到UTC时间: {dt}, 转换为本地时间: {local_dt}")
            return local_dt
        except (TypeError, ValueError) as e:
            logger.error(f"日期时间解析错误: {str(e)}, 值: {value}")
            raise ValueError(f"无效的日期时间格式: {value}")

class StatusUpdate(BaseModel):
    status: str

class TitleUpdate(BaseModel):
    title: str

class DirectPublishRequest(BaseModel):
    toutiao_first: bool = False
    schedule_publish: bool = False
    schedule_time: Optional[datetime] = None

    @validator('schedule_time', pre=True)
    def parse_datetime(cls, value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            # 前端发送的是ISO格式的UTC时间，需要转换为本地时间
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            local_dt = dt + timedelta(hours=8)  # 转换为东八区时间
            logger.info(f"收到UTC时间: {dt}, 转换为本地时间: {local_dt}")
            return local_dt
        except (TypeError, ValueError) as e:
            logger.error(f"日期时间解析错误: {str(e)}, 值: {value}")
            raise ValueError(f"无效的日期时间格式: {value}")

class ScheduleTimeUpdate(BaseModel):
    schedule_time: datetime

    @validator('schedule_time', pre=True)
    def parse_datetime(cls, value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            # 前端发送的是ISO格式的UTC时间，需要转换为本地时间
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            local_dt = dt + timedelta(hours=8)  # 转换为东八区时间
            logger.info(f"收到UTC时间: {dt}, 转换为本地时间: {local_dt}")
            return local_dt
        except (TypeError, ValueError) as e:
            logger.error(f"日期时间解析错误: {str(e)}, 值: {value}")
            raise ValueError(f"无效的日期时间格式: {value}")

def open_bitbrowser(browser_id: str) -> tuple[bool, str]:
    """打开 BitBrowser 并获取 WebSocket 地址"""
    try:
        url = f"http://127.0.0.1:54345/browser/open"
        data = {"id": browser_id}
        headers = {"Content-Type": "application/json"}
        
        logger.info(f"正在打开浏览器: {browser_id}")
        logger.info(f"请求URL: {url}")
        logger.info(f"请求数据: {data}")
        
        response = requests.post(url, json=data, headers=headers)
        
        logger.info(f"API响应状态码: {response.status_code}")
        logger.info(f"API响应内容: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                logger.info(f"解析后的响应: {result}")
                
                if result.get("success") is True:
                    ws_url = result.get("data", {}).get("ws")
                    if ws_url:
                        logger.info(f"浏览器启动成功，WebSocket地址: {ws_url}")
                        time.sleep(3)
                        return True, ws_url
                    else:
                        logger.error("响应中没有找到 WebSocket 地址")
                        return False, ""
                else:
                    error_msg = result.get("msg") or result.get("message") or "未知错误"
                    logger.error(f"打开浏览器失败: {error_msg}")
                    return False, ""
            except ValueError as e:
                logger.error(f"解析响应JSON失败: {str(e)}")
                return False, ""
        else:
            logger.error(f"打开浏览器失败: {response.status_code} - {response.text}")
            return False, ""
            
    except Exception as e:
        logger.error(f"打开浏览器出错: {str(e)}")
        logger.error(traceback.format_exc())
        return False, ""

def _run_playwright_in_process(browser_id: str, content_file: str, author: str, result_queue: Queue):
    """在单独的进程中运行 Playwright"""
    try:
        # 打开浏览器并获取 WebSocket 地址
        success, ws_url = open_bitbrowser(browser_id)
        if not success:
            result_queue.put((False, "无法打开浏览器"))
            return

        logger.info(f"正在连接到浏览器 WebSocket: {ws_url}")

        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.connect_over_cdp(ws_url)
                context = browser.contexts[0]
                page = context.new_page()
                
                # 访问微信公众平台
                logger.info("正在访问微信公众平台...")
                page.goto("https://mp.weixin.qq.com", wait_until="networkidle")
                
                # 点击内容管理
                logger.info("点击内容管理...")
                page.wait_for_selector("//span[contains(text(), '内容管理')]", state="visible")
                page.click("//span[contains(text(), '内容管理')]")
                page.wait_for_load_state("networkidle")
                
                # 点击草稿箱
                logger.info("点击草稿箱...")
                page.wait_for_selector("span.weui-desktop-menu__name:has-text('草稿箱')", state="visible")
                page.click("span.weui-desktop-menu__name:has-text('草稿箱')")
                page.wait_for_load_state("networkidle")
                
                # 点击新建图文
                logger.info("点击新的创作...")
                try:
                    page.wait_for_selector("div.weui-desktop-card__inner:has-text('新的创作')", state="visible")
                    page.click("div.weui-desktop-card__inner:has-text('新的创作')")
                except:
                    logger.info("尝试使用备选元素点击...")
                    page.wait_for_selector('div.weui-desktop-card__inner[style="height: 234px;"][data-label-id="0"]', state="visible")
                    page.click('div.weui-desktop-card__inner[style="height: 234px;"][data-label-id="0"]')
                
                # 等待新页面打开
                logger.info("点击写新文章...")
                try:
                    with context.expect_page() as new_page_info:
                        page.click("a:has-text('写新文章')")
                    new_page = new_page_info.value
                except:
                    logger.info("尝试使用备选元素点击...")
                    with context.expect_page() as new_page_info:
                        page.click("a:has-text('写新图文')")
                    new_page = new_page_info.value
                
                # 等待新页面加载
                logger.info("等待新页面加载...")
                new_page.wait_for_load_state("networkidle")
                new_page.bring_to_front()
                
                # 上传文件
                logger.info("准备上传文件...")
                new_page.wait_for_selector("#js_import_file", state="visible", timeout=30000)
                new_page.click("#js_import_file")
                
                with new_page.expect_file_chooser() as fc_info:
                    new_page.click("label[style*='opacity: 0']")
                file_chooser = fc_info.value
                file_chooser.set_files(content_file)
                
                time.sleep(3)
                
                # 填写作者
                logger.info("填写作者信息...")
                new_page.fill("#author", author)
                
                # 处理原创声明
                logger.info("处理原创声明...")
                new_page.click("div.js_unset_original_title")
                checkbox = new_page.wait_for_selector("i.weui-desktop-icon-checkbox", state="visible")

                checkbox.check()
                new_page.click("button.weui-desktop-btn_primary:has-text('确定')")
                
                time.sleep(2)
                
                # 处理广告区域
                try:
                    logger.info("检查并处理广告区域...")
                    ad_area = new_page.wait_for_selector('//*[@id="js_insert_ad_area"]/label/span', 
                                                       state="visible", 
                                                       timeout=2000)
                    if ad_area:
                        logger.info("发布广告区域，进行处理...")
                        new_page.click('//*[@id="js_insert_ad_area"]/label/div/span[3]')
                        time.sleep(3)  # 增加等待时间
                        
                        frame = new_page.wait_for_selector('iframe', state="visible", timeout=2000)
                        if frame:
                            frame_element = frame.content_frame()
                            if frame_element:
                                # 直接使用 JavaScript 方案
                                frame_element.evaluate('''() => {
                                    const buttons = Array.from(document.querySelectorAll('button'));
                                    const confirmBtn = buttons.find(btn => {
                                        const span = btn.querySelector('span.adui-button-content');
                                        return span && span.textContent === '确认';
                                    });
                                    if (confirmBtn) confirmBtn.click();
                                }''')
                                time.sleep(2)  # 增加确认按钮点击后的等待时间
                except Exception as e:
                    logger.error(f"广告区域处理过程中出错: {str(e)}")
                    logger.info("继续执行后续步骤...")
                
                # 选择封面图
                logger.info("处理封面图...")
                try:
                    new_page.evaluate('''() => {
                        const links = Array.from(document.querySelectorAll('a'));
                        const link = links.find(a => a.textContent.includes('从正文选择'));
                        if (link) link.click();
                    }''')
                    
                    time.sleep(1)
                    
                    new_page.evaluate('''() => {
                        const images = document.querySelectorAll('.card_mask_global');
                        if (images.length > 0) {
                            images[0].click();
                        }
                    }''')
                    
                    next_button = new_page.wait_for_selector("button.weui-desktop-btn_primary:has-text('下一步')", 
                                                           state="visible", 
                                                           timeout=5000)
                    if next_button:
                        next_button.click()
                        
                        confirm_button = new_page.wait_for_selector("button.weui-desktop-btn_primary:has-text('确认')", 
                                                                  state="visible", 
                                                                  timeout=5000)
                        if confirm_button:
                            confirm_button.click()
                            logger.info("第二个发表按钮点击成功")
                            time.sleep(2)  # 等待2秒
                            
                            # 点击"继续发表"按钮
                            logger.info("尝试点击继续发表按钮...")
                            try:
                                continue_button = new_page.wait_for_selector(
                                    "div.weui-desktop-btn_wrp button.weui-desktop-btn.weui-desktop-btn_primary:has-text('继续发表')",
                                    state="visible",
                                    timeout=5000
                                )
                                if continue_button:
                                    # 获取按钮的位置信息
                                    box = continue_button.bounding_box()
                                    if box:
                                        # 移动鼠标到按钮中心
                                        new_page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                                        time.sleep(0.5)  # 短暂等待
                                        # 模拟鼠标点击
                                        new_page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                                        logger.info("继续发表按钮点击成功")
                                        # 等待15秒确保发布完成
                                        logger.info("等待15秒确保发布完成...")
                                        time.sleep(15)
                                        logger.info("等待完成，准备关闭页面...")
                                    else:
                                        logger.info("继续发表按钮不可见，跳过点击")
                            except Exception as e:
                                logger.info(f"继续发按钮不存在或无法点击，继续执行: {str(e)}")
                            
                            time.sleep(2)  # 等待完成
                            
                            # 注释掉关闭浏览器的代码，让浏览器保持打开
                            # 关闭所有页面
                            # logger.info("关闭所有页面...")
                            # for page in context.pages:
                            #     page.close()
                            
                            # 关闭浏览器
                            # logger.info("关闭浏览器...")
                            # browser.close()
                            
                            # 关闭 BitBrowser
                            # url = f"http://127.0.0.1:54345/browser/close"
                            # data = {"id": browser_id}
                            # headers = {"Content-Type": "application/json"}
                            # response = requests.post(url, json=data, headers=headers)
                            # if response.status_code == 200:
                            #     logger.info("BitBrowser 已关闭")
                            # else:
                            #     logger.error(f"关闭 BitBrowser 失败: {response.status_code} - {response.text}")
                            
                            logger.info("发布成功，浏览器保持打开状态")
                            result_queue.put((True, "发布成功，浏览器保持打开状态"))
                        else:
                            raise Exception("找不到第二个发表按钮")
                    else:
                        raise Exception("找不到第一个发表按钮")
                except Exception as e:
                    logger.error(f"发布过程中出错: {str(e)}")
                    result_queue.put((False, str(e)))
                
            except Exception as e:
                logger.error(f"发布过程中出错: {str(e)}")
                logger.error(traceback.format_exc())
                try:
                    if 'new_page' in locals():
                        new_page.screenshot(path="error.png")
                        elements = new_page.evaluate('''() => {
                            return {
                                images: Array.from(document.querySelectorAll('*[class*="mask"]')).map(el => ({
                                    class: el.className,
                                    visible: el.offsetParent !== null,
                                    rect: el.getBoundingClientRect()
                                })),
                                buttons: Array.from(document.querySelectorAll('button')).map(el => ({
                                    text: el.textContent.trim(),
                                    visible: el.offsetParent !== null,
                                    disabled: el.disabled
                                }))
                            };
                        }''')
                        logger.error(f"页面元素状态: {elements}")
                except:
                    if 'page' in locals():
                        page.screenshot(path="error.png")
                result_queue.put((False, str(e)))
            finally:
                # 注释掉自动关闭浏览器的代码，让浏览器保持打开状态
                # if 'new_page' in locals() and new_page:
                #     new_page.close()
                # if 'browser' in locals() and browser:
                #     browser.close()
                
                # 清理工作已完成，结果已在前面的try-except中放入队列
                pass
                    
    except Exception as e:
        logger.error(f"发布失败: {str(e)}")
        logger.error(traceback.format_exc())
        result_queue.put((False, str(e)))

def _run_toutiao_playwright_in_process(browser_id: str, content_file: str, author: str, result_queue: Queue, title: str, is_first_publish: bool = False):
    """在单独进程中运行头条号的 Playwright 发布操作"""
    browser = None
    try:
        # 打开浏览器并获取 WebSocket 地址
        success, ws_url = open_bitbrowser(browser_id)
        if not success:
            result_queue.put((False, "无法打开浏览器"))
            return

        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.connect_over_cdp(ws_url)
                context = browser.contexts[0]
                page = context.new_page()

                # 访问头条号
                page.goto("https://mp.toutiao.com/profile_v4/index")
                logger.info("等待页面加载完成...")
                
                # 等待发文按钮出现，确保已登录
                page.wait_for_selector('a[href="/profile_v4/graphic/publish"]')
                
                # 直接访问发文页面
                page.goto("https://mp.toutiao.com/profile_v4/graphic/publish")
                page.wait_for_load_state('networkidle')
                
                # 尝试点击 AI 助手
                try:
                    ai_button = page.locator('path[fill-rule="evenodd"][clip-rule="evenodd"][fill="#999"]')
                    box = ai_button.bounding_box()
                    if box:
                        page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                        time.sleep(0.5)
                        page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                    else:
                        logger.warning("点击ai助手失败")
                except Exception as e:
                    logger.warning(f"点击ai助手失败: {str(e)}")

                # 导入文档
                try:
                    _handle_document_import(page, content_file)
                except Exception as e:
                    logger.error(f"导入文档失败: {str(e)}")
                    raise

                # 输入标题
                try:
                    title_element = page.locator('textarea[placeholder="请输入文章标题（2～30个字）"]')
                    title_element.fill(title)
                except Exception as e:
                    logger.error(f"输入标题失败: {str(e)}")
                    raise

                # 处理首发选项
                try:
                    _handle_first_publish_option(page, is_first_publish)
                except Exception as e:
                    logger.error(f"处理首发选项失败: {str(e)}")
                    logger.error(traceback.format_exc())
                    # 继续执行，不中断流程

                # 设置封面
                try:
                    _handle_cover_settings(page)
                except Exception as e:
                    logger.error(f"设置封面失败: {str(e)}")
                    # 继续执行，不中断流程

                # 处理头条首发复选框
                if not is_first_publish:
                    try:
                        _handle_toutiao_first_checkbox(page, result_queue)
                    except Exception as e:
                        logger.error(f"处理头条首发复选框失败: {str(e)}")
                        logger.error(traceback.format_exc())
                        raise

                # 发布文章
                try:
                    _publish_article(page)
                    result_queue.put((True, "发布成功"))
                except Exception as e:
                    logger.error(f"发布文章失败: {str(e)}")
                    raise

            except Exception as e:
                logger.error(f"头条号发布操作失败: {str(e)}")
                logger.error(traceback.format_exc())
                try:
                    if page:
                        page.screenshot(path="error.png")
                        with open("error.html", "w", encoding="utf-8") as f:
                            f.write(page.content())
                except:
                    pass
                result_queue.put((False, str(e)))
            finally:
                if browser:
                    try:
                        browser.close()
                    except:
                        pass

    except Exception as e:
        logger.error(f"头条号发布进程出错: {str(e)}")
        result_queue.put((False, str(e)))

def get_checkbox_state(page) -> bool:
    """尝试多种方式获取复选框状态"""
    try:
        # 方法1: 通过class检查
        try:
            is_checked = page.evaluate('''() => {
                const label = document.querySelector('label.byte-checkbox.checkbot-item.checkbox-with-tip');
                return label && label.classList.contains('byte-checkbox-checked');
            }''')
            logger.info(f"方法1检查结果: {is_checked}")
        except Exception as e:
            logger.error(f"方法1检查失败: {str(e)}")
            is_checked = False
        
        # 方法2: 通过input的checked属性检查
        try:
            input_checked = page.evaluate('''() => {
                const input = document.querySelector('div.exclusive-checkbox-wraper input[type="checkbox"]');
                return input && input.checked;
            }''')
            logger.info(f"方法2检查结果: {input_checked}")
        except Exception as e:
            logger.error(f"方法2检查失败: {str(e)}")
            input_checked = False
        
        # 方法3: 通过aria-checked属性检查
        try:
            aria_checked = page.evaluate('''() => {
                const label = document.querySelector('label.byte-checkbox.checkbot-item.checkbox-with-tip');
                return label && label.getAttribute('aria-checked') === 'true';
            }''')
            logger.info(f"方法3检查结果: {aria_checked}")
        except Exception as e:
            logger.error(f"方法3检查失败: {str(e)}")
            aria_checked = False
        
        # 返回任一为true的结果
        return is_checked or input_checked or aria_checked
        
    except Exception as e:
        logger.error(f"检查复选框状态时出错: {str(e)}")
        return False

def close_bitbrowser(browser_id: str):
    """关闭 BitBrowser"""
    try:
        url = f"http://127.0.0.1:54345/browser/close"
        data = {"id": browser_id}
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            logger.info(f"成功关闭浏览器: {browser_id}")
        else:
            logger.error(f"关闭浏览器失败: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"关闭浏览器出错: {str(e)}")

def check_process_result(process: Process, result_queue: Queue, timeout: int = 300) -> Tuple[bool, str]:
    """检查进程执行结果"""
    try:
        # 等待进程完成
        process.join(timeout)
        
        # 检查是否超时
        if process.is_alive():
            process.terminate()
            return False, "操作超时"
        
        # 获取结果
        if not result_queue.empty():
            return result_queue.get()
        
        return False, "进程未返回结果"
    except Exception as e:
        return False, str(e)
    finally:
        if process.is_alive():
            process.terminate()

def wait_for_process(process: Process, result_queue: Queue, timeout: int = 300) -> Tuple[bool, str]:
    """等待进程完成并返回结果"""
    try:
        # 等待进程完成
        process.join(timeout)
        
        # 检查是否超时
        if process.is_alive():
            process.terminate()
            return False, "操作超时"
        
        # 获取结果
        if not result_queue.empty():
            return result_queue.get()
        
        return False, "进程未返回结果"
    except Exception as e:
        return False, str(e)
    finally:
        if process.is_alive():
            process.terminate()

async def publish_to_wechat(browser_id: str, content_file: str, author: str) -> bool:
    """启动单独进程执行发布操作"""
    process = None
    try:
        logger.info(f"准备发布文章: 浏览器ID {browser_id}, 作者 {author}")
        result_queue = multiprocessing.Queue()
        process = Process(
            target=_run_playwright_in_process,
            args=(browser_id, content_file, author, result_queue)
        )
        
        logger.info(f"启动发布进程: 浏览器ID {browser_id}")
        process.start()
        
        # 在线程池中等待进程完成
        loop = asyncio.get_event_loop()
        success, message = await loop.run_in_executor(None, wait_for_process, process, result_queue)
        
        if not success:
            logger.error(f"发布失败: 浏览器ID {browser_id}, 错误信息: {message}")
        else:
            logger.info(f"发布成功: 浏览器ID {browser_id}")
        
        return success
    except Exception as e:
        logger.error(f"发布过程出错: 浏览器ID {browser_id}, 错误信息: {str(e)}")
        return False
    finally:
        if process and process.is_alive():
            process.terminate()

async def publish_to_toutiao(browser_id: str, content_file: str, author: str, title: str, is_first_publish: bool = False) -> bool:
    """启动单独进程执行头条号发布操作"""
    process = None
    try:
        logger.info(f"准备发布文章到头条号: 浏览器ID {browser_id}, 作者 {author}, 标题 {title}")
        result_queue = multiprocessing.Queue()
        process = Process(
            target=_run_toutiao_playwright_in_process,
            args=(browser_id, content_file, author, result_queue, title, is_first_publish)
        )
        
        logger.info(f"启动头条号发布进程: 浏览器ID {browser_id}")
        process.start()
        
        # 在线程池中等待进程完成
        loop = asyncio.get_event_loop()
        success, message = await loop.run_in_executor(None, wait_for_process, process, result_queue)
        
        if not success:
            logger.error(f"头条号发布失败: 浏览器ID {browser_id}, 错误信息: {message}")
        else:
            logger.info(f"头条号发布成功: 浏览器ID {browser_id}")
        
        return success
    except Exception as e:
        logger.error(f"头条号发布过程出错: 浏览器ID {browser_id}, 错误信息: {str(e)}")
        return False
    finally:
        if process and process.is_alive():
            process.terminate()

async def publish_to_wechat_direct(browser_id: str, content_file: str, author: str) -> bool:
    """启动单独进程执行直接发布操作"""
    try:
        logger.info(f"准备直接发布文章: 浏览器ID {browser_id}, 作者 {author}")
        result_queue = multiprocessing.Queue()
        process = Process(
            target=_run_playwright_direct_publish,
            args=(browser_id, content_file, author, result_queue)
        )
        
        logger.info(f"启动直接发布进程: 浏览器ID {browser_id}")
        process.start()
        
        # 使用异步循环检查进程状态
        start_time = time.time()
        while time.time() - start_time < 300:  # 5分钟超时
            if not process.is_alive():
                break
            await asyncio.sleep(1)  # 让出控制权给其他任务
        
        # 等待进程完全结束
        process.join(timeout=10)
        
        if process.is_alive():
            logger.error(f"发布操作超时: 浏览器ID {browser_id}")
            process.terminate()
            process.join()
            return False
            
        # 检查结果队列
        try:
            if not result_queue.empty():
                success, message = result_queue.get(timeout=5)
                logger.info(f"发布结果: success={success}, message={message}")
                if not success:
                    logger.error(f"发布失败: 浏览器ID {browser_id}, 错误信息: {message}")
                else:
                    logger.info(f"发布成功: 浏览器ID {browser_id}")
                return success
            else:
                logger.error(f"发布进程未返回结果: 浏览器ID {browser_id}")
                return False
        except Exception as e:
            logger.error(f"获取发布结果时出错: {str(e)}")
            return False
        
    except Exception as e:
        logger.error(f"发布过程出错: 浏览器ID {browser_id}, 错误信息: {str(e)}")
        return False

def _run_playwright_direct_publish(browser_id: str, content_file: str, author: str, result_queue: Queue):
    """在单独进程中执行直接发布操作"""
    try:
        # 打开浏览器并获取 WebSocket 地址
        success, ws_url = open_bitbrowser(browser_id)
        if not success:
            result_queue.put((False, "无法打开浏览器"))
            return

        logger.info(f"正在连接到浏览器 WebSocket: {ws_url}")

        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.connect_over_cdp(ws_url)
                context = browser.contexts[0]
                page = context.new_page()
                
                # 访问微信公众平台
                logger.info("正在访问微信公众平台...")
                page.goto("https://mp.weixin.qq.com", wait_until="networkidle")
                
                # 点击内容管理
                logger.info("点击内容管理...")
                page.wait_for_selector("//span[contains(text(), '内容管理')]", state="visible")
                page.click("//span[contains(text(), '内容管理')]")
                page.wait_for_load_state("networkidle")
                
                # 点击草稿箱
                logger.info("点击草稿箱...")
                page.wait_for_selector("span.weui-desktop-menu__name:has-text('草稿箱')", state="visible")
                page.click("span.weui-desktop-menu__name:has-text('草稿箱')")
                page.wait_for_load_state("networkidle")
                
                # 点击新建图文
                logger.info("点击新的创作...")
                try:
                    page.wait_for_selector("div.weui-desktop-card__inner:has-text('新的创作')", state="visible")
                    page.click("div.weui-desktop-card__inner:has-text('新的创作')")
                except:
                    logger.info("尝试使用备选元素点击...")
                    page.wait_for_selector('div.weui-desktop-card__inner[style="height: 234px;"][data-label-id="0"]', state="visible")
                    page.click('div.weui-desktop-card__inner[style="height: 234px;"][data-label-id="0"]')
                
                # 等待新页面打开
                logger.info("点击写新文章...")
                try:
                    with context.expect_page() as new_page_info:
                        page.click("a:has-text('写新文章')")
                    new_page = new_page_info.value
                except:
                    logger.info("尝试使用备选元素点击...")
                    with context.expect_page() as new_page_info:
                        page.click("a:has-text('写新图文')")
                    new_page = new_page_info.value
                
                # 等待新页面加载
                logger.info("等待新页面加载...")
                new_page.wait_for_load_state("networkidle")
                new_page.bring_to_front()
                
                # 上传文件
                logger.info("准备上传文件...")
                new_page.wait_for_selector("#js_import_file", state="visible", timeout=30000)
                new_page.click("#js_import_file")
                
                with new_page.expect_file_chooser() as fc_info:
                    new_page.click("label[style*='opacity: 0']")
                file_chooser = fc_info.value
                file_chooser.set_files(content_file)
                
                time.sleep(3)
                
                # 填写作者
                logger.info("填写作者信息...")
                new_page.fill("#author", author)
                
                # 处理原创声明
                logger.info("处理原创声明...")
                new_page.click("div.js_unset_original_title")
                checkbox = new_page.wait_for_selector("i.weui-desktop-icon-checkbox", state="visible")
                checkbox.check()
                new_page.click("button.weui-desktop-btn_primary:has-text('确定')")
                
                time.sleep(2)
                
                # 处理广告区域
                try:
                    logger.info("检查并处理广告区域...")
                    ad_area = new_page.wait_for_selector('//*[@id="js_insert_ad_area"]/label/span', 
                                                       state="visible", 
                                                       timeout=2000)
                    if ad_area:
                        logger.info("发布广告区域，进行处理...")
                        new_page.click('//*[@id="js_insert_ad_area"]/label/div/span[3]')
                        time.sleep(3)  # 增加等待时间
                        
                        frame = new_page.wait_for_selector('iframe', state="visible", timeout=2000)
                        if frame:
                            frame_element = frame.content_frame()
                            if frame_element:
                                # 直接使用 JavaScript 方案
                                frame_element.evaluate('''() => {
                                    const buttons = Array.from(document.querySelectorAll('button'));
                                    const confirmBtn = buttons.find(btn => {
                                        const span = btn.querySelector('span.adui-button-content');
                                        return span && span.textContent === '确认';
                                    });
                                    if (confirmBtn) confirmBtn.click();
                                }''')
                                time.sleep(2)  # 增加确认按钮点击后的等待时间
                except Exception as e:
                    logger.error(f"广告区域处理过程中出错: {str(e)}")
                    logger.info("继续执行后续步骤...")
                
                # 选择封面图
                logger.info("处理封面图...")
                try:
                    new_page.evaluate('''() => {
                        const links = Array.from(document.querySelectorAll('a'));
                        const link = links.find(a => a.textContent.includes('从正文选择'));
                        if (link) link.click();
                    }''')
                    
                    time.sleep(1)
                    
                    new_page.evaluate('''() => {
                        const images = document.querySelectorAll('.card_mask_global');
                        if (images.length > 0) {
                            images[0].click();
                        }
                    }''')
                    
                    next_button = new_page.wait_for_selector("button.weui-desktop-btn_primary:has-text('下一步')", 
                                                           state="visible", 
                                                           timeout=5000)
                    if next_button:
                        next_button.click()
                        
                        confirm_button = new_page.wait_for_selector("button.weui-desktop-btn_primary:has-text('确认')", 
                                                                  state="visible", 
                                                                  timeout=5000)
                        if confirm_button:
                            confirm_button.click()
                except Exception as e:
                    logger.error(f"封面图处理失败: {str(e)}")
                    logger.info("继续执行后续步骤...")

                # 等待封面图处理完成
                logger.info("等待封面图处理完成...")
                time.sleep(5)  # 在封面图处理和发表按钮之间增加等待时间

                # 直接发布
                logger.info("点击发表按钮...")
                try:
                    # 1. 点击第一个发表按钮 (mass_send)
                    logger.info("点击第一个发表按钮...")
                    publish_button = new_page.wait_for_selector("button.mass_send", state="visible", timeout=5000)
                    if publish_button:
                        publish_button.click()
                        logger.info("第一个发表按钮点击成功")
                        time.sleep(2)  # 等待2秒
                        
                        # 2. 点击第二个发表按钮 (weui-desktop-btn_primary)
                        logger.info("点击第二个发表按钮...")
                        confirm_publish = new_page.wait_for_selector(
                            "div.weui-desktop-btn_wrp button.weui-desktop-btn.weui-desktop-btn_primary:has-text('发表')", 
                            state="visible", 
                            timeout=5000
                        )
                        if confirm_publish:
                            confirm_publish.click()
                            logger.info("第二个发表按钮点击成功")
                            time.sleep(2)  # 等待2秒
                            
                            # 点击"继续发表"按钮
                            # logger.info("尝试点击继续发表按钮...")
                            # try:
                            #     continue_button = new_page.wait_for_selector(
                            #         "div.weui-desktop-btn_wrp button.weui-desktop-btn.weui-desktop-btn_primary:has-text('继续发表')",
                            #         state="visible",
                            #         timeout=5000
                            #     )
                            #     if continue_button:
                            #         # 获取按钮的位置信息
                            #         box = continue_button.bounding_box()
                            #         if box:
                            #             # 移动鼠标到按钮中心
                            #             new_page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                            #             time.sleep(0.5)  # 短暂等待
                            #             # 模拟鼠标点击
                            #             new_page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                            #             logger.info("继续发表按钮点击成功")
                            #             # 等待15秒确保发布完成
                            #             logger.info("等待1秒确保发布完成...")
                            #             time.sleep(1)
                            #             logger.info("等待完成，准备关闭页面...")
                            #         else:
                            #             logger.info("继续发表按钮不可见，跳过点击")
                            # except Exception as e:
                            #     logger.info(f"继续发表按钮不存在或无法点击，继续执行: {str(e)}")
                            
                            # time.sleep(2)  # 等待完成
                            
                            # 注释掉关闭浏览器的代码，让浏览器保持打开
                            # 关闭所有页面
                            # logger.info("关闭所有页面...")
                            # for page in context.pages:
                            #     page.close()
                            
                            # 关闭浏览器
                            # logger.info("关闭浏览器...")
                            # browser.close()
                            
                            # 关闭 BitBrowser
                            # url = f"http://127.0.0.1:54345/browser/close"
                            # data = {"id": browser_id}
                            # headers = {"Content-Type": "application/json"}
                            # response = requests.post(url, json=data, headers=headers)
                            # if response.status_code == 200:
                            #     logger.info("BitBrowser 已关闭")
                            # else:
                            #     logger.error(f"关闭 BitBrowser 失败: {response.status_code} - {response.text}")
                            
                            logger.info("发布成功，浏览器保持打开状态")
                            result_queue.put((True, "发布成功，浏览器保持打开状态"))
                        else:
                            raise Exception("找不到第二个发表按钮")
                    else:
                        raise Exception("找不到第一个发表按钮")
                except Exception as e:
                    logger.error(f"发布过程中出错: {str(e)}")
                    result_queue.put((False, str(e)))
                
            except Exception as e:
                logger.error(f"微信公众号发布操作失败: {str(e)}")
                logger.error(traceback.format_exc())
                try:
                    if 'new_page' in locals():
                        new_page.screenshot(path="error.png")
                        elements = new_page.evaluate('''() => {
                            return {
                                images: Array.from(document.querySelectorAll('*[class*="mask"]')).map(el => ({
                                    class: el.className,
                                    visible: el.offsetParent !== null,
                                    rect: el.getBoundingClientRect()
                                })),
                                buttons: Array.from(document.querySelectorAll('button')).map(el => ({
                                    text: el.textContent.trim(),
                                    visible: el.offsetParent !== null,
                                    disabled: el.disabled
                                }))
                            };
                        }''')
                        logger.error(f"页面元素状态: {elements}")
                except:
                    if 'page' in locals():
                        page.screenshot(path="error.png")
                result_queue.put((False, str(e)))
            finally:
                # 注释掉自动关闭浏览器的代码，让浏览器保持打开状态
                # if 'new_page' in locals() and new_page:
                #     new_page.close()
                # if 'browser' in locals() and browser:
                #     browser.close()
                
                # 清理工作已完成，结果已在前面的try-except中放入队列
                pass
                    
    except Exception as e:
        logger.error(f"发布失败: {str(e)}")
        logger.error(traceback.format_exc())
        result_queue.put((False, str(e)))

def extract_chinese_number(title):
    """从标题中提取中文序号并转换为数字"""
    chinese_numbers = {
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
        '十六': 16, '十七': 17, '十八': 18, '十九': 19, '二十': 20
    }
    
    # 检查标题是否以（序号）结尾
    if title and title.endswith('）'):
        start_pos = title.rfind('（')
        if start_pos != -1:
            number_part = title[start_pos+1:-1]
            return chinese_numbers.get(number_part, 999)  # 如果找不到对应的数字，返回一个大数
    return 999  # 如果没有序号，返回一个大数

def custom_title_sort(material):
    """自定义标题排序函数"""
    # 先按标题的主体部分排序
    base_title = material.title.rsplit('（', 1)[0] if material.title and '（' in material.title else material.title
    # 再按序号排序
    number_order = extract_chinese_number(material.title)
    return (base_title, number_order)

@router.get("")
async def get_materials(
    status: str = None,
    db: Session = Depends(get_db)
):
    """获取素材列表"""
    try:
        # 记录请求参数
        logger.info(f"获取素材列表，状态: {status}")
        
        # 构建基本查询
        query = db.query(Material)
        
        # 根据状态筛选
        if status == "published":
            query = query.filter(Material.status == "published")
        elif status == "unpublished":
            query = query.filter(Material.status == "unpublished")
        elif status == "scheduled":
            query = query.filter(
                Material.status == "unpublished",
                Material.schedule_time != None
            )
            
        # 获取所有账号信息，用于前端显示
        accounts = db.query(Account).all()
        logger.info(f"找到 {len(accounts)} 个账号")
        
        # 执行查询
        materials = query.all()
        logger.info(f"找到 {len(materials)} 个素材")
        
        # 转换为字典列表
        materials_list = []
        for material in materials:
            material_dict = {
                "id": material.id,
                "title": material.title,
                "word_count": material.word_count,
                "image_count": material.image_count,
                "status": material.status,
                "publish_status": material.publish_status,
                "publish_time": material.publish_time.isoformat() if material.publish_time else None,
                "account_id": material.account_id,
                "error_message": material.error_message,
                "schedule_time": material.schedule_time.isoformat() if material.schedule_time else None,
                "schedule_status": material.schedule_status,
                "author_name": material.account.author_name if material.account else None,
                "account_type": material.account.account_type if material.account else None
            }
            materials_list.append(material_dict)
            
        # 返回结果
        return {
            "success": True,
            "materials": materials_list,
            "accounts": [
                {
                    "id": account.id,
                    "author_name": account.author_name,
                    "account_type": account.account_type
                }
                for account in accounts
            ]
        }
        
    except Exception as e:
        logger.error(f"获取素材列表时出错: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

async def publish_group_materials(account_id: int, browser_id: str, material_ids: List[int], db: Session, toutiao_first: bool = False):
    """按顺序发布同一账号下的素材"""
    results = []
    browser = None
    account = db.query(Account).get(account_id)
    logger.info(f"开始处理账号 {account.author_name} (浏览器 {browser_id}) 的素材组，共 {len(material_ids)} 个素材")
    
    try:
        for material_id in material_ids:
            try:
                # 获取素材信息
                material = db.query(Material).filter(Material.id == material_id).first()
                if not material:
                    logger.error(f"素材 {material_id} 不存在")
                    results.append((material_id, False, "素材不存在"))
                    continue

                # 获取素材文件路径
                settings = db.query(Settings).first()
                if not settings or not settings.materials_path:
                    logger.error(f"素材 {material_id} 未设置素材库路径")
                    results.append((material_id, False, "未设置素材库路径"))
                    continue

                # 查找文件
                file_path = os.path.join(settings.materials_path, f"{material.original_title}.docx")
                if not os.path.exists(file_path):
                    found = False
                    for root, dirs, files in os.walk(settings.materials_path):
                        if f"{material.original_title}.docx" in files:
                            file_path = os.path.join(root, f"{material.original_title}.docx")
                            found = True
                            break
                    if not found:
                        logger.error(f"素材 {material_id} 找不到文件: {material.original_title}.docx")
                        results.append((material_id, False, f"找不到文件: {material.original_title}.docx"))
                        continue

                logger.info(f"开始发布素材: {material.title} (ID: {material_id})")
                # 根据账号类型执行不同的发布程序
                if account.account_type == "头条号":
                    success = await publish_to_toutiao(
                        browser_id=browser_id,
                        content_file=file_path,
                        author=account.author_name,
                        title=material.title,
                        is_first_publish=toutiao_first
                    )
                else:
                    success = await publish_to_wechat_direct(
                        browser_id=browser_id,
                        content_file=file_path,
                        author=account.author_name
                    )

                # 根据发布结果更新状态
                if success:
                    # 更新素材状态为成功
                    material.status = "published"
                    material.publish_status = "success"
                    material.publish_time = datetime.now()
                    if material.schedule_status == "scheduled":
                        material.schedule_status = "published"
                    db.commit()
                    logger.info(f"素材 {material.title} (ID: {material_id}) 发布成功")
                    results.append((material_id, True, "发布成功"))
                else:
                    # 更新素材状态为失败
                    material.status = "published"
                    material.publish_status = "failed"
                    material.publish_time = datetime.now()
                    if material.schedule_status == "scheduled":
                        material.schedule_status = "failed"
                    db.commit()
                    logger.info(f"素材 {material.title} (ID: {material_id}) 发布失败")
                    results.append((material_id, False, "发布失败"))

            except Exception as e:
                logger.error(f"发布素材 {material_id} 失败: {str(e)}")
                logger.error(traceback.format_exc())
                results.append((material_id, False, str(e)))
                continue

    except Exception as e:
        logger.error(f"发布组内素材失败: {str(e)}")
        logger.error(traceback.format_exc())
        if not results:
            results.append((material_ids[0] if material_ids else 0, False, str(e)))

    logger.info(f"账号 {account.author_name} 的素材组处理完成")
    return results

async def batch_publish_materials(material_ids: List[int], toutiao_first: bool, db: Session):
    """批量发布素材，支持同账号顺序发布和不同账号并行发布"""
    try:
        # 1. 按账号和浏览器分组
        groups = {}  # {(account_id, browser_id): [material_ids]}
        order_map = {}  # {material_id: original_order}
        browser_info = set()  # 用于记录不同的浏器信息
        
        logger.info(f"开始处理批量发布请求，共 {len(material_ids)} 个素材")
        logger.info(f"头条号首发状态: {toutiao_first}")
        logger.info(f"素材ID列表: {material_ids}")

        for order, material_id in enumerate(material_ids):
            material = db.query(Material).get(material_id)
            if not material or not material.account_id:
                logger.warning(f"素材 {material_id} 未设置发布账号，跳过")
                continue
            
            account = db.query(Account).get(material.account_id)
            if not account:
                logger.warning(f"素材 {material_id} 的账号不存在，跳过")
                continue
                
            key = (account.id, account.browser_id)
            browser_info.add((account.author_name, account.browser_id))
            if key not in groups:
                groups[key] = []
            groups[key].append(material_id)
            order_map[material_id] = order

        # 记录分组和浏览器信息
        logger.info(f"共有 {len(material_ids)} 个素材待发布")
        logger.info(f"分组后共有 {len(groups)} 个发布组")
        logger.info("浏览器使用情况:")
        for author_name, browser_id in browser_info:
            logger.info(f"- 号: {author_name}, 浏览器ID: {browser_id}")

        # 2. 创建发布任务
        tasks = []
        for (account_id, browser_id), group_material_ids in groups.items():
            # 对每个组内的素材按原选择顺序排序
            sorted_materials = sorted(group_material_ids, key=lambda x: order_map[x])
            account = db.query(Account).get(account_id)
            logger.info(f"创建发布任务: 号 {account.author_name}, 浏览器 {browser_id}, 素材数量 {len(sorted_materials)}")
            logger.info(f"该组素材ID（按序）: {sorted_materials}")
            
            # 根据账号类型选择发布函数和参数
            task = publish_group_materials(account_id, browser_id, sorted_materials, db, toutiao_first)
            tasks.append(task)

        # 3. 并行执行不同组的任务
        logger.info(f"开始并行执行 {len(tasks)} 个发布任务")
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 4. 处理结果
        final_results = []
        for results in all_results:
            if isinstance(results, Exception):
                logger.error(f"任务执行失败: {str(results)}")
                continue
            final_results.extend(results)

        # 记录执行结果
        success_count = sum(1 for r in final_results if r[1])
        logger.info(f"批量发布完成: 成功 {success_count} 个, 失败 {len(final_results) - success_count} 个")
        logger.info("详细结果:")
        for material_id, success, message in final_results:
            logger.info(f"- 素材 {material_id}: {'成功' if success else '失败'} - {message}")

        return final_results

    except Exception as e:
        logger.error(f"批量发布过程出错: {str(e)}")
        logger.error(traceback.format_exc())
        raise

@router.post("/publish-batch")
async def publish_batch(
    request: BatchPublishRequest,
    db: Session = Depends(get_db)
):
    try:
        if request.schedule_publish:
            # 前端发送的已经是本地时间，直接使用
            schedule_time = request.schedule_time
            logger.info(f"处理预约发布请求: {len(request.material_ids)} 个素材, 预约时间: {schedule_time}")
            success_count = 0
            results = []
            
            for material_id in request.material_ids:
                try:
                    material = db.query(Material).get(material_id)
                    if not material:
                        results.append((material_id, False, "素材不存在"))
                        continue
                        
                    if not material.account_id:
                        results.append((material_id, False, "未选择发布账号"))
                        continue
                        
                    # 更新为预约状态
                    material.status = "scheduled"
                    material.schedule_status = "scheduled"
                    material.schedule_time = schedule_time  # 使用转换后的东八区时间
                    success_count += 1
                    results.append((material_id, True, "预约成功"))
                    logger.info(f"素材 {material_id} 预约成功")
                    
                except Exception as e:
                    logger.error(f"预约素材 {material_id} 失败: {str(e)}")
                    results.append((material_id, False, str(e)))
            
            db.commit()
            return {
                "success": True,
                "message": f"完成预约：{success_count}个成功，{len(results) - success_count}个失败",
                "details": [
                    {
                        "material_id": r[0],
                        "success": r[1],
                        "message": r[2]
                    }
                    for r in results
                ]
            }
        else:
            # 原有的直接发布逻辑
            results = await batch_publish_materials(request.material_ids, request.toutiao_first, db)
            
            # 更新成功发布的素材状态
            success_count = 0
            for material_id, success, message in results:
                material = db.query(Material).get(material_id)
                if material:
                    material.status = "published"
                    material.publish_status = "success" if success else "failed"
                    material.publish_time = datetime.now()
                    if success:
                        success_count += 1

            db.commit()
            failed_count = len(results) - success_count
            
            return {
                "success": True,
                "message": f"完成发布：{success_count}个成功，{failed_count}个失败",
                "details": [
                    {
                        "material_id": r[0],
                        "success": r[1],
                        "message": r[2]
                    }
                    for r in results
                ]
            }
    except Exception as e:
        db.rollback()
        logger.error(f"批量发布失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{material_id}")
async def delete_material(material_id: int, db: Session = Depends(get_db)):
    try:
        material = db.query(Material).filter(Material.id == material_id).first()
        if not material:
            raise HTTPException(status_code=404, detail="Material not found")
        
        # 只删除数据库记录，不删除文件
        db.delete(material)
        db.commit()
        return {"success": True, "message": "素材已删除"}
    except Exception as e:
        db.rollback()
        logger.error(f"删除素材失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{material_id}/status")
async def update_material_status(
    material_id: int,
    status_update: StatusUpdate,
    db: Session = Depends(get_db)
):
    try:
        material = db.query(Material).filter(Material.id == material_id).first()
        if not material:
            raise HTTPException(status_code=404, detail="Material not found")
        
        # 更新状态
        material.status = status_update.status
        # 如果返回到未发布状态，清除发布时间和发布状态
        if status_update.status == "unpublished":
            material.publish_time = None
            material.publish_status = None
        elif status_update.status == "published":
            material.publish_time = datetime.now()
            material.publish_status = "success"
            
        db.commit()
        return {"success": True, "message": f"素材状态已更新为{status_update.status}"}
    except Exception as e:
        db.rollback()
        logger.error(f"更新素材状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch-return")
async def batch_return_to_unpublished(db: Session = Depends(get_db)):
    try:
        # 获取所有发布的非示例素材
        materials = db.query(Material).filter(
            Material.status == "published",
            ~Material.title.in_([
                "人工智能发展趋势",
                "Web3.0技术解析",
                "元宙发展前景"
            ])
        ).all()
        
        # 更新状态为未发布
        for material in materials:
            material.status = "unpublished"
            material.publish_time = None
        
        db.commit()
        return {
            "success": True,
            "message": f"已将 {len(materials)} 个素材返回到未发布状态"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"批量返回到未发布状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch-clear")
async def batch_clear_published(db: Session = Depends(get_db)):
    """批量清空已发布素材显示（设置为隐藏状态）"""
    try:
        # 获取所有已发布的素材
        materials = db.query(Material).filter(
            Material.status == "published"
        ).all()
        
        cleared_count = 0
        # 将已发布的素材设置为隐藏状态
        for material in materials:
            material.status = "hidden"  # 使用hidden状态来隐藏显示
            cleared_count += 1
        
        db.commit()
        logger.info(f"批量清空了 {cleared_count} 个已发布素材")
        
        return {
            "success": True,
            "cleared_count": cleared_count,
            "message": f"已清空 {cleared_count} 个已发布素材的显示"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"批量清空已发布素材失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{material_id}/title")
async def update_material_title(
    material_id: int,
    title_update: TitleUpdate,
    db: Session = Depends(get_db)
):
    try:
        material = db.query(Material).filter(Material.id == material_id).first()
        if not material:
            raise HTTPException(status_code=404, detail="Material not found")
        
        # 只更新显示标题，不更新原始标题
        material.title = title_update.title
        db.commit()
        
        return {"success": True, "message": "题已更新"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating material title: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{material_id}/direct-publish")
async def direct_publish_material(
    material_id: int,
    request: DirectPublishRequest,
    db: Session = Depends(get_db)
):
    """直接发布或预约发布素材"""
    logger.info(f"收到发布请求，material_id: {material_id}, 头条号首发: {request.toutiao_first}, 预约发布: {request.schedule_publish}")
    try:
        # 获取素材信息
        material = db.query(Material).filter(Material.id == material_id).first()
        if not material:
            logger.error(f"找不到素材: {material_id}")
            raise HTTPException(status_code=404, detail="Material not found")
            
        # 检查是否已选择账号
        if not material.account_id:
            logger.error(f"素材 {material_id} 未选择发布账号")
            raise HTTPException(status_code=400, detail="请先选择发布账号")
            
        # 获取账号信息
        account = db.query(Account).filter(Account.id == material.account_id).first()
        if not account:
            logger.error(f"找不到账号: {material.account_id}")
            raise HTTPException(status_code=404, detail="Account not found")
            
        # 检查账号状态
        if account.status != "active":
            logger.error(f"账号 {account.id} 未激活")
            raise HTTPException(status_code=400, detail="所选账号未激活")

        if request.schedule_publish:
            # 预约发布，前端发送的已经是本地时间，直接使用
            material.status = "scheduled"
            material.schedule_status = "scheduled"
            material.schedule_time = request.schedule_time
            db.commit()
            return {"success": True, "message": "预约发布成功"}
        else:
            # 原有的直接发布逻辑
            # 检查 original_title 是否存在
            if not material.original_title:
                logger.error(f"素材 {material_id} 没有原始文件名")
                raise HTTPException(status_code=400, detail="素材文件名错误，请重新扫描素材库")
            
            # 获取素材库路径
            settings = db.query(Settings).first()
            if not settings or not settings.materials_path:
                logger.error("未设置素材库路径")
                raise HTTPException(status_code=400, detail="未设置素材库路径")
            
            # 构建文件路径 - 使用 original_title 而不是 title
            file_path = os.path.join(settings.materials_path, f"{material.original_title}.docx")
            logger.info(f"尝试查找文件: {file_path}")
            
            if not os.path.exists(file_path):
                logger.info("在根目录未找到文件，尝试在子目录中查找")
                # 尝试在子目录中查找
                found = False
                for root, dirs, files in os.walk(settings.materials_path):
                    for file in files:
                        if file == f"{material.original_title}.docx":
                            file_path = os.path.join(root, file)
                            found = True
                            logger.info(f"在子目录中找到文件: {file_path}")
                            break
                    if found:
                        break
                
                if not found:
                    logger.error(f"找不到文件: {material.original_title}.docx")
                    raise HTTPException(status_code=404, detail=f"找不到文件: {material.original_title}.docx")
            
            logger.info(f"找到文件: {file_path}")
            
            # 根据账号类型选择发布函数
            if account.account_type == "公众号":
                success = await publish_to_wechat_direct(
                    browser_id=account.browser_id,
                    content_file=file_path,
                    author=account.author_name
                )
            elif account.account_type == "头条号":
                # 头条号直接使用原有的发布到草稿箱功能但传入首发状态
                success = await publish_to_toutiao(
                    browser_id=account.browser_id,
                    content_file=file_path,
                    author=account.author_name,
                    title=material.title,
                    is_first_publish=request.toutiao_first  # 添加首发状态参数
                )
            else:
                logger.error(f"不支持的账号类型: {account.account_type}")
                raise HTTPException(status_code=400, detail=f"不支持的账号类型: {account.account_type}")
            
            if success:
                # 更新素材状态为已发布，并设置发布状态为成功
                material.status = "published"
                material.publish_status = "success"
                material.publish_time = datetime.now()
                db.commit()
                return {"success": True, "message": "文章已发布"}
            else:
                # 更新素材状态为已发布，但设置发布状态为失败
                material.status = "published"
                material.publish_status = "failed"
                material.publish_time = datetime.now()
                db.commit()
                raise HTTPException(status_code=500, detail="发布失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发布素材失败: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel-all-schedules")
async def cancel_all_schedules(db: Session = Depends(get_db)):
    """取消所有预约发布任务"""
    try:
        # 查找所有预约状态的素材
        materials = db.query(Material).filter(
            Material.status == "scheduled",
            Material.schedule_status == "scheduled"
        ).all()
        
        count = 0
        for material in materials:
            material.status = "unpublished"
            material.schedule_status = None
            material.schedule_time = None
            count += 1
        
        db.commit()
        return {
            "success": True,
            "message": f"已取消 {count} 个预约发布任务"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"取消所有预约失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{material_id}/cancel-schedule")
async def cancel_schedule(material_id: int, db: Session = Depends(get_db)):
    """取消单个预约发布任务"""
    try:
        material = db.query(Material).get(material_id)
        if not material:
            raise HTTPException(status_code=404, detail="Material not found")
            
        if material.status != "scheduled" or material.schedule_status != "scheduled":
            raise HTTPException(status_code=400, detail="该素材不是预约状态")
            
        material.status = "unpublished"
        material.schedule_status = None
        material.schedule_time = None
        db.commit()
        
        return {
            "success": True,
            "message": "预约已取消"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"取消预约失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{material_id}/update-schedule")
async def update_schedule_time(
    material_id: int,
    schedule_data: ScheduleTimeUpdate,
    db: Session = Depends(get_db)
):
    """更新预约发布时间"""
    try:
        material = db.query(Material).get(material_id)
        if not material:
            raise HTTPException(status_code=404, detail="Material not found")
            
        if material.status != "scheduled" or material.schedule_status != "scheduled":
            raise HTTPException(status_code=400, detail="该素材不是预约状态")
            
        # 前端发送的已经是本地时间，直接使用
        material.schedule_time = schedule_data.schedule_time
        db.commit()
        
        return {
            "success": True,
            "message": "预约时间已更新"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新预约时间失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class AccountUpdate(BaseModel):
    account_id: int

@router.post("/{material_id}/account")
async def update_material_account(
    material_id: int,
    account_update: AccountUpdate,
    db: Session = Depends(get_db)
):
    """更新素材的发布账号"""
    try:
        logger.info(f"更新素材 {material_id} 的账号为 {account_update.account_id}")
        
        # 获取素材
        material = db.query(Material).filter(Material.id == material_id).first()
        if not material:
            logger.error(f"素材 {material_id} 不存在")
            return {"success": False, "message": "素材不存在"}
            
        # 获取账号
        account = db.query(Account).filter(Account.id == account_update.account_id).first()
        if not account:
            logger.error(f"账号 {account_update.account_id} 不存在")
            return {"success": False, "message": "账号不存在"}
            
        # 更新素材的账号
        material.account_id = account_update.account_id
        db.commit()
        
        logger.info(f"成功更新素材 {material_id} 的账号")
        return {"success": True}
        
    except Exception as e:
        logger.error(f"更新素材账号时出错: {str(e)}")
        db.rollback()
        return {"success": False, "message": str(e)}

def _handle_document_import(page, content_file: str):
    """处理文档导入"""
    button = page.locator('button.syl-toolbar-button:has(svg path[d="M19 17v2a1 1 0 01-1 1H6a1 1 0 01-1-1V5a1 1 0 011-1h7l6 4v4"])')
    box = button.bounding_box()
    if box:
        page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
        time.sleep(0.5)
        page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
    else:
        raise Exception("未能找到文档导入按钮")

    time.sleep(2)

    # 试多种方式定位文件上传输入框
    selectors = [
        'input[type="file"]',
        'input[accept=".doc,.docx,application/msword"]',
        'input[accept*="pdf"]',
        '//input[@type="file"]'
    ]

    upload_success = False
    for selector in selectors:
        try:
            logger.info(f"尝试使用选择器: {selector}")
            if selector.startswith('//'):
                element = page.wait_for_selector(f"xpath={selector}", timeout=5000)
            else:
                element = page.wait_for_selector(selector, timeout=5000)

            if element:
                page.set_input_files(selector, content_file)
                upload_success = True
                logger.info("文件上传成功")
                break
        except Exception as e:
            logger.warning(f"选择器 {selector} 失败: {str(e)}")
            continue

    if not upload_success:
        raise Exception("无法找到文件上传输入框")

    # 等待上传完成
    page.wait_for_load_state('networkidle')
    time.sleep(3)

def _handle_first_publish_option(page, is_first_publish: bool):
    """处理首发选项"""
    logger.info(f"处理首发选项，发状态: {is_first_publish}")
    
    # 等待首发复选框出现
    page.wait_for_selector('div.byte-checkbox-wrapper', timeout=5000)
    time.sleep(1)  # 给页面一点时间完全加载

    # 获取当前复选框状态
    is_checked = page.evaluate('''() => {
        const checkbox = document.querySelector('div.byte-checkbox-wrapper');
        return checkbox && checkbox.classList.contains('byte-checkbox-checked');
    }''')
    
    logger.info(f"当前首发复选框状态: {is_checked}, 目标状态: {is_first_publish}")
    
    if is_first_publish != is_checked:
        logger.info(f"需{'勾选' if is_first_publish else '取消勾选'}首发复选框...")
        success = False
        
        # 尝试所有可能的点击方法
        click_methods = [
            _try_click_label_first_publish,
            _try_click_input_first_publish,
            _try_click_js_event_first_publish,
            _try_click_mouse_first_publish,
            _try_click_keyboard_first_publish
        ]
        
        for method in click_methods:
            if not success:
                try:
                    success = method(page, is_checked)  # 传递当前状态
                    if success:
                        # 验证状态是否真的改变了
                        new_state = page.evaluate('''() => {
                            const checkbox = document.querySelector('div.byte-checkbox-wrapper');
                            return checkbox && checkbox.classList.contains('byte-checkbox-checked');
                        }''')
                        if new_state == is_first_publish:
                            logger.info(f"{method.__name__} 成")
                            break
                        else:
                            logger.warning(f"{method.__name__} 看似成功但状态未改变")
                            success = False
                except Exception as e:
                    logger.error(f"{method.__name__} 失败: {str(e)}")
                    # 继续尝试下一个方法
                    continue
        
        if not success:
            error_msg = f"所有方法都失败了，无法{'勾选' if is_first_publish else '取消勾选'}首发复选框"
            logger.error(error_msg)
            # 保存错误截图
            try:
                page.screenshot(path="first_publish_error.png")
                logger.info("已保存错误截图: first_publish_error.png")
            except Exception as screenshot_error:
                logger.error(f"保存错误截图失败: {str(screenshot_error)}")
            raise Exception(error_msg)
        
        logger.info(f"成功{'勾选' if is_first_publish else '取消勾选'}首发复选框")
    else:
        logger.info(f"复选框已经是{'选中' if is_first_publish else '未选中'}状态，无需操作")

def _try_click_label_first_publish(page, current_state: bool) -> bool:
    """尝试点击label元素"""
    logger.info("尝试方法: 直接点击label元素")
    label = page.locator('div.byte-checkbox-wrapper').first
    if label:
        label.click()
        time.sleep(1)
        # 检查状态是否改变
        new_state = page.evaluate('''() => {
            const checkbox = document.querySelector('div.byte-checkbox-wrapper');
            return checkbox && checkbox.classList.contains('byte-checkbox-checked');
        }''')
        return new_state != current_state
    return False

def _try_click_input_first_publish(page, current_state: bool) -> bool:
    """尝试点击input元素"""
    logger.info("尝试方法: 点击input元素")
    page.evaluate('''() => {
        const input = document.querySelector('div.byte-checkbox-wrapper input[type="checkbox"]');
        if (input) input.click();
    }''')
    time.sleep(1)
    # 检查状态是否改变
    new_state = page.evaluate('''() => {
        const checkbox = document.querySelector('div.byte-checkbox-wrapper');
        return checkbox && checkbox.classList.contains('byte-checkbox-checked');
    }''')
    return new_state != current_state

def _try_click_js_event_first_publish(page, current_state: bool) -> bool:
    """尝试使用JavaScript模拟点击事件"""
    logger.info("尝试方法: 使用JavaScript模拟点击事件")
    page.evaluate('''() => {
        const label = document.querySelector('div.byte-checkbox-wrapper');
        if (label) {
            const event = new MouseEvent('click', {
                bubbles: true,
                cancelable: true,
                view: window
            });
            label.dispatchEvent(event);
        }
    }''')
    time.sleep(1)
    # 检查状态是否改变
    new_state = page.evaluate('''() => {
        const checkbox = document.querySelector('div.byte-checkbox-wrapper');
        return checkbox && checkbox.classList.contains('byte-checkbox-checked');
    }''')
    return new_state != current_state

def _try_click_mouse_first_publish(page, current_state: bool) -> bool:
    """尝试使用鼠标模拟点击"""
    logger.info("尝试方法: 使用鼠标模拟点击")
    checkbox = page.locator('div.byte-checkbox-wrapper')
    box = checkbox.bounding_box()
    if box:
        logger.info(f"复选框位置信息: x={box['x']}, y={box['y']}, width={box['width']}, height={box['height']}")
        click_x = box['x'] + box['width']/2
        click_y = box['y'] + box['height']/2
        page.mouse.move(click_x, click_y)
        time.sleep(0.5)
        page.mouse.click(click_x, click_y)
        time.sleep(1)
        # 检查状态是否改变
        new_state = page.evaluate('''() => {
            const checkbox = document.querySelector('div.byte-checkbox-wrapper');
            return checkbox && checkbox.classList.contains('byte-checkbox-checked');
        }''')
        return new_state != current_state
    return False

def _try_click_keyboard_first_publish(page, current_state: bool) -> bool:
    """尝试使用keyboard模拟空格键"""
    logger.info("尝试方法: 使用keyboard模拟空格键")
    label = page.locator('div.byte-checkbox-wrapper').first
    if label:
        label.focus()
        page.keyboard.press('Space')
        time.sleep(1)
        # 检查状态是否改变
        new_state = page.evaluate('''() => {
            const checkbox = document.querySelector('div.byte-checkbox-wrapper');
            return checkbox && checkbox.classList.contains('byte-checkbox-checked');
        }''')
        return new_state != current_state
    return False

def _handle_cover_settings(page):
    """处理封面设置"""
    logger.info("正在检查封面设置选项...")
    
    # 检查封面设置按钮是否存在
    cover_add = page.locator('div.article-cover-add')
    if cover_add.count() > 0:
        logger.info("找到封面设置按钮，进行封面设置...")
        # 点击"无封面"选项
        no_cover_radio = page.locator("label").filter(has_text="无封面").locator("div")
        if no_cover_radio.count() > 0:
            no_cover_radio.click()
            logger.info("已选择无封面选项")
        else:
            logger.warning("未找到无封面选项，跳过封面设置")
    else:
        logger.info("未找到封面设置按钮，跳过封面设置")

def _handle_toutiao_first_checkbox(page, result_queue: Queue):
    """处理头条首发复选框"""
    logger.info("=== 开始处理头条首发复选框 ===")
    logger.info("目标状态: 取消勾选")
    
    # 确保页面仍然打开
    if page.is_closed():
        logger.error("页面已关闭，无法操作复选框")
        raise Exception("页面已关闭")

    logger.info("正在等待复选框元素出现...")
    # 等待复选框元素出现
    checkbox = page.wait_for_selector('div.exclusive-checkbox-wraper', timeout=5000)
    if not checkbox:
        logger.warning("未找到头条首发复选框，继续执行...")
        return

    logger.info("成功找到复选框容器元素")
    
    # 记录元素的HTML结构
    try:
        element_html = page.evaluate('''(element) => element.outerHTML''', checkbox)
        logger.info(f"复选框元素HTML结构: {element_html}")
    except Exception as e:
        logger.error(f"获取HTML结构失败: {str(e)}")
    
    # 使用多种方式检查复选框状态
    is_checked = get_checkbox_state(page)
    logger.info(f"当前头条首发复选框状态: {'已选中' if is_checked else '未选中'}")
    
    # 如果复选框已勾选，则尝试多种方式取消勾选
    if is_checked:
        logger.info("需要取消勾选头条首发复选框...")
        success = False
        
        # 尝试所有可能的点击方法
        click_methods = [
            _try_click_label,
            _try_click_input,
            _try_click_js_event,
            _try_click_mouse,
            _try_click_keyboard
        ]
        
        for method in click_methods:
            if not success:
                try:
                    success = method(page)
                    if success:
                        logger.info(f"{method.__name__} 成功")
                        break
                except Exception as e:
                    logger.error(f"{method.__name__} 失败: {str(e)}")
        
        if not success:
            logger.error("所有方法都失败了，无法取消勾选复选框")
            result_queue.put((False, "无法取消勾选头条首发复选框"))
            raise Exception("无法取消勾选头条首发复选框")
        
        logger.info("成功取消勾选复选框")
    else:
        logger.info("复选框已经是未选中状态，无需操作")

    logger.info("=== 头条首发复选框处理完成 ===")
    logger.info("继续执行发布流程...")

def _try_click_label(page) -> bool:
    """尝试点击label元素"""
    logger.info("尝试方法: 直接点击label元素")
    label = page.locator('label.byte-checkbox.checkbot-item.checkbox-with-tip').first
    if label:
        label.click()
        time.sleep(1)
        return not get_checkbox_state(page)
    return False

def _try_click_input(page) -> bool:
    """尝试点击input元素"""
    logger.info("尝试方法: 点击input元素")
    page.evaluate('''() => {
        const input = document.querySelector('div.exclusive-checkbox-wraper input[type="checkbox"]');
        if (input) input.click();
    }''')
    time.sleep(1)
    return not get_checkbox_state(page)

def _try_click_js_event(page) -> bool:
    """尝试使用JavaScript模拟点击事件"""
    logger.info("尝试方法: 使用JavaScript模拟点击事件")
    page.evaluate('''() => {
        const label = document.querySelector('label.byte-checkbox.checkbot-item.checkbox-with-tip');
        if (label) {
            const event = new MouseEvent('click', {
                bubbles: true,
                cancelable: true,
                view: window
            });
            label.dispatchEvent(event);
        }
    }''')
    time.sleep(1)
    return not get_checkbox_state(page)

def _try_click_mouse(page) -> bool:
    """尝试使用鼠标模拟点击"""
    logger.info("尝试方法: 使用鼠标模拟点击")
    checkbox = page.locator('div.exclusive-checkbox-wraper')
    box = checkbox.bounding_box()
    if box:
        logger.info(f"复选框位置信息: x={box['x']}, y={box['y']}, width={box['width']}, height={box['height']}")
        click_x = box['x'] + box['width']/2
        click_y = box['y'] + box['height']/2
        page.mouse.move(click_x, click_y)
        time.sleep(0.5)
        page.mouse.click(click_x, click_y)
        time.sleep(1)
        return not get_checkbox_state(page)
    return False

def _try_click_keyboard(page) -> bool:
    """尝试使用keyboard模拟空格键"""
    logger.info("尝试方法: 使用keyboard模拟空格键")
    label = page.locator('label.byte-checkbox.checkbot-item.checkbox-with-tip').first
    if label:
        label.focus()
        page.keyboard.press('Space')
        time.sleep(1)
        return not get_checkbox_state(page)
    return False

def _publish_article(page):
    """发布文章"""
    # 点击"预览并发布"
    logger.info("正在点击预览并发布按钮...")
    page.click('button.publish-btn:has-text("预览并发")')
    
    # 等待预览页面加载
    time.sleep(2)
    
    # 点击"确认发布"
    logger.info("正在点击确认发布按钮...")
    page.click('button.publish-btn:has-text("确认发布")')
    
    # 等待发布完成
    time.sleep(5)
    logger.info("文章发布流程完成") 

@router.post("/batch-publish")
async def batch_publish(
    material_ids: list[int],
    is_toutiao_first: bool = False,
    db: Session = Depends(get_db)
):
    """批量发布素材"""
    try:
        logger.info(f"开始批量发布，素材IDs: {material_ids}, 头条优先: {is_toutiao_first}")
        
        # 获取所有活跃的账号
        accounts = db.query(Account).filter(Account.status == "active").all()
        logger.info(f"找到 {len(accounts)} 个活跃账号")
        
        if not accounts:
            logger.error("没有可用的账号")
            return {"success": False, "message": "没有可用的账号"}
            
        # 按账号类型分组
        toutiao_accounts = [acc for acc in accounts if acc.account_type == "头条号" and acc.can_login]
        wechat_accounts = [acc for acc in accounts if acc.account_type == "公众号" and acc.can_login]
        
        logger.info(f"可用头条号账号: {len(toutiao_accounts)}")
        logger.info(f"可用公众号账号: {len(wechat_accounts)}")
        
        # 获取要发布的素材
        materials = db.query(Material).filter(Material.id.in_(material_ids)).all()
        logger.info(f"找到 {len(materials)} 个要发布的素材")
        
        if not materials:
            logger.error("没有找到要发布的素材")
            return {"success": False, "message": "没有找到要发布的素材"}
            
        # 发布结果统计
        results = {
            "total": len(materials),
            "success": 0,
            "failed": 0,
            "details": []
        }
        
        # 根据头条优先设置决定发布顺序
        if is_toutiao_first and toutiao_accounts:
            primary_accounts = toutiao_accounts
            secondary_accounts = wechat_accounts
            logger.info("使用头条号优先发布策略")
        else:
            primary_accounts = wechat_accounts
            secondary_accounts = toutiao_accounts
            logger.info("使用公众号优先发布策略")
            
        # 合并账号列表，确保有序性
        all_accounts = primary_accounts + secondary_accounts
        logger.info(f"总可用账号数: {len(all_accounts)}")
        
        # 记录每个账号已发布的数量
        account_publish_count = {acc.id: 0 for acc in all_accounts}
        
        # 为每个素材分配账号并发布
        for material in materials:
            try:
                logger.info(f"正在处理素材: {material.title}")
                
                # 找到发布量最少的账号
                selected_account = min(
                    all_accounts,
                    key=lambda acc: account_publish_count[acc.id]
                )
                
                logger.info(f"选择账号 {selected_account.username} 进行发布")
                
                # 更新素材状态
                material.account_id = selected_account.id
                material.status = "published"
                material.publish_time = datetime.now()
                
                # 增加该账号的发布计数
                account_publish_count[selected_account.id] += 1
                
                # 记录发布成功
                results["success"] += 1
                results["details"].append({
                    "material_id": material.id,
                    "title": material.title,
                    "account": selected_account.username,
                    "status": "success"
                })
                
                logger.info(f"素材 {material.title} 发布成功")
                
            except Exception as e:
                logger.error(f"发布素材 {material.title} 时出错: {str(e)}")
                results["failed"] += 1
                results["details"].append({
                    "material_id": material.id,
                    "title": material.title,
                    "error": str(e),
                    "status": "failed"
                })
                continue
        
        # 提交数据库更改
        db.commit()
        logger.info(f"批量发布完成，成功: {results['success']}, 失败: {results['failed']}")
        
        return {
            "success": True,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"批量发布过程出错: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        return {"success": False, "message": str(e)}