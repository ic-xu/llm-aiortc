import av
from aiortc import VideoStreamTrack, MediaStreamTrack
from av.frame import Frame
import time
import fractions


class VideoStreamTrackToMP4(VideoStreamTrack):
    def __init__(self, output_file):
        super().__init__()
        self.output_file = output_file
        self.container = av.open(output_file, mode='w')
        self.stream = self.container.add_stream('h264', rate=30)
        self.stream.width = 640
        self.stream.height = 480
        self.video_track = None
        self.audio_track = None
        self.stream.pix_fmt = 'yuv420p'
        self.start_time = None
        self.audio_pts = 0
        self.video_pts = 0
        self.audio_stream = self.container.add_stream('aac')
        self.video_time_base = fractions.Fraction(1, 30)  # 假设视频帧率为30fps
        self.audio_time_base = fractions.Fraction(1, 48000)  # 假设音频采样率为48kHz



    async def recv(self) -> Frame:
        if self.video_track is None:
            raise ValueError("视频轨道未设置")
        
        frame: Frame = await self.video_track.recv()
        if self.start_time is None:
            self.start_time = time.time()
        
        # 计算视频帧的时间戳
        self.video_pts = int((time.time() - self.start_time) / self.video_time_base)
        frame.pts = self.video_pts
        frame.time_base = self.video_time_base
        
        packets = self.stream.encode(frame)
        if packets:
            for packet in packets:
                packet.pts = self.video_pts
                packet.dts = self.video_pts
                packet.time_base = self.video_time_base
                self.container.mux(packet)
        
        # 同时处理音频数据
        await self.process_audio()
        
        return frame

    async def process_audio(self):
        if self.audio_track is None:
            return
        
        try:
            audio_frame: Frame = await self.audio_track.recv()
            
            # 计算音频帧的时间戳
            self.audio_pts = int((time.time() - self.start_time) / self.audio_time_base)
            audio_frame.pts = self.audio_pts
            audio_frame.time_base = self.audio_time_base
            
            audio_packets = self.audio_stream.encode(audio_frame)
            if audio_packets:
                for packet in audio_packets:
                    packet.pts = self.audio_pts
                    packet.dts = self.audio_pts
                    packet.time_base = self.audio_time_base
                    self.container.mux(packet)
        except Exception as e:
            print(f"处理音频数据时出错: {e}")

    async def recv_audio(self) -> Frame:
        if self.audio_track is None:
            raise ValueError("音频轨道未设置")
        
        frame: Frame = await self.audio_track.recv()
        if self.start_time is None:
            self.start_time = time.time()
        
        # 计算音频帧的时间戳
        self.audio_pts = int((time.time() - self.start_time) / self.audio_time_base)
        frame.pts = self.audio_pts
        frame.time_base = self.audio_time_base
        
        packets = self.audio_stream.encode(frame)
        if packets:
            for packet in packets:
                packet.pts = self.audio_pts
                packet.dts = self.audio_pts
                packet.time_base = self.audio_time_base
                self.container.mux(packet)
        
        return frame

    def close(self):
        try:
            self.container.close()
        except Exception as e:
            print(f"Error in closing container: {e}")

#
# # 使用示例
# async def main():
#     video_track = VideoStreamTrackToMP4('output.mp4')
#     try:
#         for _ in range(300):  # 生成10秒的视频 (30fps * 10s)
#             await video_track.recv()
#     finally:
#         video_track.close()
#
#
# # 运行示例
# asyncio.run(main())
