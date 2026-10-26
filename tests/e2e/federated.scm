;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; tests/e2e/federated.scm — the federation lane and the write registry.
;;;
;;; federated admits on provenance (source network + upstream record id) —
;;; not our evidence gate, not consent. The actuator half: a cell-decl's
;;; write-kinds bound what an admitted write may ask of a device, and the
;;; webnode seam turns a browser session into a declared cell. The closed
;;; world still holds: consent-gated lanes still refuse without consent,
;;; refused lanes still refuse with it.
;;;
;;; Run: guile --no-auto-compile -L module -L . tests/e2e/federated.scm

(use-modules (living specs)
             (living offers)
             (adapters federated)
             (adapters webnode)
             (srfi srfi-1)
             (ice-9 format))

(define pass-count 0)
(define fail-count 0)

(define (check label . args)
  (let ((pass? (if (null? (cdr args))
                   (car args)
                   (equal? (car args) (cadr args)))))
    (if pass?
        (begin (set! pass-count (+ 1 pass-count))
               (format #t "  ok: ~a~%" label))
        (begin (set! fail-count (+ 1 fail-count))
               (format #t "  FAIL: ~a~%" label)
               (unless (null? (cdr args))
                 (format #t "    expected: ~s~%    got:      ~s~%"
                         (cadr args) (car args)))))))

(define (scenario s) (format #t "~%── ~a ──~%" s))

(define (test-summary!)
  (format #t "~%=== Results: ~a passed, ~a failed ===~%"
          pass-count fail-count)
  (exit (if (zero? fail-count) 0 1)))

(define GUARDIAN "did:keri:EGuardianAna")
(define OPERATOR "aid:operator-node7")
(define CONSENT `((consent . ((guardian . ,GUARDIAN)
                             (operator . ,OPERATOR)
                             (said . "said:joint-consent-1")))))
(define (reason-of reply) (refusal-reason (cdr reply)))


(scenario "federated rides provenance, not evidence and not consent")
(define book '())
(check "federated is a known lane" (lane-known? 'federated) #t)
(check "federated is its own class" (lane-federated? 'federated) #t)
(check "not consent-gated, not transport, not refused"
       (and (not (lane-consent-gated? 'federated))
            (not (lane-transport? 'federated))
            (not (lane-refused? 'federated))))
(check "source + source-id admits — no evidence SAID needed"
       (admitted? (admit-intent book 'federated
                                '((source . birdweather)
                                  (source-id . "det-8821"))))
       #t)
(check "no provenance refuses as source-required"
       (reason-of (admit-intent book 'federated '()))
       'source-required)
(check "source without source-id still refuses"
       (reason-of (admit-intent book 'federated '((source . inaturalist))))
       'source-required)
(check "an unknown lane still refuses as unknown-lane"
       (reason-of (admit-intent book 'not-a-lane '())) 'unknown-lane)


(scenario "the federated record round-trips through the gate")
(define rec
  (make-federated-record
   #:source 'birdweather #:source-id "det-9912"
   #:subject "subject-meadow-1" #:channel 'acoustic
   #:at 1730000000
   #:payload '((species . "Erithacus rubecula") (score . 0.87))))
(check "record carries its provenance"
       (federated-record-source rec) 'birdweather)
(check "record→intent admits on the federated lane"
       (admitted? (admit-intent book (car (federated-record->intent rec))
                                (cdr (federated-record->intent rec))))
       #t)
(check "a record without provenance cannot be born"
       (catch #t
         (lambda () (make-federated-record #:source 'x #:source-id #f
                                           #:subject #f #:channel 'env
                                           #:at 0 #:payload '())
                    #f)
         (lambda _ 'refused))
       'refused)


(scenario "the source catalogue marks each network honestly")
(check "birdweather is live-now"
       (source-status 'birdweather) 'live-now)
(check "goe waits on partnership"
       (source-status 'goe) 'gated-partnership)
(check "farmbot-demo is open-invitation, farmbot opt-in-operator"
       (list (source-status 'farmbot-demo) (source-status 'farmbot))
       '(open-invitation opt-in-operator))
(check "lethal actuation is named as excluded, never carried"
       (source-status 'goodnature) 'excluded)
(check "a network we have not found is simply not known"
       (source-known? 'strangers-network) #f)


(scenario "write-kinds bound what a declared actuator accepts")
(define garden-cell
  (make-cell-decl #:node-id "farm-1" #:heads '(cam)
                  #:link-type 'wifi #:location-class 'garden
                  #:accepts-write #t #:write-kinds '(irrigate mist)))
(define consent+cell (cons (cons 'cell garden-cell) CONSENT))
(check "a kind the cell declares is admitted"
       (admitted? (admit-intent book 'emit
                                (cons '(write-kind . irrigate) consent+cell)))
       #t)
(check "a kind the cell does not declare refuses as write-refused"
       (reason-of (admit-intent book 'emit
                                (cons '(write-kind . acoustic-playback)
                                      consent+cell)))
       'write-refused)
(check "a kind the commons does not name refuses as write-refused"
       (reason-of (admit-intent book 'emit
                                (cons '(write-kind . vaporize) CONSENT)))
       'write-refused)
(define open-cell-any
  (make-cell-decl #:node-id "node-legacy" #:heads '(cam mic)
                  #:link-type 'wifi #:location-class 'garden
                  #:accepts-write #t))
(check "write-kinds #f stays open — the back-compat declaration"
       (admitted? (admit-intent book 'emit
                                (cons '(write-kind . vibrate)
                                      (cons (cons 'cell open-cell-any)
                                            CONSENT))))
       #t)
(check "consent still rules — write-kind alone never admits"
       (reason-of (admit-intent book 'emit
                                `((cell . ,garden-cell)
                                  (write-kind . irrigate))))
       'consent-required)


(scenario "a visitor's browser is a declared, session-bounded cell")
(define session-cell
  (browser-session->cell "session-3f9a"
                         '((heads . (mic camera))
                           (actuate . #t)
                           (write-kinds . (soundscape)))))
(check "the session becomes a real cell-decl"
       (cell-decl? session-cell) #t)
(check "its write-kinds are what the browser granted"
       (cell-decl-write-kinds session-cell) '(soundscape))
(check "every webnode write-kind is a kind the commons names"
       (every write-kind? (webnode-write-kinds)))
(define visit
  (webnode-record "session-3f9a" 'acoustic '((species . "Parus major"))
                  #:subject "subject-garden-1" #:at 1730000100))
(check "the visitor's detection is provenance-tagged web-visitor"
       (federated-record-source visit) 'web-visitor)
(check "and honestly flagged uncalibrated"
       (assq-ref (federated-record-payload visit) 'uncalibrated) #t)


(test-summary!)
