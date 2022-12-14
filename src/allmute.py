import asyncio
import typing
from typing import Any

import discord
from discord.ext import commands


class MuteDict(typing.TypedDict):
    mute: bool
    deafen: bool


def make_dict(is_mute: bool) -> tuple[MuteDict, MuteDict]:
    if is_mute:
        return (MuteDict(mute=True, deafen=True), MuteDict(mute=False, deafen=False))
    else:
        return (MuteDict(mute=False, deafen=False), MuteDict(mute=True, deafen=False))


class ChangeView(discord.ui.View):
    def __init__(self, channel: discord.VoiceChannel | discord.StageChannel) -> None:
        super().__init__()
        self.dead_: list[discord.Member] = []
        self.is_mute = False
        self.channel = channel

    @discord.ui.button(label="switch", style=discord.ButtonStyle.primary)
    async def switch(self, interaction: discord.Interaction, _: Any) -> None:
        self.is_mute = not self.is_mute
        alive, dead = make_dict(self.is_mute)
        tasks = [
            asyncio.create_task(x.edit(**alive))
            for x in self.channel.members
            if x not in self.dead_
        ]
        tasks += [asyncio.create_task(x.edit(**dead)) for x in self.dead_]

        # await interaction.response.send_message("switch", ephemeral=True)
        await interaction.response.edit_message(view=self)
        await asyncio.wait(tasks)

    @discord.ui.button(label="dead", style=discord.ButtonStyle.primary)
    async def dead(self, interaction: discord.Interaction, _: Any) -> None:
        if not isinstance(user := interaction.user, discord.Member):
            await interaction.response.send_message("not allow DM", ephemeral=True)
            return

        if user.voice is None:
            await interaction.response.send_message("please join vc", ephemeral=True)
            return

        if user.voice.channel != self.channel:
            await interaction.response.send_message("vc tigau", ephemeral=True)
            return

        self.dead_.append(user)
        if not self.is_mute:
            _, args = make_dict(self.is_mute)
            await user.edit(**args)
        # await interaction.response.send_message("dead", ephemeral=True)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="reset", style=discord.ButtonStyle.green)
    async def reset(self, interaction: discord.Interaction, _: typing.Any) -> None:
        self.dead_ = []
        tasks = [
            asyncio.create_task(x.edit(mute=False, deafen=False))
            for x in self.channel.members
        ]
        self.is_mute = False
        # await interaction.response.send_message("reset", ephemeral=True)
        await interaction.response.edit_message(view=self)
        await asyncio.wait(tasks)

    @discord.ui.button(label="leave", style=discord.ButtonStyle.danger)
    async def leave(self, interaction: discord.Interaction, _: typing.Any) -> None:
        self.clear_items()
        await interaction.response.edit_message(view=self)
        if interaction.message is None:
            return

        await interaction.message.delete()


class DeadView(discord.ui.View):
    def __init__(self, change_view: ChangeView) -> None:
        super().__init__()
        self.change_view = change_view


class AllMute(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.data: dict[int, discord.Message] = {}

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, mem: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:

        if after.channel is not None:
            return
        if before.channel is None:
            return

        if len(before.channel.members) != 1:
            return

        await self.data[before.channel.id].delete()

    @commands.hybrid_command()
    async def join(self, ctx: commands.Context[typing.Any]) -> None:
        if not isinstance(ctx.author, discord.Member):
            await ctx.send("not allow DM")
            return

        if ctx.author.voice is None:
            await ctx.send("join vc")
            return

        if ctx.author.voice.channel is None:
            await ctx.send("join vc")
            return

        voice_channel = ctx.author.voice.channel
        if (mes := self.data.get(voice_channel.id)) is not None:
            try:
                await mes.fetch()
                await ctx.send("already joined")
                return
            except discord.NotFound:
                pass
        view = ChangeView(voice_channel)

        self.data[voice_channel.id] = await ctx.send(voice_channel.name, view=view)
        print(self.data[voice_channel.id].components)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AllMute(bot))


if __name__ == "__main__":
    import os
    from pathlib import Path

    import discord
    from dotenv import load_dotenv

    load_dotenv()

    file = Path(__file__).resolve()
    prefix = file.parent
    try:
        token = os.environ["token"]
    except KeyError:
        token = os.environ["DIS_TEST_TOKEN"]

    intents = discord.Intents.all()

    class MyBot(commands.Bot):
        async def on_ready(self) -> None:
            print("ready")

        async def setup_hook(self) -> None:
            await self.load_extension(file.stem)
            guild_id = 524972650548953126
            guild = self.get_guild(guild_id)
            if guild is None:
                guild = await self.fetch_guild(guild_id)

            await self.tree.sync(guild=guild)
            await self.tree.sync()

    bot = MyBot("t!", intents=intents)
    bot.run(token)
