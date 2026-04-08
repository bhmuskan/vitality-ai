import streamlit as st
from groq import Groq
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os


class ChatAgent:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        # Attempt Initialize Embeddings with Fallback
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            self.use_fallback_retriever = False
        except Exception as e:
            # Fallback to simple keyword search if heavy dependencies fail (Keras/Torch)
            print(f"Warning: Falling back to simple retriever: {str(e)}")
            self.embeddings = None
            self.use_fallback_retriever = True

        # Safe Groq API key retrieval
        import os
        try:
            try:
                groq_api_key = st.secrets["GROQ_API_KEY"]
            except Exception:
                groq_api_key = os.getenv("GROQ_API_KEY", "")

            if not groq_api_key:
                st.error("Groq API key not found in secrets or environment.")
                st.stop()
                
            self.client = Groq(api_key=groq_api_key)
        except Exception as e:
            st.error(f"Failed to initialize Chat Agent: {str(e)}")
            st.stop()
            
        self.model_name = "llama-3.3-70b-versatile"

    def initialize_vector_store(self, text_content):
        """Create vector store from text content."""
        if not text_content or text_content.strip() == "":
            text_content = "No report context available."

        texts = self.text_splitter.split_text(text_content)
        if not texts:
            texts = [text_content]

        if not self.use_fallback_retriever:
            try:
                from langchain_community.vectorstores import FAISS
                vectorstore = FAISS.from_texts(texts, self.embeddings)
                return {"type": "faiss", "store": vectorstore, "texts": texts}
            except Exception:
                # If FAISS creation fails at runtime, swap to fallback
                self.use_fallback_retriever = True
        
        # Simple fallback store (list of text chunks)
        return {"type": "simple", "store": None, "texts": texts}

    def _format_chat_history(self, chat_history):
        """Format chat history for Groq API."""
        messages = []
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        return messages

    def _contextualize_query(self, query, chat_history):
        """Reformulate query considering chat history."""
        if not chat_history:
            return query

        # Build context from recent chat history
        recent_history = chat_history[-4:]  # Last 2 exchanges
        history_text = "\n".join(
            [
                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                for msg in recent_history
            ]
        )

        contextualize_prompt = f"""Given a chat history and the latest user question, formulate a standalone question which can be understood without the chat history. Do NOT answer the question, just reformulate it if needed and otherwise return it as is.

Chat History:
{history_text}

Latest User Question: {query}

Standalone Question:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You reformulate questions to be standalone.",
                    },
                    {"role": "user", "content": contextualize_prompt},
                ],
                temperature=0.1,
                max_tokens=200,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return query  # Fallback to original query

    def get_response(self, query, vectorstore_obj, chat_history=None):
        """Get response using RAG."""
        if chat_history is None:
            chat_history = []

        # 1. Contextualize query based on chat history
        contextualized_query = self._contextualize_query(query, chat_history)

        # 2. Retrieve relevant documents
        try:
            if vectorstore_obj["type"] == "faiss":
                retriever = vectorstore_obj["store"].as_retriever(search_kwargs={"k": 3})
                docs = retriever.invoke(contextualized_query)
                context = "\n\n".join([doc.page_content for doc in docs])
            else:
                # Simple keyword matching fallback
                texts = vectorstore_obj["texts"]
                query_words = set(contextualized_query.lower().split())
                
                # Rank chunks by overlap
                scored_texts = []
                for t in texts:
                    count = 0
                    for word in query_words:
                        if len(word) > 2 and word in t.lower():
                            count += 1
                    scored_texts.append((count, t))
                
                scored_texts.sort(key=lambda x: x[0], reverse=True)
                context = "\n\n".join([t[1] for t in scored_texts[:2]]) # Get top 2
            
            # If context is just placeholder text, set to empty
            if context.strip() == "No report context available.":
                context = ""
        except Exception:
            # If retrieval fails, proceed without context
            context = ""

        # 3. Build prompt with context and chat history
        qa_system_prompt = (
            "You are an assistant for medical question-answering tasks. "
            "Use the following pieces of retrieved context from a patient report to answer the question. "
            "If the answer isn't in the context, but is general health knowledge, you can provide a balanced view while noting the report lacks specific data. "
            "If you don't know the answer, just say that you don't know and suggest consulting a doctor. "
            "Keep the answer concise and professional."
        )

        # Format messages for Groq API
        messages = [{"role": "system", "content": qa_system_prompt}]

        # Add chat history
        if chat_history:
            formatted_history = self._format_chat_history(
                chat_history[-6:]
            )  # Last 3 exchanges
            messages.extend(formatted_history)

        # Add context and current query
        if (
            context
            and context.strip()
            and context.strip() != "No report context available."
        ):
            user_message = f"Context from report:\n{context}\n\nQuestion: {query}"
        else:
            # No report context available, rely on chat history only
            user_message = f"Question: {query}\n\nNote: No specific context from the current report was found for this query. Answer based on general medical knowledge or previous history if applicable."
        messages.append({"role": "user", "content": user_message})

        # 4. Get response from Groq
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=600,
            )
            return response.choices[0].message.content
        except Exception as e:
            error_message = str(e).lower()
            if any(msg in error_message for msg in ["connection", "unreachable", "timeout", "resolution", "dns"]):
                return "Note: I'm currently in Offline/Demo mode because I couldn't reach my medical discovery brain. Generally, I can assist with clinical report interpretation and wellness guidance. Please check your connection to resume full functionality."
            return f"Error generating response: {str(e)}"
