
from document_index import DocumentIndex

index = DocumentIndex(1234)
#index.add_message('Bob says hello, AI responds hi', 1234)
print(index.search_index('Bob says hello, AI responds hi'))
