from google.cloud import datastore
from flask import Blueprint, Flask, jsonify, make_response, request, redirect
import json
import jwt
import constants

client = datastore.Client()
bp = Blueprint('pilots', __name__, url_prefix='/pilots')

#############################################################################
# Create an pilot // Get an pilot
#############################################################################
@bp.route('', methods=constants.http_verbs)
def create_get_pilots():
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
        if "first_name" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        if "last_name" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        if "captain_qual" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        if "first_officer_qual" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        else:
            new_pilot = datastore.entity.Entity(key=client.key(constants.pilots))
            new_pilot.update({"first_name": content["first_name"],
                              "last_name": content["last_name"],
                              "captain_qual": content["captain_qual"],
                              "first_officer_qual": content["first_officer_qual"],
                              "created_by": owner,
                              "flight": None})
            client.put(new_pilot)
            pilot_id = str(new_pilot.key.id)
            new_pilot["self"] = request.base_url + "/" + pilot_id
            new_pilot["id"] = pilot_id
            return jsonify(new_pilot), 201
    elif request.method == 'GET':
        query = client.query(kind=constants.pilots)
        collection = query.fetch()
        count = 0
        for pilots in collection:
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
        pilot_arr = []
        for pilots in results:
            pilot_dict = {}
            pilot_dict["id"] = pilots.key.id
            pilot_dict["first_name"] = pilots["first_name"]
            pilot_dict["last_name"] = pilots["last_name"]
            pilot_dict["captain_qual"] = pilots["captain_qual"]
            pilot_dict["first_officer_qual"] = pilots["first_officer_qual"]
            pilot_dict["flight"] = pilots["flight"]
            pilot_dict["created_by"] = pilots["created_by"]
            pilot_dict["self"] = request.base_url + "/" + str(pilots.key.id)
            pilot_arr.append(pilot_dict)
        output = {"pilots": pilot_arr}
        output["count"] = count
        if next_url:
            output["next"] = next_url
        if q_offset > 0 and len(pilot_arr):
            prev_offset = q_offset - q_limit
            output["prev"] = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(prev_offset)
        return jsonify(output), 200
    else:
        res = make_response(jsonify(Error='Invalid HTTP Method used for request'))
        res.status_code = 405
        return res

#############################################################################
# Get an pilot // Edit an pilot // Delete an pilot
#############################################################################
@bp.route('<string:pilot_id>', methods=constants.http_verbs)
def get_edit_and_delete_pilot(pilot_id):
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
    pilot_key = client.key(constants.pilots, int(pilot_id))
    pilot = client.get(key=pilot_key)
    if pilot is None:
        return jsonify(Error='No pilot with this pilot_id exists'), 404
    else:
        if pilot["created_by"] != owner:
            res = make_response(
                jsonify(Error='You do not have authorization to access this entity'))
            res.status_code = 401
            return res

    if request.method == 'GET':
        pilot["id"] = pilot_id
        pilot["self"] = request.base_url
        return jsonify(pilot), 200
    elif request.method == 'PATCH' or request.method == 'PUT':
        content = request.get_json()
        if "first_name" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        if "last_name" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        if "captain_qual" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        if "first_officer_qual" not in content:
            return jsonify(Error='The request object is missing at least one of the required attributes'), 400
        else:
            pilot.update({"first_name": content["first_name"],
                          "last_name": content["last_name"],
                          "captain_qual":content["captain_qual"],
                          "first_officer_qual":content["first_officer_qual"]})
            client.put(pilot)
            pilot["id"] = pilot_id
            pilot["self"] = request.base_url
            return jsonify(pilot), 200
    elif request.method == 'DELETE':
        if pilot["flight"] is not None:
            flight_key = client.key(constants.flights, int(pilot["flight"]["id"]))
            flight = client.get(key=flight_key)
            if flight["captain"] and flight["captain"]["id"] == pilot_id:
                flight.update({"captain": None})
            if flight["first_officer"] and flight["first_officer"]["id"] == pilot_id:
                flight.update({"first_officer": None})
            client.put(flight)
        client.delete(pilot_key)
        return '', 204
    else:
        res = make_response(jsonify(Error='Invalid HTTP Method used for request'))
        res.status_code = 405
        return res