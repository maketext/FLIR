from abc import ABC, abstractmethod
class CameraAction(ABC):
    system = None
    cams = None

    @abstractmethod
    def triggerSet(self):
        pass

    @abstractmethod
    def frameProcessor(self):
        pass

    @abstractmethod
    def onGrab(self):
        pass