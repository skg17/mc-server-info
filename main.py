import os
import base64
import io
from flask import Flask, jsonify, request, render_template_string, send_file
from mcstatus import JavaServer
from threading import Thread
from discord.ext import commands
import requests
import discord
import asyncio
import json

app = Flask(__name__)

# Loads servers from Docker environment variables
def load_servers_from_env():
    servers = {}
    for key, value in os.environ.items():
        if key.startswith("SERVER_"):
            name = key[7:]
            if ":" in value:
                host, port = value.split(":")
                servers[name] = {"host": host, "port": int(port)}
    return servers

SERVERS = load_servers_from_env()
TRACK_FILE = "tracked_servers.json"

# Return JavaServer object for IP:Port pair value from Docker Env
def get_server(name):
    info = SERVERS.get(name)
    if not info:
        raise ValueError(f"Unknown server name: {name}")
    return JavaServer(info["host"], info["port"])

@app.route("/status")
def status():
    name = request.args.get("server")
    if not name:
        return jsonify({"error": "Missing 'server' query parameter"}), 400

    try:
        # Query server status
        server = get_server(name)
        status = server.status()

        # Get server icon if applicable
        icon_data = (
            status.icon.replace("data:image/png;base64,", "")
            if hasattr(status, "icon") and status.icon
            else None
        )

        # Get server MOTD if applicable
        motd = status.description.get("text", "") if isinstance(status.description, dict) else str(status.description)

        # Return server status as JSON
        return jsonify({
            "online": True,
            "name": name,
            "motd": motd,
            "players": {
                "online": status.players.online,
                "max": status.players.max,
                "list": [p.name for p in status.players.sample] if status.players.sample else []
            },
            "latency_ms": round(status.latency, 2),
            "icon": icon_data
        })

    except Exception as e:
        return jsonify({"online": False, "error": str(e)})

@app.route("/")
def landing():
    results = []
    for name, info in SERVERS.items():
        try:
            server = JavaServer(info["host"], info["port"])
            status = server.status()

            icon_data = (
                status.icon.replace("data:image/png;base64,", "")
                if hasattr(status, "icon") and status.icon
                else None
            )

            motd = status.description.get("text", "") if isinstance(status.description, dict) else str(status.description)

            results.append({
                "name": name,
                "online": True,
                "motd": motd,
                "icon": icon_data,
                "players": f"{status.players.online}/{status.players.max}",
                "latency": round(status.latency, 2),
                "player_list": [p.name for p in status.players.sample] if status.players.sample else []
            })
        except Exception as e:
            results.append({
                "name": name,
                "online": False,
                "error": str(e),
                "player_list": []
            })

    # HTML rendering
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <title>Minecraft Dashboard</title>
    <meta http-equiv="refresh" content="30"> <!-- Auto-refresh every 30 seconds -->
    <style>
        body {
        font-family: system-ui, sans-serif;
        background: #1e1e2e;
        color: #fff;
        padding: 2rem;
        }
        h2 {
        margin-bottom: 1rem;
        }
        .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
        gap: 1.5rem;
        }
        .card {
        background: #2a2a3c;
        border-radius: 1rem;
        padding: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        box-shadow: 0 0 10px rgba(0,0,0,0.4);
        }
        .left {
        flex: 1;
        }
        .right {
        text-align: right;
        margin-left: 1rem;
        min-width: 120px;
        }
        .right img {
        border-radius: 0.25rem;
        margin-bottom: 4px;
        }
        .right .player-name {
        font-size: 0.85rem;
        opacity: 0.8;
        }
        a {
        color: #80dfff;
        text-decoration: none;
        }
    </style>
    </head>
    <body>
    <h2>Minecraft Server Dashboard</h2>
    <div class="grid">
        {% for s in servers %}
        <div class="card">
            <!-- Left Panel -->
            <div class="left">
            {% if s.icon %}
                <img src="data:image/png;base64,{{ s.icon }}" width="48" height="48">
            {% endif %}
            <h3 style="margin: 0;">{{ s.name }} {% if s.online %}🟢{% else %}🔴{% endif %}</h3>
            {% if s.online %}
                <p><strong>MOTD:</strong> {{ s.motd }}</p>
                <p><strong>Players:</strong> {{ s.players }}</p>
                <p><strong>Ping:</strong> {{ s.latency }} ms</p>
            {% else %}
                <p style="color: red;">Offline</p>
                <p><em>{{ s.error }}</em></p>
            {% endif %}
            </div>

            <!-- Right Panel: Player Avatars -->
            {% if s.online and s.player_list %}
            <div class="right">
                {% for player in s.player_list %}
                <img src="https://minotar.net/helm/{{ player }}/32" alt="{{ player }}" title="{{ player }}">
                <div class="player-name">{{ player }}</div>
                {% endfor %}
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    </body>
    </html>
    """
    return render_template_string(html_template, servers=results)

@app.route("/widget")
def homarr_widget():
    results = []
    for name, info in SERVERS.items():
        try:
            server = JavaServer(info["host"], info["port"])
            status = server.status()

            icon_data = (
                status.icon.replace("data:image/png;base64,", "")
                if hasattr(status, "icon") and status.icon
                else None
            )
            motd = status.description.get("text", "") if isinstance(status.description, dict) else str(status.description)
            player_list = [p.name for p in status.players.sample] if status.players.sample else []

            results.append({
                "name": name,
                "online": True,
                "motd": motd,
                "icon": icon_data,
                "players": f"{status.players.online}/{status.players.max}",
                "latency": round(status.latency, 2),
                "player_list": player_list
            })

        except Exception as e:
            results.append({
                "name": name,
                "online": False,
                "error": str(e),
                "player_list": []
            })

    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Minecraft Widget</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <meta http-equiv="refresh" content="30">
      <style>
        body {
          margin: 0;
          font-family: system-ui, sans-serif;
          background: #1e1e2e;
          color: #fff;
          padding: 1rem;
        }
        .grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 1rem;
        }
        .card {
          background: #2a2a3c;
          border-radius: 1rem;
          padding: 1rem;
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          box-shadow: 0 0 10px rgba(0,0,0,0.4);
        }
        .left {
          flex: 1;
        }
        .right {
          text-align: right;
          margin-left: 1rem;
          min-width: 100px;
        }
        .right img {
          border-radius: 0.25rem;
          margin-bottom: 4px;
        }
        .right .player-name {
          font-size: 0.85rem;
          opacity: 0.8;
        }
      </style>
    </head>
    <body>
      <div class="grid">
        {% for s in servers %}
          <div class="card">
            <div class="left">
              {% if s.icon %}
                <img src="data:image/png;base64,{{ s.icon }}" width="32" height="32">
              {% endif %}
              <h4 style="margin: 0;">{{ s.name }} {% if s.online %}🟢{% else %}🔴{% endif %}</h4>
              {% if s.online %}
                <p style="margin: 0.5em 0;"><strong>MOTD:</strong> {{ s.motd }}</p>
                <p><strong>Players:</strong> {{ s.players }}</p>
                <p><strong>Ping:</strong> {{ s.latency }} ms</p>
              {% else %}
                <p style="color: red;">Offline</p>
                <p><em>{{ s.error }}</em></p>
              {% endif %}
            </div>
            {% if s.online and s.player_list %}
              <div class="right">
                {% for player in s.player_list %}
                  <img src="https://minotar.net/helm/{{ player }}/32" alt="{{ player }}" title="{{ player }}">
                  <div class="player-name">{{ player }}</div>
                {% endfor %}
              </div>
            {% endif %}
          </div>
        {% endfor %}
      </div>
    </body>
    </html>
    """
    return render_template_string(html_template, servers=results)

