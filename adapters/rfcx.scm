;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/rfcx.scm — Rainforest Connection Guardian devices → records.
;;;
;;; gated-partnership: RFCx's solar phones in tree canopies stream to
;;; Arbimon; the platform is gated, so this seam stays unbound until a
;;; partnership/credentials land. When bound, RFCx is the closest deployed
;;; analogue of the living cloud's own acoustic cells.

(define-module (adapters rfcx)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*rfcx-url* *rfcx-credentials* *rfcx-fetch* rfcx-streams import-detection))

(define *rfcx-url* "https://arbimon.org/api")
(define *rfcx-credentials* (make-parameter #f))
(define *rfcx-fetch* (make-parameter #f))

(define (rfcx-streams)
  (if (not (and (*rfcx-credentials*) (*rfcx-fetch*)))
      'no-source
      ((*rfcx-fetch*) *rfcx-url* (*rfcx-credentials*))))

(define (import-detection d subject)
  (make-federated-record
   #:source 'rfcx
   #:source-id (or (assq-ref d 'id) (assq-ref d 'stream_id))
   #:subject subject
   #:channel 'acoustic
   #:at (assq-ref d 'start)
   #:payload `((stream . ,(assq-ref d 'stream_id))
               (classification . ,(assq-ref d 'classification))
               (confidence . ,(assq-ref d 'confidence)))))
