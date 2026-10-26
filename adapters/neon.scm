;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/neon.scm — NSF NEON observatories → federated records.
;;;
;;; 81 instrumented ecological sites — towers, phenocams, aquatic arrays —
;;; all behind an open REST API. NEON is the flagship-grade federated
;;; source: instrumented, calibrated, documented. *neon-fetch* is the seam
;;; (bound to a plain REST caller at deployment); unbound → 'no-source.

(define-module (adapters neon)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*neon-url* *neon-fetch* neon-site import-product))

(define *neon-url* "https://data.neonscience.org/api/v0")

;;; (proc path) → alist | #f. Bound at deployment.
(define *neon-fetch* (make-parameter #f))

(define (neon-site code)
  (let ((fetch (*neon-fetch*)))
    (if (not fetch)
        'no-source
        (fetch (string-append *neon-url* "/sites/" code)))))

(define (import-product v subject)
  "One NEON data value → <federated-record> (channel 'env)."
  (make-federated-record
   #:source 'neon
   #:source-id (or (assq-ref v 'site) (assq-ref v 'id))
   #:subject subject
   #:channel 'env
   #:at (or (assq-ref v 'startDateTime) (assq-ref v 'timestamp))
   #:payload `((product . ,(assq-ref v 'product))
               (value . ,(assq-ref v 'value))
               (license . "CC0 (NEON open data)"))))
