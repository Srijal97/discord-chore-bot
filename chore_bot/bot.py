# bot.py

import os
import json
import datetime
import pytz
import discord
from discord.ext import commands, tasks

from chore_manager import ChoreManager

# time zone for scheduling
TZ = pytz.timezone(os.environ.get("TIMEZONE", "US/Eastern"))

# file paths
CONFIG_FILE = os.environ.get("CONFIG_FILE", "config.json")
STATE_FILE = os.environ.get("STATE_FILE", "state.json")
CHANNEL_ID = int(os.environ.get("CHORE_CHANNEL_ID", "1275242284358565928"))  # set this env var

intents = discord.Intents.default()
intents.message_content = True      # needed to read !commands in guild channels
intents.members = True              # only if you need to do guild.members
intents.guilds = True               # usually on by default, but safe to ensure

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
chore_manager: ChoreManager  # will init in on_ready


@bot.event
async def on_ready():
    global chore_manager
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    # grab all non-bot member names
    guild = bot.guilds[0]
    members = [m.name for m in guild.members if not m.bot]
    chore_manager = ChoreManager(members, CONFIG_FILE, state_file=STATE_FILE)
    # kick off daily notification at 6:00
    send_daily_chores.start()
    print("ChoreManager initialized and daily task started.")


@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TZ))
async def send_daily_chores():
    if CHANNEL_ID == 0:
        return
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(_format_assignments())


def _format_assignments() -> str:
    today = datetime.datetime.now(TZ).strftime("%A")
    daily = chore_manager.daily_assignments()
    weekly = chore_manager.weekly_assignments(today)

    lines = ["**Today's Chores:**"]
    for chore, person in daily.items():
        lines.append(f"- {chore}: **{person}**")
    if weekly:
        lines.append(f"\n**{today}'s Weekly Chores:**")
        for chore, person in weekly.items():
            lines.append(f"- {chore}: **{person}**")
    return "\n".join(lines)


@bot.command()
async def chores(ctx: commands.Context):
    """Display today's chores."""
    await ctx.send(_format_assignments())


@bot.command()
async def done(ctx: commands.Context, arg: str = None):
    """
    Mark a chore as done.
    If arg is an integer, marks that numbered chore.
    If omitted, marks all of your chores.
    """
    member = ctx.author.name
    # try to parse integer first
    chore_arg: int | None
    try:
        chore_arg = int(arg) if arg else None
    except ValueError:
        chore_arg = arg  # treat as string
    ok = chore_manager.mark_as_done(member, chore_arg)
    if ok:
        await ctx.send(f"{member}, marked `{arg or 'all your chores'}` as done.")
    else:
        await ctx.send(f"Could not find chore `{arg}` to mark done.")


@bot.command()
async def inactive(ctx: commands.Context, member: str = None):
    """
    Mark a member inactive (they'll be skipped).
    If no member is given, marks you.
    """
    who = member or ctx.author.name
    chore_manager.add_inactive_member(who)
    await ctx.send(f"Marked **{who}** as inactive.")


@bot.command()
async def active(ctx: commands.Context, member: str = None):
    """
    Mark a member active again.
    If no member is given, marks you.
    """
    who = member or ctx.author.name
    chore_manager.remove_inactive_member(who)
    await ctx.send(f"Marked **{who}** as active.")


@bot.command()
async def help(ctx: commands.Context):
    """Display help message."""
    message = "Here are the available commands:\n"
    message += "!chores: Display today's chores.\n"
    message += "!done [chore]: Mark a chore as done. If unspecified, all of your chores will be marked as done.\n"
    message += "!inactive [member]: Mark a member as inactive. If unspecified, you will be marked as inactive.\n"
    message += "!active [member]: Mark a member as active. If unspecified, you will be marked as active.\n"
    message += "!help: Display this message."
    await ctx.send(message)


if __name__ == "__main__":
    TOKEN = os.environ["DISCORD_BOT_TOKEN"]
    bot.run(TOKEN)
