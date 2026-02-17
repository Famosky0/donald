# ============================================================
# TASKFLOW APP (Flask)
# - This file controls what pages exist (routes)
# - It connects to the database (MySQL)
# - It handles login/register + user sessions
# - It handles tasks/lists CRUD
# ============================================================

# ============================================================
# 1) IMPORTS (Libraries we use)
# ============================================================

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, g, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from authlib.integrations.flask_client import OAuth
from datetime import datetime
import mysql.connector
import os
import json
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


# Load environment variables from .env FIRST (so os.environ works)
load_dotenv()


# ============================================================
# 2) APP SETUP (Flask instance + session settings)
# ============================================================

app = Flask(__name__)

# ============================================================
# EMAIL (Gmail SMTP)
# ============================================================

app.config.update(
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
    MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=("TaskFlow", os.environ.get("MAIL_USERNAME")),
)


mail = Mail(app)


# Secret key is used to protect session cookies (login sessions).
# In production, ALWAYS store this in .env
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "DEV_ONLY_CHANGE_ME")
EMAIL_VERIFY_MAX_AGE = int(os.environ.get("EMAIL_VERIFY_MAX_AGE", "86400"))
EMAIL_VERIFY_SALT = os.environ.get("EMAIL_VERIFY_SALT", "taskflow-email-verify")

def get_email_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(app.secret_key)

def format_note_timestamp(dt):
    if dt is None:
        return ""

    today = datetime.now().date()
    dt_date = dt.date()
    delta_days = (today - dt_date).days

    if delta_days == 0:
        hour = dt.hour % 12 or 12
        minute = dt.minute
        am_pm = "AM" if dt.hour < 12 else "PM"
        return f"{hour}:{minute:02d} {am_pm}"

    if 0 < delta_days < 7:
        return dt.strftime("%A")

    year_short = str(dt.year)[-2:]
    return f"{dt.month}/{dt.day}/{year_short}"

@app.template_filter("note_timestamp")
def note_timestamp(value):
    if not value:
        return ""
    return format_note_timestamp(value)


def group_notes_by_date(notes):
    if not notes:
        return []

    today = datetime.now().date()
    groups = {
        "Today": [],
        "Yesterday": [],
        "Previous 7 Days": [],
        "Previous 30 Days": [],
        "Older": []
    }

    for note in notes:
        timestamp = note.get("last_opened_at") or note.get("updated_at")
        if not timestamp:
            groups["Older"].append(note)
            continue

        delta_days = (today - timestamp.date()).days
        if delta_days == 0:
            groups["Today"].append(note)
        elif delta_days == 1:
            groups["Yesterday"].append(note)
        elif 1 < delta_days < 7:
            groups["Previous 7 Days"].append(note)
        elif 7 <= delta_days < 30:
            groups["Previous 30 Days"].append(note)
        else:
            groups["Older"].append(note)

    order = [
        "Today",
        "Yesterday",
        "Previous 7 Days",
        "Previous 30 Days",
        "Older"
    ]
    return [
        {"label": label, "notes": groups[label]}
        for label in order
        if groups[label]
    ]


# ============================================================
# 3) FILE UPLOAD SETTINGS (profile pictures)
# ============================================================

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ============================================================
# 4) DATABASE SETTINGS (MySQL connection info)
# ============================================================
# NOTE: Hardcoding your password in code is risky.
# Move these into a .env later (DB_HOST, DB_USER, etc.)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "Smile0731."),
    "database": os.environ.get("DB_NAME", "todo_list"),
    "autocommit": True,
}


# ============================================================
# 5) GOOGLE OAUTH (Sign in with Google)
# ============================================================

oauth = OAuth(app)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

google = None

# Only enable Google login if credentials are present
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    google = oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        # Google OpenID metadata (tells Authlib where JWKS + endpoints are)
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
else:
    print("⚠️ Google OAuth disabled (missing env vars)")


# ============================================================
# 6) DATABASE CONNECTION HELPERS
# ============================================================

def get_db():
    """
    Creates ONE database connection per request.
    Flask stores it in `g` so every function can reuse it safely.
    """
    if "db" not in g:
        g.db = mysql.connector.connect(**DB_CONFIG)
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    """
    After each request finishes, Flask calls this function automatically.
    It closes the database connection to prevent leaks.
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ============================================================
# 7) SMALL UTILITY HELPERS (simple reusable functions)
# ============================================================

def logged_in() -> bool:
    """Returns True if the user is currently logged in."""
    return "user_id" in session


def login_required(route_func):
    """
    A decorator: it protects pages that require login.
    If you're not logged in, it sends you to /login.
    """
    def wrapper(*args, **kwargs):
        if not logged_in():
            return redirect(url_for("login_page"))
        return route_func(*args, **kwargs)
    wrapper.__name__ = route_func.__name__
    return wrapper


def allowed_file(filename: str) -> bool:
    """Checks if a file extension is allowed (png/jpg/jpeg/gif)."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================================
# GLOBAL TEMPLATE VARIABLES (available in ALL templates)
# ============================================================

@app.context_processor
def inject_user_globals():
    if "user_id" not in session:
        return {}

    user = fetch_user_by_id(session["user_id"])
    if not user:
        return {}

    return {
        "profile_image": user["profile_image"] or "default.png",
        "username": user["username"],
        "name": user["name"].split()[0],
    }


# ============================================================
# 8) USER DATA HELPERS (talking to users table)
# ============================================================

def fetch_user_by_email(email: str):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()
    cursor.close()
    return user


def fetch_user_by_username(username: str):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()
    cursor.close()
    return user


def fetch_user_by_id(user_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, name, username, email, profile_image, auth_provider, is_verified FROM users WHERE id=%s",
        (user_id,)
    )
    user = cursor.fetchone()
    cursor.close()
    return user


