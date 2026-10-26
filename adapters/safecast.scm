;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/safecast.scm — citizen radiation network → federated records.
;;;
;;; Safecast grew out of Fukushima: thousands of bGeigie mobile sensors and
;;; fixed realtime stations, all CC0 — one of the oldest open sensor
;;; commons on earth. *safecast-fetch* is the seam; unbound → 'no-source.

(define-module (adapters safecast)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*safecast-url* *safecast-fetch* safecast-measurements import-measurement))

(define *safecast-url* "https://api.safecast.org")

;;; (proc path) → alist | #f. Bound at deployment.
(define *safecast-fetch* (make-parameter #f))

(define* (safecast-measurements #:key (near #f))
  (let ((fetch (*safecast-fetch*)))
    (if (not fetch)
        'no-source
        (fetch (string-append *safecast-url* "/measurements.json")))))

(define (import-measurement m subject)
  (make-federated-record
   #:source 'safecast
   #:source-id (assq-ref m 'id)
   #:subject subject
   #:channel 'env
   #:at (assq-ref m 'captured_at)
   #:payload `((value . ,(assq-ref m 'value))
               (unit . ,(assq-ref m 'unit))
               (latitude . ,(assq-ref m 'latitude))
               (longitude . ,(assq-ref m 'longitude))
               (license . "CC0"))))
