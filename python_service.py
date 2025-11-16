



















# python_service.py
import os
import json
import asyncio
import traceback
import requests
from aiohttp import web
from datetime import datetime

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "EAAzIG7LU0TYBO4EsZCcETbfEgZAW79NJFQZCh3RJ5Y182q0CQVj0ELcdoEkgZCf3blKWbuCLdKtZBIKEOZAbh6x0RpdcXPEoSl2wxe8D1OUjpEvyz2O3eakLUqHQDLXbie3wcy9QJuFHaVLjxa1SHmutNdZCQvxM4MFqZB6ZCUdWdUJ8CueRn4LKZClBBZABcuqPHZAOHgZDZD").strip()
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "732355239960210").strip()
GRAPH = "https://graph.facebook.com/v20.0"

# Fallback public audio
AUDIO_URL = "https://samplelib.com/lib/preview/wav/sample-3s.wav"

# Track call status
CALL_STATUS = {}

def make_valid_sdp():
    return (
        "v=0\r\n"
        "o=- 0 0 IN IP4 0.0.0.0\r\n"
        "s=-\r\n"
        "t=0 0\r\n"
        "m=audio 9 RTP/AVP 111 126\r\n"
        "c=IN IP4 0.0.0.0\r\n"
        "a=rtpmap:111 opus/48000/2\r\n"
        "a=rtpmap:126 telephone-event/8000\r\n"
        "a=fmtp:111 maxaveragebitrate=20000;maxplaybackrate=16000;minptime=20;sprop-maxcapturerate=16000;useinbandfec=1\r\n"
        "a=maxptime:20\r\n"
        "a=ptime:20\r\n"
        "a=sendrecv\r\n"
    )

async def send_call_action(call_id, action, sdp):
    try:
        r = requests.post(
            f"{GRAPH}/{PHONE_NUMBER_ID}/calls",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "call_id": call_id,
                "action": action,
                "session": {"sdp_type": "answer", "sdp": sdp}
            },
            timeout=10,
        )
        print(f"[send_call_action] {action} response: {r.status_code}")
    except Exception as e:
        print(f"[send_call_action] {action} failed: {e}")

async def handle_call(call):
    try:
        if not isinstance(call, dict):
            print("Bad payload (not dict).")
            return

        event = call.get("event")
        call_id = call.get("id") or call.get("call_id") or call.get("waba_call_id")
        session = call.get("session", {}) or {}
        print(f"[handle_call] event: {event} call_id: {call_id}")

        if event not in ("connect", "offer", "incoming"):
            print(f"[handle_call] ignoring event: {event}")
            return

        incoming_sdp = session.get("sdp") or session.get("offer") or None
        use_aiortc = False
        try:
            from aiortc import RTCPeerConnection, RTCSessionDescription, MediaPlayer
            use_aiortc = True
            print("[handle_call] aiortc available")
        except Exception:
            print("[handle_call] aiortc not available, will use fallback SDP/audio")

        sdp_to_use = incoming_sdp if incoming_sdp else make_valid_sdp()
        ice_connected = False
        pc = None

        if use_aiortc and incoming_sdp:
            try:
                pc = RTCPeerConnection()
                # Try to add audio track
                try:
                    player = MediaPlayer(AUDIO_URL)
                    if player.audio:
                        pc.addTrack(player.audio)
                        print("[handle_call] added MediaPlayer audio track")
                except Exception as e:
                    print(f"[handle_call] MediaPlayer init failed: {e}, fallback will continue")

                offer = RTCSessionDescription(sdp=incoming_sdp, type="offer")
                await pc.setRemoteDescription(offer)
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                sdp_to_use = pc.localDescription.sdp

                @pc.on("iceconnectionstatechange")
                async def on_ice():
                    nonlocal ice_connected
                    state = pc.iceConnectionState
                    print(f"[ICE] Connection state: {state}")
                    if state == "connected":
                        ice_connected = True
            except Exception as e:
                print(f"[handle_call] aiortc setup failed, fallback SDP will be used: {e}")
                sdp_to_use = make_valid_sdp()
                pc = None

        # Retry loop until ICE connected or COMPLETED or 50 seconds max
        start_time = datetime.utcnow()
        while (datetime.utcnow() - start_time).seconds < 50:
            if CALL_STATUS.get(call_id) == "COMPLETED":
                print(f"[handle_call] call {call_id} completed, stopping retries")
                break
            if ice_connected:
                print(f"[handle_call] ICE connected, stopping retries")
                break

            await send_call_action(call_id, "pre_accept", sdp_to_use)
            await asyncio.sleep(1)
            await send_call_action(call_id, "accept", sdp_to_use)
            await asyncio.sleep(3)

        if pc:
            await pc.close()

        print(f"[handle_call] finished call handling for call_id {call_id}")

    except Exception as exc:
        print(f"[handle_call] unexpected error: {exc}")
        traceback.print_exc()

