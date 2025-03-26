from flask import Flask, jsonify
from mcstatus import JavaServer

app = Flask(__name__)

# Replace this with your server's IP or hostname and port
MINECRAFT_SERVER = "calendar-damages.gl.joinmc.link"  # e.g. "10.x.x.x" or "yourname.meshnet-nordvpn.com"
PORT = 25565

@app.route("/status")
def status():
    try:
        server = JavaServer.lookup(MINECRAFT_SERVER)
        status = server.status()
        return jsonify({
            "online": True,
            "players": {
                "online": status.players.online,
                "max": status.players.max,
                "list": [p.name for p in status.players.sample] if status.players.sample else []
            },
            "motd": status.description.get("text", "") if isinstance(status.description, dict) else str(status.description),
            "latency_ms": round(status.latency, 2)
        })
    except Exception as e:
        return jsonify({
            "online": False,
            "error": str(e)
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1701)