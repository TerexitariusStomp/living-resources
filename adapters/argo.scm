;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/argo.scm — ocean profiling floats → federated records.
;;;
;;; ~4,000 Argo floats drift the ocean reading temperature/salinity (and
;;; biogeochemistry on BGC floats) — public via ERDDAP/GDAC, the same door
;;; CDIP wave buoys and IOOS gliders use. The Python edge adopts erddapy;
;;; *argo-fetch* is the Scheme seam, unbound → 'no-source.

(define-module (adapters argo)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*argo-erddap* *argo-fetch* argo-latest import-profile))

(define *argo-erddap* "https://erddap.ifremer.fr/erddap")

;;; (proc dataset constraints) → alist rows | #f. Bound to erddapy at edge.
(define *argo-fetch* (make-parameter #f))

(define (argo-latest)
  (let ((fetch (*argo-fetch*)))
    (if (not fetch)
        'no-source
        (fetch "ArgoFloats" '()))))

(define (import-profile p subject)
  "One float profile → <federated-record> (channel 'ocean)."
  (make-federated-record
   #:source 'argo
   #:source-id (or (assq-ref p 'platform) (assq-ref p 'id))
   #:subject subject
   #:channel 'ocean
   #:at (assq-ref p 'time)
   #:payload `((latitude . ,(assq-ref p 'latitude))
               (longitude . ,(assq-ref p 'longitude))
               (temperature . ,(assq-ref p 'temp))
               (salinity . ,(assq-ref p 'psal)))))