async def webhook(request):
    try:
        payload = await request.json()
    except Exception:
        text = await request.text()
        print("[webhook] invalid JSON:", text[:2000])
        return web.Response(text="invalid json", status=400)

    print("[webhook] payload received")
    try:
        print(json.dumps(payload, indent=2)[:2000])
    except Exception:
        print(str(payload)[:2000])

    calls = None
    if isinstance(payload, dict):
        entry = payload.get("entry") or []
        if entry and isinstance(entry, list):
            try:
                calls = entry[0]["changes"][0]["value"].get("calls")
            except Exception:
                calls = None

    if not calls:
        print("[webhook] no call object found")
        return web.Response(text="no-call", status=200)

    for call in calls:
        call_id = call.get("id") or call.get("call_id")
        if call.get("status") == "COMPLETED":
            CALL_STATUS[call_id] = "COMPLETED"
            print(f"[webhook] call {call_id} marked COMPLETED")
        else:
            asyncio.create_task(handle_call(call))

    return web.Response(text="ok", status=200)

async def health(request):
    return web.Response(text="python-call-agent OK", status=200)

def create_app():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_post("/", webhook)
    app.router.add_post("/run", webhook)
    return app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"Starting python call agent on port {port}")
    web.run_app(create_app(), host="0.0.0.0", port=port)
# # python_service.py
# import os
# import json
# import asyncio
# import traceback
# import requests
# from aiohttp import web


# WHATSAPP_TOKEN = "EAAzIG7LU0TYBO4EsZCcETbfEgZAW79NJFQZCh3RJ5Y182q0CQVj0ELcdoEkgZCf3blKWbuCLdKtZBIKEOZAbh6x0RpdcXPEoSl2wxe8D1OUjpEvyz2O3eakLUqHQDLXbie3wcy9QJuFHaVLjxa1SHmutNdZCQvxM4MFqZB6ZCUdWdUJ8CueRn4LKZClBBZABcuqPHZAOHgZDZD"
# PHONE_NUMBER_ID = "732355239960210"

# # WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "").strip()
# # PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "").strip()
# GRAPH = "https://graph.facebook.com/v20.0"

# # Public audio URL fallback (optional)
# AUDIO_URL = "https://samplelib.com/lib/preview/wav/sample-3s.wav"

# def make_fake_sdp():
#     # Minimal fallback SDP for testing without aiortc
#     return (
#         "v=0\r\n"
#         "o=- 0 0 IN IP4 0.0.0.0\r\n"
#         "s=python-agent\r\n"
#         "t=0 0\r\n"
#         "m=audio 9 RTP/AVP 0\r\n"
#         "c=IN IP4 0.0.0.0\r\n"
#     )

# async def handle_call(call):
#     try:
#         if not isinstance(call, dict):
#             print("Bad payload (not dict).")
#             return

#         event = call.get("event")
#         call_id = call.get("id") or call.get("call_id") or call.get("waba_call_id")
#         session = call.get("session", {}) or {}
#         print(f"[handle_call] event: {event} id: {call_id}")

#         if event not in ("connect", "offer", "incoming"):
#             print(f"[handle_call] ignoring event: {event}")
#             return

#         incoming_sdp = session.get("sdp") or session.get("offer") or None

