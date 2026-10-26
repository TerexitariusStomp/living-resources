;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/orcasound.scm — live hydrophones → federated records.
;;;
;;; Orcasound runs public hydrophone nodes with live audio streams and
;;; community whale detections — channel 'acoustic, ocean-flavoured.
;;; *orca-fetch* is the seam (detections/feeds endpoint); unbound →
;;; 'no-source. Audio itself stays at the source — we import detections,
;;; not streams, by default (streams would be a band-lane question anyway).

(define-module (adapters orcasound)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*orca-url* *orca-fetch* orca-detections import-detection))

(define *orca-url* "https://live.orcasound.net/api")

;;; (proc path) → alist | #f. Bound at deployment.
(define *orca-fetch* (make-parameter #f))

(define (orca-detections)
  (let ((fetch (*orca-fetch*)))
    (if (not fetch)
        'no-source
        (fetch (string-append *orca-url* "/detections")))))

(define (import-detection d subject)
  (make-federated-record
   #:source 'orcasound
   #:source-id (or (assq-ref d 'id) (assq-ref d 'feed))
   #:subject subject
   #:channel 'acoustic
   #:at (or (assq-ref d 'timestamp) (assq-ref d 'detected_at))
   #:payload `((feed . ,(assq-ref d 'feed))
               (category . ,(assq-ref d 'category))
               (listeners . ,(assq-ref d 'listener_count)))))
