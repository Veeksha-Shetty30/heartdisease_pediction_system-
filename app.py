from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
import numpy as np
import pickle
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.linear_model import LogisticRegression
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'

model = pickle.load(open('model.pkl', 'rb'))
scaler = pickle.load(open('scaler.pkl', 'rb'))

DB_NAME = 'database.db'

# Initialize the database
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                input_data TEXT,
                result TEXT
            )
        ''')
        conn.commit()

init_db()

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']

        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT password FROM users WHERE username = ?", (uname,))
            record = c.fetchone()

            if record and check_password_hash(record[0], pwd):
                session['user'] = uname
                return redirect(url_for('form'))
            else:
                flash("INVALID CREDENTIAL", "error")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        hashed_pwd = generate_password_hash(pwd)

        try:
            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (uname, hashed_pwd))
                conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists.", "error")
    return render_template('register.html')

@app.route('/form', methods=['GET', 'POST'])
def form():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        input_data = [float(request.form[col]) for col in [
            'age','sex','cp','trestbps','chol','fbs','restecg','thalach','exang',
            'oldpeak','slope','ca','thal']]
        input_scaled = scaler.transform([input_data])
        prediction = model.predict(input_scaled)[0]
        result = "Yes" if prediction == 1 else "No"

        # Save prediction to database
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO predictions (username, input_data, result) VALUES (?, ?, ?)", 
                      (session['user'], json.dumps(input_data), result))
            conn.commit()

        return render_template('result.html', result=result)

    return render_template('form.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
