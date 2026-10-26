;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/phenocam.scm — PhenoCam vegetation cameras → federated records.
;;;
;;; ~900 networked cameras watch leaf-out and greenness worldwide — the
;;; photo-phenology sense-kind already in the vocabulary. The API is open;
;;; *phenocam-fetch* is the seam, unbound → 'no-source.

(define-module (adapters phenocam)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*phenocam-url* *phenocam-fetch* phenocam-sites import-frame))

(define *phenocam-url* "https://phenocam.nau.edu/api")

;;; (proc path) → alist | #f. Bound at deployment.
(define *phenocam-fetch* (make-parameter #f))

(define (phenocam-sites)
  (let ((fetch (*phenocam-fetch*)))
    (if (not fetch)
        'no-source
        (fetch (string-append *phenocam-url* "/sites/")))))

(define (import-frame f subject)
  "One camera greenness frame → <federated-record> (channel 'camera)."
  (make-federated-record
   #:source 'phenocam
   #:source-id (or (assq-ref f 'site) (assq-ref f 'id))
   #:subject subject
   #:channel 'camera
   #:at (or (assq-ref f 'date) (assq-ref f 'timestamp))
   #:payload `((gcc . ,(assq-ref f 'gcc))         ; green chromatic coordinate
               (image . ,(assq-ref f 'image-url)))))
