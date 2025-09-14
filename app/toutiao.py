from playwright.sync_api import sync_playwright
import time

def publish_article():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # 访问头条号
        page.goto("https://mp.toutiao.com/profile_v4/index")
        
        print("请在打开的浏览器中完成登录操作...")
        page.wait_for_selector('a[href="/profile_v4/graphic/publish"]')
        
        # 直接访问发文页面
        page.goto("https://mp.toutiao.com/profile_v4/graphic/publish")
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # 尝试点击 AI 助手
        try:
            ai_button = page.locator('path[fill-rule="evenodd"][clip-rule="evenodd"][fill="#999"]')
            box = ai_button.bounding_box()
            if box:
                page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                time.sleep(0.5)
                page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
            else:
                print("点击ai助手失败")
        except Exception as e:
            print("点击ai助手失败:", str(e))
        
        try:
            # 使用更精确的选择器定位文档导入按钮
            button = page.locator('button.syl-toolbar-button:has(svg path[d="M19 17v2a1 1 0 01-1 1H6a1 1 0 01-1-1V5a1 1 0 011-1h7l6 4v4"])')
            
            # 如果上面的选择器不工作，可以尝试这个备选方案
            # button = page.locator('button.syl-toolbar-button:has(svg[width="24"][height="24"]):has(g[stroke="#222"])')
            
            box = button.bounding_box()
            if box:
                # 模拟鼠标移动到按钮上
                page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                time.sleep(0.5)
                # 模拟鼠标点击
                page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
            else:
                print("未能找到文档导入按钮的位置")
            
            time.sleep(2)
            
            # 尝试多种方式定位文件上传输入框
            selectors = [
                'input[type="file"]',
                'input[accept=".doc,.docx,application/msword"]',
                'input[accept*="pdf"]',
                '//input[@type="file"]'  # xpath方��
            ]
            
            file_path = r"E:\领导数据\简历输出\盘点2位嘉兴出生的市委书记（一）.docx"
            upload_success = False
            
            for selector in selectors:
                try:
                    print(f"尝试使用选择器: {selector}")
                    if selector.startswith('//'):
                        # 对于xpath选择器
                        element = page.wait_for_selector(f"xpath={selector}", timeout=5000)
                    else:
                        element = page.wait_for_selector(selector, timeout=5000)
                        
                    if element:
                        page.set_input_files(selector, file_path)
                        upload_success = True
                        print("文件上传成功")
                        break
                except Exception as e:
                    print(f"选择器 {selector} 失败: {str(e)}")
                    continue
            
            if not upload_success:
                raise Exception("无法找到文件上传输入框")
            
            # 等待上传完成
            page.wait_for_load_state('networkidle')
            time.sleep(3)
            
            # 等待文档上传完成后的页面加载
            print("等待��面加载...")
            page.wait_for_load_state('networkidle')
            time.sleep(5)  # 增加等待时间确保页面完全加载
            
            # 使用locator定位并填写文章标题
            print("开始尝试输入文章标题...")
            try:
                title_element = page.locator('textarea[placeholder="请输入文章标题（2～30个字）"]')
                title_element.fill("盘点2位嘉兴出生的市委书记（一）")
                print("文章标题填写完成")
            except Exception as e:
                print(f"填写标题失败: {str(e)}")
                page.screenshot(path="title_error.png")
                raise Exception("无法找到或填写文章标题输入框")
            
            # 确保"头条首发"复选框被选中
            print("开始检查'头条首发'复选框状态...")
            try:
                checkbox_status = page.evaluate('''() => {
                    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
                    for (let checkbox of checkboxes) {
                        if (checkbox.checked) {
                            console.log('复选框已经被选中');
                            return true;
                        } else {
                            console.log('复选框未选中，执行点击');
                            checkbox.click();
                            return false;
                        }
                    }
                    return null;  // 没有找到复选框
                }''')
                
                if checkbox_status is True:
                    print("复选框已经是选中状态")
                elif checkbox_status is False:
                    print("已执行选中操作")
                    time.sleep(1)
                    # 验证是否成功选中
                    checkbox_selected = page.evaluate('''() => {
                        const checkbox = document.querySelector('input[type="checkbox"]');
                        return checkbox ? checkbox.checked : false;
                    }''')
                    if checkbox_selected:
                        print("确认复选框已被选中")
                    else:
                        print("警告：复选框可能未被正确选中")
                else:
                    print("未找到复选框元素")
                    page.screenshot(path="checkbox_not_found.png")
                    raise Exception("未找到复选框元素")

            except Exception as e:
                print(f"复选框操作失败: {str(e)}")
                page.screenshot(path="checkbox_error.png")
                raise

            time.sleep(2)  # 给予充足的时间让UI更新
            
            # 点击"封面"
            print("正在点击封面按钮...")
            page.click('div.article-cover-add')
            
            # 选择图片
            print("正在选择封面图片...")
            page.click('span.img-span')
            
            # 点击确认
            print("正在确认封面图片选择...")
            page.click('button.byte-btn-primary:has-text("确定")')
            
            # 等待封面设置完成
            print("等待封面设置完成...")
            time.sleep(2)
            
            # 点击"预览并发布"
            print("正在点击预览并发布按钮...")
            page.click('button.publish-btn:has-text("预览并发布")')
            
            # 等待预览页面加载
            print("等待预览页面加载...")
            time.sleep(2)
            
            # 点击"确认发布"
            print("正在点击确认发布按钮...")
            page.click('button.publish-btn:has-text("确认发布")')
            
            # 等待发布完成
            print("等待发布完成...")
            time.sleep(5)
            print("文章发布流程完成")
            
        except Exception as e:
            print(f"发生错误: {str(e)}")
            # 保存当前页面状态以便调试
            print("正在保存错误截图...")
            page.screenshot(path="error.png")
            print("正在保存页面HTML...")
            with open("error.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            
        finally:
            print("正在关闭浏览器...")
            browser.close()

if __name__ == "__main__":
    publish_article()