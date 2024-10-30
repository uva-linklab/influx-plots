import configparser
import io
import sys

import arrow
import flask
import influxdb
import matplotlib
import matplotlib.pyplot


def convert_influx_time_to_datetime(time_str, timezone):
    t = arrow.Arrow.strptime(time_str[:19], "%Y-%m-%dT%H:%M:%S")
    return t.to(timezone).datetime


def get_longform_df(result_set, timezone="US/Eastern"):
    """
    Essentially converting the result set to long_form
    """
    df = {"time": [], "value": []}

    for p in result_set.get_points():
        df["time"].append(convert_influx_time_to_datetime(p["time"], timezone))
        df["value"].append(p["value"])

    return df


# Read in config parameters from a file passed as the first argument
config = configparser.ConfigParser(allow_unnamed_section=True)
config_file_name = sys.argv[1]
config.read(config_file_name)


# Initialize Flask app
app = flask.Flask(__name__)

# Avoid using matplotlib GUI
matplotlib.use("Agg")


# Initialize InfluxDB client
class Influx:
    def __init__(self):
        self.user = config.get(configparser.UNNAMED_SECTION, "INFLUXDB_USERNAME")
        self.password = config.get(configparser.UNNAMED_SECTION, "INFLUXDB_PASSWORD")
        self.host = config.get(configparser.UNNAMED_SECTION, "INFLUX_HOST")
        self.dbname = "gateway-generic"
        self.port = 443
        self.ssl = True
        self.client = self.get_client()

    def get_client(self, dbname="gateway-generic"):
        client = influxdb.InfluxDBClient(
            host=self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            database=self.dbname,
            ssl=self.ssl,
        )
        self.client = client
        return client

    def get_result_set(self, fieldname, add_param):
        q_str = 'SELECT * FROM "%s" WHERE %s' % (fieldname, add_param)
        client = self.client
        result_set = client.query(q_str)
        return result_set

    def get_device_query_adds(self, device_id_list):
        q_append = ""
        count = 0
        for device_id in device_id_list:
            if count == 0:
                q_append += "and (\"device_id\"='%s'" % device_id
            else:
                q_append += "or \"device_id\"='%s'" % device_id
            count += 1
        q_append += ")"
        return q_append

    # Get data from the past 1 hour
    def get_time_query_from_one_hr(self):
        tq = "time > now() - 1h "
        return tq


# Initialize Influx instance
inf = Influx()


# Flask route to get recent data and return it as an image
@app.route("/get_recent_data_image", methods=["GET"])
def get_recent_data_image():
    try:
        # Get device_id and fieldname from query parameters
        device_id = flask.request.args.get(
            "device_id", default="your_default_device_id"
        )
        # Default field name is co2_ppm
        fieldname = flask.request.args.get("fieldname", default="co2_ppm")

        # Query InfluxDB for data from the past 1 hour
        time_query = inf.get_time_query_from_one_hr()
        device_query = inf.get_device_query_adds([device_id])

        # Combine time and device queries
        full_query = time_query + device_query
        result_set = inf.get_result_set(fieldname, full_query)

        # Convert result set to a DataFrame
        df = get_longform_df(result_set)

        # If no data is found
        if len(df["time"]) == 0:
            return jsonify({"error": "No data found for the device."}), 404

        # Generate the plot using matplotlib
        matplotlib.pyplot.figure(figsize=(10, 6))
        matplotlib.pyplot.plot(df["time"], df["value"], label=fieldname, color="blue")

        # Add labels and title
        matplotlib.pyplot.xlabel("Time")
        matplotlib.pyplot.ylabel("Value")
        matplotlib.pyplot.title(f"{fieldname} data for device {device_id}")
        matplotlib.pyplot.legend()

        # Save plot to a BytesIO object
        img = io.BytesIO()
        matplotlib.pyplot.savefig(img, format="png")
        matplotlib.pyplot.close()
        img.seek(0)

        # Return the image as a response
        return flask.send_file(img, mimetype="image/png")

    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500


# Run Flask app
if __name__ == "__main__":
    app.run(host="localhost", port=5012)
