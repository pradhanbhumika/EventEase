"""
EventEase - Event Ticket Booking System
A beginner-friendly Flask + SQLite project.

Install:  pip install -r requirements.txt
Run with: python app.py
Then open: http://127.0.0.1:5000

Default admin login (created automatically):
    Email:    admin@eventease.com
    Password: admin123
"""

import base64
import io
import math
import os
import re
import secrets
import sqlite3
import string
from datetime import date, datetime, timedelta
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

# The QR code library is optional at start-up so the site still opens if it is
# missing (the ticket then shows a friendly message instead of a QR image).
try:
    import qrcode
except ImportError:
    qrcode = None

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "eventease-dev-secret-change-me")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "eventease.db")

SEATS_PER_ROW = 10          # every row in the seat map has up to 10 seats
MAX_SEATS_PER_BOOKING = 6   # a user can book at most 6 seats at once
FEE_RATE = 0.05             # 5% convenience fee
CATEGORIES = ["Concert", "Conference", "Sports", "Comedy",
              "Festival", "Workshop", "Theatre"]
BANKS = ["State Bank of India", "HDFC Bank", "ICICI Bank",
         "Axis Bank", "Kotak Mahindra Bank", "Bank of Baroda"]
DEFAULT_IMAGE = ("https://images.unsplash.com/photo-1501281668745-f7f57925c3b4"
                 "?auto=format&fit=crop&w=1000&q=60")

# Filter and sort choices for the Events page: (value in the URL, label shown)
PRICE_FILTERS = [
    ("under_500", "Under ₹500"),
    ("500_1000", "₹500 – ₹1,000"),
    ("1000_2500", "₹1,000 – ₹2,500"),
    ("2500_plus", "₹2,500+"),
]
DATE_FILTERS = [
    ("today", "Today"),
    ("week", "This Week"),      # today + the next 6 days
    ("month", "This Month"),    # today + the next 29 days
]
SORT_OPTIONS = [
    ("date", "Date: Soonest"),
    ("date_desc", "Date: Latest"),
    ("price_low", "Price: Low to High"),
    ("price_high", "Price: High to Low"),
    ("name", "Name: A–Z"),
]
SORT_SQL = {
    "date": "e.event_date ASC, e.event_time ASC",
    "date_desc": "e.event_date DESC, e.event_time DESC",
    "price_low": "e.price ASC, e.event_date ASC",
    "price_high": "e.price DESC, e.event_date ASC",
    "name": "e.title COLLATE NOCASE ASC",
}

# Used only to show "Mumbai, Maharashtra" on event cards.
# A city that is not in this list is simply shown by its own name.
CITY_STATES = {
    "Mumbai": "Maharashtra", "Pune": "Maharashtra", "Navi Mumbai": "Maharashtra",
    "Thane": "Maharashtra", "Nagpur": "Maharashtra", "Nashik": "Maharashtra",
    "Bengaluru": "Karnataka", "Hyderabad": "Telangana", "Chennai": "Tamil Nadu",
    "Delhi": "Delhi", "Kolkata": "West Bengal", "Ahmedabad": "Gujarat",
    "Jaipur": "Rajasthan", "Goa": "Goa",
}

# Seat categories. The event price is the "Standard" price.
# VIP seats cost 1.5x and Premium seats cost 1.25x.
TIER_INFO = {
    "vip": {"label": "VIP", "multiplier": 1.5},
    "premium": {"label": "Premium", "multiplier": 1.25},
    "standard": {"label": "Standard", "multiplier": 1.0},
}
TIER_ORDER = ["vip", "premium", "standard"]

# Card used to test a declined payment (passes the card-number check)
DECLINE_TEST_CARD = "4000000000000002"

# Characters used in booking IDs (no 0/O or 1/I so they are easy to read)
CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
UPI_RE = re.compile(r"^[\w.\-]{2,}@[A-Za-z]{2,}$")
URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Sample events (added automatically the first time the database is created)
# ---------------------------------------------------------------------------
_IMG_SUFFIX = "?auto=format&fit=crop&w=1000&q=60"
_UNSPLASH = "https://images.unsplash.com/photo-"

# One picture per category. Admins can change any event's image URL later.
SAMPLE_IMAGES = {
    "Concert": _UNSPLASH + "1459749411175-04bf5292ceea" + _IMG_SUFFIX,
    "Conference": _UNSPLASH + "1540575467063-178a50c2df87" + _IMG_SUFFIX,
    "Sports": _UNSPLASH + "1505373877841-8d25f7d46678" + _IMG_SUFFIX,
    "Comedy": _UNSPLASH + "1492684223066-81342ee5ff30" + _IMG_SUFFIX,
    "Festival": _UNSPLASH + "1533174072545-7a4b6ad7a6c3" + _IMG_SUFFIX,
    "Workshop": _UNSPLASH + "1540575467063-178a50c2df87" + _IMG_SUFFIX,
    "Theatre": DEFAULT_IMAGE,
}

