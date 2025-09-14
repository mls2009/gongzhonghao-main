// 模板素材管理JavaScript文件
let currentTemplateId = null;
let templateState = {
    imageTemplateEnabled: false,
    contentTemplateEnabled: false,
    imageTemplateMode: 'random',
    contentTemplateMode: 'random',
    currentImageTemplateId: null,
    currentContentTemplateId: null
};

// Canvas 相关变量
let canvas = null;
let ctx = null;
let previewImage = null;
let customBackgroundImage = null; // 当前会话的自定义背景图片对象
let customBackgroundDataUrl = null; // 当前会话的自定义背景数据URL（用于保存到模板）

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('Template Materials JS loaded');
    initializeCanvasPreview();
    loadCurrentTemplateState();
    loadTemplateData();
    setupEventListeners();
    // 加载当前模板状态并应用到预览
    loadAndApplyCurrentTemplate();
});

// 初始化Canvas预览
function initializeCanvasPreview() {
    canvas = document.getElementById('preview-canvas');
    if (!canvas) {
        console.warn('Canvas element not found');
        return;
    }
    
    ctx = canvas.getContext('2d');
    // 修改为与发布一致的尺寸以确保设计准确性
    // 发布尺寸: 750x1000, 预览尺寸: 750x1000 (1:1比例)
    canvas.width = 750;
    canvas.height = 1000;
    
    // 通过CSS缩放显示以适应页面布局
    canvas.style.width = '300px';
    canvas.style.height = '400px';
    canvas.style.objectFit = 'contain';
    
    console.log('🎨 预览Canvas初始化: 750x1000 (与发布尺寸一致, CSS缩放显示为300x400)');
    
    // 设置默认样式
    ctx.fillStyle = '#f8f9fa';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#666';
    ctx.font = '40px Arial'; // 调整默认字体以适应750x1000画布
    ctx.textAlign = 'center';
    ctx.fillText('预览区域', canvas.width/2, canvas.height/2);
}

// 设置事件监听器
function setupEventListeners() {
    console.log('Setting up event listeners');
    
    // 模板类型切换
    const templateTypeRadios = document.querySelectorAll('input[name="template-type"]');
    templateTypeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            console.log('Template type changed to:', this.value);
            updatePreview();
        });
    });
    
    const contentModeRadios = document.querySelectorAll('input[name="contentTemplateMode"]');
    contentModeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            templateState.contentTemplateMode = this.value;
            updateTemplateState();
            console.log('Content template mode changed to:', this.value);
        });
    });
    
    // 文字样式按钮
    const styleButtons = document.querySelectorAll('.style-btn');
    console.log('Found style buttons:', styleButtons.length);
    styleButtons.forEach((btn, index) => {
        console.log(`Button ${index}:`, btn.textContent, 'data-style:', btn.dataset.style);
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Style button clicked:', this.textContent, this.dataset.style);
            // 移除所有active类
            styleButtons.forEach(b => b.classList.remove('active'));
            // 添加当前按钮的active类
            this.classList.add('active');
            console.log('Style changed to:', this.dataset.style);
            updatePreview();
        });
    });
    
    // 背景样式按钮 - 修复CSS选择器
    const bgButtons = document.querySelectorAll('.bg-btn');
    console.log('Found bg buttons:', bgButtons.length);
    bgButtons.forEach((btn, index) => {
        console.log(`BG Button ${index}:`, btn.textContent, 'data-bg:', btn.dataset.bg);
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Background button clicked:', this.textContent, this.dataset.bg);
            // 移除所有active类
            bgButtons.forEach(b => b.classList.remove('active'));
            // 添加当前按钮的active类
            this.classList.add('active');
            console.log('Background changed to:', this.dataset.bg);
            updatePreview();
        });
    });
    
    // 颜色选择器
    const colorPicker = document.getElementById('text-color-picker');
    if (colorPicker) {
        colorPicker.addEventListener('change', function() {
            console.log('Color changed to:', this.value);
            updatePreview();
        });
    }
    
    // 滑块控件
    const fontSize = document.getElementById('font-size');
    const lineHeight = document.getElementById('line-height');
    const maskOpacity = document.getElementById('mask-opacity');
    
    if (fontSize) {
        fontSize.addEventListener('input', function() {
            document.getElementById('font-size-value').textContent = this.value + 'px';
            updatePreview();
        });
    }
    if (lineHeight) {
        lineHeight.addEventListener('input', function() {
            document.getElementById('line-height-value').textContent = this.value;
            updatePreview();
        });
    }
    if (maskOpacity) {
        maskOpacity.addEventListener('input', function() {
            document.getElementById('mask-opacity-value').textContent = this.value;
            updatePreview();
        });
    }
    
    // 文字行数
    const textLinesRadios = document.querySelectorAll('input[name="text-lines"]');
    textLinesRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            console.log('Text lines changed to:', this.value);
            updatePreview();
        });
    });
    
    // 文字输入框
    const textInputs = document.querySelectorAll('input[id^="text-line-"]');
    textInputs.forEach(input => {
        input.addEventListener('input', function() {
            console.log('Text input changed:', this.id, this.value);
            updatePreview();
        });
    });
    
    // 背景图片上传
    const bgUpload = document.getElementById('bg-upload');
    if (bgUpload) {
        bgUpload.addEventListener('change', function(e) {
            console.log('Background file selected:', e.target.files[0]);
            handleBackgroundUpload(e.target.files[0]);
        });
    }

    // 背景图片URL输入（按回车使用）
    const bgUrlInput = document.getElementById('bg-url-input');
    if (bgUrlInput) {
        bgUrlInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                uploadBackgroundFromUrl();
            }
        });
    }
}

// 加载当前模板状态 - 简化版本
async function loadCurrentTemplateState() {
    try {
        const response = await fetch('/api/template-materials/current-templates');
        const data = await response.json();
        
        if (data.success) {
            console.log('Template state loaded:', data);
            // 更新当前图片模板显示
            updateCurrentTemplateDisplay();
            // 更新当前内容模板显示
            updateCurrentContentTemplateDisplay();
        }
    } catch (error) {
        console.error('加载模板状态失败:', error);
    }
}

// 更新当前模板显示
function updateCurrentTemplateDisplay(template = null) {
    const imageTemplateNameEl = document.getElementById('current-image-template-name');
    const contentTemplateNameEl = document.getElementById('current-content-template-name');
    
    if (template) {
        // 显示指定的模板
        if (imageTemplateNameEl) {
            imageTemplateNameEl.textContent = template.name;
            imageTemplateNameEl.className = 'font-medium text-indigo-600';
        }
        console.log('Current template updated to:', template.name);
    } else {
        // 从服务器获取当前模板状态
        loadCurrentTemplateStatus();
    }
}

// 更新当前内容模板显示
function updateCurrentContentTemplateDisplay(template = null) {
    const contentTemplateNameEl = document.getElementById('current-content-template-name');
    
    if (template) {
        // 显示指定的内容模板
        if (contentTemplateNameEl) {
            contentTemplateNameEl.textContent = template.name;
            contentTemplateNameEl.className = 'font-medium text-indigo-600';
        }
        console.log('Current content template updated to:', template.name);
    } else {
        // 从服务器获取当前内容模板状态
        loadCurrentContentTemplateStatus();
    }
}

// 加载当前模板状态
async function loadCurrentTemplateStatus() {
    try {
        const response = await fetch('/api/template-materials/get-template-status');
        const data = await response.json();
        
        const imageTemplateNameEl = document.getElementById('current-image-template-name');
        if (imageTemplateNameEl) {
            if (data.has_template) {
                imageTemplateNameEl.textContent = data.template_name;
                imageTemplateNameEl.className = 'font-medium text-indigo-600';
            } else {
                imageTemplateNameEl.textContent = '未指定';
                imageTemplateNameEl.className = 'font-medium text-gray-500';
            }
        }
        
        console.log('Template status loaded:', data);
    } catch (error) {
        console.error('Failed to load template status:', error);
    }
}

