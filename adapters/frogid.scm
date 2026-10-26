;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/frogid.scm — Australian Museum FrogID calls → records.
;;;
;;; gated-partnership: FrogID is a GoE-supported citizen-science app whose
;;; verified frog-call records need a relationship to reach. Seam stays
;;; unbound until then — 'no-source is the honest answer.

(define-module (adapters frogid)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*frogid-url* *frogid-credentials* *frogid-fetch* frogid-calls import-call))

(define *frogid-url* "https://www.frogid.net.au/api")
(define *frogid-credentials* (make-parameter #f))
(define *frogid-fetch* (make-parameter #f))

(define (frogid-calls)
  (if (not (and (*frogid-credentials*) (*frogid-fetch*)))
      'no-source
      ((*frogid-fetch*) *frogid-url* (*frogid-credentials*))))

(define (import-call c subject)
  (make-federated-record
   #:source 'frogid
   #:source-id (assq-ref c 'id)
   #:subject subject
   #:channel 'acoustic
   #:at (or (assq-ref c 'recorded_at) (assq-ref c 'timestamp))
   #:payload `((species . ,(assq-ref c 'species))
               (verified . ,(assq-ref c 'verified)))))
