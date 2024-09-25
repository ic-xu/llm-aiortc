import asyncio

from av import AudioFrame

from kerner.process.processor import Processor
from kerner.stream import StreamState


class ASRProcessor(Processor):
    def __init__(self, audio_queue: asyncio.Queue):
        self.audio_queue = audio_queue

    async def process(self):
        return await self.asr()
    

    async def asr(self):
        while self.stream.state.value == StreamState.RUNNING.value:
            for track in self.stream.tracks.values():
                if track.kind == "audio":
                    frame = await track.recv()
                    self.process_asr(frame)

        # 实现语音转文字逻辑
        await self.on_stream_completed_or_error()




    async def on_stream_completed_or_error(self):
        pass


    async def process_asr(self, frame:AudioFrame):
        pass