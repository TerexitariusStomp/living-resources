;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/opensprinkler.scm — irrigation writes through OpenSprinkler.
;;;
;;; OpenSprinkler is open-hardware irrigation with an HTTP API plus an
;;; OpenThings Cloud relay for owner-authorised remote reach. Two shapes
;;; land here: open-invitation (the live demo unit) and opt-in-operator
;;; (an owner shares their device). Either way the intent arrives already
;;; gated — emit's two-key consent ran upstream; this seam only speaks the
;;; device protocol. *os-send* is the delegation seam; unbound → 'no-source.

(define-module (adapters opensprinkler)
  #:use-module (living specs)
  #:use-module (living offers)
  #:use-module (adapters federated)
  #:export (*os-url* *os-send* os-irrigate write-intent->os))

(define *os-url* "https://demo.opensprinkler.com")

;;; (proc device-url credential command) → receipt alist | #f.
;;; Bound at deployment to an (web client) caller; the credential is the
;;; owner-issued token — never stored here.
(define *os-send* (make-parameter #f))

(define* (os-irrigate device-url credential station duration-s)
  "Run one station for a duration. Admitted intents only — this is the
   last mile, not the gate."
  (let ((send (*os-send*)))
    (if (not send)
        'no-source
        (send device-url credential
              `((command . "cm") (sid . ,station) (en . 1) (t . ,duration-s))))))

(define (write-intent->os intent device-url)
  "Map an admitted emit intent's write-params onto device commands."
  (let* ((params (cdr intent))
         (kind (assq-ref params 'write-kind)))
    (if (eq? kind 'irrigate)
        `((device . ,device-url)
          (command . run-station)
          (duration . ,(assq-ref params 'duration-s)))
        (refused 'emit 'write-refused
                 "opensprinkler speaks 'irrigate, no other write kind"))))
