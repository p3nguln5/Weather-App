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
    
    # Extract Current Weather data
    current = weather_data.get('current', {})
    for field in ['last_updated_epoch', 'last_updated', 'temp_c', 'temp_f', 'is_day', 
                 'wind_mph', 'wind_kph', 'wind_degree', 'wind_dir', 'pressure_mb', 
                 'pressure_in', 'precip_mm', 'precip_in', 'humidity', 'cloud', 
                 'feelslike_c', 'feelslike_f', 'vis_km', 'vis_miles', 'gust_mph', 
                 'gust_kph', 'uv', 'windchill_c', 'windchill_f', 'heatindex_c', 
                 'heatindex_f', 'dewpoint_c', 'dewpoint_f']:
        result[field] = current.get(field)
    
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
    for field in day_fields:
        result[field] = day.get(field)
    
    # Day condition
    day_condition = day.get('condition', {})
    result['day_condition_text'] = day_condition.get('text')
    result['day_condition_icon'] = day_condition.get('icon')
    result['day_condition_code'] = day_condition.get('code')
    
    # Astro data
    astro = forecast_day.get('astro', {})
    astro_fields = ['sunrise', 'sunset', 'moonrise', 'moonset', 'moon_phase', 
                   'moon_illumination', 'is_sun_up', 'is_moon_up']
    for field in astro_fields:
        result[field] = astro.get(field)
    
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
        for field in hour_fields:
            result[f'hour_{field}'] = hour_data.get(field)
        
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
        result['tide_time'] = tide_data.get('tide_time')
        result['tide_height_mt'] = tide_data.get('tide_height_mt')
        result['tide_type'] = tide_data.get('tide_type')
    
    # Marine hour data
    marine_fields = ['sig_ht_mt', 'swell_ht_mt', 'swell_ht_ft', 'swell_dir', 
                    'swell_dir_16_point', 'swell_period_secs', 'water_temp_c', 'water_temp_f']
    for field in marine_fields:
        result[field] = hour_data.get(field) if hour_data else None
    
    # Air quality data
    if 'air_quality' in current:
        result['air_quality'] = {
            'co': current['air_quality'].get('co'),
            'o3': current['air_quality'].get('o3'),
            'no2': current['air_quality'].get('no2'),
            'so2': current['air_quality'].get('so2'),
            'pm2_5': current['air_quality'].get('pm2_5'),
            'pm10': current['air_quality'].get('pm10'),
            'us_epa_index': current['air_quality'].get('us-epa-index'),
            'gb_defra_index': current['air_quality'].get('gb-defra-index')
        }
    else:
        result['air_quality'] = {}
    
    # Alerts
    result['alerts'] = extract_nested_value(weather_data, ['alerts', 'alert', 0, 'headline'], "None")
    
    # Location data
    location = weather_data.get('location', {})
    result['location_data'] = {
        'name': location.get('name'),
        'region': location.get('region'),
        'country': location.get('country'),
        'lat': location.get('lat'),
        'lon': location.get('lon'),
        'tz_id': location.get('tz_id'),
        'localtime_epoch': location.get('localtime_epoch'),
        'localtime': location.get('localtime')
    }
    
    # Format location string
    result['formatted_location'] = f"{location.get('name', '')}, {location.get('country', '')}"
    
    return result

