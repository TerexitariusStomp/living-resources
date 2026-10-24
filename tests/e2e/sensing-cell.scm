;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; tests/e2e/sensing-cell.scm — the whole pipeline, simulated.
;;;
;;; Register a guardian and an ecological subject → declare the cell and a
;;; sense offer → feed three detection readings (two through the mic
;;; adapter's wire format, one constructed) → assert the fleet quorum →
;;; assert the witnessed receipt carries both SAIDs → assert the credit
;;; event lands in the subject's custodial account.
;;;
;;; Runs under real Goblins when it is on the load path, and under the
;;; specs.scm synchronous shim when it is not — the acts being tested are
;;; identical either way.
;;;
;;; Run: guile --no-auto-compile -L module -L . tests/e2e/sensing-cell.scm

(use-modules (living specs)
             (living agents)
             (living sense-subject)
             (living offers)
             (living attest)
             (living settlement)
             (adapters mic)
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

(define (check-error label thunk)
  (check label (catch #t (lambda () (thunk) #f) (lambda _ #t))))

(define (scenario s) (format #t "~%── ~a ──~%" s))

(define (test-summary!)
  (format #t "~%=== Results: ~a passed, ~a failed ===~%"
          pass-count fail-count)
  (exit (if (zero? fail-count) 0 1)))

(define vat (spawn-vat #:name "sensing-cell-e2e"))

(define GUARDIAN "did:keri:EGuardianAna")
(define STRANGER "did:keri:EStrangerMal")
(define SUBJECT  "eco:turdus-territory-7")
(define CUSTODY  "acct:guardian-ana:thrush-7")
(define CAL-SAID "said:cal-node7-48k-reference")
(define CONSENT-SAID "said:consent-thrush-7")
(define (sig aid payload) (guardian-sig aid payload))


(with-vat vat

  (scenario "the subject — guardian held, voice 0")
  (define eco
    (spawn ^eco-agent
           (make-ecological-agent #:id SUBJECT #:guardian-aid GUARDIAN
                                  #:taxa-scope 'vocal #:custody CUSTODY)
           #f))
  (check "the subject's voice is 0" ($ eco 'voice) 0)
  (check "no consent on file yet" ($ eco 'consented?) #f)
  (check-error "a stranger cannot grant consent"
               (lambda () ($ eco 'grant-consent STRANGER
                             (sig STRANGER CONSENT-SAID) CONSENT-SAID)))
  (check-error "the subject cannot amend itself"
               (lambda () ($ eco 'amend SUBJECT
                             (sig SUBJECT '((taxa-scope . plant)))
                             '((taxa-scope . plant)))))
  ($ eco 'grant-consent GUARDIAN (sig GUARDIAN CONSENT-SAID) CONSENT-SAID)
  (check "guardian consent lands" ($ eco 'consented?) #t)

  (scenario "the cell and the offer — declared and calibrated")
  (define cell
    (make-cell-decl #:node-id "node-7" #:heads '(mic)
                    #:link-type 'wifi #:location-class 'garden))
  (define book
    (declare-lane (declare-lane '() 'sense CAL-SAID)
                  'fleet "said:fleet-evidence"))
  (define offer
    (make-sense-offer #:id "offer-1" #:subject SUBJECT
                      #:kind 'bioacoustic #:cadence 60 #:duty-cycle 0.3
                      #:taxa-scope 'vocal #:evidence-said CAL-SAID))
  (check "the sense offer is admitted"
         (admitted? (admit-offer book offer)) #t)
  (check "the cell declares its heads"
         (cell-decl-heads cell) '(mic))

  (scenario "three detections — two over the wire, one constructed")
  (define node
    (spawn ^sense-node SUBJECT "offer-1" '() '()
           *default-quorum-size* *default-quorum-nodes*))
  (define agents-map (list (cons SUBJECT ($ eco 'who))))
  (define wire
    (map (lambda (p) (cdr p))
         (call-with-input-string
             "((species . \"Turdus migratorius\") (confidence . 0.91) (timestamp . 1000) (node . \"node-7\") (mic_cal . \"said:cal-node7-48k-reference\") (gain . 12) (subject . \"eco:turdus-territory-7\"))\n((species . \"Turdus migratorius\") (confidence . 0.87) (timestamp . 1100) (node . \"node-8\") (mic_cal . \"said:cal-node8\") (gain . 12) (subject . \"eco:turdus-territory-7\"))\n"
           read-detections)))
  (define third
    (make-reading #:subject SUBJECT #:channel "node-7" #:timestamp 1200
                  #:payload '((species . "Turdus migratorius")
                              (confidence . 0.94))
                  #:mic-cal CAL-SAID #:gain 12))
  (for-each
   (lambda (r)
     (check "a reading is admitted at the gate"
            (admitted? (admit-reading agents-map r)) #t)
     ($ node 'ingest r))
   (append wire (list third)))
  (check "three legs emitted" (length ($ node 'legs)) 3)
  (check "the fleet reaches quorum" ($ node 'quorum?) #t)
  (check "quorum agrees across channels"
         (quorum-met? ($ node 'legs)) #t)

  (scenario "the receipt — witnessed, two SAIDs")
  (define att
    (build-witnessed-receipt #:subject SUBJECT #:legs ($ node 'legs)
                             #:audio-said "said:audio-helia-abc"
                             #:detection-said "said:det-ledger-def"))
  (check "the quorum attests" (attested? att) #t)
  (define receipt (cdr att))
  (check "both evidence SAIDs ride the receipt"
         (list (receipt-audio-said receipt)
               (receipt-detection-said receipt))
         '("said:audio-helia-abc" "said:det-ledger-def"))
  (check "two distinct nodes witnessed"
         (>= (length (receipt-witnessed receipt)) 2) #t)
  (check "the quantity is the contributions attested"
         (receipt-quantity receipt) 3)

  (scenario "the credit — to the subject, held by the guardian")
  (define draft (receipt->credit-draft receipt ($ eco 'who)))
  (check "the draft credits the agent"
         (assoc-ref draft 'provider) SUBJECT)
  (check "the draft names the guardian's custody"
         (assoc-ref draft 'account) CUSTODY)
  (define-values (book* event)
    (settle-receipt '() receipt ($ eco 'who)))
  (check "credit lands in the custodial account"
         (balance-of book* CUSTODY) 3)
  (check "the credit event names the ecological agent"
         (credit-event-agent-id event) SUBJECT)
  (check "the credit event names the guardian"
         (credit-event-guardian-aid event) GUARDIAN)
  (check "the event points back at the receipt"
         (credit-event-receipt-id event) (receipt-id receipt))

  (test-summary!))