@app.route("/servers")
def list_servers():
    return jsonify(list(SERVERS.keys()))

@app.route("/icon/<server_name>")
def get_icon(server_name):
    server = SERVERS.get(server_name)
    if not server:
        return "", 204  # No Content

    try:
        status = JavaServer.lookup(server).status()
        icon_data = getattr(status, "icon", None) or getattr(status, "favicon", None)
        if icon_data:
            base64_data = icon_data.replace("data:image/png;base64,", "")
            image_data = base64.b64decode(base64_data)
            return send_file(io.BytesIO(image_data), mimetype="image/png")
    except Exception as e:
        print(f"[ICON ERROR] {server_name}: {e}")

    return "", 204  # Gracefully do nothing if no icon or error

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
TRACK_FILE = "/data/tracked_servers.json"
tracked_servers = {}
last_status = {
    "online": None,
    "players": set()
}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def load_tracked_servers():
    global tracked_servers
    if os.path.exists(TRACK_FILE):
        try:
            with open(TRACK_FILE, "r") as f:
                tracked_servers.update(json.load(f))
                print(f"✅ Loaded tracked_servers: {tracked_servers}")
        except Exception as e:
            print(f"⚠️ Failed to load tracked servers: {e}")
            tracked_servers = {}
    else:
        tracked_servers = {}

def save_tracked_servers():
    try:
        with open(TRACK_FILE, "w") as f:
            json.dump(tracked_servers, f)
            print(f"💾 Saved tracked servers")
    except Exception as e:
        print(f"⚠️ Failed to save tracked servers: {e}")

@bot.command(name="mcinfo")
async def mcinfo(ctx, server_name: str = "main"):
    flask_url = f"http://localhost:1701/status?server={server_name}"

    try:
        response = requests.get(flask_url)
        data = response.json()

        if not data.get("online"):
            await ctx.send(f"🔴 `{server_name}` is currently offline.")
            return

        players = data["players"]
        motd = data.get("motd", "N/A")
        latency = data.get("latency_ms", "?")

        msg = (
            f"🟢 **{server_name} is online**\n"
            f"**MOTD**: {motd}\n"
            f"**Players**: {players['online']}/{players['max']}\n"
            f"**Ping**: {latency} ms"
        )

        if players.get("list"):
            names = ', '.join(players["list"])
            msg += f"\n**Online Players**: {names}"

        await ctx.send(msg)

    except Exception as e:
        await ctx.send(f"⚠️ Error fetching `{server_name}` status: `{e}`")

