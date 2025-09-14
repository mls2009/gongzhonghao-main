from playwright.sync_api import sync_playwright
import time

def automate_wechat_publish():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        try:
            # 访问微信公众平台
            print("正在访问微信公众平台...")
            page.goto("https://mp.weixin.qq.com/cgi-bin/home?t=home/index&token=1324782881&lang=zh_CN")
            
            print("等待页面加载完成...")
            page.wait_for_load_state('networkidle')
            
            print("点击内容管理...")
            page.wait_for_selector("//span[contains(text(), '内容管理')]", state="visible")
            page.click("//span[contains(text(), '内容管理')]")
            
            print("点击草稿箱...")
            page.wait_for_selector("span.weui-desktop-menu__name:has-text('草稿箱')", state="visible")
            page.click("span.weui-desktop-menu__name:has-text('草稿箱')")
            
            print("点击新的创作...")
            try:
                page.wait_for_selector("div.weui-desktop-card__inner:has-text('新的创作')", state="visible")
                page.click("div.weui-desktop-card__inner:has-text('新的创作')")
            except:
                print("尝试使用备选元素点击...")
                page.wait_for_selector('div.weui-desktop-card__inner[style="height: 234px;"][data-label-id="0"]', state="visible")
                page.click('div.weui-desktop-card__inner[style="height: 234px;"][data-label-id="0"]')
            print("点击写新文章...")
            # 等待新页面打开
            try:
                with context.expect_page() as new_page_info:
                    page.click("a:has-text('写新文章')")
                new_page = new_page_info.value
            except:
                print("尝试使用备选元素点击...")
                with context.expect_page() as new_page_info:
                    page.click("a:has-text('写新图文')")
                new_page = new_page_info.value
            
            # 等待新页面加载完成
            print("等待新页面加载...")
            new_page.wait_for_load_state('networkidle')
            new_page.bring_to_front()
            
            print("在新页面中查找导入按钮...")
            new_page.wait_for_selector("#js_import_file", state="visible", timeout=30000)
            new_page.click("#js_import_file")
            
            print("准备上传文件...")
            with new_page.expect_file_chooser() as fc_info:
                new_page.click("label[style*='opacity: 0']")
            file_chooser = fc_info.value
            file_chooser.set_files(r"E:\领导数据\简历输出\盘点4位东阳出生的市委书记，1人当过副省长，1人当过省长，1人官至省委书记（一）.docx")
            
            time.sleep(3)
            
            print("填写作者信息...")
            new_page.fill("#author", "仕途说")
            
            print("点击未声明...")
            new_page.click("div.js_unset_original_title")
            
            print("勾选已同意...")
            new_page.click("i.weui-desktop-icon-checkbox")
            
            print("点击确认...")
            new_page.click("button.weui-desktop-btn_primary:has-text('确定')")
            
            time.sleep(2)
            
            print("检查并处理广告区域...")
            try:
                # 检查广告区域是否存在
                ad_area = new_page.wait_for_selector('//*[@id="js_insert_ad_area"]/label/span', 
                                                   state="visible", 
                                                   timeout=5000)
                if ad_area:
                    print("发现广告区域，进行处理...")
                    # 点击第一个元素
                    new_page.click('//*[@id="js_insert_ad_area"]/label/div/span[3]')
                    time.sleep(2)  # 等待iframe加载
                    
                    print("等待iframe加载...")
                    # 等待并获取iframe
                    frame = new_page.wait_for_selector('iframe', state="visible", timeout=5000)
                    if frame:
                        # 获取iframe的内容
                        frame_element = frame.content_frame()
                        if frame_element:
                            print("切换到iframe内部...")
                            # 在iframe中点击确认按钮
                            try:
                                frame_element.click('button.btn.adui-button-base.adui-button-primary.adui-button-medium')
                            except Exception as e:
                                print(f"直接点击失败，尝试JavaScript方式: {str(e)}")
                                try:
                                    # 在iframe中使用JavaScript点击
                                    frame_element.evaluate('''() => {
                                        const buttons = Array.from(document.querySelectorAll('button'));
                                        const confirmBtn = buttons.find(btn => {
                                            const span = btn.querySelector('span.adui-button-content');
                                            return span && span.textContent === '确认';
                                        });
                                        
                                        if (confirmBtn) {
                                            confirmBtn.click();
                                            return;
                                        }
                                        throw new Error('在iframe中未找到确认按钮');
                                    }''')
                                except Exception as e:
                                    print(f"JavaScript点击也失败了: {str(e)}")
                                    # 打印iframe中的按钮信息
                                    buttons = frame_element.evaluate('''() => {
                                        return Array.from(document.querySelectorAll('button')).map(btn => ({
                                            text: btn.textContent.trim(),
                                            class: btn.className,
                                            spanContent: btn.querySelector('span')?.textContent.trim(),
                                            spanClass: btn.querySelector('span')?.className
                                        }));
                                    }''')
                                    print("iframe中的按钮:", buttons)
                                    raise Exception("无法在iframe中点击确认按钮")
                        else:
                            raise Exception("无法获取iframe内容")
                    else:
                        raise Exception("未找到iframe")
                    
                    time.sleep(1)
                    print("广告区域处理完成")
            except Exception as e:
                print(f"广告区域处理过程中出错: {str(e)}")
                print("继续执行后续步骤...")
            
            print("尝试点击从正文中选择...")
            try:
                # 使用JavaScript点击从正文选择按钮
                new_page.evaluate('''() => {
                    const links = Array.from(document.querySelectorAll('a'));
                    const link = links.find(a => a.textContent.includes('从正文选择'));
                    if (link) link.click();
                }''')
            except Exception as e:
                print(f"方式3失败: {str(e)}")
                print("尝试定位'从正文选择'按钮...")
                elements = new_page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a, button, div')).map(el => ({
                        tag: el.tagName,
                        text: el.textContent,
                        class: el.className,
                        visible: el.offsetParent !== null
                    })).filter(el => el.text.includes('从正文') || el.text.includes('选择'));
                }''')
                print("找到的相关元素：", elements)
                raise Exception("无法点击'从正文选择'按钮")
            
            print("等待图片加载...")
            time.sleep(1)

            # 使用JavaScript点击图片
            print("尝试选择图片...")
            try:
                new_page.evaluate('''() => {
                    const images = document.querySelectorAll('.card_mask_global');
                    if (images.length > 0) {
                        images[0].click();
                    }
                }''')
            except Exception as e:
                print(f"选择图片失败: {str(e)}")
                new_page.screenshot(path="image_selection_error.png")
                raise Exception("无法选择图片")


            print("点击下一步...")
            next_button = new_page.wait_for_selector("button.weui-desktop-btn_primary:has-text('下一步')", 
                                                   state="visible", 
                                                   timeout=5000)
            if next_button:
                next_button.click()
            else:
                raise Exception("找不到下一步按钮")

            print("点击确认...")
            confirm_button = new_page.wait_for_selector("button.weui-desktop-btn_primary:has-text('确认')", 
                                                      state="visible", 
                                                      timeout=5000)
            if confirm_button:
                confirm_button.click()
            else:
                raise Exception("找不到确认按钮")

            print("保存为草稿...")
            draft_button = new_page.wait_for_selector("button:has-text('保存为草稿')", 
                                                    state="visible", 
                                                    timeout=5000)
            if draft_button:
                draft_button.click()
            else:
                raise Exception("找不到保存为草稿按钮")

            print("等待保存完成...")
            time.sleep(3)
            print("操作完成！")

        except Exception as e:
            print(f"发生错误: {str(e)}")
            try:
                new_page.screenshot(path="error.png")
                print("\n当前页面元素状态：")
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
                print("页面元素状态：", elements)
            except:
                page.screenshot(path="error.png")
        finally:
            input("按回车键关闭浏览器...")
            browser.close()

if __name__ == "__main__":
    automate_wechat_publish()
