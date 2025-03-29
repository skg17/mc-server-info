from flask import Flask, jsonify, render_template_string
from mcstatus import JavaServer

app = Flask(__name__)

# Replace this with your server's IP or hostname and port
MINECRAFT_SERVER = "192.168.1.123"  # Minecraft server Local IP
PORT = 25565

@app.route("/status")
def status():
    try:
        # Define server
        server = JavaServer(MINECRAFT_SERVER, PORT)
        # Query server status
        status = server.status()
        # Return server status as JSON
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
    
@app.route("/")
def pretty():
    try:
        server = JavaServer(MINECRAFT_SERVER, PORT)
        status = server.status()

        # Get server icon if applicable
        icon = status.favicon if hasattr(status, "favicon") else None
        icon_data = icon.replace("data:image/png;base64,", "") if icon else None

        # Get server MOTD if applicable
        motd = ""
        if isinstance(status.description, dict):
            motd = status.description.get("text", "")
        elif isinstance(status.description, str):
            motd = status.description
        else:
            motd = str(status.description)

        # HTML template for webpage
        html_template = """
        <!DOCTYPE html>
        <html style="font-family: system-ui, sans-serif; background: #1e1e2e; color: #fff; padding: 2em;">
        <head>
            <meta charset="UTF-8">
            <title>Minecraft Server Status</title>
            <style>
                .card {
                    background: #2a2a40;
                    border-radius: 1rem;
                    padding: 1.5rem;
                    max-width: 400px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.5);
                }
                .icon {
                    width: 64px;
                    height: 64px;
                    margin-bottom: 1rem;
                }
            </style>
        </head>
        <body>
            <div class="card">
                {% if icon_data %}
                    <img class="icon" src="data:image/png;base64,{{ icon_data }}" alt="Server icon">
                {% endif %}
                <h2>🟢 Server is Online</h2>
                <p><strong>MOTD:</strong> {{ motd }}</p>
                <p><strong>Players:</strong> {{ online }}/{{ max }}</p>
                <p><strong>Ping:</strong> {{ latency }} ms</p>
            </div>
        </body>
        </html>
        """
        return render_template_string(html_template,
            icon_data=icon_data,
            motd=motd,
            online=status.players.online,
            max=status.players.max,
            latency=round(status.latency, 2)
        )

    except Exception as e:
        return f"<p style='color: red;'>Server offline or error: {e}</p>"

# Run app on Port 1701
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1701)