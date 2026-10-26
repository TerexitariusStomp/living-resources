;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/motus.scm — wildlife telemetry towers → federated records.
;;;
;;; ~1,700 Motus receivers hear tagged birds, bats and insects fly past —
;;; radio telemetry as a federation source. Data needs registration, so
;;; the seam is key-required: *motus-fetch* binds at deployment, unbound
;;; → 'no-source.

(define-module (adapters motus)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*motus-url* *motus-key* *motus-fetch* motus-detections import-detection))

(define *motus-url* "https://motus.org/api")
(define *motus-key* (make-parameter #f))
(define *motus-fetch* (make-parameter #f))

(define (motus-detections)
  (if (not (and (*motus-key*) (*motus-fetch*)))
      'no-source
      ((*motus-fetch*) *motus-url* (*motus-key*))))

(define (import-detection d subject)
  (make-federated-record
   #:source 'motus
   #:source-id (or (assq-ref d 'hitID) (assq-ref d 'id))
   #:subject subject
   #:channel 'telemetry
   #:at (assq-ref d 'ts)
   #:payload `((tag . ,(assq-ref d 'tagDeployID))
               (receiver . ,(assq-ref d 'recvDeployID))
               (species . ,(assq-ref d 'species)))))
