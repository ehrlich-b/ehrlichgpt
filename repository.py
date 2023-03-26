import os
import sqlite3
from conversation import Conversation
from message import Message
from langchain.chat_models import ChatOpenAI
class Repository:
    def create_db_if_not_exists(db_path):
        conn = sqlite3.connect(db_path)
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

    def clear_messages(db_path):
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM messages")
        conn.commit()
        conn.close()

    def save_message(db_path, sender, content):
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO messages (sender, content) VALUES (?, ?)", (sender, content))
        conn.commit()
        conn.close()

    def save_conversation_context(db_path, conversation_context):
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM conversation_context")
        conn.execute("INSERT INTO conversation_context (context) VALUES (?)", (conversation_context,))
        conn.commit()
        conn.close()

    def save_long_term_memory(db_path, long_term_memory):
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM long_term_memory")
        conn.execute("INSERT INTO long_term_memory (memory) VALUES (?)", (long_term_memory,))
        conn.commit()
        conn.close()

    def load_messages(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT sender, content FROM messages")
        messages = cursor.fetchall()
        conn.close()
        return messages

    def load_conversation_context(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT context FROM conversation_context")
        context = cursor.fetchone()
        conn.close()
        return context[0] if context else ''

    def load_long_term_memory(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT memory FROM long_term_memory")
        memory = cursor.fetchone()
        conn.close()
        return memory[0] if memory else ''

    def sync_conversation_context(db_path, conversation):
        Repository.clear_messages(db_path)
        for message in conversation.messages:
            Repository.save_message(db_path, message.sender, message.content)
        Repository.save_conversation_context(db_path, conversation.conversation_context)
        Repository.save_long_term_memory(db_path, conversation.long_term_memory)

    def load_conversation(channel_id, db_path):
        messages = Repository.load_messages(db_path)
        conversation_context = Repository.load_conversation_context(db_path)
        long_term_memory = Repository.load_long_term_memory(db_path)
        conversation = Conversation(channel_id, [], conversation_context, long_term_memory)
        for sender, content in messages:
            conversation.add_message(Message(sender, content))
        return conversation

    @staticmethod
    async def summarize_conversation(conversation):
        while len(conversation.conversation_history) > 1 and conversation.get_conversation_token_count() > 400:
            print(conversation.get_conversation_token_count())
            await conversation.run_summarizer()
            new_messages = []
            total_tokens = 0
            for message in reversed(conversation.conversation_history):
                new_messages.insert(0, message)
                total_tokens += message.get_number_of_tokens()
                if total_tokens > 50:
                    break
            conversation.conversation_history = new_messages
            conversation.sync_busy_history()
            print(conversation.get_conversation_token_count())
            Repository.save_conversation_context(Repository.get_db_path(conversation.conversation_id), conversation.active_memory)
            Repository.clear_messages(Repository.get_db_path(conversation.conversation_id))
            for message in conversation.conversation_history:
                Repository.save_message(Repository.get_db_path(conversation.conversation_id), message.sender, message.content)


    def get_db_path(channel_id):
        return os.path.join("conversations", f"{channel_id}.db")
