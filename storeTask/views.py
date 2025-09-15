import base64
from collections import ChainMap
from curses import meta
import curses
from fileinput import FileInput
import django
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.shortcuts import redirect, render, get_object_or_404
from django.template import loader
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required 
import datetime, uuid, re 
from django.contrib import messages
from django.core.mail import EmailMessage, send_mail
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str 
from django.conf import settings
import requests 
from Task_Project import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User 
from django.views.decorators.csrf import csrf_exempt
from storeTask.models import Image, Video, Audio
from django.utils import timezone
from django.core.files.base import ContentFile  
import folium
from folium.plugins import FastMarkerCluster
from itertools import product   
import json, random, os, logging 
# any datamodel
from django.db.models import Avg
from itertools import product
from django.http import HttpResponse
from django.template import loader  


# Create your views here.
def home(request):
    template = loader.get_template('home.html')   
    context = {       
        } 
    return HttpResponse(template.render(context, request))

import os
import json
from itertools import product
 

ITEM_LIMIT = 2500000  # 25 Lac  --- Adjust the limit as necessary
 
def generate_alpha_dict(start_range, end_range, start_key, chunk_size=ITEM_LIMIT):
    list_Character = [chr(i) for i in range(97, 123)]  # Generate 'a' to 'z'
    alpha_dict = {}
    counter = start_key  # Start from the provided key
    chunk_counter = 0  # Track how many combinations have been added

    for repeat in range(start_range, end_range):
        for combo in product(list_Character, repeat=repeat):
            alpha_dict[counter] = ''.join(combo)
            counter += 1
            chunk_counter += 1
 
            if chunk_counter >= chunk_size:
                yield alpha_dict  # Yield the current chunk
                alpha_dict = {}  # Clear the dictionary to free memory
                chunk_counter = 0
 
    if alpha_dict:
        yield alpha_dict
 
def save_alpha_dict_to_file_chunked(generator, base_file_name, directory, start_part=1):
    part = start_part  # Start from the correct file part number
    try:
        for alpha_dict in generator:
            file_name = f"{base_file_name}_{part}.json"  # Create the part filename
            file_path = os.path.join(directory, file_name)
            
            with open(file_path, 'w') as file:
                json.dump(alpha_dict, file, indent=4)
            
            part += 1  # Increment file part counter
        print(f"Dictionary saved successfully across parts.")
    except Exception as e:
        print(f"Error saving dictionary to file: {e}")
 
def get_last_key_from_previous_files(base_file_name, directory):
    last_key = 0
    part = 1

    while True:
        file_path = os.path.join(directory, f"{base_file_name}_{part}.json")
        if not os.path.exists(file_path):
            break
        with open(file_path, 'r') as file:
            data = json.load(file)
            last_key = max(int(key) for key in data.keys())
        part += 1
    
    return last_key, part  # Return the last key and the next part number
 
def load_alpha_dict_from_file_parts(base_file_name, directory):
    alpha_dict = {}
    part = 1
    
    while True:
        file_path = os.path.join(directory, f"{base_file_name}_{part}.json")
        if not os.path.exists(file_path):
            break
        
        with open(file_path, 'r') as file:
            data = json.load(file)
            alpha_dict.update(data)
        
        part += 1
    
    return alpha_dict if alpha_dict else None
 
def get_last_key_from_all_previous_files(directory):
    last_key = 0
    file_pattern = re.compile(r"english_(\d+)_(\d+).json")  # Pattern to match files like english_3_2.json
 
    for filename in sorted(os.listdir(directory)):
        match = file_pattern.match(filename)
        if match:
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r') as file:
                data = json.load(file)
                if data:
                    last_key = max(int(key) for key in data.keys())  # Get the highest key from the last file

    return last_key

 
