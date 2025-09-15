import requests
import folium
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

def get_location_from_phone_number(phone_number, account_sid, auth_token):
    """
    Get geolocation information from a phone number using Twilio API.

    Args:
    phone_number (str): The phone number to look up.
    account_sid (str): The Account SID for accessing Twilio API.
    auth_token (str): The Auth Token for accessing Twilio API.

    Returns:
    dict: The JSON response from Twilio API containing location data.
    """
    client = Client(account_sid, auth_token)
    try:
        phone_number_info = client.lookups.v1.phone_numbers(phone_number).fetch(type="carrier")
        return phone_number_info
    except TwilioRestException as e:
        print(f"Error: {e}")
        return None

def create_map(location):
    """
    Create a map with a marker at the specified location and save it as an HTML file.

    Args:
    location (dict): The geolocation data containing latitude and longitude.
    """
    default_lat = 40.712776  # Default latitude (New York City)
    default_lon = -74.005974  # Default longitude (New York City)

    if location:
        print("API Response:", location)
        carrier_type = location.carrier.get('type', 'Unknown')
        city = location.carrier.get('city', 'Unknown City')
        country = location.carrier.get('country', 'Unknown Country')

        if carrier_type == 'mobile' and city != 'Unknown City' and country != 'Unknown Country':
            # Simulate coordinates for the city and country.
            response = requests.get(f"https://nominatim.openstreetmap.org/search?city={city}&country={country}&format=json")
            data = response.json()
            if data:
                latitude = data[0]['lat']
                longitude = data[0]['lon']
                m = folium.Map(location=[latitude, longitude], zoom_start=12)
                folium.Marker([latitude, longitude], popup=f"{city}, {country}").add_to(m)
                m.save("phone_location_map.html")
                print("Map created and saved as phone_location_map.html")
            else:
                print("Unable to find coordinates for the given location. Using default location.")
                m = folium.Map(location=[default_lat, default_lon], zoom_start=12)
                folium.Marker([default_lat, default_lon], popup="Default Location").add_to(m)
                m.save("phone_location_map.html")
                print("Map created and saved as phone_location_map.html")
        else:
            print(f"The phone number is not a mobile number or location data is insufficient. Using default location.")
            m = folium.Map(location=[default_lat, default_lon], zoom_start=12)
            folium.Marker([default_lat, default_lon], popup="Default Location").add_to(m)
            m.save("phone_location_map.html")
            print("Map created and saved as phone_location_map.html")
    else:
        print("Location data not found in API response.")
        m = folium.Map(location=[default_lat, default_lon], zoom_start=12)
        folium.Marker([default_lat, default_lon], popup="Default Location").add_to(m)
        m.save("phone_location_map.html")
        print("Map created and saved as phone_location_map.html")

# Your Twilio Account SID and Auth Token
account_sid = "" # 'YOUR_TWILIO_ACCOUNT_SID'
auth_token = "" # 'YOUR_TWILIO_AUTH_TOKEN'

# The phone number you want to lookup
phone_number = '+923401710232'

# Get location information for the phone number
location = get_location_from_phone_number(phone_number, account_sid, auth_token)

# Create and save the map with the retrieved location data
create_map(location)









# EFTCEJUFQ93WZBFDPWUL4SJV recovert code