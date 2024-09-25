
from kerner.stream_manager import StreamManager



class AppContext:
    def __init__(self):
        self.stream_manager = StreamManager()

    def add_track(self, track):
        self.recorder.addTrack(track)

    def start(self):
        self.recorder.start()