# 35 events, 5 per category.
# Each row: title, category, description, venue, city,
#           days from today, time (24h), price (Standard seat, in rupees), total seats
# Dates are relative to the day the database is created, so they are always upcoming.
SAMPLE_EVENTS = [
    # ---------------- CONCERTS ----------------
    ("Soulful Evenings Unplugged", "Concert",
     "A warm acoustic night of Hindi film classics and soft romantic ballads, "
     "performed live with strings, guitar and a full vocal ensemble.",
     "Skyline Arena", "Mumbai", 9, "19:30", 1799, 100),
    ("Indie Nights Pune", "Concert",
     "Four rising indie bands, one cosy venue. Original songs, raw energy and "
     "a crowd that sings along to every chorus.",
     "The Amp Room", "Pune", 4, "20:30", 799, 50),
    ("Bollywood Beats", "Concert",
     "Dance to the biggest Bollywood party hits with a live band, dancers and a "
     "dazzling light show on an open-air stage.",
     "Harmony Open Grounds", "Navi Mumbai", 21, "18:00", 1299, 90),
    ("Electro Pulse Night", "Concert",
     "Three top DJs, a massive sound system and laser visuals. Doors open at "
     "9 PM and the bass drops soon after.",
     "Neon Warehouse", "Bengaluru", 15, "21:00", 2499, 80),
    ("Sufi & Ghazal Evening", "Concert",
     "An intimate evening of qawwali, sufi and ghazal in a candle-lit "
     "courtyard. Come for the poetry, stay for the music.",
     "Heritage Courtyard", "Hyderabad", 33, "19:00", 999, 60),

    # ---------------- CONFERENCES ----------------
    ("Tech Innovators Summit", "Conference",
     "A full-day summit on cloud, web and mobile engineering with talks from "
     "industry leaders, live demos and a networking lunch.",
     "Hi-Tech Convention Centre", "Pune", 17, "09:30", 2999, 120),
    ("AI & Future Tech Conference", "Conference",
     "Two tracks on machine learning, generative AI and responsible "
     "automation, with research talks and startup showcases.",
     "Tech Park Auditorium", "Bengaluru", 28, "09:00", 3999, 150),
    ("Startup India Meet", "Conference",
     "Founders, investors and students meet for pitch sessions, funding "
     "panels and one-to-one mentoring slots.",
     "Bharat Convention Hall", "Delhi", 11, "10:00", 1499, 100),
    ("Digital Commerce Expo", "Conference",
     "Explore the future of online retail, payments and logistics with "
     "exhibitors, workshops and keynote sessions.",
     "Grand Expo Centre", "Mumbai", 40, "10:30", 1999, 140),
    ("Future of Computing Summit", "Conference",
     "A deep-dive into quantum computing, edge devices and next-generation "
     "chips, aimed at engineers and researchers.",
     "Cyber Towers Hall", "Hyderabad", 55, "09:30", 4999, 80),

    # ---------------- SPORTS ----------------
    ("Mumbai Coastal Run", "Sports",
     "A scenic 10 km run along the sea front with timing chips, medals for "
     "all finishers and a post-run breakfast.",
     "Marine Drive Start Point", "Mumbai", 26, "05:30", 499, 150),
    ("Premier Cricket Fan Fest", "Sports",
     "Watch the season finale live from the stands, with big screens, fan "
     "zones and food stalls all around the stadium.",
     "Bay Stadium", "Navi Mumbai", 12, "18:30", 899, 70),
    ("Inter-City Football Championship", "Sports",
     "Eight city teams compete in a one-day knockout football tournament "
     "under floodlights. Great atmosphere for families.",
     "Riverside Football Ground", "Kolkata", 19, "17:00", 349, 120),
    ("All India Badminton Open", "Sports",
     "Watch top shuttlers battle it out in singles and doubles on a "
     "professional indoor court.",
     "Indoor Sports Complex", "Hyderabad", 7, "10:00", 599, 60),
    ("Cricket Legends Meet", "Sports",
     "Retired international players come together for an exhibition match, "
     "followed by an autograph and photo session.",
     "Deccan Cricket Ground", "Pune", 45, "15:00", 2799, 100),

    # ---------------- COMEDY ----------------
    ("Stand-up Saturday", "Comedy",
     "Six comics, ten minutes each. A fast, fresh and fearless lineup "
     "of observational comedy.",
     "Punchline Theatre", "Mumbai", 2, "20:30", 599, 40),
    ("Laugh Riot Comedy Night", "Comedy",
     "Five of the funniest stand-up comedians in one evening. Guaranteed to "
     "leave your cheeks sore from laughing.",
     "The Laughing Vault", "Thane", 0, "20:00", 499, 40),
    ("Laugh Factory Pune", "Comedy",
     "A friendly weekday show with sharp jokes about college life, jobs and "
     "family WhatsApp groups.",
     "Giggle Garage", "Pune", 8, "20:00", 399, 35),
    ("Open Mic Madness", "Comedy",
     "New comics try out their freshest material in front of a live "
     "audience. Entry is cheap and the laughs are real.",
     "The Mic Drop Cafe", "Delhi", 5, "19:00", 199, 30),
    ("The Comedy Club Live", "Comedy",
     "A premium headline show with a touring comic, a warm-up act and "
     "reserved lounge seating.",
     "Chuckle Lounge", "Bengaluru", 20, "21:00", 1199, 45),

    # ---------------- FESTIVALS ----------------
    ("Sunset Music Festival", "Festival",
     "Two stages, food trucks, art installations and a sunset you will never "
     "forget. Bring your friends and enjoy the ultimate weekend festival.",
     "Marine Drive Grounds", "Mumbai", 36, "16:00", 1999, 80),
    ("Mumbai Street Food Festival", "Festival",
     "Over sixty stalls serving street food from every corner of India, "
     "with live cooking demos and a chai tasting zone.",
     "Bandra Open Grounds", "Mumbai", 13, "12:00", 299, 120),
    ("Pink City Heritage Festival", "Festival",
     "Folk dance, puppet shows, handicraft bazaars and evening light "
     "projections celebrating Rajasthan's heritage.",
     "Heritage Gardens", "Jaipur", 48, "17:00", 1499, 100),
    ("Navi Mumbai Cultural Fest", "Festival",
     "A family-friendly weekend of classical dance, regional music, art "
     "exhibitions and children's activities.",
     "Central Park Grounds", "Navi Mumbai", 31, "16:30", 399, 110),
    ("Goa Beats Beach Festival", "Festival",
     "A sunset-to-midnight beach festival with international DJs, "
     "beachside food shacks and water sports.",
     "Sandy Cove Beach", "Goa", 60, "15:00", 3499, 150),

    # ---------------- WORKSHOPS ----------------
    ("UI/UX Design Workshop", "Workshop",
     "A hands-on workshop for beginners. Learn the basics of user research, "
     "wireframing and prototyping, and build your first app design.",
     "Creative Hub", "Bengaluru", 3, "10:00", 299, 30),
    ("AI/ML Hands-on Workshop", "Workshop",
     "Train your first machine learning model in one day. Laptops required, "
     "no prior experience needed.",
     "Code Lab Studio", "Pune", 14, "10:00", 1499, 30),
    ("Photography Masterclass", "Workshop",
     "Learn composition, lighting and editing from a working photographer, "
     "including a guided street-photo walk.",
     "Lens Studio", "Mumbai", 10, "11:00", 999, 25),
    ("Python Bootcamp for Beginners", "Workshop",
     "A friendly one-day introduction to Python. Write real programs, "
     "fix your first bugs and take home practice projects.",
     "Learning Loft", "Thane", 22, "09:30", 699, 40),
    ("Digital Marketing Workshop", "Workshop",
     "Understand SEO, social media ads and email campaigns with live "
     "examples and a small practical project.",
     "Skill Hub", "Delhi", 35, "14:00", 549, 35),

    # ---------------- THEATRE ----------------
    ("Shakespeare Under the Stars", "Theatre",
     "A magical open-air performance of a timeless classic, performed by a "
     "talented local theatre group under the night sky.",
     "Open Air Amphitheatre", "Pune", 6, "19:30", 599, 30),
    ("Marathi Natak Evening", "Theatre",
     "A much-loved Marathi family drama full of humour and emotion, "
     "performed by a veteran stage company.",
     "Rangmanch Auditorium", "Thane", 16, "19:00", 349, 60),
    ("Broadway Nights", "Theatre",
     "Songs and scenes from famous Broadway musicals, performed live with "
     "full costumes, choreography and a live band.",
     "Grand Stage Theatre", "Mumbai", 29, "19:30", 1299, 80),
    ("Modern Theatre Showcase", "Theatre",
     "Three short experimental plays by young playwrights on city life, "
     "identity and technology.",
     "Black Box Studio", "Delhi", 24, "18:30", 799, 40),
    ("Mumbai Theatre Festival", "Theatre",
     "A weekend of plays in Hindi, English and Marathi, with interactions "
     "between audiences and directors after each show.",
     "City Playhouse", "Mumbai", 38, "18:00", 449, 70),
]

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user',
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    category    TEXT NOT NULL,
    description TEXT NOT NULL,
    venue       TEXT NOT NULL,
    city        TEXT NOT NULL,
    event_date  TEXT NOT NULL,      -- YYYY-MM-DD
    event_time  TEXT NOT NULL,      -- HH:MM (24 hour)
    price       REAL NOT NULL,
    total_seats INTEGER NOT NULL,
    image_url   TEXT,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bookings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_code   TEXT NOT NULL UNIQUE,
    user_id        INTEGER NOT NULL,
    event_id       INTEGER NOT NULL,
    seats          TEXT NOT NULL,   -- e.g. "A1,A2,A3"
    num_tickets    INTEGER NOT NULL,
    subtotal       REAL NOT NULL,
    fee            REAL NOT NULL,
    total_amount   REAL NOT NULL,
    payment_method TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'Confirmed',
    booked_at      TEXT NOT NULL,
    FOREIGN KEY (user_id)  REFERENCES users(id),
    FOREIGN KEY (event_id) REFERENCES events(id)
);

