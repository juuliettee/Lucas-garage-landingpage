from flask import Flask, render_template, request ,redirect, url_for

app = Flask(__name__)

##like @GetMapping in Spring Boot
@app.route('/')
def home():
    garage_name = "Luca's Garage"
    return render_template('index.html', name=garage_name)