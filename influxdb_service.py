from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import os
import dotenv
import traceback
import logging
from functools import lru_cache
from typing import Dict, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('influxdb_service')

# Load environment variables from .env file
dotenv.load_dotenv()

# InfluxDB configuration
INFLUXDB_URL = os.environ.get("INFLUXDB_URL")
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET")

# Global client instance
client = None
write_api = None

# Check if required environment variables are set
if not all([INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET]):
    logger.warning("Missing InfluxDB configuration. Data storage will not be available.")
    logger.warning("Please set INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, and INFLUXDB_BUCKET in your .env file.")
else:
    # Initialize InfluxDB client
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        write_api = client.write_api(write_options=SYNCHRONOUS)
        logger.info("InfluxDB client initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing InfluxDB client: {e}")
        traceback.print_exc()

def add_field_to_point(point: Point, name: str, value: Any, is_string: bool = False) -> Point:
    """Helper function to add a field to a point with proper type conversion"""
    if value is None:
        return point
    
    if is_string:
        return point.field(name, str(value))
    else:
        try:
            # Convert to float if possible
            return point.field(name, float(value))
        except (ValueError, TypeError):
            # If conversion fails, store as string
            return point.field(name, str(value))

def get_client() -> Optional[InfluxDBClient]:
    """Get the InfluxDB client, initializing it if necessary"""
    global client, write_api
    
    if client is None and all([INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET]):
        try:
            client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
            write_api = client.write_api(write_options=SYNCHRONOUS)
            logger.info("InfluxDB client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing InfluxDB client: {e}")
            return None
    
    return client

def write_weather_data(location: str, **fields) -> bool:
    """
    Write weather data to InfluxDB.
    
    Args:
        location: The location for which weather data is being recorded
        **fields: All weather data fields to be stored
        
    Returns:
        bool: True if write was successful, False otherwise
    """
    if client is None or write_api is None:
        logger.error("InfluxDB client not initialized. Cannot write data.")
        return False
    
    try:
        # Create a point with the measurement name and location tag
        point = Point("weather_data").tag("location", location)
        
        # Process string fields separately
        string_fields = [
            'condition', 'wind_direction', 'alerts', 'sunrise', 'sunset',
            'condition_text', 'condition_icon', 'wind_dir', 'day_condition_text',
            'day_condition_icon', 'moon_phase', 'hour_condition_text', 
            'hour_condition_icon', 'tide_type', 'swell_dir_16_point',
            'formatted_location', 'last_updated', 'date', 'moonrise', 'moonset',
            'moon_illumination', 'hour_time', 'swell_dir'
        ]
        
        # Add all fields to the point
        for field_name, field_value in fields.items():
            if field_value is not None:
                is_string = field_name in string_fields
                point = add_field_to_point(point, field_name, field_value, is_string)
        
        # Write the point to InfluxDB
        write_api.write(bucket=INFLUXDB_BUCKET, record=point)
        logger.info(f"Successfully wrote weather data for {location} to InfluxDB")
        return True
        
    except Exception as e:
        logger.error(f"Error writing weather data to InfluxDB: {e}")
        logger.error(traceback.format_exc())
        return False

@lru_cache(maxsize=10)
def verify_data_written(location: str) -> bool:
    """
    Verify that data was written to InfluxDB for the given location.
    Results are cached to improve performance.
    
    Args:
        location: The location to check
        
    Returns:
        bool: True if data was found, False otherwise
    """
    if client is None:
        logger.error("InfluxDB client not initialized. Cannot verify data.")
        return False
    
    try:
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
            |> range(start: -1h)
            |> filter(fn: (r) => r._measurement == "weather_data")
            |> filter(fn: (r) => r.location == "{location}")
            |> limit(n: 1)
        '''
        
        query_api = client.query_api()
        result = query_api.query(query=query)
        
        # Check if any data was returned
        if result and len(result) > 0 and len(result[0].records) > 0:
            logger.info(f"Verified data was written for {location}")
            return True
        else:
            logger.warning(f"No data found for {location} in the last hour")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying data for {location}: {e}")
        return False

def delete_measurement(measurement_name):
    """
    Deletes a measurement from InfluxDB.
    
    Args:
        measurement_name (str): The name of the measurement to delete.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        print(f"Deleting measurement '{measurement_name}' from bucket '{INFLUXDB_BUCKET}'")
        
        # Create a delete API client
        delete_api = client.delete_api()
        
        # Delete data for the specified measurement
        start = "1970-01-01T00:00:00Z"  # Beginning of time
        stop = "2099-12-31T23:59:59Z"   # Far in the future
        
        delete_api.delete(
            start=start,
            stop=stop,
            predicate=f'_measurement="{measurement_name}"',
            bucket=INFLUXDB_BUCKET,
            org=INFLUXDB_ORG
        )
        
        print(f"Measurement '{measurement_name}' deleted successfully")
        return True
        
    except Exception as e:
        print(f"Error deleting measurement '{measurement_name}': {e}")
        traceback.print_exc()
        return False

def reset_database():
    """
    Resets the database by deleting all measurements.
    Use with caution!
    
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        print(f"Resetting database - deleting all measurements from bucket '{INFLUXDB_BUCKET}'")
        
        # List of measurements to delete
        measurements = [
            "temperature", "humidity", "feels_like", "wind", 
            "sunrise", "sunset", "alerts", "pressure", 
            "uv_index", "visibility", "condition", "precipitation", 
            "cloud_cover", "wind_direction", "gust", "weather_data"
        ]
        
        success = True
        for measurement in measurements:
            if not delete_measurement(measurement):
                success = False
        
        return success
        
    except Exception as e:
        print(f"Error resetting database: {e}")
        traceback.print_exc()
        return False 