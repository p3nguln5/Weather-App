import requests
import json
import logging
from functools import lru_cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('weather_service')

# Create a session with retry capability
def create_session():
    """Create a requests session with retry capability"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# Create a global session
session = create_session()

def handle_request_error(location, error, error_type="Error"):
    """Handle and log request errors"""
    logger.error(f"{error_type} fetching weather data for {location}: {error}")
    return None

def get_weather_data(api_key, location, days=3):
    """
    Retrieves comprehensive weather data for a given location.

    Args:
        api_key (str): Your WeatherAPI.com API key.
        location (str): The location query (city name, zip code, latitude/longitude, IP address, etc.)
        days (int): Number of forecast days to retrieve (default: 3)

    Returns:
        dict: A dictionary containing the weather data, or None if an error occurs.
    """
    url = f"http://api.weatherapi.com/v1/forecast.json"
    params = {
        "key": api_key,
        "q": location,
        "alerts": "yes",
        "aqi": "yes",
        "days": days,
        "marine": "yes"
    }
    
    logger.info(f"Fetching weather data for location: {location}")
    
    try:
        response = session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully retrieved weather data for {location}")
        return data

    except requests.exceptions.Timeout:
        return handle_request_error(location, "Timeout error", "Timeout")
    except requests.exceptions.ConnectionError:
        return handle_request_error(location, "Connection error", "Connection error")
    except requests.exceptions.HTTPError as e:
        return handle_request_error(location, e, "HTTP error")
    except requests.exceptions.RequestException as e:
        return handle_request_error(location, e)
    except json.JSONDecodeError as e:
        return handle_request_error(location, e, "JSON decode error")
    except Exception as e:
        return handle_request_error(location, e, "Unexpected error")

@lru_cache(maxsize=32)
def search_locations(api_key, query):
    """
    Searches for locations matching the query using the WeatherAPI.com search API.
    Results are cached to improve performance for repeated queries.

    Args:
        api_key (str): Your WeatherAPI.com API key.
        query (str): The search query.

    Returns:
        list: A list of matching locations, or None if an error occurs.
    """
    url = f"http://api.weatherapi.com/v1/search.json"
    params = {
        "key": api_key,
        "q": query
    }
    
    logger.info(f"Searching locations with query: {query}")
    
    try:
        response = session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Found {len(data)} locations matching '{query}'")
        return data

    except requests.exceptions.Timeout:
        return handle_request_error(query, "Timeout error", "Timeout")
    except requests.exceptions.ConnectionError:
        return handle_request_error(query, "Connection error", "Connection error")
    except requests.exceptions.HTTPError as e:
        return handle_request_error(query, e, "HTTP error")
    except requests.exceptions.RequestException as e:
        return handle_request_error(query, e)
    except json.JSONDecodeError as e:
        return handle_request_error(query, e, "JSON decode error")
    except Exception as e:
        return handle_request_error(query, e, "Unexpected error") 