def get_key_for_word_from_files(word, directory):
    
    word_length = len(word) 
    base_file_name = f"english_{word_length}"

    part = 1
    while True: 
        file_path = os.path.join(directory, f"{base_file_name}_{part}.json")
 
        if not os.path.exists(file_path):
            break
         
        alpha_dict = load_alpha_dict_from_file(file_path)
        if alpha_dict is not None:
            reverse_dict = {v: k for k, v in alpha_dict.items()}  # Reverse the dictionary for searching
 
            if word in reverse_dict:
                return reverse_dict[word]
        
        part += 1  
    
    return "Word not found"
 
def load_alpha_dict_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading file {file_path}: {e}")
        return None

    
def english(request):
    template = loader.get_template('alphabets.html')
 
    posted_word = 'a'
    file_number = 1
    alpha_dict_show = {}
    words_show = {}
    key_sequence = 0
    file_show = 1

    if request.method == "POST":
        posted_word = request.POST.get('word', 'a')
        file_number = int(request.POST.get('file_number', '1'))
        file_show = int(request.POST.get('file_show', '1'))
 
        file_number_ranges = {
            1: (1, 2), 2: (2, 3), 3: (3, 4), 4: (4, 5),
            5: (5, 6), 6: (6, 7), 7: (7, 8), 8: (8, 9),
            9: (9, 10), 10: (10, 11), 11: (11, 12), 12: (12, 13),
            13: (13, 14), 14: (14, 15), 15: (15, 16), 16: (16, 17),
            17: (17, 18), 18: (18, 19), 19: (19, 20), 20: (20, 21),
            21: (21, 22), 22: (22, 23), 23: (23, 24), 24: (24, 25),
            25: (25, 26), 26: (26, 27)
        }

        start_range, end_range = file_number_ranges.get(file_number, (1, 2)) 
        base_directory = os.path.join(settings.BASE_DIR, "statics/English/")
        
        
        if file_show is not None:
            base_file_name = f"english_{file_show}"
            words_show = load_alpha_dict_from_file_parts(base_file_name, base_directory)
            
        base_file_name = f"english_{file_number}" 
        alpha_dict_show = load_alpha_dict_from_file_parts(base_file_name, base_directory)
        last_key = get_last_key_from_all_previous_files(base_directory)
 
        if not alpha_dict_show:
            start_key = last_key + 1 if last_key else 1  # Start from the last key found
            alpha_dict_gen = generate_alpha_dict(start_range, end_range, start_key)
            save_alpha_dict_to_file_chunked(alpha_dict_gen, base_file_name, base_directory)
        
        if posted_word is not None: 
            key_sequence = get_key_for_word_from_files(posted_word, base_directory)

    context = {
        'alpha_dict': words_show,
        'posted_word': posted_word,
        'key_sequence': key_sequence,
        'file_show': file_show,
        'file_number': file_number,
    }

    return HttpResponse(template.render(context, request))




