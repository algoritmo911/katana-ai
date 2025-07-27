from abc import ABC, abstractmethod

class BaseAgent(ABC):
    @abstractmethod
    def get_response(self, user_input):
        pass

    @abstractmethod
    def render_ui(self):
        pass
