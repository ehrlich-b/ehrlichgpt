from langchain.utilities import BingSearchAPIWrapper

search = BingSearchAPIWrapper(k=10) # type: ignore

print(search.run('How many episodes in picard season 3'))

