from aiortc.contrib.media import MediaRecorder

from kerner.process.processor import Processor
from kerner.stream_state import StreamState
import asyncio
import logging

logger = logging.getLogger(__name__)


class MP4Recorder(Processor):

    def __init__(self, stream):
        self.recorder = None
        self.stream = stream
        self.recorder_started = False
        self.recorder = MediaRecorder(f'output_{stream.stream_id}.mp4')

    def process(self):
        self.record()

    def record(self):
        logging.info("开始录制方法")
        # 录制成视频的方法
        for track in self.stream.tracks.values():
            if track.kind in ["video", "audio"]:
                self.recorder.addTrack(track)
                logging.info(f"添加了 {track.kind} 轨道")

        # 启动录制器
        asyncio.get_event_loop().run_until_complete(self.recorder.start())
        self.recorder_started = True
        logging.info("录制器已启动")

        # 持续检查流的状态
        while self.stream.state.value == StreamState.RUNNING.value:
            asyncio.get_event_loop().run_until_complete(asyncio.sleep(1))

        # 当流结束时，停止录制
        logging.info("停止录制")
        asyncio.get_event_loop().run_until_complete(self.recorder.stop())

    def stop(self):
        # 如果需要手动停止录制，可以调用这个方法
        if self.recorder_started:
            asyncio.get_event_loop().run_until_complete(self.recorder.stop())
            self.recorder_started = False
        logging.info("录制已停止")