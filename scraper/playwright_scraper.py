"""使用Playwright抓取LOL Fandom Scoreboard页面数据"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger(__name__)


@dataclass
class PlayerData:
    """玩家数据"""
    team: str  # blue/red
    player_name: str
    champion: str
    summoner_spells: str
    role: str
    kills: int
    deaths: int
    assists: int
    cs: int
    gold: int
    towers: int
    items: str


@dataclass
class GameData:
    """单局比赛数据"""
    game_number: int
    duration: str
    winner: str
    external_id: str
    players: list[PlayerData]


@dataclass
class SeriesData:
    """系列赛数据"""
    tournament: str
    blue_team: str
    red_team: str
    blue_score: int
    red_score: int
    winner: str
    external_id: str
    games: list[GameData]


class PlaywrightScraper:
    """Playwright爬虫"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Browser | None = None
        self.page: Page | None = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """启动浏览器"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        logger.info("浏览器已启动")

    async def close(self):
        """关闭浏览器"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        logger.info("浏览器已关闭")

    async def scrape_series(self, url: str) -> list[SeriesData]:
        """
        抓取系列赛数据

        Args:
            url: 目标页面URL

        Returns:
            系列赛数据列表
        """
        if not self.page:
            raise RuntimeError("浏览器未启动，请先调用start()")

        logger.info(f"[步骤1] 开始抓取: {url}")
        try:
            logger.info("[步骤2] 正在打开网页...")
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            logger.info("[步骤3] 页面加载完成")
        except Exception as e:
            logger.error(f"[步骤2失败] 打开网页失败: {e}")
            raise

        # 等待scoreboard表格出现
        try:
            logger.info("[步骤4] 等待scoreboard表格出现...")
            await self.page.wait_for_selector("table.sb", timeout=10000)
            logger.info("[步骤5] Scoreboard表格已加载")
        except Exception as e:
            logger.warning(f"[步骤4警告] 等待scoreboard表格超时: {e}")

        # 立即展开所有"Show Round"按钮
        logger.info("[步骤6] 正在展开所有Show Round按钮...")
        await self._expand_all_rounds()

        # 等待展开完成
        await self.page.wait_for_timeout(1000)
        logger.info("[步骤7] 展开完成")

        # 调试：保存页面HTML和截图
        logger.info("[步骤7.1] 保存调试信息...")
        await self._save_debug_info()
        logger.info("[步骤7.2] 调试信息保存完成")

        # 解析系列赛数据
        logger.info("[步骤8] 开始解析系列赛数据...")
        series_list = await self._parse_series()

        logger.info(f"[步骤9] 抓取完成，共 {len(series_list)} 个系列赛")
        return series_list

    async def _expand_all_rounds(self):
        """展开所有Show Round按钮"""
        logger.info("[步骤6.1] 查找所有Show按钮...")

        # 查找所有包含"Show"文本的按钮
        show_buttons = await self.page.query_selector_all('button:has-text("Show")')
        logger.info(f"[步骤6.2] 找到 {len(show_buttons)} 个Show按钮")

        for i, button in enumerate(show_buttons):
            try:
                logger.info(f"[步骤6.3] 点击第 {i+1}/{len(show_buttons)} 个按钮...")
                await button.click()
                await self.page.wait_for_timeout(300)
                logger.info(f"[步骤6.4] 第 {i+1} 个按钮点击成功")
            except Exception as e:
                logger.error(f"[步骤6.4失败] 第 {i+1} 个按钮点击失败: {e}")

        logger.info(f"[步骤6.5] 已点击 {len(show_buttons)} 个展开按钮")

    async def _save_debug_info(self):
        """保存调试信息：HTML和截图"""
        try:
            # 保存HTML
            html = await self.page.content()
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(html)
            logger.info("[调试] HTML已保存到 debug_page.html")

            # 保存截图
            await self.page.screenshot(path="debug_page.png", full_page=True)
            logger.info("[调试] 截图已保存到 debug_page.png")
        except Exception as e:
            logger.error(f"[调试] 保存调试信息失败: {e}")

    async def _debug_dom_matching(self):
        """调试：打印各种selector的匹配数量"""
        logger.info("[调试] 开始DOM匹配分析...")

        selectors = [
            "table.sb",
            ".match-block",
            ".series-block",
            ".game-block",
            "div.match",
            "div.series",
            "div.game",
            ".sb-match",
            ".sb-series",
            "tr.sb-row",
        ]

        for selector in selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                logger.info(f"[调试] Selector: '{selector}', 找到: {len(elements)} 个")
            except Exception as e:
                logger.warning(f"[调试] Selector: '{selector}', 查询失败: {e}")

    async def _debug_selector_failure(self, selector: str):
        """调试：selector失败时输出详细信息"""
        logger.error(f"[调试] Selector '{selector}' 匹配失败，输出详细信息...")

        try:
            # 获取页面body的HTML片段
            body = await self.page.query_selector("body")
            if body:
                body_html = await body.inner_html()
                logger.error(f"[调试] Body HTML片段 (前2000字符):\n{body_html[:2000]}")

            # 尝试查找父节点
            parent_selectors = [
                "div",
                "main",
                "#content",
                ".content",
                ".page-content",
                "#mw-content-text",
            ]

            for parent_selector in parent_selectors:
                try:
                    parent = await self.page.query_selector(parent_selector)
                    if parent:
                        parent_class = await parent.get_attribute("class")
                        logger.info(f"[调试] 找到父节点: '{parent_selector}', class: '{parent_class}'")
                except:
                    pass

        except Exception as e:
            logger.error(f"[调试] 获取详细信息失败: {e}")

    async def _parse_series(self) -> list[SeriesData]:
        """解析系列赛数据"""
        series_list = []

        # 调试：打印各种selector的匹配数量
        await self._debug_dom_matching()

        # 查找所有scoreboard表格
        sb_tables = await self.page.query_selector_all("table.sb")
        logger.info(f"[步骤8.1] Selector: 'table.sb', 找到 {len(sb_tables)} 个scoreboard表格")

        if len(sb_tables) == 0:
            logger.error("[步骤8.1失败] 未找到任何scoreboard表格！")
            await self._debug_selector_failure("table.sb")
            return series_list

        for i, table in enumerate(sb_tables):
            try:
                logger.info(f"[步骤8.2] 正在解析第 {i+1}/{len(sb_tables)} 个系列赛表格...")
                series = await self._parse_series_table(table)
                if series:
                    series_list.append(series)
                    logger.info(f"[步骤8.3] 第 {i+1} 个系列赛解析成功: {series.blue_team} vs {series.red_team}")
            except Exception as e:
                logger.error(f"[步骤8.3失败] 第 {i+1} 个系列赛表格解析失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue

        logger.info(f"[步骤8.4] 系列赛解析完成，共 {len(series_list)} 个")
        return series_list

    async def _parse_series_table(self, table) -> SeriesData | None:
        """解析单个系列赛表格"""
        try:
            # 获取队伍名称
            team_names = await table.query_selector_all("th.sb-teamname .teamname a")
            if len(team_names) < 2:
                logger.warning("队伍名称不足2个，跳过")
                return None

            blue_team = await team_names[0].inner_text()
            red_team = await team_names[1].inner_text()
            logger.info(f"[步骤8.2.1] 队伍: {blue_team} vs {red_team}")

            # 获取比分
            score_cells = await table.query_selector_all("th.side-blue, th.side-red")
            blue_score = 0
            red_score = 0

            if len(score_cells) >= 2:
                blue_score_text = await score_cells[0].inner_text()
                red_score_text = await score_cells[1].inner_text()
                try:
                    blue_score = int(blue_score_text.strip())
                    red_score = int(red_score_text.strip())
                    logger.info(f"[步骤8.2.2] 比分: {blue_score}-{red_score}")
                except ValueError:
                    logger.warning(f"[步骤8.2.2警告] 比分解析失败: {blue_score_text} vs {red_score_text}")

            # 确定胜者
            winner = None
            if blue_score > red_score:
                winner = blue_team
            elif red_score > blue_score:
                winner = red_team

            # 生成external_id (使用队伍名称组合)
            external_id = f"{blue_team}_vs_{red_team}".replace(" ", "_")

            # 解析游戏数据
            logger.info(f"[步骤8.2.3] 开始解析游戏数据...")
            games = await self._parse_games(table, blue_team, red_team)
            logger.info(f"[步骤8.2.4] 游戏解析完成，共 {len(games)} 局")

            # 创建系列赛数据
            series_data = SeriesData(
                tournament="CBLOL 2026 Split 1 Playoffs",
                blue_team=blue_team,
                red_team=red_team,
                blue_score=blue_score,
                red_score=red_score,
                winner=winner,
                external_id=external_id,
                games=games
            )

            logger.info(f"[步骤8.2.5] 系列赛数据创建完成: {blue_team} vs {red_team} ({blue_score}-{red_score}), {len(games)} 局")
            return series_data
        except Exception as e:
            logger.error(f"[步骤8.2失败] 解析系列赛表格失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    async def _parse_games(self, table, blue_team: str, red_team: str) -> list[GameData]:
        """解析单局比赛数据"""
        games = []

        # 查找所有游戏show按钮（排除Round级别的按钮）
        show_buttons = await table.query_selector_all("span.sections-toggler")
        logger.info(f"[步骤8.2.3.1] 找到 {len(show_buttons)} 个sections-toggler按钮")

        # 过滤出游戏级别的show按钮（包含g1, g2等）
        game_buttons = []
        for button in show_buttons:
            try:
                class_list = await button.get_attribute("class")
                if class_list and any(f"g{i}" in class_list for i in range(1, 10)):
                    game_buttons.append(button)
            except:
                pass

        logger.info(f"[步骤8.2.3.2] 过滤后找到 {len(game_buttons)} 个游戏展开按钮")

        game_number = 0
        for i, button in enumerate(game_buttons):
            try:
                button_text = await button.inner_text()
                if "show" not in button_text.lower():
                    continue

                game_number += 1
                logger.info(f"[步骤8.2.3.3] 正在解析 Game {game_number}...")

                # 点击展开按钮
                await button.click()
                await self.page.wait_for_timeout(500)
                logger.info(f"[步骤8.2.3.4] Game {game_number} 展开按钮点击成功")

                # 解析游戏详情
                game_data = await self._parse_game_detail(table, game_number, blue_team, red_team)
                if game_data:
                    games.append(game_data)
                    logger.info(f"[步骤8.2.3.5] Game {game_number} 解析成功，玩家数: {len(game_data.players)}")
                else:
                    logger.warning(f"[步骤8.2.3.5警告] Game {game_number} 解析返回空数据")

            except Exception as e:
                logger.error(f"[步骤8.2.3.5失败] 解析游戏 {game_number} 失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue

        logger.info(f"[步骤8.2.3.6] 游戏解析完成，共 {len(games)} 局")
        return games

    async def _parse_game_detail(self, table, game_number: int, blue_team: str, red_team: str) -> GameData | None:
        """解析单局比赛详情"""
        # 这里需要根据实际展开后的HTML结构解析玩家数据
        # 暂时返回基础数据
        game_data = GameData(
            game_number=game_number,
            duration="",
            winner="",
            external_id=f"{blue_team}_vs_{red_team}_game{game_number}",
            players=[]
        )
        return game_data


async def scrape_url(url: str, headless: bool = True) -> list[SeriesData]:
    """
    抓取指定URL的系列赛数据

    Args:
        url: 目标页面URL
        headless: 是否使用无头模式

    Returns:
        系列赛数据列表
    """
    async with PlaywrightScraper(headless=headless) as scraper:
        return await scraper.scrape_series(url)
