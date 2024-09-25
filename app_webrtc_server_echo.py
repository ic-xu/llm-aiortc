import argparse
import asyncio
import json
import logging
import ssl
from aiohttp import web
import aiohttp_cors
from aiortc import RTCPeerConnection, RTCSessionDescription
from kerner.stream import Stream
from kerner.stream_manager import StreamManager

logger = logging.getLogger("pc")


async def offer(request):
    remote_addr = request.remote
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"连接状态变更: {pc.connectionState}")

    @pc.on("track")
    def on_track(track):
        logger.info(f"接收到 {track.kind} 轨道")
        pc.addTrack(track)

    @pc.on("datachannel")
    def on_datachannel(channel):
        @channel.on("message")
        def on_message(message):
            channel.send(message)  # 回声数据通道消息

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        })
    )


async def on_shutdown(app):
    for stream in app.streamManager.streams.values():
        coros = [pc.close() for pc in stream.pcs]
        await asyncio.gather(*coros)
        stream.pcs.clear()


class WebRTCServerApp(web.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.streamManager = StreamManager()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC SFU Server")
    parser.add_argument("--cert-file", help="SSL certificate file (for HTTPS)")
    parser.add_argument("--key-file", help="SSL key file (for HTTPS)")
    parser.add_argument("--host", default="0.0.0.0", help="Host for HTTP server (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Port for HTTP server (default: 8080)")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.cert_file:
        ssl_context = ssl.SSLContext()
        ssl_context.load_cert_chain(args.cert_file, args.key_file)
    else:
        ssl_context = None

    app = WebRTCServerApp()
    app.on_shutdown.append(on_shutdown)
    # app.router.add_get("/", index)
    # app.router.add_get("/client.js", javascript)
    # app.router.add_get("/styles.css", css)
    app.router.add_post("/offer", offer)
    # 添加跨域中间件
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    # 为所有路由添加跨域支持
    for route in list(app.router.routes()):
        cors.add(route)

    web.run_app(app, host=args.host, port=args.port, ssl_context=ssl_context)
