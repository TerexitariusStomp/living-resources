;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/farmbot.scm — garden-robot writes through FarmBot.
;;;
;;; Two statuses share this seam: farmbot-demo is open-invitation (the
;;; public demo account drives a real garden robot — the flagship "write
;;; to nature today"); farmbot proper is opt-in-operator (owner OAuth).
;;; The seam maps admitted emit intents (write-kinds water/seed/photo)
;;; onto sequences; farmbot-py is the adopted OSS on the edge.
;;; *fb-send* unbound → 'no-source.

(define-module (adapters farmbot)
  #:use-module (living specs)
  #:use-module (living offers)
  #:use-module (adapters federated)
  #:export (*fb-url* *fb-demo* *fb-send* fb-execute write-intent->fb))

(define *fb-url* "https://my.farm.bot/api")
(define *fb-demo* "https://demo.farm.bot/api")

;;; (proc base-url credential sequence) → receipt alist | #f.
(define *fb-send* (make-parameter #f))

(define* (fb-execute base-url credential sequence)
  (let ((send (*fb-send*)))
    (if (not send)
        'no-source
        (send base-url credential sequence))))

(define (write-intent->fb intent)
  "Admitted emit intent → a FarmBot sequence, or a refusal. Only the
   write kinds the platform can actually carry are named."
  (let* ((params (cdr intent))
         (kind (assq-ref params 'write-kind))
         (point (assq-ref params 'point)))
    (case kind
      ((water)  `((sequence . "water") (point . ,point)))
      ((seed)   `((sequence . "seed")  (point . ,point)))
      ((photo)  `((sequence . "take-photo") (point . ,point)))
      (else (refused 'emit 'write-refused
                     "farmbot speaks 'water, 'seed and 'photo")))))
