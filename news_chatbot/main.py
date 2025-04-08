import pandas as pd
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain.llms import HuggingFaceHub
from langchain.chains import RetrievalQA
import gradio as gr
# Define the path for the ChromaDB directory
persist_dir = "./news_chroma_db"

try:
    # Load the dataset
    df = pd.read_csv("english_news_dataset.csv", encoding="latin-1",on_bad_lines='skip')
    TEXT_COLUMN = "Content"
    df = df.dropna(subset=[TEXT_COLUMN])
    texts = df[TEXT_COLUMN].tolist()

    # Initialize text splitter
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.create_documents(texts)

    # Initialize embeddings
    embedding_model_name = "sentence-transformers/all-mpnet-base-v2"
    embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name)

    # Check for existence of essential ChromaDB files before loading
    expected_files = ["index/id_to_uuid.pkl", "index/uuid_to_id.pkl", "index/chroma-embeddings.parquet", "index/chroma-metadata.parquet", "chroma.sqlite3"]
    all_files_present = all(os.path.exists(os.path.join(persist_dir, f)) for f in expected_files)

    # Load or create the vector database
    if os.path.exists(persist_dir) and os.listdir(persist_dir) and all_files_present:
        try:
            vectordb = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
            print(f"Loaded existing vector db with {vectordb._collection.count()} documents")
        except Exception as load_error:
            print(f"Error loading existing ChromaDB: {load_error}")
            print("Creating a new vector database...")
            vectordb = Chroma.from_documents(
                documents=docs,
                embedding=embeddings,
                persist_directory=persist_dir
            )
            vectordb.persist()
            print(f"Created and persisted new vector db with {vectordb._collection.count()} documents")
    else:
        print("Creating a new vector database...")
        vectordb = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            persist_directory=persist_dir
        )
        vectordb.persist()
        print(f"Created and persisted new vector db with {vectordb._collection.count()} documents")

    # Initialize Hugging Face Hub LLM
    HUGGINGFACEHUB_API_TOKEN = ""
    llm_model_name = "google/flan-t5-xxl"
    llm = HuggingFaceHub(repo_id=llm_model_name, model_kwargs={"temperature": 0.5, "max_length": 512}, huggingfacehub_api_token=HUGGINGFACEHUB_API_TOKEN, task="text-generation")

    # Set up the RetrievalQA chain
    retriever = vectordb.as_retriever(search_kwargs={"k": 2})
    qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever)

    # Interactive query loop
    def chat_with(query):
        if query.lower()=="exit":
            return "Chat Ended"
        result=qa.run(query)
        return f"Chatbor :{result}"
    interface=gr.Interface(
        fn=chat_with,
        inputs=gr.Textbox(lines=2,placeholder="Enter your question here..."),
        outputs=gr.Textbox(),
        title="News Chatbot",
        description="Ask questions about the news articles and type 'exit' to end the chat.",
        theme="default"
    )
    interface.launch()
except Exception as e:
    print(f"An error occurred: {e}")