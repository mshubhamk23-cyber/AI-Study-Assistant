from flask import render_template, request, redirect, url_for, flash, current_app
from werkzeug.security import generate_password_hash
from pymongo.errors import DuplicateKeyError
from . import auth

@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        if not full_name or not email or not password or not confirm:
            flash("All fields are required.", "error")
            return render_template("register.html")

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        pw_hash = generate_password_hash(password)

        try:
            current_app.db.users.insert_one({
                "full_name": full_name,
                "email": email,
                "password_hash": pw_hash
            })
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("auth.login"))
        except DuplicateKeyError:
            flash("Email already registered. Try logging in.", "error")
        except Exception as e:
            flash(f"Something went wrong: {e}", "error")

    return render_template("register.html")
