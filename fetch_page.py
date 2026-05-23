"""获取页面HTML用于分析结构"""

import asyncio
from playwright.async_api import async_playwright


async def main():
    url = "https://lol.fandom.com/wiki/CBLOL/2026_Season/Split_1_Playoffs/Scoreboards"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print(f"正在访问: {url}")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        
        # 等待页面加载
        await page.wait_for_timeout(3000)
        
        # 展开所有"Show"按钮
        show_buttons = await page.query_selector_all('button:has-text("Show")')
        print(f"找到 {len(show_buttons)} 个展开按钮")
        
        for i, button in enumerate(show_buttons):
            try:
                await button.click()
                await page.wait_for_timeout(500)
                print(f"已点击第 {i+1} 个按钮")
            except Exception as e:
                print(f"点击按钮 {i+1} 失败: {e}")
        
        # 等待展开完成
        await page.wait_for_timeout(2000)
        
        # 保存HTML
        html = await page.content()
        with open("page_structure.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        print("HTML已保存到 page_structure.html")
        
        # 截图
        await page.screenshot(path="page_screenshot.png", full_page=True)
        print("截图已保存到 page_screenshot.png")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
