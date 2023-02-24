"""
gnssmqttclient.py

Command line utility, installed with PyPi library pygnssutils,
which acts as an SPARTN MQTT client, retrieving correction data
from an IP (MQTT) source and (optionally) sending the data to a
designated writeable output medium (serial, file, socket, queue).

Includes provision to be invoked from within PyGPSClient tkinter
application (or any tkinter app which implements comparable
GUI update methods).

Thingstream > Location Services > PointPerfect Thing > Credentials
Default location for key files is user's HOME directory

Created on 20 Feb 2023

:author: semuadmin
:copyright: SEMU Consulting © 2023
:license: BSD 3-Clause
"""
# pylint: disable=invalid-name

from os import path, getenv
from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from queue import Queue
from datetime import datetime
from io import BytesIO, TextIOWrapper, BufferedWriter
from time import sleep
from threading import Thread, Event
import socket
from serial import Serial
import paho.mqtt.client as mqtt
from pyubx2 import (
    UBXReader,
    UBXParseError,
    SET,
)
from pyspartn import (
    SPARTNReader,
    SPARTNParseError,
    SPARTNMessageError,
    SPARTNStreamError,
)
from pygnssutils.globals import (
    VERBOSITY_LOW,
    VERBOSITY_MEDIUM,
    LOGLIMIT,
    OUTPORT_SPARTN,
    EPILOG,
    TOPIC_IP,
    TOPIC_MGA,
    TOPIC_RXM,
    SPARTN_PPSERVER,
    SPARTN_EVENT,
)
from pygnssutils.exceptions import ParameterError
from pygnssutils._version import __version__ as VERSION

TIMEOUT = 8