#         use_aiortc = False
#         try:
#             from aiortc import RTCPeerConnection, RTCSessionDescription, MediaPlayer
#             use_aiortc = True
#             print("[handle_call] aiortc imported successfully.")
#         except Exception as e:
#             print(f"[handle_call] aiortc not available, fallback: {e}")

#         if use_aiortc and incoming_sdp:
#             pc = RTCPeerConnection()

#             # Add audio track from URL if possible (optional)
#             try:
#                 player = MediaPlayer(AUDIO_URL)
#                 if player.audio:
#                     pc.addTrack(player.audio)
#                     print("[handle_call] added MediaPlayer audio track")
#             except Exception as e:
#                 print(f"[handle_call] MediaPlayer init failed: {e}")

#             # Set remote description from incoming SDP
#             offer = RTCSessionDescription(sdp=incoming_sdp, type="offer")
#             await pc.setRemoteDescription(offer)

#             # Create answer
#             answer = await pc.createAnswer()
#             await pc.setLocalDescription(answer)
#             local_sdp = pc.localDescription.sdp
#             print(f"[handle_call] generated SDP answer length: {len(local_sdp)}")

#             # Send pre_accept to WhatsApp Graph API
#             if WHATSAPP_TOKEN and PHONE_NUMBER_ID:
#                 try:
#                     r = requests.post(
#                         f"{GRAPH}/{PHONE_NUMBER_ID}/calls",
#                         headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
#                         json={
#                             "messaging_product": "whatsapp",
#                             "call_id": call_id,
#                             "action": "pre_accept",
#                             "session": {"sdp_type": "answer", "sdp": local_sdp}
#                         },
#                         timeout=10,
#                     )
#                     print(f"[handle_call] pre_accept response: {r.status_code}")
#                 except Exception as e:
#                     print(f"[handle_call] pre_accept POST failed: {e}")

#             # Wait for ICE to connect, then send accept
#             @pc.on("iceconnectionstatechange")
#             async def on_ice():
#                 print(f"[handle_call] ICE state changed: {pc.iceConnectionState}")
#                 if pc.iceConnectionState == "connected":
#                     try:
#                         r = requests.post(
#                             f"{GRAPH}/{PHONE_NUMBER_ID}/calls",
#                             headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
#                             json={
#                                 "messaging_product": "whatsapp",
#                                 "call_id": call_id,
#                                 "action": "accept",
#                                 "session": {"sdp_type": "answer", "sdp": pc.localDescription.sdp}
#                             },
#                             timeout=10,
#                         )
#                         print(f"[handle_call] accept response: {r.status_code}")
#                     except Exception as e:
#                         print(f"[handle_call] accept POST failed: {e}")

#             # Keep connection alive to process ICE events
#             await asyncio.sleep(30)  # keep PC alive for ICE to connect

#             await pc.close()
#             print("[handle_call] call handling done.")
#             return

#         # Fallback - no aiortc or no SDP, use fake SDP to pre_accept + accept
#         fallback_sdp = make_fake_sdp()
#         print("[handle_call] using fallback SDP")

#         if WHATSAPP_TOKEN and PHONE_NUMBER_ID:
#             try:
#                 r = requests.post(
#                     f"{GRAPH}/{PHONE_NUMBER_ID}/calls",
#                     headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
#                     json={
#                         "messaging_product": "whatsapp",
#                         "call_id": call_id,
#                         "action": "pre_accept",
#                         "session": {"sdp_type": "answer", "sdp": fallback_sdp}
#                     },
#                     timeout=10,
#                 )
#                 print(f"[handle_call] fallback pre_accept response: {r.status_code}")
#             except Exception as e:
#                 print(f"[handle_call] fallback pre_accept failed: {e}")

#             await asyncio.sleep(0.5)

#             try:
#                 r = requests.post(
#                     f"{GRAPH}/{PHONE_NUMBER_ID}/calls",
#                     headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
#                     json={
#                         "messaging_product": "whatsapp",
#                         "call_id": call_id,
#                         "action": "accept",
#                         "session": {"sdp_type": "answer", "sdp": fallback_sdp}
#                     },
#                     timeout=10,
#                 )
#                 print(f"[handle_call] fallback accept response: {r.status_code}")
#             except Exception as e:
#                 print(f"[handle_call] fallback accept failed: {e}")