// 加载当前内容模板状态
async function loadCurrentContentTemplateStatus() {
    try {
        const response = await fetch('/api/template-materials/current-templates');
        const data = await response.json();
        
        const contentTemplateNameEl = document.getElementById('current-content-template-name');
        if (contentTemplateNameEl && data.success) {
            const contentMode = data.content_template_mode;
            if (contentMode && !contentMode.is_random_mode && contentMode.current_template_name) {
                // 指定模板模式
                contentTemplateNameEl.textContent = contentMode.current_template_name;
                contentTemplateNameEl.className = 'font-medium text-indigo-600';
            } else if (contentMode && contentMode.is_random_mode) {
                // 随机模式
                contentTemplateNameEl.textContent = '随机模式';
                contentTemplateNameEl.className = 'font-medium text-purple-600';
            } else {
                // 未指定状态
                contentTemplateNameEl.textContent = '未指定';
                contentTemplateNameEl.className = 'font-medium text-gray-500';
            }
        }
        
        console.log('Content template status loaded:', data);
    } catch (error) {
        console.error('Failed to load content template status:', error);
    }
}

// 应用模板到预览
async function applyTemplateToPreview(template) {
    if (!canvas || !ctx) {
        console.warn('Canvas not available for preview');
        return;
    }
    
    console.log('=== APPLYING TEMPLATE TO PREVIEW ===');
    console.log('Template:', template);
    console.log('Current customBackgroundImage:', !!customBackgroundImage);
    
    // 清除现有选择，应用模板设置
    // 设置模板类型
    const templateTypeRadio = document.querySelector(`input[name="template-type"][value="${template.template_type}"]`);
    if (templateTypeRadio) {
        templateTypeRadio.checked = true;
        console.log(`Template type set to: ${template.template_type}`);
    } else {
        console.warn(`Template type radio not found: ${template.template_type}`);
    }
    
    // 设置文字样式
    const styleButtons = document.querySelectorAll('.style-btn');
    let styleSet = false;
    styleButtons.forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.style === template.text_style) {
            btn.classList.add('active');
            styleSet = true;
        }
    });
    console.log(`Text style set to: ${template.text_style}, found: ${styleSet}`);
    
    // 设置背景样式
    const bgButtons = document.querySelectorAll('.bg-btn');
    let bgSet = false;
    bgButtons.forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.bg === template.background_style) {
            btn.classList.add('active');
            bgSet = true;
        }
    });
    console.log(`Background style set to: ${template.background_style}, found: ${bgSet}`);
    
    // 设置颜色
    const colorPicker = document.getElementById('text-color-picker');
    if (colorPicker) colorPicker.value = template.text_color;
    
    // 设置字体大小
    const fontSize = document.getElementById('font-size');
    if (fontSize) {
        fontSize.value = template.font_size;
        updateFontSizeValue(template.font_size);
    }
    
    // 设置行高
    const lineHeight = document.getElementById('line-height');
    if (lineHeight) {
        lineHeight.value = template.line_height;
        updateLineHeightValue(template.line_height);
    }
    
    // 设置遮罩透明度
    const maskOpacity = document.getElementById('mask-opacity');
    if (maskOpacity) {
        maskOpacity.value = template.mask_opacity;
        updateMaskOpacityValue(template.mask_opacity);
    }
    
    // 设置文字行数
    const textLinesRadio = document.querySelector(`input[name="text-lines"][value="${template.text_lines}"]`);
    if (textLinesRadio) textLinesRadio.checked = true;
    
    // 显示第四行文本框如果需要
    const textLine4 = document.getElementById('text-line-4');
    if (textLine4) {
        if (template.text_lines === 4) {
            textLine4.classList.remove('hidden');
        } else {
            textLine4.classList.add('hidden');
        }
    }
    
    // 如果模板包含自定义背景（data URL），先加载到当前会话
    try {
        if (template && typeof template.custom_background_path === 'string' && template.custom_background_path.startsWith('data:image')) {
            if (customBackgroundDataUrl !== template.custom_background_path) {
                console.log('Loading template custom background data URL into session...');
                await setCustomBackgroundFromDataUrl(template.custom_background_path);
            }
        }
    } catch (e) {
        console.warn('Failed to preload template custom background:', e);
    }

    // 强制更新预览，传入模板参数以确保正确渲染
    console.log('About to call updatePreviewWithTemplate...');
    try {
        updatePreviewWithTemplate(template);
        console.log('=== TEMPLATE APPLIED TO PREVIEW SUCCESSFULLY ===');
    } catch (error) {
        console.error('Error updating preview with template:', error);
        console.log('Falling back to regular updatePreview...');
        // 如果出错，回退到普通预览更新
        updatePreview();
    }
}

// 使用模板参数更新预览
function updatePreviewWithTemplate(template) {
    if (!canvas || !ctx) return;
    
    console.log('Updating preview with template:', template);
    
    // 强制重置Canvas状态
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0); // 重置变换矩阵
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.restore();
    
    // 使用模板参数而不是DOM元素的值
    const templateType = template.template_type || 'insert';
    const textStyle = template.text_style || 'gold';
    const textColor = template.text_color || '#2c3e50';
    const backgroundStyle = template.background_style || 'minimal_gradient';
    const fontSize = parseInt(template.font_size || 100); // 调整默认字体大小以适应750x1000画布
    const textLines = parseInt(template.text_lines || 3);
    
    // 绘制背景，传入完整的模板信息
    drawBackground(backgroundStyle, templateType, template);
    
    // 绘制示例文本
    drawSampleTextWithTemplate(textStyle, textColor, fontSize, textLines, templateType, template);
    
    console.log('Preview updated with template:', template.name);
}

