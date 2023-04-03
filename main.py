import traceback
from typing import Dict, Set
from builtins import Exception, int, isinstance, len, print, set, str
import asyncio
import os
import pprint
import random
from memory_retriever import MemoryRetriever
from web_searcher import WebSearcher
import time

import discord
from discord import DMChannel, TextChannel
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate

from conversation import Conversation
from message import Message
from repository import Repository
from utils import format_discord_mentions, get_formatted_date, scold, truncate_text
from web_searcher import WebSearcher

DISCORD_NAME = 'EhrlichGPT'

def clean_up_response(discord_name, original_response):
    print(f"Original response: {original_response}")
    search_term = "Response:"
    start_index = original_response.find(search_term)
    response = ""
    if start_index != -1:
        response_start = start_index + len(search_term)
        response = original_response[response_start:].strip()
        response = response.strip('\"')
    else:
        response = original_response
    if response.startswith(discord_name + ":"):
        response = response[len(discord_name + ":"):]
    elif response.startswith("AI:"):
        response = response[len("AI:"):]
    return response.strip()

async def run_chain(channel, chain, discord_context, conversation_context, long_term_memory, search_results, latest_messages):
    response = await chain.arun(
        discord_name=DISCORD_NAME,
        discord_context=discord_context,
        conversation_context=conversation_context,
        long_term_memory=long_term_memory,
        search_results=search_results,
        current_date=get_formatted_date(),
        latest_messages=latest_messages,
    )

    response = clean_up_response(DISCORD_NAME, response)
    message_to_send = response[:2000]
    print(f"Sending message: {message_to_send}")
    await channel.send(message_to_send)

def get_chat_llm(temperature=0.8, max_tokens=500, gpt_version=3):
    if gpt_version == 4:
        chat_llm = ChatOpenAI(temperature=temperature, max_tokens=max_tokens, model='gpt-4')
    else:
        chat_llm = ChatOpenAI(temperature=temperature, max_tokens=max_tokens)
    return chat_llm

def load_conversation(channel_id):
    repository = Repository(channel_id)
    messages = repository.load_messages()
    conversation_context = repository.load_conversation_context()
    long_term_memory = ''
    conversation = Conversation(channel_id, [], conversation_context, long_term_memory)
    for sender, content in messages:
        conversation.add_message(Message(sender, content, int(time.time())))
    return conversation

discord_bot_key = os.environ['DISCORD_BOT_TOKEN']
intents = discord.Intents.default()
intents.message_content = True
paused = False

# TODO: Make this configurable
admin = 'adotout#7295'

client = discord.Client(intents=intents)
client_user = None
conversations: Dict[int, Conversation] = {}
global_message_lock: asyncio.Lock = asyncio.Lock()

os.makedirs("conversations", exist_ok=True)

async def process_queue(conversation):
    while True:
        try:
            message = await conversation.queue.get()
            await queue_on_message(message)
            conversation.queue.task_done()
        except Exception as e:
            print("Ignoring error on_message: " + str(e))
            traceback.print_exc()
        except asyncio.CancelledError:
            break

async def queue_on_message(message):
    global paused, conversations, client_user
    pprint.pprint(message)
    channel_id = message.channel.id
    repository = Repository(channel_id)
    formatted_sender = message.author.name + "#" + message.author.discriminator
    at_mentioned = False
    if client_user in message.mentions:
        at_mentioned = True
    if "<@" + str(client_user.id) + ">" in message.content:
        at_mentioned = True

    if isinstance(message.channel, DMChannel):
        context = "Direct Message"
        at_mentioned = True
    elif isinstance(message.channel, TextChannel):
        context = "Group Room with " + str(len(message.channel.members)) + " members"
    else:
        context = "Unknown"

    if paused:
        if at_mentioned and not message.author == client_user:
            if formatted_sender == admin and 'unpause' in message.content.lower():
                paused = False
                await message.channel.send("I'm back, baby! 🤖")
            else:
                await message.channel.send("I've been paused, Bryan probably looked at the bill. 😅")
        return
    else:
        if formatted_sender == admin and 'pause' in message.content.lower():
            paused = True
            await message.channel.send("Bye 😴")
            return

    formatted_content = format_discord_mentions(message)
    current_conversation = conversations[channel_id]
    if message.author == client_user:
        # Add our own AI message to conversation
        truncated_content = truncate_text(formatted_content, 100)
        current_conversation.add_message(Message("ai", truncated_content, int(time.time())))
        repository.save_message("ai", truncated_content)
        # We're responding, so we're being talked to, we don't want to constantly summarize, but we also
        # don't want to re-submit huge history in prompts, so 500,300,[add when you try another]? Idk
        await repository.summarize_conversation(current_conversation, trigger_token_limit=300)
        return
    else:
        violates_rules = Message.violates_content_policy(message.content) # Use raw content here just in case usernames contain something that would censor
        if violates_rules:
            censored_content = Message.CENSORED
            if at_mentioned:
                scold_msg = "You there! " + formatted_sender + "! Halt! It's the thought police! 👮‍♂️\n\n"
                scold_msg += "You've been convicted of " + str(random.randint(2, 10)) + " counts of thought crime.\n\n"
                scold_msg += "I've prepared this statement as punishment:\n"
                scold_msg += await scold()
                await message.channel.send(scold_msg)
                at_mentioned = False
        else:
            censored_content = formatted_content

        requested_gpt_version = 3
        if at_mentioned and 'think hard' in censored_content.lower():
            requested_gpt_version = 4
        current_conversation.add_message(Message(formatted_sender, censored_content, int(time.time()), requested_gpt_version, at_mentioned))
        repository.save_message(formatted_sender, censored_content)

        if at_mentioned:
            await send_message_with_typing_indicator(current_conversation, context, message.channel, message)
        else:
            # Nobody is talking to us, summarize larger chunks so we're not constantly churning through summarization
            await repository.summarize_conversation(current_conversation, trigger_token_limit=500)

