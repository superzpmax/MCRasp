from collections import defaultdict

class Events:
    def __init__(self):
        self._handlers = defaultdict(list)

    def on(self, event_name):
        def wrapper(func):
            self._handlers[event_name].append(func)
            return func
        return wrapper

    async def fire(self, event_name, *args, **kwargs):
        for func in self._handlers[event_name]:
            result = func(*args, **kwargs)
            if callable(getattr(result, "__await__", None)):
                await result
        return True

events = Events()
