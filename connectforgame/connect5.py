import asyncio
import json
import secrets
import websockets

from connect4 import PLAYER1, PLAYER2, Connect4

JOIN = {}
WATCH = {}

async def error(websocket, message):
    event = {
        "type": "error",
        "message": message,
    }
    await websocket.send(json.dumps(event))

async def replay(websocket, game):
    for player, column, row in game.moves.copy():
        event = {
            "type": "play",
            "player": player,
            "column": column,
            "row": row,
        }
        await websocket.send(json.dumps(event))

async def play(websocket, game, player, connected):
    move_counter = 0  # Счетчик ходов

    async for message in websocket:
        event = json.loads(message)
        assert event["type"] == "play"
        column = event["column"]

        try:
            row = game.play(player, column)
        except RuntimeError as exc:
            await error(websocket, str(exc))
            continue

        move_counter += 1  # Увеличиваем счетчик после каждого хода

        event = {
            "type": "play",
            "player": player,
            "column": column,
            "row": row,
        }
        websockets.broadcast(connected, json.dumps(event))

        if game.winner is not None:
            event = {
                "type": "win",
                "player": game.winner,
            }
            websockets.broadcast(connected, json.dumps(event))

        if move_counter >= 14:  # Изменено на 13 ходов
            event = {
                "type": "draw",  # Добавляем сообщение о ничьей
            }
            websockets.broadcast(connected, json.dumps(event))
            break  # Завершаем игру после 13 ходов

        if game.winner is not None:
            break  # Завершаем игру, если есть победитель

async def start(websocket):
    game = Connect4()
    connected = {websocket}

    join_key = secrets.token_urlsafe(14)
    JOIN[join_key] = game, connected

    watch_key = secrets.token_urlsafe(14)
    WATCH[watch_key] = game, connected

    try:
        event = {
            "type": "init",
            "join": join_key,
            "watch": watch_key,
        }
        await websocket.send(json.dumps(event))
        await play(websocket, game, PLAYER1, connected)
    finally:
        del JOIN[join_key]
        del WATCH[watch_key]

async def join(websocket, join_key):
    try:
        game, connected = JOIN[join_key]
    except KeyError:
        await error(websocket, "Game not found.")
        return

    connected.add(websocket)
    try:
        await replay(websocket, game)
        await play(websocket, game, PLAYER2, connected)
    finally:
        connected.remove(websocket)

async def watch(websocket, watch_key):
    try:
        game, connected = WATCH[watch_key]
    except KeyError:
        await error(websocket, "Game not found.")
        return

    connected.add(websocket)
    try:
        await replay(websocket, game)
        await websocket.wait_closed()
    finally:
        connected.remove(websocket)

async def handler(websocket):
    message = await websocket.recv()
    event = json.loads(message)
    assert event["type"] == "init"

    if "join" in event:
        await join(websocket, event["join"])
    elif "watch" in event:
        await watch(websocket, event["watch"])
    else:
        await start(websocket)

async def main():
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()

timers = {}

async def close(websocket):
    stop_timer(websocket)
    await websocket.close()

def start_timer(websocket):
    timers[websocket] = 20
    asyncio.ensure_future(update_timer(websocket))

def stop_timer(websocket):
    timers.pop(websocket, None)

async def update_timer(websocket):
    while websocket in timers and timers[websocket] > 0:
        await asyncio.sleep(1)
        timers[websocket] -= 1
    if websocket in timers:
        await close(websocket)

if __name__ == "__main__":
    asyncio.run(main())

