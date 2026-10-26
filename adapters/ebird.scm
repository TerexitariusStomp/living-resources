;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/ebird.scm — Cornell eBird sightings → federated records.
;;;
;;; Key-required: ebird-api on the Python edge; the free Cornell key binds
;;; via *ebird-key* at deployment. eBird is one of GoE's supported feeds —
;;; importing it covers another lane of the same upstream.

(define-module (adapters ebird)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*ebird-url* *ebird-key* *ebird-fetch* ebird-recent import-obs))

(define *ebird-url* "https://api.ebird.org/v2")
(define *ebird-key* (make-parameter #f))
(define *ebird-fetch* (make-parameter #f))

(define* (ebird-recent region #:key (days 2))
  (if (not (and (*ebird-key*) (*ebird-fetch*)))
      'no-source
      ((*ebird-fetch*)
       (string-append *ebird-url* "/data/obs/" region "/recent")
       `((key . ,(*ebird-key*)) (back . ,days)))))

(define (import-obs o subject)
  (make-federated-record
   #:source 'ebird
   #:source-id (or (assq-ref o 'subId) (assq-ref o 'obsDt))
   #:subject subject
   #:channel 'acoustic
   #:at (assq-ref o 'obsDt)
   #:payload `((species . ,(assq-ref o 'comName))
               (count . ,(assq-ref o 'howMany))
               (location . ,(assq-ref o 'locName)))))
