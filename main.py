from pathlib import Path
import markdown  # Used to convert markdown documents to plain text.
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import GPT4AllEmbeddings
import subprocess
import json

# Setting up variables for the script.
local_path = "/home/Toma5OD/dev/test_files_for_rag2"

# Defines a simple document structure to hold content and optional metadata.
class SimpleDocument:
    def __init__(self, content, metadata=None):
        self.page_content = content
        self.metadata = metadata if metadata is not None else {}

class CustomChromaRetriever:
    def __init__(self, vectorstore, search_type="similarity", search_kwargs=None):
        self.vectorstore = vectorstore
        self.search_type = search_type  # Store the search type
        self.search_kwargs = search_kwargs if search_kwargs is not None else {}

    def get_relevant_documents(self, query, limit=10):
        # Include 'search_type' as a positional argument
        search_kwargs = {"k": limit, **self.search_kwargs}
        return self.vectorstore.search(query, self.search_type, **search_kwargs)

# Document loading and processing. Reads all markdown files from a directory.
docs = []
repo_path = Path(local_path)
for index, md_file in enumerate(repo_path.glob('**/*.md'), start=1):
    with open(md_file, 'r', encoding='utf-8') as file:
        text = file.read()
        plain_text = markdown.markdown(text)
        docs.append(plain_text)
        # print(f"{index}: plain_text: {plain_text}")

# Creates document objects from the text of each document.
doc_objects = [SimpleDocument(text, {}) for text in docs]

# Splits documents into chunks suitable for processing, based on character count.
text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(chunk_size=500, chunk_overlap=100)
all_splits = text_splitter.split_documents(doc_objects)

# Embeds documents using a specified model and indexes them for retrieval.
embedding = GPT4AllEmbeddings()
vectorstore = Chroma.from_documents(documents=all_splits, collection_name="rag-chroma", embedding=embedding)

# Interactively asks the user for a query.
search_term = input("Please enter your question: ")

# Instantiate your custom retriever with the desired search type (if different from "similarity").
retriever = CustomChromaRetriever(vectorstore, search_type="similarity")

# Retrieve documents as before.
results = retriever.get_relevant_documents(search_term, limit=20)

# Defines a function to generate answers using a local language model.
def generate_answer_with_ollama(context, question):
    prompt = f"Question: '{question}'. Context required to answer the question: '{context}'"

    # uncomment to see the prompt
    # print(f"Prompt: {prompt}")

    command = ["ollama", "run", "mistral", prompt, "--format", "json"]
    process = subprocess.run(command, capture_output=True, text=True)
    response = process.stdout

    # uncomment to see the context
    # print(f"THIS IS THE CONTEXT:\n {context}")

    try:
        answer_data = json.loads(response)
        answer = answer_data.get("answer", next(iter(answer_data.values()), "No answer found."))
    except (json.JSONDecodeError, StopIteration):
        answer = "Failed to decode the response or response format unexpected."
    return answer

# Prepares the context from retrieved documents and generates an answer.
context = "\n\n".join([doc.page_content for doc in results])
answer = generate_answer_with_ollama(context, search_term)

# Displays the generated answer to the user's query.
print(f"Question: {search_term}\nAnswer: {answer}")
