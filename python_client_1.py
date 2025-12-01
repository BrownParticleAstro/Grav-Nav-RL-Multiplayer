import asyncio
import json
import websockets
import uuid
import time

# Python Rocket Controller Client Script
# This script connects to the server the same way a browser would, using
# a WebSocket. It acts exactly like a "Manual Player" but controlled from Python
# instead of JavaScript.
#
# Key Idea:
# - The server sends "action_request" every simulation tick
# - We must respond with "manual_action" messages
#
# Once connected, the server simulation treats this client like a player.
async def main():
    # WebSocket address of the server (change this if server IP changes)
    uri = "ws://10.37.117.236:5500/ws"

    # Connect to the server
    async with websockets.connect(uri) as ws:
        # JOIN REQUEST MESSAGE
        # This message is copied from the server's expected message format:
        # Specifically from create_message() in server_multiship.py.
        # It selects "manual" mode and gives our rocket a name.
        join_message = {
            "header": {
                "version": "1.0",
                "type": "join_mode",   # The server checks this to know what we want
                "tick": 0,
                "timestamp": time.time(),
                "client_id": str(uuid.uuid4())  # We create our own client_id here
            },
            "payload": {
                "mode": "manual",     # Could also be "model" for AI-controlled ships
                "name": "PythonRocket"  # Shown in leaderboard + next to rocket
            }
        }
        # Send join request to server
        await ws.send(json.dumps(join_message))

        # Main event loop
        # Continuously listen for server messages and respond
        while True:
            # Receive raw JSON message from server
            message = await ws.recv()
            data = json.loads(message)
            msg_type = data["header"]["type"]

            # Server confirmed our mode selection (we successfully joined)
            if msg_type == "mode_confirmed":
                print("Joined:", data["payload"])

            # Server is asking us for our next control input
            # This happens once per simulation tick.
            elif msg_type == "action_request":
                # Server is asking for our next action
                # Example: just send no thrust or turn
                action_msg = {
                    "header": {
                        "version": "1.0",
                        "type": "manual_action",
                        "tick": data["header"]["tick"],
                        "timestamp": time.time(),
                        "client_id": str(uuid.uuid4())
                    },
                    "payload": {
                        "turn": 1.0, # figure out units
                        "thrust": 0.1
                    }
                }
                await ws.send(json.dumps(action_msg))
                print("Sent action:", action_msg["payload"])

            elif msg_type == "state_update":
                ships = data["payload"]["ships"]
                print(f"[TICK {data['header']['tick']}] Got {len(ships)} ships")

            await asyncio.sleep(0.01)

# Run the async WebSocket client
asyncio.run(main())