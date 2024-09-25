from kerner.stream import Stream


class StreamManager:
    def __init__(self):
        self.streams = {}

    def add_stream(self, stream: Stream):
        self.streams[stream.stream_id] = stream

    def get_stream(self, stream_id: str):
        return self.streams.get(stream_id)
    
    def remove_stream(self, stream: Stream):
        if stream.stream_id in self.streams:
            del self.streams[stream.stream_id]