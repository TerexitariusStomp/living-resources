;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/inat.scm — iNaturalist/GBIF observations → federated records.
;;;
;;; iNaturalist is the upstream of much of Guardians of Earth — obs flow to
;;; Realms within ~24h — so this seam effectively imports part of GoE's
;;; feed already. Live route: api.inaturalist.org/v1 (pyinaturalist on the
;;; edge); bulk route: the weekly research-grade GBIF DwC-A (pygbif —
;;; carries a citable DOI). The record keeps license + quality_grade in
;;; the payload so the attribution chain survives the import.
;;; *inat-fetch* is the seam; unbound → 'no-source.

(define-module (adapters inat)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*inat-url* *gbif-dataset* *inat-fetch* inat-observations import-observation))

(define *inat-url* "https://api.inaturalist.org/v1")
(define *gbif-dataset* "doi:10.15468/ab3s5x") ; iNat research-grade export

;;; (proc path params) → alist | #f. Bound at deployment (pyinaturalist).
(define *inat-fetch* (make-parameter #f))

(define* (inat-observations #:key (taxon #f) (place #f) (order-by 'created_at))
  (let ((fetch (*inat-fetch*)))
    (if (not fetch)
        'no-source
        (fetch (string-append *inat-url* "/observations")
               `((taxon . ,taxon) (place . ,place) (order_by . ,order-by))))))

(define (import-observation o subject)
  (make-federated-record
   #:source 'inaturalist
   #:source-id (assq-ref o 'id)
   #:subject subject
   #:channel 'photo
   #:at (or (assq-ref o 'time_observed_at) (assq-ref o 'observed_on))
   #:payload `((taxon . ,(assq-ref o 'taxon))
               (quality-grade . ,(assq-ref o 'quality_grade))
               (license . ,(assq-ref o 'license_code))
               (uri . ,(assq-ref o 'uri)))))
