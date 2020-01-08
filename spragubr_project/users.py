from google.cloud import datastore
from flask import Blueprint, Flask, jsonify, make_response, request, redirect, render_template
from passlib.context import CryptContext
import json
import jwt
import datetime
import constants

client = datastore.Client()
bp = Blueprint('users', __name__, url_prefix='/users')
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto"
)

#############################################################################
# Create a user
#############################################################################
@bp.route('/new_account', methods=constants.http_verbs)
def create_account():
    if request.method == 'POST':
        content = request.form
        new_user = datastore.entity.Entity(key=client.key(constants.users))
        hashed_pwd = pwd_context.hash(content["password"])
        new_user.update({"username": content["username"],
                         "password": hashed_pwd})
        client.put(new_user)
        return redirect(request.url_root)
    elif request.method == 'GET':
        return render_template('create_account.html', req_url=request.base_url)
    else:
        res = make_response(jsonify(Error='Invalid HTTP Method used for request'))
        res.status_code = 405
        return res

#############################################################################
# Verify a user
#############################################################################
@bp.route('/login', methods=constants.http_verbs)
def login():
    if request.method == 'POST':
        content = request.form
        query = client.query(kind=constants.users)
        results = list(query.fetch())
        for users in results:
            if users["username"] == content["username"]:
                if pwd_context.verify(content["password"], users["password"]):
                    #make jwt
                    enc_jwt = jwt.encode({'user' : users["username"],
                                          'id' : str(users.key.id),
                                          'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=60)},
                                          constants.my_secret,
                                          algorithm='HS256').decode('utf-8')
                    return render_template('user.html', username=users["username"], uid=str(users.key.id), jwToken=enc_jwt)
                else:
                    return redirect(request.base_url)
        return redirect(request.url_root + 'users/new_account')
    elif request.method == 'GET':
        return render_template('login.html', req_url=request.base_url)
    else:
        res = make_response(jsonify(Error='Invalid HTTP Method used for request'))
        res.status_code = 405
        return res

#############################################################################
# Get a user's entities
#############################################################################
@bp.route('/<string:user_id>/created', methods=constants.http_verbs)
def get_created_entities(user_id):
    if request.method == 'GET':
        # Get the JWT from the header
        header = request.headers.items()
        header_list = list(header)
        for items in header_list:
            if items[0] == "Authorization":
                token = items[1]
                token = str(token[7:])
            if items[0] == "Accept":
                if items[1] != "application/json":
                    res = make_response(jsonify(Error="Accept header is not set to ‘application/json’"))
                    res.status_code = 406
                    return res

        # verify the JWT
        try:
            id_info = jwt.decode(token, constants.my_secret, algorithms='HS256')
        except:
            res = make_response(jsonify(Error='A valid JWT is missing from the Authorization header in the request'))
            res.status_code = 401
            return res
        owner = id_info["id"]
        if owner != user_id:
            res = make_response(jsonify(Error="You do not have permission to access this endpoint"))
            res.status_code = 401
            return res
        output = []
        # Get Airplanes
        query = client.query(kind=constants.airplanes)
        results = query.fetch()
        airplane_arr = []
        for airplanes in results:
            if owner == airplanes["created_by"]:
                airplane_dict = {}
                airplane_dict["id"] = airplanes.key.id
                airplane_dict["model"] = airplanes["model"]
                airplane_dict["max_gross_weight"] = airplanes["max_gross_weight"]
                airplane_dict["max_capacity"] = airplanes["max_capacity"]
                airplane_dict["flight"] = airplanes["flight"]
                airplane_dict["created_by"] = airplanes["created_by"]
                airplane_dict["self"] = request.url_root + "airplanes/" + str(airplanes.key.id)
                airplane_arr.append(airplane_dict)
        output.append({"airplanes": airplane_arr})
        # Get Pilots
        query = client.query(kind=constants.pilots)
        results = query.fetch()
        pilot_arr = []
        for pilots in results:
            if owner == pilots["created_by"]:
                pilot_dict = {}
                pilot_dict["id"] = pilots.key.id
                pilot_dict["first_name"] = pilots["first_name"]
                pilot_dict["last_name"] = pilots["last_name"]
                pilot_dict["captain_qual"] = pilots["captain_qual"]
                pilot_dict["first_officer_qual"] = pilots["first_officer_qual"]
                pilot_dict["flight"] = pilots["flight"]
                pilot_dict["created_by"] = pilots["created_by"]
                pilot_dict["self"] = request.url_root + "pilots/" + str(pilots.key.id)
                pilot_arr.append(pilot_dict)
        output.append({"pilots": pilot_arr})
        # Get Flights
        query = client.query(kind=constants.flights)
        results = query.fetch()
        flight_arr = []
        for flights in results:
            if owner == flights["created_by"]:
                flight_dict = {}
                flight_dict["id"] = flights.key.id
                flight_dict["destination"] = flights["destination"]
                flight_dict["flight_time"] = flights["flight_time"]
                flight_dict["inflight_meal"] = flights["inflight_meal"]
                flight_dict["airplane"] = flights["airplane"]
                flight_dict["captain"] = flights["captain"]
                flight_dict["first_officer"] = flights["first_officer"]
                flight_dict["created_by"] = flights["created_by"]
                flight_dict["self"] = request.url_root + "flights/" + str(flights.key.id)
                flight_arr.append(flight_dict)
        output.append({"flights": flight_arr})
        return jsonify(output), 200
    else:
        res = make_response(jsonify(Error='Invalid HTTP Method used for request'))
        res.status_code = 405
        return res