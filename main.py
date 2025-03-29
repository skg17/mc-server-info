import os
from flask import Flask, jsonify, request, render_template_string
from mcstatus import JavaServer

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
            status.favicon.replace("data:image/png;base64,", "")
            if hasattr(status, "favicon") and status.favicon
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
                status.favicon.replace("data:image/png;base64,", "")
                if hasattr(status, "favicon") and status.favicon
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

# Run app on Port 1701
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1701)