def create_user_local(full_name, username, email, password_hash):
    """
    Creates a normal account (email/password) and returns new user_id.
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO users (name, username, email, password_hash, is_verified) VALUES (%s,%s,%s,%s,%s)",
        (full_name, username, email, password_hash, 0),
    )
    user_id = cursor.lastrowid
    cursor.close()
    return user_id


def create_user_oauth(name, email, provider, provider_id):
    """
    Creates a new user after logging in with Google.
    If username already exists, it adds a number (example: donny, donny1, donny2).
    """
    base_username = (email.split("@")[0] if email else "user").lower()
    username = base_username
    suffix = 0

    while fetch_user_by_username(username):
        suffix += 1
        username = f"{base_username}{suffix}"

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO users (name, username, email, auth_provider, provider_id, is_verified, email_verified_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        (name, username, email, provider, provider_id, 1, datetime.utcnow()),
    )
    user_id = cursor.lastrowid
    cursor.close()

    return user_id, username


def set_email_verification_token(user_id: int, token: str):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE users SET email_verify_token=%s, email_verify_sent_at=%s WHERE id=%s",
        (token, datetime.utcnow(), user_id),
    )
    cursor.close()


def mark_user_verified(user_id: int):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE users SET is_verified=1, email_verified_at=%s, email_verify_token=NULL WHERE id=%s",
        (datetime.utcnow(), user_id),
    )
    cursor.close()


def generate_email_verification_token(user_id: int, email: str) -> str:
    serializer = get_email_serializer()
    return serializer.dumps({"user_id": user_id, "email": email}, salt=EMAIL_VERIFY_SALT)


def verify_email_token(token: str):
    serializer = get_email_serializer()
    return serializer.loads(token, salt=EMAIL_VERIFY_SALT, max_age=EMAIL_VERIFY_MAX_AGE)


def send_verification_email(email: str, token: str):
    verify_url = url_for("verify_email", token=token, _external=True)
    msg = Message(
        subject="Verify your TaskFlow email",
        recipients=[email],
        body=f"Welcome to TaskFlow!\n\nVerify your email: {verify_url}\n\nThis link expires in 24 hours."
    )
    mail.send(msg)


def send_welcome_email(email: str, first_name: str):
    login_url = url_for("login_page", _external=True)
    msg = Message(
        subject=f"Welcome to TaskFlow, {first_name}!",
        recipients=[email],
    )
    msg.body = f"""
Hi {first_name},

Welcome to TaskFlow!

Your account has been successfully created — we are glad to have you.

Here is what you can do next:
- Log in: {login_url}
- Create your first task
- Explore your dashboard and get productive

Need help? Reply to this email anytime — we are here for you.

Happy planning,
The TaskFlow Team
""".strip()
    mail.send(msg)


# ============================================================
# 9) LIST + TASK HELPERS
# ============================================================

def user_owns_list(user_id: int, list_id: int) -> bool:
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT 1 FROM task_lists WHERE id=%s AND user_id=%s", (list_id, user_id))
    ok = cursor.fetchone() is not None
    cursor.close()
    return ok


def get_inbox_list_id(user_id: int) -> int:
    """
    Every user should always have an Inbox list.
    If it doesn't exist, this creates it.
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT id FROM task_lists WHERE user_id=%s AND name='Inbox' LIMIT 1",
        (user_id,)
    )
    row = cursor.fetchone()

    if row:
        cursor.close()
        return row["id"]

    cursor2 = db.cursor()
    cursor2.execute(
        "INSERT INTO task_lists (user_id, name) VALUES (%s, %s)",
        (user_id, "Inbox")
    )
    inbox_id = cursor2.lastrowid
    cursor2.close()
    cursor.close()
    return inbox_id