#     except Exception as exc:
#         print(f"[handle_call] unexpected error: {exc}")
#         traceback.print_exc()

# async def webhook(request):
#     try:
#         payload = await request.json()
#     except Exception:
#         text = await request.text()
#         print("[webhook] invalid JSON body:", text[:2000])
#         return web.Response(text="invalid json", status=400)

#     print("[webhook] payload received:")
#     try:
#         print(json.dumps(payload, indent=2)[:2000])
#     except Exception:
#         print(str(payload)[:2000])

#     # Extract calls array
#     calls = None
#     if isinstance(payload, dict):
#         if payload.get("event") or payload.get("id"):
#             calls = [payload]
#         else:
#             entry = payload.get("entry") or []
#             if entry and isinstance(entry, list):
#                 try:
#                     calls = entry[0]["changes"][0]["value"].get("calls")
#                 except Exception:
#                     calls = None

#     if not calls:
#         print("[webhook] no call object found; ack and return")
#         return web.Response(text="no-call", status=200)

#     for call in calls:
#         asyncio.create_task(handle_call(call))

#     return web.Response(text="ok", status=200)

# async def health(request):
#     return web.Response(text="python-call-agent OK", status=200)

# def create_app():
#     app = web.Application()
#     app.router.add_get("/", health)
#     app.router.add_post("/", webhook)
#     app.router.add_post("/run", webhook)  # alternative endpoint
#     return app

# if __name__ == "__main__":
#     port = int(os.getenv("PORT", 8080))
#     print(f"Starting python call agent on port {port}")
#     web.run_app(create_app(), host="0.0.0.0", port=port)










# # import os
# # import json
# # import asyncio
# # import traceback
# # import requests
# # from aiohttp import web


# # WHATSAPP_TOKEN = "EAAzIG7LU0TYBO4EsZCcETbfEgZAW79NJFQZCh3RJ5Y182q0CQVj0ELcdoEkgZCf3blKWbuCLdKtZBIKEOZAbh6x0RpdcXPEoSl2wxe8D1OUjpEvyz2O3eakLUqHQDLXbie3wcy9QJuFHaVLjxa1SHmutNdZCQvxM4MFqZB6ZCUdWdUJ8CueRn4LKZClBBZABcuqPHZAOHgZDZD"
# # PHONE_NUMBER_ID = "732355239960210"


# # # WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "").strip()
# # # PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "").strip()
# # GRAPH = "https://graph.facebook.com/v20.0"

# # # Public audio URL used when aiortc is NOT available (informational)
# # AUDIO_URL = "https://samplelib.com/lib/preview/wav/sample-3s.wav"


# # def make_fake_sdp():
# #     """
# #     Minimal placeholder SDP answer useful for testing flows where
# #     a true WebRTC stack is not available. Not a real media endpoint,
# #     but accepted by some test setups to progress call state.
# #     """
# #     return (
# #         "v=0\r\n"
# #         "o=- 0 0 IN IP4 0.0.0.0\r\n"
# #         "s=python-agent\r\n"
# #         "t=0 0\r\n"
# #         "m=audio 9 RTP/AVP 0\r\n"
# #         "c=IN IP4 0.0.0.0\r\n"
# #     )


# # async def handle_call(call):
# #     """
# #     Background worker to handle call events:
# #     - If incoming offer SDP present and aiortc available -> build real answer
# #     - Else -> send a fake SDP answer via pre_accept + accept (for testing)
# #     """
# #     try:
# #         if not isinstance(call, dict):
# #             print("Bad payload (not dict).")
# #             return

# #         event = call.get("event")
# #         call_id = call.get("id") or call.get("call_id") or call.get("waba_call_id")
# #         session = call.get("session", {}) or {}
# #         print("[handle_call] event:", event, "id:", call_id)

# #         # Only process connect/offer/incoming types for answering
# #         if event not in ("connect", "offer", "incoming"):
# #             print("[handle_call] ignoring event:", event)
# #             return

# #         incoming_sdp = session.get("sdp") or session.get("offer") or None

