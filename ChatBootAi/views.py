from django.http import HttpResponse
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer   
from nltk.corpus import stopwords    
from collections import defaultdict  
from django.core.cache import cache 
from django.template import loader  
from Task_Project import settings     
from .models import Conversation     
from nltk import word_tokenize   
from textblob import TextBlob   
import  datetime 
import  random
import  spacy
import  time
import  json 
import nltk 
import  re 
import  os     
 
from selenium import webdriver   
from selenium.webdriver.common.by import By 
from selenium.webdriver.chrome.options import Options  
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service  
from webdriver_manager.chrome import ChromeDriverManager 

 
# Load NLP models
nlp = spacy.load("en_core_web_sm")
analyzer = SentimentIntensityAnalyzer()
nltk.data.path.append('C:/nltk_data')
lemmatizer = nltk.WordNetLemmatizer()
response_file = os.path.join(settings.BASE_DIR, "statics/response.json")
intents_file = os.path.join(settings.BASE_DIR, "statics/intents.json")
emotion_file = os.path.join(settings.BASE_DIR, "statics/emotions.json")
user_context = defaultdict(dict)

# Load response, intents, and emotions data
def load_json_file(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def load_responses():
    return load_json_file(response_file)

def load_intents():
    return load_json_file(intents_file)

def load_emotions():
    return load_json_file(emotion_file)
 
def validate_user_input(user_input):
    return bool(user_input.strip()) and not re.search(r'<script>|<\/script>', user_input)
 
def predict_intent(user_input, intents):
    tokens = word_tokenize(user_input.lower())
    filtered_tokens = [lemmatizer.lemmatize(token) for token in tokens if token not in stopwords.words('english')]

    intent_scores = {intent: 0 for intent in intents}

    for intent, keywords in intents.items():
        for keyword in keywords:
            keyword_tokens = word_tokenize(keyword.lower())  # Tokenize the intent keyword phrase
            n = len(keyword_tokens) 
            
            for i in range(len(filtered_tokens) - n + 1):
                phrase = ' '.join(filtered_tokens[i:i + n])
                if phrase == keyword.lower():  # Require exact phrase match
                    intent_scores[intent] += 1
    
    return [intent for intent, score in sorted(intent_scores.items(), key=lambda x: x[1], reverse=True) if score > 0]

# Extract entities from user input
def extract_entities(user_input):
    doc = nlp(user_input)
    entities = {}
    for ent in doc.ents:
        if ent.label_ == 'PERSON':
            entities['name'] = ent.text
        if ent.label_ == 'GPE':
            entities['place'] = ent.text
    return entities

# Fetch user data from the database if the name is not found in the input
def fetch_user_data(user_email):
    conversations = Conversation.objects.filter(user_email=user_email)
    previous_data = {}

    for conv in conversations:
        entities = extract_entities(conv.user_input)
        if 'name' in entities:
            previous_data['name'] = entities['name']
        if 'place' in entities:
            previous_data['place'] = entities['place']

    return previous_data

# Rate limiting functions
def is_rate_limited(user_email):
    key = f"chat_rate_limit_{user_email}"
    if cache.get(key):
        return True
    cache.set(key, '1', timeout=2)  # 2 seconds rate limit
    return False

def rate_limit_phrases(user_input, user_email):
    key = f"user_input_{user_email}"
    recent_input = cache.get(key)
    if recent_input == user_input:
        return True
    cache.set(key, user_input, timeout=10)
    return False

# Sentiment and emotion analysis
def analyze_sentiment_polarity(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    vader_scores = analyzer.polarity_scores(text)
    return polarity, vader_scores

def detect_emotion(user_input):
    doc = nlp(user_input.lower())
    emotions = load_emotions()
    emotion_scores = defaultdict(int)

    for emotion, keywords in emotions.items():
        for token in doc:
            if token.lemma_ in keywords:
                emotion_scores[emotion] += 1

    return max(emotion_scores, key=emotion_scores.get, default="neutral") if emotion_scores else None

# Handle laughter in user input
def detect_laughter(user_input):
    laughter_patterns = re.compile(r'(ha[ha]+|he[he]+|lol|lmao|rofl)', re.IGNORECASE)
    match = laughter_patterns.search(user_input)
    return match.group(0) if match else False

def handle_laughter_response(laughter):
    laughter_responses = {
        r'ha[ha]+': "Your tone feels light-hearted and positive. You seem amused!",
        r'he[he]+': "Your tone feels playful and sly. Are you teasing?",
        r'lol': "'LOL'! Glad to see you're having fun!",
        r'hmm+': "'Hmm'... are you pondering something? Your tone feels thoughtful.",
    }
    for pattern, response in laughter_responses.items():
        if re.match(pattern, laughter, re.IGNORECASE):
            return response
    return "I noticed you're laughing. What's amusing you?"

def analyze_sentiment(user_input):
    blob = TextBlob(user_input)
    polarity = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity
    vader_scores = analyzer.polarity_scores(user_input)

    laughter = detect_laughter(user_input)
    if laughter:
        return handle_laughter_response(laughter)

    emotion = detect_emotion(user_input)
    response = f"I sense you're feeling {emotion}." if emotion else ""

    if polarity < -0.5 or vader_scores['compound'] < -0.5:
        response += " It seems like you're feeling down. I'm here to listen."
    elif polarity > 0.5 or vader_scores['compound'] > 0.5:
        response += " You're in high spirits! Keep up the positivity."

    if subjectivity > 0.75:
        response += " You seem to have a strong opinion on this matter."
    elif subjectivity < 0.25:
        response += ""

    if "not" in user_input or "no" in user_input:
        response += " I noticed some negation in your words. Feel free to clarify."

    return response


# Generate combined responses
def get_combined_responses(queries, responses, user_email):
    combined_responses = []
    previous_data = fetch_user_data(user_email)

    for query in queries:
        query = query.strip()
        if not query:
            continue
        intents_user = predict_intent(query, load_intents())
        entities = extract_entities(query)
        name = entities.get('name', previous_data.get('name', "there"))

        sentiment_response = analyze_sentiment(query)
        if not intents_user:
            combined_responses.append(fetch_google_summary(query))
        elif sentiment_response:
            combined_responses.append(sentiment_response)
        elif "datetime" in intents_user:
            current_datetime = datetime.datetime.now().strftime("%Y-%m-%d - %H:%M:%S")
            combined_responses.append(random.choice(responses["datetime"]).replace("{datetime}", current_datetime))
        elif "time" in intents_user:
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            combined_responses.append(random.choice(responses["time"]).replace("{time}", current_time))
        elif "date" in intents_user:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d")
            combined_responses.append(random.choice(responses["date"]).replace("{date}", current_time))
        else:
            for intent in intents_user:
                response_template = random.choice(responses[intent]).replace("{name}", name)
                combined_responses.append(response_template)

    return " ".join(combined_responses)
 
# Adding intents and responses to JSON
def add_intent_to_json(intent_name, keywords):
    intents = load_intents()
    keywords_list = [keyword.strip().lower() for keyword in keywords if keyword.strip()]  # Ensure keywords are cleaned
    if intent_name not in intents:
        intents[intent_name] = keywords_list
        with open(intents_file, 'w') as f:
            json.dump(intents, f, indent=4)
        return f"Intent '{intent_name}' has been added successfully!"
    return f"Intent '{intent_name}' already exists."

def add_response_to_json(intent_name, responses):
    response_data = load_responses()
    response_list = [response.strip() for response in responses if response.strip()]  # Ensure responses are cleaned
    if intent_name in response_data:
        response_data[intent_name].extend(response_list)
    else:
        response_data[intent_name] = response_list
    with open(response_file, 'w') as f:
        json.dump(response_data, f, indent=4)
    return f"Responses added successfully to intent '{intent_name}'."
   
def find_keywords(response):
    keywords = ["image", "photo", "picture", "pics", "img", "photos", "images", "pictures"]
    action_words = ["create", "made", "make", "send", "sent"]
    
    # Check if the response is too long
    if len(response) > 100:  # Adjust the maximum length as needed
        return None
    
    found_keywords = []
    found_actions = [] 
    for word in keywords:
        if word in response:
            found_keywords.append(word) 
    for action in action_words:
        if action in response:
            found_actions.append(action)

    # Form phrases
    phrases = []
    if found_keywords and found_actions:
        phrases = [f"{action} {keyword}" for action in found_actions for keyword in found_keywords]

    # Also return single keywords found
    return phrases, found_keywords if phrases else found_keywords 

 
def fetch_google_summary(query, max_pages=2):
    print("query :", query) 
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}&hl=en&gl=us"
    print("query :", url)
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--log-level=3") 
    chrome_options.add_argument("--remote-allow-origins=*")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
     
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
  

    try:
        service = Service(ChromeDriverManager().install()) 
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
                """
            },
        )
    except Exception as e:
        return f"Error initializing browser: {str(e)}"
    
    driver.get(url) 
    search_results = []
    image_links = []
    current_page = 1
    first_link = None
    
    while current_page <= max_pages: 
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div#search, input[name='q']"))
                # EC.presence_of_element_located((By.XPATH, "//h3"))
            )  
        except Exception as e:
            driver.quit()
            return f"Google search timed out. The page structure may have changed. {current_page}: {str(e)}"
          
        try:
            featured_snippet = driver.find_element(By.CSS_SELECTOR, 'span.hgKElc')
            snippet_text = featured_snippet.text.strip()
            search_results.append(f"{snippet_text.replace('...', ".")}")
        except Exception as e:
            print(".", str(e))  
         
        results = driver.find_elements(By.XPATH, "//div[@id='search']//h3")
        for result in results:
            try:
                title = result.text.strip()
                print("TITLE:", title)
                print("TITLE In:", driver.title)
                
                # link_element = result.find_element(By.CSS_SELECTOR, 'a')
                link = result.find_element(By.XPATH, "./ancestor::a").get_attribute("href")
                print("LINK:", link)

                if first_link is None:
                    first_link = link
                print("resultSS: ", results) 
                container = result.find_element(By.XPATH, "./ancestor::div[@class='g']")
                try:
                    snippet_element = container.find_element(By.CLASS_NAME, "VwiC3b")
                    snippet = snippet_element.text.strip()
                except Exception as e:
                    print(str(e))
                    snippet = "."
                
                search_results.append(f"{snippet} ")
                 
                try:
                    img_element = result.find_element(By.TAG_NAME, 'img')
                    img_link = img_element.get_attribute('src').strip()
                    if img_link:
                        image_links.append(img_link)  
                except Exception as e:
                    print(f"{"Error processing inner Block"}", str(e))  

            except Exception as e:
                print(f"Error processing result: {str(e)}")
         
        # Check for next page
        try:
            next_button = driver.find_element(By.ID, 'pnnext')
            next_button.click()
            time.sleep(3)  
            current_page += 1
        except Exception as e:
            print(".", str(e))   
            break
    print("resultSSS: ", results)
    print("TITLE end:", driver.title)
    if first_link:
        driver.execute_script("window.open('');") 
        driver.switch_to.window(driver.window_handles[1])  
        driver.get(first_link) 

        try: 
            WebDriverWait(driver, 7).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            page_content = driver.find_element(By.TAG_NAME, 'body').text[:10000].strip()  
            search_results.append(f"{' \n\n '}" + f"{page_content}" + f"{' \n\n '}")

            # Check for images on the opened page
            img_elements = driver.find_elements(By.TAG_NAME, 'img')
            for img_element in img_elements:
                img_link = img_element.get_attribute('src').strip()
                if img_link:
                    image_links.append(f"{first_link} :- {img_link}")
        
        except Exception as e:
            search_results.append(f"Failed to retrieve content from {first_link}\n\n", str(e))
        
        driver.close()  # Close the tab
        driver.switch_to.window(driver.window_handles[0])  
    
    driver.quit()
    found_words, single_keywords = find_keywords(query)
    valid_combinations = {
        "image", "images", "img",  
        "an image", "an images", "an img", 
        "one image", "one images", "one img",
        "many image", "many images", "many img",
        "more image", "more images", "more img",
        "create image", "create photo", "create picture", "create pics", "create img", "create images", "create photos", "create pictures", 
        "create an image", "create an photo", "create an picture", "create an pics", "create an img", "create an images", "create an photos", "create an pictures",
        "create a image", "create a photo", "create a picture", "create a pics", "create a img", "create a images", "create a photos", "create a pictures",
        "create one image", "create one photo", "create one picture", "create one pics", "create one img", "create one images", "create one photos", "create one pictures",
        "create more image", "create more photo", "create more picture", "create more pics", "create more img", "create more images", "create more photos", "create more pictures",
        "create many image", "create many photo", "create many picture", "create many pics", "create many img", "create many images", "create many photos", "create many pictures",
        "photo", "photos",
        "make image", "make photo", "make picture", "make pics", "make img", "make images", "make photos", "make pictures",
        "make an image", "make an photo", "make an picture", "make an pics", "make an img", "make an images", "make an photos", "make an pictures",
        "make a image", "make a photo", "make a picture", "make a pics", "make a img", "make a images", "make a photos", "make a pictures",
        "make one image", "make one photo", "make one picture", "make one pics", "make one img", "make one images", "make one photos", "make one pictures",
        "make more image", "make more photo", "make more picture", "make more pics", "make more img", "make more images", "make more photos", "make more pictures",
        "make many image", "make many photo", "make many picture", "make many pics", "make many img", "make many images", "make many photos", "make many pictures",
        "picture", "picture", 
        "made image", "made photo", "made picture", "made pics", "made img", "made images", "made photos", "made pictures", 
        "made a image", "made a photo", "made a picture", "made a pics", "made a img", "made a images", "made a photos", "made a pictures", 
        "made one image", "made one photo", "made one picture", "made one pics", "made one img", "made one images", "made one photos", "made one pictures", 
        "made many image", "made many photo", "made many picture", "made many pics", "made many img", "made many images", "made many photos", "made many pictures", 
        "made more image", "made more photo", "made more picture", "made more pics", "made more img", "made more images", "made more photos", "made more pictures",  
        "send image", "send photo", "send picture", "send images", "send pictures", "send photos", "send img", "send pics", 
        "sent image", "sent photo", "sent picture", "sent images", "sent pictures", "sent photos", "sent img", "sent pics",
        "sent an image", "sent an photo", "sent an picture", "sent an images", "sent an pictures", "sent an photos", "sent an img", "sent an pics"
    } 
    # Check for any valid combination in found words
     
    if image_links:
        search_results.append(f"{first_link} : {link} \n\n \n {img_link}")
    
    if single_keywords:
        return f"\n {query} : " + " \n\n " + img_link
    elif found_words and any(combination in found_words for combination in valid_combinations):
        return f"\n {query} : " + " \n\n " + img_link
    elif search_results:
        return "\n\n".join(search_results)
    else:
        return "No relevant search results found."
 

def clear_multiple_whitespaces(text): 
    return re.sub(r'\s+', ' ', text).strip()
 

def format_code_like_syntax(text): 
    function_pattern = re.compile(
        r'\b(public|private|protected|static|def|var|function|void)?\s*'
        r'(int|float|char|bool|void)?\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)(\s*\{.*\})?'
    )
    
    formatted_text = function_pattern.sub(
        r'<br><i><span style="font-family: monospace; background-color: lightgray;">\1 \2 \3(\4)\5</span></i>', text
    )
    
    return formatted_text.replace(formatted_text, f"{formatted_text} <br>")

def replace_dots_except_in_urls_and_titles(text):
    
    url_pattern = re.compile(r'(https?://[^\s]+)')
    urls = url_pattern.findall(text)

    for i, url in enumerate(urls):
        text = text.replace(url, f"__URL_{i}__")

    abbreviations = ["Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Sr.", "Jr."]
    
    for i, abbrev in enumerate(abbreviations):
        text = text.replace(abbrev, f"__ABBREV_{i}__")
     
    text = text.replace(". ", ".<br>")

    for i, abbrev in enumerate(abbreviations):
        text = text.replace(f"__ABBREV_{i}__", abbrev)

    for i, url in enumerate(urls):
        text = text.replace(f"__URL_{i}__", url)

    return text

def format_bot_response(response): 
    formatted = response.replace("...", " ").replace('....', " ").replace("\n", "<br>").replace("--", " ").replace("---", " ").replace("----", " ").replace("!!!", "!")
      
    formatted = replace_dots_except_in_urls_and_titles(formatted)
      
    formatted = format_code_like_syntax(formatted)
      
    # Default iframe for other links
    url_pattern = re.compile(r'(https?://[^\s]+)')
    formatted = url_pattern.sub(r'<br><iframe src="\1" class="responsive-iframe" target="_blank" ></iframe><br>', formatted) 
    default_matches = url_pattern.findall(formatted)
    print("YouTube Matches:", default_matches)  # Debugging line
    # Image formatting to handle multiple image types (PNG, JPEG, JPG, GIF)
    url_pattern_img = re.compile(r'(data:image/(png|jpeg|webp|jpng|jpg|ico|icon|svg|gif);base64,[^\s]+)')
    formatted = url_pattern_img.sub(r'<br><a href="\1"><img src="\1"  class="responsive-image"  target="_blank"></img></a>', formatted)
     
    # YouTube Embed
    youtube_pattern = re.compile(r'https?://(?:www\.)?(youtube\.com/watch\?v=|youtu\.be/)([^\s&]+)')
    youtube_matches = youtube_pattern.findall(formatted)
    print("YouTube Matches:", youtube_matches)  # Debugging line
    formatted = youtube_pattern.sub(r'<br><iframe width="560" height="315" src="https://www.youtube.com/embed/\2" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe><br>', formatted)

    # TikTok Embed
    tiktok_pattern = re.compile(r'https?://(?:www\.)?tiktok\.com/@[^\s]+/video/([^\s]+)')
    tiktok_matches = tiktok_pattern.findall(formatted)
    print("TikTok Matches:", tiktok_matches)  # Debugging line
    formatted = tiktok_pattern.sub(r'<br><blockquote class="tiktok-embed" cite="https://www.tiktok.com/@user/video/\1" style="max-width: 605px;min-width: 325px;"></blockquote><script async src="https://www.tiktok.com/embed.js"></script><br>', formatted)

    # Facebook Embed
    facebook_pattern = re.compile(r'https?://(?:www\.)?facebook\.com/[^/]+/posts/([^\s]+)')
    facebook_matches = facebook_pattern.findall(formatted)
    print("Facebook Matches:", facebook_matches)  # Debugging line
    formatted = facebook_pattern.sub(r'<br><iframe width="560" height="315" src="https://www.facebook.com/posts/\1" allowTransparency="true" frameborder="0" scrolling="no" allow="encrypted-media" allowfullscreen></iframe><script async defer crossorigin="anonymous" src="https://connect.facebook.net/en_US/sdk.js#xfbml=1&version=v9.0"></script><br>', formatted)

    # Instagram Embed
    instagram_pattern = re.compile(r'https?://(?:www\.)?instagram\.com/p/([^\s/]+)')
    instagram_matches = instagram_pattern.findall(formatted)
    print("Instagram Matches:", instagram_matches)  # Debugging line
    formatted = instagram_pattern.sub(r'<br><blockquote class="instagram-media" data-instgrm-permalink="https://www.instagram.com/p/\1" data-instgrm-version="12"></blockquote><script async defer src="//www.instagram.com/embed.js"></script><br>', formatted)

    # Twitter Embed
    twitter_pattern = re.compile(r'https?://(?:www\.)?twitter\.com/[^\s]+/status/([^\s?]+)')
    twitter_matches = twitter_pattern.findall(formatted)
    print("Twitter Matches:", twitter_matches)  # Debugging line
    formatted = twitter_pattern.sub(r'<br><blockquote class="twitter-tweet"><a href="https://twitter.com/user/status/\1"></a></blockquote><script async src="https://platform.twitter.com/widgets.js"></script><br>', formatted)
 
    bullet_point_pattern = re.compile(r'( · [^\s]+)')
    formatted = bullet_point_pattern.sub(r'<ul><li>\1</li></ul>', formatted)
     
    formatted = re.sub(r'(\d{3}[-\s]\d{7})', r'<strong>\1</strong>', formatted)
    
    return formatted

# Chatbot main function
def chatbot(request):
    template = loader.get_template('chat.html')
    user_email = request.user.email
    msg_show = Conversation.objects.filter(user_email=user_email)  
    
    if request.method == "POST":
        user_input = request.POST.get('user_input')

        if not validate_user_input(user_input):
            context = {'error': "Invalid input", 'success': '', 'msg_show': msg_show}
            return HttpResponse(template.render(context, request)) 
        if is_rate_limited(user_email) or rate_limit_phrases(user_input, user_email):
            context = {'error': "Please wait before sending another message.", 'success': '', 'msg_show': msg_show}
            return HttpResponse(template.render(context, request))
 
        combined_response = get_combined_responses([user_input], load_responses(), user_email)
        combined_response_new = clear_multiple_whitespaces(combined_response)
        new_combined_response = combined_response_new.replace("...", " ").replace('....', " ").replace("\n", " ").replace("--", " ").replace("---", " ").replace("----", " ").replace("!!!", "!")  
        keywords = user_input
        intent_name = user_input
        if intent_name and keywords:
            keywords_list = keywords.split(",")
            add_intent_to_json(intent_name, keywords_list)  # Add intent

        response_intent = keywords
        new_responses = new_combined_response
        if response_intent and new_responses:
            response_list = new_responses.split(",")  
            add_response_to_json(response_intent, response_list)
    
        # Store the conversation
        Conversation.objects.create(user_email=user_email, user_input=user_input, bot_response = new_combined_response)
        for msg in msg_show: 
            msg.bot_response = format_bot_response(msg.bot_response) 
        context = {'error': '', 'success': '', 'msg_show': msg_show}
        return HttpResponse(template.render(context, request))
    
    for msg in msg_show: 
        msg.bot_response = format_bot_response(msg.bot_response) 
    context = {'error': '', 'success': '', 'msg_show': msg_show}
    return HttpResponse(template.render(context, request))

 

# # Chatbot main function
# def chatbot(request):
#     template = loader.get_template('chat.html')
#     user_email = request.user.email
#     msg_show = Conversation.objects.filter(user_email=user_email)  
    
#     if request.method == "POST":
#         user_input = request.POST.get('user_input')

#         if not validate_user_input(user_input):
#             context = {'error': "Invalid input", 'success': '', 'msg_show': msg_show}
#             return HttpResponse(template.render(context, request)) 
#         if is_rate_limited(user_email) or rate_limit_phrases(user_input, user_email):
#             context = {'error': "Please wait before sending another message.", 'success': '', 'msg_show': msg_show}
#             return HttpResponse(template.render(context, request))
 
#         combined_response = get_combined_responses([user_input], load_responses(), user_email)
#         combined_response_new = clear_multiple_whitespaces(combined_response)
#         new_combined_response = combined_response_new.replace("...", " ").replace('....', " ").replace("\n", " ").replace("--", " ").replace("---", " ").replace("----", " ").replace("!!!", "!")  
#         keywords = user_input
#         intent_name = user_input
#         if intent_name and keywords:
#             keywords_list = keywords.split(",")
#             add_intent_message = add_intent_to_json(intent_name, keywords_list)  # Add intent

#         response_intent = keywords
#         new_responses = new_combined_response
#         if response_intent and new_responses:
#             response_list = new_responses.split(",")  
#             add_response_message = add_response_to_json(response_intent, response_list)
    
#         # Store the conversation
#         Conversation.objects.create(user_email=user_email, user_input=user_input, bot_response = new_combined_response)
#         for msg in msg_show: 
#             msg.bot_response = format_bot_response(msg.bot_response) 
#         context = {'error': '', 'success': '', 'msg_show': msg_show}
#         return HttpResponse(template.render(context, request))
    
#     for msg in msg_show: 
#         msg.bot_response = format_bot_response(msg.bot_response) 
#     context = {'error': '', 'success': '', 'msg_show': msg_show}
#     return HttpResponse(template.render(context, request))


#   # valid_combinations = {
#     #     "image", "images", "img",  
#     #     "an image", "an images", "an img", 
#     #     "one image", "one images", "one img",
#     #     "many image", "many images", "many img",
#     #     "more image", "more images", "more img",
#     #     "create image", "create photo", "create picture", "create pics", "create img", "create images", "create photos", "create pictures", 
#     #     "create an image", "create an photo", "create an picture", "create an pics", "create an img", "create an images", "create an photos", "create an pictures",
#     #     "create a image", "create a photo", "create a picture", "create a pics", "create a img", "create a images", "create a photos", "create a pictures",
#     #     "create one image", "create one photo", "create one picture", "create one pics", "create one img", "create one images", "create one photos", "create one pictures",
#     #     "create more image", "create more photo", "create more picture", "create more pics", "create more img", "create more images", "create more photos", "create more pictures",
#     #     "create many image", "create many photo", "create many picture", "create many pics", "create many img", "create many images", "create many photos", "create many pictures",
#     #     "photo", "photos",
#     #     "make image", "make photo", "make picture", "make pics", "make img", "make images", "make photos", "make pictures",
#     #     "make an image", "make an photo", "make an picture", "make an pics", "make an img", "make an images", "make an photos", "make an pictures",
#     #     "make a image", "make a photo", "make a picture", "make a pics", "make a img", "make a images", "make a photos", "make a pictures",
#     #     "make one image", "make one photo", "make one picture", "make one pics", "make one img", "make one images", "make one photos", "make one pictures",
#     #     "make more image", "make more photo", "make more picture", "make more pics", "make more img", "make more images", "make more photos", "make more pictures",
#     #     "make many image", "make many photo", "make many picture", "make many pics", "make many img", "make many images", "make many photos", "make many pictures",
#     #     "picture", "picture", 
#     #     "made image", "made photo", "made picture", "made pics", "made img", "made images", "made photos", "made pictures", 
#     #     "made a image", "made a photo", "made a picture", "made a pics", "made a img", "made a images", "made a photos", "made a pictures", 
#     #     "made one image", "made one photo", "made one picture", "made one pics", "made one img", "made one images", "made one photos", "made one pictures", 
#     #     "made many image", "made many photo", "made many picture", "made many pics", "made many img", "made many images", "made many photos", "made many pictures", 
#     #     "made more image", "made more photo", "made more picture", "made more pics", "made more img", "made more images", "made more photos", "made more pictures",  
#     #     "send image", "send photo", "send picture", "send images", "send pictures", "send photos", "send img", "send pics", 
#     #     "sent image", "sent photo", "sent picture", "sent images", "sent pictures", "sent photos", "sent img", "sent pics",
#     #     "sent an image", "sent an photo", "sent an picture", "sent an images", "sent an pictures", "sent an photos", "sent an img", "sent an pics"
#     # }




# 0000000000000000000000000000000000000000000

# def find_keywords(response):
#     keywords = ["image", "photo", "picture", "pics", "img", "photos", "images", "pictures"]
#     action_words = ["create", "made", "make", "send", "sent"]

#     found_keywords = [word for word in keywords if word in response.lower()]
#     found_actions = [action for action in action_words if action in response.lower()]

#     phrases = []
#     if found_keywords and found_actions:
#         phrases = [f"{action} {keyword}" for action in found_actions for keyword in found_keywords]

#     return phrases, found_keywords


# def get_combined_responses(queries, responses, user_email):
#     combined_responses = []
#     previous_data = fetch_user_data(user_email)

#     for query in queries:
#         query = query.strip()
#         if not query:
#             continue
#         intents_user = predict_intent(query, load_intents())
#         entities = extract_entities(query)
#         name = entities.get('name', previous_data.get('name', "there"))

#         sentiment_response = analyze_sentiment(query)
            
#         if is_image_request(query):
#             combined_responses.append(fetch_google_summary(query))
#         elif not intents_user:
#             combined_responses.append(fetch_google_summary(query))
#         elif sentiment_response:
#             combined_responses.append(sentiment_response)
#         elif "datetime" in intents_user:
#             current_datetime = datetime.datetime.now().strftime("%Y-%m-%d - %H:%M:%S")
#             combined_responses.append(random.choice(responses["datetime"]).replace("{datetime}", current_datetime))
#         elif "time" in intents_user:
#             current_time = datetime.datetime.now().strftime("%H:%M:%S")
#             combined_responses.append(random.choice(responses["time"]).replace("{time}", current_time))
#         elif "date" in intents_user:
#             current_time = datetime.datetime.now().strftime("%Y-%m-%d")
#             combined_responses.append(random.choice(responses["date"]).replace("{date}", current_time))
#         else:
#             for intent in intents_user:
#                 if intent in responses and responses[intent]:
#                     response_template = random.choice(responses[intent]).replace("{name}", name)
#                     combined_responses.append(response_template)

#     return " ".join(combined_responses)

# def is_image_request(query: str) -> bool:
#     query = query.lower()

#     action_words = {"create", "make", "made", "send", "sent"}
#     quantity_words = {"a", "an", "one", "many", "more"}
#     image_words = {"image", "images", "img", "photo", "photos", "picture", "pictures", "pics"}

#     words = query.split()
 
#     has_image_word = any(word in image_words for word in words) 
#     has_action_word = any(word in action_words for word in words) 
#     if has_image_word and not has_action_word:
#         return True
 
#     if has_image_word and has_action_word:
#         return True

#     return False

# def is_image_request(query: str) -> bool:
#     query = query.lower().strip()

#     valid_combinations = {
#         "image", "images", "img",
#         "photo", "photos", "pht", 
#         "picture", "pictures", "pics",
#         "Image", "Images", "Img",
#         "Photo", "Photos", "Pht",
#         "PICTURE", "PICTURES", "PICS",
#         "IMAGE", "IMAGES", "IMG",
#         "PHOTO", "PHOTOS"
#     }

#     action_words = {"create", "send", "sent", "made", "make",
#                     "Create", "Send", "Sent", "Made", "Make",
#                     "CREATE", "SEND", "SENT", "MADE", "MAKE",
#                     "a", "an", "one", "many", "Many", "MANY", "more", "More", "MORE"}

#     words = query.split()
 
#     contains_image_word = any(word in valid_combinations for word in words)
 
#     contains_action = any(word in action_words for word in words)
 
#     return contains_image_word or (contains_image_word and contains_action)