def fetch_task_for_user(task_id: int, user_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tasks WHERE id=%s AND user_id=%s", (task_id, user_id))
    task = cursor.fetchone()
    cursor.close()
    return task


# ============================================================
# 10) PUBLIC PAGES (no login required)
# ============================================================

@app.route("/")
def landing_page():
    return render_template("landing_page.html")


@app.route("/terms")
def terms_page():
    return render_template("policy/terms.html")

@app.route("/cookie")
def cookie_page():
    return render_template("policy/cookie.html")
@app.route("/contact")
def contact_page():
    return render_template("navlinks/contact.html")


@app.route("/privacy")
def privacy_page():
    return render_template("policy/privacy.html")

@app.route("/features")
def features_page():
    return render_template("navlinks/features.html")
@app.route("/premium")
def premium_page():
    return render_template("navlinks/premium.html")
@app.route("/pricing")
def pricing_page():
    return render_template("navlinks/pricing.html")
@app.route("/about")
def about_page():
    return render_template("navlinks/about.html")


# ============================================================
# 11) AUTH ROUTES (register/login/logout)
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register_page():
    if request.method == "POST":
        first = request.form.get("first_name", "").strip().capitalize()
        last = request.form.get("last_name", "").strip().capitalize()
        identifier = request.form.get("identifier", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not all([first, last, identifier, password]):
            return render_template("auth/register.html", error_identifier="Please fill out all fields.")

        if "@" not in identifier:
            return render_template("auth/register.html", error_identifier="Please use a valid email address.")

        email = identifier
        username = None

        if username and fetch_user_by_username(username):
            return render_template("auth/register.html", error_identifier="Username already exists.")

        if email and fetch_user_by_email(email):
            return render_template("auth/register.html", error_identifier="Email already exists.")

        # If user registered with email only, auto-generate username from email prefix
        if username is None:
            base = email.split("@")[0]
            username = base
            i = 0
            while fetch_user_by_username(username):
                i += 1
                username = f"{base}{i}"

        password_hash = generate_password_hash(password)
        full_name = f"{first} {last}"

        user_id = create_user_local(full_name, username, email, password_hash)

        send_welcome_email(email, first)
        token = generate_email_verification_token(user_id, email)
        set_email_verification_token(user_id, token)
        send_verification_email(email, token)

        return redirect(url_for("login_page", verify="sent"))

    return render_template("auth/register.html")


@app.route("/login", methods=["GET", "POST"])
def login_page():
    error_identifier = None
    error_password = None
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT id, name, username, password_hash, auth_provider, email
            FROM users
            WHERE username=%s OR email=%s
            """,
            (identifier, identifier),
        )
        user = cursor.fetchone()
        cursor.close()

        if not user:
            error_identifier = "Invalid username/email or password."
        elif not user[3] or not check_password_hash(user[3], password):
            error_password = "Invalid username/email or password."
        else:
            session.update({
                "user_id": user[0],
                "user_name": user[1],
                "username": user[2]
            })
            return redirect(url_for("home_page"))

    return render_template("auth/login.html",
                           error_identifier=error_identifier,
                           error_password=error_password)


@app.route("/verify-email")
def verify_email():
    token = request.args.get("token", "")
    if not token:
        return render_template("auth/verify_email_result.html", status="invalid")

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, email, is_verified, email_verify_token FROM users WHERE email_verify_token=%s",
        (token,),
    )
    user = cursor.fetchone()
    cursor.close()

    if not user:
        return render_template("auth/verify_email_result.html", status="invalid")

    try:
        data = verify_email_token(token)
    except SignatureExpired:
        return render_template("auth/verify_email_result.html", status="expired")
    except BadSignature:
        return render_template("auth/verify_email_result.html", status="invalid")

    if data.get("user_id") != user["id"] or data.get("email") != user["email"]:
        return render_template("auth/verify_email_result.html", status="invalid")

    if not user["is_verified"]:
        mark_user_verified(user["id"])

    return redirect(url_for("home_page"))

@app.route("/username_suggestions", methods=["POST"])
def username_suggestions():
    first = (request.form.get("first_name") or "").lower()
    last = (request.form.get("last_name") or "").lower()

    if not first or not last:
        return {"suggestions": []}

    patterns = [
        f"{first}{last}",
        f"{first}.{last}",
        f"{first}_{last}",
        f"{first}{last[:1]}",
        f"{first[:1]}{last}",
        f"{first}{last}{len(first)}",
        f"{first}{last}dev",
        f"{first}{last}ai",
        f"{first}_{last}_tf"
    ]

    suggestions = []
    for name in patterns:
        if not fetch_user_by_username(name):
            suggestions.append(name)
        if len(suggestions) >= 6:
            break

    return {"suggestions": suggestions}

@app.route("/check-identifier", methods=["POST"])
def check_identifier():
    identifier = (request.form.get("identifier") or "").lower()

    exists = False
    if "@" in identifier:
        exists = bool(fetch_user_by_email(identifier))
    else:
        exists = bool(fetch_user_by_username(identifier))

    return {"exists": exists}

@app.route("/logout")
def logout():
    """
    Logs the user out by clearing their session cookie.
    """
    session.clear()
    return redirect(url_for("landing_page"))

# ============================================================
# 12) ACCOUNT / SETTINGS ROUTES (login required)
# ============================================================

@app.route("/account")
@login_required
def account_page():
    user = fetch_user_by_id(session["user_id"])
    is_modal = request.args.get("modal")
    verify_notice = request.args.get("verify")

    template = (
        "auth/account_modal.html"
        if is_modal
        else "auth/account_page.html"
    )

    return render_template(
        template,
        name=user["name"].split()[0],
        full_name=user["name"],
        username=user["username"],
        email=user["email"],
        profile_image=user["profile_image"] or "default.png",
        auth_provider=user["auth_provider"],
        is_verified=bool(user["is_verified"]),
        verify_notice=verify_notice,
    )


@app.route("/resend-verification")
@login_required
def resend_verification():
    user = fetch_user_by_id(session["user_id"])

    if user["auth_provider"] or not user["email"]:
        return redirect(url_for("account_page", modal=1, verify="not-applicable"))

    if user["is_verified"]:
        return redirect(url_for("account_page", modal=1, verify="already"))

    token = generate_email_verification_token(user["id"], user["email"])
    set_email_verification_token(user["id"], token)
    send_verification_email(user["email"], token)

    return redirect(url_for("verify_email_pending"))


@app.route("/verify-email/pending")
@login_required
def verify_email_pending():
    return render_template("auth/verify_email_result.html", status="pending")




@app.route("/upload_profile", methods=["POST"])
@login_required
def upload_profile():
    """
    Receives a profile image upload from your JS fetch() call.
    Saves image to /static/uploads and stores filename in DB.
    """
    if "profile_image" not in request.files:
        abort(400, "Missing file: profile_image")

    file = request.files["profile_image"]
    if not file or file.filename == "":
        abort(400, "No file selected")

    if not allowed_file(file.filename):
        abort(400, "Invalid file type")

    # Ensure folder exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"user_{session['user_id']}_{int(datetime.now().timestamp())}.{ext}"
    filename = secure_filename(filename)

    file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    # Save filename in database
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE users SET profile_image=%s WHERE id=%s",
        (filename, session["user_id"])
    )
    cursor.close()

    return ("", 204)


@app.route("/update_profile_name", methods=["POST"])
@login_required
def update_profile_name():
    full_name = (request.form.get("full_name") or "").strip()
    if not full_name:
        abort(400, "Name is required")

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE users SET name=%s WHERE id=%s",
        (full_name, session["user_id"])
    )
    db.commit()
    cursor.close()

    session["user_name"] = full_name
    return ("", 204)


# ============================================================
# 13) PASSWORD RESET (MVP)
# ============================================================

@app.route("/accountreset", methods=["GET", "POST"])
def account_reset():
    """
    Simple password reset page (MVP):
    - User types email
    - We DO NOT reveal if email exists (security best practice)
    - Later you can email a token link
    """
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()

        if not email:
            return render_template("auth/account_reset.html", error="Enter your email.")

        if "@" not in email or "." not in email:
            return render_template("auth/account_reset.html", error="Enter a valid email address.")

        _user = fetch_user_by_email(email)  # don't reveal result

        return render_template(
            "auth/account_reset.html",
            message="If that email exists, a reset link has been sent."
        )

    return render_template("auth/account_reset.html")


# ============================================================
# 14) DASHBOARD / HOME (login required)
# ============================================================

@app.route("/home")
@login_required
def home_page():
    """
    Main logged-in app page: shows lists + tasks.
    """
    user_id = session["user_id"]
    active_list_id = request.args.get("list_id", type=int)

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT name, username, profile_image FROM users WHERE id=%s",
        (user_id,),
    )
    user = cursor.fetchone()

    cursor.execute(
        "SELECT id, name, created_at FROM task_lists WHERE user_id=%s ORDER BY created_at DESC",
        (user_id,)
    )
    lists = cursor.fetchall()

    inbox_id = get_inbox_list_id(user_id)

    if not any(l["id"] == inbox_id for l in lists):
        cursor.execute(
            "SELECT id, name, created_at FROM task_lists WHERE user_id=%s ORDER BY created_at DESC",
            (user_id,)
        )
        lists = cursor.fetchall()

    # Choose active list safely
    if not active_list_id or not any(l["id"] == active_list_id for l in lists):
        active_list_id = inbox_id

    active_list = next((l for l in lists if l["id"] == active_list_id), None)

    cursor.execute(
        "SELECT * FROM tasks WHERE user_id=%s AND list_id=%s ORDER BY created_at DESC",
        (user_id, active_list_id)
    )
    tasks = cursor.fetchall()
    cursor.close()
    
    return render_template(
    "sidebar/home.html",
    active_page="home",
    page_title="Home",
    lists=lists,
    active_list=active_list,
    active_list_id=active_list_id,
    tasks=tasks,
)



# ============================================================
# 15) LIST ROUTES (create/rename/delete)
# ============================================================

@app.route("/lists/create", methods=["POST"])
@login_required
def create_list():
    name = (request.form.get("name") or "").strip()
    if not name:
        return redirect(url_for("home_page"))

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO task_lists (user_id, name) VALUES (%s, %s)",
        (session["user_id"], name)
    )
    new_id = cursor.lastrowid
    cursor.close()

    return redirect(url_for("tasks_page", list_id=new_id))

@app.route("/lists/reorder", methods=["POST"])
@login_required
def reorder_lists():
    order = request.json["order"]

    db = get_db()
    cursor = db.cursor()

    for index, list_id in enumerate(order):
        cursor.execute(
            "UPDATE task_lists SET position=%s WHERE id=%s AND user_id=%s",
            (index, list_id, session["user_id"])
        )

    cursor.close()
    return "", 204




@app.route("/lists/rename/<int:list_id>", methods=["POST"])
@login_required
def rename_list(list_id):
    name = (request.form.get("name") or "").strip()
    if not name:
        return redirect(url_for("tasks_page", list_id=list_id))

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE task_lists SET name=%s WHERE id=%s AND user_id=%s",
        (name, list_id, session["user_id"])
    )
    cursor.close()

    return redirect(url_for("tasks_page", list_id=list_id))



@app.route("/lists/delete/<int:list_id>", methods=["POST"])
@login_required
def delete_list(list_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT name FROM task_lists WHERE id=%s AND user_id=%s",
        (list_id, session["user_id"])
    )
    row = cursor.fetchone()
    cursor.close()

    if not row or row["name"] == "Inbox":
        return redirect(url_for("tasks_page"))

    cursor = db.cursor()
    cursor.execute(
        "DELETE FROM task_lists WHERE id=%s AND user_id=%s",
        (list_id, session["user_id"])
    )
    cursor.close()

    inbox_id = get_inbox_list_id(session["user_id"])
    return redirect(url_for("tasks_page", list_id=inbox_id))



# ============================================================
# 16) TASK ROUTES (create/view/edit/toggle/delete)
# ============================================================

@app.route("/tasks/create", methods=["POST"])
@login_required
def create_task():
    list_id = request.form.get("list_id", type=int)
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()

    # If no title, stay on tasks page
    if not title:
        return redirect(url_for("tasks_page", list_id=list_id))

    # Fallback to Inbox if list is invalid or not owned
    if not list_id or not user_owns_list(session["user_id"], list_id):
        list_id = get_inbox_list_id(session["user_id"])

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO tasks (user_id, list_id, title, description)
        VALUES (%s, %s, %s, %s)
        """,
        (session["user_id"], list_id, title, description)
    )
    cursor.close()

    # 🔥 THIS IS THE KEY LINE
    return redirect(url_for("tasks_page", list_id=list_id))



@app.route("/tasks/<int:task_id>")
@login_required
def view_task(task_id):
    task = fetch_task_for_user(task_id, session["user_id"])
    if not task:
        return redirect(url_for("home_page"))
    return render_template("task_view.html", task=task)


@app.route("/tasks/edit/<int:task_id>", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task = fetch_task_for_user(task_id, session["user_id"])
    if not task:
        return redirect(url_for("home_page"))

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()

        if not title:
            return render_template("task_edit.html", task=task, error="Title is required.")

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "UPDATE tasks SET title=%s, description=%s WHERE id=%s AND user_id=%s",
            (title, description, task_id, session["user_id"])
        )
        cursor.close()

        return redirect(url_for("home_page", list_id=task["list_id"]))

    return render_template("task_edit.html", task=task)


@app.route("/tasks/toggle/<int:task_id>", methods=["POST"])
@login_required
def toggle_task(task_id):
    task = fetch_task_for_user(task_id, session["user_id"])
    if not task:
        return redirect(url_for("home_page"))

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE tasks SET completed = NOT completed WHERE id=%s AND user_id=%s",
        (task_id, session["user_id"])
    )
    cursor.close()

    return redirect(url_for("home_page", list_id=task["list_id"]))


