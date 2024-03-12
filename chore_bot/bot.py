# This example requires the 'message_content' intent.

import datetime
import os

import discord
from discord.ext import commands, tasks

from chore_bot.chore_manager import ChoreManager

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

chore_manager = None
local_timezone = datetime.datetime.now().astimezone().tzinfo
daily_notification_time = datetime.time(hour=9, minute=0, tzinfo=local_timezone)
CHORES_CHANNEL = 1216559239456227439


@bot.event
async def on_ready():
    members = []
    for guild in bot.guilds:
        for member in guild.members:
            if not member.bot:
                members.append(member)
    global chore_manager
    chore_manager = ChoreManager(members, "config.json")
    send_daily_notification.start()


def chores_list() -> str:
    message = ""
    daily_assignments = chore_manager.daily_assignments()
    for idx, (chore, assignee) in enumerate(daily_assignments.items(), 1):
        message += f"\n{idx}. {chore}: {assignee.mention}"
    weekday = datetime.datetime.now().strftime("%A")
    weekly_assignments = chore_manager.weekly_assignments(weekday)
    for idx, (chore, assignee) in enumerate(
        weekly_assignments.items(), len(daily_assignments) + 1
    ):
        message += f"\n{idx}. {chore}: {assignee.mention}"
    return message


@tasks.loop(time=daily_notification_time)
async def send_daily_notification():
    message = "Good morning! Here are today's assignments:"
    message += chores_list()
    message += "\nHave a great day!"
    await bot.get_channel(CHORES_CHANNEL).send(message)


@bot.command()
async def inactive(ctx, member: discord.Member = None):
    """Mark a member as inactive. If unspecified, you will be marked as inactive."""
    if member:
        inactive_member = member
    else:
        inactive_member = ctx.author
    chore_manager.add_inactive_member(inactive_member)
    message = f"{inactive_member.mention} has been marked as inactive. Here are the new assignments:"
    message += chores_list()
    await ctx.send(message)


@bot.command()
async def active(ctx, member: discord.Member = None):
    """Mark a member as active. If unspecified, you will be marked as active."""
    if member:
        active_member = member
    else:
        active_member = ctx.author
    chore_manager.remove_inactive_member(active_member)
    message = f"{active_member.mention} has been marked as active"
    await ctx.send(message)


@bot.command()
async def chores(ctx):
    """Display today's chores."""
    message = "Here are today's assignments:"
    message += chores_list()
    await ctx.send(message)


@bot.command()
async def done(ctx, chore: str = None):
    """Mark a chore as done."""
    if chore is None:
        marked = chore_manager.mark_as_done(ctx.author)
        if marked:
            message = f"All of {ctx.author.mention}'s chores have been marked as done. Thank you for completing them!"
        else:
            message = (
                f"{ctx.author.mention}, you don't have any chores to be marked as done."
            )
    else:
        marked = chore_manager.mark_as_done(ctx.author, chore)
        if marked:
            message = f"'{chore}' has been marked as done. Thank you for completing it!"
        else:
            message = f"{ctx.author.mention}, you don't have a chore named '{chore}'."
    await ctx.send(message)


@bot.command()
async def help(ctx):
    """Display help message."""
    message = "Here are the available commands:\n"
    message += "!chores: Display today's chores.\n"
    message += "!done [chore]: Mark a chore as done. If unspecified, all of your chores will be marked as done.\n"
    message += "!inactive [member]: Mark a member as inactive. If unspecified, you will be marked as inactive.\n"
    message += "!active [member]: Mark a member as active. If unspecified, you will be marked as active.\n"
    message += "!help: Display this message."
    await ctx.send(message)


bot.run(os.environ["DISCORD_BOT_TOKEN"])
