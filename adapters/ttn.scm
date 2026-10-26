;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/ttn.scm — The Things Network as the commons' backhaul lane.
;;;
;;; TTN carries both directions on community gateways: uplinks (our LoRa
;;; nodes' bundles arrive via webhook — reads reaching the edge with no
;;; gateway of our own) and downlinks (admitted write intents reaching
;;; owner-joined LoRa actuators — valves, relays, speakers). The MQTT/API
;;; client binds at deployment (paho-mqtt class); *ttn-uplink-handler*
;;; and *ttn-downlink* unbound → 'no-source. Helium rides the same shape.

(define-module (adapters ttn)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*ttn-app* *ttn-key* *ttn-uplink-handler* *ttn-downlink*
            ttn-decode-uplink write-intent->downlink))

;;; Application + api key bind per deployment — community credentials.
(define *ttn-app* (make-parameter #f))
(define *ttn-key*  (make-parameter #f))

;;; (proc uplink-alist) → federated record | #f — bound to the webhook.
(define *ttn-uplink-handler* (make-parameter #f))

;;; (proc app key device-id port payload-bytes) → receipt | #f.
(define *ttn-downlink* (make-parameter #f))

(define (ttn-decode-uplink u subject)
  "One TTN webhook uplink → <federated-record> (channel 'relay-origin).
   decoded_payload is whatever firmware packed — our own bundle bytes."
  (make-federated-record
   #:source 'ttn
   #:source-id (or (assq-ref u 'device_id) (assq-ref u 'uplink_token))
   #:subject subject
   #:channel 'relay
   #:at (assq-ref u 'received_at)
   #:payload `((frm . ,(assq-ref u 'frm_payload))
               (decoded . ,(assq-ref u 'decoded_payload))
               (gateway . ,(assq-ref u 'gateway_ids)))))

(define (write-intent->downlink intent device-id)
  "Admitted emit/cast intent → downlink request. The payload bytes are
   the intent's own write-params, packed by firmware."
  (let ((send (*ttn-downlink*))
        (params (cdr intent)))
    (if (not (and send (*ttn-app*) (*ttn-key*)))
        'no-source
        (send (*ttn-app*) (*ttn-key*) device-id
              (or (assq-ref params 'port) 1)
              (assq-ref params 'payload)))))