@app.route("/tasks/delete/<int:task_id>", methods=["POST"])
@login_required
def delete_task(task_id):
    task = fetch_task_for_user(task_id, session["user_id"])
    if not task:
        return redirect(url_for("home_page"))

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "DELETE FROM tasks WHERE id=%s AND user_id=%s",
        (task_id, session["user_id"])
    )
    cursor.close()

    return redirect(url_for("home_page", list_id=task["list_id"]))

# ============================================================
# SIDEBAR PAGES (login required)
# ============================================================

@app.route("/search")
@login_required
def search_page():
    return render_template("sidebar/search.html", active_page="search")


@app.route("/habits")
@login_required
def habits_page():
    return render_template("sidebar/habits.html", active_page="habits", page_title="Habits")


# ---------------- NOTES ----------------

def fetch_note_folders_tree(user_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, name, parent_id
        FROM note_folders
        WHERE user_id = %s AND deleted_at IS NULL
        ORDER BY created_at ASC
    """, (user_id,))

    rows = cursor.fetchall()
    cursor.close()

    folders = {}
    tree = []

    for row in rows:
        row["children"] = []
        folders[row["id"]] = row

    for row in rows:
        pid = row.get("parent_id")
        if pid and pid in folders:
            folders[pid]["children"].append(row)
        else:
            tree.append(row)

    return tree

def is_mobile_request():
    user_agent = request.headers.get("User-Agent", "")
    return any(token in user_agent for token in ("Mobile", "Android", "iPhone", "iPad", "iPod"))


@app.route("/notes")
@login_required
def notes_page():
    user_id = session["user_id"]
    folder_id = request.args.get("folder_id", type=int)
    view = request.args.get("view")
    list_only = request.args.get("list") == "1" or request.args.get("folders") == "1"
    force_mobile_page = None

    if is_mobile_request() and not request.args:
        view = "root"
        list_only = True
        force_mobile_page = "folders"

    scope = "all"
    if view == "root":
        scope = "root"
    elif folder_id:
        scope = f"folder:{folder_id}"

    active_folders = fetch_active_folders(user_id)
    folder_counts = fetch_folder_counts(user_id)
    all_notes_count, root_notes_count = fetch_notes_counts(user_id)

    db = get_db()
    cursor = db.cursor(dictionary=True)

    last_opened_note_id = None
    raw_scope_cookie = request.cookies.get("last_opened_note_by_scope")
    if raw_scope_cookie:
        try:
            scope_map = json.loads(raw_scope_cookie)
            last_opened_note_id = scope_map.get(scope)
        except (json.JSONDecodeError, TypeError):
            last_opened_note_id = None

    if scope == "all" and not last_opened_note_id:
        last_opened_note_id = request.cookies.get("last_opened_note_id")

    if last_opened_note_id and not list_only:
        cursor.execute("""
            SELECT id, folder_id
            FROM notes
            WHERE id = %s
              AND user_id = %s
              AND deleted_at IS NULL
        """, (last_opened_note_id, user_id))
        note = cursor.fetchone()

        if note:
            if scope == "root" and note["folder_id"] is None:
                cursor.close()
                return redirect(url_for("view_note", note_id=note["id"], view="root"))
            if scope.startswith("folder:") and note["folder_id"] == folder_id:
                cursor.close()
                return redirect(url_for("view_note", note_id=note["id"], folder_id=folder_id))
            if scope == "all":
                cursor.close()
                return redirect(url_for("view_note", note_id=note["id"], view="all"))

    if scope == "root" and not list_only:
        cursor.execute("""
            SELECT id
            FROM notes
            WHERE user_id = %s
              AND folder_id IS NULL
              AND deleted_at IS NULL
              AND NOT ((title IS NULL OR title = '') AND (content IS NULL OR content = ''))
            ORDER BY COALESCE(last_opened_at, updated_at) DESC
            LIMIT 1
        """, (user_id,))
        fallback = cursor.fetchone()
        if fallback:
            cursor.close()
            return redirect(url_for("view_note", note_id=fallback["id"], view="root"))

    if scope.startswith("folder:") and folder_id and not list_only:
        cursor.execute("""
            SELECT id
            FROM notes
            WHERE user_id = %s
              AND folder_id = %s
              AND deleted_at IS NULL
              AND NOT ((title IS NULL OR title = '') AND (content IS NULL OR content = ''))
            ORDER BY COALESCE(last_opened_at, updated_at) DESC
            LIMIT 1
        """, (user_id, folder_id))
        fallback = cursor.fetchone()
        if fallback:
            cursor.close()
            return redirect(url_for("view_note", note_id=fallback["id"], folder_id=folder_id))

    if scope == "all" and not list_only:
        cursor.execute("""
            SELECT id, folder_id
            FROM notes
            WHERE user_id = %s
              AND deleted_at IS NULL
              AND NOT ((title IS NULL OR title = '') AND (content IS NULL OR content = ''))
            ORDER BY COALESCE(last_opened_at, updated_at) DESC
            LIMIT 1
        """, (user_id,))
        fallback = cursor.fetchone()
        if fallback:
            cursor.close()
            return redirect(url_for("view_note", note_id=fallback["id"], view="all"))

    active_folder = None
    notes = []
    notes_view = "all"

    if view == "root":
        cursor.execute("""
            SELECT *
            FROM notes
            WHERE user_id = %s
              AND folder_id IS NULL
              AND deleted_at IS NULL
              AND NOT ((title IS NULL OR title = '') AND (content IS NULL OR content = ''))
            ORDER BY COALESCE(last_opened_at, updated_at) DESC
        """, (user_id,))
        notes = cursor.fetchall()
        notes_view = "root"

    elif folder_id:
        cursor.execute("""
            SELECT *
            FROM notes
            WHERE user_id = %s
              AND folder_id = %s
              AND deleted_at IS NULL
              AND NOT ((title IS NULL OR title = '') AND (content IS NULL OR content = ''))
            ORDER BY COALESCE(last_opened_at, updated_at) DESC
        """, (user_id, folder_id))
        notes = cursor.fetchall()

        cursor.execute("""
            SELECT id, name
            FROM note_folders
            WHERE id = %s AND user_id = %s
        """, (folder_id, user_id))
        active_folder = cursor.fetchone()

        notes_view = "folder"

    else:
        cursor.execute("""
            SELECT *
            FROM notes
            WHERE user_id = %s
              AND deleted_at IS NULL
              AND NOT ((title IS NULL OR title = '') AND (content IS NULL OR content = ''))
            ORDER BY COALESCE(last_opened_at, updated_at) DESC
        """, (user_id,))
        notes = cursor.fetchall()
        notes_view = "all"

    cursor.close()
    deleted_notes_count = fetch_deleted_notes_count(user_id)

    return render_template(
        "sidebar/notes.html",
        active_page="notes",
        notes_view=notes_view,
        page_title="Notes",
        active_folders=active_folders,
        notes=notes,
        notes_grouped=group_notes_by_date(notes),
        active_folder_id=folder_id if notes_view == "folder" else None,
        active_folder=active_folder,
        folder_counts=folder_counts,
        all_notes_count=all_notes_count,
        root_notes_count=root_notes_count,
        deleted_notes_count=deleted_notes_count,
        force_mobile_page=force_mobile_page
    )




@app.route("/notes/new")
@login_required
def new_note_root():
    user_id = session["user_id"]

    notes_folder_id = get_notes_folder_id(user_id)

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO notes (user_id, folder_id, title, content)
        VALUES (%s, %s, NULL, '')
    """, (user_id, notes_folder_id))

    note_id = cursor.lastrowid
    cursor.close()

    return redirect(url_for("view_note", note_id=note_id)) 


