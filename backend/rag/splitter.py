from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

def split_documents(documents: list[Document]) -> list[Document]:
    # Since each attraction document is small (under 800 characters),
    # we can use a chunk size of 1200 to keep each attraction as a single document.
    splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=0)
    return splitter.split_documents(documents)
