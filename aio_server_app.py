import argparse
import asyncio
import json
import logging
import os
import ssl
import threading
from asyncio import create_task
from html_resource import index,javascript,css
from aiohttp import web
from aiortc import RTCSessionDescription, MediaStreamTrack
from av import open as av_open

from stream.states import State
from stream.video_stream_track import VideoStreamTrackToMP4

logger = logging.getLogger("pc")
ROOT = os.path.dirname(__file__)

pcs = set()

output = av_open('static/output.mp4', mode='w')


async def offer(request):
    params = await request.json()

    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    print("Came inside offer")

    state = State()
    pcs.add(state)

    state.log_info("Created for %s", request.remote)

    state.pc.addTrack(state.response_player)
    state.pc.addTrack(state.video_player)

    video_track = VideoStreamTrackToMP4(output_file='static/output.mp4')

    @state.pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        state.log_info("ICE connection state is %s", state.pc.iceConnectionState)
        if state.pc.iceConnectionState == "failed":
            await state.pc.close()
            pcs.remove(state)
            state.recording = False
        if state.pc.iceConnectionState == "closed":
            pcs.remove(state)
            state.recording = False
        print(pcs)

    async def record(audio_track: VideoStreamTrackToMP4):
        state.log_info("Recording %s", state.filename)
        state.recording = True
        while state.recording:
            await audio_track.recv_audio()
            await asyncio.sleep(0)
        audio_track.close()

    async def record_av(video_track: VideoStreamTrackToMP4):
        state.recording=True
        while state.recording:
            await video_track.recv()
            await asyncio.sleep(0)
        video_track.close()

    @state.pc.on("track")
    async def on_track(track: MediaStreamTrack):
        state.log_info("Track %s received", track.kind)

        if track.kind == "audio":
            state.log_info("Received %s", track.kind)
            video_track.audio_track = track
            # state.task = create_task(record(video_track))

        if track.kind == "video":
            state.log_info("Received %s", track.kind)
            video_track.video_track = track
            state.task = create_task(record_av(video_track))

        @track.on("ended")
        async def on_ended():
            state.log_info("Track %s ended", track.kind)
            state.task.cancel()
            track.stop()
            video_track.close()
            state.recording = False
            state.response_player.response_ended = True

    # handle offer
    await state.pc.setRemoteDescription(offer)

    # send answer
    answer = await state.pc.createAnswer()
    await state.pc.setLocalDescription(answer)

    @state.pc.on("datachannel")
    async def on_datachannel(channel):
        state.log_info("DataChannel")
        state.response_player.channel = channel

        @channel.on("message")
        async def on_message(message):
            state.log_info("Received message on channel: %s", message)
            if message == "get_response":
                state.response_player.response_ready = True
            if message == "get_silence":
                state.response_player.response_ready = False
            if message == "start_recording":
                state.log_info("Start Recording")
                state.response_player.response_ready = False
                state.buffer = []
                state.recording = True
                state.counter += 1
                state.filename = f"{state.id}_{state.counter}.wav"
            if message == "stop_recording":
                state.log_info("Stop Recording")
                state.recording = False
                await asyncio.sleep(0.5)
                data = state.flush_audio()
                process_loop = create_bg_loop()
                asyncio.run_coroutine_threadsafe(process_request(data), process_loop)
            if message[0:7] == "preset:":
                preset = message[7:]
                state.log_info("Changed voice preset to %s", preset)
            if message[0:6] == "model:":
                model = message[6:]
                state.log_info("Changed model to %s", model)

        async def process_request(data):
            # TODO : Use the saved user.mp3 file
            continue_to_synthesize, response = await transcribe_request(data)
            if continue_to_synthesize:
                response = response.strip().split("\n")[0]
                state.log_info(response)
                await synthesize_response(response)
            # try:
            #     loop = asyncio.get_running_loop()
            #     loop.stop()
            # finally:
            #     pass

        async def transcribe_request(data):
            response = None
            state.response_player.reset_step()
            # Lets say that the user is saying "I am a good boy"
            # and it takes 500ms to find that from the audio (user.mp3)
            await asyncio.sleep(0.5)
            transcription = 'I am a good boy'
            channel.send(f"Human: {transcription}")
            state.log_info(transcription)

            await generate_dummy_llm(state)

            response = 'Yes you are'
            continue_to_synthesize = True
            return continue_to_synthesize, response

        async def generate_dummy_llm(state: State):
            config = {"bark_out.wav": 0.5, "sample-3s.wav": 0.5, "sample-9s.wav": 1.5}

            state.response_player.response_ready = True
            for audio, sleep_delay in config.items():
                print(f"audio {audio} sleep_delay {sleep_delay}")
                # Assume it takes another 500ms to get the LLM first partial response
                print(f"Before SLEEP {sleep_delay}")
                await asyncio.sleep(sleep_delay)  # TODO -> This needs to be replaced with actual LLM logic
                print("AFTER SLEEP")
                # Now the audio is ready
                state.response_player.add_partial_audio(audio)
                # Let go of control of event loop so audio streaming for first audio can begin
                await asyncio.sleep(0)

            state.response_player.set_last_step(3)
            # # Now start sending silence
            # state.response_player.reset_step()

        async def synthesize_response(response):
            if len(response.strip()) > 0:
                channel.send(f"AI: {response}")
                await asyncio.sleep(0)
                state.response_player.response_ready = True
            else:
                channel.send("playing: response")
                channel.send("playing: silence")
            await asyncio.sleep(0)

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": state.pc.localDescription.sdp, "type": state.pc.localDescription.type}
        ),
    )


async def on_shutdown(app):
    # close peer connections
    coros = [state.pc.close() for state in pcs]
    for state in pcs:
        print(f"Deleting file {state.filename}")
        # deleteFile(state.filename)
    await asyncio.gather(*coros)


def deleteFile(filename):
    try:
        os.remove(filename)
    except OSError:
        pass


# https://gist.github.com/ultrafunkamsterdam/8be3d55ac45759aa1bd843ab64ce876d
def create_bg_loop():
    def to_bg(loop):
        asyncio.set_event_loop(loop)
        try:
            loop.run_forever()
        except asyncio.CancelledError as e:
            print('CANCELLEDERROR {}'.format(e))
        finally:
            for task in asyncio.all_tasks(loop):
                task.cancel()
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.stop()
            loop.close()

    new_loop = asyncio.new_event_loop()
    t = threading.Thread(target=to_bg, args=(new_loop,))
    t.start()
    return new_loop


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC AI Voice Chat")
    parser.add_argument("--cert-file", help="SSL certificate file (for HTTPS)")
    parser.add_argument("--key-file", help="SSL key file (for HTTPS)")
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host for HTTP server (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port for HTTP server (default: 8080)"
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.cert_file:
        ssl_context = ssl.SSLContext()
        ssl_context.load_cert_chain(args.cert_file, args.key_file)
    else:
        ssl_context = None

    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", index)
    app.router.add_get("/client.js", javascript)
    app.router.add_get("/styles.css", css)
    app.router.add_post("/offer", offer)
    web.run_app(app, host=args.host, port=args.port, ssl_context=ssl_context)