'''
ITEM_LIMIT = 100000  # Adjust the limit as necessary

# Function to generate combinations of alphabets based on range
def generate_alpha_dict(start_range, end_range, start_key, chunk_size=ITEM_LIMIT):
    list_Character = [chr(i) for i in range(97, 123)]  # Generate 'a' to 'z'
    alpha_dict = {}
    counter = start_key  # Start from the provided key
    chunk_counter = 0  # Track how many combinations have been added

    for repeat in range(start_range, end_range):
        for combo in product(list_Character, repeat=repeat):
            alpha_dict[counter] = ''.join(combo)
            counter += 1
            chunk_counter += 1

            # If the current chunk reaches the limit, save it and clear the dictionary
            if chunk_counter >= chunk_size:
                yield alpha_dict  # Yield the current chunk
                alpha_dict = {}  # Clear the dictionary to free memory
                chunk_counter = 0

    # Yield the remaining combinations (if any)
    if alpha_dict:
        yield alpha_dict

# Function to save the dictionary to a JSON file with proper sequencing
def save_alpha_dict_to_file_chunked(generator, base_file_name, directory, start_part=1):
    part = start_part  # Start from the correct file part number
    try:
        for alpha_dict in generator:
            file_name = f"{base_file_name}_{part}.json"  # Create the part filename
            file_path = os.path.join(directory, file_name)
            
            with open(file_path, 'w') as file:
                json.dump(alpha_dict, file, indent=4)
            
            part += 1  # Increment file part counter
        print(f"Dictionary saved successfully across parts.")
    except Exception as e:
        print(f"Error saving dictionary to file: {e}")

# Function to get the last key from all previous file parts
def get_last_key_from_previous_files(base_file_name, directory):
    last_key = 0
    part = 1

    while True:
        file_path = os.path.join(directory, f"{base_file_name}_{part}.json")
        if not os.path.exists(file_path):
            break
        with open(file_path, 'r') as file:
            data = json.load(file)
            last_key = max(int(key) for key in data.keys())
        part += 1
    
    return last_key, part  # Return the last key and the next part number

# Function to load a dictionary from a file
def load_alpha_dict_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading file {file_path}: {e}")
        return None

# Function to load the dictionary from multiple file parts
def load_alpha_dict_from_file_parts(base_file_name, directory):
    alpha_dict = {}
    part = 1
    
    while True:
        file_path = os.path.join(directory, f"{base_file_name}_{part}.json")
        if not os.path.exists(file_path):
            break
        
        with open(file_path, 'r') as file:
            data = json.load(file)
            alpha_dict.update(data)
        
        part += 1
    
    return alpha_dict if alpha_dict else None

# Function to get the key for a word from files
def get_key_for_word_from_files(word):
    for i in range(1, 27):  # Loop through files english_1.json to english_26.json
        file_name = f"english_{i}.json"
        file_path = os.path.join(settings.BASE_DIR, f"statics/English/{file_name}")
        alpha_dict = load_alpha_dict_from_file(file_path)

        if alpha_dict is not None:  # Check if the dictionary was loaded successfully
            reverse_dict = {v: k for k, v in alpha_dict.items()}  # Reverse the dictionary

            if word in reverse_dict:
                return reverse_dict[word]  # Return the key if the word is found

    return "Word not found"

# Function to handle the entire process in your view
def english(request):
    template = loader.get_template('alphabets.html')

    # Default word and parameters
    posted_word = 'a'
    file_number = 1
    alpha_dict_show = {}
    key_sequence = 0
    file_show = 1

    if request.method == "POST":
        posted_word = request.POST.get('word', 'a')
        file_number = int(request.POST.get('file_number', '1'))
        file_show = int(request.POST.get('file_show', '1'))

        # Map file_number to corresponding ranges
        file_number_ranges = {
            1: (1, 2), 2: (2, 3), 3: (3, 4), 4: (4, 5),
            5: (5, 6), 6: (6, 7), 7: (7, 8), 8: (8, 9),
            9: (9, 10), 10: (10, 11), 11: (11, 12), 12: (12, 13),
            13: (13, 14), 14: (14, 15), 15: (15, 16), 16: (16, 17),
            17: (17, 18), 18: (18, 19), 19: (19, 20), 20: (20, 21),
            21: (21, 22), 22: (22, 23), 23: (23, 24), 24: (24, 25),
            25: (25, 26), 26: (26, 27)
        }

        start_range, end_range = file_number_ranges.get(file_number, (1, 2))

        # Determine the base file name for the display
        base_directory = os.path.join(settings.BASE_DIR, "statics/English/")
        base_file_name = f"english_{file_number}"
        alpha_dict_show = load_alpha_dict_from_file_parts(base_file_name, base_directory)

        # Get the last key and part number from all previous files
        last_key, next_part = get_last_key_from_previous_files(base_file_name, base_directory)

        # Generate the dictionary if the file doesn't exist
        if not alpha_dict_show:
            start_key = last_key + 1 if last_key else 1
            alpha_dict_gen = generate_alpha_dict(start_range, end_range, start_key)
            save_alpha_dict_to_file_chunked(alpha_dict_gen, base_file_name, base_directory, next_part)

        # Get the key sequence for the posted word
        key_sequence = get_key_for_word_from_files(posted_word)

    context = {
        'alpha_dict': alpha_dict_show,
        'posted_word': posted_word,
        'key_sequence': key_sequence,
        'file_show': file_show,
        'file_number': file_number,
    }

    return HttpResponse(template.render(context, request))
'''



 

  
# /////////////////////////////////   ///////////////////      Chart/Graph      //////////////////      ////////////////////////////////
def charted(request):
    template = loader.get_template('charted.html')
    sequences = {}  # Dictionary to store all sequences for each number
    no_convergence = []  # List to track numbers that don't generate 1, 4, or 2

    if request.method == "POST":
        try: 
            start_value = int(request.POST.get('start_val'))
            end_value = int(request.POST.get('end_val'))
        except ValueError:
            context = {'error': "Please enter valid integers."}
            return HttpResponse(template.render(context, request))
 
        for num in range(start_value, end_value + 1):
            var_value = num
            generated_values = []
  
            while var_value != 1:
                generated_values.append(var_value)

                if var_value % 2 == 0:
                    var_value = int(var_value / 2)
                else:
                    var_value = int((var_value * 3) + 1)
  
                if var_value in [1, 2, 4]:
                    generated_values.append(var_value)
                    break
  
            sequences[f'num_{num}'] = generated_values
  
            if not any(x in generated_values for x in [1, 2, 4]):
                no_convergence.append(num)

    context = {
        'sequences': sequences,  # Pass the dictionary of sequences to the template
        'no_convergence': no_convergence  # Pass the numbers that don't generate 1, 2, or 4
    }

    return HttpResponse(template.render(context, request))

  


