;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/reticulum.scm — the edge-side Reticulum ear.
;;;
;;; WHAT THE FILE HOLDS. The receiving seam between field nodes and the
;;; commons: detection packets arrive over LXMF (LoRa/RNode) or UDP (WiFi
;;; path), are normalized into the detection alist adapters/mic.scm already
;;; understands, and handed to the caller's sink. The WiFi path is a real
;;; socket — udp-socket/udp-demux/run-udp-listener — speaking the node's
;;; frame tags directly; the LXMF path remains a boundable seam on
;;; *reticulum-transport* for when MicroReticulum is on the host.
;;;
;;; THE PACKET. A detection packet is tens of bytes on the LoRa path —
;;; species, confidence, timestamp, node-id, plus the SAIDs the edge adds:
;;; {species, confidence, timestamp, node, mic_cal, gain, audio_said,
;;;  subject}. packet->detection normalizes without inventing: absent
;;; fields stay absent and the gate downstream decides whether that
;;; matters.

(define-module (adapters reticulum)
  #:use-module (srfi srfi-1)
  #:use-module (rnrs bytevectors)
  #:use-module (adapters mic)
  #:export (*reticulum-transport* packet->detection
            detection-packet? make-edge-listener
            udp-socket udp-recv-frame udp-demux
            run-udp-listener))


;;; ── the transport seam ──────────────────────────────────────────────────
;;; Two bindings live here. *reticulum-transport* stays the parameter for
;;; a real MicroReticulum / rns-bridge LXMF destination — bound when that
;;; stack is on the host. The WiFi path is real already: udp-socket /
;;; run-udp-listener below demux the node's DET1/AUD1/TSK1 frames over a
;;; bound datagram socket, the same bytes the LoRa path carries inside
;;; RNode frames. License note: Reticulum's terms bar logged traffic from
;;; training corpora — detections pass through, they are not retained for
;;; eval use.
(define *reticulum-transport* (make-parameter #f))


;;; ── the WiFi path — a real socket ───────────────────────────────────────
;;; Frame contract shared with firmware/node/main.py: a 4-byte tag then the
;;; payload — DET1 = detection line, AUD1 = audio chunk (name-len u8, name,
;;; pcm), TSK1/LANE = downlink writes. udp-demux splits the tag; the
;;; listener feeds DET1 bodies through mic.scm's line parser into
;;; on-detection, and hands AUD1 bodies to on-audio for the content store.

(define (udp-socket port)
  "Bound datagram socket on PORT — the edge's ear."
  (let ((s (socket AF_INET SOCK_DGRAM 0)))
    (setsockopt s SOL_SOCKET SO_REUSEADDR 1)
    (bind s AF_INET INADDR_ANY port)
    s))

(define* (udp-recv-frame sock #:key (buf-size 65536))
  "One datagram → (values tag body-bv) | (values #f #f) on a short frame."
  (let ((buf (make-bytevector buf-size)))
    (let-values (((n _addr) (recvfrom! sock buf)))
      (if (< n 4)
          (values #f #f)
          (values (utf8->string (bytevector-copy buf 0 4))
                  (bytevector-copy buf 4 n))))))

(define* (udp-demux listener tag body #:key (on-audio (lambda (n b) b)))
  "Route one frame by tag. DET1 bodies parse through mic.scm into the
   listener; AUD1 bodies go to on-audio as (name . pcm). Anything else is
   a refused value, never a drop."
  (cond
   ((equal? tag "DET1")
    (let ((p (parse-detection-line (utf8->string body))))
      (if (eq? 'det (car p))
          (listener (cdr p))
          (cons 'refused '((reason . malformed-detection))))))
   ((equal? tag "AUD1")
    (let ((nlen (bytevector-u8-ref body 0)))
      (on-audio (utf8->string (bytevector-copy body 1 (+ 1 nlen)))
                (bytevector-copy body (+ 1 nlen)
                                 (bytevector-length body)))))
   (else
    (cons 'refused `((reason . unknown-frame-tag) (tag . ,tag))))))

(define* (run-udp-listener #:key (port 4242)
                          (listener (make-edge-listener))
                          (on-audio (lambda (n b) b))
                          (max-frames #f))
  "The edge's receive loop: recv → demux → sink. MAX-FRAMES bounds it for
   tests; #f runs until the process dies — the ear doesn't sleep."
  (let ((sock (udp-socket port)))
    (let loop ((seen 0))
      (if (and max-frames (>= seen max-frames))
          (begin (close-port sock) seen)
          (begin
            (let-values (((tag body) (udp-recv-frame sock)))
              (when tag (udp-demux listener tag body #:on-audio on-audio)))
            (loop (+ 1 seen)))))))


;;; ── packets ─────────────────────────────────────────────────────────────
;;; Required: species, confidence, timestamp and a node — a packet that
;;; cannot say who heard what, when, is not a detection.

(define (detection-packet? pkt)
  (and (list? pkt)
       (assq 'species pkt) (assq 'confidence pkt)
       (assq 'timestamp pkt)
       (or (assq 'node pkt) (assq 'channel pkt) (assq 'node_id pkt))
       #t))

(define (packet->detection pkt)
  "Normalize a wire packet into the detection alist mic.scm maps.
   Absent optional fields are simply absent — no invented evidence."
  (filter-map
   (lambda (k) (let ((p (assq k pkt))) (and p p)))
   '(subject species confidence timestamp ts node channel node_id
     mic_cal mic-cal calibration gain audio_said band start end)))


;;; ── the listener ────────────────────────────────────────────────────────
;;; (make-edge-listener #:on-detection proc) → a listener procedure. Feed
;;; it packets: each is normalized; a valid one is handed to ON-DETECTION;
;;; an invalid one is refused with a reason — the same posture as the lane
;;; gate: answered, not dropped. When *reticulum-transport* is bound the
;;; real daemon's dispatch loop calls this same procedure per decoded
;;; packet; the stub is exactly that loop minus the socket.

(define* (make-edge-listener #:key (on-detection (lambda (d) d)))
  (lambda (packet)
    (cond
     ((not (detection-packet? packet))
      (cons 'refused
            '((reason . malformed-packet)
              (detail . "species, confidence, timestamp and node are required"))))
     (else
      (cons 'detection (on-detection (packet->detection packet)))))))
