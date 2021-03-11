import re

import lavalink
from discord.ext import commands

url_rx = re.compile(r'https?://(?:www\.)?.+')

class Music(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.get_guild(754135767999185029)
        self.channel = bot.get_channel(819045649487626280)

        if not hasattr(bot, 'lavalink'):  # This ensures the client isn't overwritten during cog reloads.
            bot.lavalink = lavalink.Client(bot.user.id)
            bot.lavalink.add_node('127.0.0.1', 2333, 'youshallnotpass', 'us', 'default-node')  # Host, Port, Password, Region, Name
            bot.add_listener(bot.lavalink.voice_update_handler, 'on_socket_response')

    def cog_unload(self):
        """Cog unload handler. This removes any event hooks that were registered."""
        self.bot.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, ctx):
        """Command before-invoke handler."""
        guild_check = ctx.guild is not None
        #  This is essentially the same as `@commands.guild_only()`
        #  except it saves us repeating ourselves (and also a few lines).

        if guild_check:
            await self.ensure_voice(ctx)
            #  Ensure that the bot and command author share a mutual voicechannel.

        return guild_check

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(error.original)
            # The above handles errors thrown in this cog and shows them to the user.
            # This shouldn't be a problem as the only errors thrown in this cog are from `ensure_voice`
            # which contain a reason string, such as "Join a voicechannel" etc. You can modify the above
            # if you want to do things differently.

    async def ensure_voice(self, ctx):
        """This check ensures that the bot and command author are in the same voicechannel."""
        player = self.bot.lavalink.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))
        # Create returns a player if one exists, otherwise creates.
        # This line is important because it ensures that a player always exists for a guild.

        # Most people might consider this a waste of resources for guilds that aren't playing, but this is
        # the easiest and simplest way of ensuring players are created.

        # These are commands that require the bot to join a voicechannel (i.e. initiating playback).
        # Commands such as volume/skip etc don't require the bot to be in a voicechannel so don't need listing here.
        should_connect = ctx.command.name in ('setup',)

        if not player.is_connected:
            if not should_connect:
                raise commands.CommandInvokeError('Not connected.')

            # permissions = ctx.author.voice.channel.permissions_for(ctx.me)

            # if not permissions.connect or not permissions.speak:  # Check user limit too?
            #     raise commands.CommandInvokeError('I need the `CONNECT` and `SPEAK` permissions.')

            player.store('channel', self.channel.id)
            await self.connect_to(str(self.channel.id))

    async def connect_to(self, channel_id: str):
        """A channel_id of `None` means disconnect."""
        ws = self.bot._connection._get_websocket(self.guild.id)
        await ws.voice_state(str(self.guild.id), channel_id)
        # The above looks dirty, we could alternatively use `bot.shards[shard_id].ws` but that assumes
        # the bot instance is an AutoShardedBot.

    @commands.command(aliases=['s'])
    async def setup(self, ctx):
        """Plays lofi in Lofi Study Room voice channel."""
        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
        query = "https://www.youtube.com/watch?v=DWcJFNfaw9c"

        # Get the results for the query from Lavalink.
        results = await player.node.get_tracks(query)

        track = results['tracks'][0]

        # You can attach additional information to audiotracks through kwargs, however this involves
        # constructing the AudioTrack class yourself.
        track = lavalink.models.AudioTrack(track, ctx.author.id, recommended=True)
        player.add(requester=ctx.author.id, track=track)

        # We don't want to call .play() if the player is playing as that will effectively skip
        # the current track.
        if not player.is_playing:
            await player.play()
        await ctx.send("Setup complete!")

def setup(bot):
    bot.add_cog(Music(bot))
