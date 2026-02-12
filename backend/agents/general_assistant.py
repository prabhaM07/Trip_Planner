import uuid
from travelstate import TravelState
from prompts import GENERAL_QUERY_PROMPT, build_general_assistant_context
from utils import collect_tool_results, invoke_model, is_greeting_via_llm
from langfuse.decorators import observe
from langchain_core.messages import ToolMessage, AIMessage


# Purpose:
# This agent answers general travel-related questions
# 
# Output:
# - Returns either a web search tool call or a final answer to the user’s question

@observe(name="general_query_agent")
def general_query_node(state: TravelState, llm) -> dict:

    messages = state.get("messages", [])
    user_query = state.get("user_query", "")
    is_fallback = state.get("needs_general_fallback", False)
    pdf_data = state.get("pdf_data", "")
    vector_created = state.get("vector_created", False)

    tool_results_block = collect_tool_results(messages)

    is_greeting = is_greeting_via_llm(llm, user_query)

    if is_greeting:
        response = invoke_model(
            model=llm,
            systemMessage=GENERAL_QUERY_PROMPT,
            humanMessage=user_query
        )

        return {
            "messages": [response],
            "general_assistant_called": True,
            "general_assistant_result": response.content,
            "needs_general_fallback": False,
            "last_active_agent": "general_assistant"
        }

    if messages and isinstance(messages[-1], ToolMessage):

        context = build_general_assistant_context(
            user_query=user_query,
            tool_results_block=tool_results_block,
            pdf_data=pdf_data if pdf_data or vector_created else ""
        )

        response = invoke_model(
            model=llm,
            systemMessage=GENERAL_QUERY_PROMPT,
            humanMessage=context
        )

        return {
            "messages": [response],
            "general_assistant_called": True,
            "general_assistant_result": response.content,
            "needs_general_fallback": False,
        }

    search_query = f"{user_query} travel information guide" if is_fallback else user_query

    tool_calls = [{
        "name": "web_search",
        "args": {"query": search_query},
        "id": f"call_{uuid.uuid4().hex[:8]}"
    }]

    response = AIMessage(content="", tool_calls=tool_calls)

    return {
        "messages": [response],
        "general_assistant_called": True,
        "needs_general_fallback": False,
        "last_active_agent": "general_assistant"
    }
