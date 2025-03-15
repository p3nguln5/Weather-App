from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import os
import dotenv
import traceback
import logging

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

# Check if required environment variables are set
if not all([INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET]):
    logger.warning("Missing InfluxDB configuration. Data storage will not be available.")
    logger.warning("Please set INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, and INFLUXDB_BUCKET in your .env file.")
    client = None
else:
    # Initialize InfluxDB client
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        write_api = client.write_api(write_options=SYNCHRONOUS)
        logger.info("InfluxDB client initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing InfluxDB client: {e}")
        traceback.print_exc()
        client = None

def add_field_to_point(point, name, value, is_string=False):
    """Helper function to add a field to a point with proper type conversion"""
    if value is None:
        return point
    
    if is_string:
        return point.field(name, str(value))
    else:
        try:
            return point.field(name, float(value))
        except (ValueError, TypeError):
            print(f"Warning: Could not convert {name}={value} to float, skipping")
            return point

def write_weather_data(location, temperature, humidity, feels_like, wind, sunrise, sunset, alerts,
                      pressure=None, uv_index=None, visibility=None, condition=None, 
                      precipitation=None, cloud_cover=None, wind_direction=None, gust=None,
                      # Current Weather
                      last_updated_epoch=None, last_updated=None, temp_c=None, temp_f=None,
                      is_day=None, icon=None, code=None, wind_mph=None, wind_kph=None,
                      wind_degree=None, pressure_mb=None, pressure_in=None, precip_mm=None,
                      precip_in=None, vis_km=None, vis_miles=None, gust_mph=None, gust_kph=None,
                      feelslike_c=None, feelslike_f=None, windchill_c=None, windchill_f=None,
                      heatindex_c=None, heatindex_f=None, dewpoint_c=None, dewpoint_f=None,
                      # Forecast/Future/History Weather
                      date=None, date_epoch=None, maxtemp_c=None, maxtemp_f=None, 
                      mintemp_c=None, mintemp_f=None, avgtemp_c=None, avgtemp_f=None,
                      max_wind_mph=None, max_wind_kph=None, totalprecip_mm=None, 
                      totalprecip_in=None, totalsnow_cm=None, avgvis_km=None, 
                      avgvis_miles=None, avghumidity=None, daily_will_it_rain=None,
                      daily_will_it_snow=None, daily_chance_of_rain=None, 
                      daily_chance_of_snow=None,
                      # Astro
                      moonrise=None, moonset=None, moon_phase=None, 
                      moon_illumination=None, is_sun_up=None, is_moon_up=None,
                      # Hour
                      time_epoch=None, time=None, will_it_rain=None, will_it_snow=None,
                      chance_of_rain=None, chance_of_snow=None, snow_cm=None,
                      # Marine Weather
                      tides=None, tide_time=None, tide_height_mt=None, tide_type=None,
                      sig_ht_mt=None, swell_ht_mt=None, swell_ht_ft=None, swell_dir=None,
                      swell_dir_16_point=None, swell_period_secs=None, water_temp_c=None,
                      water_temp_f=None,
                      # Additional parameters
                      air_quality=None, location_data=None):
    """
    Writes comprehensive weather data to InfluxDB.

    Args:
        location (str): The location for which the weather data is recorded.
        temperature (float): The temperature value in Celsius.
        humidity (float): The humidity value.
        feels_like (float): The 'feels like' temperature value in Celsius.
        wind (float): The wind speed value in km/h.
        sunrise (str): The sunrise time.
        sunset (str): The sunset time.
        alerts (str): Weather alerts.
        
        # Many optional parameters for all weather data fields
        # See WeatherAPI documentation for details on each field
    """
    try:
        print(f"Attempting to write weather data for location: {location}")
        
        # Create a single point with all weather data
        point = Point("weather_data").tag("location", location)
        
        # Define field groups with their types
        numeric_fields = {
            # Base fields
            'temperature': temperature,
            'humidity': humidity,
            'feels_like': feels_like,
            'wind': wind,
            'pressure': pressure,
            'uv_index': uv_index,
            'visibility': visibility,
            'precipitation': precipitation,
            'cloud_cover': cloud_cover,
            'gust': gust,
            
            # Current Weather fields
            'last_updated_epoch': last_updated_epoch,
            'temp_c': temp_c,
            'temp_f': temp_f,
            'is_day': is_day,
            'code': code,
            'wind_mph': wind_mph,
            'wind_kph': wind_kph,
            'wind_degree': wind_degree,
            'pressure_mb': pressure_mb,
            'pressure_in': pressure_in,
            'precip_mm': precip_mm,
            'precip_in': precip_in,
            'vis_km': vis_km,
            'vis_miles': vis_miles,
            'gust_mph': gust_mph,
            'gust_kph': gust_kph,
            'feelslike_c': feelslike_c,
            'feelslike_f': feelslike_f,
            'windchill_c': windchill_c,
            'windchill_f': windchill_f,
            'heatindex_c': heatindex_c,
            'heatindex_f': heatindex_f,
            'dewpoint_c': dewpoint_c,
            'dewpoint_f': dewpoint_f,
            
            # Forecast/Future/History Weather fields
            'date_epoch': date_epoch,
            'maxtemp_c': maxtemp_c,
            'maxtemp_f': maxtemp_f,
            'mintemp_c': mintemp_c,
            'mintemp_f': mintemp_f,
            'avgtemp_c': avgtemp_c,
            'avgtemp_f': avgtemp_f,
            'max_wind_mph': max_wind_mph,
            'max_wind_kph': max_wind_kph,
            'totalprecip_mm': totalprecip_mm,
            'totalprecip_in': totalprecip_in,
            'totalsnow_cm': totalsnow_cm,
            'avgvis_km': avgvis_km,
            'avgvis_miles': avgvis_miles,
            'avghumidity': avghumidity,
            'daily_will_it_rain': daily_will_it_rain,
            'daily_will_it_snow': daily_will_it_snow,
            'daily_chance_of_rain': daily_chance_of_rain,
            'daily_chance_of_snow': daily_chance_of_snow,
            
            # Astro fields
            'is_sun_up': is_sun_up,
            'is_moon_up': is_moon_up,
            
            # Hour fields
            'time_epoch': time_epoch,
            'will_it_rain': will_it_rain,
            'will_it_snow': will_it_snow,
            'chance_of_rain': chance_of_rain,
            'chance_of_snow': chance_of_snow,
            'snow_cm': snow_cm,
            
            # Marine Weather fields
            'tide_height_mt': tide_height_mt,
            'sig_ht_mt': sig_ht_mt,
            'swell_ht_mt': swell_ht_mt,
            'swell_ht_ft': swell_ht_ft,
            'swell_dir': swell_dir,
            'swell_period_secs': swell_period_secs,
            'water_temp_c': water_temp_c,
            'water_temp_f': water_temp_f,
        }
        
        string_fields = {
            # String fields
            'sunrise': sunrise,
            'sunset': sunset,
            'alerts': alerts,
            'condition': condition,
            'wind_direction': wind_direction,
            'last_updated': last_updated,
            'icon': icon,
            'date': date,
            'moonrise': moonrise,
            'moonset': moonset,
            'moon_phase': moon_phase,
            'moon_illumination': moon_illumination,
            'time': time,
            'tides': tides,
            'tide_time': tide_time,
            'tide_type': tide_type,
            'swell_dir_16_point': swell_dir_16_point,
        }
        
        # Add numeric fields
        for name, value in numeric_fields.items():
            point = add_field_to_point(point, name, value)
        
        # Add string fields
        for name, value in string_fields.items():
            point = add_field_to_point(point, name, value, is_string=True)
            
        # Add air quality data if available
        if air_quality:
            for key, value in air_quality.items():
                if value is not None:
                    point = add_field_to_point(point, f"air_quality_{key}", value)
                    
        # Add location data if available
        if location_data:
            for key, value in location_data.items():
                if value is not None:
                    if key in ['lat', 'lon', 'localtime_epoch']:
                        point = add_field_to_point(point, f"location_{key}", value)
                    else:
                        point = add_field_to_point(point, f"location_{key}", value, is_string=True)
        
        # Write the point to InfluxDB
        write_api.write(bucket=INFLUXDB_BUCKET, record=point)
        print(f"Successfully wrote weather data for {location} to InfluxDB")
        
        # Verify data was written
        verification = verify_data_written(location)
        return verification
        
    except Exception as e:
        print(f"Error writing weather data to InfluxDB: {e}")
        traceback.print_exc()
        return False

