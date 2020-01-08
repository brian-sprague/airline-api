from google.cloud import datastore
from flask import Blueprint, Flask, jsonify, make_response, request, redirect
import json
import jwt
import constants

client = datastore.Client()
bp = Blueprint('flights', __name__, url_prefix='/flights')

#############################################################################
# Create an flight // Get an flight
#############################################################################
@bp.route('', methods=constants.http_verbs)
def create_get_flights():
    if request.method == 'POST':

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

        content = request.get_json()
        if "destination" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        if "flight_time" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        if "inflight_meal" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        else:
            new_flight = datastore.entity.Entity(key=client.key(constants.flights))
            new_flight.update({"destination": content["destination"],
                               "flight_time": content["flight_time"],
                               "inflight_meal": content["inflight_meal"],
                               "created_by": owner,
                               "airplane": None,
                               "captain": None,
                               "first_officer": None})
            client.put(new_flight)
            flight_id = str(new_flight.key.id)
            new_flight["self"] = request.base_url + "/" + flight_id
            new_flight["id"] = flight_id
            return jsonify(new_flight), 201
    elif request.method == 'GET':
        query = client.query(kind=constants.flights)
        collection = query.fetch()
        count = 0
        for flights in collection:
            count += 1
        q_limit = int(request.args.get('limit', '5'))
        q_offset = int(request.args.get('offset', '0'))
        l_iterator = query.fetch(limit=q_limit, offset=q_offset)
        pages = l_iterator.pages
        results = list(next(pages))
        if l_iterator.next_page_token:
            next_offset = q_offset + q_limit
            next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
        else:
            next_url = None
        flight_arr = []
        for flights in results:
            flight_dict = {}
            flight_dict["id"] = flights.key.id
            flight_dict["destination"] = flights["destination"]
            flight_dict["flight_time"] = flights["flight_time"]
            flight_dict["inflight_meal"] = flights["inflight_meal"]
            flight_dict["airplane"] = flights["airplane"]
            flight_dict["captain"] = flights["captain"]
            flight_dict["first_officer"] = flights["first_officer"]
            flight_dict["created_by"] = flights["created_by"]
            flight_dict["self"] = request.base_url + "/" + str(flights.key.id)
            flight_arr.append(flight_dict)
        output = {"flights": flight_arr}
        output["count"] = count
        if next_url:
            output["next"] = next_url
        if q_offset > 0 and len(flight_arr):
            prev_offset = q_offset - q_limit
            output["prev"] = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(prev_offset)
        return jsonify(output), 200
    else:
        res = make_response(jsonify(Error='Invalid HTTP Method used for request'))
        res.status_code = 405
        return res

#############################################################################
# Get an flight // Edit an flight // Delete an flight
#############################################################################
@bp.route('<string:flight_id>', methods=constants.http_verbs)
def get_edit_and_delete_flight(flight_id):
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
    flight_key = client.key(constants.flights, int(flight_id))
    flight = client.get(key=flight_key)
    if flight is None:
        return jsonify(Error='No flight with this flight_id exists'), 404
    else:
        if flight["created_by"] != owner:
            res = make_response(
                jsonify(Error='You do not have authorization to access this entity'))
            res.status_code = 401
            return res

    if request.method == 'GET':
        flight["id"] = flight_id
        flight["self"] = request.base_url
        return jsonify(flight), 200
    elif request.method == 'PATCH' or request.method == 'PUT':
        content = request.get_json()
        if "destination" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        if "flight_time" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        if "inflight_meal" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        else:
            flight.update({"destination": content["destination"],
                          "flight_time": content["flight_time"],
                          "inflight_meal":content["inflight_meal"]})
            client.put(flight)
            flight["id"] = flight_id
            flight["self"] = request.base_url
            return jsonify(flight), 200
    elif request.method == 'DELETE':
        if flight["airplane"] is not None:
            airplane_key = client.key(constants.airplanes, int(flight["airplane"]["id"]))
            airplane = client.get(key=airplane_key)
            airplane.update({"flight": None})
            client.put(airplane)
        if flight["captain"] is not None:
            captain_key = client.key(constants.pilots, int(flight["captain"]["id"]))
            captain = client.get(key=captain_key)
            captain.update({"flight": None})
            client.put(captain)
        if flight["first_officer"] is not None:
            first_officer_key = client.key(constants.pilots, int(flight["first_officer"]["id"]))
            first_officer = client.get(key=first_officer_key)
            first_officer.update({"flight": None})
            client.put(first_officer)
        client.delete(flight_key)
        return '', 204
    else:
        res = make_response(jsonify(Error='Invalid HTTP Method used for request'))
        res.status_code = 405
        return res

