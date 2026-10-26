;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; tests/e2e/refused-lanes.scm — the honest refusals.
;;;
;;; Every refused lane answers a structured reason, not silence:
;;; hop/compute/engineered intents → lane-refused; emit/cast/store intents
;;; → consent-required unless they carry the joint guardian+operator
;;; consent (the consent gate's positive case is checked too); an
;;; unnamed lane → unknown-lane; a sense offer without the gate's evidence
;;; SAID → evidence-required; a reading without a subject →
;;; subject-required; a reading against an unconsented subject →
;;; consent-required. This suite is the gates' negative space —
;;; the half that keeps the commons honest.
;;;
;;; Run: guile --no-auto-compile -L module -L . tests/e2e/refused-lanes.scm

(use-modules (living specs)
             (living agents)
             (living sense-subject)
             (living offers)
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

(define vat (spawn-vat #:name "refused-lanes-e2e"))

(define GUARDIAN "did:keri:EGuardianAna")
(define SUBJECT  "eco:turdus-territory-7")
(define CAL-SAID "said:cal-node7-48k-reference")
(define (reason-of reply) (refusal-reason (cdr reply)))


(with-vat vat

  (scenario "the refused lanes — hop/compute/engineered, denied by name")
  (define book
    (declare-lane '() 'sense CAL-SAID))
  (for-each
   (lambda (lane)
     (let ((reply (admit-intent book lane '())))
       (check (format #f "~a intent is refused" lane)
              (refused? reply) #t)
       (check (format #f "~a refusal says lane-refused" lane)
              (reason-of reply) 'lane-refused)
       (check (format #f "~a refusal names its lane" lane)
              (refusal-lane (cdr reply)) lane)))
   '(hop compute engineered))

  (scenario "the consent lanes — emit/cast/store refuse without joint consent")
  (define OPERATOR "aid:operator-node7")
  (for-each
   (lambda (lane)
     (let ((reply (admit-intent book lane '())))
       (check (format #f "~a with no consent refuses" lane)
              (reason-of reply) 'consent-required))
     (let ((reply (admit-intent book lane
                     '((consent . ((guardian . "did:keri:EGuardianAna")))))))
       (check (format #f "~a with one signer refuses" lane)
              (reason-of reply) 'consent-required))
     (let* ((consent `((consent . ((guardian . ,GUARDIAN)
                                  (operator . ,OPERATOR)
                                  (said . "said:joint-emit-1")))))
            (reply (admit-intent book lane consent)))
       (check (format #f "~a with joint consent is admitted" lane)
              (admitted? reply) #t)))
   '(emit cast store))

  (scenario "the transport lane — relay needs a content-addressed payload")
  (check "relay without a packet SAID refuses"
         (reason-of (admit-intent book 'relay '())) 'payload-required)
  (check "relay refusal names its lane"
         (refusal-lane (cdr (admit-intent book 'relay '()))) 'relay)
  (check "relay carrying a packet SAID is admitted"
         (admitted? (admit-intent book 'relay
                                  '((packet-said . "said:bundle-node7-0482"))))
         #t)

  (scenario "lanes the commons does not name")
  (check "an unnamed lane refuses as unknown"
         (reason-of (admit-intent book 'warp '())) 'unknown-lane)
  (check "even an admitted lane refuses without evidence"
         (reason-of (admit-intent '() 'sense '())) 'evidence-required)

  (scenario "the offer gate — evidence first, declarations second")
  (define offer
    (make-sense-offer #:id "offer-1" #:subject SUBJECT
                      #:kind 'bioacoustic #:cadence 60 #:duty-cycle 0.3
                      #:taxa-scope 'vocal #:evidence-said CAL-SAID))
  (check "a gate with no evidence refuses the offer"
         (reason-of (admit-offer '() offer)) 'evidence-required)
  (define unevidenced
    (make-sense-offer #:id "offer-2" #:subject SUBJECT
                      #:kind 'bioacoustic #:cadence 60 #:duty-cycle 0.3
                      #:taxa-scope 'vocal #:evidence-said #f))
  (check "an offer citing no evidence refused on a gated lane"
         (reason-of (admit-offer book unevidenced)) 'evidence-required)
  (define wrong-evidence
    (make-sense-offer #:id "offer-3" #:subject SUBJECT
                      #:kind 'bioacoustic #:cadence 60 #:duty-cycle 0.3
                      #:taxa-scope 'vocal #:evidence-said "said:not-the-gates"))
  (check "an offer citing another SAID refused"
         (reason-of (admit-offer book wrong-evidence)) 'evidence-required)
  (check "the honest offer passes the same gate"
         (admitted? (admit-offer book offer)) #t)

  (scenario "the reading boundary — subject and consent")
  (define eco
    (spawn ^eco-agent
           (make-ecological-agent #:id SUBJECT #:guardian-aid GUARDIAN
                                  #:taxa-scope 'vocal
                                  #:custody "acct:guardian-ana:thrush-7")
           #f))
  (define agents-map (list (cons SUBJECT ($ eco 'who))))
  (define orphan-reading
    (make-reading #:subject #f #:channel "node-7" #:timestamp 1000
                  #:payload '((species . "Turdus migratorius"))
                  #:mic-cal CAL-SAID #:gain 12))
  (check "a reading without a subject is refused"
         (reason-of (admit-reading agents-map orphan-reading))
         'subject-required)
  (define stray-reading
    (make-reading #:subject "eco:nobody" #:channel "node-7" #:timestamp 1000
                  #:payload '() #:mic-cal CAL-SAID #:gain 12))
  (check "a reading naming an unregistered subject is refused"
         (reason-of (admit-reading agents-map stray-reading))
         'unknown-subject)
  (define good-reading
    (make-reading #:subject SUBJECT #:channel "node-7" #:timestamp 1000
                  #:payload '((species . "Turdus migratorius"))
                  #:mic-cal CAL-SAID #:gain 12))
  (check "a reading without guardian consent is refused"
         (reason-of (admit-reading agents-map good-reading))
         'consent-required)
  ($ eco 'grant-consent GUARDIAN
     (guardian-sig GUARDIAN "said:consent-thrush-7") "said:consent-thrush-7")
  (check "consent granted, the same reading is admitted"
         (admitted? (admit-reading
                     (list (cons SUBJECT ($ eco 'who))) good-reading))
         #t)

  (test-summary!))
