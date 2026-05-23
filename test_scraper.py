"""测试Playwright爬虫"""

import asyncio
import logging
import sys

from scraper.playwright_scraper import scrape_url

# 配置日志输出到控制台
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

async def main():
    url = "https://lol.fandom.com/wiki/CBLOL/2026_Season/Split_1_Playoffs/Scoreboards"

    print(f"开始抓取: {url}")

    try:
        series_list = await scrape_url(url, headless=False)

        print(f"\n抓取完成，共 {len(series_list)} 个系列赛")

        for series in series_list:
            print(f"\n系列赛: {series.blue_team} vs {series.red_team}")
            print(f"  比分: {series.blue_score}-{series.red_score}")
            print(f"  胜者: {series.winner}")
            print(f"  小局数: {len(series.games)}")

            for game in series.games:
                print(f"    Game {game.game_number}: {game.duration}, 胜者: {game.winner}")
                print(f"      玩家数: {len(game.players)}")

    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
