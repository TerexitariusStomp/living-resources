;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/raspberry-shake.scm — citizen seismographs → federated records.
;;;
;;; Raspberry Shake is the ~6k-station AM network speaking standard FDSN
;;; webservices — the same protocol IRIS observatories use, so the adopted
;;; OSS is ObsPy on the Python edge. Ground vibration is an ecological
;;; channel: footfalls, surf, storms, traffic. *shake-fetch* is the seam —
;;; bound to an ObsPy fdsn client at deployment; unbound → 'no-source.

(define-module (adapters raspberry-shake)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*shake-url* *shake-fetch* shake-stations import-event))

(define *shake-url* "https://data.raspberryshake.org/fdsnws")

;;; (proc path) → alist | #f. Bound at deployment (ObsPy fdsnws).
(define *shake-fetch* (make-parameter #f))

(define (shake-stations)
  "Stations reporting in the last day — station/1/query?network=AM…"
  (let ((fetch (*shake-fetch*)))
    (if (not fetch)
        'no-source
        (fetch (string-append *shake-url* "/station/1/query"
                              "?network=AM&level=station&format=text")))))

(define (import-event e subject)
  "One seismic event/station reading → <federated-record> (channel 'seismic)."
  (make-federated-record
   #:source 'raspberryshake
   #:source-id (or (assq-ref e 'station) (assq-ref e 'id))
   #:subject subject
   #:channel 'seismic
   #:at (or (assq-ref e 'at) (assq-ref e 'timestamp))
   #:payload `((latitude . ,(assq-ref e 'lat))
               (longitude . ,(assq-ref e 'lon))
               (sample . ,(assq-ref e 'sample)))))
