import json
import os

import discord
from discord.ext import commands

from dotenv import load_dotenv

intents = discord.Intents.default()

load_dotenv(override=True)

cogs = []


class DiscordBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            intents=intents, help_command=None, command_prefix=commands.when_mentioned
        )

        self.database = None

        self.database = json.load(open("db.json", "r+"))

    async def load_cogs(self) -> None:
        for file in os.listdir(f"{os.path.realpath(os.path.dirname(__file__))}/cogs"):
            if file.endswith(".py"):
                extension = file[:-3]
                try:
                    await self.load_extension(f"cogs.{extension}")
                    cogs.append(extension)
                    print(f"Loaded extension {extension}.")
                except Exception as e:
                    print(f"Failed to load extension {extension}.")
                    print(e)

    async def sync_commands(self) -> None:
        guild = discord.Object(id=os.getenv("GUILD_ID"))

        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def setup_hook(self):
        await self.load_cogs()

        await self.sync_commands()

    async def on_ready(self) -> None:
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="Assetto Corsa Competizione"
            )
        )

        print("Logged in as", self.user)


bot = DiscordBot()


@bot.tree.command(
    name="reload_cogs",
    description="Reloads all cogs",
)
async def reload_cogs(interaction: discord.Interaction):
    if interaction.user.id != int(os.getenv("OWNER_ID")):
        return await interaction.response.send_message(
            "You must be the owner to run this command", ephemeral=True
        )

    for cog in cogs:
        await bot.reload_extension(f"cogs.{cog}")

    await interaction.response.send_message("Reloaded cogs")
    await bot.sync_commands()


bot.run(os.getenv("TOKEN"))
