import pandas as pd
import os
from langchain.embeddings import SentenceTransformerEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.vectorstores import Chroma
from langchain.llms import OpenAI 
from langchain.chains import RetrievalQA 

persist_dir="./chroma_db"
embedding_model_name="all-MiniLM-L6-v2"
openai_model_name="gpt-3.5-turbo"
os.environ["OPENAI_API_KEY"]="YOUR_OPENAI_API_KEY"
try:
    df=pd.read_csv("alldata_1_for_kaggle.csv",encoding="latin-1")
    df['text']=df['a']
    df=df[['text']]
    texts=df['text'].tolist()
    metadatas=df.to_dict('records')
    print(f"Loaded {len(texts)} documents")

    embedding_func=SentenceTransformerEmbeddings(model_name=embedding_model_name)
    if os.path.exists(persist_dir):
        vectordb=Chroma(persist_directory=persist_dir, embedding_function=embedding_func)
        print(f"Loaded existing vector db with {len(vectordb)} documents")
    else:
        vectordb=Chroma.from_texts(
            texts=texts,
            embedding=embedding_func,
            metadatas=metadatas,
            persist_directory=persist_dir,
        )
        vectordb.persist()
        print(f"Vector db persisted")
    llm=ChatOpenAI(model_name=openai_model_name)
    print("Model initialized")
    retriever=vectordb.as_retriever(search_kwargs={"k":2})
    qa_chain=RetrievalQA.from_llm(
        llm=llm,
        retriever=retriever
    )
    print("RetrievalQA chain created")
    while True:
        ui=input('Enter your query:')
        if ui.lower()=='exit':
            print("Exiting the chatbot")
            break
        result=qa_chain({"query":ui})
        print('Chatbot : ',result['result'])
    
except FileNotFoundError as e1:
    print(e1)
except ImportError as e2:
    print(e2)
except Exception as e:
    print(e)