class GNSSMQTTClient:
    """
    SPARTN MQTT client class.
    """

    def __init__(self, app=None, **kwargs):
        """
        Constructor.

        :param object app: application from which this class is invoked (None)
        :param object verbosity: (kwarg) log verbosity (1 = medium)
        :param object logtofile: (kwarg) log to file (0 = False)
        :param object logpath: (kwarg) log file path (".")
        """

        self.__app = app  # Reference to calling application class (if applicable)
        self._validargs = True
        clientid = getenv("MQTTCLIENTID", default="enter-client-id")

        self._settings = {
            "server": SPARTN_PPSERVER,
            "port": OUTPORT_SPARTN,
            "clientid": clientid,
            "region": "eu",
            "topic_ip": 1,
            "topic_mga": 1,
            "topic_key": 1,
            "tlscrt": path.join(Path.home(), f"device-{clientid}-pp-cert.crt"),
            "tlskey": path.join(Path.home(), f"device-{clientid}-pp-key.pem"),
            "output": None,
        }

        self._timeout = kwargs.get("timeout", TIMEOUT)
        self.errevent = kwargs.get("errevent", Event())
        self._verbosity = int(kwargs.get("verbosity", VERBOSITY_MEDIUM))
        self._logtofile = int(kwargs.get("logtofile", 0))
        self._logpath = kwargs.get("logpath", ".")
        self._loglines = 0
        self._socket = None
        self._connected = False
        self._stopevent = Event()
        self._mqtt_thread = None

    def __enter__(self):
        """
        Context manager enter routine.
        """

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """
        Context manager exit routine.

        Terminates threads in an orderly fashion.
        """

        self.stop()

    @property
    def settings(self):
        """
        Getter for SPARTN IP settings.
        """

        return self._settings

    @property
    def connected(self):
        """
        Connection status getter.
        """

        return self._connected

    def start(self, **kwargs) -> int:
        """
        Start MQTT handler thread.

        :return: return code
        :rtype: int
        """

        try:
            for kwarg in [
                "server",
                "port",
                "clientid",
                "region",
                "topic_ip",
                "topic_mga",
                "topic_key",
                "tlscrt",
                "tlskey",
                "output",
            ]:
                if kwarg in kwargs:
                    self._settings[kwarg] = kwargs.get(kwarg)
            self._verbosity = int(kwargs.get("verbosity", self._verbosity))
            self._logtofile = int(kwargs.get("logtofile", self._logtofile))
            self._logpath = kwargs.get("logpath", self._logpath)

        except (ParameterError, ValueError, TypeError) as err:
            self._do_log(
                f"Invalid input arguments {kwargs}\n{err}\nType gnssntripclient -h for help.",
                VERBOSITY_LOW,
            )
            self._validargs = False
            return 0

        self._do_log(
            f"Starting MQTT client with arguments {self._settings}.",
            VERBOSITY_MEDIUM,
        )
        self._stopevent.clear()
        self._mqtt_thread = Thread(
            target=self._run,
            args=(
                self.__app,
                self._settings,
                self._timeout,
                self._stopevent,
            ),
            daemon=True,
        )
        self._mqtt_thread.start()
        return 1

    def stop(self):
        """
        Stop MQTT handler thread.
        """

        self._stopevent.set()
        self._mqtt_thread = None
        self._do_log(
            "MQTT Client Stopped.",
            VERBOSITY_MEDIUM,
        )

    def _run(
        self,
        app: object,
        settings: dict,
        timeout: int,
        stopevent: Event,
    ):
        """
        THREADED Run MQTT client thread.

        :param object app: calling application
        :param dict settings: dict of settings
        :param int timeout: connection timeout in seconds
        :param event stopevent: stop event
        """

        topics = []
        if settings["topic_ip"]:
            topics.append((TOPIC_IP.format(settings["region"]), 0))
        if settings["topic_mga"]:
            topics.append((TOPIC_MGA, 0))
        if settings["topic_key"]:
            topics.append((TOPIC_RXM, 0))
        userdata = {
            "gnss": settings["output"],
            "topics": topics,
            "app": app,
            "readevent": SPARTN_EVENT,
        }

        try:
            client = mqtt.Client(client_id=settings["clientid"], userdata=userdata)
            client.on_connect = self.on_connect
            client.on_message = self.on_message
            client.tls_set(certfile=settings["tlscrt"], keyfile=settings["tlskey"])
            i = 1
            while not stopevent.is_set():
                try:
                    client.connect(settings["server"], port=settings["port"])
                    break
                except Exception as err:  # pylint: disable=broad-exception-caught
                    if i > 4:
                        raise TimeoutError(
                            f"Unable to connect to {settings['server']}"
                            + f":{settings['port']} in {timeout} seconds. "
                        ) from err
                    self._do_log(f"Trying to connect {i} ...", VERBOSITY_MEDIUM)
                    sleep(timeout / 4)
                    i += 1

            client.loop_start()
            while not stopevent.is_set():
                # run the client loop in the same thread, as callback access gnss
                # client.loop(timeout=0.1)
                sleep(0.1)
        except (FileNotFoundError, TimeoutError) as err:
            stopevent.set()
            self._do_log(f"ERROR! {err}", VERBOSITY_MEDIUM)
            if app is not None:
                if hasattr(app, "dlg_spartnconfig"):
                    if hasattr(app.dlg_spartnconfig, "disconnect_ip"):
                        app.dlg_spartnconfig.disconnect_ip(f"ERROR! {err}")
            self.stop()
            self.errevent.set()

        finally:
            client.loop_stop()

    @staticmethod
    def on_connect(client, userdata, flags, rcd):  # pylint: disable=unused-argument
        """
        The callback for when the client receives a CONNACK response from the server.

        :param object client: client
        :param list userdata:  list of user defined data items
        :param list flags: optional flags
        :param int rcd: return status code
        """

        if rcd == 0:
            client.subscribe(userdata["topics"])
        else:
            print(f"PyPGSClient MQTT Client - Connection failed, rc: {rcd}!")

    @staticmethod
    def on_message(client, userdata, msg):  # pylint: disable=unused-argument
        """
        The callback for when a PUBLISH message is received from the server.
        Some MQTT topics may contain more than one UBX or SPARTN message in
        a single payload.

        :param list userdata: list of user defined data items
        :param object msg: SPARTN or UBX message topic content
        """

        def do_write(output: object, raw: bytes, parsed: object):
            """
            Send SPARTN data to designated output medium.

            If output is Queue, will send both raw and parsed data.

            :param object output: writeable output medium for SPARTN data
            :param bytes raw: raw data
            :param object parsed: parsed message
            """

            if output is None:
                print(parsed)
            else:
                if isinstance(output, (Serial, BufferedWriter)):
                    output.write(raw)
                elif isinstance(output, TextIOWrapper):
                    output.write(str(parsed))
                elif isinstance(output, Queue):
                    output.put((raw, parsed))
                elif isinstance(output, socket.socket):
                    output.sendall(raw)

        def do_notify(app: object):
            """
            Notify any calling app of SPARTN read event.

            :param object app: calling application
            """

            if hasattr(app, "appmaster"):
                if hasattr(app.appmaster, "event_generate"):
                    app.appmaster.event_generate("<<spartn_read>>")

        if msg.topic in (TOPIC_MGA, TOPIC_RXM):  # multiple UBX MGA or RXM messages
            ubr = UBXReader(BytesIO(msg.payload), msgmode=SET)
            try:
                for raw, parsed in ubr:
                    # userdata["gnss"].put((raw, parsed))
                    do_write(userdata["gnss"], raw, parsed)
                    do_notify(userdata["app"])
            except UBXParseError:
                parsed = f"MQTT UBXParseError {msg.topic} {msg.payload}"
                # userdata["gnss"].put((msg.payload, parsed))
                do_write(userdata["gnss"], msg.payload, parsed)
                do_notify(userdata["app"])
        else:  # SPARTN protocol message
            spr = SPARTNReader(BytesIO(msg.payload))
            try:
                for raw, parsed in spr:
                    # userdata["gnss"].put((raw, parsed))
                    do_write(userdata["gnss"], raw, parsed)
                    do_notify(userdata["app"])
            except (SPARTNMessageError, SPARTNParseError, SPARTNStreamError):
                parsed = f"MQTT SPARTNParseError {msg.topic} {msg.payload}"
                # userdata["gnss"].put((msg.payload, parsed))
                do_write(userdata["gnss"], msg.payload, parsed)
                do_notify(userdata["app"])

    def _app_update_status(self, status: bool, msg: tuple = None):
        """
        THREADED
        Update SPARTN connection status in calling application.

        :param bool status: SPARTN server connection status
        :param tuple msg: optional (message, color)
        """

        if hasattr(self.__app, "update_spartn_status"):
            self.__app.update_spartn_status(status, msg)

    def _do_log(
        self,
        message: object,
        loglevel: int = VERBOSITY_MEDIUM,
        timestamp: bool = True,
    ):
        """
        THREADED
        Write timestamped log message according to verbosity and logfile settings.

        :param object message: message or object to log
        :param int loglevel: log level for this message (0,1,2)
        :param bool timestamp: prefix message with timestamp (Y/N)
        """

        if timestamp:
            message = f"{datetime.now()}: {str(message)}"
        else:
            message = str(message)

        if self._verbosity >= loglevel:
            if self._logtofile:
                self._cycle_log()
                with open(self._logpath, "a", encoding="UTF-8") as log:
                    log.write(message + "\n")
                    self._loglines += 1
            else:
                print(message)

    def _cycle_log(self):
        """
        THREADED
        Generate new timestamped logfile path.
        """

        if not self._loglines % LOGLIMIT:
            tim = datetime.now().strftime("%Y%m%d%H%M%S")
            self._logpath = path.join(self._logpath, f"gnssspartnclient-{tim}.log")
            self._loglines = 0


