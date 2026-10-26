;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/husqvarna.scm — Automower/Gardena writes, owner opt-in only.
;;;
;;; The largest write-capable fleet (~2.5M robotic mowers + Gardena smart
;;; irrigation) — and entirely owner-keyed: Husqvarna OAuth only ever sees
;;; devices the owner registered. opt-in-operator by construction. The
;;; edge adopts the MIT `husqvarna-automower` client; *husq-send* binds
;;; at deployment. Write-kinds: mow-schedule, irrigate.

(define-module (adapters husqvarna)
  #:use-module (living specs)
  #:use-module (living offers)
  #:use-module (adapters federated)
  #:export (*husq-url* *husq-send* write-intent->husq))

(define *husq-url* "https://api.amc.husqvarna.dev/v1")

;;; (proc oauth-token action device-id params) → receipt | #f.
(define *husq-send* (make-parameter #f))

(define (write-intent->husq intent oauth-token device-id)
  "Admitted emit intent → a Husqvarna action, or 'no-source / refusal."
  (let ((send (*husq-send*))
        (kind (assq-ref (cdr intent) 'write-kind)))
    (cond
     ((not send) 'no-source)
     ((memq kind '(mow-schedule irrigate))
      (send oauth-token kind device-id (cdr intent)))
     (else (refused 'emit 'write-refused
                    "husqvarna speaks 'mow-schedule and 'irrigate")))))
