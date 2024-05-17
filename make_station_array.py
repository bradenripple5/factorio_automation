from convert_json_to_blueprint_string import *
from make_station import *
import json

with open("blueprints\\skeleton_scaffold.json") as f:
	blueprint = json.loads(f.read())
