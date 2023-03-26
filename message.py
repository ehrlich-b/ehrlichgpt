
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
)
from utils import Utils

class Message:
    def __init__(self, sender, content):
        self.sender = sender
        self.content = content

    def get_prompt_template(self):
        if self.sender == "ai":
            message_prompt = AIMessagePromptTemplate(
                prompt=PromptTemplate(
                    template=Utils.escape_prompt_content(self.content),
                    input_variables=[],
                )
            )
        else:  # sender == "ai"
            message_prompt = HumanMessagePromptTemplate(
                prompt=PromptTemplate(
                    template=Utils.escape_prompt_content(self.sender + ": " + self.content),
                    input_variables=[],
                )
            )

        return message_prompt

