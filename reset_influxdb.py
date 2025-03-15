#!/usr/bin/env python3
"""
Script to reset InfluxDB database by deleting all data.
This gives you a fresh start when encountering field type conflicts.
"""

import os
import sys
import dotenv
from influxdb_client import InfluxDBClient
import traceback
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('reset_influxdb')

# Load environment variables from .env file
dotenv.load_dotenv()

# InfluxDB configuration
INFLUXDB_URL = os.environ.get("INFLUXDB_URL")
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET")

# Check if required environment variables are set
if not all([INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET]):
    logger.error("Missing InfluxDB configuration. Please set INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, and INFLUXDB_BUCKET in your .env file.")
    sys.exit(1)

logger.info(f"InfluxDB Configuration:")
logger.info(f"URL: {INFLUXDB_URL}")
logger.info(f"Organization: {INFLUXDB_ORG}")
logger.info(f"Bucket: {INFLUXDB_BUCKET}")
logger.info(f"Token: {INFLUXDB_TOKEN[:5]}...{INFLUXDB_TOKEN[-5:] if INFLUXDB_TOKEN else None}")

def get_all_measurements(client):
    """
    Get all measurements in the bucket to ensure we delete everything.
    
    Args:
        client: InfluxDB client
        
    Returns:
        list: List of measurement names
    """
    try:
        query_api = client.query_api()
        query = f'''
        import "influxdata/influxdb/schema"

        schema.measurements(bucket: "{INFLUXDB_BUCKET}")
        '''
        
        result = query_api.query(query=query, org=INFLUXDB_ORG)
        
        measurements = []
        if result and len(result) > 0:
            for table in result:
                for record in table.records:
                    measurements.append(record.values.get('_value'))
        
        logger.info(f"Found {len(measurements)} measurements in the bucket")
        return measurements
    except Exception as e:
        logger.error(f"Error getting measurements: {e}")
        return ["weather_data"]  # Fallback to at least delete the main measurement

def reset_influxdb():
    """
    Completely resets the InfluxDB bucket by deleting all data.
    """
    try:
        # Initialize InfluxDB client
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        
        # Get the delete API
        delete_api = client.delete_api()
        
        # Confirm with the user
        print(f"\nWARNING: This will delete ALL data in the bucket '{INFLUXDB_BUCKET}'.")
        confirm = input("Are you sure you want to proceed? (yes/no): ")
        
        if confirm.lower() != 'yes':
            logger.info("Operation cancelled by user")
            return False
        
        # Delete all data in the bucket
        logger.info(f"Deleting all data from bucket '{INFLUXDB_BUCKET}'...")
        
        # Delete from the beginning of time to far in the future
        start = "1970-01-01T00:00:00Z"
        stop = "2099-12-31T23:59:59Z"
        
        # First approach: Delete everything without specifying a predicate
        try:
            logger.info("Attempting to delete all data without predicate...")
            delete_api.delete(
                start=start,
                stop=stop,
                predicate="",
                bucket=INFLUXDB_BUCKET,
                org=INFLUXDB_ORG
            )
            logger.info("Successfully deleted all data without predicate")
        except Exception as e:
            logger.warning(f"Error deleting all data without predicate: {e}")
            logger.info("Falling back to measurement-specific deletion")
            
            # Second approach: Delete the main weather_data measurement
            try:
                delete_api.delete(
                    start=start,
                    stop=stop,
                    predicate="_measurement=\"weather_data\"",
                    bucket=INFLUXDB_BUCKET,
                    org=INFLUXDB_ORG
                )
                logger.info("Deleted main weather_data measurement")
            except Exception as e:
                logger.error(f"Error deleting weather_data measurement: {e}")
            
            # Third approach: Get all measurements and delete them one by one
            measurements = get_all_measurements(client)
            
            # If no measurements found, use a predefined list
            if not measurements:
                measurements = [
                    "weather_data", "temperature", "humidity", "feels_like", "wind", 
                    "sunrise", "sunset", "alerts", "pressure", "uv_index", "visibility", 
                    "condition", "precipitation", "cloud_cover", "wind_direction", "gust",
                    # Current Weather
                    "last_updated_epoch", "last_updated", "temp_c", "temp_f", "is_day",
                    "icon", "code", "wind_mph", "wind_kph", "wind_degree", "pressure_mb",
                    "pressure_in", "precip_mm", "precip_in", "vis_km", "vis_miles",
                    "gust_mph", "gust_kph", "feelslike_c", "feelslike_f", "windchill_c",
                    "windchill_f", "heatindex_c", "heatindex_f", "dewpoint_c", "dewpoint_f",
                    # Forecast/Future/History Weather
                    "date", "date_epoch", "maxtemp_c", "maxtemp_f", "mintemp_c", "mintemp_f",
                    "avgtemp_c", "avgtemp_f", "max_wind_mph", "max_wind_kph", "totalprecip_mm",
                    "totalprecip_in", "totalsnow_cm", "avgvis_km", "avgvis_miles", "avghumidity",
                    "daily_will_it_rain", "daily_will_it_snow", "daily_chance_of_rain",
                    "daily_chance_of_snow",
                    # Astro
                    "moonrise", "moonset", "moon_phase", "moon_illumination", "is_sun_up", "is_moon_up",
                    # Hour
                    "time_epoch", "time", "will_it_rain", "will_it_snow", "chance_of_rain",
                    "chance_of_snow", "snow_cm",
                    # Marine Weather
                    "tides", "tide_time", "tide_height_mt", "tide_type", "sig_ht_mt", "swell_ht_mt",
                    "swell_ht_ft", "swell_dir", "swell_dir_16_point", "swell_period_secs",
                    "water_temp_c", "water_temp_f"
                ]
            
            success_count = 0
            error_count = 0
            
            for measurement in measurements:
                try:
                    delete_api.delete(
                        start=start,
                        stop=stop,
                        predicate=f"_measurement=\"{measurement}\"",
                        bucket=INFLUXDB_BUCKET,
                        org=INFLUXDB_ORG
                    )
                    logger.info(f"Deleted measurement: {measurement}")
                    success_count += 1
                    # Small delay to avoid overwhelming the server
                    time.sleep(0.1)
                except Exception as e:
                    logger.warning(f"Error deleting measurement '{measurement}': {e}")
                    error_count += 1
            
            logger.info(f"Deleted {success_count} measurements, encountered {error_count} errors")
        
        # Verify the deletion
        query_api = client.query_api()
        verification_query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: 0)
          |> limit(n: 1)
        '''
        
        result = query_api.query(query=verification_query, org=INFLUXDB_ORG)
        if result and len(result) > 0 and len(result[0].records) > 0:
            logger.warning("Some data may still exist in the bucket")
        else:
            logger.info("Verification successful: No data found in the bucket")
        
        logger.info("Database reset completed!")
        return True
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = reset_influxdb()
    sys.exit(0 if success else 1) 