-- One row per booked seat. The UNIQUE rule makes double booking impossible.
CREATE TABLE IF NOT EXISTS booking_seats (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    event_id   INTEGER NOT NULL,
    seat_label TEXT NOT NULL,
    UNIQUE (event_id, seat_label),
    FOREIGN KEY (booking_id) REFERENCES bookings(id),
    FOREIGN KEY (event_id)   REFERENCES events(id)
);
"""

EVENT_SELECT = """
SELECT e.*,
       (SELECT COUNT(*) FROM booking_seats bs WHERE bs.event_id = e.id) AS booked_count
FROM events e
"""

BOOKING_SELECT = """
SELECT b.*, e.title, e.venue, e.city, e.event_date, e.event_time,
       e.image_url, e.category,
       u.name AS user_name, u.email AS user_email
FROM bookings b
JOIN events e ON e.id = b.event_id
JOIN users  u ON u.id = b.user_id
"""


def get_db():
    """Open one database connection per request."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables and add sample data the first time the app runs."""
    db = sqlite3.connect(DATABASE)
    db.executescript(SCHEMA)

    # Safe migration: add the refund columns to an existing bookings table.
    # Existing bookings are kept; the new columns are simply empty for them.
    existing_columns = {row[1] for row in db.execute("PRAGMA table_info(bookings)")}
    for column, kind in (("refund_status", "TEXT"),
                         ("refund_amount", "REAL"),
                         ("cancelled_at", "TEXT")):
        if column not in existing_columns:
            db.execute("ALTER TABLE bookings ADD COLUMN {} {}".format(column, kind))

    # Default admin account
    admin_exists = db.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]
    if admin_exists == 0:
        db.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
            ("Administrator", "admin@eventease.com", generate_password_hash("admin123")))
        print("Admin account created -> admin@eventease.com / admin123")

    # Sample events (see SAMPLE_EVENTS above). They are added only when the
    # events table is empty, so events created by an admin are never overwritten.
    event_count = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    if event_count == 0:
        today = date.today()
        for (title, category, description, venue, city,
             days, time_, price, seats) in SAMPLE_EVENTS:
            db.execute(
                """INSERT INTO events
                   (title, category, description, venue, city, event_date,
                    event_time, price, total_seats, image_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (title, category, description, venue, city,
                 (today + timedelta(days=days)).isoformat(),
                 time_, price, seats, SAMPLE_IMAGES.get(category, DEFAULT_IMAGE)))
        print("{} sample events added.".format(len(SAMPLE_EVENTS)))

    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Template filters and globals
# ---------------------------------------------------------------------------
def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


@app.template_filter("inr")
def inr_filter(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value
    if value == int(value):
        return "₹{:,}".format(int(value))
    return "₹{:,.2f}".format(value)


@app.template_filter("nice_date")
def nice_date_filter(value):
    d = _parse_date(value)
    return d.strftime("%a, %d %b %Y") if d else value


@app.template_filter("day_num")
def day_num_filter(value):
    d = _parse_date(value)
    return d.strftime("%d") if d else ""


@app.template_filter("month_short")
def month_short_filter(value):
    d = _parse_date(value)
    return d.strftime("%b").upper() if d else ""


@app.template_filter("nice_time")
def nice_time_filter(value):
    try:
        return datetime.strptime(value, "%H:%M").strftime("%I:%M %p")
    except (ValueError, TypeError):
        return value


@app.template_filter("nice_datetime")
def nice_datetime_filter(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y, %I:%M %p")
    except (ValueError, TypeError):
        return value


@app.template_filter("place")
def place_filter(city):
    """'Mumbai' -> 'Mumbai, Maharashtra' (only for cities we know)."""
    state = CITY_STATES.get(city)
    return "{}, {}".format(city, state) if state else city


@app.context_processor
def inject_globals():
    return {
        "categories": CATEGORIES,
        "current_year": datetime.now().year,
        "is_logged_in": "user_id" in session,
        "is_admin": session.get("role") == "admin",
        "MAX_SEATS": MAX_SEATS_PER_BOOKING,
        "FEE_RATE": FEE_RATE,
        "FEE_PERCENT": int(round(FEE_RATE * 100)),
        "today": date.today().isoformat(),
    }


# ---------------------------------------------------------------------------
# Login helpers
# ---------------------------------------------------------------------------
def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access only. Please log in as admin.", "warning")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapper


def safe_next(target):
    """Only allow redirects to pages inside our own site."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None


def start_session(user):
    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["role"] = user["role"]


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
def password_error(password):
    """Return a message if the password is too weak, otherwise None."""
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
        return "Password must contain at least one letter and one number."
    return None


def luhn_ok(number):
    """Standard card-number check (Luhn algorithm)."""
    total = 0
    for index, ch in enumerate(reversed(number)):
        digit = int(ch)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


# ---------------------------------------------------------------------------
# Seat layout and pricing helpers
# ---------------------------------------------------------------------------
def round_half_up(value):
    """Round 2.5 -> 3 (same as JavaScript Math.round) so the server and the
    browser always calculate exactly the same price."""
    return int(math.floor(value + 0.5))


def get_event(event_id):
    return get_db().execute(EVENT_SELECT + " WHERE e.id = ?", (event_id,)).fetchone()


def get_taken_seats(event_id):
    rows = get_db().execute(
        "SELECT seat_label FROM booking_seats WHERE event_id = ?", (event_id,)).fetchall()
    return {row["seat_label"] for row in rows}


def get_total_rows(event):
    return int(math.ceil(event["total_seats"] / SEATS_PER_ROW))


def tier_for_row(row_index, total_rows):
    """Front row = VIP, next rows = Premium, back rows = Standard."""
    if total_rows < 3:
        return "standard"
    if row_index == 0:
        return "vip"
    if row_index < max(2, total_rows // 3):
        return "premium"
    return "standard"


def tier_price(event, tier):
    return round_half_up(event["price"] * TIER_INFO[tier]["multiplier"])


def seat_tier(event, seat_label):
    return tier_for_row(ord(seat_label[0]) - 65, get_total_rows(event))


def seat_price(event, seat_label):
    return tier_price(event, seat_tier(event, seat_label))


def build_seat_layout(event, taken):
    """Return a list of rows. Each row has a letter, a tier, a price and seats."""
    rows = []
    total_rows = get_total_rows(event)
    seats_left_to_place = event["total_seats"]

    for row_index in range(total_rows):
        letter = chr(65 + row_index)
        tier = tier_for_row(row_index, total_rows)
        price = tier_price(event, tier)
        seats = []
        for number in range(1, min(SEATS_PER_ROW, seats_left_to_place) + 1):
            label = "{}{}".format(letter, number)
            seats.append({"label": label, "taken": label in taken,
                          "tier": tier, "price": price})
        seats_left_to_place -= len(seats)
        rows.append({"letter": letter, "tier": tier,
                     "tier_label": TIER_INFO[tier]["label"],
                     "price": price, "seats": seats})
    return rows


def tier_legend(rows):
    """One entry per seat category that exists in this event."""
    legend = []
    seen = set()
    for row in rows:
        if row["tier"] not in seen:
            seen.add(row["tier"])
            legend.append({"key": row["tier"], "label": row["tier_label"],
                           "price": row["price"]})
    return legend


def validate_selection(event_id, seats_raw):
    """Check the chosen seats. Returns (event, seat_list, error_message)."""
    if not event_id:
        return None, [], "Event not found."
    event = get_event(event_id)
    if event is None:
        return None, [], "Event not found."
    if event["event_date"] < date.today().isoformat():
        return event, [], "This event has already taken place."

    seats = []
    for item in (seats_raw or "").split(","):
        item = item.strip().upper()
        if item and item not in seats:
            seats.append(item)

    if not seats:
        return event, [], "Please select at least one seat."
    if len(seats) > MAX_SEATS_PER_BOOKING:
        return event, [], "You can book at most {} seats at a time.".format(MAX_SEATS_PER_BOOKING)

    taken = get_taken_seats(event["id"])
    layout = build_seat_layout(event, taken)
    valid_labels = {seat["label"] for row in layout for seat in row["seats"]}
    for seat in seats:
        if seat not in valid_labels:
            return event, [], "Invalid seat selected: {}.".format(seat)
        if seat in taken:
            return event, [], "Seat {} has just been booked. Please choose another.".format(seat)

    seats.sort(key=lambda s: (s[0], int(s[1:])))
    return event, seats, None


def price_summary(event, seats):
    """Work out the price for a list of seat labels (server side)."""
    groups = {}
    subtotal = 0
    for label in seats:
        tier = seat_tier(event, label)
        price = tier_price(event, tier)
        subtotal += price
        group = groups.setdefault(tier, {"tier": tier,
                                         "label": TIER_INFO[tier]["label"],
                                         "price": price, "count": 0, "amount": 0})
        group["count"] += 1
        group["amount"] += price

    fee = round_half_up(subtotal * FEE_RATE)
    breakdown = [groups[key] for key in TIER_ORDER if key in groups]
    return {"subtotal": subtotal, "fee": fee, "total": subtotal + fee,
            "breakdown": breakdown}


def checkout_context(event, seats, method="card"):
    return {
        "event": event,
        "seats": seats,
        "seats_csv": ",".join(seats),
        "count": len(seats),
        "summary": price_summary(event, seats),
        "banks": BANKS,
        "selected_method": method,
    }


def check_payment(method, form):
    """Simulated payment check. Returns an error message or None."""
    if method == "card":
        number = form.get("card_number", "").replace(" ", "")
        if not re.fullmatch(r"[0-9]{16}", number):
            return "Please enter a valid 16-digit card number."
        if not luhn_ok(number):
            return "This card number is not valid. Please check it and try again."
        if len(form.get("card_name", "").strip()) < 2:
            return "Please enter the name on the card."

        match = re.fullmatch(r"(0[1-9]|1[0-2])/([0-9]{2})", form.get("card_expiry", "").strip())
        if not match:
            return "Please enter the expiry date as MM/YY."
        month, year = int(match.group(1)), 2000 + int(match.group(2))
        now = datetime.now()
        if (year, month) < (now.year, now.month):
            return "This card has expired. Please use another card."

        if not re.fullmatch(r"[0-9]{3}", form.get("card_cvv", "").strip()):
            return "Please enter a valid 3-digit CVV."
        if number == DECLINE_TEST_CARD:
            return "Payment declined by the bank (simulated). Please try another card."
    elif method == "upi":
        if not UPI_RE.match(form.get("upi_id", "").strip()):
            return "Please enter a valid UPI ID (for example name@bank)."
    elif method == "netbanking":
        if form.get("bank") not in BANKS:
            return "Please select your bank."
    else:
        return "Please choose a payment method."
    return None


# ---------------------------------------------------------------------------
# Booking ID and QR code helpers
# ---------------------------------------------------------------------------
def make_booking_code(db):
    """Booking IDs look like EE-260929-K7X2PA (prefix + date + 6 random chars)."""
    prefix = "EE-" + datetime.now().strftime("%y%m%d") + "-"
    while True:
        code = prefix + "".join(secrets.choice(CODE_CHARS) for _ in range(6))
        if db.execute("SELECT id FROM bookings WHERE booking_code = ?", (code,)).fetchone() is None:
            return code


def make_qr_data_uri(text):
    """Create a QR code image and return it as a data URI for an <img> tag."""
    if qrcode is None:
        return None
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=8, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#14122b", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def ticket_qr(booking):
    """Return (qr_image_data_uri, verify_url). The QR opens the verify page."""
    verify_url = url_for("verify_ticket", code=booking["booking_code"], _external=True)
    return make_qr_data_uri(verify_url), verify_url


def get_booking_or_404(booking_id):
    booking = get_db().execute(BOOKING_SELECT + " WHERE b.id = ?", (booking_id,)).fetchone()
    if booking is None:
        abort(404)
    if booking["user_id"] != session.get("user_id") and session.get("role") != "admin":
        abort(403)
    return booking


# ---------------------------------------------------------------------------
# Cancellation helpers
# ---------------------------------------------------------------------------
CANCEL_WINDOW_HOURS = 24


def event_start(booking):
    """The real start of the event, built from its stored date and time."""
    try:
        return datetime.strptime(
            "{} {}".format(booking["event_date"], booking["event_time"]), "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return None


def cancellation_check(booking):
    """Return (allowed, message). Works with a database row or a dict."""
    if booking["status"] == "Cancelled":
        return False, "This booking has already been cancelled."
    start = event_start(booking)
    if start is None:
        return False, "The event time is not available, so this booking cannot be cancelled."
    now = datetime.now()
    if start <= now:
        return False, "This event has already taken place, so it cannot be cancelled."
    if start - now <= timedelta(hours=CANCEL_WINDOW_HOURS):
        return False, "Cancellation is available only up to 24 hours before the event."
    return True, ""


# ---------------------------------------------------------------------------
# Error pages
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def page_not_found(error):
    return render_template(
        "error.html", code=404, title="Page not found",
        message="The page you are looking for does not exist or may have been moved."), 404


@app.errorhandler(403)
def forbidden(error):
    return render_template(
        "error.html", code=403, title="Access denied",
        message="You do not have permission to view this page."), 403


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    db = get_db()
    today = date.today().isoformat()
    events = db.execute(
        EVENT_SELECT + " WHERE e.event_date >= ? ORDER BY e.event_date, e.event_time LIMIT 6",
        (today,)).fetchall()
    stats = {
        "events": db.execute("SELECT COUNT(*) FROM events WHERE event_date >= ?", (today,)).fetchone()[0],
        "tickets": db.execute("SELECT COALESCE(SUM(num_tickets), 0) FROM bookings WHERE status != 'Cancelled'").fetchone()[0],
        "cities": db.execute("SELECT COUNT(DISTINCT city) FROM events").fetchone()[0],
        "users": db.execute("SELECT COUNT(*) FROM users WHERE role = 'user'").fetchone()[0],
    }
    return render_template("index.html", events=events, stats=stats)


@app.route("/events")
def events():
    db = get_db()
    today = date.today()
    today_iso = today.isoformat()

    # The locations dropdown is built from the events that are really in the database
    locations = [row["city"] for row in db.execute(
        "SELECT DISTINCT city FROM events WHERE event_date >= ? ORDER BY city COLLATE NOCASE",
        (today_iso,)).fetchall()]

    # Read the filters from the URL and ignore any value that is not allowed
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    city = request.args.get("city", "").strip()
    price = request.args.get("price", "").strip()
    when = request.args.get("when", "").strip()
    sort = request.args.get("sort", "date").strip()

    if category not in CATEGORIES:
        category = ""
    if city not in locations:
        city = ""
    if price not in dict(PRICE_FILTERS):
        price = ""
    if when not in dict(DATE_FILTERS):
        when = ""
    if sort not in SORT_SQL:
        sort = "date"

    # Build the query. Upcoming events only.
    sql = EVENT_SELECT + " WHERE e.event_date >= ?"
    params = [today_iso]

    if q:
        sql += " AND (e.title LIKE ? OR e.venue LIKE ? OR e.city LIKE ?)"
        params += ["%" + q + "%"] * 3
    if category:
        sql += " AND e.category = ?"
        params.append(category)
    if city:
        sql += " AND e.city = ?"
        params.append(city)

    if price == "under_500":
        sql += " AND e.price < 500"
    elif price == "500_1000":
        sql += " AND e.price >= 500 AND e.price <= 1000"
    elif price == "1000_2500":
        sql += " AND e.price > 1000 AND e.price < 2500"
    elif price == "2500_plus":
        sql += " AND e.price >= 2500"

    if when == "today":
        sql += " AND e.event_date = ?"
        params.append(today_iso)
    elif when == "week":
        sql += " AND e.event_date <= ?"
        params.append((today + timedelta(days=6)).isoformat())
    elif when == "month":
        sql += " AND e.event_date <= ?"
        params.append((today + timedelta(days=29)).isoformat())

    sql += " ORDER BY " + SORT_SQL[sort]
    all_events = db.execute(sql, params).fetchall()

    # Small helpers for the template
    active_filters = []
    if q:
        active_filters.append("Search: “{}”".format(q))
    if category:
        active_filters.append("Category: " + category)
    if city:
        active_filters.append("Location: " + city)
    if price:
        active_filters.append("Price: " + dict(PRICE_FILTERS)[price])
    if when:
        active_filters.append("Date: " + dict(DATE_FILTERS)[when])

    # Links for the category chips keep the other filters that are already chosen
    chip_args = {key: value for key, value in (
        ("q", q), ("city", city), ("price", price), ("when", when),
        ("sort", sort if sort != "date" else "")) if value}

    return render_template(
        "events.html", events=all_events, q=q, selected_category=category,
        selected_city=city, selected_price=price, selected_when=when, sort=sort,
        locations=locations, price_options=PRICE_FILTERS,
        date_options=DATE_FILTERS, sort_options=SORT_OPTIONS,
        active_filters=active_filters, chip_args=chip_args)


@app.route("/event/<int:event_id>")
def event_detail(event_id):
    event = get_event(event_id)
    if event is None:
        abort(404)
    seats_left = event["total_seats"] - event["booked_count"]
    is_past = event["event_date"] < date.today().isoformat()
    related = get_db().execute(
        EVENT_SELECT + """ WHERE e.category = ? AND e.id != ? AND e.event_date >= ?
                           ORDER BY e.event_date LIMIT 3""",
        (event["category"], event_id, date.today().isoformat())).fetchall()
    tiers = tier_legend(build_seat_layout(event, set()))
    return render_template("event_detail.html", event=event, seats_left=seats_left,
                           sold_out=seats_left <= 0, is_past=is_past,
                           related=related, tiers=tiers)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("index"))

    form = {"name": "", "email": ""}
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        form = {"name": name, "email": email}

        errors = []
        if len(name) < 2 or len(name) > 60:
            errors.append("Please enter your full name (2 to 60 characters).")
        elif any(ch.isdigit() for ch in name):
            errors.append("Your name cannot contain numbers.")
        if not EMAIL_RE.match(email) or len(email) > 120:
            errors.append("Please enter a valid email address.")
        problem = password_error(password)
        if problem:
            errors.append(problem)
        if password != confirm:
            errors.append("Passwords do not match.")

        db = get_db()
        if not errors and db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            errors.append("An account with this email already exists. Try logging in.")

        if errors:
            for message in errors:
                flash(message, "error")
            return render_template("register.html", form=form)

        cursor = db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)))
        db.commit()
        user = db.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
        start_session(user)
        flash("Welcome to EventEase, {}! Your account is ready.".format(name), "success")
        return redirect(url_for("index"))

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))

    next_url = safe_next(request.values.get("next"))
    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            start_session(user)
            flash("Welcome back, {}!".format(user["name"]), "success")
            return redirect(next_url or url_for("index"))
        flash("Invalid email or password.", "error")

    return render_template("login.html", email=email, next_url=next_url)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Booking flow: seats -> checkout -> pay -> confirmation -> ticket
