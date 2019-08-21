import discord
from discord.ext import commands
import config
import requests
from datetime import datetime
import base64
import json
import math
import urllib.parse
import BotUtils
from requests_oauthlib import OAuth1

class APIs(commands.Cog):
    """APIs"""

    def __init__(self, bot):
        self.bot = bot

    async def getAPI(self, url):
        r = requests.get(url=url)
        try:
            r.json()
        except:
            return(None)
        else:
            return(r.json())

    def url(self, url):
        return urllib.parse.quote(url)

    # thanks stackoverflow love ya
    def td_format(self, td_object):
        seconds = int(td_object.total_seconds())
        periods = [
            ('year',        60*60*24*365),
            ('month',       60*60*24*30),
            ('day',         60*60*24),
            ('hour',        60*60),
            ('minute',      60)
        ]

        strings=[]
        for period_name, period_seconds in periods:
            if seconds > period_seconds:
                period_value , seconds = divmod(seconds, period_seconds)
                has_s = 's' if period_value > 1 else ''
                strings.append("%s %s%s" % (period_value, period_name, has_s))

        return ", ".join(strings)
    
    # ----
    # MINECRAFT
    # ----

    async def getMinecraftAgeCheck(self, name, num):
        r = requests.get(url='https://api.mojang.com/users/profiles/minecraft/' + name + '?at=' + str(num))
        if r.status_code == 200:
            return True
        return False

    async def getMinecraftAge(self, name):
        a = 1263146630 # notch sign-up
        b = math.floor(datetime.utcnow().timestamp())
        lastfail = 0
        for i in range(30):
            if a == b:
                ok = await APIs.getMinecraftAgeCheck(self, name, a)
                if ok and lastfail == a-1:
                    return datetime.utcfromtimestamp(a)
                else:
                    return '???'
            else:
                mid = a + math.floor( ( b - a ) / 2)
                ok = await APIs.getMinecraftAgeCheck(self, name, mid)
                if ok:
                    b = mid
                else:
                    a = mid+1
                    lastfail = mid

    async def getMinecraftSales(self):
        payload = '{"metricKeys":["item_sold_minecraft","prepaid_card_redeemed_minecraft"]}'
        r = requests.post(url='https://api.mojang.com/orders/statistics', data=payload)
        return(r.json())
    
    async def getMinecraftUUID(self, name):
        r = requests.get(url='https://api.mojang.com/users/profiles/minecraft/' + name)
        if r.status_code == 200:
            return(r.json())
        
        r2 = requests.get(url='https://api.mojang.com/users/profiles/minecraft/' + name + "?at=0")
        if r2.status_code == 200:
            return(r2.json())
            
        return(None)
    
    async def getMinecraftSkinUrl(self, uuid):
        r = requests.get(url='https://sessionserver.mojang.com/session/minecraft/profile/' + uuid)
        data = r.json()
        try:
            val = data["properties"][0]["value"]
        except:
            return None
        decoded = base64.b64decode(val)
        return(json.loads(decoded))

    @commands.command(name='minecraft', aliases=['mc'])
    async def minecraftAPI(self, ctx, *, user=None):
        """Gets information about Minecraft, or searches players.
        Leave user as blank for general statistics"""
        try:
            if user:
                uuid = await APIs.getMinecraftUUID(self, user)
                if not uuid:
                    await ctx.send(content='User not found!')
                    await ctx.message.add_reaction('\N{NO ENTRY SIGN}')
                    return
                await ctx.message.add_reaction('\N{HOURGLASS}')
                history = await APIs.getAPI(self, 'https://api.mojang.com/user/profiles/' + uuid["id"] + '/names')
                names = []
                for i in range(len(history)):
                    names.append(history[i]["name"])
                    names[i] = names[i].replace('*', '\\*').replace('_', '\\_').replace('~', '\\~')
                names.reverse()
                names[0] += " **[CURRENT]**"

                created = await APIs.getMinecraftAge(self, user)

                skin = await APIs.getMinecraftSkinUrl(self, uuid["id"])
                if not skin:
                    await ctx.send("Ratelimited! Try again in 10 seconds")
                embed = discord.Embed(title='Minecraft User', colour=0x82540f)
                embed.set_author(name=history[-1]["name"], icon_url='attachment://head.png')
                embed.add_field(name='Name history', value='\n'.join(names))
                embed.add_field(name='UUID', value=uuid["id"])
                if skin["textures"]["SKIN"]["url"]:
                    embed.add_field(name='Skin URL', value='[Click me]('+skin["textures"]["SKIN"]["url"]+')')
                    await BotUtils.skinRenderer2D(skin["textures"]["SKIN"]["url"], str(uuid["id"]))
                    await BotUtils.headRenderer(skin["textures"]["SKIN"]["url"], str(uuid["id"]))
                    skin = discord.File("skins/2d/" + str(uuid["id"]) + ".png", filename="skin.png")
                    head = discord.File("skins/head/" + str(uuid["id"]) + ".png", filename="head.png")
                else:
                    skin = discord.File("skins/2d/default.png", filename="skin.png")
                    head = discord.File("skins/head/default.png", filename="head.png")
                if created != "???":
                    embed.add_field(name='Account created', value="On " + created.strftime('%c') + "\n" + self.td_format(datetime.utcnow() - created))
                else:
                    embed.add_field(name='Account created', value="???")
                embed.set_footer(text='|', icon_url='https://minecraft.net/favicon-96x96.png')
                embed.set_image(url="attachment://skin.png")
                embed.timestamp = datetime.utcnow()
                await ctx.message.clear_reactions()
                await ctx.send(files=[skin, head], embed=embed, content="")
            else:
                sale = await APIs.getMinecraftSales(self)
                embed = discord.Embed(title='Minecraft', colour=0x82540f)
                embed.add_field(name='Sold total', value=sale["total"])
                embed.add_field(name='Sold in the last 24h', value=sale["last24h"])

                embed.set_footer(text='|', icon_url='https://minecraft.net/favicon-96x96.png')
                embed.timestamp = datetime.utcnow()
                await ctx.message.clear_reactions()
                await ctx.send(embed=embed, content="")
        except Exception:
            await ctx.message.clear_reactions()
            await ctx.message.add_reaction('\N{NO ENTRY SIGN}')

    # ----
    # Apex Legends
    # ----

    async def getApexAPI(self, url):
        r = requests.get(url=url, headers={"TRN-Api-Key":config.api_keys["tracker"]})
        return(r.json())

    @commands.command(name='apex', aliases=['apexlegends', 'apesex'])
    async def apexAPI(self, ctx, user):
        """Gets information about Apex Legends players.
           Only PC information for now."""
        await ctx.message.add_reaction('\N{HOURGLASS}')
        try:
            data = await APIs.getApexAPI(self, "https://public-api.tracker.gg/apex/v1/standard/profile/5/" + user)

            stats = []
            for stat in data["data"]["stats"]:
                val = str(stat["value"])
                stats.append(("Total " + stat["metadata"]["name"], val.rstrip('0').rstrip('.') if '.' in val else val))

            for legend in data["data"]["children"]:
                for stat in legend["stats"]:
                    val = str(stat["value"])
                    stats.append((legend["metadata"]["legend_name"] + " " + stat["metadata"]["name"], val.rstrip('0').rstrip('.') if '.' in val else val))

            embed = discord.Embed(title='Apex Legends', colour=0xff6666)
            embed.set_author(name=str(data["data"]["metadata"]["platformUserHandle"]) + " - Level " + str(data["data"]["metadata"]["level"]))
            for stat in stats:
                embed.add_field(name=stat[0], value=stat[1])

            embed.set_footer(text='Missing data because EA.', icon_url='https://logodownload.org/wp-content/uploads/2019/02/apex-legends-logo-1.png')
            embed.timestamp = datetime.utcnow()
            await ctx.message.clear_reactions()
            await ctx.send(embed=embed, content="")
        except Exception as e:
            await ctx.message.clear_reactions()
            await ctx.message.add_reaction('\N{NO ENTRY SIGN}')

    # ----
    # CSGO
    # ----

    def getCSStat(self, data, stat):
        return [i for i in data["stats"] if i["name"] == "stat"]

    @commands.command(name='csgo', aliases=['cs'])
    async def CSGOAPI(self, ctx, *, user=None):
        """Gets information about CSGO players."""
        if not user:
            await ctx.send("Please enter an steam id or custom url after the command.")
            return
        try:
            if not str(user).isdigit():
                data = await APIs.getAPI(self, "http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key=" + config.api_keys["steam"] + "&vanityurl=" + APIs.url(self, user))
                user = data["response"]["steamid"]

            data = await APIs.getAPI(self, "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=" + config.api_keys["steam"] + "&steamids=" + user)
            name = data["response"]["players"][0]["personaname"]

            data = await APIs.getAPI(self, "http://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v0002/?appid=730&key=" + config.api_keys["steam"] + "&steamid=" + user)
            data = data["playerstats"]

            embed = discord.Embed(title='Counter-Strike: Global Offensive', colour=0xadd8e6)
            embed.set_author(name=str(name))

            embed.add_field(name="Kills", value=str(APIs.getCSStat(data, "total_kills")))
            embed.add_field(name="K/D", value=str(round(APIs.getCSStat(data, "total_kills")/APIs.getCSStat(data, "total_deaths"), 2)))
            embed.add_field(name="Time Played", value=str(round(APIs.getCSStat(data, "total_time_played") / 60 / 60, 1)) + "h")
            embed.add_field(name="Headshot %", value=str(round(APIs.getCSStat(data, "total_kills_headshot") / APIs.getCSStat(data, "total_kills") * 100, 1)) + "%")
            embed.add_field(name="Win %", value=str(round(APIs.getCSStat(data, "total_matches_won") / APIs.getCSStat(data, "total_matches_played") * 100, 1)) + "%")
            embed.add_field(name="Accuracy", value=str(round(APIs.getCSStat(data, "total_shots_hit") / APIs.getCSStat(data, "total_shots_fired") * 100, 1)) + "%")

            embed.timestamp = datetime.utcnow()

            await ctx.message.clear_reactions()
            await ctx.send(embed=embed, content="")
        except Exception as e:
            await ctx.message.clear_reactions()
            await ctx.message.add_reaction('\N{NO ENTRY SIGN}')

    # ----
    # CLASSICUBE
    # ----
    
    @commands.command(name='classicube', aliases=['cc'])
    async def classiCubeAPI(self, ctx, *, user=None):
        """Gets information about ClassiCube, or searches players.
        user = ID or name
        Leave as blank for general statistics"""
        await ctx.message.add_reaction('\N{HOURGLASS}')
        if user:
            data = await APIs.getAPI(self, 'https://www.classicube.net/api/player/'+user)
            if not data or data["error"] != "":
                if user.isdigit():
                    data = await APIs.getAPI(self, 'https://www.classicube.net/api/id/'+user)
                if not data or data["error"] != "":
                    await ctx.message.clear_reactions()
                    await ctx.message.add_reaction("\N{NO ENTRY SIGN}")
                    await ctx.send('User not found!')
                    return

            flags = []
            if 'b' in data["flags"]:
                flags.append('Banned from forums')
            if 'd' in data["flags"]:
                flags.append('Developer')
            if 'm' in data["flags"]:
                flags.append('Forum moderator')
            if 'a' in data["flags"]:
                flags.append('Forum admin')
            if 'e' in data["flags"]:
                flags.append('Blog editor')
            if 'p' in data["flags"]:
                flags.append('Patreon')
            
            embed = discord.Embed(title='ClassiCube User', colour=0x977dab)
            embed.set_author(name=data["username"],
                icon_url='attachment://head.png')
            embed.add_field(name='ID', value=data["id"])
            embed.add_field(name='Account created', value="On " + datetime.utcfromtimestamp(data["registered"]).strftime('%c') + "\n" + self.td_format(datetime.utcnow() - datetime.utcfromtimestamp(data["registered"])) + " ago")
            if flags:
                embed.add_field(name='Notes', value=', '.join(flags))
            
            if requests.get('https://static.classicube.net/skins/' + str(data["username"]) + '.png').status_code == 200:
                embed.add_field(name='Skin URL', value='[Click me](https://static.classicube.net/skins/' + str(data["username"]) + '.png)')
                await BotUtils.skinRenderer2D("https://static.classicube.net/skins/" + str(data["username"]) + ".png", str(data["id"]))
                await BotUtils.headRenderer("https://static.classicube.net/skins/" + str(data["username"]) + ".png", str(data["id"]))
                file = discord.File("skins/2d/" + str(data["id"]) + ".png", filename="skin.png")
                file2 = discord.File("skins/head/" + str(data["id"]) + ".png", filename="head.png")
            else:
                file = discord.File("skins/2d/default.png", filename="skin.png")
                file2 = discord.File("skins/head/default.png", filename="head.png")

            embed.set_footer(text='|', icon_url='https://www.classicube.net/static/img/cc-cube-small.png')
            embed.set_image(url="attachment://skin.png")
            embed.timestamp = datetime.utcnow()
            
            await ctx.message.clear_reactions()
            await ctx.send(files=[file, file2], embed=embed, content='')
        else:
            data = await APIs.getAPI(self, 'https://www.classicube.net/api/players/')
            onlinecount = 0
            playercount = data["playercount"]
            players = ''
            for p in data["lastfive"]:
                players += str(p) + '\n'
            
            data = await APIs.getAPI(self, 'https://www.classicube.net/api/servers/')
            serverlist = []
            servers = ""
            for server in sorted(data["servers"], key=lambda k: k["players"], reverse=True):
                if server["players"] > 0:
                    temp = "[" + str(server["country_abbr"]) + "] [" + str(server["name"]) + "](https://www.classicube.net/server/play/" + str(server["hash"]) + ") | " + str(server["players"]) + "/" + str(server["maxplayers"])
                    onlinecount += server["players"]
                    if len(servers) + len("\n---\n") + len(temp) > 1024:
                        serverlist.append(servers)
                        servers = ""
                    servers += temp+"\n---\n"
            serverlist.append(servers)

            embed = discord.Embed(title='ClassiCube', colour=0x977dab)
            embed.add_field(name='Total Accounts', value=playercount)
            embed.add_field(name='Accounts Online\n(Inaccurate)', value=str(onlinecount))
            embed.add_field(name='Last five accounts', value=players)
            for i in range(len(serverlist)):
                embed.add_field(name="("+str(i+1)+"/"+str(len(serverlist))+") Servers with players\nClick the server names to join!", value=serverlist[i])

            embed.set_footer(text='|', icon_url='https://www.classicube.net/static/img/cc-cube-small.png')
            embed.timestamp = datetime.utcnow()
            await ctx.message.clear_reactions()
            await ctx.send(embed=embed, content='')
    
    # ----
    # Wynncraft
    # ----
    
    @commands.command(name='wynncraft', aliases=['wc', 'wynn'])
    async def WynncraftAPI(self, ctx, *, user=None):
        """Gets information about Wynncraft, or searches players.
        Leave as blank for general statistics"""
        await ctx.message.add_reaction('\N{HOURGLASS}')
        if user:
            data = await APIs.getAPI(self, 'https://api.wynncraft.com/v2/player/'+user+'/stats')
            data = data["data"][0]
            if "error" in data:
                await ctx.message.clear_reactions()
                await ctx.message.add_reaction("\N{NO ENTRY SIGN}")
                await ctx.send(str(data["error"]))
                return

            rank = ""
            if data["rank"] != "Player":
                rank += "**" + data["rank"] + "**\n"

            if data["meta"]["veteran"]:
                rank += "Veteran\n"

            if data["meta"]["tag"]["value"]:
                rank += data["meta"]["tag"]["value"]

            if rank == "":
                rank = "Player"

            stats = []
            stats.append("**Items identified:** " + str(data["global"]["itemsIdentified"]))
            stats.append("**Mobs killed:** " + str(data["global"]["mobsKilled"]))
            stats.append("**PvP kills:** " + str(data["global"]["pvp"]["kills"]))
            stats.append("**PvP deaths:** " + str(data["global"]["pvp"]["deaths"]))
            stats.append("**Chests found:** " + str(data["global"]["chestsFound"]))
            stats.append("**Blocks walked:** " + str(data["global"]["blocksWalked"]))
            stats.append("**Logins:** " + str(data["global"]["logins"]))
            stats.append("**Deaths:** " + str(data["global"]["deaths"]))
            stats.append("**Combat Level:** " + str(data["global"]["totalLevel"]["combat"]))
            stats.append("**Total Level:** " + str(data["global"]["totalLevel"]["combined"]))
            stats.sort(key=lambda x:int(x.split(' ')[-1]))
            stats.reverse()

            classes = []
            for s in data["classes"]:
                classes.append("**" + ''.join([i for i in s["name"].title() if not i.isdigit()]) + ":** Level " + str(round(s["level"])))
            classes.sort(key=lambda x:float(x.split(' ')[-1]))
            classes.reverse()

            embed = discord.Embed(title='Wynncraft Player', colour=0x7bbf32)
            embed.set_author(name=data["username"],
                    icon_url='https://crafatar.com/avatars/'+data["uuid"])
            embed.add_field(name='Rank', value=rank)
            embed.add_field(name='Guild', value=str(data["guild"]["name"]))
            embed.add_field(name='Playtime', value=str(round(data["meta"]["playtime"]/12, 2))+"h")
            embed.add_field(name='First joined on', value=data["meta"]["firstJoin"].replace("T", ", ").split(".")[0])
            embed.add_field(name='Last joined on', value=data["meta"]["lastJoin"].replace("T", ", ").split(".")[0])
            if data["meta"]["location"]["online"]:
                embed.add_field(name='Currently in', value=data["meta"]["location"]["server"])
            
            embed.add_field(name='Global stats', value="\n".join(stats))
            embed.add_field(name='Classes', value="\n".join(classes))
            
            embed.set_footer(text='|', icon_url='https://cdn.wynncraft.com/img/ico/android-icon-192x192.png')
            embed.timestamp = datetime.utcnow()
            await ctx.message.clear_reactions()
            await ctx.send(embed=embed, content='')
            return
        else:
            data = await APIs.getAPI(self, 'https://api.wynncraft.com/public_api.php?action=onlinePlayersSum')
            embed = discord.Embed(title='Wynncraft', colour=0x7bbf32)
            embed.add_field(name='Players Online', value=data["players_online"])

            embed.set_footer(text='|', icon_url='https://cdn.wynncraft.com/img/ico/android-icon-192x192.png')
            embed.timestamp = datetime.utcnow()
            await ctx.message.clear_reactions()
            await ctx.send(embed=embed, content='')

    # ----
    # IMDb
    # ----

    @commands.command(name='imdb', aliases=["movie", "movies"])
    async def IMDbAPI(self, ctx, *, title):
        """Gets information about movies using the IMDb"""
        await ctx.message.add_reaction('\N{HOURGLASS}')
        data = await APIs.getAPI(self, 'http://www.omdbapi.com/?apikey=' + config.api_keys["omdb"] + '&t=' + APIs.url(self, title))
        if data["Response"] == "False":
            await ctx.message.clear_reactions()
            await ctx.message.add_reaction("\N{NO ENTRY SIGN}")
            await ctx.send(str(data["error"]))
            return

        embed = discord.Embed(title=data["Title"] + " (" + data["Year"] + ")", colour=0xf5c518, url="https://www.imdb.com/title/" + data["imdbID"])
        embed.add_field(name="Released", value=data["Released"])
        if "Production" in data:
            embed.add_field(name="Produced by", value=data["Production"])
        embed.add_field(name="Length", value=data["Runtime"])
        embed.add_field(name="Genres", value=data["Genre"])
        embed.add_field(name="Plot", value="||"+data["Plot"]+"||")
        if data["Poster"] != "N/A":
            embed.set_image(url=data["Poster"])

        if data["Ratings"]:
            ratings = ""
            for i in data["Ratings"]:
                ratings += "**" + i["Source"] + "** - `" + i["Value"] + "`\n"

            embed.add_field(name="Ratings", value=ratings)

        

        embed.timestamp = datetime.utcnow()
        await ctx.message.clear_reactions()
        await ctx.send(embed=embed, content='')

    # ----
    # Urban Dictionary
    # ----

    @commands.command(name='urbandictionary', aliases=["urban", "define"])
    async def UrbanDictionaryAPI(self, ctx, *, term):
        """Gets information about the urban dictionary"""
        await ctx.message.add_reaction('\N{HOURGLASS}')
        data = await APIs.getAPI(self, 'http://api.urbandictionary.com/v0/define?term=' + APIs.url(self, term))
        if not data["list"]:
            await ctx.message.clear_reactions()
            await ctx.message.add_reaction("\N{NO ENTRY SIGN}")
            return
        data = data["list"][0]
        embed = discord.Embed(title=data["word"], colour=0x1d2439, url=data["permalink"])
        embed.add_field(name="Definition", value="```"+data["definition"].replace("\r","")+"```")
        embed.add_field(name="Example", value="```"+data["example"].replace("\r","")+"```")
        
        embed.set_footer(text=str(data["thumbs_up"])+"👍, " + str(data["thumbs_down"]) + "👎 | Submitted")
        embed.timestamp = datetime.strptime(data["written_on"].split("T")[0], "%Y-%m-%d")
        await ctx.message.clear_reactions()
        await ctx.send(embed=embed, content='')

    # ----
    # Discord
    # ----
    @commands.command(name='invite', aliases=["discord"])
    async def DiscordAPI(self, ctx, *, invite):
        """Gets information about discord invites"""
        await ctx.message.add_reaction('\N{HOURGLASS}')
        invite = str(invite.split("/")[-1])
        data = await APIs.getAPI(self, 'https://discordapp.com/api/v6/invite/' +  APIs.url(self, invite) + "?with_counts=true")
        
        try:
            data["guild"]
        except:
            await ctx.message.clear_reactions()
            await ctx.message.add_reaction("\N{NO ENTRY SIGN}")
            await ctx.send(data["message"])
            return

        embed = discord.Embed(title="Click here to join the server!", colour=0x7289DA, url="https://discord.gg/" + data["code"])
        embed.add_field(name="Guild Name", value=str(data["guild"]["name"]))
        if data["guild"]["description"]:
            embed.add_field(name="Description", value=str(data["guild"]["description"]))
        embed.add_field(name="Members", value=str(data["approximate_member_count"]))
        embed.add_field(name="Online", value=str(data["approximate_presence_count"]))
        

        flagName = {
            "VERIFIED": "Verified",
            "LURKABLE": "Lurking enabled",
            "INVITE_SPLASH": "Custom invite splash screen",
            "VIP_REGIONS": "VIP Server",
            "FEATURABLE": "Featured server",
            "DISCOVERABLE": "In server discoveries",
            "NEWS": "News channel",
            "BANNER": "Custom banner",
            "VANITY_URL": "Custom vanity url",
            "ANIMATED_ICON": "Animated icon",
            "COMMERCE": "Store",
            "MORE_EMOJI": "More emoji"
        }

        flags = data["guild"]["features"]

        if flags:
            embed.add_field(name="Special features", value="\n".join([flagName[n] for n in flags]))
        
        try:
            embed.add_field(name="Invite created by", value=str(data["inviter"]["username"]) + "#" + str(data["inviter"]["discriminator"]) + " (<@" + str(data["inviter"]["id"]) + ">)")
        except KeyError:
            pass

        if "BANNER" in flags and data["guild"]["banner"]:
            embed.set_image(url="https://cdn.discordapp.com/banners/" + str(data["guild"]["id"]) + "/" + str(data["guild"]["banner"]) + ".webp?size=4096")
       
        if "ANIMATED_ICON" in flags and \
            data["guild"]["icon"] and \
            data["guild"]["icon"].startswith("a_"):
            embed.set_thumbnail(url="https://cdn.discordapp.com/icons/" + str(data["guild"]["id"]) + "/" + str(data["guild"]["icon"] + ".gif?size=4096"))
        elif data["guild"]["icon"]:
            embed.set_thumbnail(url="https://cdn.discordapp.com/icons/" + str(data["guild"]["id"]) + "/" + str(data["guild"]["icon"] + ".webp?size=4096"))
        
        embed.set_footer(text="Server ID " + str(data["guild"]["id"]))
        embed.timestamp = datetime.utcnow()
        await ctx.message.clear_reactions()
        await ctx.send(embed=embed, content='')

    # ----
    # DarkSky
    # ----
    @commands.command(name='weather', aliases=["sää"])
    async def weather(self, ctx, *, city):
        try:
            """Gets information about the weather"""
            await ctx.message.add_reaction('\N{HOURGLASS}')
            geocoding = await APIs.getAPI(self, "https://nominatim.openstreetmap.org/search?format=json&limit=1&accept-language=en&q=" + APIs.url(self, city))
            data = await APIs.getAPI(self, 'https://api.darksky.net/forecast/' +  config.api_keys["darksky"] + "/" + geocoding[0]["lat"] + "," + geocoding[0]["lon"] + "?exclude=minutely,hourly,daily,alerts,flags&units=si")

            embed = discord.Embed(title=geocoding[0]["display_name"], colour=0xffb347)
            embed.set_thumbnail(url="https://darksky.net/images/weather-icons/" + data["currently"]["icon"] + ".png")
            embed.description = "**Weather**\n" + str(round(data["currently"]["temperature"], 2)) + "°C (" + str(round(data["currently"]["temperature"] * (9/5) + 32, 2)) + "°F)\n" \
                + data["currently"]["summary"] + "\n" \
                + "Feels Like: " + str(round(data["currently"]["apparentTemperature"], 2)) + "°C (" + str(round(data["currently"]["apparentTemperature"] * (9/5) + 32, 2)) + "°F)\n" \
                + "Humidity: " + str(round(data["currently"]["humidity"] * 100, 2)) + "%\n" \
                + "Clouds: " + str(round(data["currently"]["cloudCover"] * 100, 2)) + "%\n" \
                + "Wind: " + str(data["currently"]["windSpeed"]) + " m/s (" + str(round(int(data["currently"]["windSpeed"]) * 2.2369362920544, 2)) + " mph)"
            embed.set_footer(text="Powered by Dark Sky and OpenStreetMap")
            embed.timestamp = datetime.fromtimestamp(data["currently"]["time"])
            await ctx.message.clear_reactions()
            await ctx.send(embed=embed, content='')
        except Exception as e:
            await ctx.message.clear_reactions()
            await ctx.message.add_reaction('\N{NO ENTRY SIGN}')

    # ---
    # TWITTER
    # ---

    def twitterVerify(self, url):
        auth = OAuth1(config.api_keys["twitterConsKey"], config.api_keys["twitterConsSecret"], config.api_keys["twitterAccToken"], config.api_keys["twitterAccSecret"])
        return requests.get(url, auth=auth).json()
    
    @commands.command(name='twitter')
    async def twitter(self, ctx, *, user):
        data = self.twitterVerify("https://api.twitter.com/1.1/users/search.json?count=1&q=" + self.url(user))[0]
        embed = discord.Embed(title=data["name"] + " (@" + data["screen_name"] + ")", url="https://twitter.com/"+data["screen_name"], description=data["description"], color=0x1DA1F2)
        embed.set_thumbnail(url=data["profile_image_url_https"])
        embed.add_field(name="Tweets", value=str(data["statuses_count"]))
        embed.add_field(name="Followers", value=str(data["followers_count"]))
        embed.add_field(name="Following", value=str(data["friends_count"]))
        embed.add_field(name="Liked posts", value=str(data["favourites_count"]))
        if data["location"]:
            embed.add_field(name="Location", value=data["location"])
        extra = []
        if data["verified"]:
            extra.append("Verified")
        if data["protected"]:
            extra.append("Private")
        if extra:
            embed.add_field(name="+", value="\n".join(extra))
        embed.set_footer(icon_url="https://about.twitter.com/etc/designs/about-twitter/public/img/favicon-32x32.png", text="Twitter • Account created")
        embed.timestamp = datetime.strptime(data["created_at"], "%a %b %d %H:%M:%S %z %Y")
        await ctx.send(embed=embed)

    # ---
    # DISCORD USER
    # ---
    @commands.command(name='user', aliases=["käyttäjä"])
    async def discordUser(self, ctx, *, user):
        """Gets Discord User stats"""
        await ctx.message.add_reaction('\N{HOURGLASS}')
        user = await commands.UserConverter().convert(ctx, user)
        
        embed = discord.Embed(title="Discord User " + user.name + "#" + str(user.discriminator), colour=0x7289DA)
        embed.set_thumbnail(url=str(user.avatar_url))
        embed.add_field(name="Account created", value="On " + datetime.utcfromtimestamp(user.created_at).strftime('%c') + "\n" + self.td_format(datetime.utcnow() - user.created_at) + " ago")
        embed.set_footer(text="User ID" + str(user.id))
        await ctx.message.clear_reactions()
        await ctx.send(embed=embed, content='')

    @commands.command(aliases=["statuspage"])
    async def status(self, ctx, *, name="None"):
        pages = [
            ("discord", "https://status.discordapp.com/index.json"),
            ("twitter", "https://api.twitterstat.us/index.json"),
            ("reddit", "https://reddit.statuspage.io/index.json"),
            ("cloudflare", "https://www.cloudflarestatus.com/index.json"),
            ("dropbox", "https://status.dropbox.com/index.json"),
            ("github", "https://www.githubstatus.com/index.json"),
        ]
        await ctx.message.add_reaction('\N{HOURGLASS}')
        for page in pages:
            if name.lower() == page[0]:
                col = 0x00
                j = await APIs.getAPI(self, page[1])
                if j["status"]["indicator"] == "none":
                    col = 0x00ff00
                elif j["status"]["indicator"] == "minor":
                    col = 0xffa500
                elif j["status"]["indicator"] == "major":
                    col = 0xff0000

                embed = discord.Embed(title="**" + page[0].title() + " Status** - " + j["status"]["description"], colour=col)
                for comp in j["components"]:
                    embed.add_field(name=comp["name"], value=comp["status"].replace("_", " ").title())
                embed.timestamp = datetime.utcnow()
                
                await ctx.message.clear_reactions()
                await ctx.send(embed=embed, content='')
                
                for incident in j["incidents"]:
                    if incident["status"] == "resolved" or incident["status"] == "completed":
                        continue
                    firstUpdate = incident["incident_updates"][-1]
                    if incident["status"] == "scheduled":
                        col = 0xffa500
                    else:
                        col = 0xff0000
                    
                    embed = discord.Embed(title="**" + incident["status"].title() + "** - " + incident["name"], color=col)
                    
                    embed.add_field(name="Affected components", value="\n".join(c["name"] for c in firstUpdate["affected_components"]))

                    embed.description = firstUpdate["body"]

                    if incident["scheduled_for"]:
                        embed.timestamp = datetime.strptime(incident["scheduled_for"], "%Y-%m-%dT%H:%M:%S.%fZ")
                        embed.set_footer(text=incident["impact"].title() + " • starts")
                    else:
                        embed.timestamp = datetime.strptime(incident["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
                        embed.set_footer(text=incident["impact"].title() + " • started")

                    await ctx.send(embed=embed, content='')
                return

        await ctx.message.clear_reactions()
        await ctx.message.add_reaction('\N{NO ENTRY SIGN}')
        await ctx.send("Invalid page! Currently supported pages: ```\n" + "\n".join([n.title() for n, a in pages]) + "```")

def setup(bot):
    bot.add_cog(APIs(bot))