// 使用模板参数绘制文本
function drawSampleTextWithTemplate(textStyle, textColor, fontSize, textLines, templateType, template) {
    console.log('=== DRAWING SAMPLE TEXT WITH TEMPLATE ===');
    console.log('Parameters:', {textStyle, textColor, fontSize, textLines, templateType});
    console.log('Canvas context available:', !!ctx);
    
    // 获取实际文本输入
    const texts = [];
    for (let i = 1; i <= textLines; i++) {
        const input = document.getElementById(`text-line-${i}`);
        if (input && input.value.trim()) {
            texts.push(input.value.trim());
        }
    }
    console.log('Input texts found:', texts);
    
    // 如果没有输入文本，使用默认示例
    if (texts.length === 0) {
        texts.push('2025年9月6日');
        texts.push('北京国企');
        texts.push('招聘信息差');
        if (textLines === 4) {
            texts.push('右划更多👉🏻');
        }
        console.log('Using default texts:', texts);
    }
    
    // 设置字体样式 - 包含金色沉稳样式
    let fontFamily = 'Arial, "Helvetica Neue", sans-serif';
    let fontWeight = 'normal';
    let shadowEffect = false;
    let gradientEffect = false;
    
    if (textStyle === 'gold' || textStyle === 'gold_stable') {
        fontWeight = 'bold';
        fontFamily = '"Times New Roman", serif';
        shadowEffect = true;
        gradientEffect = true;
    } else if (textStyle.includes('handwritten')) {
        fontFamily = 'cursive';
        fontWeight = '500';
    }
    
    ctx.font = `${fontWeight} ${fontSize}px ${fontFamily}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    
    const lineHeightValue = parseFloat(template.line_height || 1.2);
    const lineHeight = fontSize * lineHeightValue;
    const totalHeight = (texts.length - 1) * lineHeight;
    const startY = (canvas.height - totalHeight) / 2;
    
    // 如果是覆盖模式，添加背景蒙版
    if (templateType === 'overlay') {
        const maskOpacityValue = parseFloat(template.mask_opacity || 0);
        if (maskOpacityValue > 0) {
            ctx.save();
            ctx.fillStyle = `rgba(0, 0, 0, ${maskOpacityValue})`;
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.restore();
        }
    }
    
    // 绘制文本（包含更多手写样式变体）
    texts.forEach((text, index) => {
        const y = startY + index * lineHeight;

        if (textStyle === 'gold') {
            ctx.font = `bold ${fontSize}px "Times New Roman", serif`;
            ctx.save();
            ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
            ctx.fillText(text, canvas.width / 2 + 2, y + 2);
            ctx.restore();

            const gradient = ctx.createLinearGradient(0, y - fontSize/2, 0, y + fontSize/2);
            gradient.addColorStop(0, '#FFD700');
            gradient.addColorStop(0.5, '#FFA500');
            gradient.addColorStop(1, '#FF8C00');
            ctx.fillStyle = gradient;
            ctx.fillText(text, canvas.width / 2, y);
            ctx.strokeStyle = '#B8860B';
            ctx.lineWidth = 1;
            ctx.strokeText(text, canvas.width / 2, y);
        } else if (textStyle === 'gold_stable') {
            ctx.font = `bold ${fontSize}px "Times New Roman", serif`;
            ctx.save();
            ctx.shadowColor = 'rgba(139, 69, 19, 0.5)';
            ctx.shadowBlur = 4;
            ctx.shadowOffsetX = 2;
            ctx.shadowOffsetY = 2;
            const gradient = ctx.createLinearGradient(0, y - fontSize/2, 0, y + fontSize/2);
            gradient.addColorStop(0, '#FFD700');
            gradient.addColorStop(0.5, '#FFA500');
            gradient.addColorStop(1, '#FF8C00');
            ctx.fillStyle = gradient;
            ctx.strokeStyle = '#8B4513';
            ctx.lineWidth = 2;
            ctx.strokeText(text, canvas.width / 2, y);
            ctx.fillText(text, canvas.width / 2, y);
            ctx.restore();
        } else if (textStyle === 'handwritten_elegant') {
            ctx.font = `500 ${fontSize}px cursive`;
            ctx.fillStyle = textColor;
            ctx.fillText(text, canvas.width / 2, y);
        } else if (textStyle === 'handwritten_warm') {
            ctx.save();
            ctx.font = `500 ${fontSize}px cursive`;
            ctx.shadowColor = 'rgba(255, 140, 0, 0.35)';
            ctx.shadowBlur = 6;
            ctx.fillStyle = textColor;
            ctx.fillText(text, canvas.width / 2, y);
            ctx.restore();
        } else if (textStyle === 'handwritten_flowing') {
            ctx.save();
            ctx.font = `italic 500 ${fontSize}px cursive`;
            ctx.translate(canvas.width / 2, y);
            ctx.transform(1, 0, -0.2, 1, 0, 0);
            ctx.fillStyle = textColor;
            ctx.fillText(text, 0, 0);
            ctx.restore();
        } else if (textStyle === 'handwritten_delicate') {
            ctx.save();
            // 使用中文黑体/粗体字体族，而非简单加粗
            ctx.font = `900 ${fontSize}px "SimHei", "Heiti SC", "STHeiti", "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif`;
            ctx.fillStyle = textColor;
            ctx.fillText(text, canvas.width / 2, y);
            ctx.restore();
        } else if (textStyle === 'handwritten_playful') {
            ctx.save();
            ctx.font = `600 ${fontSize}px cursive`;
            const angle = (index % 2 === 0 ? -0.03 : 0.03);
            ctx.translate(canvas.width / 2, y);
            ctx.rotate(angle);
            ctx.fillStyle = textColor;
            ctx.fillText(text, 0, 0);
            ctx.restore();
        } else if (textStyle === 'handwritten_artistic') {
            ctx.save();
            ctx.font = `600 ${fontSize}px cursive`;
            const g = ctx.createLinearGradient(0, y - fontSize, canvas.width, y + fontSize);
            g.addColorStop(0, '#ff5f6d');
            g.addColorStop(0.5, '#ffc371');
            g.addColorStop(1, '#6a11cb');
            ctx.fillStyle = g;
            ctx.strokeStyle = 'rgba(0,0,0,0.15)';
            ctx.lineWidth = 2;
            ctx.strokeText(text, canvas.width / 2, y);
            ctx.fillText(text, canvas.width / 2, y);
            ctx.restore();
        } else if (textStyle === 'handwritten_casual') {
            ctx.save();
            ctx.font = `normal 400 ${fontSize}px cursive`;
            ctx.fillStyle = textColor;
            ctx.fillText(text, canvas.width / 2, y);
            ctx.restore();
        } else {
            if (templateType === 'overlay') {
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 3;
                ctx.strokeText(text, canvas.width / 2, y);
            }
            ctx.fillStyle = textColor;
            ctx.fillText(text, canvas.width / 2, y);
        }
    });
    console.log('=== TEXT DRAWING WITH TEMPLATE COMPLETED ===');
}

// 加载模板数据
async function loadTemplateData() {
    await loadImageTemplates();
    await loadContentTemplates();
}

// 加载图片模板列表
async function loadImageTemplates() {
    try {
        const response = await fetch('/api/template-materials/image-templates');
        const data = await response.json();
        
        // API直接返回数组，不是{success, data}格式
        if (Array.isArray(data)) {
            renderImageTemplatesList(data);
            console.log('Image templates loaded:', data.length);
        } else if (data.success) {
            // 备用：如果API返回{success, data}格式
            renderImageTemplatesList(data.data);
            console.log('Image templates loaded:', data.data.length);
        }
    } catch (error) {
        console.error('加载图片模板失败:', error);
    }
}

// 加载内容模板列表
async function loadContentTemplates() {
    try {
        const response = await fetch('/api/template-materials/content-templates');
        const data = await response.json();
        
        // API直接返回数组，不是{success, data}格式
        if (Array.isArray(data)) {
            renderContentTemplatesList(data);
            console.log('Content templates loaded:', data.length);
        } else if (data.success) {
            // 备用：如果API返回{success, data}格式
            renderContentTemplatesList(data.data);
            console.log('Content templates loaded:', data.data.length);
        }
    } catch (error) {
        console.error('加载内容模板失败:', error);
    }
}

// 渲染图片模板列表
function renderImageTemplatesList(templates) {
    const container = document.getElementById('template-list');
    if (!container) return;
    
    if (templates.length === 0) {
        container.innerHTML = '<div class="text-gray-500 text-center py-4">暂无模板</div>';
        return;
    }
    
    container.innerHTML = templates.map(template => `
        <div class="flex justify-between items-center p-3 bg-gray-50 rounded mb-2">
            <div>
                <div class="font-medium text-gray-900">${template.name}</div>
                <div class="text-sm text-gray-500">
                    ${template.template_type === 'insert' ? '插入模式' : '覆盖模式'} | 
                    ${template.font_size}px | 
                    ${template.text_lines}行
                </div>
            </div>
            <div class="flex space-x-2">
                <button onclick="applyImageTemplate(${template.id})" 
                        class="text-indigo-600 hover:text-indigo-900 text-sm">
                    应用
                </button>
                <button onclick="deleteImageTemplate(${template.id})" 
                        class="text-red-600 hover:text-red-900 text-sm">
                    删除
                </button>
            </div>
        </div>
    `).join('');
}

