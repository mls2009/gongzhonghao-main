from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db, Account
from playwright.sync_api import sync_playwright
import asyncio
import logging
import httpx
from multiprocessing import Process, Queue
import traceback
from collections import defaultdict

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

async def open_bitbrowser(browser_id: str) -> dict:
    """打开BitBrowser，增加重试机制"""
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            url = f"http://127.0.0.1:54345/browser/open"
            json_data = {"id": browser_id}
            headers = {"Content-Type": "application/json"}
            
            logger.info(f"尝试打开浏览器，第 {retry_count + 1} 次尝试")
            logger.info(f"请求URL: {url}")
            logger.info(f"请求数据: {json_data}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=json_data, headers=headers)
                logger.info(f"API 响应状态码: {response.status_code}")
                logger.info(f"API 响应内容: {response.text}")
                
                response_data = response.json()
                logger.info(f"解析后的响应数据: {response_data}")
                
                if response_data.get('success'):
                    browser_data = response_data.get('data', {})
                    logger.info(f"成功打开浏览器 {browser_id}")
                    logger.info(f"浏览器数据: {browser_data}")
                    if browser_data.get('ws'):
                        logger.info(f"获取到 WebSocket URL: {browser_data['ws']}")
                    else:
                        logger.error("响应中没有 WebSocket URL")
                    return browser_data
                else:
                    error_msg = response_data.get('msg') or response_data.get('message') or "未知错误"
                    logger.error(f"API 返回错误: {error_msg}")
                    
        except Exception as e:
            logger.error(f"打开浏览器时发生异常: {str(e)}")
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            
        retry_count += 1
        if retry_count < max_retries:
            logger.info(f"等待 5 秒后进行第 {retry_count + 1} 次重试...")
            await asyncio.sleep(5)
    
    logger.error(f"在 {max_retries} 次尝试后仍然无法打开浏览器")
    return None

def _run_playwright_process(browser_id: str, account_type: str, ws_url: str, result_queue: Queue):
    """在单独进程中运行 Playwright"""
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(ws_url)
            context = browser.contexts[0]
            page = context.new_page()

            if account_type == "公众号":
                page.goto("https://mp.weixin.qq.com/")
                logger.info("正在访问公众号平台...")
                page.wait_for_load_state('networkidle')
            elif account_type == "头条号":
                page.goto("https://mp.toutiao.com/profile_v4/index")
                logger.info("正在访问头条号平台...")
                page.wait_for_load_state('networkidle')
            elif account_type == "小红书":
                page.goto("https://creator.xiaohongshu.com/publish/publish?source=official&from=menu&target=image")
                logger.info("正在访问小红书平台...")
                page.wait_for_load_state('networkidle')

            result_queue.put((True, None))
    except Exception as e:
        result_queue.put((False, str(e)))
    finally:
        try:
            browser.close()
        except:
            pass

@router.post("/{account_id}/open")
async def open_account(account_id: int, db: Session = Depends(get_db)):
    """打开账号并访问对应平台"""
    try:
        logger.info(f"=== 开始打开账号操作，账号ID: {account_id} ===")
        
        # 获取账号信息
        logger.info("步骤1: 从数据库获取账号信息")
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            logger.error(f"账号不存在: {account_id}")
            raise HTTPException(status_code=404, detail="账号不存在")
        
        logger.info(f"找到账号: {account.username}, 类型: {account.account_type}, 浏览器ID: {account.browser_id}")
            
        # 尝试打开浏览器
        logger.info("步骤2: 尝试打开BitBrowser")
        browser_data = await open_bitbrowser(account.browser_id)
        
        if not browser_data:
            logger.error("open_bitbrowser 返回了 None")
            raise HTTPException(status_code=500, detail="无法连接到BitBrowser服务")
        
        logger.info(f"BitBrowser响应数据: {browser_data}")
        
        if not browser_data.get('ws'):
            logger.error(f"BitBrowser响应中没有WebSocket URL，完整响应: {browser_data}")
            raise HTTPException(status_code=500, detail="无法获取浏览器WebSocket URL")
        
        logger.info(f"获取到WebSocket URL: {browser_data['ws']}")
            
        # 使用 Playwright 访问对应平台
        logger.info("步骤3: 使用Playwright访问平台")
        try:
            result_queue = Queue()
            logger.info("创建多进程队列成功")
            
            process = Process(
                target=_run_playwright_process,
                args=(account.browser_id, account.account_type, browser_data['ws'], result_queue)
            )
            logger.info("创建子进程成功，准备启动")
            
            process.start()
            logger.info("子进程已启动，等待完成")
            
            process.join()
            logger.info("子进程执行完成，获取结果")
            
            success, error = result_queue.get()
            logger.info(f"子进程执行结果: success={success}, error={error}")
            
            if not success:
                logger.error(f"访问平台失败: {error}")
                return {"success": True, "message": f"浏览器已打开，但访问平台时出现问题: {error}"}
            
            logger.info(f"成功打开账号 {account.username} 并访问 {account.account_type} 平台")
            return {"success": True, "message": f"成功打开账号并访问 {account.account_type} 平台"}
            
        except Exception as playwright_error:
            logger.error(f"Playwright操作出错: {str(playwright_error)}")
            logger.error(f"Playwright错误堆栈: {traceback.format_exc()}")
            return {"success": True, "message": f"浏览器已打开，但访问平台时出现问题: {str(playwright_error)}"}
            
    except HTTPException:
        # 重新抛出HTTPException，不做修改
        raise
    except Exception as e:
        logger.error(f"=== 打开账号时发生未预期的异常: {str(e)} ===")
        logger.error(f"异常类型: {type(e).__name__}")
        logger.error(f"异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")

async def close_bitbrowser(browser_id: str):
    """关闭 BitBrowser"""
    try:
        url = f"http://127.0.0.1:54345/browser/close"
        data = {"id": browser_id}
        headers = {"Content-Type": "application/json"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers)
            if response.status_code == 200:
                logger.info(f"成功关闭浏览器: {browser_id}")
            else:
                logger.error(f"关闭浏览器失败: {response.status_code} - {response.text}")
                
    except Exception as e:
        logger.error(f"关闭浏览器出错: {str(e)}")

def _close_browser_in_process(browser):
    """在进程中关闭浏览器和所有页面"""
    try:
        if not browser:
            return
            
        # 在同步上下文中关闭所有内容
        with sync_playwright() as playwright:
            try:
                # 关闭所有页面
                for context in browser.contexts:
                    try:
                        # 先关闭所有页面
                        pages = context.pages.copy()  # 创建页面列表的副本
                        for page in pages:
                            if page and not page.is_closed():
                                page.close()
                    except Exception as e:
                        logger.error(f"关闭页面时出错: {str(e)}")
                    
                    # 再关闭上下文
                    if not context.is_closed():
                        context.close()
                
                # 最后关闭浏览器
                if not browser.is_closed():
                    browser.close()
                    
            except Exception as e:
                logger.error(f"关闭浏览器时出错: {str(e)}")
    except Exception as e:
        logger.error(f"关闭浏览器程出错: {str(e)}")

def _check_status_process(browser_id: str, account_type: str, ws_url: str, result_queue: Queue):
    """在单独进程中检查账号状态"""
    browser = None
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(ws_url)
            context = browser.contexts[0]
            page = context.new_page()

            if account_type == "公众号":
                logger.info(f"正在检查公众号账号状态...")
                page.goto("https://mp.weixin.qq.com/")
                page.wait_for_load_state('networkidle')
                
                try:
                    # 使用更精确的选择器，查找"使用账号登录"按钮
                    login_button = page.get_by_role("link", name="使用账号登录")
                    is_login_visible = login_button.is_visible(timeout=5000)
                    
                    if is_login_visible:
                        logger.info(f"发现登录按钮，账号状态：不能正常打开")
                        result_queue.put((True, False))
                        # 状态不正常时不关闭浏览器
                        browser = None
                    else:
                        logger.info(f"未发现登录按钮，账号状态：能正常打开")
                        result_queue.put((True, True))
                        # 立即关闭浏览器
                        try:
                            page.close()
                            context.close()
                            browser.close()
                        except Exception as e:
                            logger.error(f"关闭浏览器时出错: {str(e)}")
                        browser = None
                except Exception as e:
                    logger.error(f"检查公众号登录状态时出错: {str(e)}")
                    result_queue.put((False, str(e)))
                    
            elif account_type == "头条号":
                logger.info(f"正在检查头条号账号状态...")
                page.goto("https://mp.toutiao.com/")
                page.wait_for_load_state('networkidle')
                
                try:
                    # 检查是否出现验证码登录标题
                    login_title = page.locator('div.web-login-union__login__form__title')
                    is_login_visible = login_title.is_visible(timeout=5000)
                    
                    if is_login_visible:
                        logger.info(f"发现验证码登录标题，账号状态：不能正常打开")
                        result_queue.put((True, False))
                        # 状态不正常时不关闭浏览器
                        browser = None
                    else:
                        logger.info(f"未发现验证码登录标题，账号状态：能正常打开")
                        result_queue.put((True, True))
                        # 立即关闭浏览器
                        try:
                            page.close()
                            context.close()
                            browser.close()
                        except Exception as e:
                            logger.error(f"关闭浏览器时出错: {str(e)}")
                        browser = None
                except Exception as e:
                    logger.error(f"检查头条号登录状态时出错: {str(e)}")
                    result_queue.put((False, str(e)))
                    
            elif account_type == "小红书":
                logger.info(f"正在检查小红书账号状态...")
                page.goto("https://creator.xiaohongshu.com/publish/publish?source=official&from=menu&target=image")
                page.wait_for_load_state('networkidle')
                
                try:
                    # 检查是否出现登录按钮或登录相关元素
                    # 小红书可能有多种登录状态指示器，这里检查常见的登录按钮
                    login_button = page.locator('button:has-text("登录")')
                    is_login_visible = login_button.is_visible(timeout=5000)
                    
                    if is_login_visible:
                        logger.info(f"发现登录按钮，账号状态：不能正常打开")
                        result_queue.put((True, False))
                        # 状态不正常时不关闭浏览器
                        browser = None
                    else:
                        logger.info(f"未发现登录按钮，账号状态：能正常打开")
                        result_queue.put((True, True))
                        # 立即关闭浏览器
                        try:
                            page.close()
                            context.close()
                            browser.close()
                        except Exception as e:
                            logger.error(f"关闭浏览器时出错: {str(e)}")
                        browser = None
                except Exception as e:
                    logger.error(f"检查小红书登录状态时出错: {str(e)}")
                    result_queue.put((False, str(e)))
    except Exception as e:
        logger.error(f"检查账号状态过程出错: {str(e)}")
        result_queue.put((False, str(e)))
    finally:
        if browser:  # 只在状态检查失败时尝试关闭浏览器
            try:
                page.close()
                context.close()
                browser.close()
            except Exception as e:
                logger.error(f"关闭浏览器时出错: {str(e)}")

async def check_account_status(browser_id: str, account_type: str) -> tuple[bool, bool]:
    """检查账号状态，返回 (是否成功检查, 账号是否可用)"""
    browser_data = await open_bitbrowser(browser_id)
    if not browser_data or not browser_data.get('ws'):
        return False, False

    try:
        result_queue = Queue()
        process = Process(
            target=_check_status_process,
            args=(browser_id, account_type, browser_data['ws'], result_queue)
        )
        process.start()
        process.join()

        success, result = result_queue.get()
        
        # 如果状态不正常，不关闭浏览器
        if success and not result:
            logger.info(f"账号状态不正常，保持浏览器打开")
            return True, False
            
        return True, result

    except Exception as e:
        logger.error(f"检查账号状态出错: {str(e)}")
        return False, False
    finally:
        if success and result:  # 只有在状态正常时才关闭浏览器
            try:
                await close_bitbrowser(browser_id)
            except Exception as e:
                logger.error(f"关闭浏览器出错: {str(e)}")
                # 不影响返回结果

@router.post("/refresh-status")
async def refresh_all_accounts_status(db: Session = Depends(get_db)):
    """刷新所有账号的状态"""
    try:
        accounts = db.query(Account).all()
        logger.info(f"开始检查 {len(accounts)} 个账号的状态...")
        
        # 按浏览器ID分组账号
        browser_groups = defaultdict(list)
        for account in accounts:
            browser_groups[account.browser_id].append(account)
        
        # 并行执行所有检查任务，但限制并发数量
        all_results = []
        semaphore = asyncio.Semaphore(3)  # 限制最多同时执行3个浏览器的检查
        
        async def check_with_semaphore(browser_id: str, accounts: list):
            async with semaphore:
                try:
                    return await check_browser_group(browser_id, accounts)
                except Exception as e:
                    logger.error(f"检查浏览器 {browser_id} 时出错: {str(e)}")
                    return [(account, False) for account in accounts]
        
        # 创建所有检查任务
        tasks = [
            check_with_semaphore(browser_id, browser_accounts)
            for browser_id, browser_accounts in browser_groups.items()
        ]
        
        # 使用 asyncio.gather 的 return_exceptions=True 选项来处理错误
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"任务执行出错: {str(result)}")
                continue
            if result:
                all_results.extend(result)
        
        # 更新数据库
        for account, can_login in all_results:
            account.can_login = can_login
            logger.info(f"账号 {account.username} 状态更新为: {'能正常打开' if can_login else '不能正常打开'}")
        
        db.commit()
        logger.info("所有账号状态检查完成")
        return {"success": True}
        
    except Exception as e:
        logger.error(f"刷新账号状态时出错: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

async def check_browser_group(browser_id: str, accounts: list) -> list:
    """检查同一浏览器下的所有账号"""
    results = []
    
    try:
        # 按顺序检查同一浏览器的不同账号
        for account in accounts:
            try:
                logger.info(f"正在检查账号 {account.username} ({account.account_type})...")
                check_success, can_login = await check_account_status(account.browser_id, account.account_type)
                
                # 只有在成功检查时才更新状态
                if check_success:
                    results.append((account, can_login))
                else:
                    # 检查失败时保持原状态
                    logger.warning(f"账号 {account.username} 状态检查失败，保持原状态")
                    results.append((account, account.can_login))
                
                # 如果状态不正常，等待一下再检查下一个账号
                if not can_login:
                    await asyncio.sleep(2)  # 给用户一些时间查看状态
                    continue
                    
                # 每次检查完一个正常账号后稍微等待一下，避免过于频繁的操作
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"检查账号 {account.username} 时出错: {str(e)}")
                # 出错时保持原状态
                results.append((account, account.can_login))
                
    except Exception as e:
        logger.error(f"检查浏览器组 {browser_id} 时出错: {str(e)}")
        # 如果整个浏览器组检查失败，保持所有账号原状态
        for account in accounts:
            results.append((account, account.can_login))
            
    return results

# 修改前端 JavaScript 代码，添加加载状态