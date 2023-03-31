import os
import sqlite3
import faiss
import numpy as np

from conversation import Conversation
from memory import Memory
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

    def save_long_term_memory(self, long_term_memory, unix_timestamp, serialized_embedding):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO long_term_memory (timestamp, memory_text, embedding_serialized_csv_text) VALUES (?, ?, ?)", (unix_timestamp, long_term_memory, serialized_embedding))
        memory_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return memory_id

    def save_long_term_memory_index(self, faiss_index):
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM long_term_memory_index")
        conn.execute("INSERT INTO long_term_memory_index (serialized_faiss_index) VALUES (?)", (faiss.serialize_index(faiss_index),))
        conn.commit()
        conn.close()

    def load_long_term_memory_index(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT serialized_faiss_index FROM long_term_memory_index")
        serialized_index = cursor.fetchone()
        conn.close()
        if serialized_index:
            serialized_index_np = np.frombuffer(serialized_index[0], dtype=np.uint8)
            return faiss.deserialize_index(serialized_index_np)
        else:
            return None

    def load_memory(self, id):
        conn = sqlite3.connect(self.db_path)
        print(self.db_path)
        print("id type:", type(id))
        cursor = conn.execute("SELECT id, memory_text, timestamp, embedding_serialized_csv_text FROM long_term_memory WHERE id=?", (id,))
        memory = cursor.fetchone()
        print(id)
        print(memory)
        conn.close()
        return Memory(memory[0], memory[1], memory[2], memory[3]) if memory else None

    # Load ordered embeddings ascending by id
    def load_embeddings(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT embedding_serialized_csv_text FROM long_term_memory ORDER BY id ASC")
        embeddings = cursor.fetchall()
        conn.close()
        return [list(map(float, embedding[0].split(','))) for embedding in embeddings]

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

    def sync_conversation_context(self, conversation):
        self.clear_messages()
        for message in conversation.messages:
            self.save_message(message.sender, message.content)
        self.save_conversation_context(conversation.conversation_context)
        self.save_long_term_memory(conversation.long_term_memory)

    def load_conversation(self, channel_id):
        messages = self.load_messages()
        conversation_context = self.load_conversation_context()
        long_term_memory = ''
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
        conn.execute('''CREATE TABLE IF NOT EXISTS long_term_memory (
            id INTEGER PRIMARY KEY,
            timestamp INTEGER,
            memory_text TEXT,
            embedding_serialized_csv_text TEXT
        )''')

        conn.execute('''CREATE TABLE IF NOT EXISTS long_term_memory_index (
            id INTEGER PRIMARY KEY,
            serialized_faiss_index BLOB
        )''')
        conn.commit()
        conn.close()
