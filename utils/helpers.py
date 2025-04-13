import pytz
from datetime import datetime
from typing import Tuple
from config.settings import config

class TimeHelper:
    def __init__(self):
        self.tz = pytz.timezone(config.get("DEFAULT", "timezone"))
    
    def current_time(self) -> str:
        return datetime.now(self.tz).strftime("%x %X %Z")
    
    def format_seconds(self, seconds: int) -> Tuple[int, int, int]:
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return hours, minutes, seconds
    
    def timestamp_to_str(self, timestamp: int) -> str:
        return datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")

class ProgressColumn:
    def __init__(self):
        self.time_helper = TimeHelper()
    
    def __call__(self, task):
        return self.render(task)
    
    def render(self, task) -> str:
        return f"{task.completed}/{task.total} ta"