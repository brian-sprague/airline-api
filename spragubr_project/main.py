#############################################################################
# Author: Brian Sprague
# Assignment: Project
# Description: Implements the airline API as described in the accompanying
# API documentation.
# Sources cited:

#############################################################################


from google.cloud import datastore
from flask import Flask, request, render_template
import json
import constants
import airplanes
import flights
import pilots
import users


app = Flask(__name__)
client = datastore.Client()
app.register_blueprint(airplanes.bp)
app.register_blueprint(flights.bp)
app.register_blueprint(pilots.bp)
app.register_blueprint(users.bp)

# login_url = 'http://127.0.0.1:8080/users/login'
# reg_url = 'http://127.0.0.1:8080/users/new_account'


login_url = 'https://spragubr-project-airline.appspot.com/users/login'
reg_url = 'https://spragubr-project-airline.appspot.com/users/new_account'

@app.route('/')
def index():
    return render_template('index.html', login_uri=login_url, register_uri=reg_url)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
