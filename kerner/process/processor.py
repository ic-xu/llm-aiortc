import asyncio
from abc import ABC, abstractmethod
from typing import List


class Processor(ABC):
    @abstractmethod
    def process(self):
        pass


class ProcessManager(ABC):
    def __init__(self, processors: List[Processor]):
        self.processors = processors

    def process(self):
        for processor in self.processors:
            asyncio.create_task(processor.process())