def get_notes_folder_id(user_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT id
        FROM note_folders
        WHERE user_id = %s
          AND name = 'Notes'
          AND deleted_at IS NULL
        LIMIT 1
    """, (user_id,))

    row = cursor.fetchone()

    if row:
        cursor.close()
        return row["id"]

    # Create it if missing (first-time user)
    cursor2 = db.cursor()
    cursor2.execute("""
        INSERT INTO note_folders (user_id, name)
        VALUES (%s, 'Notes')
    """, (user_id,))
    folder_id = cursor2.lastrowid

    cursor2.close()
    cursor.close()
    return folder_id

@app.route("/notes/last-opened", methods=["POST"])
@login_required
def save_last_opened_note():
    note_id = request.json.get("note_id")
    scope = request.json.get("scope")

    if not note_id or not scope:
        return "", 400

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE notes
        SET last_opened_at = NOW()
        WHERE id = %s
          AND user_id = %s
          AND deleted_at IS NULL
    """, (note_id, session["user_id"]))

    cursor.close()

    scope_map = {}
    raw_scope_cookie = request.cookies.get("last_opened_note_by_scope")
    if raw_scope_cookie:
        try:
            scope_map = json.loads(raw_scope_cookie)
        except (json.JSONDecodeError, TypeError):
            scope_map = {}

    scope_map[scope] = str(note_id)

    resp = app.make_response("", 204)
    resp.set_cookie(
        "last_opened_note_id",
        str(note_id),
        max_age=60 * 60 * 24 * 30,  # 30 days
        httponly=True,
        samesite="Lax"
    )
    resp.set_cookie(
        "last_opened_note_by_scope",
        json.dumps(scope_map),
        max_age=60 * 60 * 24 * 30,
        httponly=True,
        samesite="Lax"
    )
    return resp






