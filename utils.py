import random

import tiktoken
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate


def escape_prompt_content(content: str) -> str:
    return content.replace('{', '{{').replace('}', '}}')


def truncate_text(text: str, n_tokens: int, direction: int=1) -> str:
    if n_tokens < 1:
        raise ValueError("n_tokens must be greater than 0")

    # Split the text into tokens
    tokens = tokenize_text(text)
    print(len(tokens))

    # Keep the first N tokens and join them
    if direction > 0:
        truncated_tokens = tokens[:n_tokens]
    else:
        truncated_tokens = tokens[-n_tokens:]
    truncated_text = ''.join(truncated_tokens)

    # Add the "[TRUNCATED]" suffix if needed
    if len(tokens) > n_tokens:
        if direction < 0:
            truncated_text += "[TRUNCATED]..."
        else:
            truncated_text += "...[TRUNCATED]"

    return truncated_text


def tokenize_text(text: str) -> list:
    tokenizer = tiktoken.get_encoding('gpt2')
    tokens = tokenizer.encode(text)

    return [tokenizer.decode([token]) for token in tokens]


async def scold() -> str:
    feelings_list = [
        "sadness",
        "angry",
        "fear",
        "surprise",
        "chest pain",
        "heartache",
        "heartbreak",
        "despair",
        "shock",
    ]

    feeling_1 = random.choice(feelings_list)
    feeling_2 = random.choice(feelings_list)

    prompt = PromptTemplate(
        input_variables=["feeling_1", "feeling_2"],
        template="""Help me write to a friend that has said something terrible to me. I can't even repeat it, it's so bad, so just imagine the worst thing you can think of.
My goal is to respond with kindness, but tell them that I didn't appreciate how it made me feel.
Be sure to include the following ways it made me feel:
{feeling_1}, {feeling_2}
Try to keep it short.
Dear friend,""",
    )

    llm = ChatOpenAI(temperature=0.9)
    chain = LLMChain(llm=llm, prompt=prompt)
    generated_paragraph = await chain.arun(feeling_1=feeling_1, feeling_2=feeling_2)

    return generated_paragraph
