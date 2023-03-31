import asyncio
import os
import pprint
import random
import time

import discord
from discord import DMChannel, TextChannel
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate

from conversation import Conversation
from message import Message
from repository import Repository
from utils import format_discord_mentions, scold, truncate_text

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
        long_term_memory=long_term_memory,
    )

    response = clean_up_response(DISCORD_NAME, response)
    await channel.send(response)

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

conversations = {}

os.makedirs("conversations", exist_ok=True)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    for db_file in os.listdir("conversations"):
        if db_file == ".gitignore":
            continue
        channel_db = os.path.splitext(db_file)[0]
        channel_id = int(channel_db.split('.')[0])
        conversations[channel_id] = load_conversation(channel_id)

@client.event
async def on_message(message):
    global paused, conversations
    pprint.pprint(message)
    channel_id = message.channel.id
    repository = Repository(channel_id)
    formatted_sender = message.author.name + "#" + message.author.discriminator
    at_mentioned = False
    if client.user in message.mentions:
        at_mentioned = True
    if DISCORD_NAME.lower() in message.content.lower():
        at_mentioned = True
    if "<@" + str(client.user.id) + ">" in message.content:
        at_mentioned = True

    if isinstance(message.channel, DMChannel):
        context = "Direct Message"
        at_mentioned = True
    elif isinstance(message.channel, TextChannel):
        context = "Group Room with " + str(len(message.channel.members)) + " members"
    else:
        context = "Unknown"

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

    formatted_content = format_discord_mentions(message)
    current_conversation = conversations[channel_id]
    if message.author == client.user:
        # Add our own AI message to conversation
        truncated_content = truncate_text(formatted_content, 100)
        current_conversation.add_message(Message("ai", truncated_content, int(time.time())))
        repository.save_message("ai", truncated_content)
        async with current_conversation.lock:
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

        if not current_conversation.lock.locked():
            async with current_conversation.lock:
                if at_mentioned:
                    await send_message_with_typing_indicator(current_conversation, context, message.channel, message, formatted_content)
                else:
                    # Nobody is talking to us, summarize larger chunks so we're not constantly churning through summarization
                    await repository.summarize_conversation(current_conversation, trigger_token_limit=500)


async def send_message_with_typing_indicator(current_conversation, discord_context, channel, inbound_message, formatted_content):
    channel_id = channel.id
    repository = Repository(channel_id)
    while True:
        if current_conversation.requests_gpt_4():
            print("GPT-4")
            gpt_version = 4
        else:
            gpt_version = 3
        chat_prompt_template = ChatPromptTemplate.from_messages(conversations[channel_id].get_conversation_prompts())
        chain = LLMChain(llm=get_chat_llm(gpt_version=gpt_version), prompt=chat_prompt_template)
        if gpt_version == 4:
            # Force a summarization, so if we haven't been summoned in awhile we don't submit 1000 tokens to gpt-4
            await repository.summarize_conversation(current_conversation, trigger_token_limit=300)
        async with inbound_message.channel.typing():
            await run_chain(inbound_message.channel, chain, discord_context, current_conversation.get_active_memory(), current_conversation.get_long_term_memories(formatted_content))

        if not current_conversation.sync_busy_history():
            break

client.run(discord_bot_key)