def main():
    """
    CLI Entry point.

    :param int waittime: response wait time in seconds (3)
    :param: as per GNSSSPARTNClient constructor and run() method.
    :raises: ParameterError if parameters are invalid
    """
    # pylint: disable=raise-missing-from

    clientid = getenv("MQTTCLIENTID", default="enter-client-id")
    ap = ArgumentParser(
        description="Client ID can be read from environment variable MQTTCLIENTID",
        epilog=EPILOG,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)
    ap.add_argument(
        "-C",
        "--clientid",
        required=False,
        help="Client ID",
        default=clientid,
    )
    ap.add_argument(
        "-S",
        "--server",
        required=False,
        help="SPARTN MQTT server URL",
        default=SPARTN_PPSERVER,
    )
    ap.add_argument(
        "-P",
        "--port",
        required=False,
        help="SPARTN MQTT server port",
        type=int,
        default=OUTPORT_SPARTN,
    )
    ap.add_argument(
        "-R",
        "--region",
        required=False,
        help="SPARTN region code",
        choices=["us", "eu", "au", "kr"],
        default="eu",
    )
    ap.add_argument(
        "--topic_ip",
        required=False,
        help="Subscribe to SPARTN IP topic for the selected region",
        type=int,
        choices=[0, 1],
        default=1,
    )
    ap.add_argument(
        "--topic_mga",
        required=False,
        help="Subscribe to SPARTN MGA (Assist-Now) topic",
        type=int,
        choices=[0, 1],
        default=1,
    )
    ap.add_argument(
        "--topickey",
        required=False,
        help="Subscribe to SPARTN Key (RXM-SPARTNKEY) topic",
        type=int,
        choices=[0, 1],
        default=1,
    )
    ap.add_argument(
        "--tlscrt",
        required=False,
        help="Fully-qualified path to TLS cert (*.crt)",
        default=path.join(Path.home(), f"device-{clientid}-pp-cert.crt"),
    )
    ap.add_argument(
        "--tlskey",
        required=False,
        help="Fully-qualified path to TLS key (*.pem)",
        default=path.join(Path.home(), f"device-{clientid}-pp-key.pem"),
    )
    ap.add_argument(
        "--output",
        required=False,
        help="Output medium (defaults to stdout)",
        default=None,
    )
    ap.add_argument(
        "--verbosity",
        required=False,
        help="Log message verbosity 0 = low, 1 = medium, 2 = high",
        type=int,
        choices=[0, 1, 2],
        default=1,
    )
    ap.add_argument(
        "--logtofile",
        required=False,
        help="0 = log to stdout, 1 = log to file '/logpath/gnssspartnclient-timestamp.log'",
        type=int,
        choices=[0, 1],
        default=0,
    )
    ap.add_argument(
        "--logpath",
        required=False,
        help="Fully qualified path to logfile folder",
        default=".",
    )
    ap.add_argument(
        "--waittime",
        required=False,
        help="waitimer",
        type=float,
        default=0.5,
    )
    ap.add_argument(
        "--timeout",
        required=False,
        help="MQTT connection timeout (seconds)",
        type=int,
        default=TIMEOUT,
    )
    ap.add_argument(
        "--errevent",
        required=False,
        help="Error event",
        default=Event(),
    )

    args = ap.parse_args()
    kwargs = vars(args)
    try:
        with GNSSMQTTClient(None, **kwargs) as gsc:
            streaming = gsc.start(**kwargs)
            while (
                streaming and not kwargs["errevent"].is_set()
            ):  # run until error or user presses CTRL-C
                sleep(args.waittime)
            sleep(args.waittime)

    except (KeyboardInterrupt, TimeoutError):
        gsc.stop()


if __name__ == "__main__":
    main()
