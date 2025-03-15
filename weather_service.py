import requests
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('weather_service')

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
    url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={location}&alerts=yes&aqi=yes&days={days}&marine=yes"
    
    logger.info(f"Fetching weather data for location: {location}")
    
    try:
        response = requests.get(url, timeout=10)  # Add timeout for better error handling
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        logger.info(f"Successfully retrieved weather data for {location}")
        return data

    except requests.exceptions.Timeout:
        logger.error(f"Timeout error fetching weather data for {location}")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error fetching weather data for {location}")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching weather data for {location}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weather data for {location}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON response for {location}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching weather data for {location}: {e}")
        return None

def search_locations(api_key, query):
    """
    Searches for locations matching the query using the WeatherAPI.com search API.

    Args:
        api_key (str): Your WeatherAPI.com API key.
        query (str): The search query.

    Returns:
        list: A list of matching locations, or None if an error occurs.
    """
    url = f"http://api.weatherapi.com/v1/search.json?key={api_key}&q={query}"
    
    logger.info(f"Searching locations with query: {query}")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Found {len(data)} locations matching '{query}'")
        return data

    except requests.exceptions.Timeout:
        logger.error(f"Timeout error searching locations for '{query}'")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error searching locations for '{query}'")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error searching locations for '{query}': {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error searching locations for '{query}': {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON response for '{query}': {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error searching locations for '{query}': {e}")
        return None 