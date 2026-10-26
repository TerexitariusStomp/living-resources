;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/sensor-community.scm — Sensor.Community DIY boxes → records.
;;;
;;; ~14k community air/noise/environment sensors; the JSON API needs no key
;;; and the data is CC-BY-SA — attribution must ride the payload. The fetch
;;; is a seam (*sc-fetch*), bound in deployment to (web client); unbound it
;;; answers 'no-source. Covers SDS011-class particulate, DHT-class env and
;;; DNMS noise units; noise readings are the interesting half for us.

(define-module (adapters sensor-community)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*sc-url* *sc-fetch* sc-sensors-in-area import-reading))

(define *sc-url* "https://data.sensor.community/airrohr/v1")

;;; (proc path) → alist list | #f. Bound at deployment.
(define *sc-fetch* (make-parameter #f))

(define* (sc-sensors-in-area lat lon radius-km #:key (type "DNMS"))
  "Sensors of a type within a radius — e.g. filter/area=52.5,13.4,10&type=DNMS."
  (let ((fetch (*sc-fetch*)))
    (if (not fetch)
        'no-source
        (fetch (string-append *sc-url* "/filter/area="
                              (number->string lat) "," (number->string lon) ","
                              (number->string radius-km) "&type=" type)))))

(define (import-reading s subject)
  "One Sensor.Community record → <federated-record> (channel 'env).
   The record keeps its license so the CC-BY-SA chain survives."
  (make-federated-record
   #:source 'sensorcommunity
   #:source-id (assq-ref s 'id)
   #:subject subject
   #:channel 'env
   #:at (assq-ref s 'timestamp)
   #:payload `((location . ,(assq-ref s 'location))
               (sensordatavalues . ,(assq-ref s 'sensordatavalues))
               (license . "CC-BY-SA"))))
