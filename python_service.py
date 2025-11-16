import os
import json
import asyncio
import traceback
import requests
from aiohttp import web

# -------------------------
# Configuration
# -------------------------
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "").strip()
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "").strip()
GRAPH = "https://graph.facebook.com/v20.0"

# Simple public audio URL (only informational — actual media via WebRTC SDP in real flow)
AUDIO_URL = "https://www2.cs.uic.edu/~i101/SoundFiles/StarWars3.wav"

# -------------------------
# Utility: generate minimal fake SDP
# -------------------------
def make_fake_sdp():
    # Very minimal placeholder SDP. It is not a true media endpoint SDP,
    # but many test setups accept a placeholder for validation steps.
    return (
        "v=0\r\n"
        "o=- 0 0 IN IP4 127.0.0.1\r\n"
        "s=python-agent\r\n"
        "t=0 0\r\n"
        "m=audio 9 RTP/AVP 0\r\n"
        "c=IN IP4 0.0.0.0\r\n"
    )

# -------------------------
# Background handler (simulated simple voice agent)
# -------------------------
async def handle_call_simple(call):
    try:
        if not isinstance(call, dict):
            print("Invalid call payload (not a dict).")
            return

        event = call.get("event")
        call_id = call.get("id")
        session = call.get("session", {})

        print("[handle_call_simple] event:", event, "id:", call_id)

        if event != "connect":
            print("Ignoring event (not connect):", event)
            return

        # If incoming had an SDP we could use it; for now build a safe fake answer
        answer_sdp = make_fake_sdp()

        # Pre-accept (optional if you want to test call flow)
        if WHATSAPP_TOKEN and PHONE_NUMBER_ID:
            try:
                resp = requests.post(
                    f"{GRAPH}/{PHONE_NUMBER_ID}/calls",
                    headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
                    json={
                        "messaging_product": "whatsapp",
                        "call_id": call_id,
                        "action": "pre_accept",
                        "session": {"sdp_type": "answer", "sdp": answer_sdp}
                    },
                    timeout=15,
                )
                print("[pre_accept] status:", resp.status_code, "body:", resp.text[:1000])
            except Exception as e:
                print("[pre_accept] exception:", e)
                traceback.print_exc()
        else:
            print("[pre_accept] WHATSAPP_TOKEN or PHONE_NUMBER_ID not set — skipping real pre_accept (OK for local testing).")

        # small delay to simulate processing
        await asyncio.sleep(1)

        # Accept call (again with fake SDP)
        if WHATSAPP_TOKEN and PHONE_NUMBER_ID:
            try:
                resp = requests.post(
                    f"{GRAPH}/{PHONE_NUMBER_ID}/calls",
                    headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
                    json={
                        "messaging_product": "whatsapp",
                        "call_id": call_id,
                        "action": "accept",
                        "session": {"sdp_type": "answer", "sdp": answer_sdp}
                    },
                    timeout=15,
                )
                print("[accept] status:", resp.status_code, "body:", resp.text[:1000])
            except Exception as e:
                print("[accept] exception:", e)
                traceback.print_exc()
        else:
            print("[accept] WHATSAPP_TOKEN or PHONE_NUMBER_ID not set — skipping real accept (OK for local testing).")

        # Optionally: log the audio URL we'll "play"
        print("[handle_call_simple] (simulated) will play audio:", AUDIO_URL)

    except Exception as exc:
        print("[handle_call_simple] Exception:", exc)
        traceback.print_exc()


# -------------------------
# Webhook HTTP handler
# -------------------------
async def webhook(request):
    try:
        data = await request.json()
    except Exception:
        raw = await request.text()
        print("[webhook] Invalid JSON body:", raw[:2000])
        return web.Response(text="invalid json", status=400)

    print("[webhook] Received payload (truncated):")
    try:
        print(json.dumps(data, indent=2)[:2000])
    except Exception:
        print(str(data)[:2000])

    # Process in background so we immediately ack the webhook
    asyncio.create_task(handle_call_simple(data))

    return web.Response(text="OK", status=200)


# -------------------------
# Health endpoint
# -------------------------
async def health(request):
    return web.Response(text="python-call-agent OK", status=200)


# -------------------------
# App setup
# -------------------------
def create_app():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_post("/run", webhook)  # /run used by many webhook setups
    return app


app = create_app()


# -------------------------
# Run server (Cloud Run compatible)
# -------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"Starting python-call-agent on 0.0.0.0:{port}")
    web.run_app(app, host="0.0.0.0", port=port)