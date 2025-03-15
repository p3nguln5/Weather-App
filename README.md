# Weather App

A web application that displays current weather conditions, astronomy data, and weather alerts for locations around the world using the WeatherAPI.com service.

## Features

- Current weather conditions (temperature, humidity, wind, etc.)
- Astronomy data (sunrise, sunset, moonrise, moonset, moon phase)
- Weather alerts and warnings
- Search by city name, zip code, IP address, or coordinates
- Optional data storage with InfluxDB

## Installation

1. Clone or download this repository:
   ```
   git clone <repository-url>
   cd weather-app
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   - Copy the `.env.example` file to `.env`:
     ```
     cp .env.example .env
     ```
   - Edit the `.env` file and add your own values:
     - Get a free API key from [WeatherAPI.com](https://www.weatherapi.com/)
     - Configure your InfluxDB settings if you want to store weather data

4. Run the application:
   ```
   python app.py
   ```

5. Open your web browser and navigate to `http://127.0.0.1:5000`

## Environment Variables

The application uses the following environment variables:

- `WEATHER_API_KEY`: Your WeatherAPI.com API key (required)
- `INFLUXDB_URL`: URL of your InfluxDB instance (optional, for data storage)
- `INFLUXDB_TOKEN`: Authentication token for InfluxDB (optional, for data storage)
- `INFLUXDB_ORG`: Your organization name in InfluxDB (optional, for data storage)
- `INFLUXDB_BUCKET`: Bucket name for storing weather data (optional, for data storage)

If InfluxDB environment variables are not set, the application will run without data storage capabilities.

## Search Options

You can search for weather information using any of the following formats:

- City name (e.g., "London", "New York")
- City and country (e.g., "Paris, France")
- US zip code (e.g., "90210")
- UK postcode (e.g., "SW1")
- Canada postal code (e.g., "G2J")
- IP address (e.g., "100.0.0.1")
- Latitude and longitude (e.g., "48.8567,2.3508")

## Technologies Used

- Python
- Flask
- Bootstrap 5
- Font Awesome
- WeatherAPI.com

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Weather data provided by [WeatherAPI.com](https://www.weatherapi.com/)
- Icons by [Font Awesome](https://fontawesome.com/)
- UI components by [Bootstrap](https://getbootstrap.com/) 