;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; tests/e2e/connectome-witness.scm — wiring diagrams as witnesses.
;;;
;;; The connectome pipeline end to end: runner JSONL parses into verdicts
;;; via the adapter seam → verdicts stamp legs on connectome:<name>
;;; channels → a distinct-topology quorum folds into one evidence digest →
;;; a witnessed receipt binds that digest beside its audio/detection
;;; SAIDs → settlement still credits the subject. Plus the refusals: not
;;; enough distinct wiring, a verdict not reproducible, a connectome leg
;;; counted as its own channel but never as the quorum's only witness.
;;;
;;; Run: guile --no-auto-compile -L module -L . tests/e2e/connectome-witness.scm

(use-modules (living specs)
             (living agents)
             (living sense-subject)
             (living offers)
             (living attest)
             (living settlement)
             (living connectome)
             (adapters connectome)
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

(define vat (spawn-vat #:name "connectome-witness-e2e"))

(define GUARDIAN "did:keri:EGuardianAna")
(define SUBJECT  "eco:turdus-territory-7")
(define CUSTODY  "acct:guardian-ana:thrush-7")
(define CAL-SAID "said:cal-node7-48k-reference")
(define CONSENT-SAID "said:consent-thrush-7")

;;; Runner output shape — what lif.py emits per connectome (alist form,
;;; so this suite needs no (json) module).
(define fixture-line
  "((connectome . celegans) (input_said . \"blake2s:abc\") (action . 1) (confidence . 51) (spike_count . 2519) (spike_digest . \"blake2s:digest-ce\") (steps . 10) (encoder . \"lif-sensing-v1\"))")

(with-vat vat

  (scenario "setup — subject, gate, node")
  (define eco
    (spawn ^eco-agent
           (make-ecological-agent #:id SUBJECT #:guardian-aid GUARDIAN
                                  #:taxa-scope 'vocal #:custody CUSTODY)
           #f))
  ($ eco 'grant-consent GUARDIAN (guardian-sig GUARDIAN CONSENT-SAID)
     CONSENT-SAID)
  (define node
    (spawn ^sense-node SUBJECT "offer-1" '() '()
           *default-quorum-size* *default-quorum-nodes*))
  (define r
    (make-reading #:subject SUBJECT #:channel "node-7" #:timestamp 1200
                  #:payload '((species . "Turdus migratorius")
                              (confidence . 0.91))
                  #:mic-cal CAL-SAID #:gain 12))
  ($ node 'ingest r)
  ($ node 'ingest (make-reading #:subject SUBJECT #:channel "node-8"
                                #:timestamp 1300 #:payload '((species . "Turdus migratorius") (confidence . 0.87))
                                #:mic-cal "said:cal-node8" #:gain 12))
  ($ node 'ingest (make-reading #:subject SUBJECT #:channel "node-9"
                                #:timestamp 1400 #:payload '((species . "Turdus migratorius") (confidence . 0.94))
                                #:mic-cal "said:cal-node9" #:gain 12))
  (check "node legs at quorum" ($ node 'quorum?) #t)

  (scenario "verdicts — the adapter parses the runner's wire")
  (define v1 (verdict-line->verdict fixture-line))
  (check "a verdict parses" (connectome-verdict? v1) #t)
  (check "the connectome names itself" (connectome-verdict-connectome v1) 'celegans)
  (check "the encoder version rides" (connectome-verdict-encoder v1) "lif-sensing-v1")
  (check "skipped lines refuse quietly"
         (verdict-line->verdict "not a verdict") #f)

  (define v2 (make-connectome-verdict
              #:id "cv-2" #:connectome 'drosophila
              #:input-said "blake2s:abc" #:action 1 #:confidence 60
              #:spike-count 466 #:spike-digest "blake2s:digest-fly"
              #:steps 10 #:encoder "lif-sensing-v1"))
  (define v3 (make-connectome-verdict
              #:id "cv-3" #:connectome 'human
              #:input-said "blake2s:abc" #:action 1 #:confidence 55
              #:spike-count 2202 #:spike-digest "blake2s:digest-human"
              #:steps 10 #:encoder "lif-sensing-v1"))
  (define v3-dup (make-connectome-verdict
                  #:id "cv-3b" #:connectome 'human
                  #:input-said "blake2s:abc" #:action 1 #:confidence 55
                  #:spike-count 2202 #:spike-digest "blake2s:digest-human"
                  #:steps 10 #:encoder "lif-sensing-v1"))
  (check-error "a bad action refuses the record"
               (lambda () (make-connectome-verdict
                           #:id "cv-x" #:connectome 'rat #:action 7
                           #:confidence 50 #:spike-count 0
                           #:spike-digest #f #:steps 1 #:encoder "x")))

  (scenario "the connectome quorum — distinct topologies or no witness")
  (check "three distinct connectomes meet quorum"
         (connectome-quorum? (list v1 v2 v3)) #t)
  (check "two verdicts is not quorum"
         (connectome-quorum? (list v1 v2)) #f)
  (check "one connectome twice is not quorum"
         (connectome-quorum? (list v3 v3-dup)) #f)
  (check "the digest binds the witness set"
         (string? (verdicts-digest (list v1 v2 v3))) #t)
  (check "no verdicts → no digest"
         (verdicts-digest '()) #f)

  (scenario "verdict legs — each wiring diagram is its own channel")
  (define vlegs (map (lambda (v) (verdict->leg v SUBJECT r))
                     (list v1 v2 v3)))
  (check "legs carry the connectome channel"
         (fleet-leg-node-id (car vlegs)) 'connectome:celegans)
  (check "the leg's reading is the witnessed reading"
         (fleet-leg-reading (car vlegs)) r)
  (check "three verdicts → three distinct channels"
         (length (distinct-nodes vlegs)) 3)

  (scenario "the receipt — connectome evidence bound, additive")
  (define csaid (verdicts-digest (list v1 v2 v3)))
  (define att
    (build-witnessed-receipt #:subject SUBJECT #:legs ($ node 'legs)
                             #:audio-said "said:audio-abc"
                             #:detection-said "said:det-def"
                             #:connectome-said csaid))
  (check "the quorum attests" (attested? att) #t)
  (define receipt (cdr att))
  (check "the connectome digest rides the receipt"
         (receipt-connectome-said receipt) csaid)
  (check "the two SAIDs are still required and present"
         (list (receipt-audio-said receipt)
               (receipt-detection-said receipt))
         '("said:audio-abc" "said:det-def"))

  (scenario "the receipt without connectome evidence — still valid")
  (define att-plain
    (build-witnessed-receipt #:subject SUBJECT #:legs ($ node 'legs)
                             #:audio-said "said:audio-abc"
                             #:detection-said "said:det-def"))
  (check "no connectome leg → #f, not a refusal"
         (and (attested? att-plain)
              (not (receipt-connectome-said (cdr att-plain))))
         #t)

  (scenario "settlement — credit flows regardless of connectome legs")
  (define-values (book* event)
    (settle-receipt '() receipt ($ eco 'who)))
  (check "credit lands in custody" (balance-of book* CUSTODY) 3)
  (check "the draft carries the connectome evidence"
         (let ((d (receipt->credit-draft receipt ($ eco 'who))))
           (assoc-ref (assoc-ref d 'evidence) 'connectome))
         csaid)

  (test-summary!))
