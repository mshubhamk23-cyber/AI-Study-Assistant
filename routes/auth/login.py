from flask import render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import check_password_hash
from . import auth

@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        remember = request.form.get("remember") == "on"

        user = current_app.db.users.find_one({"email": email})
        if not user or not check_password_hash(user.get("password_hash", ""), password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        # Session
        session["user_id"] = str(user["_id"])
        session["full_name"] = user["full_name"]
        session["email"] = user["email"]
        session.permanent = remember  # respect "Remember me" checkbox

        return redirect(url_for("dashboard"))

    return render_template("login.html")


@auth.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))