def fetch_folder_counts(user_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT folder_id, COUNT(*) AS count
        FROM notes
        WHERE user_id = %s
          AND deleted_at IS NULL
          AND folder_id IS NOT NULL
          AND NOT ((title IS NULL OR title = '') AND (content IS NULL OR content = ''))
        GROUP BY folder_id
    """, (user_id,))

    counts = {row["folder_id"]: row["count"] for row in cursor.fetchall()}
    cursor.close()

    return counts


def fetch_notes_counts(user_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM notes
        WHERE user_id = %s
          AND deleted_at IS NULL
          AND NOT ((title IS NULL OR title = '') AND (content IS NULL OR content = ''))
    """, (user_id,))
    all_count = cursor.fetchone()["count"]

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM notes
        WHERE user_id = %s
          AND folder_id IS NULL
          AND deleted_at IS NULL
          AND NOT ((title IS NULL OR title = '') AND (content IS NULL OR content = ''))
    """, (user_id,))
    root_count = cursor.fetchone()["count"]

    cursor.close()

    return all_count, root_count


def fetch_deleted_notes_count(user_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM notes
        WHERE user_id = %s
          AND deleted_at IS NOT NULL
    """, (user_id,))
    count = cursor.fetchone()["count"]
    cursor.close()

    return count


@app.route("/notes/delete/<int:note_id>", methods=["POST"])
@login_required
def delete_note(note_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE notes
        SET deleted_at = NOW()
        WHERE id = %s AND user_id = %s
    """, (note_id, session["user_id"]))

    cursor.close()
    return "", 204


@app.route("/notes/restore/<int:note_id>", methods=["POST"])
@login_required
def restore_note(note_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE notes
        SET deleted_at = NULL
        WHERE id = %s AND user_id = %s
    """, (note_id, session["user_id"]))

    cursor.close()
    return redirect(url_for("recently_deleted_page"))

@app.route("/notes/purge/<int:note_id>", methods=["POST"])
@login_required
def purge_note(note_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        DELETE FROM notes
        WHERE id = %s AND user_id = %s
    """, (note_id, session["user_id"]))

    cursor.close()
    return redirect(url_for("recently_deleted_page"))

@app.route("/notes/recently-deleted/purge-all", methods=["POST"])
@login_required
def purge_all_deleted_notes():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        DELETE FROM notes
        WHERE user_id = %s AND deleted_at IS NOT NULL
    """, (session["user_id"],))

    cursor.close()
    return "", 204





