;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; module/living/attest.scm — the witnessed receipt.
;;;
;;; WHAT THE FILE HOLDS. The pure half of attestation: count a quorum of
;;; legs, merge them into a witnessed receipt that links the two evidence
;;; SAIDs — the lossless audio and the detection record — and draft the
;;; economic event that credits the ecological subject through its
;;; guardian's custodial account. No actors: a receipt is a value, and a
;;; refusal is a value too — (receipt . r) | (refused . reason).
;;;
;;; THE WITNESS RULE. A window is witnessed when it carries at least
;;; *default-quorum-size* legs across at least *default-quorum-nodes*
;;; distinct channels: no single node may witness itself, and two legs is
;;; agreement, not quorum. The digest binds subject, witnesses, SAIDs and
;;; window into one string the receipt carries; gcrypt's sha256 when it is
;;; on the load path, a clearly-marked fallback where it is not — the seam
;;; is named so the real hash is one binding away.

(define-module (living attest)
  #:use-module (srfi srfi-1)
  #:use-module (srfi srfi-9)
  #:use-module (living specs)
  #:export (distinct-nodes legs-window quorum-met? merge-legs
            build-witnessed-receipt receipt->credit-draft
            attested? refusal-of))


;;; ── the digest seam ─────────────────────────────────────────────────────
;;; sha256 over the printed fields when (gcrypt) resolves; a 64-bit
;;; string-hash fallback otherwise. A receipt minted under the fallback
;;; says so in its digest's length — it is never mistaken for the real
;;; commitment.

(define (%digest-fields . fields)
  (let ((s (call-with-output-string
            (lambda (p) (write fields p)))))
    (catch #t
      (lambda ()
        (let* ((h (resolve-interface '(gcrypt hash)))
               (b (resolve-interface '(gcrypt base16)))
               (sha256 (module-ref h 'sha256))
               (b16 (module-ref b 'bytevector->base16-string)))
          (string-downcase (b16 (sha256 (string->utf8 s))))))
      (lambda _ (string-append "fallback:" (number->string (string-hash s) 16))))))


;;; ── the quorum ──────────────────────────────────────────────────────────

(define (distinct-nodes legs)
  (delete-duplicates (map fleet-leg-node-id legs)))

(define (legs-window legs)
  "The (start . end) ms window the legs span; #f on an empty fleet."
  (and (pair? legs)
       (cons (fold min (fleet-leg-at (car legs)) (map fleet-leg-at legs))
             (fold max (fleet-leg-at (car legs)) (map fleet-leg-at legs)))))

(define* (quorum-met? legs #:key (size *default-quorum-size*)
                      (min-nodes *default-quorum-nodes*))
  (and (>= (length legs) size)
       (>= (length (distinct-nodes legs)) min-nodes)))

(define (merge-legs legs)
  "The fleet's summary of itself: leg count, the nodes that stood behind
   them, the species tallies across leg payloads, and the window covered."
  (let* ((nodes (distinct-nodes legs))
         (species (fold
                   (lambda (leg acc)
                     (let* ((p (fleet-leg-reading leg))
                            (sp (and (reading? p)
                                     (assoc-ref (reading-payload p) 'species))))
                       (if sp
                           (let ((cell (assoc sp acc)))
                             (if cell
                                 (begin (set-cdr! cell (+ 1 (cdr cell))) acc)
                                 (cons (cons sp 1) acc)))
                           acc)))
                   '() legs)))
    `((count . ,(length legs))
      (nodes . ,nodes)
      (species . ,species)
      (window . ,(legs-window legs)))))


;;; ── the receipt ─────────────────────────────────────────────────────────
;;; (build-witnessed-receipt #:subject #:legs #:audio-said #:detection-said
;;;                          [#:size #:min-nodes]) → (receipt . r) | (refused . r)
;;;
;;; Both SAIDs are required before a receipt exists: audio is the evidence
;;; a buyer replays, detection is the record a ledger cites — one without
;;; the other is not a receipt, it is half a claim.

(define* (build-witnessed-receipt #:key subject legs audio-said detection-said
                                  (size *default-quorum-size*)
                                  (min-nodes *default-quorum-nodes*))
  (cond
   ((not subject)
    (cons 'refused 'subject-required))
   ((not (quorum-met? legs #:size size #:min-nodes min-nodes))
    (cons 'refused
          (list 'quorum-not-met
                (length legs) (length (distinct-nodes legs)))))
   ((not audio-said)
    (cons 'refused 'audio-said-required))
   ((not detection-said)
    (cons 'refused 'detection-said-required))
   (else
    (let* ((nodes (distinct-nodes legs))
           (window (legs-window legs))
           (digest (%digest-fields 'living-receipt/v1 subject nodes
                                   audio-said detection-said window)))
      (cons 'receipt
            (make-witnessed-receipt
             #:id (generate-id "rcpt-")
             #:subject subject
             #:witnessed nodes
             #:audio-said audio-said
             #:detection-said detection-said
             #:window window
             #:quantity (length legs)
             #:digest digest))))))

(define (attested? r) (and (pair? r) (eq? 'receipt (car r))))
(define (refusal-of r) (and (pair? r) (eq? 'refused (car r)) (cdr r)))


;;; ── the credit draft ────────────────────────────────────────────────────
;;; The economic event a settlement lands: action 'use (the commons used
;;; the subject's sensed contribution), provider the ecological agent,
;;; custody the guardian's custodial account — the agent earns, the
;;; guardian holds. An alist, not a record, because the wire to the hREA
;;; fold is JSON and the draft lands verbatim.

(define (receipt->credit-draft receipt agent)
  `((note . "living-receipt/v1")
    (action . "use")
    (provider . ,(ecological-agent-id agent))
    (custodian . ,(ecological-agent-guardian-aid agent))
    (account . ,(ecological-agent-custody agent))
    (receiver . "commons:living-sensing")
    (resource-quantity . ((unit . "readings")
                          (amount . ,(receipt-quantity receipt))))
    (evidence . ((audio . ,(receipt-audio-said receipt))
                 (detection . ,(receipt-detection-said receipt))
                 (witnessed . ,(receipt-witnessed receipt))
                 (window . ,(receipt-window receipt))))
    (receipt . ,(receipt-id receipt))
    (digest . ,(receipt-digest receipt))
    (state . "draft")))
