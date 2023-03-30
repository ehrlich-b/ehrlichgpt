import os
import sqlite3

from conversation import Conversation
from message import Message


class Repository:
    def __init__(self, channel_id: int) -> None:
        self.db_path = self.__get_db_path(channel_id)
        self.__create_db_if_not_exists()

    def clear_messages(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM messages")
        conn.commit()
        conn.close()

    def save_message(self, sender, content):
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO messages (sender, content) VALUES (?, ?)", (sender, content))
        conn.commit()
        conn.close()

    def save_conversation_context(self, conversation_context):
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM conversation_context")
        conn.execute("INSERT INTO conversation_context (context) VALUES (?)", (conversation_context,))
        conn.commit()
        conn.close()

    def save_long_term_memory(self, long_term_memory):
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM long_term_memory")
        conn.execute("INSERT INTO long_term_memory (memory) VALUES (?)", (long_term_memory,))
        conn.commit()
        conn.close()

    def load_messages(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT sender, content FROM messages")
        messages = cursor.fetchall()
        conn.close()
        return messages

    def load_conversation_context(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT context FROM conversation_context")
        context = cursor.fetchone()
        conn.close()
        return context[0] if context else ''

    def load_long_term_memory(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT memory FROM long_term_memory")
        memory = cursor.fetchone()
        conn.close()
        return memory[0] if memory else ''

    def sync_conversation_context(self, conversation):
        self.clear_messages()
        for message in conversation.messages:
            self.save_message(message.sender, message.content)
        self.save_conversation_context(conversation.conversation_context)
        self.save_long_term_memory(conversation.long_term_memory)

    def load_conversation(self, channel_id):
        messages = self.load_messages()
        conversation_context = self.load_conversation_context()
        long_term_memory = self.load_long_term_memory()
        conversation = Conversation(channel_id, [], conversation_context, long_term_memory)
        for sender, content in messages:
            conversation.add_message(Message(sender, content))
        return conversation

    async def summarize_conversation(self, conversation, trigger_token_limit=400, conversation_window_tokens=200):
        needed_summary=False
        while len(conversation.conversation_history) > 1 and conversation.get_conversation_token_count() > trigger_token_limit:
            needed_summary=True
            print(conversation.get_conversation_token_count())
            await conversation.run_summarizer()
            new_messages = []
            total_tokens = 0
            for message in reversed(conversation.conversation_history):
                potential_total_tokens = total_tokens + message.get_number_of_tokens()
                if potential_total_tokens > trigger_token_limit:
                    break
                new_messages.insert(0, message)
                total_tokens = potential_total_tokens
                if total_tokens > conversation_window_tokens:
                    break
            conversation.conversation_history = new_messages
            conversation.sync_busy_history()
            print(conversation.get_conversation_token_count())
            self.save_conversation_context(conversation.active_memory)
            self.clear_messages()
            for message in conversation.conversation_history:
                self.save_message(message.sender, message.content)
        return needed_summary

    def __get_db_path(self, channel_id: int) -> str:
        return os.path.join("conversations", f"{channel_id}.db")

    def __create_db_if_not_exists(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute('''CREATE TABLE IF NOT EXISTS messages
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sender TEXT NOT NULL,
                        content TEXT NOT NULL);''')
        conn.execute('''CREATE TABLE IF NOT EXISTS conversation_context
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        context TEXT NOT NULL);''')
        conn.execute('''CREATE TABLE IF NOT EXISTS long_term_memory
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        memory TEXT NOT NULL);''')
        conn.commit()
        conn.close()
