from flask import Flask, render_template, request, session, redirect, url_for
from flask_session import Session
import re
import json
import random
from datetime import datetime, timedelta
import urllib.parse
import difflib
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = 'hotelbotsecretkey'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
Session(app)

# Mock Booking.com API configuration (in real scenario, use actual API key)
API_KEY = "mock_booking_api_key"
API_ENDPOINT = "https://api.mockbooking.com/v1/hotels"

def get_hotels_from_api(city, checkin, checkout, adults):
    """Fetch hotels from mock Booking.com API"""
    try:
        params = {
            "city": city,
            "checkin": checkin,
            "checkout": checkout,
            "adults": adults,
            "api_key": API_KEY
        }
        response = requests.get(API_ENDPOINT, params=params, timeout=5)
        return response.json().get('hotels', [])
    except Exception:
        # Fallback to local mock data if API fails
        with open("all_mock_hotels_updated.json", "r") as mf:
            return json.load(mf).get(city.lower(), [])

def parse_message(message):
    """Enhanced message parser with more flexibility"""
    city_match = re.search(r'(?:in|at|to)\s+([a-zA-Z\s]+)(?=\s|$)', message.lower())
    city = city_match.group(1).strip() if city_match else "goa"

    date_pattern = r'(\d{1,2})(?:[a-z]{0,2})?\s+([a-z]+)(?:\s+\d{4})?\s*(?:to|till|until|-)\s*(\d{1,2})(?:[a-z]{0,2})?\s+([a-z]+)'
    date_range_match = re.search(date_pattern, message.lower())
    days_stay_match = re.search(r'for (\d+)\s*(day|days|night|nights)', message.lower())
    
    months = {
        'jan': 'january', 'feb': 'february', 'mar': 'march', 'apr': 'april',
        'may': 'may', 'jun': 'june', 'jul': 'july', 'aug': 'august',
        'sep': 'september', 'oct': 'october', 'nov': 'november', 'dec': 'december'
    }

    if date_range_match:
        start_day = int(date_range_match.group(1))
        start_month = months.get(date_range_match.group(2)[:3], date_range_match.group(2))
        end_day = int(date_range_match.group(3))
        end_month = months.get(date_range_match.group(4)[:3], date_range_match.group(4))
        
        checkin = datetime.strptime(f"{start_day} {start_month} 2025", "%d %B %Y")
        checkout = datetime.strptime(f"{end_day} {end_month} 2025", "%d %B %Y")
    else:
        checkin = datetime.today()
        checkout = checkin + timedelta(days=int(days_stay_match.group(1)) if days_stay_match else 1)

    people_match = re.search(r'(\d+)\s*(?:adult|person|people|guest)s?', message.lower())
    adults = int(people_match.group(1)) if people_match else 1

    return city, checkin.strftime("%Y-%m-%d"), checkout.strftime("%Y-%m-%d"), adults

def generate_star_rating(rating):
    """Generate visual star rating"""
    full_stars = int(rating) if rating else 3
    return "⭐" * full_stars + "☆" * (5 - full_stars)

@app.route('/', methods=['GET'])
def index():
    if 'chat' not in session or not session['chat']:
        welcome_msg = """🌟 Welcome to HotelBot! 🌟
I can help you find amazing hotels worldwide! Simply tell me:
- Where you want to go
- When you're staying
- How many people
Try something like: "Hotels in Paris from 15 May to 20 May for 2 adults" """
        session['chat'] = [{'sender': 'bot', 'text': welcome_msg}]
    return render_template('index.html', chat_history=session['chat'])

@app.route('/chat', methods=['POST'])
def chat():
    message = request.form['message']
    session['chat'].append({'sender': 'user', 'text': message})

    # Handle special commands
    if "clear" in message.lower():
        session['chat'] = [{'sender': 'bot', 'text': 'Chat cleared! How can I assist you now? 🌟'}]
        return redirect(url_for('index'))

    city, checkin, checkout, adults = parse_message(message)
    
    # Get hotels from API
    all_hotels = get_hotels_from_api(city, checkin, checkout, adults)

    if "book" in message.lower() or "details" in message.lower():
        hotel_names = [hotel["hotel"]["name"].lower() for hotel in all_hotels]
        matches = difflib.get_close_matches(message.lower(), hotel_names, n=1, cutoff=0.6)
        if matches:
            selected_hotel = next(h for h in all_hotels if h["hotel"]["name"].lower() == matches[0])
            query = urllib.parse.quote_plus(f"{selected_hotel['hotel']['name']} {city}")
            
            bot_text = f"""🏨 *{selected_hotel['hotel']['name']}*
📍 Location: {selected_hotel['hotel'].get('address', 'Central ' + city.title())}
⭐ Rating: {generate_star_rating(selected_hotel['hotel'].get('rating'))}
💰 {selected_hotel['offers'][0]['price']['total']} {selected_hotel['offers'][0]['price']['currency']}/night
🔗 <a href='https://www.google.com/maps/search/{query}' target='_blank'>View on Map</a>
📞 <a href='tel:+1234567890'>Contact Hotel</a>
📝 Want to book? Just say "Book {selected_hotel['hotel']['name']}"!"""
            
            session['chat'].append({'sender': 'bot', 'text': bot_text})
            return redirect(url_for('index'))

    if not all_hotels:
        session['chat'].append({'sender': 'bot', 'text': f"😔 No hotels found in {city.title()}. Try another destination!"})
        return redirect(url_for('index'))

    # Select random hotels with better presentation
    valid_hotels = random.sample(all_hotels, min(len(all_hotels), 3))
    
    stay_duration = (datetime.strptime(checkout, "%Y-%m-%d") - datetime.strptime(checkin, "%Y-%m-%d")).days
    reply = f"""🌴 Hotel recommendations for {city.upper()}
📅 {checkin} to {checkout} ({stay_duration} nights) | 👥 {adults} adult{'s' if adults > 1 else ''}

Here are my top picks:"""

    for hotel in valid_hotels:
        price = hotel['offers'][0]['price']['total']
        currency = hotel['offers'][0]['price']['currency']
        total_price = price * stay_duration
        
        reply += f"""
🏨 *{hotel['hotel']['name']}*
⭐ {generate_star_rating(hotel['hotel'].get('rating'))}
💰 {price} {currency}/night | Total: {total_price} {currency}
🛏 {hotel['offers'][0]['room']['description']['text'][:100]}...
📍 {hotel['hotel'].get('address', 'Prime Location')}
🔎 Say "details {hotel['hotel']['name']}" for more info
----------------------------------------"""

    reply += """🌟 Type "book [hotel name]" to proceed with booking or ask for more options!"""
    session['chat'].append({'sender': 'bot', 'text': reply})
    return redirect(url_for('index'))

@app.route('/api/hotels', methods=['GET'])
def api_hotels():
    """Simple API endpoint for external access"""
    city = request.args.get('city', 'goa')
    checkin = request.args.get('checkin', datetime.today().strftime("%Y-%m-%d"))
    checkout = request.args.get('checkout', (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d"))
    adults = int(request.args.get('adults', 1))
    
    hotels = get_hotels_from_api(city, checkin, checkout, adults)
    return json.dumps({'hotels': hotels[:5], 'city': city, 'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)