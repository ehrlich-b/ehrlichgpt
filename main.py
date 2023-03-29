import discord
import os
import pprint
import random
import sqlite3
import asyncio

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
)
from discord import (DMChannel, TextChannel)
from conversation import Conversation
from repository import Repository
from message import Message
from utils import Utils

DISCORD_NAME = 'EhrlichGPT'

def clean_up_response(discord_name, original_response):
    if original_response.startswith(discord_name + ":"):
        original_response = original_response[len(discord_name + ":"):]
    elif original_response.startswith("AI:"):
        original_response = original_response[len("AI:"):]
    return original_response.strip()

async def run_chain(channel, chain, discord_context, conversation_context, long_term_memory):
    response = await chain.arun(
        discord_name=DISCORD_NAME,
        discord_context=discord_context,
        conversation_context=conversation_context,
        long_term_memory='',
    )

    response = clean_up_response(DISCORD_NAME, response)
    await channel.send(response)

async def delayed_typing_indicator(channel, delay=2):
    await asyncio.sleep(delay)
    async with channel.typing():
        await asyncio.sleep(float('inf'))

def get_chat_llm(temperature=0.9, max_tokens=500, gpt_version=3):
    if gpt_version == 4:
        chat_llm = ChatOpenAI(temperature=temperature, max_tokens=max_tokens, model='gpt-4')
    else:
        chat_llm = ChatOpenAI(temperature=temperature, max_tokens=max_tokens)
    return chat_llm

discord_bot_key = os.environ['DISCORD_BOT_TOKEN']
intents = discord.Intents.default()
intents.message_content = True
paused = False

# TODO: Make this configurable
admin = 'adotout#7295'

client = discord.Client(intents=intents)

conversations = {}
chat = ChatOpenAI(temperature=0.9, max_tokens=500)

os.makedirs("conversations", exist_ok=True)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    for db_file in os.listdir("conversations"):
        if db_file == ".gitignore":
            continue
        channel_db = os.path.splitext(db_file)[0]
        channel_id = int(channel_db.split('.')[0])
        db_path = Repository.get_db_path(channel_id)
        Repository.create_db_if_not_exists(db_path)
        conversations[channel_id] = Repository.load_conversation(channel_id, db_path)

@client.event
async def on_message(message):
    global paused, conversations
    pprint.pprint(message)
    channel_id = message.channel.id
    db_path = Repository.get_db_path(channel_id)
    Repository.create_db_if_not_exists(db_path)
    formatted_sender = message.author.name + "#" + message.author.discriminator
    at_mentioned = False
    if client.user in message.mentions:
        at_mentioned = True
    if DISCORD_NAME.lower() in message.content.lower():
        at_mentioned = True
    if "<@" + str(client.user.id) + ">" in message.content:
        at_mentioned = True

    is_group_chat = False
    if isinstance(message.channel, DMChannel):
        context = "Direct Message"
        at_mentioned = True
    elif isinstance(message.channel, TextChannel):
        context = "Group Room with " + str(len(message.channel.members)) + " members"
        is_group_chat = True
    else:
        context = "Unknown"
        is_group_chat = True

    if paused:
        if at_mentioned and not message.author == client.user:
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

    if channel_id not in conversations:
        conversations[channel_id] = Conversation(channel_id, [], '', '')

    current_conversation = conversations[channel_id]
    if message.author == client.user:
        # Add our own AI message to conversation
        truncated_content = Utils.truncate_text(message.content, 100)
        current_conversation.add_message(Message("ai", truncated_content))
        Repository.save_message(db_path, "ai", truncated_content)
        async with current_conversation.lock:
            # We're responding, so we're being talked to, we don't want to constantly summarize, but we also
            # don't want to re-submit huge history in prompts, so 500? Idk
            await Repository.summarize_conversation(current_conversation, trigger_token_limit=500)
        return
    else:
        violates_rules = Message.violates_content_policy(message.content)
        if violates_rules:
            censored_content = Message.CENSORED
            if at_mentioned:
                scold = "You there! " + formatted_sender + "! Halt! It's the thought police! 👮‍♂️\n\n"
                scold += "You've been convicted of " + str(random.randint(2, 10)) + " counts of thought crime.\n\n"
                scold += "I've prepared this statement as punishment:\n"
                scold += await Utils.scold()
                await message.channel.send(scold)
                at_mentioned = False
        else:
            censored_content = message.content

        requested_gpt_version = 3
        if at_mentioned and 'think hard' in censored_content.lower():
            requested_gpt_version = 4
        current_conversation.add_message(Message(formatted_sender, censored_content, requested_gpt_version, at_mentioned))
        Repository.save_message(db_path, formatted_sender, censored_content)

        context += " your alias <@" + str(client.user.id) + ">"

        if not current_conversation.lock.locked():
            async with current_conversation.lock:
                if at_mentioned:
                    await send_message_with_typing_indicator(current_conversation, context, message.channel, message)
                else:
                    # Nobody is talking to us, summarize larger chunks so we're not constantly churning through summarization
                    await Repository.summarize_conversation(current_conversation, trigger_token_limit=1000)


async def send_message_with_typing_indicator(current_conversation, discord_context, channel, message):
    channel_id = channel.id
    while True:
        if current_conversation.requests_gpt_4():
            print("GPT-4")
            gpt_version = 4
        else:
            gpt_version = 3
        chat_prompt_template = ChatPromptTemplate.from_messages(conversations[channel_id].get_conversation_prompts())
        chain = LLMChain(llm=get_chat_llm(gpt_version=gpt_version), prompt=chat_prompt_template)
        typing_indicator_task = asyncio.create_task(delayed_typing_indicator(message.channel))
        if gpt_version == 4:
            # Force a summarization, so if we haven't been summoned in awhile we don't submit 1000 tokens to gpt-4
            await Repository.summarize_conversation(current_conversation, trigger_token_limit=300)
        chain_run_task = asyncio.create_task(run_chain(message.channel, chain, discord_context, current_conversation.get_active_memory(), None))
        await asyncio.wait([typing_indicator_task, chain_run_task], return_when=asyncio.FIRST_COMPLETED)
        typing_indicator_task.cancel()
        if not current_conversation.sync_busy_history():
            break

client.run(discord_bot_key)
