import io

import json

import os
import asyncio

from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

import math

from utils.Types import Tracks
from utils.ACCServer import format_data, get_result, get_results_list, get_page
from utils.ImageHandler import format_data as format_data_image, gen_image


def format_time(time: int) -> str:
    minutes, seconds = divmod(time, 60000)
    seconds, ms = divmod(seconds, 1000)

    return f"{minutes:02}:{seconds:02}.{ms:03}"


class Confirm(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "Database has been updated", ephemeral=True
        )
        self.value = True
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Ok! I won't update", ephemeral=True)
        self.value = False
        self.stop()


class Timing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="times",
        description="Get the best times for a track",
    )
    @app_commands.describe(
        track="Enter the track name",
    )
    async def times(self, interaction: discord.Interaction, track: Tracks):
        data = format_data_image(self.bot.database[track.name])

        image = gen_image(data)

        await interaction.response.send_message(
            f"Here are the best times for {Tracks[track.name].value}!",
            file=discord.File(filename=f"{track.name}.png", fp=image),
        )

    @app_commands.command(
        description="Deletes a time",
    )
    @app_commands.describe(
        track="Enter the track name",
        userid="Enter the name of the driver. Providing no user will show all the user ids",
    )
    async def delete(
        self, interaction: discord.Interaction, track: Tracks, userid: str = ""
    ):
        if (
            not interaction.user.guild_permissions.administrator
            or interaction.user.id != int(os.getenv("OWNER_ID"))
        ):
            return await interaction.response.send_message(
                "You must have admin permissions to run this command", ephemeral=True
            )

        if userid == "":
            msg = ""

            best_times = self.bot.database.get(track.name, {})

            for index, result in best_times.items():
                msg += f"{index}. {result['name']}\n"

            await interaction.response.send_message(msg)

        user = self.bot.database.get(track.name, {}).get(userid, {})

        if not user:
            await interaction.response.send_message("No time found for this driver")
            return

        del self.bot.database[track.name][userid]

        json.dump(self.bot.database, open("db.json", "w+"), indent=4)

        await interaction.response.send_message("Time deleted")

    @app_commands.command(
        name="sync",
        description="Manually syncs all the times",
    )
    @app_commands.describe(
        from_date="Enter a date to sync from. Use the format MM-DD-YYYY",
    )
    async def sync(self, interaction: discord.Interaction, from_date: str = ""):
        if (
            not interaction.user.guild_permissions.administrator
            and interaction.user.id != int(os.getenv("OWNER_ID"))
        ):
            return await interaction.response.send_message(
                "You must have admin permissions to run this command", ephemeral=True
            )

        self.sync_loop.stop()

        await interaction.response.send_message(
            "Syncing times, please wait.", ephemeral=False
        )

        results_list = await get_results_list()

        time_to_fetch = math.floor(len(results_list) / 4) * 20

        await interaction.edit_original_response(
            content=f"Syncing times, please wait. Estimated time: {time_to_fetch+20} seconds."
        )

        from_date = datetime.strptime(from_date, "%m-%d-%Y")

        await asyncio.sleep(20)

        temp_db = {}

        rate_limit_counter = 0

        for i, result_url in enumerate(results_list, 1):
            if rate_limit_counter == 4:
                await asyncio.sleep(20)
                rate_limit_counter = 0

            result = await get_result(result_url["results_json_url"])

            if from_date:
                result_date = datetime.strptime(result["Date"], "%Y-%m-%dT%H:%M:%SZ")

                if result_date < from_date:
                    break

            track_name = result["trackName"]

            result_data = temp_db.get(track_name, {})

            for driver_id, data in format_data(result).items():
                bestLap = data["bestLap"]

                if (
                    result_data.get(driver_id, {"bestLap": 900000})["bestLap"] > bestLap
                    and bestLap > 60000
                    and bestLap < 900000
                ):
                    result_data[driver_id] = data

            temp_db[track_name] = result_data

            await interaction.edit_original_response(
                content=f"Syncing times, please wait. Estimated time: {time_to_fetch - math.floor(i / 4)*20} seconds. Progress: {i} of {len(results_list)} entries."
            )

            rate_limit_counter += 1

        buttons = Confirm()

        await interaction.edit_original_response(
            content=f"Sync complete! Here is the raw results. Should I overwrite the current database?",
            attachments=[
                discord.File(
                    filename="results.json",
                    fp=io.BytesIO(json.dumps(temp_db, indent=4).encode()),
                )
            ],
            view=buttons,
        )

        await buttons.wait()

        await interaction.edit_original_response(view=None)

        if buttons.value is None:
            await interaction.edit_original_response(
                content="Timed out...Database not updated"
            )

        if buttons.value:
            self.bot.database = temp_db
            json.dump(self.bot.database, open("db.json", "w+"), indent=4)

        self.sync_loop.restart()

    @app_commands.command(
        name="reset_loop",
        description="Manually syncs all the times",
    )
    async def reset_loop(self, interaction: discord.Interaction):
        if interaction.user.id != int(os.getenv("OWNER_ID")):
            return await interaction.response.send_message(
                "You must be the bot owner to run this command", ephemeral=True
            )

        self.sync_loop.restart()
        await interaction.response.send_message("Loop restarted")

    @tasks.loop(minutes=2)
    async def sync_loop(self):
        results_url = await get_page()
        results = await get_result(results_url["results"][0]["results_json_url"])

        if not self.bot.database.get(results["trackName"]):
            self.bot.database[results["trackName"]] = {}

        temp_db = self.bot.database.get(results["trackName"], {})

        for driver_id, data in format_data(results).items():
            bestLap = data["bestLap"]

            if (
                temp_db.get(driver_id, {"bestLap": 900000})["bestLap"] > bestLap
                and bestLap > 60000
                and bestLap < 900000
            ):
                temp_db[driver_id] = data

        self.bot.database[results["trackName"]] = temp_db
        json.dump(self.bot.database, open("db.json", "w+"), indent=4)


async def setup(bot):
    await bot.add_cog(Timing(bot))
    bot.get_cog("Timing").sync_loop.start()
