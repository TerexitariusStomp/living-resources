;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/usgs-water.scm — river gauges → federated records.
;;;
;;; ~11k USGS real-time stream gauges (~2k more under the UK Environment
;;; Agency's open hydrology API). Streamflow is a river's pulse — the commons
;;; reads it as channel 'water. The Python edge adopts USGS's own
;;; `dataretrieval` lib; *water-fetch* is the Scheme seam, unbound →
;;; 'no-source. The same file covers EA gauges via *ea-url*.

(define-module (adapters usgs-water)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*usgs-url* *ea-url* *water-fetch* latest-flow import-gauge))

(define *usgs-url* "https://waterservices.usgs.gov/nwis/iv/")
(define *ea-url*   "https://environment.data.gov.uk/hydrology")

;;; (proc url params) → alist | #f. Bound at deployment (dataretrieval).
(define *water-fetch* (make-parameter #f))

(define* (latest-flow site #:key (agency 'usgs))
  "Latest instantaneous value for a gauge site."
  (let ((fetch (*water-fetch*)))
    (if (not fetch)
        'no-source
        (fetch (if (eq? agency 'ea) *ea-url* *usgs-url*)
               `((site . ,site) (parameter . "00060"))))))

(define (import-gauge g subject)
  (make-federated-record
   #:source (or (assq-ref g 'source) 'usgs-water)
   #:source-id (assq-ref g 'site)
   #:subject subject
   #:channel 'water
   #:at (assq-ref g 'timestamp)
   #:payload `((flow-cfs . ,(assq-ref g 'value))
               (parameter . ,(assq-ref g 'parameter)))))
