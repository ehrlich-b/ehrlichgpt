from typing import cast
from langchain.llms.base import BaseLLM
from langchain.agents import initialize_agent, Tool
from langchain.tools import BaseTool
from langchain.chat_models import ChatOpenAI
from langchain import LLMChain, LLMMathChain, SerpAPIWrapper
from langchain.agents import load_tools
from langchain.prompts import PromptTemplate
from langchain.schema import (HumanMessage, AIMessage)

llm = ChatOpenAI(temperature=0.0) # type: ignore

template="""You are an information retrieval bot, you are given a discord chat message, and a set of tools. It is your job to select the proper information collection tools to respond to the message.

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
{message}
"""

# Make a basic hello world prompt
prompt = PromptTemplate(
    template=template,
    input_variables=["message"],
)

chain = LLMChain(llm=llm, prompt=prompt)
print (chain.run(message="adotout#1452: Ok, given everything that's been said, what do you think is the most logical conclusion?"))
