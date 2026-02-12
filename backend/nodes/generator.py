from travelstate import TravelState
from RAG.generator import ResponseGenerator
from langfuse.decorators import observe

# Purpose:
# This node generates the final answer using the user's query and thedocument chunks retrieved from the vector store.
# 
# Inputs:
# - user_query       : The original query asked by the user
# - retrieved_docs   : Relevant document chunks retrieved by the retriever agent
#
# Model Used:
# - LLM: ChatGroq
# - Model: "llama-3.3-70b-versatile"
# - Temperature: 0.2
# - Max Tokens: 1000


@observe(name="generator_node")
def generator_node(state: TravelState, llm):
    user_query = state.get("user_query", "").strip()
    retrieved_docs = state.get("retrieved_docs", [])

    generator = ResponseGenerator(llm)
    answer = generator.generate(user_query, retrieved_docs)

    is_no_answer = not answer or answer == "NO_ANSWER_FOUND"
    
    # Fallback if:
    # 1. No docs retrieved
    # 2. Answer is NO_ANSWER_FOUND
    # 3. Answer is empty
    needs_fallback = (
        not retrieved_docs or 
        len(retrieved_docs) == 0 or 
        is_no_answer
    )

    response = "" if is_no_answer else answer

    return {
        "research_agent_called": True,
        "needs_general_fallback": needs_fallback,
        "pdf_data": response,
        "messages": [response],
    }
