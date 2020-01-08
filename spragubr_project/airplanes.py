from google.cloud import datastore
from flask import Blueprint, Flask, jsonify, make_response, request, redirect
import json
import jwt
import constants

client = datastore.Client()
bp = Blueprint('airplanes', __name__, url_prefix='/airplanes')

#############################################################################
# Create an airplane // Get an airplane
#############################################################################
@bp.route('', methods=constants.http_verbs)
def create_get_airplanes():
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
        if "model" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        if "max_gross_weight" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        if "max_capacity" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        else:
            new_airplane = datastore.entity.Entity(key=client.key(constants.airplanes))
            new_airplane.update({"model": content["model"],
                                 "max_gross_weight": content["max_gross_weight"],
                                 "max_capacity": content["max_capacity"],
                                 "created_by": owner,
                                 "flight": None})
            client.put(new_airplane)
            airplane_id = str(new_airplane.key.id)
            new_airplane["self"] = request.base_url + "/" + airplane_id
            new_airplane["id"] = airplane_id
            return jsonify(new_airplane), 201
    elif request.method == 'GET':
        query = client.query(kind=constants.airplanes)
        collection = query.fetch()
        count = 0
        for airplanes in collection:
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
        airplane_arr = []
        for airplanes in results:
            airplane_dict = {}
            airplane_dict["id"] = airplanes.key.id
            airplane_dict["model"] = airplanes["model"]
            airplane_dict["max_gross_weight"] = airplanes["max_gross_weight"]
            airplane_dict["max_capacity"] = airplanes["max_capacity"]
            airplane_dict["flight"] = airplanes["flight"]
            airplane_dict["created_by"] = airplanes["created_by"]
            airplane_dict["self"] = request.base_url + "/" + str(airplanes.key.id)
            airplane_arr.append(airplane_dict)
        output = {"airplanes": airplane_arr}
        output["count"] = count
        if next_url:
            output["next"] = next_url
        if q_offset > 0 and len(airplane_arr):
            prev_offset = q_offset - q_limit
            output["prev"] = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(prev_offset)
        return jsonify(output), 200
    else:
        res = make_response(jsonify(Error='Invalid HTTP Method used for request'))
        res.status_code = 405
        return res

#############################################################################
# Get an airplane // Edit an airplane // Delete an airplane
#############################################################################
@bp.route('<string:airplane_id>', methods=constants.http_verbs)
def get_edit_and_delete_airplane(airplane_id):
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
    airplane_key = client.key(constants.airplanes, int(airplane_id))
    airplane = client.get(key=airplane_key)
    if airplane is None:
        return jsonify(Error='No airplane with this airplane_id exists'), 404
    else:
        if airplane["created_by"] != owner:
            res = make_response(
                jsonify(Error='You do not have authorization to access this entity'))
            res.status_code = 401
            return res

    if request.method == 'GET':
        airplane["id"] = airplane_id
        airplane["self"] = request.base_url
        return jsonify(airplane), 200
    elif request.method == 'PATCH' or request.method == 'PUT':
        content = request.get_json()
        if "model" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        if "max_gross_weight" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        if "max_capacity" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        else:
            airplane.update({"model": content["model"],
                             "max_gross_weight": content["max_gross_weight"],
                             "max_capacity":content["max_capacity"]})
            client.put(airplane)
            airplane["id"] = airplane_id
            airplane["self"] = request.base_url
            return jsonify(airplane), 200
    elif request.method == 'DELETE':
        if airplane["flight"] is not None:
            flight_key = client.key(constants.flights, int(airplane["flight"]["id"]))
            flight = client.get(key=flight_key)
            flight.update({"airplane": None})
            client.put(flight)
        client.delete(airplane_key)
        return '', 204
    else:
        res = make_response(jsonify(Error='Invalid HTTP Method used for request'))
        res.status_code = 405
        return res