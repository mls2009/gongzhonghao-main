import os
import base64
from typing import List, Dict
from playwright.async_api import async_playwright


def _read_canvas_script() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    js_path = os.path.normpath(os.path.join(here, '..', 'static', 'js', 'canvas-image-generator.js'))
    with open(js_path, 'r', encoding='utf-8') as f:
        return f.read()


async def render_image_dataurl(template_config: Dict, text_lines: List[str], mode: str) -> str:
    """Use headless Chromium to render image via the shared Canvas generator; return data URL string."""
    script = _read_canvas_script()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content('<html><head></head><body></body></html>')
        await page.add_script_tag(content=script)

        data_url = await page.evaluate(
            """
            (args) => {
                const { cfg, lines, mode } = args || {};
                const gen = (window.canvasImageGenerator) ? window.canvasImageGenerator : new window.CanvasImageGenerator();
                // ensure a canvas exists
                let canvas = document.getElementById('gen');
                if (!canvas) {
                    canvas = document.createElement('canvas');
                    canvas.id = 'gen';
                    document.body.appendChild(canvas);
                }
                gen.initialize('gen', 750, 1000);
                return gen.generateImage(cfg || {}, lines || [], mode || 'insert');
            }
            """,
            {"cfg": template_config, "lines": text_lines, "mode": mode}
        )
        await context.close()
        await browser.close()
        return data_url


def save_dataurl_to_file(data_url: str, output_path: str):
    if ',' in data_url:
        b64 = data_url.split(',', 1)[1]
    else:
        b64 = data_url
    data = base64.b64decode(b64)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(data)
