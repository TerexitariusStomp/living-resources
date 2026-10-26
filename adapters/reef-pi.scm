;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/reef-pi.scm — reef-pi aquarium controllers, owner opt-in.
;;;
;;; reef-pi is open-source aquarium control — pumps, lights, feeders,
;;; dosing — living marine systems whose owner can opt the device into
;;; the write federation. REST is on-device (owner LAN / authorised
;;; tunnel); *reef-send* binds at deployment. Write-kinds: feed, light,
;;; dose, pump.

(define-module (adapters reef-pi)
  #:use-module (living specs)
  #:use-module (living offers)
  #:use-module (adapters federated)
  #:export (*reef-send* write-intent->reef))

;;; (proc device-url credential endpoint body) → receipt | #f.
(define *reef-send* (make-parameter #f))

(define (write-intent->reef intent device-url credential)
  "Admitted emit intent → reef-pi REST call, or 'no-source / refusal."
  (let ((send (*reef-send*))
        (params (cdr intent))
        (kind (assq-ref (cdr intent) 'write-kind)))
    (cond
     ((not send) 'no-source)
     ((memq kind '(feed light dose pump))
      (send device-url credential
            (string-append "/api/" (symbol->string kind))
            params))
     (else (refused 'emit 'write-refused
                    "reef-pi speaks 'feed, 'light, 'dose and 'pump")))))