@app.route("/notes/folders/create", methods=["POST"])
@login_required
def create_folder():
    name = (request.form.get("name") or "").strip()
    parent_id = (request.form.get("parent_id") or "").strip()

    if not name:
        return redirect(url_for("notes_page"))

    # convert parent_id safely
    parent_id_val = int(parent_id) if parent_id.isdigit() else None

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO note_folders (user_id, name, parent_id)
        VALUES (%s, %s, %s)
    """, (session["user_id"], name, parent_id_val))

    # 🔑 THIS IS THE KEY LINE
    folder_id = cursor.lastrowid

    db.commit()
    cursor.close()

    # 👇 Redirect directly into the new folder
    return redirect(url_for("notes_page", folder_id=folder_id))



@app.route("/notes/folders/delete/<int:folder_id>", methods=["POST"])
@login_required
def delete_folder(folder_id):
    db = get_db()
    cursor = db.cursor()

    # Soft delete folder
    cursor.execute("""
        UPDATE note_folders
        SET deleted_at = NOW()
        WHERE id = %s AND user_id = %s
    """, (folder_id, session["user_id"]))

    cursor.close()
    return "", 204

@app.route("/notes/recently-deleted")
@login_required
def recently_deleted_page():
    user_id = session["user_id"]
    note_id = request.args.get("note_id", type=int)

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Deleted folders
    cursor.execute("""
        SELECT * FROM note_folders
        WHERE user_id = %s AND deleted_at IS NOT NULL
        ORDER BY deleted_at DESC
    """, (user_id,))
    deleted_folders = cursor.fetchall()

    # Deleted notes
    cursor.execute("""
        SELECT * FROM notes
        WHERE user_id = %s AND deleted_at IS NOT NULL
        ORDER BY deleted_at DESC
    """, (user_id,))
    deleted_notes = cursor.fetchall()

    # ✅ ACTIVE DELETED NOTE (NEW)
    active_note = None
    if note_id:
        cursor.execute("""
            SELECT *
            FROM notes
            WHERE id = %s
              AND user_id = %s
              AND deleted_at IS NOT NULL
        """, (note_id, user_id))
        active_note = cursor.fetchone()

    cursor.close()
    all_notes_count, root_notes_count = fetch_notes_counts(user_id)
    folder_counts = fetch_folder_counts(user_id)

    return render_template(
        "sidebar/notes_recently_deleted.html",
        active_page="notes",
        page_title="Recently Deleted",
        deleted_folders=deleted_folders,
        deleted_notes=deleted_notes,
        deleted_notes_count=len(deleted_notes),
        active_note=active_note,
        active_folders=fetch_active_folders(user_id),
        folder_counts=folder_counts,
        all_notes_count=all_notes_count,
        root_notes_count=root_notes_count
    )

@app.route("/notes/recently-deleted/<int:note_id>")
@login_required
def view_deleted_note(note_id):
    user_id = session["user_id"]
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Fetch the deleted note
    cursor.execute("""
        SELECT *
        FROM notes
        WHERE id = %s AND user_id = %s AND deleted_at IS NOT NULL
    """, (note_id, user_id))
    active_note = cursor.fetchone()

    if not active_note:
        cursor.close()
        return redirect(url_for("recently_deleted_page"))

    # Fetch all deleted notes for left pane
    cursor.execute("""
        SELECT *
        FROM notes
        WHERE user_id = %s AND deleted_at IS NOT NULL
        ORDER BY deleted_at DESC
    """, (user_id,))
    deleted_notes = cursor.fetchall()

    cursor.close()
    all_notes_count, root_notes_count = fetch_notes_counts(user_id)
    folder_counts = fetch_folder_counts(user_id)
    deleted_notes_count = len(deleted_notes)

    return render_template(
        "sidebar/notes_recently_deleted.html",
        active_page="notes",
        page_title="Recently Deleted",
        deleted_notes=deleted_notes,
        deleted_notes_count=deleted_notes_count,
        active_note=active_note,
        active_folders=fetch_active_folders(user_id),
        folder_counts=folder_counts,
        all_notes_count=all_notes_count,
        root_notes_count=root_notes_count
    )



@app.route("/notes/folders/restore/<int:folder_id>", methods=["POST"])
@login_required
def restore_folder(folder_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE note_folders
        SET deleted_at = NULL
        WHERE id = %s AND user_id = %s
    """, (folder_id, session["user_id"]))

    cursor.close()
    return redirect(url_for("recently_deleted_page"))
@app.route("/notes/folders/purge/<int:folder_id>", methods=["POST"])
@login_required
def purge_folder(folder_id):
    user_id = session["user_id"]
    db = get_db()
    cursor = db.cursor()

    # 1️⃣ Delete notes inside folder
    cursor.execute("""
        DELETE FROM notes
        WHERE folder_id = %s AND user_id = %s
    """, (folder_id, user_id))

    # 2️⃣ Delete the folder itself
    cursor.execute("""
        DELETE FROM note_folders
        WHERE id = %s AND user_id = %s
    """, (folder_id, user_id))

    cursor.close()
    return redirect(url_for("recently_deleted_page"))

def fetch_active_folders(user_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, name, color
        FROM note_folders
        WHERE user_id = %s
          AND deleted_at IS NULL
        ORDER BY created_at ASC
    """, (user_id,))

    rows = cursor.fetchall()
    cursor.close()
    return rows


def fetch_deleted_folders(user_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, name, deleted_at
        FROM note_folders
        WHERE user_id = %s
          AND deleted_at IS NOT NULL
        ORDER BY deleted_at DESC
    """, (user_id,))

    rows = cursor.fetchall()
    cursor.close()
    return rows


