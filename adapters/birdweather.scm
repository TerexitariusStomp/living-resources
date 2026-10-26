;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/birdweather.scm — BirdWeather PUC stations → federated records.
;;;
;;; WHAT THE FILE HOLDS. BirdWeather is the GoE-supported acoustic network:
;;; tens of thousands of PUC stations posting BirdNET detections live. The
;;; public GraphQL API needs no key; *birdweather-fetch* is the seam — bound
;;; in deployment to a (web client) GraphQL caller, unbound it answers
;;; 'no-source rather than invent a detection. import-detection maps one
;;; upstream record into a federated record the lane admits on provenance.
;;; Write capability (playback) is unknown — advisor question; never assume.

(define-module (adapters birdweather)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*birdweather-gql* *birdweather-fetch*
            birdweather-detections import-detection))

(define *birdweather-gql* "https://app.birdweather.com/graphql")

;;; (proc gql query-vars) → alist detections | #f. Bound at deployment.
(define *birdweather-fetch* (make-parameter #f))

(define %stations-q
  "{ stations { totalCount } }")
(define %detections-q
  "{ detections(first: 25) { edges { node { id timestamp score species { commonName } station { id coords { lat lon } } } } } }")

(define* (birdweather-detections #:key (since #f))
  "Latest detections across the network, or 'no-source when unbound."
  (let ((fetch (*birdweather-fetch*)))
    (if (not fetch)
        'no-source
        (fetch *birdweather-gql* %detections-q `((since . ,since))))))

(define (import-detection d subject)
  "One BirdWeather detection → <federated-record> (channel 'acoustic)."
  (make-federated-record
   #:source 'birdweather
   #:source-id (assq-ref d 'id)
   #:subject subject
   #:channel 'acoustic
   #:at (assq-ref d 'timestamp)
   #:payload `((species . ,(assq-ref d 'species))
               (score . ,(assq-ref d 'score))
               (station . ,(assq-ref d 'station)))))
