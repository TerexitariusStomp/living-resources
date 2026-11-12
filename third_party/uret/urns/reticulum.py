# µReticulum Core Engine
# Simplified for Pico W: JSON config, no RPC, async event loop

import os
import gc
import time
from . import const
from .log import log, set_loglevel, LOG_VERBOSE, LOG_DEBUG, LOG_ERROR, LOG_NOTICE, LOG_INFO
from .identity import Identity
from .transport import Transport
from .interfaces import Interface as _BaseInterface

IFACE_DEFAULT_GRAVITY = _BaseInterface.DEFAULT_GRAVITY


class Reticulum:
    # Protocol constants (also accessible via const module)
    MTU = const.MTU
    TRUNCATED_HASHLENGTH = const.TRUNCATED_HASHLENGTH
    HEADER_MAXSIZE = const.HEADER_MAXSIZE
    MDU = const.MDU
    DEFAULT_PER_HOP_TIMEOUT = const.DEFAULT_PER_HOP_TIMEOUT

    _instance = None
    _use_implicit_proof = True

    def __init__(self, config_path="/rns/config.json", loglevel=None):
        if loglevel is not None:
            set_loglevel(loglevel)

        gc.collect()
        Reticulum._instance = self

        self.is_connected_to_shared_instance = False
        self.config = {}
        self.interfaces = []
        self.probe_destination = None

        # Derive storage directory from config path
        if "/" in config_path:
            self.storagepath = config_path[:config_path.rfind("/")]
        else:
            self.storagepath = "."

        # Ensure storage directory exists
        self._ensure_dir(self.storagepath)
        self._ensure_dir(self.storagepath + "/ratchets")

        # Load or create identity
        Identity.storagepath = self.storagepath
        self.identity = self._load_or_create_identity()

        # Load config
        self._load_config(config_path)

        # Load known destinations
        Identity.load_known_destinations()

        # Start transport
        Transport.start(self)

        log("µReticulum v0.1.0 started", LOG_NOTICE)
        log("Identity: " + self.identity.hexhash, LOG_INFO)
        log("Free memory: " + str(gc.mem_free()) + " bytes", LOG_VERBOSE)

    def _load_or_create_identity(self):
        identity_path = self.storagepath + "/identity"
        if self._file_exists(identity_path):
            identity = Identity.from_file(identity_path)
            if identity:
                log("Loaded identity from storage", LOG_VERBOSE)
                return identity
        # Create new identity
        identity = Identity()
        identity.to_file(identity_path)
        log("Created new identity", LOG_VERBOSE)
        return identity

    def _load_config(self, config_path):
        try:
            import json
            if self._file_exists(config_path):
                with open(config_path, "r") as f:
                    self.config = json.load(f)
                log("Loaded configuration from " + config_path, LOG_VERBOSE)
            else:
                self.config = self._default_config()
                with open(config_path, "w") as f:
                    json.dump(self.config, f)
                log("Created default configuration", LOG_VERBOSE)
        except Exception as e:
            log("Config error, using defaults: " + str(e), LOG_ERROR)
            self.config = self._default_config()

    def _default_config(self):
        return {
            "loglevel": 3,
            "enable_transport": False,
            "interfaces": [
                {
                    "type": "UDPInterface",
                    "name": "WiFi UDP",
                    "enabled": True,
           ...[2645 chars truncated]...", [])































































        )
        Transport.time_sync_min_sources = ts_cfg.get("min_sources", 2)
        Transport.time_sync_tolerance = ts_cfg.get("tolerance", 120)
        if Transport.time_sync_enabled:
            if Transport.time_sync_trusted:
                _mode = "trusted: " + str(len(Transport.time_sync_trusted))
            else:
                _mode = "corroborate: " + str(Transport.time_sync_min_sources) + " nodes"
            log("Time sync enabled (" + _mode + ")", LOG_NOTICE)

        for iface_config in self.config.get("interfaces", []):
            if not iface_config.get("enabled", True):
                continue
            iface_config = self._resolve_board(iface_config)
            itype = iface_config.get("type", "")
            modname = self._INTERFACE_MAP.get(itype)
            if modname is None:
                log("Unknown interface type: " + itype, LOG_ERROR)
                continue
            try:
                mod = __import__("urns.interfaces." + modname, None, None, (itype,))
                cls = getattr(mod, itype)
                iface = cls(iface_config)
                iface.setup_ifac(iface_config)
                # Pathing affinity: per-interface "gravity", else the network-wide
                # "default_gravity", else neutral. Higher wins a same-hop tie in
                # the path table — e.g. prefer WiFi over LoRa for a destination
                # both can reach (see Transport._handle_announce).
                try:
                    iface.gravity = int(iface_config.get(
                        "gravity", self.config.get("default_gravity",
                                                   IFACE_DEFAULT_GRAVITY)))
                except (TypeError, ValueError):
                    log("Invalid gravity for " + itype + ", using default", LOG_ERROR)
                    iface.gravity = IFACE_DEFAULT_GRAVITY
                self.interfaces.append(iface)
                Transport.register_interface(iface)
            except Exception as e:
                log("Interface " + itype + " init failed: " + str(e), LOG_ERROR)

        # Path-table persistence (transport nodes): reload cached routes on boot so
        # a reboot isn't a mesh blackout. Periodic saves run in job_loop; a final
        # save runs on shutdown. Interfaces must be registered first (above) so a
        # restored route can re-resolve its interface by name.
        _storage = getattr(self, "storagepath", None)
        if Transport.transport_enabled and _storage:
            try:
                Transport.persist_path = _storage + "/path_table"
                Transport.load_path_table(Transport.persist_path)
            except Exception as e:
                log("Path persistence init failed: " + str(e), LOG_ERROR)

        self._setup_probe_destination()

    def _setup_probe_destination(self):
        """Optionally expose a probe destination that replies to rnprobe.
        Mirrors upstream Transport.probe_destination (Reticulum Transport.py:399)."""
        probe_cfg = self.config.get("probe", {})
        if not probe_cfg.get("enabled", False):
            return
        from .destination import Destination
        app_name = probe_cfg.get("app_name", "urns")
        aspect = probe_cfg.get("aspect", "probe")
        self.probe_destination = Destination(
            self.identity, Destination.IN, Destination.SINGLE,
            app_name, aspect,
        )
        self.probe_destination.accepts_links(False)
        self.probe_destination.set_proof_strategy(Destination.PROVE_ALL)
        print("Probe address:", self.probe_destination.hexhash,
              "(" + app_name + "." + aspect + ")")

    async def run(self):