@client.event
async def on_ready():
    global client_user
    print(f'We have logged in as {client.user}')
    client_user = client.user
    for db_file in os.listdir("conversations"):
        if db_file == ".gitignore":
            continue
        channel_db = os.path.splitext(db_file)[0]
        channel_id = int(channel_db.split('.')[0])
        conversations[channel_id] = load_conversation(channel_id)
        asyncio.create_task(process_queue(conversations[channel_id]))

@client.event
async def on_message(message):
    global global_message_lock

    async with global_message_lock:
        channel_id = message.channel.id
        if channel_id not in conversations:
            conversations[channel_id] = Conversation(channel_id, [], '', '')
            asyncio.create_task(process_queue(conversations[channel_id]))
        conversations[channel_id].enqueue_discord_message(message)


async def send_message_with_typing_indicator(current_conversation, discord_context, channel, inbound_message):
    channel_id = channel.id
    repository = Repository(channel_id)
    if current_conversation.requests_gpt_4():
        print("GPT-4")
        gpt_version = 4
    else:
        gpt_version = 3

    if gpt_version == 4:
        # Force a summarization, so if we haven't been summoned in awhile we don't submit 1000 tokens to gpt-4
        await repository.summarize_conversation(current_conversation, trigger_token_limit=300)
    # Construct a memory retreiver, arun it to get the requested memory, loop through the memory, if .SHORT_TERM_MEMORY for example then fill in get_active_memory()
    memory_retriever = MemoryRetriever()
    requested_memory = await memory_retriever.arun(current_conversation.get_formatted_conversation(True), DISCORD_NAME)
    active_memory = ''
    long_term_memory = ''
    search_results = ''

    chat_prompt_template = ChatPromptTemplate.from_messages(conversations[channel_id].get_conversation_prompts())
    for memory in requested_memory:
        print(memory)
        command, parameter = memory
        if command == MemoryRetriever.LONG_TERM_MEMORY:
            print("Long term memory: " + parameter)
            long_term_memory = current_conversation.get_long_term_memories(parameter)
        if command == MemoryRetriever.SUMMARIZED_MEMORY:
            print("Summarized memory")
            active_memory = current_conversation.active_memory
        if command == MemoryRetriever.WEB_SEARCH:
            print("Web search: " + parameter)
            web_searcher = WebSearcher()
            try:
                await channel.send("Searching the web for that one...")
            except:
                print("Failed to send web search message")
            search_results = "Web browsing results which may contain up to date information. Look closely to see if you can extract an answer to the most recent message:\n" + await web_searcher.run(parameter)
    chain = LLMChain(llm=get_chat_llm(gpt_version=gpt_version), prompt=chat_prompt_template)
    async def typing_indicator_wrapper():
        try:
            async with channel.typing():
                await asyncio.sleep(float('inf'))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print("Failed to indicate typing")

    typing_task = asyncio.create_task(typing_indicator_wrapper())
    try:
        await run_chain(inbound_message.channel, chain, discord_context, active_memory, long_term_memory, search_results, current_conversation.get_formatted_conversation(True))
    finally:
        typing_task.cancel()

client.run(discord_bot_key)