// 渲染内容模板列表
function renderContentTemplatesList(templates) {
    const container = document.getElementById('content-template-list');
    if (!container) return;
    
    if (templates.length === 0) {
        container.innerHTML = '<div class="text-gray-500 text-center py-4">暂无内容模板</div>';
        return;
    }
    
    container.innerHTML = templates.map(template => `
        <div class="flex justify-between items-center p-3 bg-gray-50 rounded mb-2">
            <div>
                <div class="font-medium text-gray-900">${template.name}</div>
                <div class="text-sm text-gray-500">
                    话题数量: ${template.topic_count} | 
                    随机描述: ${template.use_random_description ? '是' : '否'}
                </div>
            </div>
            <div class="flex space-x-2">
                <button onclick="applyContentTemplate(${template.id})" 
                        class="text-indigo-600 hover:text-indigo-900 text-sm">
                    应用
                </button>
                <button onclick="deleteContentTemplate(${template.id})" 
                        class="text-red-600 hover:text-red-900 text-sm">
                    删除
                </button>
            </div>
        </div>
    `).join('');
}

// 应用图片模板
async function applyImageTemplate(templateId) {
    try {
        console.log('Applying image template:', templateId);
        
        // 1. 先获取模板详细信息
        const templateResponse = await fetch(`/api/template-materials/image-templates`);
        const templates = await templateResponse.json();
        const template = templates.find(t => t.id === templateId);
        
        if (!template) {
            showAlert('模板不存在', 'error');
            return;
        }
        
        // 2. 应用模板到后端
        const response = await fetch(`/api/template-materials/apply-image-template/${templateId}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        if (result.success) {
            console.log('Template applied successfully:', template.name);
            
            // 3. 更新预览
            await applyTemplateToPreview(template);
            
            // 4. 更新当前模板显示
            updateCurrentTemplateDisplay(template);
            
            // 5. 通知其他页面模板状态已更改
            notifyTemplateStatusChange();
            
            showAlert(`已应用模板: ${template.name}`, 'success');
        } else {
            showAlert('应用失败: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('Apply image template error:', error);
        showAlert('应用失败', 'error');
    }
}

// 应用内容模板
async function applyContentTemplate(templateId) {
    try {
        console.log('Applying content template:', templateId);
        
        // 1. 先获取模板详细信息
        const templateResponse = await fetch('/api/template-materials/content-templates');
        const templates = await templateResponse.json();
        const template = Array.isArray(templates) ? templates.find(t => t.id === templateId) : templates.data?.find(t => t.id === templateId);
        
        if (!template) {
            showAlert('内容模板不存在', 'error');
            return;
        }
        
        // 2. 应用模板到后端
        const response = await fetch(`/api/template-materials/apply-content-template/${templateId}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        if (result.success) {
            console.log('Content template applied successfully:', template.name);
            
            // 3. 生成并显示内容预览
            await generateContentPreviewWithTemplate(templateId);
            
            // 4. 更新当前内容模板显示
            updateCurrentContentTemplateDisplay(template);
            
            // 5. 通知其他页面模板状态已更改
            notifyTemplateStatusChange();
            
            showAlert(`已应用内容模板: ${template.name}`, 'success');
        } else {
            showAlert('应用失败: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('Apply content template error:', error);
        showAlert('应用失败', 'error');
    }
}

// 预览功能 - 支持金色沉稳样式
function updatePreview() {
    if (!canvas || !ctx) return;
    
    // 清除canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const templateType = document.querySelector('input[name="template-type"]:checked')?.value || 'insert';
    const activeStyleBtn = document.querySelector('.style-btn.active');
    const textStyle = activeStyleBtn?.dataset.style || 'gold';
    const textColor = document.getElementById('text-color-picker')?.value || '#2c3e50';
    const activeBgBtn = document.querySelector('.bg-btn.active');
    const backgroundStyle = activeBgBtn?.dataset.bg || 'minimal_gradient';
    const fontSize = parseInt(document.getElementById('font-size')?.value || '100'); // 调整默认字体大小以适应750x1000画布
    const textLinesRadio = document.querySelector('input[name="text-lines"]:checked');
    const textLines = parseInt(textLinesRadio?.value || '3');
    
    // 显示/隐藏第四行文本框
    const textLine4 = document.getElementById('text-line-4');
    if (textLine4) {
        if (textLines === 4) {
            textLine4.classList.remove('hidden');
        } else {
            textLine4.classList.add('hidden');
        }
    }
    
    // 绘制背景（普通预览模式，无模板参数）
    drawBackground(backgroundStyle, templateType);
    
    // 绘制示例文本
    drawSampleText(textStyle, textColor, fontSize, textLines, templateType);
}

function drawBackground(style, templateType, template = null) {
    const hasCustomBgPath = template && template.custom_background_path;
    console.log('Drawing background - Style:', style, 'TemplateType:', templateType, 'Has custom BG var:', !!customBackgroundImage, 'Template has custom BG path:', hasCustomBgPath);

    // 仅在未应用具体模板时，优先使用当前会话自定义背景
    if (!template && customBackgroundImage) {
        console.log('Using session custom background image for ad-hoc preview');
        drawCustomBackgroundImage(customBackgroundImage);
        return;
    }
    
    if (templateType === 'overlay') {
        // 覆盖模式：根据模板设定智能选择背景
        if (hasCustomBgPath && customBackgroundImage) {
            console.log('Using current session custom background for overlay mode (template requires custom bg)');
            drawCustomBackgroundImage(customBackgroundImage);
        } else if (hasCustomBgPath) {
            console.log('Template has custom background path but no current image - showing enhanced example background');
            // 模板有自定义背景路径但当前会话没有图片，显示增强的示例背景
            ctx.fillStyle = '#e8e8e8';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // 添加更真实的示例图片内容
            ctx.fillStyle = '#d0d0d0';
            ctx.fillRect(15, 40, canvas.width - 30, 100);
            ctx.fillRect(15, 160, canvas.width - 30, 80);
            ctx.fillRect(15, 260, canvas.width - 30, 100);
            
            ctx.fillStyle = '#c0c0c0';
            ctx.fillRect(25, 50, 60, 80);
            ctx.fillRect(canvas.width - 85, 50, 60, 80);
            
            // 添加示例图片文字
            ctx.fillStyle = '#888';
            ctx.font = '14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('模板预览 - 覆盖模式', canvas.width / 2, canvas.height / 2 - 20);
            ctx.fillText('(实际使用时会覆盖在您的图片上)', canvas.width / 2, canvas.height / 2 + 20);
        } else {
            console.log('Using simple example background for overlay mode');
            // 没有自定义背景时显示简单示例图片背景
            ctx.fillStyle = '#f0f0f0';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            ctx.fillStyle = '#ddd';
            ctx.fillRect(20, 50, canvas.width - 40, 120);
            ctx.fillRect(20, 200, canvas.width - 40, 80);
            ctx.fillRect(20, 300, canvas.width - 40, 60);
            
            ctx.fillStyle = '#999';
            ctx.font = '14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('示例图片内容', canvas.width / 2, canvas.height / 2 - 40);
            ctx.fillText('(上传背景图片查看覆盖效果)', canvas.width / 2, canvas.height / 2 + 40);
        }
        return;
    }
    
    // 插入模式：如模板含自定义背景且已加载，则优先使用该背景；否则使用预设背景样式
    if (templateType === 'insert') {
        if (hasCustomBgPath && customBackgroundImage) {
            console.log('Insert mode - using template custom background image');
            drawCustomBackgroundImage(customBackgroundImage);
            return;
        }
        console.log('Insert mode - using preset background:', style);
        // 插入模式使用预设背景样式
        switch (style) {
            case 'clean_solid':
                ctx.fillStyle = '#f8f9fa';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                break;
            case 'minimal_gradient':
                const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
                gradient.addColorStop(0, '#667eea');
                gradient.addColorStop(1, '#764ba2');
                ctx.fillStyle = gradient;
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                break;
            case 'subtle_texture':
                ctx.fillStyle = '#f5f5f5';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = 'rgba(200, 200, 200, 0.3)';
                for (let x = 0; x < canvas.width; x += 50) {
                    for (let y = 0; y < canvas.height; y += 50) {
                        if ((x + y) % 100 === 0) {
                            ctx.fillRect(x, y, 25, 25);
                        }
                    }
                }
                break;
            case 'soft_blur':
                const blurGradient = ctx.createRadialGradient(canvas.width/2, canvas.height/2, 0, canvas.width/2, canvas.height/2, canvas.width);
                blurGradient.addColorStop(0, '#ff9a9e');
                blurGradient.addColorStop(1, '#fecfef');
                ctx.fillStyle = blurGradient;
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                break;
            case 'geometric_minimal':
                ctx.fillStyle = '#ffffff';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.strokeStyle = '#e1e5e9';
                ctx.lineWidth = 2;
                // 绘制几何图形
                for (let i = 0; i < 5; i++) {
                    ctx.strokeRect(50 + i * 30, 50 + i * 40, canvas.width - 100 - i * 60, canvas.height - 100 - i * 80);
                }
                break;
            case 'paper_texture':
                ctx.fillStyle = '#faf8f5';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                // 添加纸质纹理效果
                ctx.fillStyle = 'rgba(139, 137, 120, 0.1)';
                for (let i = 0; i < 1000; i++) {
                    const x = Math.random() * canvas.width;
                    const y = Math.random() * canvas.height;
                    ctx.fillRect(x, y, 1, 1);
                }
                break;
            case 'gradient_fade':
                const fadeGradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
                fadeGradient.addColorStop(0, '#74b9ff');
                fadeGradient.addColorStop(0.5, '#0984e3');
                fadeGradient.addColorStop(1, '#2d3436');
                ctx.fillStyle = fadeGradient;
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                break;
            case 'clean_lines':
                ctx.fillStyle = '#ffffff';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.strokeStyle = '#ddd';
                ctx.lineWidth = 1;
                // 绘制简洁线条
                for (let i = 0; i < canvas.width; i += 100) {
                    ctx.beginPath();
                    ctx.moveTo(i, 0);
                    ctx.lineTo(i, canvas.height);
                    ctx.stroke();
                }
                for (let i = 0; i < canvas.height; i += 100) {
                    ctx.beginPath();
                    ctx.moveTo(0, i);
                    ctx.lineTo(canvas.width, i);
                    ctx.stroke();
                }
                break;
            default:
                const defaultGradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
                defaultGradient.addColorStop(0, '#4facfe');
                defaultGradient.addColorStop(1, '#00f2fe');
                ctx.fillStyle = defaultGradient;
                ctx.fillRect(0, 0, canvas.width, canvas.height);
        }
    }
}

function drawSampleText(textStyle, textColor, fontSize, textLines, templateType) {
    // 获取实际文本输入
    const texts = [];
    for (let i = 1; i <= textLines; i++) {
        const input = document.getElementById(`text-line-${i}`);
        if (input && input.value.trim()) {
            texts.push(input.value.trim());
        }
    }
    
    // 如果没有输入文本，使用默认示例
    if (texts.length === 0) {
        texts.push('2025年9月6日');
        texts.push('北京国企');
        texts.push('招聘信息差');
        if (textLines === 4) {
            texts.push('右划更多👉🏻');
        }
    }
    
    // 公共字体基线
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    
    const lineHeightValue = parseFloat(document.getElementById('line-height')?.value || '1.2');
    const lineHeight = fontSize * lineHeightValue;
    const totalHeight = (texts.length - 1) * lineHeight;
    const startY = (canvas.height - totalHeight) / 2;
    
    // 如果是覆盖模式，添加背景蒙版
    if (templateType === 'overlay') {
        const maskOpacityValue = parseFloat(document.getElementById('mask-opacity')?.value || '0');
        if (maskOpacityValue > 0) {
            ctx.save();
            ctx.fillStyle = `rgba(0, 0, 0, ${maskOpacityValue})`;
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.restore();
        }
    }
    
    // 绘制文本
    texts.forEach((text, index) => {
        const y = startY + index * lineHeight;
        
        // 金色奢华样式
        if (textStyle === 'gold') {
            // 绘制阴影
            ctx.save();
            ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
            ctx.fillText(text, canvas.width / 2 + 2, y + 2);
            ctx.restore();
            
            // 绘制金色渐变文字
            const gradient = ctx.createLinearGradient(0, y - fontSize/2, 0, y + fontSize/2);
            gradient.addColorStop(0, '#FFD700');
            gradient.addColorStop(0.5, '#FFA500');
            gradient.addColorStop(1, '#FF8C00');
            ctx.fillStyle = gradient;
            ctx.fillText(text, canvas.width / 2, y);
            
            // 添加描边
            ctx.strokeStyle = '#B8860B';
            ctx.lineWidth = 1;
            ctx.strokeText(text, canvas.width / 2, y);
        } else if (textStyle === 'gold_stable') {
            // 金色沉稳样式处理
            ctx.save();
            
            // 绘制阴影效果
            ctx.shadowColor = 'rgba(139, 69, 19, 0.5)';
            ctx.shadowBlur = 4;
            ctx.shadowOffsetX = 2;
            ctx.shadowOffsetY = 2;
            
            // 金色渐变
            const gradient = ctx.createLinearGradient(0, y - fontSize/2, 0, y + fontSize/2);
            gradient.addColorStop(0, '#FFD700');
            gradient.addColorStop(0.5, '#FFA500');
            gradient.addColorStop(1, '#FF8C00');
            
            ctx.fillStyle = gradient;
            ctx.strokeStyle = '#8B4513';
            ctx.lineWidth = 2;
            ctx.strokeText(text, canvas.width / 2, y);
            ctx.fillText(text, canvas.width / 2, y);
            
            ctx.restore();
        } else if (textStyle === 'handwritten_elegant') {
            ctx.font = `500 ${fontSize}px cursive`;
            ctx.fillStyle = textColor;
            ctx.fillText(text, canvas.width / 2, y);
        } else if (textStyle === 'handwritten_warm') {
            ctx.save();
            ctx.font = `500 ${fontSize}px cursive`;
            ctx.shadowColor = 'rgba(255, 140, 0, 0.35)';
            ctx.shadowBlur = 6;
            ctx.fillStyle = textColor;
            ctx.fillText(text, canvas.width / 2, y);
            ctx.restore();
        } else if (textStyle === 'handwritten_flowing') {
            ctx.save();
            ctx.font = `italic 500 ${fontSize}px cursive`;
            // 轻微斜体效果（倾斜变换）
            ctx.translate(canvas.width / 2, y);
            ctx.transform(1, 0, -0.2, 1, 0, 0);
            ctx.fillStyle = textColor;
            ctx.fillText(text, 0, 0);
            ctx.restore();
        } else if (textStyle === 'handwritten_delicate') {
            ctx.save();
            // 使用中文黑体/粗体字体族，而非简单加粗
            ctx.font = `900 ${fontSize}px "SimHei", "Heiti SC", "STHeiti", "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif`;
            ctx.fillStyle = textColor;
            ctx.fillText(text, canvas.width / 2, y);
            ctx.restore();
        } else if (textStyle === 'handwritten_playful') {
            ctx.save();
            ctx.font = `600 ${fontSize}px cursive`;
            const angle = (index % 2 === 0 ? -0.03 : 0.03); // 轻微摆动
            ctx.translate(canvas.width / 2, y);
            ctx.rotate(angle);
            ctx.fillStyle = textColor;
            ctx.fillText(text, 0, 0);
            ctx.restore();
        } else if (textStyle === 'handwritten_artistic') {
            ctx.save();
            ctx.font = `600 ${fontSize}px cursive`;
            const g = ctx.createLinearGradient(0, y - fontSize, canvas.width, y + fontSize);
            g.addColorStop(0, '#ff5f6d');
            g.addColorStop(0.5, '#ffc371');
            g.addColorStop(1, '#6a11cb');
            ctx.fillStyle = g;
            // 轻描边增强艺术感
            ctx.strokeStyle = 'rgba(0,0,0,0.15)';
            ctx.lineWidth = 2;
            ctx.strokeText(text, canvas.width / 2, y);
            ctx.fillText(text, canvas.width / 2, y);
            ctx.restore();
        } else if (textStyle === 'handwritten_casual') {
            ctx.save();
            ctx.font = `normal 400 ${fontSize}px cursive`;
            ctx.fillStyle = textColor;
            ctx.fillText(text, canvas.width / 2, y);
            ctx.restore();
        } else {
            // 添加文本描边效果（仅覆盖模式）
            if (templateType === 'overlay') {
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 3;
                ctx.strokeText(text, canvas.width / 2, y);
            }
            // 默认字体
            ctx.font = `normal ${fontSize}px Arial, "Helvetica Neue", sans-serif`;
            ctx.fillStyle = textColor;
            ctx.fillText(text, canvas.width / 2, y);
        }
    });
}

// 保存图片模板
async function saveTemplate() {
    console.log('saveTemplate function called');
    
    const templateName = document.getElementById('template-name')?.value;
    console.log('Template name:', templateName);
    
    if (!templateName || templateName.trim() === '') {
        showAlert('请输入模板名称', 'error');
        return;
    }
    
    // 收集模板数据
    const templateType = document.querySelector('input[name="template-type"]:checked')?.value || 'insert';
    const activeStyleBtn = document.querySelector('.style-btn.active');
    const textStyle = activeStyleBtn?.dataset.style || 'gold';
    const textColor = document.getElementById('text-color-picker')?.value || '#2c3e50';
    const activeBgBtn = document.querySelector('.bg-btn.active');
    const backgroundStyle = activeBgBtn?.dataset.bg || 'minimal_gradient';
    const fontSize = parseInt(document.getElementById('font-size')?.value || '100'); // 调整默认字体大小以适应750x1000画布
    const lineHeight = document.getElementById('line-height')?.value || '1.2';
    const maskOpacity = document.getElementById('mask-opacity')?.value || '0';
    const textLinesRadio = document.querySelector('input[name="text-lines"]:checked');
    const textLines = parseInt(textLinesRadio?.value || '3');
    
    // 获取自定义背景（若有则保存 data URL 到模板）
    let customBackgroundPath = null;
    if (customBackgroundDataUrl && typeof customBackgroundDataUrl === 'string' && customBackgroundDataUrl.startsWith('data:image')) {
        customBackgroundPath = customBackgroundDataUrl;
    }
    
    const templateData = {
        name: templateName.trim(),
        template_type: templateType,
        text_style: textStyle,
        text_color: textColor,
        background_style: backgroundStyle,
        font_size: fontSize,
        line_height: lineHeight,
        mask_opacity: maskOpacity,
        text_lines: textLines,
        custom_background_path: customBackgroundPath
    };
    
    console.log('Template data to save:', templateData);
    
    try {
        console.log('Sending POST request to /api/template-materials/save-image-template');
        const response = await fetch('/api/template-materials/save-image-template', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(templateData)
        });
        
        console.log('Response status:', response.status);
        const result = await response.json();
        console.log('Response data:', result);
        
        if (result.success) {
            console.log('Template saved successfully, customBackgroundImage before reload:', !!customBackgroundImage);
            showAlert('模板保存成功', 'success');
            loadImageTemplates(); // 重新加载模板列表
            
            // 检查是否新模板被自动设为当前模板
            setTimeout(async () => {
                const statusResponse = await fetch('/api/template-materials/get-template-status');
                const statusData = await statusResponse.json();
                console.log('Current template status after save:', statusData);
                
                // 如果新保存的模板被自动应用了，这可能是问题的原因
                if (statusData.template_id === result.template_id) {
                    console.warn('New template was automatically applied! This might cause preview lock issue.');
                }
            }, 100);
            
            // 清空表单
            document.getElementById('template-name').value = '';
            console.log('Template saved successfully, customBackgroundImage after reload:', !!customBackgroundImage);
        } else {
            showAlert('保存失败: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('Save error:', error);
        showAlert('保存失败: ' + error.message, 'error');
    }
}

// 下载预览图片
function downloadImage() {
    if (!canvas) return;
    
    const link = document.createElement('a');
    link.download = 'template-preview.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
}

// 退出当前模板
async function exitCurrentTemplate() {
    try {
        console.log('Exiting current template');
        
        const response = await fetch('/api/template-materials/exit-current-template', {
            method: 'POST'
        });
        
        const result = await response.json();
        if (result.success) {
            console.log('Template exited successfully');
            
            // 清除预览画布，重置为默认状态
            clearTemplatePreview();
            
            // 更新当前模板显示为"未指定"
            const imageTemplateNameEl = document.getElementById('current-image-template-name');
            if (imageTemplateNameEl) {
                imageTemplateNameEl.textContent = '未指定';
                imageTemplateNameEl.className = 'font-medium text-gray-500';
            }
            
            // 通知其他页面模板状态已更改
            notifyTemplateStatusChange();
            
            showAlert('已退出当前模板', 'success');
        } else {
            showAlert('退出失败: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('Exit template error:', error);
        showAlert('退出失败', 'error');
    }
}

// 清除模板预览
function clearTemplatePreview() {
    if (!canvas || !ctx) return;
    
    console.log('Clearing template preview');
    
    // 重置画布为默认状态
    ctx.fillStyle = '#f8f9fa';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#666';
    ctx.font = '40px Arial'; // 调整默认字体以适应750x1000画布
    ctx.textAlign = 'center';
    ctx.fillText('预览区域', canvas.width/2, canvas.height/2);
    
    // 重置表单控件为默认值
    // 重置模板类型为插入模式
    const insertRadio = document.querySelector('input[name="template-type"][value="insert"]');
    if (insertRadio) insertRadio.checked = true;
    
    // 重置样式按钮
    const styleButtons = document.querySelectorAll('.style-btn');
    styleButtons.forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.style === 'gold') {
            btn.classList.add('active');
        }
    });
    
    // 重置背景按钮
    const bgButtons = document.querySelectorAll('.bg-btn');
    bgButtons.forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.bg === 'minimal_gradient') {
            btn.classList.add('active');
        }
    });
    
    // 重置颜色选择器
    const colorPicker = document.getElementById('text-color-picker');
    if (colorPicker) colorPicker.value = '#2c3e50';
    
    // 重置字体大小
    const fontSize = document.getElementById('font-size');
    if (fontSize) {
        fontSize.value = 40;
        updateFontSizeValue(40);
    }
    
    // 重置行高
    const lineHeight = document.getElementById('line-height');
    if (lineHeight) {
        lineHeight.value = 1.2;
        updateLineHeightValue(1.2);
    }
    
    // 重置遮罩透明度
    const maskOpacity = document.getElementById('mask-opacity');
    if (maskOpacity) {
        maskOpacity.value = 0;
        updateMaskOpacityValue(0);
    }
    
    // 重置文字行数
    const threeLines = document.querySelector('input[name="text-lines"][value="3"]');
    if (threeLines) threeLines.checked = true;
    
    console.log('Template preview cleared');
}