# /////////////////////////////////   ///////////////////      IMAGE      //////////////////      ////////////////////////////////

@csrf_exempt
def Imge(request):
    template = loader.get_template('image.html')   
    img_show = Image.objects.filter()
    if request.method == "POST":
        var_img = request.POST.get('data_img')
        data_coded = Image_Decode(var_img)
         
        obj_image = Image.objects.create(img_file = data_coded)
        obj_image.save()
    context = {      
               'img_show': img_show ,  
        } 
    return HttpResponse(template.render(context, request))


def Image_Decode(img): 
    base64_img = img # get the base64 img 
    base64key = ";base64,"
    date = timezone.now().strftime('%Y%m%d%H%M%S%f') 
    name_file =  "Profile_"  + str(date) # name for new upload img 
                        
    if base64key in base64_img:
        format, img_str = base64_img.split(base64key)
        ext = format.split('/')[-1]  
        ext_0 = format.split('A')[0]    
        print("ext_0: ", ext_0 )
        full_file_name = f'{name_file}.{ext}' 
        var_profile = ContentFile(base64.b64decode(img_str), name = full_file_name)   
        return var_profile

# /////////////////////////////////   ///////////////////      VIDEO      //////////////////      ////////////////////////////////
def Vdeo(request):
    template = loader.get_template('video.html') 
    
    vid_show = Video.objects.filter()  
    if request.method == "POST":
        var_vid = request.POST.get('data_vid')
        data_coded = Image_Decode(var_vid)
        obj_video = Video.objects.create(vid_file = data_coded)
        obj_video.save()
    context = {      
               'vid_show': vid_show 
        } 
    return HttpResponse(template.render(context, request))



# /////////////////////////////////   ///////////////////      AUDIO      //////////////////      ////////////////////////////////
def Adio(request):
    template = loader.get_template('audio.html')  
    aud_show = Audio.objects.filter() 
    if request.method == "POST":
        var_aud = request.POST.get('data_aud')
        data_coded = Image_Decode(var_aud)
        obj_audio = Audio.objects.create(aud_file = data_coded)
        obj_audio.save() 
    context = {   
               'aud_show': aud_show    
        } 
    return HttpResponse(template.render(context, request))


