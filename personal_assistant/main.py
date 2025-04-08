# First install required packages:
# pip install llama-index langchain openai chromadb python-dotenv tiktoken

# Set up environment

# ----------------------
# 1. Data Preparation & Indexing
# ----------------------
#
import os
import json
import gradio as gr
from langchain.chains import RetrievalQA
from langchain_openai import OpenAIEmbeddings, OpenAI
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from langchain_chroma import Chroma
from langchain.memory import ConversationBufferMemory

# Set up environment
os.environ["OPENAI_API_KEY"] = ''

# ----------------------
# 1. Data Preparation & Indexing
# ----------------------
class KnowledgeBaseManager:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.vector_store = None
        self.index = None
        
    def load_documents(self):
        return SimpleDirectoryReader(self.data_dir).load_data()
    
    def setup_vector_store(self):
        embeddings = OpenAIEmbeddings()
        documents = self.load_documents()
        
        self.vector_store = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory="./chroma_db",
            collection_name="knowledge_base"
        )
        return self.vector_store


# ----------------------
# 2. User Profile Management
# ----------------------
class UserProfileManager:
    def __init__(self):
        self.profiles = {}
        
    def create_profile(self, user_id):
        self.profiles[user_id] = {
            "learning_style": "visual",  # visual/auditory/kinesthetic
            "difficulty_level": "intermediate",
            "preferred_topics": [],
            "learning_history": []
        }
        return self.profiles[user_id]
    
    def update_preferences(self, user_id, preferences):
        if user_id in self.profiles:
            self.profiles[user_id].update(preferences)
        return self.profiles[user_id]

# ----------------------
# 3. Learning Assistant Core
# ----------------------
class LearningAssistant:
    def __init__(self):
        self.knowledge_base = KnowledgeBaseManager()
        self.user_manager = UserProfileManager()
        self.vector_store = self.knowledge_base.setup_vector_store()
        
        # Initialize LangChain components
        self.memory = ConversationBufferMemory()
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=OpenAI(temperature=0.7),
            chain_type="stuff",
            retriever=self.vector_store.as_retriever(),
            memory=self.memory,
            return_source_documents=True
        )
    
    def personalize_prompt(self, user_id, question):
        profile = self.user_manager.profiles.get(user_id, {})
        style = profile.get("learning_style", "general")
        level = profile.get("difficulty_level", "intermediate")
        
        return f"""Adapt this response for a {style} learner at {level} level.
        Use examples and analogies appropriate for this style.
        Question: {question}
        Answer:"""
    
    def ask_question(self, user_id, question):
        personalized_prompt = self.personalize_prompt(user_id, question)
        result = self.qa_chain.invoke({"query": personalized_prompt})
        
        # Update user history
        self.user_manager.profiles[user_id]["learning_history"].append({
            "question": question,
            "response": result["result"]
        })
        
        return result["result"]

# ----------------------
# 4. Gradio Interface (Updated)
# ----------------------
def main():
    assistant = LearningAssistant()
    user_id = "sample_user"
    
    # Initialize default profile
    assistant.user_manager.create_profile(user_id)
    
    def chat(message, history):
        response = assistant.ask_question(user_id, message)
        return response

    def update_profile(learning_style, difficulty, topics):
        assistant.user_manager.update_preferences(user_id, {
            "learning_style": learning_style,
            "difficulty_level": difficulty,
            "preferred_topics": [t.strip() for t in topics.split(",")]
        })
        return "Profile updated successfully!"

    with gr.Blocks(theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🧠 Personalized Learning Assistant")
        
        with gr.Row():
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(height=500)
                msg = gr.Textbox(label="Your Question")
                clear = gr.Button("Clear History")
            
            with gr.Column(scale=1):
                gr.Markdown("## Profile Settings")
                learning_style = gr.Dropdown(
                    choices=["visual", "auditory", "kinesthetic"],
                    value="visual",
                    label="Learning Style"
                )
                difficulty = gr.Dropdown(
                    choices=["beginner", "intermediate", "advanced"],
                    value="intermediate",
                    label="Difficulty Level"
                )
                topics = gr.Textbox(
                    label="Preferred Topics (comma-separated)",
                    value="machine learning, neural networks"
                )
                update_btn = gr.Button("Update Profile")
                status = gr.Textbox(label="Update Status")

        msg.submit(chat, [msg, chatbot], [msg, chatbot])
        clear.click(lambda: None, None, chatbot, queue=False)
        update_btn.click(update_profile, 
                        [learning_style, difficulty, topics], 
                        status)

    demo.launch()

if __name__ == "__main__":
    main()