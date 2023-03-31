

import time
from utils import tokenize_text

class Memory:
    def __init__(self, id, memory_text, unix_timestamp, serialized_embedding):
        self.id = id
        self.memory_text = memory_text
        self.unix_timestamp = unix_timestamp
        self.serialized_embedding = serialized_embedding
        self.text_token_count = -1

    # Function that gets the token count of memory_text
    def get_token_count(self):
        if self.text_token_count == -1:
            self.text_token_count = len(tokenize_text(self.memory_text))
        return self.text_token_count

    def __str__(self):
        return "Memory(id={}, memory_text='{}', timestamp={})".format(self.id, self.memory_text, self.timestamp)

    def llm_readable_time_in_past(self):
        seconds_in_year = 60 * 60 * 24 * 365
        seconds_in_month = 60 * 60 * 24 * 30
        seconds_in_week = 60 * 60 * 24 * 7
        seconds_in_day = 60 * 60 * 24
        seconds_in_hour = 60 * 60
        seconds_in_minute = 60

        seconds_in_past = time.time() - self.unix_timestamp

        if seconds_in_past < seconds_in_minute:
            return "just now"
        elif seconds_in_past < seconds_in_hour:
            return "{} minutes ago".format(int(seconds_in_past / seconds_in_minute))
        elif seconds_in_past < seconds_in_day:
            return "{} hours ago".format(int(seconds_in_past / seconds_in_hour))
        elif seconds_in_past < seconds_in_week:
            return "{} days ago".format(int(seconds_in_past / seconds_in_day))
        elif seconds_in_past < seconds_in_month:
            return "{} weeks ago".format(int(seconds_in_past / seconds_in_week))
        elif seconds_in_past < seconds_in_year:
            return "{} months ago".format(int(seconds_in_past / seconds_in_month))
        else:
            return "{} years ago".format(int(seconds_in_past / seconds_in_year))

