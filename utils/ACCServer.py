import os

import aiohttp
import asyncio


async def get_result(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(os.getenv("BASE_URL") + url) as response:
            if response.status == 429:
                await asyncio.sleep(5)
                return await get_result(url)

            return await response.json()


async def get_page(page: int = 0) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{os.getenv('BASE_URL')}/api/results/list.json?page={page}"
        ) as response:
            if response.status == 429:
                await asyncio.sleep(5)
                return await get_page(page)

            return await response.json()


async def get_results_list() -> dict:
    first_results_list = await get_page()

    results_list = first_results_list["results"]

    # Check if there are more pages
    if first_results_list["num_pages"] > 1:
        for page_num in range(1, first_results_list["num_pages"] - 1):
            page_results = await get_page(page_num)

            results_list.extend(page_results["results"])

            # To prevent rate limiting
            if page_num % 5 == 0:
                await asyncio.sleep(25)

    return results_list


def format_data(result):
    data = {}

    for driver in result["sessionResult"]["leaderBoardLines"]:
        best_splits = []

        best_splits = next(
            (
                lap["splits"]
                for lap in result["laps"]
                if lap["laptime"] == driver["timing"]["bestLap"]
            ),
            None,
        )

        data[driver["currentDriver"]["playerId"]] = {
            "bestLap": driver["timing"]["bestLap"],
            "bestSplits": best_splits,
            "car": driver["car"]["carModel"],
            "name": driver["currentDriver"]["firstName"]
            + " "
            + driver["currentDriver"]["lastName"],
        }

    return data