#############################################################################
# Add airplane to flight // Remove airplane from flight
#############################################################################
@bp.route('<string:flight_id>/airplane/<string:airplane_id>', methods=constants.http_verbs)
def add_airplane_remove_airplane(flight_id, airplane_id):
    if request.method == 'PUT':
        airplane_key = client.key(constants.airplanes, int(airplane_id))
        airplane = client.get(key=airplane_key)
        if airplane is None:
            return jsonify(Error='The specified flight and/or airplane do not exist in the database'), 404
        flight_key = client.key(constants.flights, int(flight_id))
        flight = client.get(key=flight_key)
        if flight is None:
            return jsonify(Error='The specified flight and/or airplane do not exist in the database'), 404
        if airplane["flight"] is not None:
            return jsonify(Error='This airplane is already assigned to a flight'), 403
        if flight["airplane"] is not None:
            return jsonify(Error='This flight already has an airplane assigned to it'), 403
        airplane.update({"flight": {"id": str(flight_id),
                                    "self": request.url_root + 'flights/' + flight_id}})
        flight.update({"airplane": {"id": str(airplane_id),
                                    "self": request.url_root + 'airplanes/' +airplane_id}})
        client.put(airplane)
        client.put(flight)
        return '', 204
    elif request.method == 'DELETE':
        airplane_key = client.key(constants.airplanes, int(airplane_id))
        airplane = client.get(key=airplane_key)
        if airplane is None:
            return jsonify(Error='The specified flight and/or airplane do not exist in the database'), 404
        flight_key = client.key(constants.flights, int(flight_id))
        flight = client.get(key=flight_key)
        if flight is None:
            return jsonify(Error='The specified flight and/or airplane do not exist in the database'), 404
        if airplane["flight"] is None or airplane["flight"]["id"] != flight_id:
            return jsonify(Error='The specified airplane is not assigned to this flight'), 404
        airplane.update({"flight": None})
        flight.update({"airplane": None})
        client.put(airplane)
        client.put(flight)
        return ('', 204)
    else:
        res = make_response(jsonify(Error='Invalid HTTP Method used for request'))
        res.status_code = 405
        return res

#############################################################################
# Add captain to flight // Remove captain from flight
#############################################################################
@bp.route('<string:flight_id>/captain/<string:captain_id>', methods=constants.http_verbs)
def add_captain_remove_captain(flight_id, captain_id):
    if request.method == 'PUT':
        captain_key = client.key(constants.pilots, int(captain_id))
        captain = client.get(key=captain_key)
        if captain is None:
            return jsonify(Error='The specified flight and/or pilot do not exist in the database'), 404
        flight_key = client.key(constants.flights, int(flight_id))
        flight = client.get(key=flight_key)
        if flight is None:
            return jsonify(Error='The specified flight and/or pilot do not exist in the database'), 404
        if captain["flight"] is not None:
            return jsonify(Error='This pilot is already assigned to a flight as a Captain or a First Officer'), 403
        if flight["captain"] is not None:
            return jsonify(Error='This flight already has a Captain assigned to it'), 403
        if captain["captain_qual"] is False:
            return jsonify(Error='This pilot cannot be a Captain for this flight'), 403
        captain.update({"flight": {"id": str(flight_id),
                                   "self": request.url_root + 'flights/' + flight_id}})
        flight.update({"captain": {"id": str(captain_id),
                                   "self": request.url_root + 'pilots/' + captain_id}})
        client.put(captain)
        client.put(flight)
        return '', 204
    elif request.method == 'DELETE':
        captain_key = client.key(constants.pilots, int(captain_id))
        captain = client.get(key=captain_key)
        if captain is None:
            return jsonify(Error='The specified flight and/or pilot do not exist in the database'), 404
        flight_key = client.key(constants.flights, int(flight_id))
        flight = client.get(key=flight_key)
        if flight is None:
            return jsonify(Error='The specified flight and/or pilot do not exist in the database'), 404
        if captain["flight"] is None or captain["flight"]["id"] != flight_id:
            return jsonify(Error='The specified pilot is not assigned to this flight'), 404
        captain.update({"flight": None})
        flight.update({"captain": None})
        client.put(captain)
        client.put(flight)
        return ('', 204)
    else:
        res = make_response(jsonify(Error='Invalid HTTP Method used for request'))
        res.status_code = 405
        return res

#############################################################################
# Add first officer to flight // Remove first officer from flight
#############################################################################
@bp.route('<string:flight_id>/first_officer/<string:first_officer_id>', methods=constants.http_verbs)
def add_first_officer_remove_first_officer(flight_id, first_officer_id):
    if request.method == 'PUT':
        first_officer_key = client.key(constants.pilots, int(first_officer_id))
        first_officer = client.get(key=first_officer_key)
        if first_officer is None:
            return jsonify(Error='The specified flight and/or pilot do not exist in the database'), 404
        flight_key = client.key(constants.flights, int(flight_id))
        flight = client.get(key=flight_key)
        if flight is None:
            return jsonify(Error='The specified flight and/or pilot do not exist in the database'), 404
        if first_officer["flight"] is not None:
            return jsonify(Error='This pilot is already assigned to a flight as a Captain or a First Officer'), 403
        if flight["first_officer"] is not None:
            return jsonify(Error='This flight already has a First Officer assigned to it'), 403
        if first_officer["first_officer_qual"] is False:
            return jsonify(Error='This pilot cannot be a First Officer for this flight'), 403
        first_officer.update({"flight": {"id": str(flight_id),
                                         "self": request.url_root + 'flights/' + flight_id}})
        flight.update({"first_officer": {"id": str(first_officer_id),
                                         "self": request.url_root + 'pilots/' + first_officer_id}})
        client.put(first_officer)
        client.put(flight)
        return '', 204
    elif request.method == 'DELETE':
        first_officer_key = client.key(constants.pilots, int(first_officer_id))
        first_officer = client.get(key=first_officer_key)
        if first_officer is None:
            return jsonify(Error='The specified flight and/or pilot do not exist in the database'), 404
        flight_key = client.key(constants.flights, int(flight_id))
        flight = client.get(key=flight_key)
        if flight is None:
            return jsonify(Error='The specified flight and/or pilot do not exist in the database'), 404
        if first_officer["flight"] is None or first_officer["flight"]["id"] != flight_id:
            return jsonify(Error='The specified pilot is not assigned to this flight'), 404
        first_officer.update({"flight": None})
        flight.update({"first_officer": None})
        client.put(first_officer)
        client.put(flight)
        return ('', 204)
    else:
        res = make_response(jsonify(Error='Invalid HTTP Method used for request'))
        res.status_code = 405
        return res