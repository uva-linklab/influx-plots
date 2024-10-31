Influx Plots
============

A simple webserver to generate plots with InfluxDB data on the fly.


Configuration
-------------

You need to create a config file like:

```
[influx]
INFLUXDB_USERNAME=username
INFLUXDB_PASSWORD=password
INFLUX_HOST=hostname
```

and provide the path to the config file as the argument to the Python script.
