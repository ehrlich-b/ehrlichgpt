

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
