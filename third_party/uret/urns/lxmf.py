





























































































    # Verification
    SOURCE_UNKNOWN    = 0x01
    SIGNATURE_INVALID = 0x02

    # Sizes
    DESTINATION_LENGTH = Identity.TRUNCATED_HASHLENGTH // 8   # 16
    SIGNATURE_LENGTH   = Identity.SIGLENGTH // 8              # 64
    TIMESTAMP_SIZE     = 8
    TICKET_LENGTH      = 16   # reference LXMessage.TICKET_LENGTH (truncated hash size)
    STRUCT_OVERHEAD    = 8
    LXMF_OVERHEAD      = 2 * DESTINATION_LENGTH + SIGNATURE_LENGTH + TIMESTAMP_SIZE + STRUCT_OVERHEAD  # 112

    # Max content that fits in a single encrypted packet (opportunistic)
    ENCRYPTED_PACKET_MAX_CONTENT = Packet.ENCRYPTED_MDU + TIMESTAMP_SIZE - LXMF_OVERHEAD + DESTINATION_LENGTH

    def __init__(self, destination=None, source=None, content=b"", title=b"",
                 fields=None, desired_method=None,
                 destination_hash=None, source_hash=None):

        self._destination = destination
        self._source = source
        self.destination_hash = destination_hash or (destination.hash if destination else None)
        self.source_hash = source_hash or (source.hash if source else None)

        if isinstance(title, str):
            title = title.encode("utf-8")
        if isinstance(content, str):
            content = content.encode("utf-8")

        self.title = title
        self.content = content
        self.fields = fields if fields is not None else {}

        self.timestamp = None
        self.signature = None
        self.hash = None
        self.message_id = None
        self.packed = None
        # Stamp (5th payload element). We only ever generate TICKET stamps:
        # truncated_hash(ticket + message_id), free to compute, accepted by
        # reference LXMF peers that hand us a ticket. PoW stamps are out of
        # reach on an MCU, so outbound_ticket is the only way to satisfy a
        # peer that requires stamps.
        self.stamp = None
        self.outbound_ticket = None
        self.state = LXMessage.GENERATING
        self.method = LXMessage.UNKNOWN
        self.desired_method = desired_method

        self.incoming = False
        self.signature_validated = False
        self.unverified_reason = None
        self.transport_encrypted = False
        self.transport_encryption = None

        self.rssi = None
        self.snr = None
        self.q = None

        self._delivery_callback = None
        self._failed_callback = None

    @property
    def destination(self):
        return self._destination

    @destination.setter
    def destination(self, d):
        if self._destination is None:
            self._destination = d
        else:
            raise ValueError("Cannot reassign destination")

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, s):
        if self._source is None:
            self._source = s
        else:
            raise ValueError("Cannot reassign source")

    def content_as_string(self):
        try:
            return self.content.decode("utf-8")
        except Exception:
            return None

    def title_as_string(self):
        try:
            return self.title.decode("utf-8")
        except Exception:
            return None

    def register_delivery_callback(self, callback):
        self._delivery_callback = callback

    def register_failed_callback(self, callback):
        self._failed_callback = callback

    def pack(self):
        """Pack message...[2831 chars truncated]...           self.transport_encryption = "Curve25519"



































































            log("Sent opportunistic LXMF message to " + self.destination_hash.hex()[:8], LOG_NOTICE)

            if self._delivery_callback:
                try:
                    self._delivery_callback(self)
                except Exception as e:
                    log("Delivery callback error: " + str(e), LOG_ERROR)

        elif self.method == LXMessage.DIRECT:
            # DIRECT delivery handled by LXMRouter._send_direct()
            pass
        else:
            log("Unsupported delivery method: " + str(self.method), LOG_ERROR)
            self.state = LXMessage.FAILED

    @staticmethod
    def unpack_from_bytes(lxmf_bytes):
        """Unpack LXMF message from wire format bytes"""
        DL = LXMessage.DESTINATION_LENGTH
        SL = LXMessage.SIGNATURE_LENGTH

        destination_hash = lxmf_bytes[:DL]
        source_hash = lxmf_bytes[DL:2 * DL]
        signature = lxmf_bytes[2 * DL:2 * DL + SL]
        packed_payload = lxmf_bytes[2 * DL + SL:]

        unpacked_payload = umsgpack.unpackb(packed_payload)

        # Extract stamp if present (5th element)
        stamp = None
        if len(unpacked_payload) > 4:
            stamp = unpacked_payload[4]
            unpacked_payload = unpacked_payload[:4]
            packed_payload = umsgpack.packb(unpacked_payload)

        # Compute message hash
        hashed_part = destination_hash + source_hash + packed_payload
        message_hash = sha256(hashed_part)
        signed_part = hashed_part + message_hash

        timestamp = unpacked_payload[0]
        title_bytes = unpacked_payload[1]
        content_bytes = unpacked_payload[2]
        fields = unpacked_payload[3]

        # Try to find source identity for signature validation
        source_identity = Identity.recall(source_hash)

        # Build source destination if identity known
        source_dest = None
        if source_identity:
            source_dest = Destination(source_identity, Destination.OUT,
                                       Destination.SINGLE, APP_NAME, "delivery")

        # Build destination object if identity known
        dest_identity = Identity.recall(destination_hash)
        dest_obj = None
        if dest_identity:
            dest_obj = Destination(dest_identity, Destination.OUT,
                                    Destination.SINGLE, APP_NAME, "delivery")

        message = LXMessage(
            destination=dest_obj,
            source=source_dest,
            destination_hash=destination_hash,
            source_hash=source_hash,
        )

        message.hash = message_hash
        message.message_id = message_hash
        message.signature = signature
        message.stamp = stamp
        message.incoming = True
        message.timestamp = timestamp
        message.title = title_bytes if isinstance(title_bytes, bytes) else title_bytes.encode("utf-8") if title_bytes else b""
        message.content = content_bytes if isinstance(content_bytes, bytes) else content_bytes.encode("utf-8") if content_bytes else b""
        message.fields = fields if isinstance(fields, dict) else {}
        message.packed = lxmf_bytes

        # Validate signature
        if source_identity:
            if not LXMRouter.verify_signatures:
                # Skip expensive Ed25519 verify on constrained devices.
                # Message is already authenticated by encryption layer
                # (X25519 ECDH + HMAC-SHA256).
                message.signature_validated = True
            else:
                try:
                    if source_identity.validate(signature, signed_part):
























































        self._delivery_callback = None
        self._announce_callback = None
        self._progress_callback = None

        # Tickets peers gave us (FIELD_TICKET in their messages) so we can
        # reply with a free ticket stamp: dest_hash -> [expires_unix, ticket].
        # Persisted: a reference peer re-issues a ticket at most once a day
        # (TICKET_INTERVAL), so losing it on reboot would fail replies for
        # up to a day.
        self.outbound_tickets = {}
        self._load_tickets()

        self.peers = {}  # hash -> {name, timestamp, identity}
        self.delivered_ids = {}  # message_hash -> timestamp (dedup)

        self.MESSAGE_EXPIRY = 30 * 24 * 60 * 60  # 30 days

    def register_delivery_identity(self, identity, display_name=None, stamp_cost=None):
        """Register identity for receiving LXMF messages.
        Creates the lxmf.delivery destination and sets up callbacks."""
        self.delivery_identity = identity
        self.display_name = display_name

        self.delivery_destination = Destination(
            identity, Destination.IN, Destination.SINGLE,
            APP_NAME, "delivery"
        )

        # Set the packet callback for incoming opportunistic messages
        self.delivery_destination.set_packet_callback(self._delivery_packet)

        # Set link established callback for incoming link-based delivery (Resources)
        self.delivery_destination.set_link_established_callback(self._on_link_established)

        # Set announce handler so Transport forwards peer announces to us
        self.delivery_destination._announce_handler = self._announce_handler

        # Set app_data for announces. set_default_app_data so plain
        # Destination.announce() calls (path responses, post-clock-sync
        # re-announces) also carry the LXMF app_data — announce() falls back
        # to default_app_data.
        if display_name is not None:
            self.delivery_destination.set_default_app_data(
                self._build_app_data(display_name, stamp_cost))

        log("LXMF delivery registered: " + self.delivery_destination.hexhash, LOG_NOTICE)
        return self.delivery_destination

    def register_delivery_callback(self, callback):
        """Register callback for incoming messages: callback(lxmessage)"""
        self._delivery_callback = callback

    def register_announce_callback(self, callback):
        """Register callback for peer announces: callback(destination_hash, display_name)"""
        self._announce_callback = callback

    def register_progress_callback(self, callback):
        """Register callback for incoming resource transfer progress:
        callback(resource) — reference RNS Resource progress_callback
        signature; read resource.get_progress() or received_count/
        total_parts on it."""
        self._progress_callback = callback

    def announce(self):
        """Announce our LXMF delivery destination"""
        if self.delivery_destination:
            app_data = self._get_announce_app_data()
            self.delivery_destination.announce(app_data=app_data)
            log("LXMF announced as: " + (self.display_name or "unnamed"), LOG_NOTICE)

    def _get_announce_app_data(self):
        """Build announce app_data for our delivery destination.
        Leaf nodes never require a stamp, so stamp_cost is None."""
        return self._build_app_data(self.display_name, None)

    @staticmethod
    def _build_app_data(display_name, stamp_cost=None):
        """Build LXMF announce app_data: msgpack([display_name_bytes|None,
        stamp_cost, supported_functionality]) — the upstream LXMF shape.

        We advertise SF_COMPRESSION in the functionality list: our Resource
        layer decompresses inbound bz2 transfers on every board (native module
        or the pure-Python fallback in bz2dec), so peers may compress large
        Resources sent to us, saving airtime. Older peers that read only
        elements [0]/[1] are unaffected."""
        dn = None
        if display_name:
            dn = display_name.encode("utf-8") if isinstance(display_name, str) else display_name
        return umsgpack.packb([dn, stamp_cost, [SF_COMPRESSION]])

    def send_message(self, destination_hash, content, title="",
                     fields=None, desired_method=None):
        """Send an LXMF message to a destination hash.

        Resilient delivery chain:
          1. reuse a link we previously opened to the peer (DIRECT), else
          2. send opportunistically if a path is known (auto-upgrades to
             DIRECT via a fresh OutgoingLink when the payload is too big), else
          3. request a path and defer the send until the route is learned.

        Returns the LXMessage when sent/started, True when queued pending a path,
        or None on hard failure (reachable but identity still unknown).
        """
        from .transport import Transport

        have_link = self._find_active_link_for(destination_hash) is not None

        # No route yet: solicit a path and defer the send. The retry re-enters
        # this method once the path (and the peer's identity, carried in the
        # path-response announce) is known.
        if not have_link and not Transport.has_path(destination_hash):
            log("No path to " + destination_hash.hex()[:8] + ", requesting path", LOG_VERBOSE)
            Transport.ensure_path(
                destination_hash,
                on_found=lambda: self.send_message(
                    destination_hash, content, title, fields, desired_method),
                on_timeout=lambda: log(
                    "LXMF send to " + destination_hash.hex()[:8]
                    + " failed: no path", LOG_ERROR),
            )
            return True   # queued

        # Reachable — we need the peer's keys to encrypt.
        dest_identity = Identity.recall(destination_hash)
        if dest_identity is None:
            log("Cannot send LXMF: unknown identity for " + destination_hash.hex()[:8], LOG_ERROR)
            return None

        dest = Destination(dest_identity, Destination.OUT,
                           Destination.SINGLE, APP_NAME, "delivery")

        source = Destination(self.delivery_identity, Destination.OUT,
                             Destination.SINGLE, APP_NAME, "delivery")

        # Prefer an already-open link when the caller hasn't forced a method:
        # avoids a redundant path request when we can answer over the link.
        if have_link and desired_method is None:
            desired_method = LXMessage.DIRECT

        msg = LXMessage(
            destination=dest,
            source=source,
            content=content,
            title=title,
            fields=fields,
            desired_method=desired_method or LXMessage.OPPORTUNISTIC,
        )

        # A peer that requires stamps gave us a ticket; stamp with it so the
        # reply isn't dropped as "invalid stamp".
        msg.outbound_ticket = self.get_outbound_ticket(destination_hash)

        msg.pack()

        if msg.method == LXMessage.OPPORTUNISTIC:
            msg.send()
        elif msg.method == LXMessage.DIRECT:
            self._send_direct(msg, dest)

        return msg

    def _find_active_link_for(self, destination_hash):
        """Return an ACTIVE OutgoingLink we previously opened to this LXMF
        peer, or None. Only initiator links qualify: reference LXMF wires
        delivery callbacks on links it ACCEPTS at its delivery destination,
        not on links it OPENED — a message sent back over the peer's own
        link transfers and proves at the Resource layer but is silently
        discarded by the peer's app (observed with MeshChat image replies)."""
        from .transport import Transport
        from .link import OutgoingLink
        for link in Transport.active_links:
            if link.status != 0x01:  # ACTIVE
                continue
            if isinstance(link, OutgoingLink) and link.destination.hash == destination_hash:
                return link
        return None

    def _send_direct(self, message, destination):
        """Send LXMF message via DIRECT link delivery (link + Resource).

        Reuses an OutgoingLink we already hold to the peer, else opens a
        fresh one (path availability is guaranteed by the has_path/
        ensure_path gate in send_message). Never sends over a peer-initiated
        link — see _find_active_link_for.
