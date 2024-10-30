import asyncio
import websockets
import json

authorized_clients = {
    "a": "pass1",
    "b": "pass2",
    "c": "pass3"
}

client_weight = {
    "a" : 50,
    "b": 25,
    "c": 25
}
connected_clients = {}  # Store websocket and username pairs for authenticated clients
event_data = {"events": []}  # Store event data and scores
event_id = 0

# Event flag to control the shutdown process
shutdown_event = asyncio.Event()

async def authenticate_client(websocket):
    try:
        auth_message = await websocket.recv()
        credentials = json.loads(auth_message)
        username = credentials.get("username")
        password = credentials.get("password")

        if authorized_clients.get(username) == password:
            connected_clients[websocket] = username
            print(f"Client {username} authenticated successfully.")
            await websocket.send(json.dumps({"type": "welcome"}))
            return True
        else:
            print(f"Authentication failed for username: {username}")
            await websocket.send(json.dumps({"type": "auth_failed", "message": "Authentication failed. Disconnecting."}))
            await websocket.close()
            return False

    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected during authentication")
        return False

async def broadcast_message(message):
    if connected_clients:
        await asyncio.gather(*(client.send(message) for client in connected_clients.keys()))

async def start_event():
    global event_id
    event_id += 1
    print(f"Event {event_id} started.")
    await broadcast_message(json.dumps({"type": "event", "details": f"Event {event_id} started. Please wait for event to finish"}))

    # Simulated event duration
    await asyncio.sleep(5)  # Simulated event duration
    print(f"Event {event_id} ended. Voting started.")
    await broadcast_message(json.dumps({"type": "event_ended", "details": "Event ended. Please vote within 30 seconds."}))

    votes = await gather_votes()
    cumulative_score = sum(votes.values())
    event_data["events"].append({
        "event_id": event_id,
        "votes": votes,
        "cumulative_score": cumulative_score,
    })
    print(votes)
    print(f"Voting completed for Event {event_id}. Cumulative Score: {cumulative_score}")
    await broadcast_message(json.dumps({"type": "voteResult", "result": f"Votes collected with a cumulative score of {cumulative_score}"}))

async def gather_votes():
    votes = {}
    for client in connected_clients.keys():
        try:
            await client.send(json.dumps({"type": "request_vote"}))
            vote_message = await asyncio.wait_for(client.recv(), timeout=15)
            vote_data = json.loads(vote_message)
            votes[connected_clients[client]] = int(vote_data.get("vote", 0)) * client_weight[connected_clients[client]]/100
        except asyncio.TimeoutError:
            votes[connected_clients[client]] = 0  # Default to 0 if no vote is received
    return votes

async def handler(websocket, path):
    is_authenticated = await authenticate_client(websocket)
    if is_authenticated:
        try:
            while not shutdown_event.is_set():
                await asyncio.sleep(1)
        except websockets.exceptions.ConnectionClosed:
            print("Client disconnected")
        finally:
            connected_clients.pop(websocket, None)

async def event_loop():
    while True:
        action = input("Press 1 to trigger another event, 0 to stop: ")
        if action == '1':
            await start_event()
        elif action == '0':
            print("No more events. Sending final scores and closing all connections.")
            await broadcast_message(json.dumps({"type": "final_message", "message": "Thank you for participating, events have ended", "final_scores": event_data}))
            shutdown_event.set()
            break

async def admin_handler(websocket, path):
    try:
        while len(connected_clients) != len(authorized_clients):
            await asyncio.sleep(1)
        while True:
            action = await websocket.recv()
            data = json.loads(action)
            if data['action'] == 'start':
                await start_event()
            elif data['action'] == 'stop':
                await stop_events(websocket)
    except websockets.exceptions.ConnectionClosed:
        print("Admin connection closed")

async def stop_events(websocket):
    print("No more events. Sending final scores and closing all connections.")
    await broadcast_message(json.dumps({"type": "final_message", "message": "Thank you for participating, events have ended", "final_scores": event_data}))
    shutdown_event.set()

# Start both user and admin WebSocket servers
async def main():
    user_server = await websockets.serve(handler, "0.0.0.0", 6789)
    admin_server = await websockets.serve(admin_handler, "0.0.0.0", 6790)
    print("Servers started. User server on port 6789, Admin server on port 6790")
    await asyncio.gather(user_server.wait_closed(), admin_server.wait_closed())
    print("Server shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())
