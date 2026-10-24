;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/reticulum.scm — the edge-side Reticulum ear: a stub with a shape.
;;;
;;; WHAT THE FILE HOLDS. The receiving seam between field nodes and the
;;; commons: detection packets arrive over LXMF (LoRa/RNode) or UDP (WiFi
;;; path), are normalized into the detection alist adapters/mic.scm already
;;; understands, and handed to the caller's sink. The listener here is a
;;; queue-fed stub — packets are injected by whatever owns the transport —
;;; because the real binding is a seam, not a file: see the TODO on
;;; *reticulum-transport*.
;;;
;;; THE PACKET. A detection packet is tens of bytes on the LoRa path —
;;; species, confidence, timestamp, node-id, plus the SAIDs the edge adds:
;;; {species, confidence, timestamp, node, mic_cal, gain, audio_said,
;;;  subject}. packet->detection normalizes without inventing: absent
;;; fields stay absent and the gate downstream decides whether that
;;; matters.

(define-module (adapters reticulum)
  #:use-module (srfi srfi-1)
  #:use-module (adapters mic)
  #:export (*reticulum-transport* packet->detection
            detection-packet? make-edge-listener))


;;; ── the transport seam ──────────────────────────────────────────────────
;;; TODO(real binding): replace this parameter with the MicroReticulum /
;;; rns-bridge socket — an LXMF destination callback on the LoRa path, a
;;; UDP socket on the WiFi path. The rest of this file already speaks the
;;; packet shape both carry; the binding only has to enqueue bytes parsed
;;; to alists. License note from the spec: Reticulum's terms bar logged
;;; traffic from training corpora — detections pass through, they are not
;;; retained for eval use.
(define *reticulum-transport* (make-parameter #f))


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
