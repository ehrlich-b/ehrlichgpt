import random
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain

class Utils:
    def escape_prompt_content(content):
        return content.replace('{', '{{').replace('}', '}}')

    async def scold():
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