@app.route("/notes/folders/rename/<int:folder_id>", methods=["POST"])
@login_required
def rename_folder(folder_id):
    name = (request.form.get("name") or "").strip()

    if not name:
        return redirect(url_for("notes_page"))

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE note_folders
        SET name = %s
        WHERE id = %s AND user_id = %s
    """, (name, folder_id, session["user_id"]))

    cursor.close()
    return redirect(url_for("notes_page"))

@app.route("/notes/<int:note_id>")
@login_required
def view_note(note_id):
    user_id = session["user_id"]
    view = request.args.get("view")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # 1️⃣ Fetch the active note
    cursor.execute("""
        SELECT *
        FROM notes
        WHERE id = %s AND user_id = %s AND deleted_at IS NULL
    """, (note_id, user_id))
    active_note = cursor.fetchone()

    if not active_note:
        cursor.close()
        return redirect(url_for("notes_page"))

    folder_id = active_note["folder_id"]

    cursor.execute("""
        UPDATE notes
        SET last_opened_at = NOW()
        WHERE id = %s
          AND user_id = %s
          AND deleted_at IS NULL
    """, (note_id, user_id))

    # 2️⃣ Decide context ONLY from the note itself
    if view == "all":
        cursor.execute("""
            SELECT *
            FROM notes
            WHERE user_id = %s
              AND deleted_at IS NULL
              AND NOT ((title IS NULL OR title = '') AND (content IS NULL OR content = ''))
            ORDER BY COALESCE(last_opened_at, updated_at) DESC
        """, (user_id,))
        notes = cursor.fetchall()

        active_folder = None
        notes_view = "all"

    elif folder_id is None:
        # NOTES (root)
        cursor.execute("""
            SELECT *
            FROM notes
            WHERE user_id = %s
              AND folder_id IS NULL
              AND deleted_at IS NULL
              AND NOT ((title IS NULL OR title = '') AND (content IS NULL OR content = ''))
            ORDER BY COALESCE(last_opened_at, updated_at) DESC
        """, (user_id,))
        notes = cursor.fetchall()

        active_folder = None
        notes_view = "root"

    else:
        # FOLDER VIEW
        cursor.execute("""
            SELECT *
            FROM notes
            WHERE user_id = %s
              AND folder_id = %s
              AND deleted_at IS NULL
              AND NOT ((title IS NULL OR title = '') AND (content IS NULL OR content = ''))
            ORDER BY COALESCE(last_opened_at, updated_at) DESC
        """, (user_id, folder_id))
        notes = cursor.fetchall()

        cursor.execute("""
            SELECT id, name
            FROM note_folders
            WHERE id = %s AND user_id = %s
        """, (folder_id, user_id))
        active_folder = cursor.fetchone()

        notes_view = "folder"

    cursor.close()
    all_notes_count, root_notes_count = fetch_notes_counts(user_id)
    deleted_notes_count = fetch_deleted_notes_count(user_id)

    return render_template(
        "sidebar/notes.html",
        active_page="notes",
        notes_view=notes_view,
        active_folders=fetch_active_folders(user_id),
        notes=notes,
        notes_grouped=group_notes_by_date(notes),
        active_note=active_note,
        active_folder=active_folder,
        active_folder_id=folder_id if notes_view == "folder" else None,
        folder_counts=fetch_folder_counts(user_id),
        all_notes_count=all_notes_count,
        root_notes_count=root_notes_count,
        deleted_notes_count=deleted_notes_count
    )


@app.route("/notes/create")
@login_required
def create_note():
    user_id = session["user_id"]
    folder_id = request.args.get("folder_id", type=int)
    view = request.args.get("view")  # 👈 root | None

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO notes (user_id, folder_id, title, content)
        VALUES (%s, %s, NULL, '')
    """, (user_id, folder_id))

    note_id = cursor.lastrowid
    cursor.close()

    # 🔑 PRESERVE CONTEXT
    if view == "root":
        return redirect(url_for("view_note", note_id=note_id, view="root")) 
    
    if folder_id:
        return redirect(url_for("view_note", note_id=note_id, folder_id=folder_id))
    
    return redirect(url_for("view_note", note_id=note_id))


@app.route("/notes/<int:note_id>/autosave", methods=["POST"])
@login_required
def autosave_note(note_id):
    title = request.form.get("title")
    content = request.form.get("content")

    # Never store "Untitled"
    if not title or title.strip() == "Untitled":
        title = None

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE notes
        SET title = %s,
            content = %s,
            updated_at = NOW()
        WHERE id = %s
          AND user_id = %s
    """, (title, content, note_id, session["user_id"]))

    if cursor.rowcount == 0:
        cursor.close()
        return "Not found", 404

    cursor.close()
    return "", 204



@app.route("/calendar")
@login_required
def calendar_page():
    return render_template("sidebar/calendar.html", active_page="calendar", page_title="Calendar")


@app.route("/trash")
@login_required
def trash_page():
    return render_template("sidebar/trash.html", active_page="trash")


# ============================================================
# 17) GOOGLE LOGIN ROUTES
# ============================================================

@app.route("/login/google")
def login_google():
    if google is None:
        return "Google OAuth not configured.", 500
    return google.authorize_redirect(url_for("google_callback", _external=True))


@app.route("/auth/google/callback")
def google_callback():
    """
    Google sends the user back here after they approve login.
    We exchange the code for an access token, then read their profile.
    """
    if google is None:
        return "Google OAuth not configured.", 500

    token = google.authorize_access_token()

    # Safer way: read user info from Google API
    user_info = google.get("userinfo").json()

    email = user_info.get("email")
    name = user_info.get("name") or "TaskFlow User"
    google_id = user_info.get("sub")  # Google unique user ID

    user = fetch_user_by_email(email)

    if user:
        user_id = user["id"]
        username = user["username"]
    else:
        user_id, username = create_user_oauth(name, email, "google", google_id)

    session.update({
        "user_id": user_id,
        "user_name": name,
        "username": username
    })

    return redirect(url_for("home_page"))

# Sidebar links pages
@app.route("/tasks")
@login_required
def tasks_page():
    user_id = session["user_id"]
    active_list_id = request.args.get("list_id", type=int)

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Get all lists
    cursor.execute(
        "SELECT id, name, created_at FROM task_lists WHERE user_id=%s ORDER BY created_at DESC",
        (user_id,)
    )
    lists = cursor.fetchall()

    # Ensure Inbox exists
    inbox_id = get_inbox_list_id(user_id)

    if not active_list_id or not any(l["id"] == active_list_id for l in lists):
        active_list_id = inbox_id

    active_list = next((l for l in lists if l["id"] == active_list_id), None)

    # 🔥 THIS IS THE IMPORTANT PART
    cursor.execute(
        "SELECT * FROM tasks WHERE user_id=%s ORDER BY created_at DESC",
        (user_id,)
    )
    tasks = cursor.fetchall()

    cursor.close()

    return render_template(
        "sidebar/tasks.html",
        active_page="tasks",
        page_title="Tasks",
        lists=lists,
        active_list=active_list,
        active_list_id=active_list_id,
        tasks=tasks,
    )

@app.route("/notes/folders/color/<int:folder_id>", methods=["POST"])
@login_required
def save_folder_color(folder_id):
    color = request.json.get("color")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE note_folders
        SET color = %s
        WHERE id = %s AND user_id = %s
    """, (color, folder_id, session["user_id"]))

    cursor.close()
    return "", 204




# ============================================================
# 18) RUN APP
# ============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=True)
