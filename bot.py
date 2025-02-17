import json
import os

from enum import Enum

import aiohttp

import discord
from discord.ext import commands, tasks

from dotenv import load_dotenv

intents = discord.Intents.default()

load_dotenv()

guild_id = os.getenv("GUILD_ID")


class Tracks(Enum):
    barcelona = "Barcelona"
    brands_hatch = "Brands Hatch"
    cota = "Circuit of the Americas"
    donington = "Donington"
    hungaroring = "Hungaroring"
    imola = "Imola"
    indianapolis = "Indianapolis"
    kyalami = "Kyalami"
    laguna_seca = "Laguna Seca"
    misano = "Misano"
    monza = "Monza"
    mount_panorama = "Mount Panorama"
    nurburgring = "Nurburgring"
    nurburgring_24h = "Nordschleife"
    oulton_park = "Oulton Park"
    paul_ricard = "Paul Ricard"
    red_bull_ring = "Red Bull Ring"
    silverstone = "Silverstone"
    snetterton = "Snetterton"
    spa = "Spa"
    suzuka = "Suzuka"
    valencia = "Valencia"
    watkins_glen = "Watkins Glen"
    zandvoort = "Zandvoort"
    zolder = "Zolder"


car_types = [
    "Porsche 991 GT3 R (2018)",
    "Mercedes-AMG GT3 (2015)",
    "Ferrari 488 GT3 (2018)",
    "Audi R8 LMS (2015)",
    "Lamborghini Huracán GT3 (2015)",
    "McLaren 650S GT3 (2015)",
    "Nissan GT-R Nismo GT3 (2018)",
    "BMW M6 GT3 (2017)",
    "Bentley Continental GT3 (2018)",
    "Porsche 991 II GT3 Cup (2017)",
    "Nissan GT-R Nismo GT3 (2015)",
    "Bentley Continental GT3 (2015)",
    "AMR V12 Vantage GT3 (2013)",
    "Reiter Engineering R-EX GT3 (2017)",
    "Emil Frey Jaguar G3 (2012)",
    "Lexus RC F GT3 (2016)",
    "Lamborghini Huracan GT3 Evo (2019)",
    "Honda NSX GT3 (2017)",
    "Lamborghini Huracan SuperTrofeo (2015)",
    "Audi R8 LMS Evo (2019)",
    "AMR V8 Vantage (2019)",
    "Honda NSX GT3 Evo (2019)",
    "McLaren 720S GT3 (2019)",
    "Porsche 991 II GT3 R (2019)",
    "Ferrari 488 GT3 Evo (2020)",
    "Mercedes-AMG GT3 (2020)",
    "Ferrari 488 Challenge Evo (2020)",
    "BMW M2 Club Sport Racing (2020)",
    "Porsche 992 GT3 Cup (2021)",
    "Lamborghini Huracán SuperTrofeo EVO2 (2021)",
    "BMW M4 GT3 (2022)",
    "Audi R8 LMS GT3 Evo 2 (2022)",
    "Ferrari 296 GT3 (2023)",
    "Lamborghini Huracan GT3 Evo 2 (2023)",
    "Porsche 992 GT3 R (2023)",
    "McLaren 720S GT3 Evo (2023)",
    "Ford Mustang GT3 (2024)",
    "Alpine A110 GT4 (2018)",
    "Aston Martin Vantage GT4 (2018)",
    "Audi R8 LMS GT4 (2018)",
    "BMW M4 GT4 (2018)",
    "Chevrolet Camaro GT4 (2017)",
    "Ginetta G55 GT4 (2012)",
    "KTM X-Bow GT4 (2016)",
    "Maserati MC GT4 (2016)",
    "McLaren 570S GT4 (2016)",
    "Mercedes AMG GT4 (2016)",
    "Porsche 718 Cayman GT4 Clubsport (2019)",
    "Audi R8 LMS GT2 (2021)",
    "KTM XBOW GT2 (2021)",
    "Maserati MC20 GT2 (2023)",
    "Mercedes AMG GT2 (2023)",
    "Porsche 911 GT2 RS CS Evo (2023)",
    "Porsche 935 (2019)",
]


class DiscordBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            intents=intents, help_command=None, command_prefix=commands.when_mentioned
        )

        self.database = None

        self.database = json.load(open("db.json", "r+"))

    async def get_results(self) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{os.getenv('BASE_URL')}/api/results/list.json"
            ) as response:
                result_options = await response.json()

                async with session.get(
                    f"{os.getenv('BASE_URL')}{result_options['results'][0]['results_json_url']}"
                ) as response:
                    return await response.json()

    @tasks.loop(seconds=10.0)
    async def status_task(self) -> None:
        results = await self.get_results()

        track_name = results["trackName"]

        if results["Date"] in self.database.get(track_name, {}).get(
            "recorded_sessions", []
        ):
            return

        serialized_results = {
            f"{result['currentDriver']['firstName']} {result['currentDriver']['lastName']}": {
                "car": car_types[result["car"]["carModel"]],
                "bestSplits": result["timing"]["bestSplits"],
                "bestTime": result["timing"]["bestLap"],
            }
            for result in results["sessionResult"]["leaderBoardLines"]
        }

        if not self.database.get(track_name):
            self.database[track_name] = {"recorded_sessions": [], "best_times": {}}

        best_times = self.database[track_name]["best_times"]

        for name, result in serialized_results.items():
            if best_times.get(name, {}).get("best_time", 0) < result["bestTime"]:
                best_times[name] = result

        self.database[track_name]["recorded_sessions"].append(results["Date"])

        json.dump(self.database, open("db.json", "w+"), indent=4)

    async def setup_hook(self) -> None:
        self.status_task.start()

    async def on_ready(self) -> None:
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="Assetto Corsa Competizione"
            )
        )

        await self.tree.sync(guild=discord.Object(id=guild_id))


bot = DiscordBot()


def format_time(time: int) -> str:
    minutes, seconds = divmod(time, 60000)
    seconds, ms = divmod(seconds, 1000)

    return f"{minutes:02}:{seconds:02}.{ms:03}"


@bot.tree.command(
    name="times",
    description="Get the best times for a track",
    guild=discord.Object(id=guild_id),
)
@discord.app_commands.describe(
    track="Enter the track name",
)
async def times(interaction: discord.Interaction, track: Tracks):

    best_times = bot.database.get(track.name, {}).get("best_times", {})

    sorted_best_times = sorted(
        best_times.items(), key=lambda x: x[1]["bestTime"], reverse=False
    )

    if len(sorted_best_times) == 0:
        await interaction.response.send_message("No times found")
        return

    embed = discord.Embed(title=f"Best times for {track.value}", color=0x00FF00)

    for index, (name, result) in enumerate(sorted_best_times):
        splits = [split / 1000 for split in result["bestSplits"]]

        embed.add_field(
            name=f"{index + 1}. {name}",
            value=f"**Car:** {result['car']}\n**Time:** {format_time(result['bestTime'])}\n**Splits:** {' | '.join([str(split) for split in splits])}",
            inline=False,
        )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(
    name="delete",
    description="Deletes a time",
    guild=discord.Object(id=guild_id),
)
@discord.app_commands.describe(
    track="Enter the track name",
    name="Enter the name of the driver",
)
async def delete(interaction: discord.Interaction, track: Tracks, name: str):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(
            "You must have admin permissions to run this command", ephemeral=True
        )

    best_times = bot.database.get(track.name, {}).get("best_times", {})

    if not best_times.get(name):
        await interaction.response.send_message("No time found for this driver")
        return

    del best_times[name]

    json.dump(bot.database, open("db.json", "w+"), indent=4)

    await interaction.response.send_message("Time deleted")


bot.run(os.getenv("TOKEN"))