@app.route('/toggle_data_collection', methods=['POST'])
def toggle_data_collection():
    # Toggle the data collection state
    current_state = session.get('collect_data', DATA_COLLECTION_DEFAULT)
    session['collect_data'] = not current_state
    
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
        else:
            # Only write weather data to InfluxDB if data collection is enabled
            if session.get('collect_data', DATA_COLLECTION_DEFAULT):
                try:
                    print(f"Processing weather data for {location}")
                    
                    # Extract all weather data
                    data = extract_weather_data(weather_data)
                    
                    # Write to InfluxDB
                    write_success = write_weather_data(
                        location=data['formatted_location'],
                        temperature=data['temp_c'],
                        humidity=data['humidity'],
                        feels_like=data['feelslike_c'],
                        wind=data['wind_kph'],
                        sunrise=data.get('sunrise'),  # Use get() to handle None values
                        sunset=data.get('sunset'),    # Use get() to handle None values
                        alerts=data['alerts'],
                        pressure=data['pressure_mb'],
                        uv_index=data['uv'],
                        visibility=data['vis_km'],
                        condition=data['condition_text'],
                        precipitation=data['precip_mm'],
                        cloud_cover=data['cloud'],
                        wind_direction=data['wind_dir'],
                        gust=data['gust_kph'],
                        
                        # Current Weather
                        last_updated_epoch=data['last_updated_epoch'],
                        last_updated=data['last_updated'],
                        temp_c=data['temp_c'],
                        temp_f=data['temp_f'],
                        is_day=data['is_day'],
                        icon=data['condition_icon'],
                        code=data['condition_code'],
                        wind_mph=data['wind_mph'],
                        wind_kph=data['wind_kph'],
                        wind_degree=data['wind_degree'],
                        pressure_mb=data['pressure_mb'],
                        pressure_in=data['pressure_in'],
                        precip_mm=data['precip_mm'],
                        precip_in=data['precip_in'],
                        vis_km=data['vis_km'],
                        vis_miles=data['vis_miles'],
                        gust_mph=data['gust_mph'],
                        gust_kph=data['gust_kph'],
                        feelslike_c=data['feelslike_c'],
                        feelslike_f=data['feelslike_f'],
                        windchill_c=data['windchill_c'],
                        windchill_f=data['windchill_f'],
                        heatindex_c=data['heatindex_c'],
                        heatindex_f=data['heatindex_f'],
                        dewpoint_c=data['dewpoint_c'],
                        dewpoint_f=data['dewpoint_f'],
                        
                        # Forecast/Future/History Weather
                        date=data['date'],
                        date_epoch=data['date_epoch'],
                        maxtemp_c=data['maxtemp_c'],
                        maxtemp_f=data['maxtemp_f'],
                        mintemp_c=data['mintemp_c'],
                        mintemp_f=data['mintemp_f'],
                        avgtemp_c=data['avgtemp_c'],
                        avgtemp_f=data['avgtemp_f'],
                        max_wind_mph=data['maxwind_mph'],
                        max_wind_kph=data['maxwind_kph'],
                        totalprecip_mm=data['totalprecip_mm'],
                        totalprecip_in=data['totalprecip_in'],
                        totalsnow_cm=data['totalsnow_cm'],
                        avgvis_km=data['avgvis_km'],
                        avgvis_miles=data['avgvis_miles'],
                        avghumidity=data['avghumidity'],
                        daily_will_it_rain=data['daily_will_it_rain'],
                        daily_will_it_snow=data['daily_will_it_snow'],
                        daily_chance_of_rain=data['daily_chance_of_rain'],
                        daily_chance_of_snow=data['daily_chance_of_snow'],
                        
                        # Astro
                        moonrise=data['moonrise'],
                        moonset=data['moonset'],
                        moon_phase=data['moon_phase'],
                        moon_illumination=data['moon_illumination'],
                        is_sun_up=data['is_sun_up'],
                        is_moon_up=data['is_moon_up'],
                        
                        # Hour
                        time_epoch=data.get('hour_time_epoch'),
                        time=data.get('hour_time'),
                        will_it_rain=data.get('hour_will_it_rain'),
                        will_it_snow=data.get('hour_will_it_snow'),
                        chance_of_rain=data.get('hour_chance_of_rain'),
                        chance_of_snow=data.get('hour_chance_of_snow'),
                        snow_cm=data.get('hour_snow_cm'),
                        
                        # Marine Weather
                        tides=None,  # Not directly available in the API response
                        tide_time=data.get('tide_time'),
                        tide_height_mt=data.get('tide_height_mt'),
                        tide_type=data.get('tide_type'),
                        sig_ht_mt=data.get('sig_ht_mt'),
                        swell_ht_mt=data.get('swell_ht_mt'),
                        swell_ht_ft=data.get('swell_ht_ft'),
                        swell_dir=data.get('swell_dir'),
                        swell_dir_16_point=data.get('swell_dir_16_point'),
                        swell_period_secs=data.get('swell_period_secs'),
                        water_temp_c=data.get('water_temp_c'),
                        water_temp_f=data.get('water_temp_f'),
                        
                        # Additional data
                        air_quality=data['air_quality'],
                        location_data=data['location_data']
                    )
                    
                    if write_success:
                        flash('Weather data successfully saved to InfluxDB!', 'success')
                    else:
                        flash('Failed to save weather data to InfluxDB.', 'error')
                        
                except Exception as e:
                    print(f"Error processing weather data: {e}")
                    traceback.print_exc()
                    flash('An error occurred while processing the weather data.', 'error')
            else:
                flash('Weather data displayed but not saved to database (data collection is disabled).', 'info')
    
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