# #         # Try to import aiortc dynamically
# #         use_aiortc = False
# #         try:
# #             from aiortc import RTCPeerConnection, RTCSessionDescription, MediaPlayer  # type: ignore
# #             use_aiortc = True
# #             print("[handle_call] aiortc imported successfully.")
# #         except Exception as e:
# #             print("[handle_call] aiortc not available, falling back to fake SDP. Import error:", str(e))

# #         if use_aiortc and incoming_sdp:
# #             # Build a real answer using aiortc
# #             try:
# #                 pc = RTCPeerConnection()

# #                 # If you want to play an audio file to the caller, uncomment below:
# #                 try:
# #                     player = MediaPlayer(AUDIO_URL)
# #                     if player.audio:
# #                         pc.addTrack(player.audio)
# #                         print("[handle_call] added MediaPlayer audio track")
# #                 except Exception as e:
# #                     print("[handle_call] MediaPlayer init failed:", e)

# #                 # set remote (incoming) offer
# #                 offer = RTCSessionDescription(incoming_sdp, "offer")
# #                 await pc.setRemoteDescription(offer)

# #                 # create answer
# #                 answer = await pc.createAnswer()
# #                 await pc.setLocalDescription(answer)

# #                 local_sdp = pc.localDescription.sdp
# #                 print("[handle_call] generated real SDP answer (length):", len(local_sdp))

# #                 # send pre_accept
# #                 if WHATSAPP_TOKEN and PHONE_NUMBER_ID:
# #                     try:
# #                         requests.post(
# #                             f"{GRAPH}/{PHONE_NUMBER_ID}/calls",
# #                             headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
# #                             json={
# #                                 "messaging_product": "whatsapp",
# #                                 "call_id": call_id,
# #                                 "action": "pre_accept",
# #                                 "session": {"sdp_type": "answer", "sdp": local_sdp}
# #                             },
# #                             timeout=10
# #                         )
# #                         print("[handle_call] sent pre_accept (real sdp)")
# #                     except Exception as e:
# #                         print("[handle_call] pre_accept POST failed:", e)

# #                 # accept after ICE connected (best-effort)
# #                 @pc.on("iceconnectionstatechange")
# #                 async def on_ice():
# #                     print("[handle_call] ICE state changed:", pc.iceConnectionState)
# #                     if pc.iceConnectionState == "connected":
# #                         try:
# #                             requests.post(
# #                                 f"{GRAPH}/{PHONE_NUMBER_ID}/calls",
# #                                 headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
# #                                 json={
# #                                     "messaging_product": "whatsapp",
# #                                     "call_id": call_id,
# #                                     "action": "accept",
# #                                     "session": {"sdp_type": "answer", "sdp": pc.localDescription.sdp}
# #                                 },
# #                                 timeout=10
# #                             )
# #                             print("[handle_call] sent accept (real sdp)")
# #                         except Exception as e:
# #                             print("[handle_call] accept POST failed:", e)

# #                 return

# #             except Exception as e:
# #                 print("[handle_call] error while generating real SDP:", e)
# #                 traceback.print_exc()

# #         # Fallback path: no aiortc OR incoming_sdp missing -> send fake SDP
# #         fallback_sdp = make_fake_sdp()
# #         print("[handle_call] using fallback fake SDP (testing only)")

# #         if WHATSAPP_TOKEN and PHONE_NUMBER_ID:
# #             try:
# #                 requests.post(
# #                     f"{GRAPH}/{PHONE_NUMBER_ID}/calls",
# #                     headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
# #                     json={
# #                         "messaging_product": "whatsapp",
# #                         "call_id": call_id,
# #                         "action": "pre_accept",
# #                         "session": {"sdp_type": "answer", "sdp": fallback_sdp}
# #                     },
# #                     timeout=10
# #                 )
# #                 print("[handle_call] sent pre_accept (fake sdp)")
# #             except Exception as e:
# #                 print("[handle_call] fake pre_accept failed:", e)

