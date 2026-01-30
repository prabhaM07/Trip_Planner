from typing import List
from langchain_core.documents import Document
from langchain.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser

class ResponseGenerator:
    def __init__(self, llm):
        self.llm = llm
        self.parser = StrOutputParser()
        self.system_prompt = self._default_system_prompt()
    
    def _format_context(self, documents: List[Document]) -> str:
        return "\n\n".join(
            f"[Document {i+1}]\n{doc.page_content}" 
            for i, doc in enumerate(documents)
        )
    
    def _default_system_prompt(self) -> str:
        return """You are an intelligent assistant that helps users by providing information based on PDF content.

Your approach:
1. Read the provided PDF content carefully
2. Determine if the user's question can be meaningfully answered using the information in the PDF
3. If the PDF contains relevant information, use it to provide a helpful response
4. You may synthesize, organize, or present the information in a way that best answers the user's question
5. If the question has absolutely no connection to the PDF content, return: NO_ANSWER_FOUND
6. If the question seems connected but the PDF lacks the necessary information, return: NO_ANSWER_FOUND

Examples of when to answer:
- Direct questions about content in the PDF
- Requests to summarize, analyze, or organize information from the PDF
- Planning or recommendation requests when the PDF contains relevant details (places, schedules, options, etc.)
- Comparative questions when the PDF has the needed data

Examples of when to return NO_ANSWER_FOUND:
- Pure greetings with no actual question
- Questions about topics completely unrelated to the PDF content
- Requests for information that the PDF doesn't contain

Always base your response on the PDF content. Be helpful and comprehensive when the information is available."""

    def generate(self, query: str, retrieved_docs: List[Document]) -> str:
        if not retrieved_docs:
            return "NO_ANSWER_FOUND"
        
        context = self._format_context(retrieved_docs)
        
        user_prompt = f"""PDF CONTENT:
{context}

USER QUESTION: {query}

Analyze whether this question can be answered using the PDF content. If yes, provide a comprehensive answer based on the information available. If the question is unrelated or the PDF lacks necessary information, respond with: NO_ANSWER_FOUND

RESPONSE:"""
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_prompt),
        ]
        
        response = self.llm.invoke(messages)
        answer = self.parser.invoke(response).strip()
        
        return answer