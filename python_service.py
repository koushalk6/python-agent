import os
import json
import asyncio
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaPlayer
import requests

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
GRAPH = "https://graph.facebook.com/v20.0"
PORT = int(os.getenv("PORT", "8080"))

# Public audio file
AUDIO_URL = "https://www2.cs.uic.edu/~i101/SoundFiles/StarWars3.wav"


async def process_call(call):
    """
    Handles incoming WhatsApp call event.
    """

    event = call.get("event")
    call_id = call.get("id")

    if event != "connect":
        print("Ignored event:", event)
        return

    offer_sdp = call["session"]["sdp"]

    pc = RTCPeerConnection()

    # Add audio track
    player = MediaPlayer(AUDIO_URL)
    pc.addTrack(player.audio)

    # Set offer
    await pc.setRemoteDescription(
        RTCSessionDescription(offer_sdp, "offer")
    )

    # Create answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # Pre-Accept
    print("Sending PRE_ACCEPT...")
    requests.post(
        f"{GRAPH}/{PHONE_NUMBER_ID}/calls",
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
        json={
            "messaging_product": "whatsapp",
            "call_id": call_id,
            "action": "pre_accept",
            "session": {
                "sdp_type": "answer",
                "sdp": pc.localDescription.sdp
            }
        }
    )

    # Accept when ICE connects
    @pc.on("iceconnectionstatechange")
    async def _on_ice_state():
        print("ICE State:", pc.iceConnectionState)
        if pc.iceConnectionState == "connected":
            print("Sending ACCEPT...")
            requests.post(
                f"{GRAPH}/{PHONE_NUMBER_ID}/calls",
                headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
                json={
                    "messaging_product": "whatsapp",
                    "call_id": call_id,
                    "action": "accept",
                    "session": {
                        "sdp_type": "answer",
                        "sdp": pc.localDescription.sdp
                    }
                }
            )

    return


async def webhook(req):
    """
    Cloud Run webhook receiver
    """
    try:
        data = await req.json()
    except:
        return web.Response(text="invalid", status=400)

    asyncio.create_task(process_call(data))

    return web.Response(text="ok")


def create_app():
    app = web.Application()
    app.router.add_post("/run", webhook)
    app.router.add_get("/", lambda req: web.Response(text="Running"))
    return app


if __name__ == "__main__":
    app = create_app()
    print(f"Starting server on port {PORT}...")
    web.run_app(app, port=PORT)