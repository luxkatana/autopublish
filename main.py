import aiomysql

import discord, os, dotenv
from discord.ext import commands
dotenv.load_dotenv()
TOKEN = os.environ["TOKEN"]
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="./", intents=intents)
def something(ctx: discord.AutocompleteContext):
    mm = ctx.interaction.guild.channels
    convo = []
    for cn in mm:
        if cn.type == discord.ChannelType.news:
            convo.append(cn)
    return list(map(lambda x: x.name, convo))
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    bot.pool = await aiomysql.create_pool(
        user="root", password="", host="", db=""
    )

@bot.event
async def on_message(message: discord.Message) -> None:
    async def get_channel_id():
        async with bot.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor)as cursor:
                await cursor.execute("SELECT * FROM switches WHERE guildID=%s;", (message.guild.id,))
                fetch = await cursor.fetchall()
                if fetch == ():
                    return False
                return fetch[0]["channelID"]
    async def get_switch(ID: int) -> bool:
        async with bot.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("SELECT * FROM switches WHERE guildID=%s;", (ID,))
                a = await cursor.fetchall()
                if a == ():
                    return False
                return a[0]["switch"]
    if message.channel.type == discord.ChannelType.news and (await get_switch(message.guild.id)) == 1 and (await get_channel_id()) == message.channel.id and message.author != bot.user:
        await message.publish()
    await bot.process_commands(message)


@bot.slash_command(name="autopublish", guild_ids=[])
@discord.option(name="switch", description="on or off", choices=["on", "off"], required=True)
@discord.option(name="announcementchannel", required=True,autocomplete=something)
async def autopublish(ctx: discord.ApplicationContext, switch: str, announcementchannel) -> None:
    if switch == "on":
        announcementchannel = list(filter(lambda x: x.name == announcementchannel and x.type == discord.ChannelType.news, ctx.guild.channels))[0]
    async def update_bool(ID: int, victim: bool) -> None:
        async with bot.pool.acquire() as conn:
            async with conn.cursor()as cursor:
                await cursor.execute("UPDATE switches SET switch=%s WHERE guildID=%s;", (victim, ID))
                await conn.commit()
    async def create_record(ID: int) -> None:
        async with bot.pool.acquire() as conn:
            async with conn.cursor()as cursor:
                await cursor.execute("INSERT INTO switches VALUES(%s, %s,%s);", (ID, True, announcementchannel.id))
                await conn.commit()
    async def record_exists(ID: int) -> bool:
        async with bot.pool.acquire() as conn:
            async with conn.cursor()as cursor:
                await cursor.execute("SELECT * FROM switches WHERE guildID=%s;", (ID,))
                if (await cursor.fetchall()) == ():
                    return False
                return True
    exists = await record_exists(ctx.guild.id)
    match switch:
        case "on":
            if announcementchannel == None:
                embed = discord.Embed(title="RIP", description=f"the AnnouncementChannel argument is required!", colour=discord.Color.red())
                await ctx.respond(embed=embed, ephemeral=True)
            if exists == False:
                await create_record(ctx.guild.id)
                await announcementchannel.send(embed=discord.Embed(title="Success", description="This channel will be used for publishing", colour=discord.Color.green()))
                await ctx.respond(embed=discord.Embed(title="First time isnt it?", description="successfully switched it to **on**!", colour=discord.Color.green()), ephemeral=True)
            else:
                await update_bool(ctx.guild.id, True)
                async with bot.pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute("UPDATE switches SET channelID=%s WHERE guildID=%s;", (announcementchannel.id, ctx.guild.id))
                        await conn.commit()
                await announcementchannel.send(embed=discord.Embed(title="Success", description="This channel will be used for publishing", colour=discord.Colour.green()))
                await ctx.respond(embed=discord.Embed(title="Done!", description="Successfully switched to **on**!", colour=discord.Color.green()), ephemeral=True)
        case "off":
            if exists == True:
                await update_bool(ctx.guild_id, False)
                await ctx.respond(embed=discord.Embed(title="Switched", description="Switched to **off**", color=discord.Color.red()))
                return
            else:
                embed = discord.Embed(title="Oh uh", description="You never did **/switch on**...", color=discord.Color.red())
                await ctx.respond(embed=embed, ephemeral=True)


bot.run(TOKEN)