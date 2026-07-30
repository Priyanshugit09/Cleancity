import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, redirect, session
import sqlite3 
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static/uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
app.secret_key = os.getenv("SECRET_KEY")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    success = request.args.get("success")

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, password FROM users WHERE email=?",
            (email,)
        )

        user = cursor.fetchone()
        print(user)

        conn.close()

        if user and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            session["user"] = user[1]
            return redirect("/dashboard")

        else:
            return "Invalid Email or Password"

    return render_template("login.html", success=success)


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, password)
            )

            conn.commit()

        except sqlite3.IntegrityError:
            return "Email already exists!"

        finally:
            conn.close()

        return redirect("/login?success=1")

    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html",user=session["user"])

@app.route("/complaint", methods=["GET", "POST"])
def complaint():

    if "user" not in session:
        return redirect("/login")

    success = request.args.get("success")

    if request.method == "POST":

        area = request.form["area"]
        description = request.form["description"]

        image = request.files["image"]
        filename = ""

        if image and image.filename != "":
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            print("Saving to:",os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO complaints (user_id, area, description, image) VALUES (?, ?, ?, ?)",
            (session["user_id"], area, description, filename)
        )

        conn.commit()
        conn.close()

        return redirect("/complaint?success=1")

    return render_template(
        "complaint.html",
        success=success
    )

@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("user_id", None)
    return redirect("/")

@app.route("/history")
def history():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT area, description, image, status FROM complaints WHERE user_id=?", (session["user_id"],))
    complaints = cursor.fetchall()

    conn.close()

    return render_template("history.html", complaints=complaints)

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")
        else:
            return "Invalid Admin Credentials"

    return render_template("admin_login.html")

@app.route("/admin-logout")
def admin_logout():
    session.pop("admin", None)
    return redirect("/admin-login")

@app.route("/admin")
def admin():

    if "admin" not in session:
        return redirect("/admin-login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, area, description, image, status FROM complaints"
    )

    complaints = cursor.fetchall()

    conn.close()

    return render_template("admin.html", complaints=complaints)

@app.route("/update/<int:id>")
def update(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT status FROM complaints WHERE id=?",
        (id,)
    )

    status = cursor.fetchone()[0]

    if status == "Pending":
        new_status = "In Progress"

    elif status == "In Progress":
        new_status = "Resolved"

    elif status == "Resolved":
        new_status = "Pending"

    else:
        new_status = "Pending"

    cursor.execute(
        "UPDATE complaints SET status=? WHERE id=?",
        (new_status, id)
    )

    conn.commit()
    conn.close()

    return redirect("/admin")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    