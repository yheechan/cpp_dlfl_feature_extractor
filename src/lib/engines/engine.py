


class Engine:
    def __init__(self, config: dict):
        self.config = config

    def run(self):
        raise NotImplementedError("Subclasses should implement this method.")

    def log(self, message: str):
        print(f"[EngineBase] {message}")