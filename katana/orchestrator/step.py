from abc import ABC, abstractmethod

class StepResult:
    def __init__(self, success, message=""):
        self.success = success
        self.message = message

class Step(ABC):
    def __init__(self, id, action, context):
        self.id = id
        self.action = action
        self.context = context

    @abstractmethod
    async def execute(self) -> StepResult:
        pass

class StepExecutor(ABC):
    @abstractmethod
    def can_handle(self, step_type):
        pass

    @abstractmethod
    def create_step(self, id, action, context):
        pass
