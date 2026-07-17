import asyncio
import websockets

async def run():
    try:
        async with websockets.connect('ws://127.0.0.1:8000/ws') as ws:
            print('Connected to ws://127.0.0.1:8000/ws')
            await ws.close()
    except Exception as e:
        print(f"Error 127.0.0.1: {e}")

asyncio.run(run())
