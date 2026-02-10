import os
from langchain_core.tools import tool
from langchain_community.utilities import OpenWeatherMapAPIWrapper
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

import os
from langchain_core.tools import tool
from langchain_community.utilities import OpenWeatherMapAPIWrapper
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()


@tool
def get_weather(city: str) -> str:
    """
    Get current weather information for a city.

    Args:
        city: City name

    Returns:
        str: Weather info (temperature, conditions, humidity)
    """
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        return f"API key missing. Can't get weather for {city}."

    try:
        weather_api = OpenWeatherMapAPIWrapper(openweathermap_api_key=api_key)
        result = weather_api.run(city)
        return result
    except Exception as e:
        return f"Error fetching weather for {city}: {str(e)}"


@tool
def web_search(query: str) -> str:
    """
    Search the web and return results.

    Args:
        query: Search string

    Returns:
        str: Search results or AI answer
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Tavily API key missing. Please set TAVILY_API_KEY."

    try:
        client = TavilyClient(api_key=api_key)
        results = client.search(query=query, max_results=5, include_answer=True, search_depth="basic")


        if not results.get("results"):
            return f"No results found for: {query}"

        formatted = f"Search results for: {query}\n"
        for i, r in enumerate(results["results"][:5], 1):
            formatted += f"{i}. {r.get('title', 'No title')}\n"
            formatted += f"   {r.get('content', '')[:]}...\n"
        return formatted

    except Exception as e:
        return f"Web search error: {str(e)}"