# ---------------------------------------------------------------------------
@app.route("/event/<int:event_id>/seats")
@login_required
def select_seats(event_id):
    event = get_event(event_id)
    if event is None:
        abort(404)
    if event["event_date"] < date.today().isoformat():
        flash("This event has already taken place.", "warning")
        return redirect(url_for("event_detail", event_id=event_id))

    taken = get_taken_seats(event_id)
    if len(taken) >= event["total_seats"]:
        flash("Sorry, this event is sold out.", "warning")
        return redirect(url_for("event_detail", event_id=event_id))

    rows = build_seat_layout(event, taken)
    return render_template("seats.html", event=event, rows=rows,
                           legend=tier_legend(rows), taken_count=len(taken))


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    if request.method == "GET":
        return redirect(url_for("events"))

    event_id = request.form.get("event_id", type=int)
    event, seats, error = validate_selection(event_id, request.form.get("seats", ""))
    if error:
        flash(error, "error")
        if event:
            return redirect(url_for("select_seats", event_id=event["id"]))
        return redirect(url_for("events"))

    return render_template("checkout.html", **checkout_context(event, seats))


@app.route("/pay", methods=["POST"])
@login_required
def pay():
    event_id = request.form.get("event_id", type=int)
    event, seats, error = validate_selection(event_id, request.form.get("seats", ""))
    if error:
        flash(error, "error")
        if event:
            return redirect(url_for("select_seats", event_id=event["id"]))
        return redirect(url_for("events"))

    method = request.form.get("payment_method", "card")
    payment_error = check_payment(method, request.form)
    if payment_error:
        flash(payment_error, "error")
        return render_template("checkout.html", **checkout_context(event, seats, method))

    # Payment "succeeded" (simulated). Save the booking.
    db = get_db()
    summary = price_summary(event, seats)
    code = make_booking_code(db)
    transaction_id = "TXN" + "".join(secrets.choice(string.digits) for _ in range(10))
    booked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cursor = db.execute(
            """INSERT INTO bookings
               (booking_code, user_id, event_id, seats, num_tickets, subtotal, fee,
                total_amount, payment_method, transaction_id, status, booked_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Confirmed', ?)""",
            (code, session["user_id"], event["id"], ",".join(seats), len(seats),
             summary["subtotal"], summary["fee"], summary["total"],
             method, transaction_id, booked_at))
        booking_id = cursor.lastrowid
        for seat in seats:
            db.execute(
                "INSERT INTO booking_seats (booking_id, event_id, seat_label) VALUES (?, ?, ?)",
                (booking_id, event["id"], seat))
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        flash("Sorry, one of your seats was just booked by someone else. Please choose again.", "error")
        return redirect(url_for("select_seats", event_id=event["id"]))

    flash("Payment successful! Your booking is confirmed.", "success")
    return redirect(url_for("confirmation", booking_id=booking_id))


