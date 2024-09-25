import asyncio
import logging

from aiortc import RTCPeerConnection

from kerner.stream_state import StreamState

logger = logging.getLogger(__file__)


class Stream:

    def __init__(self, stream_id: str, pc: RTCPeerConnection):
        self.stream_id = stream_id
        self.pc = pc
        self.tracks = {}
        self.state = StreamState.INIT
        self.audio_queue = asyncio.Queue()
        self.video_queue = asyncio.Queue()
        self.pcs = set()
        self.remote_addr = None
        self.data_channel = None
        self.pcs.add(pc)

    def on_message(self, message):
        # receive message from data channel
        pass

    async def on_connectionstatechange(self):
        logger.info(f"连接状态变更: {self.pc.connectionState}")

    def on_datachannel(self, data_channel):
        @data_channel.on("message")
        async def on_message(message):
            self.on_message(message)

        self.data_channel = data_channel

    def on_track(self, remote_addr: str, track):
        if track.kind in ["audio", "video"]:
            self.pc.addTrack(track)
            self.tracks[track.kind] = track
            self.state = StreamState.RUNNING


        @track.on("ended")
        async def on_ended():
            logger.info(f"track {track.kind} 结束")
            self.audio_queue.put_nowait(None)
            self.video_queue.put_nowait(None)
            self.tracks.pop(track.kind, None)
            if len(self.tracks) == 0:
                self.state = StreamState.COMPLETED
                await self.on_completed()

    async def on_completed(self):
        self.state = StreamState.COMPLETED

    async def on_error(self, error):
        self.state = StreamState.ERROR

    def on_iceconnectionstatechange(self):
        logger.info(f"ICE 连接状态: {self.pc.iceConnectionState}")

    def on_icegatheringstatechange(self):
        logger.info(f"ICE 收集状态: {self.pc.iceGatheringState}")
