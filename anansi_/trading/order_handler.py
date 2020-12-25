from .schemas import Operation

class OrderHandler:
    def __init__(self, operation: Operation):
        self.operation = operation
    
    def proceed(self):
        pass