@app.route("/confirmation/<int:booking_id>")
@login_required
def confirmation(booking_id):
    booking = get_booking_or_404(booking_id)
    if booking["status"] == "Cancelled":
        return redirect(url_for("ticket", booking_id=booking_id))
    qr_code, verify_url = ticket_qr(booking)
    return render_template("confirmation.html", booking=booking,
                           seat_list=booking["seats"].split(","),
                           qr_code=qr_code, verify_url=verify_url)


@app.route("/ticket/<int:booking_id>")
@login_required
def ticket(booking_id):
    booking = get_booking_or_404(booking_id)
    qr_code, verify_url = ticket_qr(booking)
    return render_template("ticket.html", booking=booking,
                           seat_list=booking["seats"].split(","),
                           qr_code=qr_code, verify_url=verify_url)


@app.route("/verify/<code>")
def verify_ticket(code):
    """Opened when someone scans the QR code on a ticket. No login needed."""
    booking = get_db().execute(
        BOOKING_SELECT + " WHERE b.booking_code = ?", (code.strip().upper(),)).fetchone()
    seat_list = booking["seats"].split(",") if booking else []
    is_past = bool(booking) and booking["event_date"] < date.today().isoformat()
    return render_template("verify.html", booking=booking, code=code,
                           seat_list=seat_list, is_past=is_past)


