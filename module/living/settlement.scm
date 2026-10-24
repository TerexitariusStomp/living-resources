;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; module/living/settlement.scm — mutual credit for witnessed sensing.
;;;
;;; WHAT THE FILE HOLDS. The settle: a witnessed receipt becomes a credit
;;; event against the ecological agent's custodial account — the account
;;; its guardian holds, because the subject has voice 0 and holds nothing
;;; itself. The book is a plain account→balance alist folded forward; the
;;; credit event is the record. Per-contribution means per-reading: a
;;; receipt's quantity is the number of legs it attests.
;;;
;;; THE ONLY RULE THE SETTLE ENFORCES. A receipt that does not carry both
;;; evidence SAIDs is refused before it reaches the book — settlement is
;;; where "no evidence, no credit" stops being a slogan. Everything else
;;; is bookkeeping.

(define-module (living settlement)
  #:use-module (srfi srfi-1)
  #:use-module (srfi srfi-9)
  #:use-module (living specs)
  #:use-module (living attest)
  #:export (<credit-event> make-credit-event credit-event?
            credit-event-id credit-event-account credit-event-agent-id
            credit-event-guardian-aid credit-event-receipt-id
            credit-event-quantity credit-event-at
            settle-receipt settle-write balance-of))


;;; ── the credit event ────────────────────────────────────────────────────

(define-record-type <credit-event>
  (%make-credit-event id account agent-id guardian-aid receipt-id
                      quantity at)
  credit-event?
  (id           credit-event-id)
  (account      credit-event-account)      ; the custodial account credited
  (agent-id     credit-event-agent-id)     ; the ecological subject earning
  (guardian-aid credit-event-guardian-aid) ; the guardian holding custody
  (receipt-id   credit-event-receipt-id)   ; the receipt this settles
  (quantity     credit-event-quantity)     ; readings credited
  (at           credit-event-at))          ; epoch ms

(define* (make-credit-event #:key id account agent-id guardian-aid
                            receipt-id quantity at)
  (%make-credit-event id account agent-id guardian-aid receipt-id
                      quantity at))


;;; ── the settle ──────────────────────────────────────────────────────────
;;; (settle-receipt book receipt agent [#:at now]) → (values book' event)
;;; book is account → balance; the fold is additive and monotone — mutual
;;; credit here only ever accrues to witnessed contribution. Refuses before
;;; writing: an unattested receipt, an agent whose custody is unnamed, or a
;;; receipt naming a different subject than the agent settling it.

(define* (settle-receipt book receipt agent #:key (at #f))
  (let ((account (ecological-agent-custody agent)))
    (cond
     ((not (witnessed-receipt? receipt))
      (error "settle: not a witnessed receipt" receipt))
     ((not (and (receipt-audio-said receipt)
                (receipt-detection-said receipt)))
      (error "settle: a receipt without both evidence SAIDs earns nothing"))
     ((not (equal? (receipt-subject receipt)
                   (ecological-agent-id agent)))
      (error "settle: receipt names another subject"))
     ((not account)
      (error "settle: the agent names no custodial account"))
     (else
      (let* ((quantity (receipt-quantity receipt))
             (prior (or (assoc-ref book account) 0))
             (event (make-credit-event
                     #:id (generate-id "cr-")
                     #:account account
                     #:agent-id (ecological-agent-id agent)
                     #:guardian-aid (ecological-agent-guardian-aid agent)
                     #:receipt-id (receipt-id receipt)
                     #:quantity quantity
                     #:at (or at (and (receipt-window receipt)
                                      (cdr (receipt-window receipt)))))))
        (values (assoc-set! book account (+ prior quantity))
                event))))))

;;; ── write legs — the operator's side of the ledger ──────────────────────
;;; A node that performs a consent-gated write (task/store/emit) earns for
;;; the operator, not the ecology. The gate is identical: a receipt without
;;; both evidence SAIDs earns nothing — proof of the write is what pays.

(define* (settle-write book receipt operator-account operator-aid
                       #:key (at #f))
  "Settle a write leg to OPERATOR-ACCOUNT. Same evidence rule as
   settle-receipt; the earner is the node operator, not a subject."
  (cond
   ((not (witnessed-receipt? receipt))
    (error "settle-write: not a witnessed receipt" receipt))
   ((not (and (receipt-audio-said receipt)
              (receipt-detection-said receipt)))
    (error "settle-write: a receipt without both evidence SAIDs earns nothing"))
   ((not operator-account)
    (error "settle-write: the operator names no account"))
   (else
    (let* ((quantity (receipt-quantity receipt))
           (prior (or (assoc-ref book operator-account) 0))
           (event (make-credit-event
                   #:id (generate-id "cr-")
                   #:account operator-account
                   #:agent-id operator-aid
                   #:guardian-aid operator-aid
                   #:receipt-id (receipt-id receipt)
                   #:quantity quantity
                   #:at (or at (and (receipt-window receipt)
                                    (cdr (receipt-window receipt)))))))
      (values (assoc-set! book operator-account (+ prior quantity))
              event)))))

(define (balance-of book account)
  (or (assoc-ref book account) 0))