# #             # small delay, then accept
# #             await asyncio.sleep(0.5)
# #             try:
# #                 requests.post(
# #                     f"{GRAPH}/{PHONE_NUMBER_ID}/calls",
# #                     headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
# #                     json={
# #                         "messaging_product": "whatsapp",
# #                         "call_id": call_id,
# #                         "action": "accept",
# #                         "session": {"sdp_type": "answer", "sdp": fallback_sdp}
# #                     },
# #                     timeout=10
# #                 )
# #                 print("[handle_call] sent accept (fake sdp)")
# #             except Exception as e:
# #                 print("[handle_call] fake accept failed:", e)
# #         else:
# #             print("[handle_call] WHATSAPP_TOKEN or PHONE_NUMBER_ID not set; skipping Graph POSTs (OK for local test).")

# #     except Exception as exc:
# #         print("[handle_call] unexpected exception:", exc)
# #         traceback.print_exc()


# # # HTTP server + webhook
# # async def webhook(request):
# #     try:
# #         payload = await request.json()
# #     except Exception:
# #         text = await request.text()
# #         print("[webhook] invalid JSON body:", text[:2000])
# #         return web.Response(text="invalid json", status=400)

# #     print("[webhook] incoming payload (truncated):")
# #     try:
# #         print(json.dumps(payload, indent=2)[:2000])
# #     except Exception:
# #         print(str(payload)[:2000])

# #     # The incoming payload from Node may already be the `call` object or wrapped.
# #     # Normalize: if wrapper present, extract calls array
# #     calls = None
# #     if isinstance(payload, dict):
# #         # If this is directly the call object forwarded
# #         if payload.get("event") or payload.get("id"):
# #             calls = [payload]
# #         else:
# #             # try common WhatsApp wrapper shape
# #             entry = payload.get("entry") or []
# #             if entry and isinstance(entry, list):
# #                 try:
# #                     calls = entry[0]["changes"][0]["value"].get("calls")
# #                 except Exception:
# #                     calls = None

# #     if not calls:
# #         print("[webhook] no call object found in payload; acking and returning")
# #         # ack quickly
# #         return web.Response(text="no-call", status=200)

# #     # process each call in background
# #     for call in calls:
# #         asyncio.create_task(handle_call(call))

# #     # ACK immediately
# #     return web.Response(text="ok", status=200)


# # async def health(request):
# #     return web.Response(text="python-call-agent OK", status=200)


# # def create_app():
# #     app = web.Application()
# #     app.router.add_get("/", health)
# #     app.router.add_post("/", webhook)
# #     app.router.add_post("/run", webhook)  # keep both endpoints accepted
# #     return app


# # if __name__ == "__main__":
# #     port = int(os.getenv("PORT", 8080))
# #     print("Starting python call agent on port", port)
# #     web.run_app(create_app(), host="0.0.0.0", port=port)















# # # import os
# # # import json
# # # import asyncio
# # # import traceback
# # # import requests
# # # from aiohttp import web

# # # # -------------------------
# # # # Configuration
# # # # -------------------------
# # # WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "").strip()
# # # PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "").strip()
# # # GRAPH = "https://graph.facebook.com/v20.0"

# # # # Simple public audio URL (only informational — actual media via WebRTC SDP in real flow)
# # # AUDIO_URL = "https://samplelib.com/lib/preview/wav/sample-3s.wav"

# # # # -------------------------
# # # # Utility: generate minimal fake SDP
# # # # -------------------------
# # # def make_fake_sdp():
# # #     # Very minimal placeholder SDP. It is not a true media endpoint SDP,
# # #     # but many test setups accept a placeholder for validation steps.
# # #     return (
# # #         "v=0\r\n"
# # #         "o=- 0 0 IN IP4 127.0.0.1\r\n"
# # #         "s=python-agent\r\n"
# # #         "t=0 0\r\n"
# # #         "m=audio 9 RTP/AVP 0\r\n"
# # #         "c=IN IP4 0.0.0.0\r\n"
# # #     )

# # # # -------------------------
# # # # Background handler (simulated simple voice agent)
# # # # -------------------------
# # # async def handle_call_simple(call):
# # #     try:
# # #         if not isinstance(call, dict):
# # #             print("Invalid call payload (not a dict).")
# # #             return

# # #         event = call.get("event")
# # #         call_id = call.get("id")
# # #         session = call.get("session", {})

