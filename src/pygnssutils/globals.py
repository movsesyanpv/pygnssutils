"""
Global variables for pygnssutils.

Created on 26 May 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

OUTPORT = 50010
OUTPORT_NTRIP = 2101
DEFAULT_TLS_PORTS = (443, 2102)
MIN_NMEA_PAYLOAD = 3  # minimum viable length of NMEA message payload
EARTH_RADIUS = 6371  # km
DEFAULT_BUFSIZE = 4096  # buffer size for NTRIP client
MAXPORT = 65535  # max valid TCP port
FORMAT_PARSED = 1
FORMAT_BINARY = 2
FORMAT_HEX = 4
FORMAT_HEXTABLE = 8
FORMAT_PARSEDSTRING = 16
FORMAT_JSON = 32
VERBOSITY_LOW = 0
VERBOSITY_MEDIUM = 1
VERBOSITY_HIGH = 2
VERBOSITY_DEBUG = 3
DISCONNECTED = 0
CONNECTED = 1
LOGLIMIT = 1000  # max lines in logfile
NOGGA = -1
EPILOG = "© 2022 SEMU Consulting BSD 3-Clause license - https://github.com/semuconsulting/pygnssutils/"

GNSSLIST = {
    0: "GPS",
    1: "SBAS",
    2: "Galileo",
    3: "BeiDou",
    4: "IMES",
    5: "QZSS",
    6: "GLONASS",
}

FIXES = {
    "3D": 1,
    "2D": 2,
    "RTK FIXED": 4,
    "RTK FLOAT": 5,
    "RTK": 5,
    "DR": 6,
    "NO FIX": 0,
}

HTTPERR = [
    "400 Bad Request",
    "401 Unauthorized",
    "403 Forbidden",
    "404 Not Found",
    "405 Method Not Allowed",
    "406 Not Acceptable",
]

# ranges for ubxsetrate CLI
ALLNMEA = "allnmea"
ALLUBX = "allubx"
MINNMEA = "minnmea"
MINUBX = "minubx"
ALLNMEA_CLS = [b"\xF0", b"\xF1"]
MINMMEA_ID = [b"\xF0\x00", b"\xF0\x02", b"\xF0\x03", b"\xF0\x04", b"\xF0\x05"]
ALLUBX_CLS = [b"\x01"]
MINUBX_ID = [b"\x01\x07", b"\x01\x35"]

TOPIC_KEY = "/pp/ubx/0236/{}"
TOPIC_ASSIST = "/pp/ubx/mga"
TOPIC_DATA = "/pp/{}/{}"
TOPIC_FREQ = "/pp/frequencies/Lb"
NTRIP_EVENT = "<<ntrip_read>>"
SPARTN_EVENT = "<<spartn_read>>"
SPARTN_PPSERVER = "pp.services.u-blox.com"
OUTPORT_SPARTN = 8883
PMP_DATARATES = {
    "B600": 600,
    "B1200": 1200,
    "B2400": 2400,
    "B4800": 4800,
}

# Center point of rectangular regions mapped to the
# SPARTN MQTT PointPerfect region name
REGION_MAPPING = {
    (-26.55, 134.70): "au",
    (52.45, 011.85): "eu",
    (38.95, 139.60): "jp",  # East
    (33.10, 132.20): "jp",  # West
    (36.30, 128.20): "kr",
    (39.20, -096.60): "us",
}

HTTPCODES = {
    200: "OK",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
}

# map of fix values to descriptions
# the keys in this map are a concatenation of NMEA/UBX
# message identifier and attribute value e.g.:
# GGA1: GGA + quality = 1
# NAV-STATUS3: NAV-STATUS + gpsFix = 3
# (valid for NMEA >=4)
FIXLOOKUP = {
    "GGA1": "3D",  # quality
    "GGA2": "3D",
    "GGA4": "RTK FIXED",
    "GGA5": "RTK FLOAT",
    "GGA6": "DR",
    "GLLA": "3D",  # posMode
    "GLLD": "RTK",
    "GLLE": "DR",
    "GNSA": "3D",  # posMode
    "GNSD": "3D",
    "GNSF": "RTK FLOAT",
    "GNSR": "RTK FIXED",
    "GNSE": "DR",
    "RMCA": "3D",  # posMode
    "RMCD": "3D",
    "RMCF": "RTK FLOAT",
    "RMCR": "RTK FIXED",
    "RMCE": "DR",
    "VTGA": "3D",  # posMode
    "VTGD": "RTK",
    "VTGE": "DR",
    "NAV-PVT1": "DR",  # fixType
    "NAV-PVT2": "2D",
    "NAV-PVT3": "3D",
    "NAV-PVT4": "GNSS+DR",
    "NAV-PVT5": "TIME ONLY",
    "NAV-PVT6": "RTK FLOAT",  # carrSoln
    "NAV-PVT7": "RTK FIXED",
    "NAV-STATUS1": "DR",  # gpsFix
    "NAV-STATUS2": "3D",
    "NAV-STATUS3": "3D",
    "NAV-STATUS4": "GNSS+DR",
    "NAV-STATUS5": "TIME ONLY",
    "NAV-STATUS6": "RTK FLOAT",  # carrSoln
    "NAV-STATUS7": "RTK FIXED",
    "NAV-SOL1": "DR",  # gpsFix
    "NAV-SOL2": "3D",
    "NAV-SOL3": "3D",
    "NAV-SOL4": "GNSS+DR",
    "NAV-SOL5": "TIME ONLY",
    "HNR-PVT1": "DR",  # gpsFix
    "HNR-PVT2": "2D",
    "HNR-PVT3": "3D",
    "HNR-PVT4": "GNSS+DR",
    "HNR-PVT5": "TIME ONLY",
    "HNR-PVT6": "RTK",
    "NAV2-PVT1": "DR",  # fixType
    "NAV2-PVT2": "2D",
    "NAV2-PVT3": "3D",
    "NAV2-PVT4": "GNSS+DR",
    "NAV2-PVT5": "TIME ONLY",
    "NAV2-PVT6": "RTK FLOAT",  # carrSoln
    "NAV2-PVT7": "RTK FIXED",
    "NAV2-STATUS1": "DR",  # gpsFix
    "NAV2-STATUS2": "3D",
    "NAV2-STATUS3": "3D",
    "NAV2-STATUS4": "GNSS+DR",
    "NAV2-STATUS5": "TIME ONLY",
    "NAV2-STATUS6": "RTK FLOAT",  # carrSoln
    "NAV2-STATUS7": "RTK FIXED",
}
