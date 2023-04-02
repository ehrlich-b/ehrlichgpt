from builtins import str
import asyncio
import re
from typing import Callable, List, Tuple
from langchain.llms.base import BaseLLM
from langchain.agents import initialize_agent, Tool
from langchain.tools import BaseTool
from langchain.chat_models import ChatOpenAI
from langchain import LLMChain, LLMMathChain, SerpAPIWrapper
from langchain.agents import load_tools
from langchain.prompts import PromptTemplate
from langchain.schema import (HumanMessage, AIMessage)


class MemoryRetriever:
    SHORT_TERM_MEMORY = "ShortTermMemory"
    SUMMARIZED_MEMORY = "SummarizedMemory"
    LONG_TERM_MEMORY = "LongTermMemory"
    TEMPLATE = """You are an information retrieval bot, you are given a discord chat message, and a set of tools. It is your job to select the proper information collection tools to respond to the message.

Tools format:
Tool['parameter']: Tool description (tools can be called multiple times with different parameters, 0-1 parameter per call)

Tools:
ShortTermMemory[]: Recent full text chat messages
SummarizedMemory[]: Summarized short term memory, contains significantly more messages than fully inflated ShortTermMemory
LongTermMemory["embedding_query"]: Long term memory, parameter is the query to use, this will generate a query embedding and search for similar messages from chat history
Answer[]: You've collected all the data you need, and are ready to forward on to the answer synthesizer bot

Example 1:
bob#1234: Do you think you can help me with that?
Thought: This message is a continuation of a previous conversation, we need recent chat history
Tools:
ShortTermMemory[]
SummarizedMemory[]
Answer[]

Example 2:
bob#1234: What is the capital of France?
Thought: No additional information is needed
Tools:
Answer[]

Example 3:
bob#1234: Do you remember when we talked about my dogs? Do you remember their names?
Thought: This message is asking for information about bob#1234, and information that may be in any of the chat histories, and that information may be in the user file
Tools:
ShortTermMemory[]
SummarizedMemory[]
LongTermMemory["bob#1423's dogs"]
Answer[]

Your turn!
{message}"""

    def __init__(self) -> None:
        llm = ChatOpenAI(temperature=0.0) # type: ignore

        prompt = PromptTemplate(
            template=self.TEMPLATE,
            input_variables=["message"],
        )

        self.chain = LLMChain(llm=llm, prompt=prompt)

    def _parse_tools(self, output: str) -> List[Tuple[str, str]]:
        try:
            tools_section = re.search(r'Tools:\n(.*?)\nAnswer\[\]', output, re.DOTALL)
            if tools_section:
                tools = tools_section.group(1).strip().split('\n')
                parsed_tools = []
                for tool in tools:
                    tool_name, param = tool.strip().split('[')
                    param = param[:-1]
                    parsed_tools.append((tool_name, param.strip('"')))
                return parsed_tools
        except:
            pass
        finally:
            return []

    def run(self, message: str) -> List[Tuple[str, str]]:
        output = self.chain.run(message=message)
        return self._parse_tools(output)

    async def arun(self, message: str) -> List[Tuple[str, str]]:
        output = await self.chain.arun(message=message)
        return self._parse_tools(output)