// 通知其他页面模板状态已更改
function notifyTemplateStatusChange() {
    console.log('Notifying template status change');
    
    // 1. 通过localStorage通知其他标签页/窗口
    const timestamp = Date.now();
    localStorage.setItem('templateStatus', timestamp.toString());
    
    // 2. 通过自定义事件通知同一页面的其他组件
    const event = new CustomEvent('templateStatusChanged', {
        detail: { timestamp: timestamp }
    });
    window.dispatchEvent(event);
    
    console.log('Template status change notification sent');
}

// 页面加载时应用当前模板到预览
async function loadAndApplyCurrentTemplate() {
    try {
        console.log('Loading and applying current template');
        
        // 获取当前模板状态
        const statusResponse = await fetch('/api/template-materials/get-template-status');
        const statusData = await statusResponse.json();
        
        if (statusData.has_template && statusData.template_id) {
            console.log('Found active template:', statusData.template_name);
            
            // 获取模板详细信息
            const templatesResponse = await fetch('/api/template-materials/image-templates');
            const templates = await templatesResponse.json();
            const template = templates.find(t => t.id === statusData.template_id);
            
            if (template) {
                console.log('Applying current template to preview:', template);
                // 应用模板到预览（不调用后端应用API）
                await applyTemplateToPreview(template);
                // 更新当前模板显示
                updateCurrentTemplateDisplay(template);
            }
        } else {
            console.log('No active template, showing default state');
            // 确保显示"未指定"状态
            const imageTemplateNameEl = document.getElementById('current-image-template-name');
            if (imageTemplateNameEl) {
                imageTemplateNameEl.textContent = '未指定';
                imageTemplateNameEl.className = 'font-medium text-gray-500';
            }
        }
    } catch (error) {
        console.error('Failed to load and apply current template:', error);
    }
}

