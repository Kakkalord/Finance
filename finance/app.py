import os

from cs50 import SQL
from datetime import date
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET"])
@login_required
def index():
    """Show portfolio of stocks"""
    # get data: user_id, stock, price, date, amount, cost
    user_id = session["user_id"]

    # create new SQL table to keep track of which stocks each user has, and what fields (CREATE TABLE)
    db.execute("CREATE TABLE IF NOT EXISTS user_stocks (user_id INTEGER NOT NULL, stock TEXT NOT NULL, price INTEGER NOT NULL, date TEXT NOT NULL, amount INTEGER NOT NULL, cost INTEGER NOT NULL, status TEXT NOT NULL);")

    # get information for user's stocks
    information = db.execute("SELECT * FROM user_stocks WHERE user_id = ?;", user_id)

        # Create a list to hold the prices
    current_prices = []
        # get names of each stock in user's portfolio
    for row in information:
        stock_name = row["stock"]
        current_price = lookup(stock_name)
        if current_price:
            current_prices.append(current_price["price"])
        else:
            current_prices.append(0)
        # for each stock in user portolio
            # look up stock and find the price

    # combine stock names and current prices into list of dicts
    for stock_info, current_price in zip(information, current_prices):
        stock_info["current_price"] = current_price

    # remaining cash
    remaining_balance = []
    remaining_balance = db.execute("SELECT cash FROM users WHERE id = ?;", user_id)
    remaining_balance = remaining_balance[0]["cash"]
    return render_template("index.html", information=information, remaining_balance=remaining_balance)

    #return render_template("index.html", name=name, amount=amount, price=price, date=date, total_cost=total_cost, remaining_balance=remaining_balance, current_price=current_price)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # receive form and symbol and amount variable
        stock = request.form.get("symbol") # validate stock input using lookup fx
        result = []
        result = lookup(stock)
        if result == None:
            return apology("Stock does not exist!")

        symbol = result["symbol"]
        price = result["price"]
        name = result["name"]


        # check for valid input (not negative, stock symbol is valid)
        amount = request.form.get("amount") # validate amount
        if len(amount) < 1 or amount == "0":
            return apology("must input valid amount")
        amount = int(amount)

        # total cost of stock
        total_cost = float(price) * float(amount)

        # money in wallet via SQL
        user_id = session["user_id"]
        cash_list = db.execute("SELECT cash FROM users WHERE id = ?;", user_id)
        cash = cash_list[0]['cash']
        cash = int(cash)

        # compare with wallet
        if total_cost > cash:
            return apology("Not enough money")
        # update new amount
        cash = cash - total_cost
        db.execute("UPDATE users SET cash = ? WHERE id = ?;", cash, user_id)

        # check for existing row for user and stock
        existing_row = db.execute("SELECT * FROM user_stocks WHERE user_id = ? AND stock = ?;", user_id, symbol)

        if existing_row:
            # Update the existing row with new information
            existing_amount = existing_row[0]["amount"]
            existing_cost = existing_row[0]["cost"]
            new_amount = existing_amount + amount
            new_cost = existing_cost + total_cost
            db.execute("UPDATE user_stocks SET amount = ?, cost = ? WHERE user_id = ? AND stock = ?;", new_amount, new_cost, user_id, symbol)
        else:
        # insert purchase into portfolio
            status = "purchased"
            today = date.today()
            db.execute("INSERT INTO user_stocks (user_id, stock, price, date, amount, cost, status) VALUES (?, ?, ?, ?, ?, ?, ?);", user_id, symbol, price, today, amount, total_cost, status)

        return render_template("buy.html", name=name, price=price, total_cost=total_cost, remaining_balance=cash, status=status)

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":
        stock = request.form.get("symbol")
        result = []
        result = lookup(stock)
        if result == None:
            return apology("Stock does not exist!")

        symbol = result["symbol"]
        price = result["price"]
        name = result["name"]

        return render_template("quoted.html", name=name, price=price, symbol=symbol)

    else:
        return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        v_password = request.form.get("v_password")

        """ if blank """
        if len(username) < 1 or len(password) < 1 or len(v_password) < 1:
            return apology("Please enter username or password!")

        """ check if passwords are the same """
        if password != v_password:
            return apology("Passwords do not match!")

        """ generate password hash """
        hashed_password = generate_password_hash(password)

        """ insert user into db """
        """ check for existing username"""
        try:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?);", username, hashed_password)
        except ValueError:
            return apology("Username taken")

        """ log user in """
        user_id = db.execute("SELECT id FROM users WHERE username = (?);", username)
        session["user_id"] = user_id

        return render_template("login.html")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "POST":
        user_id = session["user_id"]
        # get data from HTML
        symbol = request.form.get("symbol")
        amount = int(request.form.get("shares"))
        # get stock date from HTML
        user_symbol = db.execute("SELECT stock FROM user_stocks WHERE stock=?;", symbol)
        user_amount = db.execute("SELECT amount FROM user_stocks WHERE stock=?;", symbol)
        user_amount = user_amount[0]["amount"]

        # check for negative or '0' amount:
        if amount < 1:
            return apology("Please enter valid amount of shares")
        # if amount to be sold is more than amount held
        if amount > user_amount:
            return apology("You do not have enough shares")

        # sell specified number of shares:
        # lookup current price of shares:
        stock_information = lookup(symbol)
        current_price = int(stock_information["price"])

        # multiply amount by current price of share:
        total_price = current_price * amount

        # update user's cash:
        current_cash = db.execute("SELECT cash FROM users WHERE id=?;", user_id)
        current_cash = current_cash[0]["cash"]
        cash = current_cash + total_price
        db.execute("UPDATE users SET cash = ? WHERE id = ?;", cash, user_id)

        # remove stock listing if amount = 0:
        amount = user_amount - amount
        if amount == 0:
            db.execute("DELETE FROM user_stocks WHERE user_id = ? AND stock = ?;", user_id, symbol)

        # update users stock listing amount if not = 0:
        db.execute("UPDATE user_stocks SET amount = ? WHERE user_id = ? AND stock = ?;", amount, user_id, symbol)
        symbols = db.execute("SELECT stock FROM user_stocks WHERE user_id=?;", user_id)
        status = "sold"
        return render_template("sell.html", name=symbol, price=current_price, total_cost=total_price, remaining_balance=cash, status=status, symbols=symbols)

    else:
        # generate list of stocks user has:
        user_id = session["user_id"]
        symbols = db.execute("SELECT stock FROM user_stocks WHERE user_id=?;", user_id)
        return render_template("sell.html", symbols=symbols)