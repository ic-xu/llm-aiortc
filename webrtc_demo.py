

import cv2
import numpy as np

class SFUServer:
    def __init__(self):
        self.streams = {}

    def add_stream(self, stream_id, pc):
        self.streams[stream_id] = pc

    def on_track(self, stream_id, track):
        if track.kind == "video":
            self.add_stream(stream_id, track)
            track.on("frame", self.process_frame)

    async def process_frame(self, frame):
        # 将帧转换为numpy数组
        img = frame.to_ndarray()
        
        # 在这里进行视频流的美化处理，例如应用滤镜
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # 示例：将图像转换为灰度
        
        # 将处理后的帧转换回适合发送的格式
        processed_frame = frame.from_ndarray(img, format="bgr")
        
        # 发送处理后的帧到客户端
        await self.send_to_client(frame.stream_id, processed_frame)
        return processed_frame

    async def send_to_client(self, stream_id, frame):
        pc = self.streams.get(stream_id)
        if pc:
            await pc.send(frame)

    async def on_message(self, message):
        # 处理来自客户端的消息
        pass