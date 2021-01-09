from queue import Queue
from typing import Union
import discord
import asyncio
import youtube_dl
from discord.ext.commands import Bot, Cog, command, when_mentioned_or, Context
from pprint import pprint

bot = Bot(command_prefix=when_mentioned_or("-"))

ytdl_opts = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_opts = {"options": "-vn"}

ytdl = youtube_dl.YoutubeDL(ytdl_opts)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title")
        self.url = data.get("url")

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()

        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream)
        )

        # pprint(data)

        if "entries" in data:
            data = data["entries"][0]

        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_opts), data=data)


class Disco(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.music_queue: Queue[str] = Queue(maxsize=50)
        self.loop = asyncio.get_event_loop()
        self.ctx: Union[None, Context] = None
        self.bot.loop.create_task(self.play_music_from_queue())

    @staticmethod
    def _create_music_queue_resp(player, initial="queued ") -> str:
        resp: str = initial
        resp = f"{player.title}"
        if artist := player.data["artist"]:
            resp += f" by {artist}"
        if album := player.data["album"]:
            resp += f" from {album}"
        if release_year := player.data["release_year"]:
            resp += f", released {release_year}"
        return resp

    def _voice_client_after_handler(self, error):
        if error:
            print(f"player error {error}")
            return
        print("done with an item")
        self.music_queue.task_done()

    async def play_music_from_queue(self):
        print("executed this dude")
        while True:
            url = self.music_queue.get()
            print(f"got {url}")
            await self.join_channel()
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            resp = self._create_music_queue_resp(player, initial="now playing ")
            await self.ctx.send(resp)
            self.ctx.voice_client.play(player, after=self._voice_client_after_handler)

    async def join_channel(self):
        channel = self.ctx.author.voice.channel  # type: ignore
        if self.ctx.voice_client is not None:
            return await self.ctx.voice_client.move_to(channel)
        await channel.channel.connect()

    @command(aliases=["p"])
    async def play(self, ctx: Context, url: str):
        print("queue size", self.music_queue.qsize())
        if self.music_queue.full():
            return await ctx.send(
                "i cant hold anymore tracks right now, play a few and then give me some more"
            )
        self.ctx = ctx
        resp: str
        async with ctx.typing():
            self.music_queue.put(url)
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            resp = self._create_music_queue_resp(player)
        await ctx.send(resp)


# join a voice channel
# turn on bot "voice"
# find the video
# stream the video


bot.add_cog(Disco(bot))
bot.run("Nzk3NTQ0MzMxMTMyMjcyNjYw.X_oBCg.LheOBSPBlrIr8KR0TqY7wNMeDdI")