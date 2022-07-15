import argparse
import logging
import os
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from model_training import lookalike_model
from pymongo import MongoClient
from dotenv import load_dotenv
from bson.objectid import ObjectId
load_dotenv()


# creating the default paser arguments
def create_argument_parser():
  parser = argparse.ArgumentParser(description='parse arguments')

  parser.add_argument(
    '-H', '--host',
    type=str,
    default='0.0.0.0',
    help='hostname to listen on')

  parser.add_argument(
    '-P', '--port',
    type=int,
    default=5000,
    help='server port')
  parser.add_argument(
    '--debug',
    action='store_true',
    default=False,
    help='if given, enable or disable debug mode')

  return parser


# creating_app using the flask
def create_app(test_config=None):
    # create and configure the app
    flask_app = Flask(__name__)


    if test_config is None:
      # load the instance config, if it exists, when not testing
      # load configs
      config_class = os.getenv('FK_APP_CONFIG',
                               'configs.DefaultConfig')
      flask_app.config.from_object(config_class)

    else:
      # load the test config if passed in
      flask_app.config.from_mapping(test_config)

    business_client = flask_app.config['BUSINESS_CLIENT']

    client = MongoClient(os.getenv('DB_URI'))
    db = client[os.getenv('DB_NAME')]

    audience_collection = db["audiences"]

    @flask_app.errorhandler(ValueError)
    def handle_value_error(ex):
      flask_app.logger.error(f"{ex}")
      response = jsonify({
        "message": f"{ex}"
      })
      response.status_code = 404
      return response

    @flask_app.errorhandler(KeyError)
    def handle_key_error(ex):
      flask_app.logger.error(f"{ex}")
      response = jsonify({
        "message": f"{ex}"
      })
      response.status_code = 404
      return response

    @flask_app.errorhandler(HTTPException)
    def handle_exception(ex):
      flask_app.logger.error(str(ex))
      response = jsonify({
        "message": ex.description
      })
      response.status_code = ex.code
      return response

    # todo: remove this handler
    @flask_app.errorhandler(Exception)
    def handle_exception(ex):
      flask_app.logger.exception(f"Unexpected runtime error: {ex}")
      response = jsonify({
        "message": "Unexpected runtime error"
      })
      response.status_code = 500
      return response

    # health check
    @flask_app.route('/', methods=['GET', 'POST'])
    def hello():
      return "Hello from lookalike model serving app"

    @flask_app.route(f'/{business_client}/lookalike/api/v1/audiences',
                      methods=['POST'])
    def get_score():
        req_json = request.get_json() if request.is_json else dict()
        audience_id = req_json.get('audiences')
        size = req_json.get('size')
        lat = req_json.get('lat')
        long = req_json.get('long')
        distance = req_json.get('distance')
        if not audience_id or not size or not lat or not long or not distance:
          return jsonify({"Code": 400, "Message": "Invalid Input"})

        try:
          # Get the lead details from the database.
          data = audience_collection.find_one({"_id": ObjectId(audience_id)}, {"_id":1})
        except:
          data = None

        if not data:
          return jsonify({"Code": 400, "Message": "The audience id is not available. Please check!"})

        coords = (lat, long)
        response = lookalike_model(audience_id, size, coords, distance).json
        return response

    # return app object
    return flask_app


if __name__ == '__main__':
  "run server"

  arg_parser = create_argument_parser()
  cmdline_args = arg_parser.parse_args()

  logging.getLogger().setLevel(logging.INFO)

  app = create_app()
  app.run(host=cmdline_args.host, port=cmdline_args.port, debug=cmdline_args.debug)
