from abc import ABC, abstractmethod
class CameraSetting(ABC):
    s_nodemap = None

    @abstractmethod
    def setNodeMap(self, s_nodemap):
        pass

    @abstractmethod
    def setNodeValue(self, nodeName, nodeValue, option):
        pass

    @abstractmethod
    def IsNodeAvailable(self, node, option="arw"):
        pass