# # #         print("[handle_call_simple] event:", event, "id:", call_id)

# # #         if event != "connect":
# # #             print("Ignoring event (not connect):", event)
# # #             return

# # #         # If incoming had an SDP we could use it; for now build a safe fake answer
# # #         answer_sdp = make_fake_sdp()

# # #         # Pre-accept (optional if you want to test call flow)
# # #         if WHATSAPP_TOKEN and PHONE_NUMBER_ID:
# # #             try:
# # #                 resp = requests.post(
# # #                     f"{GRAPH}/{PHONE_NUMBER_ID}/calls",
# # #                     headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
# # #                     json={
# # #                         "messaging_product": "whatsapp",
# # #                         "call_id": call_id,
# # #                         "action": "pre_accept",
# # #                         "session": {"sdp_type": "answer", "sdp": answer_sdp}
# # #                     },
# # #                     timeout=15,
# # #                 )
# # #                 print("[pre_accept] status:", resp.status_code, "body:", resp.text[:1000])
# # #             except Exception as e:
# # #                 print("[pre_accept] exception:", e)
# # #                 traceback.print_exc()
# # #         else:
# # #             print("[pre_accept] WHATSAPP_TOKEN or PHONE_NUMBER_ID not set — skipping real pre_accept (OK for local testing).")

# # #         # small delay to simulate processing
# # #         await asyncio.sleep(1)

# # #         # Accept call (again with fake SDP)
# # #         if WHATSAPP_TOKEN and PHONE_NUMBER_ID:
# # #             try:
# # #                 resp = requests.post(
# # #                     f"{GRAPH}/{PHONE_NUMBER_ID}/calls",
# # #                     headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
# # #                     json={
# # #                         "messaging_product": "whatsapp",
# # #                         "call_id": call_id,
# # #                         "action": "accept",
# # #                         "session": {"sdp_type": "answer", "sdp": answer_sdp}
# # #                     },
# # #                     timeout=15,
# # #                 )
# # #                 print("[accept] status:", resp.status_code, "body:", resp.text[:1000])
# # #             except Exception as e:
# # #                 print("[accept] exception:", e)
# # #                 traceback.print_exc()
# # #         else:
# # #             print("[accept] WHATSAPP_TOKEN or PHONE_NUMBER_ID not set — skipping real accept (OK for local testing).")

# # #         # Optionally: log the audio URL we'll "play"
# # #         print("[handle_call_simple] (simulated) will play audio:", AUDIO_URL)

# # #     except Exception as exc:
# # #         print("[handle_call_simple] Exception:", exc)
# # #         traceback.print_exc()


# # # # -------------------------
# # # # Webhook HTTP handler
# # # # -------------------------
# # # async def webhook(request):
# # #     try:
# # #         data = await request.json()
# # #     except Exception:
# # #         raw = await request.text()
# # #         print("[webhook] Invalid JSON body:", raw[:2000])
# # #         return web.Response(text="invalid json", status=400)

# # #     print("[webhook] Received payload (truncated):")
# # #     try:
# # #         print(json.dumps(data, indent=2)[:2000])
# # #     except Exception:
# # #         print(str(data)[:2000])

# # #     # Process in background so we immediately ack the webhook
# # #     asyncio.create_task(handle_call_simple(data))

# # #     return web.Response(text="OK", status=200)


# # # # -------------------------
# # # # Health endpoint
# # # # -------------------------
# # # async def health(request):
# # #     return web.Response(text="python-call-agent OK", status=200)


# # # # -------------------------
# # # # App setup
# # # # -------------------------
# # # def create_app():
# # #     app = web.Application()
# # #     app.router.add_get("/", health)
# # #     app.router.add_post("/run", webhook)  # /run used by many webhook setups
# # #     return app


# # # app = create_app()


# # # # -------------------------
# # # # Run server (Cloud Run compatible)
# # # # -------------------------
# # # if __name__ == "__main__":
# # #     port = int(os.getenv("PORT", 8080))
# # #     print(f"Starting python-call-agent on 0.0.0.0:{port}")
# # #     web.run_app(app, host="0.0.0.0", port=port)
