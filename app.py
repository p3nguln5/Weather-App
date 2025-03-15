from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import datetime
from weather_service import get_weather_data
import dotenv
from influxdb_service import client, write_weather_data, verify_data_written
import traceback
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('app')

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Load environment variables from .env file
dotenv.load_dotenv()

# Load API key from environment variable
API_KEY = os.environ.get("WEATHER_API_KEY")
if not API_KEY:
    logger.warning("Weather API key not found. Please set WEATHER_API_KEY in your .env file.")

# Default data collection setting (off by default)
DATA_COLLECTION_DEFAULT = False

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.datetime.now().year}

def extract_nested_value(data, keys, default=None):
    """Helper function to safely extract nested values from dictionaries"""
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current

def extract_weather_data(weather_data):
    """Extract all relevant weather data from the API response"""
    result = {}
    
    # Helper function to extract multiple fields at once
    def extract_fields(source_dict, field_list, prefix=''):
        for field in field_list:
            result[f"{prefix}{field}"] = source_dict.get(field)
    
    # Extract Current Weather data
    current = weather_data.get('current', {})
    current_fields = ['last_updated_epoch', 'last_updated', 'temp_c', 'temp_f', 'is_day', 
                     'wind_mph', 'wind_kph', 'wind_degree', 'wind_dir', 'pressure_mb', 
                     'pressure_in', 'precip_mm', 'precip_in', 'humidity', 'cloud', 
                     'feelslike_c', 'feelslike_f', 'vis_km', 'vis_miles', 'gust_mph', 
                     'gust_kph', 'uv', 'windchill_c', 'windchill_f', 'heatindex_c', 
                     'heatindex_f', 'dewpoint_c', 'dewpoint_f']
    extract_fields(current, current_fields)
    
    # Extract condition data
    condition = current.get('condition', {})
    result['condition_text'] = condition.get('text')
    result['condition_icon'] = condition.get('icon')
    result['condition_code'] = condition.get('code')
    
    # Extract Forecast data
    forecast_day = extract_nested_value(weather_data, ['forecast', 'forecastday', 0], {})
    result['date'] = forecast_day.get('date')
    result['date_epoch'] = forecast_day.get('date_epoch')
    
    # Day data
    day = forecast_day.get('day', {})
    day_fields = ['maxtemp_c', 'maxtemp_f', 'mintemp_c', 'mintemp_f', 'avgtemp_c', 
                 'avgtemp_f', 'maxwind_mph', 'maxwind_kph', 'totalprecip_mm', 
                 'totalprecip_in', 'totalsnow_cm', 'avgvis_km', 'avgvis_miles', 
                 'avghumidity', 'daily_will_it_rain', 'daily_will_it_snow', 
                 'daily_chance_of_rain', 'daily_chance_of_snow', 'uv']
    extract_fields(day, day_fields)
    
    # Day condition
    day_condition = day.get('condition', {})
    result['day_condition_text'] = day_condition.get('text')
    result['day_condition_icon'] = day_condition.get('icon')
    result['day_condition_code'] = day_condition.get('code')
    
    # Astro data
    astro = forecast_day.get('astro', {})
    astro_fields = ['sunrise', 'sunset', 'moonrise', 'moonset', 'moon_phase', 
                   'moon_illumination', 'is_sun_up', 'is_moon_up']
    extract_fields(astro, astro_fields)
    
    # Hour data (first hour of forecast)
    hour_data = extract_nested_value(forecast_day, ['hour', 0], {})
    if hour_data:
        hour_fields = ['time_epoch', 'time', 'temp_c', 'temp_f', 'is_day', 'wind_mph', 
                      'wind_kph', 'wind_degree', 'wind_dir', 'pressure_mb', 'pressure_in', 
                      'precip_mm', 'precip_in', 'snow_cm', 'humidity', 'cloud', 
                      'feelslike_c', 'feelslike_f', 'windchill_c', 'windchill_f', 
                      'heatindex_c', 'heatindex_f', 'dewpoint_c', 'dewpoint_f', 
                      'will_it_rain', 'will_it_snow', 'chance_of_rain', 'chance_of_snow', 
                      'vis_km', 'vis_miles', 'gust_mph', 'gust_kph', 'uv']
        extract_fields(hour_data, hour_fields, 'hour_')
        
        # Hour condition
        hour_condition = hour_data.get('condition', {})
        result['hour_condition_text'] = hour_condition.get('text')
        result['hour_condition_icon'] = hour_condition.get('icon')
        result['hour_condition_code'] = hour_condition.get('code')
    
    # Marine Weather data
    marine_data = weather_data.get('marine')
    
    # Extract tide data
    tide_data = extract_nested_value(marine_data, ['tides', 0, 'tide', 0], {})
    if tide_data:
        tide_fields = ['tide_time', 'tide_height_mt', 'tide_type']
        extract_fields(tide_data, tide_fields)
    
    # Marine hour data
    marine_fields = ['sig_ht_mt', 'swell_ht_mt', 'swell_ht_ft', 'swell_dir', 
                    'swell_dir_16_point', 'swell_period_secs', 'water_temp_c', 'water_temp_f']
    if hour_data:
        extract_fields(hour_data, marine_fields)
    
    # Air quality data
    if 'air_quality' in current:
        air_quality_fields = ['co', 'o3', 'no2', 'so2', 'pm2_5', 'pm10', 'us-epa-index', 'gb-defra-index']
        result['air_quality'] = {field: current['air_quality'].get(field) for field in air_quality_fields}
    else:
        result['air_quality'] = {}
    
    # Alerts
    result['alerts'] = extract_nested_value(weather_data, ['alerts', 'alert', 0, 'headline'], "None")
    
    # Location data
    location = weather_data.get('location', {})
    location_fields = ['name', 'region', 'country', 'lat', 'lon', 'tz_id', 'localtime_epoch', 'localtime']
    result['location_data'] = {field: location.get(field) for field in location_fields}
    
    # Format location string
    result['formatted_location'] = f"{location.get('name', '')}, {location.get('country', '')}"
    
    return result