# /////////////////////////////////   ///////////////////      MAP      //////////////////      ////////////////////////////////



# def get_coordinates(location_name, api_key):
#     url = 'https://api.openrouteservice.org/geocode/search'
#     params = {
#         'api_key': api_key,
#         'text': location_name,
#         'size': 1  # We only need one result
#     }
#     response = requests.get(url, params=params)
    
#     if response.status_code != 200:
#         print(f"Request failed with status code: {response.status_code}")
#         raise ValueError(f"Could not geocode location: {location_name}")

#     try:
#         data = response.json()
#     except requests.exceptions.JSONDecodeError:
#         print("Failed to decode JSON, response text:", response.text)
#         raise ValueError(f"Could not geocode location: {location_name}")

#     # Debugging: print the geocoding response
#     print("Geocoding Response:", data)
    
#     if 'features' in data and len(data['features']) > 0:
#         coordinates = data['features'][0]['geometry']['coordinates']
#         print("this:", data['bbox'][0])
#         return (coordinates[1], coordinates[0])

#     else:
#         raise ValueError(f"Could not geocode location: {location_name}")
  

def map(request):
    template = loader.get_template('maped.html') 
    ors_api_key = settings.MAP_API_SERVICE
    if request.method == 'POST':
        start_location = request.POST.get('start')
        end_location = request.POST.get('end')
        
        start_lat = request.POST.get('start_lat')
        start_lon =  request.POST.get('start_lon')
        end_lat =  request.POST.get('end_lat')
        end_lon =  request.POST.get('end_lon')
        
        location1 = (start_lat, start_lon)
        location2 = (end_lat, end_lon)
        
        # location1 = get_coordinates(start_location, ors_api_key)
        # location2 = get_coordinates(end_location, ors_api_key)
  
        ors_url = f'https://api.openrouteservice.org/v2/directions/driving-car'
        params = {
            'api_key': ors_api_key,
            'start': f'{location1[1]},{location1[0]}',
            'end': f'{location2[1]},{location2[0]}'
        }

        response = requests.get(ors_url, params=params)
        
        try:
            route_data = response.json()
            print( route_data)  
            if 'features' in route_data:  
                coordinates = route_data['features'][0]['geometry']['coordinates'] 
                route_coords = [(coord[1], coord[0]) for coord in coordinates]
 
                m = folium.Map(location=location1, width=1000, height=700, crs="EPSG3857", left=50)
  
                folium.Marker(location1, popup=start_location).add_to(m)
                folium.Marker(location2, popup=end_location).add_to(m)
  
                folium.PolyLine(route_coords, tooltip="Route", color="blue", opacity=0.85).add_to(m)
            else:
                print("No features found in the route data")
                m = folium.Map(location=location1, width=1000, height=700, crs="EPSG3857", left=50)
                folium.Marker(location1, popup=start_location).add_to(m)
                folium.Marker(location2, popup=end_location).add_to(m)
                folium.Popup("Error: Could not retrieve route data").add_to(m)

        except KeyError as e:
            print(f"KeyError: {e}")
            print(f"Response JSON: {route_data}")
            # Create an empty map with an error message
            m = folium.Map(location=location1, width=1000, height=700, crs="EPSG3857", left=50)
            folium.Marker(location1, popup=start_location).add_to(m)
            folium.Marker(location2, popup=end_location).add_to(m)
            folium.Popup("Error: Could not retrieve route data").add_to(m)

        context = {
            'map': m._repr_html_()
        }
        return HttpResponse(template.render(context, request))
    context = {
            'map': "Please Enter Your  Location"
        }
    return HttpResponse(template.render(context, request))

    