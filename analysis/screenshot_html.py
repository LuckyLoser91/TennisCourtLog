"""
将 HTML 文件截图为 PNG
依赖：pip install playwright && playwright install chromium
用法：python screenshot_html.py
"""

import os
from playwright.sync_api import sync_playwright

# ★ 按需修改
HTML_PATH  = "./cur_output/wta_gs_champions.html"
PNG_PATH   = "./cur_output/wta_gs_champions.png"
PAGE_WIDTH = 1200    # 页面宽度（px），影响表格布局


def screenshot(html_path, png_path, width=1200):
    abs_path = os.path.abspath(html_path)
    if not os.path.exists(abs_path):
        print(f"❌ 找不到文件: {abs_path}")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page    = browser.new_page(viewport={"width": width, "height": 900})

        page.goto(f"file:///{abs_path}")
        page.wait_for_timeout(800)   # 等待渲染完成

        # 截取整个页面（full_page=True 自动扩展到内容实际高度）
        page.screenshot(path=png_path, full_page=True)
        browser.close()

    print(f"✅ 截图已保存: {png_path}")


if __name__ == "__main__":
    screenshot(HTML_PATH, PNG_PATH, PAGE_WIDTH)