// 生成内容预览
async function generateContentPreview() {
    try {
        const response = await fetch('/api/template-materials/generate-content-preview', {
            method: 'POST'
        });
        
        const result = await response.json();
        if (result.success) {
            const previewEl = document.getElementById('content-preview');
            if (previewEl) {
                previewEl.innerHTML = `
                    <div class="space-y-2">
                        <div class="text-sm text-gray-600">使用模板: ${result.template_name || '随机模板'}</div>
                        <div class="whitespace-pre-wrap">${result.content || '暂无内容'}</div>
                    </div>
                `;
            }
        } else {
            showAlert('生成失败: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('Generate preview error:', error);
        showAlert('生成失败', 'error');
    }
}

// 使用指定模板生成内容预览
async function generateContentPreviewWithTemplate(templateId) {
    try {
        console.log('Generating content preview with template:', templateId);
        
        const response = await fetch('/api/template-materials/generate-content-preview', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ template_id: templateId })
        });
        
        const result = await response.json();
        if (result.success) {
            const previewEl = document.getElementById('content-preview');
            if (previewEl) {
                previewEl.innerHTML = `
                    <div class="space-y-2">
                        <div class="text-sm text-gray-600">使用模板: ${result.template_name}</div>
                        <div class="whitespace-pre-wrap bg-white p-3 rounded border">${result.content || '暂无内容'}</div>
                    </div>
                `;
            }
            console.log('Content preview generated successfully');
        } else {
            showAlert('生成预览失败: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('Generate content preview with template error:', error);
        showAlert('生成预览失败', 'error');
    }
}

// 切换内容随机模式
async function toggleContentRandomMode() {
    try {
        console.log('Toggling content random mode');
        
        const response = await fetch('/api/template-materials/enable-content-random-mode', {
            method: 'POST'
        });
        
        const result = await response.json();
        if (result.success) {
            // 更新当前内容模板显示为"随机模式"
            const contentTemplateNameEl = document.getElementById('current-content-template-name');
            if (contentTemplateNameEl) {
                contentTemplateNameEl.textContent = '随机模式';
                contentTemplateNameEl.className = 'font-medium text-purple-600';
            }
            
            // 清空内容预览
            const previewEl = document.getElementById('content-preview');
            if (previewEl) {
                previewEl.innerHTML = '<p class="text-gray-500 text-center">选择内容模板后点击"生成预览"查看效果</p>';
            }
            
            // 通知其他页面状态已更改
            notifyTemplateStatusChange();
            
            showAlert('已切换到随机模式', 'success');
        } else {
            showAlert('切换失败: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('Toggle random mode error:', error);
        showAlert('切换失败', 'error');
    }
}

// 保存内容模板
async function saveContentTemplate() {
    const templateName = document.getElementById('content-template-name')?.value;
    if (!templateName) {
        showAlert('请输入模板名称', 'error');
        return;
    }
    
    const descriptionText = document.getElementById('description-templates')?.value || '';
    const topicText = document.getElementById('topic-templates')?.value || '';
    
    const templateData = {
        name: templateName,
        description_templates: descriptionText.split('\n').filter(line => line.trim()),
        use_random_description: false,  // 固定为false，正文描述不随机
        no_description: document.getElementById('no-description')?.checked || false,
        topic_templates: topicText.split('\n').filter(line => line.trim()),
        topic_count: parseInt(document.getElementById('topic-count')?.value || '7')
    };
    
    try {
        const response = await fetch('/api/template-materials/save-content-template', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(templateData)
        });
        
        const result = await response.json();
        if (result.success) {
            showAlert('内容模板保存成功', 'success');
            loadContentTemplates();
            // 清空表单
            document.getElementById('content-template-name').value = '';
            document.getElementById('description-templates').value = '';
            document.getElementById('topic-templates').value = '';
        } else {
            showAlert('保存失败: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('Save content template error:', error);
        showAlert('保存失败', 'error');
    }
}

// 删除图片模板
function deleteImageTemplate(id) {
    if (confirm('确定要删除这个图片模板吗？')) {
        fetch(`/api/template-materials/image-template/${id}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadImageTemplates();
                showAlert('删除成功', 'success');
            } else {
                showAlert('删除失败: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('删除失败:', error);
            showAlert('删除失败', 'error');
        });
    }
}

// 删除内容模板
function deleteContentTemplate(id) {
    if (confirm('确定要删除这个内容模板吗？')) {
        fetch(`/api/template-materials/content-template/${id}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadContentTemplates();
                showAlert('删除成功', 'success');
            } else {
                showAlert('删除失败: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('删除失败:', error);
            showAlert('删除失败', 'error');
        });
    }
}

// 工具函数
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.style.position = 'fixed';
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.style.background = type === 'error' ? '#fee2e2' : (type === 'success' ? '#dcfce7' : '#e5e7eb');
    alertDiv.style.color = '#111827';
    alertDiv.style.border = '1px solid rgba(0,0,0,0.1)';
    alertDiv.style.padding = '10px 12px';
    alertDiv.style.borderRadius = '8px';
    alertDiv.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
    alertDiv.innerHTML = `
        ${message}
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Tab切换函数
function showTab(tabName) {
    console.log('Switching to tab:', tabName);
    
    // 隐藏所有tab内容
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.add('hidden');
    });
    
    // 显示目标tab
    const targetTab = document.getElementById(tabName + '-tab');
    if (targetTab) {
        targetTab.classList.remove('hidden');
    }
    
    // 更新tab按钮状态
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('border-indigo-500', 'text-indigo-600');
        btn.classList.add('border-transparent', 'text-gray-500');
    });
    
    const activeButton = document.getElementById(tabName + '-tab-button');
    if (activeButton) {
        activeButton.classList.add('border-indigo-500', 'text-indigo-600');
        activeButton.classList.remove('border-transparent', 'text-gray-500');
    }
}

// 颜色预设函数
function resetTextColor() {
    const colorPicker = document.getElementById('text-color-picker');
    if (colorPicker) {
        colorPicker.value = '#2c3e50';
        updatePreview();
    }
}

function setPresetColor(color) {
    const colorPicker = document.getElementById('text-color-picker');
    if (colorPicker) {
        colorPicker.value = color;
        updatePreview();
    }
}

// HTML中使用的辅助函数
function updateFontSizeValue(value) {
    const element = document.getElementById('font-size-value');
    if (element) element.textContent = value + 'px';
    updatePreview();
}

function updateLineHeightValue(value) {
    const element = document.getElementById('line-height-value');
    if (element) element.textContent = value;
    updatePreview();
}

function updateMaskOpacityValue(value) {
    const element = document.getElementById('mask-opacity-value');
    if (element) element.textContent = value;
    updatePreview();
}

// 处理背景图片上传
function handleBackgroundUpload(file) {
    if (!file) return;
    
    console.log('Processing background upload:', file.name, file.type);
    
    if (!file.type.startsWith('image/')) {
        showAlert('请选择图片文件', 'error');
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        console.log('Image loaded, data URL length:', e.target.result.length);
        
        const img = new Image();
        img.onload = function() {
            console.log('Image dimensions:', img.width, 'x', img.height);
            
            // 保存自定义背景图片到全局变量
            customBackgroundImage = img;
            customBackgroundDataUrl = e.target.result;
            console.log('Custom background image saved:', !!customBackgroundImage);
            
            // 显示预览
            const preview = document.getElementById('custom-bg-preview');
            if (preview) {
                preview.innerHTML = `
                    <div class="relative">
                        <img src="${e.target.result}" class="w-full h-20 object-cover rounded border">
                        <button type="button" onclick="removeCustomBackground()" class="absolute -top-2 -right-2 bg-red-600 text-white rounded-full w-5 h-5 leading-5 text-xs">×</button>
                    </div>
                    <p class="text-xs text-green-600 mt-1">✓ 背景已上传 (${img.width}x${img.height})</p>
                `;
                preview.classList.remove('hidden');
            }
            
            // 更新预览 - 现在会自动使用自定义背景
            updatePreview();
            
            showAlert('背景图片上传成功', 'success');
        };
        img.onerror = function() {
            console.error('Failed to load image');
            showAlert('图片加载失败', 'error');
        };
        img.src = e.target.result;
    };
    reader.onerror = function() {
        console.error('Failed to read file');
        showAlert('文件读取失败', 'error');
    };
    reader.readAsDataURL(file);
}

// 通过URL设置自定义背景（走后端代理，避免CORS）
async function uploadBackgroundFromUrl() {
    const input = document.getElementById('bg-url-input');
    if (!input) return;
    const url = (input.value || '').trim();
    if (!url) {
        showAlert('请输入图片URL', 'error');
        return;
    }

    try {
        console.log('Fetching image via backend proxy:', url);
        // 支持直接 data:URL
        if (url.startsWith('data:image')) {
            await setCustomBackgroundFromDataUrl(url);
            showAlert('已使用数据URL作为背景', 'success');
            return;
        }

        // 简单校验
        if (!/^https?:\/\//i.test(url)) {
            showAlert('仅支持 http/https 链接', 'error');
            return;
        }

        const resp = await fetch('/api/template-materials/fetch-image-dataurl', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        const data = await resp.json();
        if (data && data.success && data.data_url) {
            await setCustomBackgroundFromDataUrl(data.data_url);
            showAlert('背景图片加载成功', 'success');
        } else {
            console.error('Proxy fetch failed:', data);
            const detail = (data && (data.detail || data.message)) ? (data.detail || data.message) : '未知错误';
            showAlert('图片加载失败：' + detail + '，尝试直接加载预览', 'error');
            // Fallback: 直接加载 URL 预览（不保证可保存为模板）
            try {
                await setCustomBackgroundFromHttpUrlForPreview(url);
                showAlert('已直接加载预览（未保存为模板背景）', 'info');
            } catch (e2) {
                console.error('Direct load preview failed:', e2);
            }
        }
    } catch (err) {
        console.error('uploadBackgroundFromUrl error:', err);
        showAlert('图片加载失败', 'error');
    }
}

// 用 dataURL 设置自定义背景（与本地上传逻辑复用）
async function setCustomBackgroundFromDataUrl(dataUrl) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = function() {
            customBackgroundImage = img;
            customBackgroundDataUrl = dataUrl;
            const preview = document.getElementById('custom-bg-preview');
            if (preview) {
                preview.innerHTML = `
                    <div class="relative">
                        <img src="${dataUrl}" class="w-full h-20 object-cover rounded border">
                        <button type="button" onclick="removeCustomBackground()" class="absolute -top-2 -right-2 bg-red-600 text-white rounded-full w-5 h-5 leading-5 text-xs">×</button>
                    </div>
                    <p class=\"text-xs text-green-600 mt-1\">✓ 背景已加载 (${img.width}x${img.height})</p>
                `;
                preview.classList.remove('hidden');
            }
            updatePreview();
            resolve();
        };
        img.onerror = function() {
            reject(new Error('Image load error'));
        };
        img.src = dataUrl;
    });
}

// 尝试直接以 http/https URL 进行预览加载（不持久化）
async function setCustomBackgroundFromHttpUrlForPreview(url) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload = function() {
            customBackgroundImage = img;
            // 不设置 customBackgroundDataUrl，预览有效但无法保存为模板背景
            const preview = document.getElementById('custom-bg-preview');
            if (preview) {
                preview.innerHTML = `
                    <div class="relative">
                        <img src="${url}" class="w-full h-20 object-cover rounded border">
                        <button type="button" onclick="removeCustomBackground()" class="absolute -top-2 -right-2 bg-red-600 text-white rounded-full w-5 h-5 leading-5 text-xs">×</button>
                    </div>
                    <p class=\"text-xs text-yellow-700 mt-1\">已预览（未持久化）</p>
                `;
                preview.classList.remove('hidden');
            }
            updatePreview();
            resolve();
        };
        img.onerror = function() { reject(new Error('Direct image load error')); };
        // 防缓存
        const cacheBust = (url.includes('?') ? '&' : '?') + 'cb=' + Date.now();
        img.src = url + cacheBust;
    });
}

// 绘制自定义背景图片到Canvas
function drawCustomBackgroundImage(img) {
    if (!canvas || !ctx || !img) {
        console.warn('Cannot draw custom background - missing:', {canvas: !!canvas, ctx: !!ctx, img: !!img});
        return;
    }
    
    console.log('Drawing custom background image:', img.width, 'x', img.height);
    
    ctx.save();
    
    // 计算居中缩放，保持图片填满整个Canvas
    const scale = Math.max(canvas.width / img.width, canvas.height / img.height);
    const newWidth = img.width * scale;
    const newHeight = img.height * scale;
    const x = (canvas.width - newWidth) / 2;
    const y = (canvas.height - newHeight) / 2;
    
    console.log('Background scale:', scale, 'Size:', newWidth, 'x', newHeight, 'Position:', x, y);
    
    // 绘制背景图片
    ctx.drawImage(img, x, y, newWidth, newHeight);
    
    ctx.restore();
    console.log('Custom background drawn successfully');
}

// 移除自定义背景图片
function removeCustomBackground() {
    // 清除全局背景图片引用
    customBackgroundImage = null;
    customBackgroundDataUrl = null;
    
    // 隐藏预览
    const preview = document.getElementById('custom-bg-preview');
    if (preview) {
        preview.classList.add('hidden');
        preview.innerHTML = '';
    }
    
    // 清空文件输入
    const bgUpload = document.getElementById('bg-upload');
    if (bgUpload) {
        bgUpload.value = '';
    }
    
    // 更新预览，使用预设背景样式
    updatePreview();
    
    showAlert('已移除自定义背景', 'success');
}
// 全局函数定义 - 供HTML onclick调用
window.saveTemplate = saveTemplate;
window.saveContentTemplate = saveContentTemplate;
window.applyImageTemplate = applyImageTemplate;
window.deleteImageTemplate = deleteImageTemplate;
window.applyContentTemplate = applyContentTemplate;
window.deleteContentTemplate = deleteContentTemplate;
window.downloadImage = downloadImage;
window.removeCustomBackground = removeCustomBackground;
window.uploadBackgroundFromUrl = uploadBackgroundFromUrl;