@app.route('/toggle_data_collection', methods=['POST'])
def toggle_data_collection():
    # Toggle the data collection state
    current_state = session.get('collect_data', DATA_COLLECTION_DEFAULT)
    session['collect_data'] = not current_state
    
    # Add a flash message to provide feedback
    if session['collect_data']:
        flash('Data collection has been enabled. Weather data will be saved to the database.', 'success')
    else:
        flash('Data collection has been disabled. Weather data will only be displayed, not saved.', 'info')
    
    # Return to the previous page
    return redirect(request.referrer or url_for('index'))

@app.route('/', methods=['GET', 'POST'])
def index():
    weather_data = None
    location = None
    
    # Initialize data collection state if not set
    if 'collect_data' not in session:
        session['collect_data'] = DATA_COLLECTION_DEFAULT
    
    if request.method == 'POST':
        location = request.form.get('location', '').strip()
        
        if not location:
            flash('Please enter a location', 'error')
            return redirect(url_for('index'))
        
        weather_data = get_weather_data(API_KEY, location)
        
        if not weather_data:
            flash('Unable to retrieve weather data for the specified location. Please try again.', 'error')
        elif session.get('collect_data', DATA_COLLECTION_DEFAULT):
            try:
                logger.info(f"Processing weather data for {location}")
                
                # Extract all weather data
                data = extract_weather_data(weather_data)
                
                # Write to InfluxDB
                write_success = write_weather_data(
                    location=data['formatted_location'],
                    **{k: v for k, v in data.items() if k not in ['formatted_location', 'location_data', 'air_quality']}
                )
                
                if write_success:
                    logger.info(f"Successfully wrote weather data for {location} to InfluxDB")
                    verify_data_written(data['formatted_location'])
                    flash('Weather data successfully saved to InfluxDB!', 'success')
                else:
                    logger.warning(f"Failed to write weather data for {location} to InfluxDB")
                    flash('Failed to save weather data to InfluxDB.', 'warning')
                    
            except Exception as e:
                logger.error(f"Error processing weather data for {location}: {e}")
                logger.error(traceback.format_exc())
                flash('An error occurred while processing the weather data.', 'error')
        else:
            # Data collection is disabled
            flash('Weather data displayed but not saved (data collection is disabled).', 'info')
    
    return render_template('index.html', weather_data=weather_data, location=location, collect_data=session.get('collect_data', DATA_COLLECTION_DEFAULT))

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

# Test connection
try:
    client.ping()
    print("Connected to InfluxDB successfully!")
except Exception as e:
    print(f"Failed to connect to InfluxDB: {e}") 