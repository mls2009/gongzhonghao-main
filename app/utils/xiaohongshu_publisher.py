import asyncio
import random
import os
import re
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import httpx
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class XiaohongshuPublisher:
    """小红书发布工具类"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
    
    async def open_browser_and_navigate(self, browser_id: str, account_id: int) -> bool:
        """
        步骤1: 打开对应账号的浏览器，导航到发布页面
        这与账号列表中的"打开小红书账号"操作流程相同
        """
        try:
            logger.info(f"步骤1: 打开小红书账号浏览器 (browser_id: {browser_id}, account_id: {account_id})")
            
            # 打开BitBrowser
            browser_data = await self._open_bitbrowser(browser_id)
            if not browser_data or not browser_data.get('ws'):
                logger.error("无法获取浏览器WebSocket URL")
                return False
            
            # 连接到浏览器
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.connect_over_cdp(browser_data['ws'])
            self.context = self.browser.contexts[0]
            self.page = await self.context.new_page()
            
            # 导航到小红书发布页面
            target_url = "https://creator.xiaohongshu.com/publish/publish?source=official&from=menu&target=image"
            await self.page.goto(target_url, wait_until='domcontentloaded', timeout=60000)

            # 不依赖 networkidle（页面有长连接），改为等待关键元素或可交互状态
            try:
                # 优先等待“上传图文”标签出现
                await self.page.wait_for_selector('div.creator-tab:has-text("上传图文")', timeout=30000)
            except Exception:
                # 退而求其次，等待上传 input 或正文编辑器出现
                try:
                    await self.page.wait_for_selector('input.upload-input[type="file"][multiple]', timeout=20000)
                except Exception:
                    try:
                        await self.page.wait_for_selector('div.tiptap.ProseMirror[contenteditable="true"]', timeout=20000)
                    except Exception:
                        # 仍未就绪，记录但不立即失败，让下一步自行探测
                        logger.warning("页面未检测到关键元素，但已完成基础加载，继续后续步骤")
            
            logger.info("成功打开小红书发布页面")
            return True
            
        except Exception as e:
            logger.error(f"打开浏览器和导航失败: {str(e)}")
            # 尝试保存页面截图与HTML以便排查
            try:
                if self.page:
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                    await self.page.screenshot(path=f"xiaohongshu_nav_error_{ts}.png")
                    html = await self.page.content()
                    with open(f"xiaohongshu_nav_error_{ts}.html", "w", encoding="utf-8") as f:
                        f.write(html)
            except Exception:
                pass
            await self._cleanup()
            return False
    
    async def click_upload_image_text(self) -> bool:
        """
        步骤2: 点击上传图文按钮
        需要避免点击隐藏的元素 (style="position: absolute; left: -9999px; top: -9999px;")
        目标元素: <div class="creator-tab"><span class="title">上传图文</span><div class="underline"></div></div>
        """
        try:
            logger.info("步骤2: 点击上传图文按钮")
            
            # 等待随机1-3秒
            await self._random_wait()
            
            # 查找所有包含"上传图文"的 creator-tab 元素（使用 :has-text 更稳妥）
            upload_tabs = await self.page.locator('div.creator-tab:has-text("上传图文")').all()
            
            logger.info(f"找到 {len(upload_tabs)} 个上传图文标签")
            
            # 找到可见且未被隐藏的元素并点击
            for tab in upload_tabs:
                try:
                    # 检查元素是否可见
                    is_visible = await tab.is_visible()
                    if not is_visible:
                        logger.debug("跳过不可见的上传图文按钮")
                        continue
                    
                    # 获取元素的style属性，检查是否被隐藏
                    style = await tab.get_attribute('style')
                    if style and ('left: -9999px' in style or 'position: absolute' in style):
                        logger.debug(f"跳过隐藏的上传图文按钮，style: {style}")
                        continue
                    
                    # 获取元素位置，确保不在屏幕外
                    box = await tab.bounding_box()
                    if box and (box['x'] < -1000 or box['y'] < -1000):
                        logger.debug(f"跳过位置异常的上传图文按钮，位置: x={box['x']}, y={box['y']}")
                        continue
                    
                    # 点击找到的可见元素
                    await tab.click()
                    logger.info("成功点击上传图文按钮")
                    return True
                    
                except Exception as e:
                    logger.warning(f"检查上传图文按钮时出错: {str(e)}")
                    continue
            
            # 兜底：直接尝试查找上传 input，如果存在则认为已在上传图文页面
            try:
                file_input = self.page.locator('input.upload-input[type="file"][multiple]')
                await file_input.wait_for(state='visible', timeout=5000)
                logger.info("未显式点击上传图文，但检测到上传输入框，继续")
                return True
            except Exception:
                pass

            logger.error("未找到可点击的上传图文按钮")
            return False
            
        except Exception as e:
            logger.error(f"点击上传图文按钮失败: {str(e)}")
            return False
    
    async def click_upload_image(self) -> bool:
        """
        步骤3: 跳过点击上传图片按钮，直接查找文件上传input元素
        文件上传元素: <input class="upload-input" type="file" multiple="" accept=".jpg,.jpeg,.png,.webp">
        """
        try:
            logger.info("步骤3: 查找文件上传输入框")
            
            # 等待随机1-3秒
            await self._random_wait()
            
            # 直接查找文件上传的 input 元素
            file_input = self.page.locator('input.upload-input[type="file"][multiple]')

            # 等待元素出现（放宽超时）
            await file_input.wait_for(state='attached', timeout=30000)
            
            logger.info("成功找到文件上传输入框")
            return True
            
        except Exception as e:
            logger.error(f"查找文件上传输入框失败: {str(e)}")
            return False
    
    async def upload_images_from_folder(self, folder_path: str) -> bool:
        """
        步骤4: 上传素材子文件夹里面的所有图片文件
        直接使用之前找到的上传input元素
        """
        try:
            logger.info(f"步骤4: 从文件夹上传图片 {folder_path}")
            
            # 等待随机1-3秒
            await self._random_wait()
            
            # 获取文件夹中的所有图片文件
            image_files = self._get_image_files_from_folder(folder_path)
            if not image_files:
                logger.error(f"文件夹中没有找到图片文件: {folder_path}")
                return False
            
            logger.info(f"找到 {len(image_files)} 个图片文件: {[os.path.basename(f) for f in image_files]}")
            
            # 使用精确的选择器查找文件上传输入框
            file_input = self.page.locator('input.upload-input[type="file"][multiple]')
            
            # 确保元素存在并可用（放宽超时）
            await file_input.wait_for(state='attached', timeout=30000)
            
            # 上传所有图片文件
            await file_input.set_input_files(image_files)
            
            logger.info(f"文件已设置到上传输入框，等待上传处理...")
            
            # 等待上传完成，可能需要等待一段时间让图片处理完成
            # 可以通过检查页面变化来确认上传状态
            await asyncio.sleep(5)  # 增加等待时间，确保图片上传处理完成
            
            logger.info(f"成功上传 {len(image_files)} 个图片文件")
            return True
            
        except Exception as e:
            logger.error(f"上传图片失败: {str(e)}")
            return False
    
    async def fill_title(self, material_title: str) -> bool:
        """
        步骤5: 填写标题
        标题格式: "日期+地区+央国企招聘信息差"
        例如: 2025年上海央国企最新招聘信息（9月5日） -> 9月5日上海央国企招聘信息差
        元素: <input class="d-text" type="text" placeholder="填写标题会有更多赞哦" value="">
        """
        try:
            logger.info(f"步骤5: 填写标题，原标题: {material_title}")
            
            # 等待随机1-3秒
            await self._random_wait()
            
            # 解析标题生成发布标题
            publish_title = self._generate_publish_title(material_title)
            logger.info(f"生成的发布标题: {publish_title}")
            
            # 找到标题输入框并填写
            title_input = self.page.locator('input.d-text[type="text"][placeholder="填写标题会有更多赞哦"]')
            await title_input.fill(publish_title)
            
            logger.info("成功填写标题")
            return True
            
        except Exception as e:
            logger.error(f"填写标题失败: {str(e)}")
            return False
    
    async def fill_content_description(self, content: str) -> bool:
        """
        步骤6: 填写正文描述
        元素: <div contenteditable="true" role="textbox" translate="no" class="tiptap ProseMirror" tabindex="0">
        填写内容包括正文(如果有的话)加上话题(不要忘了固定话题)
        """
        try:
            logger.info("步骤6: 填写正文描述")
            
            # 等待随机1-3秒
            await self._random_wait()
            
            # 找到内容编辑框并填写正文（不包含话题）
            content_editor = self.page.locator('div.tiptap.ProseMirror[contenteditable="true"]')
            await content_editor.fill(content)
            
            logger.info("成功填写正文描述")
            return True
            
        except Exception as e:
            logger.error(f"填写正文描述失败: {str(e)}")
            return False

    def _split_content_and_topics(self, content: str) -> (str, List[str]):
        """从组合内容中拆分正文与话题列表。
        规则：提取形如 #话题 的片段作为话题，其余作为正文（保留原有换行）。
        """
        try:
            # 抓取所有以 # 开头、以空白或行尾结束的片段
            hashtags = re.findall(r"#([^\s#]+)", content)
            topics = [f"#{h.strip()}" for h in hashtags if h.strip()]
            # 去除话题文本，余下作为正文
            desc = content
            for t in topics:
                desc = desc.replace(t, "")
            # 规范化正文（去掉多余空格）但保留换行
            desc = re.sub(r"[ \t]{2,}", " ", desc).strip()
            return desc, topics
        except Exception:
            return content, []

    async def type_topics(self, topics: List[str]) -> bool:
        """逐个输入话题：输入 '#话题' -> 随机等待3-5秒 -> 回车，直到所有话题输入完成。
        在输入前将光标移动到正文末尾，并先回车新起一段；
        额外加 End/Meta+End 与点击最后块元素以增强稳健性。
        """
        try:
            if not topics:
                return True
            editor = self.page.locator('div.tiptap.ProseMirror[contenteditable="true"]')
            await editor.scroll_into_view_if_needed()
            await editor.click()  # 聚焦到编辑器

            # 将光标移动到正文末尾，并另起一段
            try:
                handle = await editor.element_handle()
                if handle:
                    await self.page.evaluate(
                        "(el) => { el.focus(); const range = document.createRange(); range.selectNodeContents(el); range.collapse(false); const sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(range); }",
                        handle
                    )
                    # 尝试将光标进一步推到末尾（不同环境兼容）
                    try:
                        await self.page.keyboard.press('End')
                    except Exception:
                        pass
                    try:
                        # macOS 兼容键
                        await self.page.keyboard.press('Meta+End')
                    except Exception:
                        pass
                    # 尝试点击最后一个块级子元素，确保定位在最后
                    try:
                        last_block = editor.locator(':scope > *:last-child')
                        if await last_block.count() > 0:
                            await last_block.first.scroll_into_view_if_needed()
                            await last_block.first.click(position={"x": 1, "y": 1})
                            try:
                                await self.page.keyboard.press('End')
                            except Exception:
                                pass
                    except Exception:
                        pass
                    await self.page.keyboard.press('Enter')
            except Exception as e:
                logger.warning(f"设置光标到末尾失败，继续尝试输入话题: {e}")
            for t in topics:
                # 规范化单个话题，去除首尾空白/全角空格，确保单个#前缀
                s = str(t).replace('\u3000', ' ').strip()
                while s.startswith('#'):
                    s = s[1:].strip()
                if not s:
                    continue
                topic_text = f'#{s}'
                await editor.type(topic_text)
                await asyncio.sleep(random.uniform(3, 5))
                await self.page.keyboard.press('Enter')
            return True
        except Exception as e:
            logger.error(f"输入话题失败: {str(e)}")
            return False
    
    async def add_product_if_enabled(self, region: str, add_product: bool) -> bool:
        """
        步骤7: 根据设置决定是否添加商品
        如果add_product为False，则跳过此步骤
        如果为True，则执行添加商品流程
        """
        try:
            if not add_product:
                logger.info("步骤7: 跳过添加商品步骤")
                return True
            
            logger.info("步骤7: 添加商品")
            
            # 等待随机1-3秒
            await self._random_wait()
            
            # 点击添加商品按钮
            add_product_button = self.page.locator('span:has-text("添加商品")')
            await add_product_button.click()
            
            # 等待页面加载
            await asyncio.sleep(2)
            
            # 在搜索框中输入地区
            search_input = self.page.locator('input[placeholder="搜索商品ID 或 商品名称"]')
            await search_input.fill(region)
            
            # 等待搜索结果
            await asyncio.sleep(2)
            
            # 点击复选框 (选择第一个商品)
            checkbox = self.page.locator('span.d-checkbox-indicator').first
            await checkbox.click()
            
            # 等待页面响应
            await self._random_wait()
            
            # 点击保存按钮
            save_button = self.page.locator('span:has-text("保存")')
            await save_button.click()
            
            # 等待保存完成
            await asyncio.sleep(2)
            
            logger.info("成功添加商品")
            return True
            
        except Exception as e:
            logger.error(f"添加商品失败: {str(e)}")
            return False
    
    async def publish_complete(self) -> bool:
        """发布完成，点击发布按钮"""
        try:
            logger.info("最终步骤: 完成发布")
            
            # 等待随机1-3秒
            await self._random_wait()
            
            # 优先匹配你提供的元素结构：<span class="d-text ...">发布</span>
            try:
                span_publish = self.page.locator("span.d-text:has-text('发布')").first
                if await span_publish.count() > 0:
                    # 尝试找到可点击的最近祖先（button / role=button / 类名包含 d-button）
                    wrapper = span_publish.locator("xpath=ancestor-or-self::*[self::button or @role='button' or contains(@class,'d-button')][1]")
                    target = wrapper.first if await wrapper.count() > 0 else span_publish
                    await target.scroll_into_view_if_needed()
                    # 检查可见与禁用状态
                    if await target.is_visible():
                        aria_disabled = await target.get_attribute('aria-disabled')
                        disabled_attr = await target.get_attribute('disabled')
                        if not (aria_disabled == 'true' or disabled_attr is not None):
                            await target.click()
                            logger.info("成功点击发布按钮（span.d-text: 发布）")
                            await asyncio.sleep(3)
                            return True
            except Exception as e:
                logger.warning(f"点击 span.d-text 发布按钮时异常: {e}")

            # 备用：常规按钮/文本选择器
            publish_buttons = [
                "button:has-text('发布')",
                "button:has-text('立即发布')",
                "span:has-text('发布')",
                "span:has-text('立即发布')"
            ]
            for selector in publish_buttons:
                try:
                    button = self.page.locator(selector).first
                    if await button.is_visible():
                        await button.scroll_into_view_if_needed()
                        aria_disabled = await button.get_attribute('aria-disabled')
                        disabled_attr = await button.get_attribute('disabled')
                        if not (aria_disabled == 'true' or disabled_attr is not None):
                            await button.click()
                            logger.info(f"成功点击发布按钮（{selector}）")
                            await asyncio.sleep(3)
                            return True
                except Exception as e:
                    logger.debug(f"尝试点击 {selector} 失败: {e}")
            
            logger.error("未找到发布按钮")
            return False
            
        except Exception as e:
            logger.error(f"完成发布失败: {str(e)}")
            return False
    
    async def _open_bitbrowser(self, browser_id: str) -> Optional[Dict[str, Any]]:
        """打开BitBrowser并返回连接信息"""
        try:
            url = "http://127.0.0.1:54345/browser/open"
            json_data = {"id": browser_id}
            headers = {"Content-Type": "application/json"}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=json_data, headers=headers)
                response_data = response.json()
                
                if response_data.get('success'):
                    return response_data.get('data', {})
                else:
                    logger.error(f"BitBrowser API错误: {response_data.get('msg', '未知错误')}")
                    return None
                    
        except Exception as e:
            logger.error(f"打开BitBrowser失败: {str(e)}")
            return None
    
    def _get_image_files_from_folder(self, folder_path: str) -> List[str]:
        """获取文件夹中的所有图片文件"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        image_files = []
        
        try:
            folder = Path(folder_path)
            if not folder.exists():
                return []
                
            for file in folder.iterdir():
                if file.is_file() and file.suffix.lower() in image_extensions:
                    image_files.append(str(file))
            
            # 按文件名排序，确保顺序一致
            image_files.sort()
            
        except Exception as e:
            logger.error(f"读取文件夹图片失败: {str(e)}")
            
        return image_files
    
    def _generate_publish_title(self, material_title: str) -> str:
        """
        根据素材标题生成发布标题
        格式: "日期+地区+央国企招聘信息差"
        例如: 2025年上海央国企最新招聘信息（9月5日） -> 9月5日上海央国企招聘信息差
        """
        try:
            # 提取日期 (只要月日，不要年份)
            date_pattern = r'(\d+月\d+日)'
            date_match = re.search(date_pattern, material_title)
            date_str = date_match.group(1) if date_match else ""
            
            # 提取地区 (使用统一的提取方法)
            region_str = self._extract_region_from_title(material_title)
            
            # 组合标题
            title_parts = []
            if date_str:
                title_parts.append(date_str)
            title_parts.append(region_str)
            title_parts.append("央国企招聘信息差")
            
            return "".join(title_parts)
            
        except Exception as e:
            logger.error(f"生成发布标题失败: {str(e)}")
            return "央国企招聘信息差"
    
    def _extract_region_from_title(self, title: str) -> str:
        """
        从标题中提取地区信息
        规则: 提取"年"和"央国企"之间的文字作为区域
        例如: "2025年江苏央国企最新招聘信息" -> "江苏"
        """
        try:
            # 使用正则表达式提取"年"和"央国企"之间的内容
            # 匹配模式: 年 + 地区 + 央国企相关词汇
            pattern = r'年([^央国企]+?)(?:央国企|央企|国企)'
            match = re.search(pattern, title)
            
            if match:
                region = match.group(1).strip().replace(" ", "")
                logger.info(f"从标题 '{title}' 中提取到区域: '{region}'")
                return region
            
            # 如果没有匹配到标准格式，尝试备用方案：直接查找已知地区名
            known_regions = [
                '北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安', '南京', '苏州',
                '天津', '重庆', '青岛', '大连', '厦门', '宁波', '无锡', '长沙', '郑州', '合肥',
                '江苏', '浙江', '广东', '山东', '河北', '河南', '湖北', '湖南', '四川', '福建',
                '安徽', '江西', '辽宁', '黑龙江', '吉林', '山西', '陕西', '甘肃', '青海', '内蒙古',
                '新疆', '西藏', '宁夏', '海南', '云南', '贵州', '台湾', '香港', '澳门'
            ]
            
            for region in known_regions:
                if region in title:
                    logger.info(f"通过备用方案从标题 '{title}' 中找到区域: '{region}'")
                    return region
                    
            logger.warning(f"无法从标题 '{title}' 中提取区域信息，使用默认值")
            return "全国"
            
        except Exception as e:
            logger.error(f"提取区域信息时出错: {str(e)}")
            return "全国"
    
    async def _random_wait(self):
        """随机等待1-3秒"""
        wait_time = random.uniform(1, 3)
        await asyncio.sleep(wait_time)
    
    async def _cleanup(self):
        """清理资源"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"清理资源时出错: {str(e)}")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._cleanup()


async def publish_xiaohongshu_material(
    material_id: int,
    material_title: str, 
    folder_path: str,
    account_id: int,
    browser_id: str,
    content: str,
    topics: Optional[List[str]] = None,
    add_product: bool = False
) -> Dict[str, Any]:
    """
    完整的小红书素材发布流程
    
    Args:
        material_id: 素材ID
        material_title: 素材标题
        folder_path: 素材文件夹路径
        account_id: 账号ID
        browser_id: 浏览器ID
        content: 发布内容(包含正文和话题)
        add_product: 是否添加商品
    
    Returns:
        发布结果字典
    """
    publisher = XiaohongshuPublisher()
    
    try:
        logger.info(f"开始发布小红书素材: {material_title} (ID: {material_id})")
        
        # 步骤1: 打开浏览器并导航到发布页面
        if not await publisher.open_browser_and_navigate(browser_id, account_id):
            return {"success": False, "message": "打开浏览器失败"}
        
        # 步骤2: 点击上传图文
        if not await publisher.click_upload_image_text():
            return {"success": False, "message": "点击上传图文失败"}
        
        # 步骤3: 查找文件上传输入框
        if not await publisher.click_upload_image():
            return {"success": False, "message": "查找文件上传输入框失败"}
        
        # 步骤4: 上传图片文件
        if not await publisher.upload_images_from_folder(folder_path):
            return {"success": False, "message": "上传图片失败"}
        
        # 步骤5: 填写标题
        if not await publisher.fill_title(material_title):
            return {"success": False, "message": "填写标题失败"}
        
        # 步骤6: 填写正文描述 + 分步输入话题
        # 优先使用外部传入的话题列表；若未提供，则从 content 中解析
        desc_text = content
        topics_list: List[str] = topics or []
        if not topics_list:
            desc_text, topics_list = publisher._split_content_and_topics(content)
        if not await publisher.fill_content_description(desc_text):
            return {"success": False, "message": "填写正文描述失败"}
        if topics_list:
            ok_topics = await publisher.type_topics(topics_list)
            if not ok_topics:
                return {"success": False, "message": "输入话题失败"}
        
        # 步骤7: 根据设置添加商品(可选)
        region = publisher._extract_region_from_title(material_title)
        if not await publisher.add_product_if_enabled(region, add_product):
            return {"success": False, "message": "添加商品失败"}
        
        # 最终步骤: 完成发布
        if not await publisher.publish_complete():
            return {"success": False, "message": "完成发布失败"}
        
        logger.info(f"成功发布小红书素材: {material_title}")
        return {
            "success": True, 
            "message": f"成功发布素材: {material_title}",
            "material_id": material_id
        }
        
    except Exception as e:
        logger.error(f"发布小红书素材失败: {str(e)}")
        return {
            "success": False, 
            "message": f"发布失败: {str(e)}",
            "material_id": material_id
        }
    finally:
        await publisher._cleanup()
