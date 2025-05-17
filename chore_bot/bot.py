# bot.py

import os
import json
import datetime
import pytz
import discord
from discord.ext import commands, tasks
from pathlib import Path

from chore_manager import ChoreManager

# time zone for scheduling
TZ = pytz.timezone(os.environ.get("TIMEZONE", "US/Eastern"))

# file paths
CONFIG_FILE = os.environ.get("CONFIG_FILE", "config.json")
STATE_FILE = os.environ.get("STATE_FILE", "state.json")
MEMBERS_FILE = os.environ.get("MEMBERS_FILE", "members.json")
CHANNEL_ID = int(os.environ.get("CHORE_CHANNEL_ID", "1275242284358565928"))  # set this env var

intents = discord.Intents.default()
intents.message_content = True      # needed to read !commands in guild channels
intents.members = True              # only if you need to do guild.members
intents.guilds = True               # usually on by default, but safe to ensure

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
chore_manager: ChoreManager  # will init in on_ready


def load_member_ids() -> list[int]:
    p = Path(MEMBERS_FILE)
    if not p.exists():
        p.write_text(json.dumps({"members": []}, indent=2))
        return []
    data = json.loads(p.read_text())
    return data.get("members", [])


def save_member_ids(ids: list[int]) -> None:
    Path(MEMBERS_FILE).write_text(json.dumps({"members": ids}, indent=2))


def build_chore_manager(guild: discord.Guild) -> ChoreManager:
    """Load roster, map to display_names, and return a fresh ChoreManager."""
    ids = load_member_ids()
    names = []
    for uid in ids:
        member = guild.get_member(uid)
        if member:
            names.append(member.display_name)
    return ChoreManager(names, CONFIG_FILE, state_file=STATE_FILE)


@bot.event
async def on_ready():
    global chore_manager
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    guild = bot.guilds[0]
    chore_manager = build_chore_manager(guild)
    send_daily_chores.start()
    print("ChoreManager initialized with roster:", chore_manager.members)


@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TZ))
async def send_daily_chores():
    if CHANNEL_ID == 0:
        return
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(_format_assignments())


def _format_assignments() -> str:
    today = datetime.datetime.now(TZ).strftime("%A")
    daily  = chore_manager.daily_assignments()
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
    member = ctx.author.display_name
    try:
        chore_arg = int(arg) if arg else None
    except ValueError:
        chore_arg = arg  # treat as string
    ok = chore_manager.mark_as_done(member, chore_arg)
    await ctx.send(
        f"{member}, marked `{arg or 'all your chores'}` as done."
        if ok else
        f"Could not find chore `{arg}` to mark done."
    )


@bot.command()
async def active(ctx: commands.Context, member: discord.Member = None):
    """
    Add yourself (or another member) into the rotation roster.
    """
    who = member or ctx.author
    ids = load_member_ids()
    if who.id in ids:
        await ctx.send(f"**{who.display_name}** is already in the rotation.")
        return

    ids.append(who.id)
    save_member_ids(ids)

    # rebuild chore_manager with the new roster
    chore_manager_ref = build_chore_manager(ctx.guild)
    globals()["chore_manager"] = chore_manager_ref

    await ctx.send(f"Added **{who.display_name}** to the rotation.")


@bot.command()
async def inactive(ctx: commands.Context, member: discord.Member = None):
    """
    Remove yourself (or another member) from the rotation roster.
    """
    who = member or ctx.author
    ids = load_member_ids()
    if who.id not in ids:
        await ctx.send(f"**{who.display_name}** is not in the rotation.")
        return

    ids.remove(who.id)
    save_member_ids(ids)

    chore_manager_ref = build_chore_manager(ctx.guild)
    globals()["chore_manager"] = chore_manager_ref

    await ctx.send(f"Removed **{who.display_name}** from the rotation.")


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
