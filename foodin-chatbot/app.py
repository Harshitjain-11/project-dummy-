"""
PRODUCTION Flask App - Fully Integrated with DINEaus
- Uses reservations table (not bookings)
- Full production schema support
- Intelligent parsing with fuzzy matching
- Bilingual support: English + Hinglish
- Multi-turn booking conversation
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime
import re
from difflib import get_close_matches
from dotenv import load_dotenv

# Import custom modules
try:
    from order_manager import OrderManager
except Exception as e:
    print(f"OrderManager import warning: {e}")
    OrderManager = None

try:
    from model_loader import ModelLoader
except Exception as e:
    print(f"ModelLoader import warning: {e}")
    ModelLoader = None

try:
    from entity_extractor import extract_booking, extract_order_id
except Exception as e:
    print(f"EntityExtractor import warning: {e}")
    extract_booking = None
    extract_order_id = None

try:
    from response_generator import choose_response
except Exception as e:
    print(f"ResponseGenerator import warning: {e}")
    choose_response = None

try:
    from chatbot.session_manager import (
        get_session, set_session, clear_temp_order,
        clear_booking_state, push_intent, reset_session
    )
    print("✅ Session manager loaded from chatbot package")
except Exception:
    try:
        from session_manager import (
            get_session, set_session, clear_temp_order,
            clear_booking_state, push_intent, reset_session
        )
        print("✅ Session manager loaded directly")
    except Exception as e:
        print(f"SessionManager import warning: {e}")
        get_session = None
        set_session = None
        clear_temp_order = None
        clear_booking_state = None
        push_intent = None
        reset_session = None

load_dotenv()

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASS', 'harshit@123'),
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'database': os.getenv('DB_NAME', 'college_practice'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'autocommit': False
}

# Word-to-Number Mapping (English + Hinglish)
WORD_TO_NUMBER = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'a': 1, 'an': 1,
    'ek': 1, 'do': 2, 'teen': 3, 'char': 4, 'paanch': 5,
    'chhe': 6, 'saat': 7, 'aath': 8, 'nau': 9, 'das': 10
}

# =============================================
# LANGUAGE DETECTION
# =============================================
_HINDI_MARKERS = {
    'kya', 'hai', 'hain', 'mujhe', 'chahiye', 'karo', 'bhai',
    'kal', 'aaj', 'log', 'kitne', 'mere', 'mera', 'nahi', 'nhi',
    'kar', 'krna', 'krdo', 'krdiya', 'batao', 'wala', 'wali',
    'smjh', 'hua', 'thi', 'tha', 'hoga', 'kab', 'kaise', 'kyun',
    'kaun', 'yahan', 'wahan', 'abhi', 'phir', 'bolo', 'dedo',
    'chahte', 'ana', 'aana', 'jao', 'leke', 'dena', 'lena',
    'theek', 'accha', 'sahi', 'nahi', 'bilkul', 'zaroor',
    'ek', 'do', 'teen', 'char', 'paanch', 'log', 'baje',
    'raat', 'subah', 'sham', 'kal', 'parso', 'aaj', 'table',
    'kitna', 'kitni', 'order', 'karna', 'book', 'dekho', 'dikhao'
}

def detect_language(text: str) -> str:
    """
    Returns 'hi' if message has Hinglish/Hindi words, else 'en'.
    Saves detected language in session for consistency across turns.
    """
    words = set(text.lower().split())
    hindi_count = len(words & _HINDI_MARKERS)
    return 'hi' if hindi_count >= 1 else 'en'

def get_lang(session: dict, message: str) -> str:
    """
    Get language — detect from message but remember first detection
    so mid-conversation it doesn't flip.
    """
    if not session.get("lang"):
        session["lang"] = detect_language(message)
    return session["lang"]

# =============================================
# BILINGUAL RESPONSE TEMPLATES
# =============================================
RESPONSES = {
    "greeting": {
        "en": "Hi! 👋 I'm DineBot.\n\n💬 Type **'view restaurants'** to start ordering!",
        "hi": "Namaste! 👋 Main DineBot hoon.\n\n💬 **'view restaurants'** type karo aur order shuru karo!"
    },
    "goodbye": {
        "en": "Goodbye! 👋 Have a great day!",
        "hi": "Alvida! 👋 Milte hain phir!"
    },
    "thanks": {
        "en": "You're welcome! 😊",
        "hi": "Koi baat nahi! 😊 Khushi hui help karke!"
    },
    "no_restaurant": {
        "en": "⚠️ Please select a restaurant first.\n\n💬 Type **'view restaurants'**",
        "hi": "⚠️ Pehle restaurant select karo.\n\n💬 **'view restaurants'** type karo"
    },
    "empty_cart": {
        "en": "🛒 Your cart is empty!\n\n💬 Type **'menu'** to see items.",
        "hi": "🛒 Cart khali hai!\n\n💬 **'menu'** type karo items dekhne ke liye."
    },
    "item_not_found": {
        "en": "🤔 Item not found.\n\n💡 Type **'menu'** to see what's available.",
        "hi": "🤔 Item nahi mila.\n\n💡 **'menu'** type karo available items dekhne ke liye."
    },
    "fallback": {
        "en": "🤔 I didn't quite get that.\n\nYou can:\n• Order food\n• Book a table\n• Track your order\n• View restaurants",
        "hi": "🤔 Samajh nahi aaya.\n\nYeh try karo:\n• Order food\n• Table book karo\n• Order track karo\n• Restaurants dekho"
    },
    "no_order": {
        "en": "No recent order found. 🤷\n\nTry: **'track 123'**",
        "hi": "Koi recent order nahi mila. 🤷\n\nTry karo: **'track 123'**"
    }
}

def r(key: str, lang: str) -> str:
    """Shorthand to get bilingual response."""
    return RESPONSES.get(key, {}).get(lang, RESPONSES.get(key, {}).get('en', ''))

# =============================================
# BILINGUAL BOOKING PROMPTS
# =============================================
def booking_ask(field: str, lang: str) -> str:
    msgs = {
        "people": {
            "en": "👥 How many people will be joining?\n\n📝 Example: **'4 people'** or **'table for 2'**",
            "hi": "👥 Kitne logon ke liye table chahiye?\n\n📝 Example: **'4 log'** ya **'2 ke liye'**"
        },
        "date": {
            "en": "📅 Which date are you planning to visit?\n\n📝 Example: **'tomorrow'** or **'today'**",
            "hi": "📅 Kaunsi date ko aana chahte ho?\n\n📝 Example: **'kal'** ya **'aaj'**"
        },
        "time": {
            "en": "🕐 What time would you like the table?\n\n📝 Example: **'7pm'** or **'8:30pm'**",
            "hi": "🕐 Kis time pe aana chahte ho?\n\n📝 Example: **'7 baje'** ya **'8:30pm'**"
        }
    }
    return msgs.get(field, {}).get(lang, msgs.get(field, {}).get('en', ''))

# =============================================
# ORDER MANAGER INIT
# =============================================
om = None
if OrderManager is not None:
    try:
        om = OrderManager(DB_CONFIG)
        print("✅ OrderManager initialized with MySQL")
    except Exception as e:
        print("Warning: Failed to initialize MySQL OrderManager:", e)
        om = None

class _InMemoryOrderManager:
    def __init__(self):
        self.orders = {}
        self.reservations = {}
        self.order_counter = 1000
        self.reservation_counter = 1000
        self.restaurants = [{"id": 1, "name": "Demo Restaurant", "location": "Demo"}]
        self.menus = {1: [{"item_name": "pizza", "price": 250.0}, {"item_name": "burger", "price": 120.0}]}

    def get_restaurants(self):
        return self.restaurants

    def get_menu(self, restaurant_id):
        return self.menus.get(restaurant_id, [])

    def add_order(self, user_id, restaurant_id, items, total_price, address_id=None):
        order_id = self.order_counter
        self.order_counter += 1
        self.orders[order_id] = {
            "id": order_id, "user_id": user_id, "restaurant_id": restaurant_id,
            "items": items, "total_price": total_price, "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        return order_id

    def confirm_order(self, order_id):
        if order_id in self.orders:
            self.orders[order_id]["status"] = "accepted"
            return True
        return False

    def track_order(self, order_id):
        return self.orders.get(order_id)

    def cancel_order(self, order_id, reason=None):
        if order_id in self.orders:
            self.orders[order_id]["status"] = "cancelled"
            return True
        return False

    def book_table(self, user_id, restaurant_id, customer_name, customer_phone,
                   booking_date, time_slot, guests):
        reservation_id = self.reservation_counter
        self.reservation_counter += 1
        self.reservations[reservation_id] = {
            "id": reservation_id, "restaurant_id": restaurant_id,
            "customer_name": customer_name, "customer_phone": customer_phone,
            "date": booking_date, "time_slot": time_slot, "guests": guests,
            "status": "pending", "created_at": datetime.utcnow().isoformat()
        }
        return reservation_id

if om is None:
    print("⚠️ Using in-memory OrderManager fallback")
    om = _InMemoryOrderManager()

# =============================================
# ML MODEL INIT
# =============================================
ml_model = None
if ModelLoader is not None:
    try:
        ml_model = ModelLoader()
        print("✅ ML Model loaded")
    except Exception as e:
        print(f"⚠️ ML model load failed: {e}")

# =============================================
# FALLBACK SESSION MANAGER (if import fails)
# =============================================
if get_session is None:
    _fallback_sessions = {}

    def get_session(user_id):
        if user_id not in _fallback_sessions:
            _fallback_sessions[user_id] = {
                "last_intent": None,
                "temp_order": {"items": []},
                "last_bot_msg": None,
                "active_restaurant": None,
                "last_order_id": None,
                "booking_state": {},
                "context_stack": [],
                "lang": None,
                "created_at": datetime.utcnow().isoformat()
            }
        else:
            s = _fallback_sessions[user_id]
            if not isinstance(s.get("temp_order"), dict):
                s["temp_order"] = {"items": []}
            if "items" not in s["temp_order"]:
                s["temp_order"]["items"] = []
            if "booking_state" not in s:
                s["booking_state"] = {}
            if "lang" not in s:
                s["lang"] = None
        return _fallback_sessions[user_id]

    def set_session(user_id, data):
        _fallback_sessions[user_id] = data
        return data

    def clear_temp_order(user_id):
        s = get_session(user_id)
        s["temp_order"] = {"items": []}
        s["last_intent"] = None
        return s

    def clear_booking_state(user_id):
        s = get_session(user_id)
        s["booking_state"] = {}
        return s

    def push_intent(user_id, intent):
        s = get_session(user_id)
        stack = s.get("context_stack", [])
        stack.append(intent)
        if len(stack) > 3:
            stack = stack[-3:]
        s["context_stack"] = stack
        s["last_intent"] = intent

    def reset_session(user_id):
        _fallback_sessions[user_id] = get_session.__wrapped__(user_id) if hasattr(get_session, '__wrapped__') else {}
        return get_session(user_id)

# =============================================
# PARSING UTILITIES
# =============================================
def normalize_quantity(qty_str):
    qty_str = qty_str.lower().strip()
    if qty_str in WORD_TO_NUMBER:
        return WORD_TO_NUMBER[qty_str]
    try:
        return int(qty_str)
    except:
        return 1

def fuzzy_match_item(user_input, menu_list, cutoff=0.6):
    if not menu_list:
        return None, 0
    user_input = user_input.lower().strip()
    if user_input in menu_list:
        return user_input, 1.0
    matches = get_close_matches(user_input, menu_list, n=1, cutoff=cutoff)
    if matches:
        return matches[0], 0.8
    return None, 0

def extract_items_from_message(message, menu_list, price_map):
    items = []
    message_lower = message.lower()

    # Pattern: "2 pizza", "ek burger", "do samosa"
    qty_words = '|'.join(WORD_TO_NUMBER.keys())
    qty_pattern = rf'\b(\d+|{qty_words})\s+(?:x\s+)?(\w+(?:\s+\w+){{0,2}})'

    for match in re.finditer(qty_pattern, message_lower):
        qty_str = match.group(1)
        potential_item = match.group(2).strip()
        matched_item, confidence = fuzzy_match_item(potential_item, menu_list)
        if matched_item and confidence >= 0.6:
            qty = normalize_quantity(qty_str)
            items.append({
                "name": matched_item,
                "qty": qty,
                "price": price_map.get(matched_item, 0)
            })

    # Direct menu item name match
    if not items:
        for item_name in menu_list:
            pattern = r'\b' + re.escape(item_name) + r'\b'
            if re.search(pattern, message_lower):
                items.append({
                    "name": item_name,
                    "qty": 1,
                    "price": price_map[item_name]
                })

    # Single word fuzzy fallback
    if not items:
        words = message_lower.split()
        for word in words:
            if len(word) > 2:
                matched_item, confidence = fuzzy_match_item(word, menu_list)
                if matched_item and confidence >= 0.7:
                    items.append({
                        "name": matched_item,
                        "qty": 1,
                        "price": price_map[matched_item]
                    })
                    break

    return items

def suggest_close_items(user_input, menu_list, n=3):
    words = user_input.lower().split()
    suggestions = set()
    for word in words:
        if len(word) > 2:
            matches = get_close_matches(word, menu_list, n=n, cutoff=0.5)
            suggestions.update(matches)
    return list(suggestions)[:n]

def get_restaurant_menu(restaurant_id):
    try:
        menu_rows = om.get_menu(restaurant_id)
        if not menu_rows:
            return None, None
        menu_list = [row["item_name"].lower() for row in menu_rows]
        price_map = {row["item_name"].lower(): float(row["price"]) for row in menu_rows}
        return menu_list, price_map
    except Exception as e:
        print(f"Error fetching menu: {e}")
        return None, None

# =============================================
# INTENT DETECTION
# =============================================
def predict_intent(text):
    if ml_model:
        try:
            results = ml_model.predict([text])
            intent, confidence = results[0]
            if confidence > 0.35:
                return intent
        except Exception as e:
            print(f"ML error: {e}")
    return simple_intent_parser(text)

def simple_intent_parser(text: str) -> str:
    """
    Regex fallback — covers English AND Hinglish patterns.
    Order matters: more specific patterns first.
    """
    t = text.lower().strip()

    # Greeting
    if re.search(r'\b(hi|hello|hey|namaste|hlo|hii|sup|howdy|yo)\b', t):
        return "greeting"

    # Goodbye
    if re.search(r'\b(bye|goodbye|see you|alvida|chal bye|milte hain|tata)\b', t):
        return "goodbye"

    # Thanks
    if re.search(r'\b(thanks|thank you|thx|shukriya|dhanyavaad|ty)\b', t):
        return "thanks"

    # Confirm order
    if re.search(r'\b(confirm|place order|checkout|finalize|order karo|order kar do|place karo|haan order|yes order)\b', t):
        return "confirm_order"

    # Cancel order
    if re.search(r'\b(cancel order|cancel kar|order cancel|nahi chahiye order|order mat|cancel karo)\b', t):
        return "cancel_order"

    # Table booking — Hinglish + English
    if re.search(r'\b(book|reserve|table|seat|reservation|baithna|dining|dine in)\b', t):
        return "book_table"
    if re.search(r'\b(table book|table chahiye|seat chahiye|book karna|reserve karna|baith|jagah)\b', t):
        return "book_table"

    # Remove item
    if re.search(r'\b(remove|delete|hata|nikal|cancel item|mat chahiye|nahi chahiye)\b', t):
        return "remove_item"

    # Track order
    if re.search(r'\b(track|where is|order status|kahan hai|status batao|order kahan|track karo)\b', t):
        return "track_order"

    # Menu
    if re.search(r'\b(menu|show menu|items|kya milta|kya hai|food list|dikhao|dekh|kha sakte)\b', t):
        return "menu"

    # Change restaurant
    if re.search(r'\b(change|switch|different|badlo|dusra)\s*(restaurant|place|jagah)?\b', t):
        return "change_restaurant"

    # Order item — English + Hinglish
    if re.search(r'\b(add|order|want|get me|i want|i need|give me|chahiye|de do|lena|mangwa|dena|bhejdo)\b', t):
        return "order_item"

    # Number-only → could be restaurant select or order item — context handled in chat_handler
    if re.search(r'^\s*\d+\s*$', t):
        return "order_item"

    # Number words
    qty_words = '|'.join(WORD_TO_NUMBER.keys())
    if re.search(rf'\b({qty_words})\b', t):
        return "order_item"

    return "fallback"

# =============================================
# ROUTES
# =============================================
@app.route("/")
def home():
    return "DineBot backend running ✅"

@app.route("/chat", methods=["POST"])
def chat_handler():
    data = request.get_json() or {}
    user_id = data.get("user_id", "anonymous")
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"reply": "Please type something! 😊"}), 200

    session = get_session(user_id)

    # Detect and remember language
    lang = get_lang(session, message)

    # -----------------------------------------------
    # RESTAURANT LIST — view/change restaurants
    # -----------------------------------------------
    if re.search(r'\b(change|switch|different|badlo|dusra)\s*(restaurant|place)?\b', message.lower()) or \
       re.search(r'\b(view restaurants?|show restaurants?|restaurants dikhao|restaurants batao)\b', message.lower()) or \
       "view restaurant" in message.lower():
        try:
            rows = om.get_restaurants()
            if not rows:
                bot_response = "No restaurants available." if lang == 'en' else "Koi restaurant available nahi hai."
            else:
                if lang == 'en':
                    text = "🍽️ **Available Restaurants:**\n\n"
                    for r in rows:
                        text += f"{r['id']}. {r['name']} ({r['location']})\n"
                    text += "\n💬 Type the restaurant number to select."
                else:
                    text = "🍽️ **Restaurants ki list:**\n\n"
                    for r in rows:
                        text += f"{r['id']}. {r['name']} ({r['location']})\n"
                    text += "\n💬 Restaurant ka number type karo select karne ke liye."
                bot_response = text
                session["active_restaurant"] = None
        except Exception as e:
            bot_response = f"Error: {str(e)}"

        set_session(user_id, session)
        return jsonify({"reply": bot_response, "intent": "view_restaurants", "speak": False, "speech_text": None}), 200

    # -----------------------------------------------
    # RESTAURANT SELECTION — user types a number
    # -----------------------------------------------
    if message.isdigit() and not session.get("active_restaurant"):
        restaurant_id = int(message)
        try:
            restaurants = om.get_restaurants()
            r = next((x for x in restaurants if x['id'] == restaurant_id), None)
            if r:
                session["active_restaurant"] = r["id"]
                set_session(user_id, session)
                if lang == 'en':
                    bot_response = f"✅ Selected **{r['name']}**!\n\n💬 Type 'menu' to see items."
                else:
                    bot_response = f"✅ **{r['name']}** select ho gaya!\n\n💬 'menu' type karo items dekhne ke liye."
            else:
                bot_response = "❌ Invalid ID. Type 'view restaurants'." if lang == 'en' else "❌ Galat number. 'view restaurants' type karo."
        except Exception as e:
            bot_response = f"Error: {str(e)}"

        return jsonify({"reply": bot_response, "intent": "select_restaurant", "speak": False, "speech_text": None}), 200

    # -----------------------------------------------
    # INTENT DETECTION
    # -----------------------------------------------
    intent = predict_intent(message)
    push_intent(user_id, intent)

    bot_response = None

    # -----------------------------------------------
    # GREETING
    # -----------------------------------------------
    if intent == "greeting":
        bot_response = r("greeting", lang)

    # -----------------------------------------------
    # GOODBYE
    # -----------------------------------------------
    elif intent == "goodbye":
        bot_response = r("goodbye", lang)
        clear_temp_order(user_id)

    # -----------------------------------------------
    # THANKS
    # -----------------------------------------------
    elif intent == "thanks":
        bot_response = r("thanks", lang)

    # -----------------------------------------------
    # MENU
    # -----------------------------------------------
    elif intent == "menu":
        active_restaurant = session.get("active_restaurant")
        if not active_restaurant:
            bot_response = r("no_restaurant", lang)
        else:
            menu_list, price_map = get_restaurant_menu(active_restaurant)
            if not menu_list:
                bot_response = "No menu items found." if lang == 'en' else "Menu abhi available nahi hai."
            else:
                if lang == 'en':
                    menu_text = "🍽️ **Menu:**\n\n"
                    for idx, item in enumerate(menu_list, 1):
                        menu_text += f"{idx}. {item.title()} - ₹{price_map[item]}\n"
                    menu_text += "\n💬 What would you like?\n💡 Try: **'2 pizzas and a coke'**"
                else:
                    menu_text = "🍽️ **Menu:**\n\n"
                    for idx, item in enumerate(menu_list, 1):
                        menu_text += f"{idx}. {item.title()} - ₹{price_map[item]}\n"
                    menu_text += "\n💬 Kya loge?\n💡 Try karo: **'2 pizza aur ek coke'**"
                bot_response = menu_text

    # -----------------------------------------------
    # ORDER ITEM / NEW ORDER / FALLBACK WITH ITEM
    # -----------------------------------------------
    elif intent in ("new_order", "order_item", "fallback"):
        active_restaurant = session.get("active_restaurant")
        if not active_restaurant:
            if intent == "fallback":
                bot_response = r("fallback", lang)
            else:
                bot_response = r("no_restaurant", lang)
        else:
            menu_list, price_map = get_restaurant_menu(active_restaurant)
            if not menu_list:
                bot_response = "No menu available." if lang == 'en' else "Menu available nahi hai."
            else:
                items = extract_items_from_message(message, menu_list, price_map)
                if items:
                    temp_items = session["temp_order"].get("items", [])
                    for item in items:
                        existing = next((i for i in temp_items if i["name"] == item["name"]), None)
                        if existing:
                            existing["qty"] += item["qty"]
                        else:
                            temp_items.append(item)
                    session["temp_order"]["items"] = temp_items

                    cart_summary = "\n".join([
                        f"• {i['qty']}x {i['name'].title()} - ₹{i['price'] * i['qty']}"
                        for i in temp_items
                    ])
                    total = sum(i['price'] * i['qty'] for i in temp_items)

                    if lang == 'en':
                        bot_response = (
                            f"✅ Added to cart!\n\n**Cart:**\n{cart_summary}\n\n"
                            f"**Total: ₹{total}**\n\n💬 Say **'confirm order'** to place!"
                        )
                    else:
                        bot_response = (
                            f"✅ Cart mein add ho gaya!\n\n**Cart:**\n{cart_summary}\n\n"
                            f"**Total: ₹{total}**\n\n💬 **'confirm order'** bolo order place karne ke liye!"
                        )
                else:
                    suggestions = suggest_close_items(message, menu_list)
                    if suggestions:
                        sugg_text = ", ".join([s.title() for s in suggestions])
                        if lang == 'en':
                            bot_response = f"🤔 Item not found.\n\n💡 Did you mean: **{sugg_text}**?"
                        else:
                            bot_response = f"🤔 Item nahi mila.\n\n💡 Kya yeh chahte the: **{sugg_text}**?"
                    else:
                        bot_response = r("item_not_found", lang)

    # -----------------------------------------------
    # REMOVE ITEM
    # -----------------------------------------------
    elif intent == "remove_item":
        temp_items = session["temp_order"].get("items", [])
        if not temp_items:
            bot_response = r("empty_cart", lang)
        else:
            active_restaurant = session.get("active_restaurant")
            if not active_restaurant:
                clear_temp_order(user_id)
                bot_response = "✅ Cart cleared! 🛒" if lang == 'en' else "✅ Cart saaf ho gaya! 🛒"
            else:
                menu_list, _ = get_restaurant_menu(active_restaurant)
                if not menu_list:
                    clear_temp_order(user_id)
                    bot_response = "✅ Cart cleared! 🛒" if lang == 'en' else "✅ Cart saaf ho gaya! 🛒"
                else:
                    items_to_remove = []
                    for word in message.lower().split():
                        if len(word) > 2:
                            matched, conf = fuzzy_match_item(word, menu_list)
                            if matched and conf >= 0.6:
                                items_to_remove.append(matched)

                    if items_to_remove:
                        removed = []
                        for item_name in items_to_remove:
                            before = len(temp_items)
                            temp_items = [i for i in temp_items if i["name"].lower() != item_name.lower()]
                            if len(temp_items) < before:
                                removed.append(item_name.title())

                        session["temp_order"]["items"] = temp_items

                        if temp_items:
                            cart_summary = "\n".join([
                                f"• {i['qty']}x {i['name'].title()} - ₹{i['price'] * i['qty']}"
                                for i in temp_items
                            ])
                            total = sum(i['price'] * i['qty'] for i in temp_items)
                            if lang == 'en':
                                bot_response = f"✅ Removed {', '.join(removed)}.\n\n**Cart:**\n{cart_summary}\n\n**Total: ₹{total}**"
                            else:
                                bot_response = f"✅ {', '.join(removed)} hata diya.\n\n**Cart:**\n{cart_summary}\n\n**Total: ₹{total}**"
                        else:
                            bot_response = "✅ Cart is now empty! 🛒" if lang == 'en' else "✅ Cart bilkul khali hai! 🛒"
                            clear_temp_order(user_id)
                    else:
                        # Could not find item — ask which one
                        item_names = [i['name'].title() for i in temp_items]
                        if lang == 'en':
                            bot_response = f"🤔 Which item to remove?\n\nYour cart: {', '.join(item_names)}"
                        else:
                            bot_response = f"🤔 Kaun sa item hatana hai?\n\nCart mein hai: {', '.join(item_names)}"

    # -----------------------------------------------
    # CONFIRM ORDER
    # -----------------------------------------------
    elif intent == "confirm_order":
        temp_items = session["temp_order"].get("items", [])
        active_restaurant = session.get("active_restaurant")

        if not temp_items:
            bot_response = r("empty_cart", lang)
        elif not active_restaurant:
            bot_response = r("no_restaurant", lang)
        else:
            try:
                total_price = sum(i["qty"] * i["price"] for i in temp_items)
                numeric_user_id = (
                    1 if user_id in ("anonymous", "") or not user_id
                    else int(user_id) if str(user_id).isdigit()
                    else 1
                )

                order_id = om.add_order(numeric_user_id, active_restaurant, temp_items, total_price)
                om.confirm_order(order_id)

                items_text = "\n".join([f"• {i['qty']}x {i['name'].title()}" for i in temp_items])
                clear_temp_order(user_id)
                session["last_order_id"] = order_id

                if lang == 'en':
                    bot_response = (
                        f"🎉 **Order Confirmed!**\n\n"
                        f"📋 Order ID: **{order_id}**\n\n"
                        f"**Items:**\n{items_text}\n\n"
                        f"💰 **Total: ₹{total_price}**\n\n"
                        f"⏱️ Ready in 30-40 minutes!\n\n"
                        f"📱 Track: **'track {order_id}'**"
                    )
                else:
                    bot_response = (
                        f"🎉 **Order Confirm Ho Gaya!**\n\n"
                        f"📋 Order ID: **{order_id}**\n\n"
                        f"**Items:**\n{items_text}\n\n"
                        f"💰 **Total: ₹{total_price}**\n\n"
                        f"⏱️ 30-40 minute mein ready hoga!\n\n"
                        f"📱 Track karo: **'track {order_id}'**"
                    )
            except Exception as e:
                print(f"❌ Order error: {e}")
                import traceback
                traceback.print_exc()
                bot_response = f"❌ Error: {str(e)}"

    # -----------------------------------------------
    # TRACK ORDER
    # -----------------------------------------------
    elif intent == "track_order":
        order_id = None
        if extract_order_id:
            order_id = extract_order_id(message)
        else:
            match = re.search(r'\b(\d{3,8})\b', message)
            if match:
                try:
                    order_id = int(match.group(1))
                except:
                    order_id = None

        if not order_id and session.get("last_order_id"):
            order_id = session["last_order_id"]

        if order_id:
            try:
                order = om.track_order(order_id)
                if order:
                    items_text = "\n".join([
                        f"• {i['qty']}x {i['name'].title()}"
                        for i in order.get("items", [])
                    ])
                    status_emoji = {
                        "pending": "⏳", "accepted": "✅", "preparing": "👨‍🍳",
                        "ready": "🔔", "out_for_delivery": "🚗", "picked_up": "📦",
                        "delivered": "🎉", "completed": "✔️", "rejected": "❌", "cancelled": "❌"
                    }.get(order['status'], "📦")
                    total = order.get('total_price', order.get('total', 0))

                    if lang == 'en':
                        bot_response = (
                            f"📦 **Order #{order_id}**\n\n"
                            f"{status_emoji} Status: **{order['status'].upper()}**\n\n"
                            f"**Items:**\n{items_text}\n\n"
                            f"💰 Total: ₹{total}"
                        )
                    else:
                        bot_response = (
                            f"📦 **Order #{order_id}**\n\n"
                            f"{status_emoji} Status: **{order['status'].upper()}**\n\n"
                            f"**Items:**\n{items_text}\n\n"
                            f"💰 Total: ₹{total}"
                        )
                else:
                    bot_response = f"❌ Order #{order_id} not found." if lang == 'en' else f"❌ Order #{order_id} nahi mila."
            except Exception as e:
                bot_response = f"❌ Error: {str(e)}"
        else:
            if lang == 'en':
                bot_response = "📝 Please provide order ID.\n\nExample: **'track 1023'**"
            else:
                bot_response = "📝 Order ID batao.\n\nExample: **'track 1023'**"

    # -----------------------------------------------
    # CANCEL ORDER
    # -----------------------------------------------
    elif intent == "cancel_order":
        if session.get("last_order_id"):
            try:
                order_id = session["last_order_id"]
                success = om.cancel_order(order_id)
                if success:
                    session["last_order_id"] = None
                    bot_response = f"❌ Order #{order_id} cancelled." if lang == 'en' else f"❌ Order #{order_id} cancel ho gaya."
                else:
                    bot_response = f"⚠️ Cannot cancel #{order_id}." if lang == 'en' else f"⚠️ #{order_id} cancel nahi ho sakta."
            except Exception as e:
                bot_response = f"❌ Error: {str(e)}"
        else:
            bot_response = r("no_order", lang)

    # -----------------------------------------------
    # BOOK TABLE — Multi-turn, bilingual
    # -----------------------------------------------
    elif intent == "book_table":
        booking_info = {}
        if extract_booking:
            booking_info = extract_booking(message)

        # Merge new info with saved state (multi-turn)
        saved = session.get("booking_state", {})
        saved["people"] = booking_info.get("people") or saved.get("people")
        saved["time"]   = booking_info.get("time")   or saved.get("time")
        saved["date"]   = booking_info.get("date")   or saved.get("date")
        session["booking_state"] = saved

        people       = saved.get("people")
        time_slot    = saved.get("time")
        booking_date = saved.get("date")
        active_restaurant = session.get("active_restaurant", 1)

        if people and time_slot and booking_date:
            try:
                numeric_user_id = (
                    1 if user_id in ("anonymous", "")
                    else int(user_id) if str(user_id).isdigit()
                    else 1
                )
                customer_name  = f"User{numeric_user_id}"
                customer_phone = "1234567890"

                booking_id = om.book_table(
                    numeric_user_id, active_restaurant,
                    customer_name, customer_phone,
                    booking_date, time_slot, people
                )

                # Clear booking state after success
                session["booking_state"] = {}

                if lang == 'en':
                    bot_response = (
                        f"✅ **Table Booked!**\n\n"
                        f"🆔 Booking ID: {booking_id}\n"
                        f"📅 Date: {booking_date}\n"
                        f"🕐 Time: {time_slot}\n"
                        f"👥 Guests: {people}\n\n"
                        f"See you there! 🎉"
                    )
                else:
                    bot_response = (
                        f"✅ **Table Book Ho Gaya!**\n\n"
                        f"🆔 Booking ID: {booking_id}\n"
                        f"📅 Date: {booking_date}\n"
                        f"🕐 Time: {time_slot}\n"
                        f"👥 Guests: {people}\n\n"
                        f"Milte hain wahan! 🎉"
                    )
            except Exception as e:
                print(f"❌ Booking error: {e}")
                bot_response = f"❌ Error: {str(e)}"
        else:
            # Ask for missing fields one by one
            if not people:
                bot_response = booking_ask("people", lang)
            elif not booking_date:
                bot_response = booking_ask("date", lang)
            elif not time_slot:
                bot_response = booking_ask("time", lang)

    # -----------------------------------------------
    # DEFAULT FALLBACK
    # -----------------------------------------------
    if not bot_response:
        bot_response = r("fallback", lang)

    session["last_bot_msg"] = bot_response
    set_session(user_id, session)

    SPEAK_INTENTS = {"confirm_order", "track_order", "book_table", "cancel_order"}
    should_speak = intent in SPEAK_INTENTS

    speech_text = None
    if intent == "confirm_order":
        speech_text = "Order confirmed. Ready in 30 minutes."
    elif intent == "track_order":
        speech_text = "Here is your order status."
    elif intent == "book_table":
        speech_text = "Table booked successfully."
    elif intent == "cancel_order":
        speech_text = "Order cancelled."

    return jsonify({
        "reply": bot_response,
        "intent": intent,
        "speak": should_speak,
        "speech_text": speech_text
    }), 200

@app.route("/reset", methods=["POST"])
def reset_chat():
    """Reset session — called when user clicks reset button."""
    data = request.get_json() or {}
    user_id = data.get("user_id", "anonymous")
    reset_session(user_id)
    return jsonify({"status": "reset", "user_id": user_id}), 200

@app.route('/health', methods=['GET'])
def health():
    db_type = 'MySQL' if (OrderManager is not None and isinstance(om, OrderManager)) else 'In-Memory'
    return jsonify({
        'status': 'healthy',
        'ml_model': ml_model is not None,
        'order_manager': om is not None,
        'database': db_type,
        'timestamp': datetime.utcnow().isoformat()
    }), 200

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', '1') == '1'
    port  = int(os.getenv('PORT', 5000))
    print(f"\n🚀 DineBot Server Starting...")
    print(f"📊 ML Model: {'✅' if ml_model else '⚠️ Regex fallback'}")
    print(f"💾 Database: {'✅ MySQL' if (OrderManager is not None and isinstance(om, OrderManager)) else '⚠️ In-Memory'}")
    print(f"🌐 Port: {port}\n")
    app.run(host='0.0.0.0', port=port, debug=debug)