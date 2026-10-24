;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; tests/e2e/write-lanes.scm — the node's write half.
;;;
;;; Cloud-write and bio-write as positive paths: emit/cast/store intents
;;; admit on the joint guardian+operator consent; store additionally
;;; honors the cell's accepts-write declaration; a performed write leg
;;; settles credit to the node operator, not the ecology. And the
;;; boundary holds — evidence-blocked lanes still refuse no matter whose
;;; consent rides along.
;;;
;;; Run: guile --no-auto-compile -L module -L . tests/e2e/write-lanes.scm

(use-modules (living specs)
             (living offers)
             (living settlement)
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
(define OP-ACCT  "acct:operator-node7")
(define CONSENT `((consent . ((guardian . ,GUARDIAN)
                             (operator . ,OPERATOR)
                             (said . "said:joint-consent-1")))))
(define (reason-of reply) (refusal-reason (cdr reply)))


(scenario "bio-write — emit rides joint consent")
(define book (declare-lane '() 'sense "said:cal-node7"))
(check "emit with joint consent is admitted"
       (admitted? (admit-intent book 'emit CONSENT)) #t)
(check "cast with joint consent is admitted"
       (admitted? (admit-intent book 'cast CONSENT)) #t)

(scenario "cloud-write — store honors the cell's declaration")
(define open-cell
  (make-cell-decl #:node-id "node-7" #:heads '(cam mic env emit)
                  #:link-type 'wifi #:location-class 'garden
                  #:accepts-write #t))
(define closed-cell
  (make-cell-decl #:node-id "node-9" #:heads '(cam mic env emit)
                  #:link-type 'lora #:location-class 'shore-dock
                  #:accepts-write #f))
(check "store to an accepts-write cell is admitted"
       (admitted? (admit-intent book 'store
                                (cons (cons 'cell open-cell) CONSENT))) #t)
(check "store to a closed cell refuses as write-refused"
       (reason-of (admit-intent book 'store
                                (cons (cons 'cell closed-cell) CONSENT)))
       'write-refused)
(check "store without a named cell still needs only consent"
       (admitted? (admit-intent book 'store CONSENT)) #t)

(scenario "consent is not evidence — the refused lanes hold")
(for-each
 (lambda (lane)
   (check (format #f "~a refuses even with full consent" lane)
          (reason-of (admit-intent book lane CONSENT)) 'lane-refused))
 '(hop compute engineered))

(scenario "the write leg settles to the operator")
(define write-receipt
  (make-witnessed-receipt
   #:id "rcpt-write-1" #:subject "node-7"
   #:witnessed '("edge-1" "edge-2" "edge-3")
   #:audio-said "said:task-proof-1"
   #:detection-said "said:task-ledger-1"
   #:window '(1000 . 2000) #:quantity 1))
(let-values (((book' event)
              (settle-write '() write-receipt OP-ACCT OPERATOR)))
  (check "operator account credited one write leg"
         (balance-of book' OP-ACCT) 1)
  (check "the event names the operator as earner"
         (credit-event-agent-id event) OPERATOR)
  (check "the event ties back to the receipt"
         (credit-event-receipt-id event) "rcpt-write-1"))

(scenario "no evidence, no credit — the write side too")
(define bare-receipt
  (make-witnessed-receipt
   #:id "rcpt-bare" #:subject "node-7" #:witnessed '("e1")
   #:audio-said #f #:detection-said #f
   #:window '(1 . 2) #:quantity 1))
(check "an unevidenced write receipt earns nothing"
       (catch #t
         (lambda () (settle-write '() bare-receipt OP-ACCT OPERATOR) #f)
         (lambda _ 'refused))
       'refused)

(test-summary!)
