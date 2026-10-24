;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/weather.scm — Open-Meteo context on readings: another thin seam.
;;;
;;; WHAT THE FILE HOLDS. Context enrichment only: a reading plus the
;;; weather at its place and instant is a better reading — rain-on-foliage
;;; is a signal, not noise, once the record can say it rained. The fetch
;;; itself is not here: *weather-fetch* is the seam, bound in deployment to
;;; an Open-Meteo client; unbound, enrichment answers 'no-context rather
;;; than invent weather.
;;;
;;; Open-Meteo needs no key and licenses data CC-BY — the endpoint is
;;; recorded on *open-meteo-url* for whoever binds the seam.

(define-module (adapters weather)
  #:use-module (srfi srfi-1)
  #:use-module (living specs)
  #:export (*weather-fetch* *open-meteo-url*
            enrich-reading weather-context))


(define *open-meteo-url*
  "https://api.open-meteo.com/v1/forecast?hourly=temperature_2m,precipitation,windspeed_10m,relative_humidity_2m")

;;; (proc lat lon at) → weather alist | #f. Bound at deployment; the seam
;;; is one call.
(define *weather-fetch* (make-parameter #f))

(define* (weather-context lat lon #:key (at #f))
  "The context a reading may cite, or #f when the seam is unbound."
  (let ((fetch (*weather-fetch*)))
    (and fetch (fetch lat lon at))))


;;; merge the context under the reading's payload as ('weather . alist) —
;;; the reading stays a <reading>, the evidence shape is untouched.
(define* (enrich-reading r weather #:key (lat #f) (lon #f))
  (let ((ctx (or weather (and lat lon (weather-context lat lon)))))
    (if (not ctx)
        (cons 'no-context r)
        (cons 'reading
              (make-reading
               #:subject (reading-subject r)
               #:channel (reading-channel r)
               #:timestamp (reading-timestamp r)
               #:payload (cons (cons 'weather ctx) (reading-payload r))
               #:mic-cal (reading-mic-cal r)
               #:gain (reading-gain r))))))