@bot.command(name="servers")
async def list_servers_command(ctx):
    try:
        res = requests.get("http://localhost:1701/servers")
        servers = res.json()

        if not servers:
            await ctx.send("⚠️ No servers are currently configured.")
            return

        msg = "🗂️ **Available Servers:**\n" + "\n".join(f"- `{s}`" for s in servers)
        await ctx.send(msg)

    except Exception as e:
        await ctx.send(f"⚠️ Could not fetch server list: `{e}`")

@bot.command(name="track")
async def track_server(ctx, mode: str, server_name: str):
    mode = mode.lower()
    server_name = server_name.lower()

    if mode not in ("on", "off"):
        await ctx.send("⚠️ Usage: `!track on|off server_name`")
        return

    if mode == "on":
        tracked_servers[server_name] = CHANNEL_ID
        save_tracked_servers()
        await ctx.send(f"🔔 Now tracking `{server_name}` in <#{CHANNEL_ID}>.")
    elif mode == "off":
        if server_name in tracked_servers:
            del tracked_servers[server_name]
            save_tracked_servers()
            await ctx.send(f"🔕 Stopped tracking `{server_name}`.")
        else:
            await ctx.send(f"⚠️ `{server_name}` is not currently being tracked.")

def start_discord_bot():
    bot.run(DISCORD_TOKEN)

async def monitor_server(server_name: str):
    await bot.wait_until_ready()
    server_icon_url = f"http://localhost:1701/icon/{server_name}"

    while True:
        try:
            if server_name not in tracked_servers:
                await asyncio.sleep(30)
                continue

            channel = bot.get_channel(tracked_servers[server_name])
            if not channel:
                await asyncio.sleep(30)
                continue

            res = requests.get(f"http://localhost:1701/status?server={server_name}")
            data = res.json()

            # Server Online
            if data["online"]:
                if last_status[server_name]["online"] is False:
                    embed = discord.Embed(
                        title=f"🟢 `{server_name}` is back online!",
                        description="Ready to play 🎮",
                        color=0x57F287
                    )
                    embed.set_thumbnail(url=server_icon_url)
                    embed.timestamp = discord.utils.utcnow()
                    await channel.send(embed=embed)


                current_players = set(data["players"].get("list", []))

                # Join
                joined = current_players - last_status[server_name]["players"]
                for player in joined:
                    embed = discord.Embed(
                        title=f"📥 {player} joined",
                        description=f"🗂️ Server: `{server_name}`",
                        color=0x57F287
                    )
                    embed.set_thumbnail(url=f"https://minotar.net/avatar/{player}/64.png")
                    embed.set_footer(text="Minecraft Server Tracker", icon_url=server_icon_url)
                    embed.timestamp = discord.utils.utcnow()
                    await channel.send(embed=embed)

                # Leave
                left = last_status[server_name]["players"] - current_players
                for player in left:
                    embed = discord.Embed(
                        title=f"📤 {player} left",
                        description=f"🗂️ Server: `{server_name}`",
                        color=0xED4245
                    )
                    embed.set_thumbnail(url=f"https://minotar.net/avatar/{player}/64.png")
                    embed.set_footer(text="Minecraft Server Tracker", icon_url=server_icon_url)
                    embed.timestamp = discord.utils.utcnow()
                    await channel.send(embed=embed)

                last_status[server_name]["players"] = current_players
                last_status[server_name]["online"] = True

            else:
                if last_status[server_name]["online"] is not False:
                    embed = discord.Embed(
                        title=f"🔴 `{server_name}` is now offline.",
                        description="The server is currently unreachable.",
                        color=0xED4245
                    )
                    embed.set_thumbnail(url=server_icon_url)
                    embed.timestamp = discord.utils.utcnow()
                    await channel.send(embed=embed)
                    
                last_status[server_name]["online"] = False
                last_status[server_name]["players"] = set()

        except Exception as e:
            print(f"❌ Error monitoring {server_name}: {e}")

        await asyncio.sleep(30)

@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")
    load_tracked_servers()

    try:
        response = requests.get("http://localhost:1701/servers")
        server_list = response.json()
        print(f"🧠 Loaded servers from API: {server_list}")
    except Exception as e:
        print(f"❌ Failed to fetch server list: {e}")
        return

    for server in server_list:
        last_status[server] = { "online": None, "players": set() }
        bot.loop.create_task(monitor_server(server))

# Run both Flask and Discord bot
if __name__ == "__main__":
    Thread(target=start_discord_bot).start()
    app.run(host="0.0.0.0", port=1701)