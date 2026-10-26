;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/purpleair.scm — ~30k citizen air sensors → federated records.
;;;
;;; Key-required source: the API is public but asks for a free key. The key
;;; binds at deployment as a parameter (*purpleair-key*) — never in the
;;; repo. Unbound → 'no-source, the honest answer.

(define-module (adapters purpleair)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*purpleair-url* *purpleair-key* *purpleair-fetch*
            purpleair-sensors import-reading))

(define *purpleair-url* "https://api.purpleair.com/v1")
(define *purpleair-key* (make-parameter #f))
(define *purpleair-fetch* (make-parameter #f))

(define (purpleair-sensors)
  (if (not (and (*purpleair-key*) (*purpleair-fetch*)))
      'no-source
      ((*purpleair-fetch*) *purpleair-url* (*purpleair-key*))))

(define (import-reading r subject)
  (make-federated-record
   #:source 'purpleair
   #:source-id (assq-ref r 'sensor_index)
   #:subject subject
   #:channel 'env
   #:at (assq-ref r 'last_seen)
   #:payload `((pm25 . ,(assq-ref r 'pm2.5))
               (latitude . ,(assq-ref r 'latitude))
               (longitude . ,(assq-ref r 'longitude)))))
