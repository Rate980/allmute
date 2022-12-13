import asyncio
import typing

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
    async def switch(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
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

    async def dead_presses(self, user: discord.Member) -> typing.Optional[str]:
        if user.voice is None:
            return "please join vc"

        if user.voice.channel != self.channel:
            return "vc tigau"

        self.dead_.append(user)
        if self.is_mute:
            await user.edit(mute=True)

    @discord.ui.button(label="dead", style=discord.ButtonStyle.primary)
    async def dead(self, interaction: discord.Interaction, _: typing.Any) -> None:
        if not isinstance(user := interaction.user, discord.Member):
            await interaction.response.send_message("not allow DM", ephemeral=True)
            return

        if (mes := await self.dead_presses(user)) is not None:
            await interaction.response.send_message(mes, ephemeral=True)
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


class AllMute(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.data: dict[int, tuple[discord.Message, ChangeView]] = {}

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, mem: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:

        if after.channel is not None:
            return

        if before.channel is None:
            return

        # print(before.channel.members)
        if before.channel.members != []:
            return
        # print(self.data)
        channel_id = before.channel.id
        await self.data[channel_id][0].delete()
        self.data.pop(channel_id)

    @commands.hybrid_command()
    async def join(self, ctx: commands.Context) -> None:
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
                await mes[0].fetch()
                await ctx.send("already joined")
                return
            except discord.NotFound:
                pass
        if ctx.interaction is None:
            await ctx.message.delete()

        view = ChangeView(voice_channel)

        self.data[voice_channel.id] = (
            await ctx.send(voice_channel.name, view=view),
            view,
        )

        # print(self.data[voice_channel.id].components)

    @commands.hybrid_command()
    async def dead(self, ctx: commands.Context, user: discord.Member) -> None:
        if ctx.interaction is not None:
            await ctx.interaction.response.send_message("dead", ephemeral=True)

        if (mes := self.data.get(user.voice.channel.id)) is None:
            return

        view = mes[1]
        await view.dead_presses(user)


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

            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            await self.tree.sync()

    bot = MyBot("t!", intents=intents)
    bot.run(token)