def verify_data_written(location):
    """
    Queries InfluxDB to verify if data for the given location exists.
    
    Args:
        location (str): The location to check for data.
        
    Returns:
        bool: True if data exists, False otherwise.
    """
    try:
        print(f"Verifying data for location: {location}")
        query_api = client.query_api()
        
        # Query to check if the consolidated weather_data measurement exists
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -1h)
          |> filter(fn: (r) => r._measurement == "weather_data")
          |> filter(fn: (r) => r.location == "{location}")
          |> limit(n: 10)
        '''
        
        print(f"Executing query: {query}")
        result = query_api.query(query=query, org=INFLUXDB_ORG)
        
        # Check if we got any results
        if result and len(result) > 0 and len(result[0].records) > 0:
            print(f"Found {len(result[0].records)} records for location {location} in weather_data measurement")
            for record in result[0].records:
                print(f"  - Field: {record.get_field()}, Value: {record.get_value()}")
            return True
        
        # If no results from weather_data, check individual measurements
        print("No data found in weather_data measurement, checking individual measurements...")
        
        # Check temperature measurement as an example
        temp_query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -1h)
          |> filter(fn: (r) => r._measurement == "temperature")
          |> filter(fn: (r) => r.location == "{location}")
          |> limit(n: 1)
        '''
        
        print(f"Executing temperature query: {temp_query}")
        temp_result = query_api.query(query=temp_query, org=INFLUXDB_ORG)
        
        if temp_result and len(temp_result) > 0 and len(temp_result[0].records) > 0:
            print(f"Found temperature data for location {location}")
            return True
        
        # Try a broader query to see what data exists in the bucket
        print("No specific data found, checking what exists in the bucket...")
        broader_query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -1h)
          |> limit(n: 20)
        '''
        
        print(f"Executing broader query: {broader_query}")
        broader_result = query_api.query(query=broader_query, org=INFLUXDB_ORG)
        
        if broader_result and len(broader_result) > 0:
            total_records = sum(len(table.records) for table in broader_result)
            print(f"Found {total_records} total records in the bucket")
            
            for table_idx, table in enumerate(broader_result):
                for record in table.records:
                    print(f"  - Table {table_idx}: {record.get_measurement()}, Field: {record.get_field()}, Value: {record.get_value()}, Tags: {record.values.get('location', 'N/A')}")
        else:
            print("No data found in the bucket at all")
            
        return False
            
    except Exception as e:
        print(f"Error verifying data in InfluxDB: {e}")
        traceback.print_exc()
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