@app.route("/my-bookings")
@login_required
def my_bookings():
    rows = get_db().execute(
        BOOKING_SELECT + " WHERE b.user_id = ? ORDER BY b.id DESC",
        (session["user_id"],)).fetchall()
    today = date.today().isoformat()

    bookings = []
    for row in rows:
        item = dict(row)
        item["can_cancel"], item["cancel_note"] = cancellation_check(row)
        bookings.append(item)

    cancelled = [b for b in bookings if b["status"] == "Cancelled"]
    active = [b for b in bookings if b["status"] != "Cancelled"]
    upcoming = [b for b in active if b["event_date"] >= today]
    upcoming.sort(key=lambda b: (b["event_date"], b["event_time"]))
    past = [b for b in active if b["event_date"] < today]
    return render_template("my_bookings.html", upcoming=upcoming, past=past,
                           cancelled=cancelled, total=len(bookings))


@app.route("/booking/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    db = get_db()
    booking = db.execute(BOOKING_SELECT + " WHERE b.id = ?", (booking_id,)).fetchone()

    if booking is None:
        flash("We could not find that booking.", "error")
        return redirect(url_for("my_bookings"))
    if booking["user_id"] != session["user_id"]:
        flash("You can only cancel your own bookings.", "error")
        return redirect(url_for("my_bookings"))

    allowed, message = cancellation_check(booking)
    if not allowed:
        flash(message, "warning")
        return redirect(url_for("my_bookings"))

    refund = booking["total_amount"]          # the full amount actually paid
    cancelled_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cursor = db.execute(
            """UPDATE bookings
               SET status = 'Cancelled', refund_status = 'Refund Initiated',
                   refund_amount = ?, cancelled_at = ?
               WHERE id = ? AND status != 'Cancelled'""",
            (refund, cancelled_at, booking_id))
        if cursor.rowcount == 0:               # someone cancelled it a moment ago
            db.rollback()
            flash("This booking has already been cancelled.", "warning")
            return redirect(url_for("my_bookings"))
        # Free ONLY the seats that belong to this booking
        db.execute("DELETE FROM booking_seats WHERE booking_id = ?", (booking_id,))
        db.commit()
    except sqlite3.Error:
        db.rollback()
        flash("Something went wrong while cancelling. Please try again.", "error")
        return redirect(url_for("my_bookings"))

    flash("Booking {} cancelled. A refund of {} has been initiated.".format(
        booking["booking_code"], inr_filter(refund)), "success")
    return redirect(url_for("my_bookings"))


# ---------------------------------------------------------------------------
# Admin area
# ---------------------------------------------------------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))

    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM users WHERE email = ? AND role = 'admin'", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            start_session(user)
            flash("Welcome to the admin panel.", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin credentials.", "error")

    return render_template("admin_login.html", email=email)


@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    revenue = db.execute(
        "SELECT COALESCE(SUM(total_amount), 0) FROM bookings WHERE status != 'Cancelled'").fetchone()[0]
    bookings_count = db.execute(
        "SELECT COUNT(*) FROM bookings WHERE status != 'Cancelled'").fetchone()[0]
    stats = {
        "revenue": revenue,
        "bookings": bookings_count,
        "tickets": db.execute(
            "SELECT COALESCE(SUM(num_tickets), 0) FROM bookings WHERE status != 'Cancelled'").fetchone()[0],
        "events": db.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        "users": db.execute("SELECT COUNT(*) FROM users WHERE role = 'user'").fetchone()[0],
        "average": (revenue / bookings_count) if bookings_count else 0,
    }
    revenue_by_event = db.execute(
        """SELECT e.id, e.title,
                  COALESCE(SUM(b.total_amount), 0) AS revenue,
                  COALESCE(SUM(b.num_tickets), 0)  AS tickets
           FROM events e
           LEFT JOIN bookings b ON b.event_id = e.id AND b.status != 'Cancelled'
           GROUP BY e.id ORDER BY revenue DESC LIMIT 6""").fetchall()
    max_revenue = max([row["revenue"] for row in revenue_by_event] + [1])
    recent = db.execute(BOOKING_SELECT + " ORDER BY b.id DESC LIMIT 8").fetchall()
    return render_template("admin_dashboard.html", stats=stats,
                           revenue_by_event=revenue_by_event,
                           max_revenue=max_revenue, recent=recent)


@app.route("/admin/events")
@admin_required
def admin_events():
    rows = get_db().execute(
        """SELECT e.*,
                  (SELECT COUNT(*) FROM booking_seats bs WHERE bs.event_id = e.id) AS booked_count,
                  (SELECT COALESCE(SUM(total_amount), 0) FROM bookings b
                    WHERE b.event_id = e.id AND b.status != 'Cancelled') AS revenue
           FROM events e ORDER BY e.event_date DESC""").fetchall()
    return render_template("admin_events.html", events=rows)


def read_event_form(is_new=False):
    """Read and validate the add/edit event form. Returns (data, errors)."""
    f = request.form
    data = {
        "title": f.get("title", "").strip(),
        "category": f.get("category", "").strip(),
        "description": f.get("description", "").strip(),
        "venue": f.get("venue", "").strip(),
        "city": f.get("city", "").strip(),
        "event_date": f.get("event_date", "").strip(),
        "event_time": f.get("event_time", "").strip(),
        "image_url": f.get("image_url", "").strip(),
        "price": f.get("price", "").strip(),
        "total_seats": f.get("total_seats", "").strip(),
    }
    errors = []

    if not 3 <= len(data["title"]) <= 100:
        errors.append("Event title must be between 3 and 100 characters.")
    if data["category"] not in CATEGORIES:
        errors.append("Please choose a valid category.")
    if len(data["description"]) < 10:
        errors.append("Description must be at least 10 characters.")
    if not data["venue"] or not data["city"]:
        errors.append("Venue and city are required.")

    parsed_date = _parse_date(data["event_date"])
    if parsed_date is None:
        errors.append("Please enter a valid event date.")
    else:
        data["event_date"] = parsed_date.strftime("%Y-%m-%d")
        if is_new and data["event_date"] < date.today().isoformat():
            errors.append("A new event must be dated today or later.")

    try:
        datetime.strptime(data["event_time"], "%H:%M")
    except ValueError:
        errors.append("Please enter a valid event time.")

    if data["image_url"] and not URL_RE.match(data["image_url"]):
        errors.append("Image URL must start with http:// or https://")

    price = seats = None
    try:
        price = float(data["price"])
        if price < 0:
            raise ValueError
    except ValueError:
        errors.append("Price must be a number (0 or more).")
    try:
        seats = int(data["total_seats"])
        if not 10 <= seats <= 200:
            raise ValueError
    except ValueError:
        errors.append("Total seats must be a whole number between 10 and 200.")

    if not errors:
        data["price"] = price
        data["total_seats"] = seats
        if not data["image_url"]:
            data["image_url"] = DEFAULT_IMAGE
    return data, errors


@app.route("/admin/events/add", methods=["GET", "POST"])
@admin_required
def admin_add_event():
    if request.method == "POST":
        data, errors = read_event_form(is_new=True)
        if errors:
            for message in errors:
                flash(message, "error")
            return render_template("admin_event_form.html", event=data, mode="add", event_id=None)

        db = get_db()
        db.execute(
            """INSERT INTO events
               (title, category, description, venue, city, event_date, event_time,
                price, total_seats, image_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data["title"], data["category"], data["description"], data["venue"],
             data["city"], data["event_date"], data["event_time"], data["price"],
             data["total_seats"], data["image_url"]))
        db.commit()
        flash("Event added successfully.", "success")
        return redirect(url_for("admin_events"))

    return render_template("admin_event_form.html", event={}, mode="add", event_id=None)


@app.route("/admin/events/<int:event_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_event(event_id):
    event = get_event(event_id)
    if event is None:
        abort(404)

    if request.method == "POST":
        data, errors = read_event_form()
        if not errors and event["booked_count"] > 0 and data["total_seats"] < event["total_seats"]:
            errors.append("This event already has bookings, so total seats cannot be reduced.")
        if errors:
            for message in errors:
                flash(message, "error")
            return render_template("admin_event_form.html", event=data, mode="edit", event_id=event_id)

        db = get_db()
        db.execute(
            """UPDATE events SET title = ?, category = ?, description = ?, venue = ?,
                                 city = ?, event_date = ?, event_time = ?, price = ?,
                                 total_seats = ?, image_url = ?
               WHERE id = ?""",
            (data["title"], data["category"], data["description"], data["venue"],
             data["city"], data["event_date"], data["event_time"], data["price"],
             data["total_seats"], data["image_url"], event_id))
        db.commit()
        flash("Event updated successfully.", "success")
        return redirect(url_for("admin_events"))

    return render_template("admin_event_form.html", event=event, mode="edit", event_id=event_id)


@app.route("/admin/events/<int:event_id>/delete", methods=["POST"])
@admin_required
def admin_delete_event(event_id):
    db = get_db()
    if get_event(event_id) is None:
        abort(404)
    db.execute("DELETE FROM booking_seats WHERE event_id = ?", (event_id,))
    db.execute("DELETE FROM bookings WHERE event_id = ?", (event_id,))
    db.execute("DELETE FROM events WHERE id = ?", (event_id,))
    db.commit()
    flash("Event and its bookings were deleted.", "info")
    return redirect(url_for("admin_events"))


@app.route("/admin/bookings")
@admin_required
def admin_bookings():
    q = request.args.get("q", "").strip()
    sql = BOOKING_SELECT
    params = []
    if q:
        sql += (" WHERE b.booking_code LIKE ? OR u.name LIKE ? "
                "OR u.email LIKE ? OR e.title LIKE ?")
        params = ["%" + q + "%"] * 4
    sql += " ORDER BY b.id DESC"

    bookings = get_db().execute(sql, params).fetchall()
    active = [b for b in bookings if b["status"] != "Cancelled"]
    total_revenue = sum(b["total_amount"] for b in active)
    total_tickets = sum(b["num_tickets"] for b in active)
    total_refunded = sum((b["refund_amount"] or 0) for b in bookings
                         if b["status"] == "Cancelled")
    return render_template("admin_bookings.html", bookings=bookings, q=q,
                           total_revenue=total_revenue, total_tickets=total_tickets,
                           total_refunded=total_refunded)


# ---------------------------------------------------------------------------
# Start the app
# ---------------------------------------------------------------------------
init_db()   # creates the database, tables and sample data if they do not exist

if __name__ == "__main__":
    app.run(debug=True)