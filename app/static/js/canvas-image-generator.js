/**
 * 共享Canvas图片生成器
 * 用于在不同页面之间复用Canvas绘制逻辑，确保样式一致性
 */
class CanvasImageGenerator {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.customBackgroundImage = null;
    }

    /**
     * 初始化Canvas
     * @param {string} canvasId - Canvas元素ID
     * @param {number} width - Canvas宽度
     * @param {number} height - Canvas高度
     */
    initialize(canvasId, width = 750, height = 1000) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            // 如果Canvas不存在，创建一个
            this.canvas = document.createElement('canvas');
            this.canvas.id = canvasId;
            this.canvas.width = width;
            this.canvas.height = height;
            this.canvas.style.display = 'none'; // 隐藏，仅用于生成
            document.body.appendChild(this.canvas);
        }
        
        this.ctx = this.canvas.getContext('2d');
        this.canvas.width = width;
        this.canvas.height = height;
        
        return this.canvas;
    }

    /**
     * 根据模版配置生成图片
     * @param {Object} templateConfig - 模版配置
     * @param {Array} textLines - 文本行数组
     * @param {string} mode - 模式 ('insert' 或 'overlay')
     * @returns {Promise<string>} - Base64图片数据
     */
    async generateImage(templateConfig, textLines, mode = 'insert') {
        if (!this.canvas || !this.ctx) {
            throw new Error('Canvas未初始化');
        }

        // 清除Canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        try {
            // 绘制背景
            await this.drawBackground(templateConfig.background_style, templateConfig.custom_background_path, mode);
            
            // 绘制文本
            this.drawTexts(templateConfig, textLines, mode);
            
            // 返回图片数据
            return this.canvas.toDataURL('image/png', 0.9);
        } catch (error) {
            console.error('生成图片时出错:', error);
            throw error;
        }
    }

    /**
     * 绘制背景
     * @param {string} backgroundStyle - 背景样式
     * @param {string} customBackgroundPath - 自定义背景路径
     * @param {string} mode - 模式
     */
    async drawBackground(backgroundStyle, customBackgroundPath, mode) {
        // 如果有自定义背景，优先使用
        if (customBackgroundPath && customBackgroundPath !== 'custom_uploaded_background') {
            try {
                await this.loadAndDrawCustomBackground(customBackgroundPath);
                return;
            } catch (error) {
                console.warn('加载自定义背景失败，使用默认样式:', error);
            }
        }

        // 覆盖模式且没有自定义背景时显示示例图片背景
        if (mode === 'overlay') {
            this.ctx.fillStyle = '#f0f0f0';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            
            // 添加示例图片文字
            this.ctx.fillStyle = '#999';
            this.ctx.font = '24px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.fillText('示例图片背景', this.canvas.width / 2, this.canvas.height / 2 - 60);
            this.ctx.font = '16px Arial';
            this.ctx.fillText('(实际发布时会覆盖在原图上)', this.canvas.width / 2, this.canvas.height / 2 - 30);
            return;
        }

        // 插入模式使用预设背景样式
        this.drawPresetBackground(backgroundStyle);
    }

    /**
     * 绘制预设背景样式
     * @param {string} style - 背景样式
     */
    drawPresetBackground(style) {
        const ctx = this.ctx;
        const { width, height } = this.canvas;

        switch (style) {
            case 'clean_solid':
                ctx.fillStyle = '#f8f9fa';
                ctx.fillRect(0, 0, width, height);
                break;

            case 'minimal_gradient':
                const gradient = ctx.createLinearGradient(0, 0, 0, height);
                gradient.addColorStop(0, '#667eea');
                gradient.addColorStop(1, '#764ba2');
                ctx.fillStyle = gradient;
                ctx.fillRect(0, 0, width, height);
                break;

            case 'subtle_texture':
                ctx.fillStyle = '#f5f5f5';
                ctx.fillRect(0, 0, width, height);
                ctx.fillStyle = 'rgba(200, 200, 200, 0.3)';
                for (let x = 0; x < width; x += 50) {
                    for (let y = 0; y < height; y += 50) {
                        if ((x + y) % 100 === 0) {
                            ctx.fillRect(x, y, 25, 25);
                        }
                    }
                }
                break;

            case 'soft_blur':
                const blurGradient = ctx.createRadialGradient(width/2, height/2, 0, width/2, height/2, width);
                blurGradient.addColorStop(0, '#ff9a9e');
                blurGradient.addColorStop(1, '#fecfef');
                ctx.fillStyle = blurGradient;
                ctx.fillRect(0, 0, width, height);
                break;

            case 'geometric_minimal':
                ctx.fillStyle = '#ffffff';
                ctx.fillRect(0, 0, width, height);
                ctx.strokeStyle = '#e1e5e9';
                ctx.lineWidth = 2;
                // 绘制几何图形
                for (let i = 0; i < 5; i++) {
                    ctx.strokeRect(50 + i * 30, 50 + i * 40, width - 100 - i * 60, height - 100 - i * 80);
                }
                break;

            case 'paper_texture':
                ctx.fillStyle = '#faf8f5';
                ctx.fillRect(0, 0, width, height);
                // 添加纸质纹理效果
                ctx.fillStyle = 'rgba(139, 137, 120, 0.1)';
                for (let i = 0; i < 1000; i++) {
                    const x = Math.random() * width;
                    const y = Math.random() * height;
                    ctx.fillRect(x, y, 1, 1);
                }
                break;

            case 'gradient_fade':
                const fadeGradient = ctx.createLinearGradient(0, 0, width, height);
                fadeGradient.addColorStop(0, '#74b9ff');
                fadeGradient.addColorStop(0.5, '#0984e3');
                fadeGradient.addColorStop(1, '#2d3436');
                ctx.fillStyle = fadeGradient;
                ctx.fillRect(0, 0, width, height);
                break;

            case 'clean_lines':
                ctx.fillStyle = '#ffffff';
                ctx.fillRect(0, 0, width, height);
                ctx.strokeStyle = '#ddd';
                ctx.lineWidth = 1;
                // 绘制简洁线条
                for (let i = 0; i < width; i += 100) {
                    ctx.beginPath();
                    ctx.moveTo(i, 0);
                    ctx.lineTo(i, height);
                    ctx.stroke();
                }
                for (let i = 0; i < height; i += 100) {
                    ctx.beginPath();
                    ctx.moveTo(0, i);
                    ctx.lineTo(width, i);
                    ctx.stroke();
                }
                break;

            case 'monochrome':
                ctx.fillStyle = '#2c3e50';
                ctx.fillRect(0, 0, width, height);
                break;

            case 'soft_shadow':
                ctx.fillStyle = '#ecf0f1';
                ctx.fillRect(0, 0, width, height);
                // 添加柔和阴影效果
                const shadowGradient = ctx.createRadialGradient(width/2, height/2, 0, width/2, height/2, width/2);
                shadowGradient.addColorStop(0, 'rgba(0, 0, 0, 0)');
                shadowGradient.addColorStop(1, 'rgba(0, 0, 0, 0.1)');
                ctx.fillStyle = shadowGradient;
                ctx.fillRect(0, 0, width, height);
                break;

            case 'marble_texture':
                ctx.fillStyle = '#f8f9fa';
                ctx.fillRect(0, 0, width, height);
                // 大理石纹理效果
                ctx.strokeStyle = 'rgba(52, 73, 94, 0.1)';
                ctx.lineWidth = 2;
                for (let i = 0; i < 20; i++) {
                    ctx.beginPath();
                    ctx.moveTo(Math.random() * width, Math.random() * height);
                    ctx.quadraticCurveTo(
                        Math.random() * width, Math.random() * height,
                        Math.random() * width, Math.random() * height
                    );
                    ctx.stroke();
                }
                break;

            case 'pastel_blend':
                const pastelGradient = ctx.createLinearGradient(0, 0, width, height);
                pastelGradient.addColorStop(0, '#fd79a8');
                pastelGradient.addColorStop(0.5, '#fdcb6e');
                pastelGradient.addColorStop(1, '#6c5ce7');
                ctx.fillStyle = pastelGradient;
                ctx.fillRect(0, 0, width, height);
                break;

            default:
                // 默认渐变背景
                const defaultGradient = ctx.createLinearGradient(0, 0, width, height);
                defaultGradient.addColorStop(0, '#4facfe');
                defaultGradient.addColorStop(1, '#00f2fe');
                ctx.fillStyle = defaultGradient;
                ctx.fillRect(0, 0, width, height);
        }
    }

    /**
     * 加载并绘制自定义背景
     * @param {string} imagePath - 图片路径
     */
    async loadAndDrawCustomBackground(imagePath) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = 'anonymous'; // 处理跨域问题
            
            img.onload = () => {
                this.drawCustomBackgroundImage(img);
                resolve();
            };
            
            img.onerror = () => {
                reject(new Error(`Failed to load background image: ${imagePath}`));
            };
            
            img.src = imagePath;
        });
    }

    /**
     * 绘制自定义背景图片到Canvas
     * @param {HTMLImageElement} img - 图片对象
     */
    drawCustomBackgroundImage(img) {
        if (!this.ctx || !img) return;
        
        this.ctx.save();
        
        // 计算居中缩放，保持图片填满整个Canvas
        const scale = Math.max(this.canvas.width / img.width, this.canvas.height / img.height);
        const newWidth = img.width * scale;
        const newHeight = img.height * scale;
        const x = (this.canvas.width - newWidth) / 2;
        const y = (this.canvas.height - newHeight) / 2;
        
        // 绘制背景图片
        this.ctx.drawImage(img, x, y, newWidth, newHeight);
        
        this.ctx.restore();
    }

    /**
     * 绘制文本内容
     * @param {Object} templateConfig - 模版配置
     * @param {Array} textLines - 文本行数组
     * @param {string} mode - 模式
     */
    drawTexts(templateConfig, textLines, mode) {
        const ctx = this.ctx;
        
        // 从配置中提取参数，不使用硬编码默认值
        const textStyle = templateConfig.text_style || 'gold';
        const textColor = templateConfig.text_color || '#2c3e50';
        const fontSize = templateConfig.font_size || 40;  // 移除硬编码的60
        const lineHeight = templateConfig.line_height || 1.2;  // 确保使用配置值
        const maskOpacity = templateConfig.mask_opacity || 0;
        
        console.log('🎨 DEBUG: Canvas drawTexts 实际使用的参数:');
        console.log(`   - fontSize: ${fontSize} (来源: ${templateConfig.font_size ? '模板配置' : '默认值'})`);
        console.log(`   - lineHeight: ${lineHeight} (来源: ${templateConfig.line_height ? '模板配置' : '默认值'})`);
        console.log(`   - textStyle: ${textStyle}`);
        console.log(`   - textColor: ${textColor}`);

        // 默认字体（各变体会在绘制时覆盖）
        ctx.font = `${'normal'} ${fontSize}px ${'Arial, "Helvetica Neue", sans-serif'}`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        const lineHeightValue = parseFloat(lineHeight);
        const actualLineHeight = fontSize * lineHeightValue;
        const totalHeight = (textLines.length - 1) * actualLineHeight;
        const startY = (this.canvas.height - totalHeight) / 2;

        // 如果是覆盖模式，添加背景蒙版
        if (mode === 'overlay') {
            const maskOpacityValue = parseFloat(maskOpacity);
            if (maskOpacityValue > 0) {
                ctx.save();
                ctx.fillStyle = `rgba(0, 0, 0, ${maskOpacityValue})`;
                ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
                ctx.restore();
            }
        }

        // 绘制文本
        textLines.forEach((text, index) => {
            if (!text) return;
            
            const y = startY + index * actualLineHeight;

            // 根据文字样式绘制
            if (textStyle === 'gold') {
                this.drawGoldLuxuryText(text, this.canvas.width / 2, y, fontSize);
            } else if (textStyle === 'gold_stable') {
                this.drawGoldStableText(text, this.canvas.width / 2, y, fontSize);
            } else if (textStyle && textStyle.startsWith('handwritten_')) {
                this.drawHandwrittenText(text, this.canvas.width / 2, y, textStyle, fontSize, textColor, mode);
            } else {
                this.drawRegularText(text, this.canvas.width / 2, y, textColor, mode);
            }
        });
    }

    /**
     * 绘制手写风格文字（多变体）
     */
    drawHandwrittenText(text, x, y, style, fontSize, textColor, mode) {
        const ctx = this.ctx;
        switch (style) {
            case 'handwritten_elegant':
                ctx.font = `500 ${fontSize}px cursive`;
                if (mode === 'overlay') {
                    ctx.strokeStyle = 'white';
                    ctx.lineWidth = 3;
                    ctx.strokeText(text, x, y);
                }
                ctx.fillStyle = textColor;
                ctx.fillText(text, x, y);
                break;
            case 'handwritten_warm':
                ctx.save();
                ctx.font = `500 ${fontSize}px cursive`;
                ctx.shadowColor = 'rgba(255, 140, 0, 0.35)';
                ctx.shadowBlur = 6;
                ctx.fillStyle = textColor;
                if (mode === 'overlay') {
                    ctx.strokeStyle = 'white';
                    ctx.lineWidth = 3;
                    ctx.strokeText(text, x, y);
                }
                ctx.fillText(text, x, y);
                ctx.restore();
                break;
            case 'handwritten_flowing':
                ctx.save();
                ctx.font = `italic 500 ${fontSize}px cursive`;
                ctx.translate(x, y);
                ctx.transform(1, 0, -0.2, 1, 0, 0);
                ctx.fillStyle = textColor;
                if (mode === 'overlay') {
                    ctx.strokeStyle = 'white';
                    ctx.lineWidth = 3;
                    ctx.strokeText(text, 0, 0);
                }
                ctx.fillText(text, 0, 0);
                ctx.restore();
                break;
            case 'handwritten_delicate':
                ctx.save();
                // 使用中文黑体/粗体字体族，而非简单加粗
                ctx.font = `900 ${fontSize}px "SimHei", "Heiti SC", "STHeiti", "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif`;
                ctx.fillStyle = textColor;
                if (mode === 'overlay') {
                    ctx.strokeStyle = 'white';
                    ctx.lineWidth = 3;
                    ctx.strokeText(text, x, y);
                }
                ctx.fillText(text, x, y);
                ctx.restore();
                break;
            case 'handwritten_playful':
                ctx.save();
                ctx.font = `600 ${fontSize}px cursive`;
                // 轻微摆动角度，随内容长度扰动
                const angle = (text.length % 2 === 0 ? -0.03 : 0.03);
                ctx.translate(x, y);
                ctx.rotate(angle);
                ctx.fillStyle = textColor;
                if (mode === 'overlay') {
                    ctx.strokeStyle = 'white';
                    ctx.lineWidth = 3;
                    ctx.strokeText(text, 0, 0);
                }
                ctx.fillText(text, 0, 0);
                ctx.restore();
                break;
            case 'handwritten_artistic':
                ctx.save();
                ctx.font = `600 ${fontSize}px cursive`;
                const g = ctx.createLinearGradient(0, y - fontSize, this.canvas.width, y + fontSize);
                g.addColorStop(0, '#ff5f6d');
                g.addColorStop(0.5, '#ffc371');
                g.addColorStop(1, '#6a11cb');
                ctx.fillStyle = g;
                ctx.strokeStyle = 'rgba(0,0,0,0.15)';
                ctx.lineWidth = 2;
                ctx.strokeText(text, x, y);
                ctx.fillText(text, x, y);
                ctx.restore();
                break;
            case 'handwritten_casual':
            default:
                ctx.font = `normal 400 ${fontSize}px cursive`;
                if (mode === 'overlay') {
                    ctx.strokeStyle = 'white';
                    ctx.lineWidth = 3;
                    ctx.strokeText(text, x, y);
                }
                ctx.fillStyle = textColor;
                ctx.fillText(text, x, y);
                break;
        }
    }

    /**
     * 绘制金色奢华文字
     * @param {string} text - 文字内容
     * @param {number} x - X坐标
     * @param {number} y - Y坐标 
     * @param {number} fontSize - 字体大小
     */
    drawGoldLuxuryText(text, x, y, fontSize) {
        const ctx = this.ctx;
        
        // 绘制阴影
        ctx.save();
        ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
        ctx.fillText(text, x + 3, y + 3);
        ctx.restore();

        // 绘制金色渐变文字
        const gradient = ctx.createLinearGradient(0, y - fontSize/2, 0, y + fontSize/2);
        gradient.addColorStop(0, '#FFD700');
        gradient.addColorStop(0.5, '#FFA500');
        gradient.addColorStop(1, '#FF8C00');
        ctx.fillStyle = gradient;
        ctx.fillText(text, x, y);

        // 添加描边
        ctx.strokeStyle = '#B8860B';
        ctx.lineWidth = 2;
        ctx.strokeText(text, x, y);
    }

    /**
     * 绘制金色沉稳文字
     * @param {string} text - 文字内容
     * @param {number} x - X坐标
     * @param {number} y - Y坐标
     * @param {number} fontSize - 字体大小
     */
    drawGoldStableText(text, x, y, fontSize) {
        const ctx = this.ctx;
        
        ctx.save();

        // 绘制阴影效果
        ctx.shadowColor = 'rgba(139, 69, 19, 0.5)';
        ctx.shadowBlur = 6;
        ctx.shadowOffsetX = 3;
        ctx.shadowOffsetY = 3;

        // 金色渐变
        const gradient = ctx.createLinearGradient(0, y - fontSize/2, 0, y + fontSize/2);
        gradient.addColorStop(0, '#FFD700');
        gradient.addColorStop(0.5, '#FFA500');
        gradient.addColorStop(1, '#FF8C00');

        ctx.fillStyle = gradient;
        ctx.strokeStyle = '#8B4513';
        ctx.lineWidth = 3;
        ctx.strokeText(text, x, y);
        ctx.fillText(text, x, y);

        ctx.restore();
    }

    /**
     * 绘制常规文字
     * @param {string} text - 文字内容
     * @param {number} x - X坐标
     * @param {number} y - Y坐标
     * @param {string} textColor - 文字颜色
     * @param {string} mode - 模式
     */
    drawRegularText(text, x, y, textColor, mode) {
        const ctx = this.ctx;
        
        // 覆盖模式添加文本描边效果
        if (mode === 'overlay') {
            ctx.strokeStyle = 'white';
            ctx.lineWidth = 4;
            ctx.strokeText(text, x, y);
        }

        ctx.fillStyle = textColor;
        ctx.fillText(text, x, y);
    }

    /**
     * 保存Canvas为Blob
     * @param {number} quality - 图片质量 (0-1)
     * @returns {Promise<Blob>}
     */
    toBlob(quality = 0.9) {
        return new Promise((resolve) => {
            this.canvas.toBlob(resolve, 'image/png', quality);
        });
    }

    /**
     * 获取Canvas的Base64数据
     * @param {number} quality - 图片质量 (0-1)
     * @returns {string}
     */
    toDataURL(quality = 0.9) {
        return this.canvas.toDataURL('image/png', quality);
    }

    /**
     * 清理资源
     */
    dispose() {
        this.customBackgroundImage = null;
        if (this.canvas && this.canvas.parentNode) {
            this.canvas.parentNode.removeChild(this.canvas);
        }
        this.canvas = null;
        this.ctx = null;
    }
}

// 全局实例，供页面直接使用
window.CanvasImageGenerator = CanvasImageGenerator;

// 创建全局生成器实例
window.canvasImageGenerator = new CanvasImageGenerator();
