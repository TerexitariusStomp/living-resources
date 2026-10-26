;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/goe.scm — Guardians of Earth → federated records.
;;;
;;; gated-partnership: api.guardiansofearth.io exists but is undocumented —
;;; this seam stays unbound until advisor-provided API docs or credentials
;;; land. Realms, BioScore and BCU are GoE's own units and must be labeled
;;; as such in the payload — never presented as the commons' measurements.
;;; Import direction only: reads from GoE, no writes.

(define-module (adapters goe)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*goe-url* *goe-credentials* *goe-fetch* goe-realms import-realm))

(define *goe-url* "https://api.guardiansofearth.io")
(define *goe-credentials* (make-parameter #f)) ; advisor-provided, never committed
(define *goe-fetch* (make-parameter #f))

(define (goe-realms)
  "Realms the partnership exposes. 'no-source until docs+credentials bind."
  (if (not (and (*goe-credentials*) (*goe-fetch*)))
      'no-source
      ((*goe-fetch*) *goe-url* (*goe-credentials*))))

(define (import-realm r subject)
  "One Realm → <federated-record>. BioScore/BCU stay GoE-labeled."
  (make-federated-record
   #:source 'goe
   #:source-id (or (assq-ref r 'realm_id) (assq-ref r 'id))
   #:subject subject
   #:channel 'composite
   #:at (or (assq-ref r 'updated_at) (assq-ref r 'at))
   #:payload `((realm . ,(assq-ref r 'name))
               (bioscore . ,(assq-ref r 'bioscore))   ; GoE's index, not ours
               (bcu . ,(assq-ref r 'bcu))             ; GoE's unit, not ours
               (guardians . ,(assq-ref r 'guardian_count)))))
