;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; module/living/offers.scm — the evidence gate: match, or refuse honestly.
;;;
;;; WHAT THE FILE HOLDS. The core of the whole commons: an offer or intent
;;; is admitted only if its lane's gate carries an evidence SAID; sense and
;;; fleet are the only lanes that can carry one. The consent lanes —
;;; emit, cast, store — answer a different gate: the joint consent of the
;;; subject's guardian and the node operator, the same authority model
;;; every Playnet offer already runs on. The engineering lanes —
;;; hop, compute, engineered — refuse outright: no evidence, and consent
;;; is not evidence. No silent drops, no defaults that drift open.
;;;
;;; THE RETURN SHAPE. Every admit answers (admitted . payload); every
;;; refusal answers (refused . <refusal>) — a record naming lane, reason
;;; and detail, so a test or a door can say WHY, not just no. The reasons
;;; are a closed vocabulary: lane-refused, unknown-lane, evidence-required,
;;; consent-required, incomplete-declaration, subject-required,
;;; unknown-subject, revoked-subject.
;;;
;;; This is the module the minimum-disruption policy lives in as code:
;;; nothing emits without the two humans deciding it, nothing computes or
;;; relocates at all yet, and every refusal — whichever gate produced it —
;;; is structured so the caller can act on it.

(define-module (living offers)
  #:use-module (srfi srfi-1)
  #:use-module (srfi srfi-9)
  #:use-module (living specs)
  #:export (<refusal> refusal? refusal-lane refusal-reason refusal-detail
            admitted? refused?
            declare-lane lane-gate-of gate-evidence
            admit-intent admit-offer admit-reading
            offer-declared?))


;;; ── the refusal ─────────────────────────────────────────────────────────

(define-record-type <refusal>
  (%make-refusal lane reason detail)
  refusal?
  (lane   refusal-lane)     ; the lane asked for | #f
  (reason refusal-reason)   ; a symbol from the closed vocabulary
  (detail refusal-detail))  ; a string — the honest sentence

(define (admitted payload) (cons 'admitted payload))
(define (refused lane reason detail)
  (cons 'refused (%make-refusal lane reason detail)))

(define (admitted? x) (and (pair? x) (eq? 'admitted (car x))))
(define (refused? x)  (and (pair? x) (eq? 'refused (car x))))


;;; ── the gate book ───────────────────────────────────────────────────────
;;; An alist lane → <lane-gate>. Declaring a lane twice rewrites its gate —
;;; the newest evidence wins and the old SAID's expiry is the caller's
;;; business, not the book's.

(define (declare-lane book lane evidence-said)
  (assoc-set! book lane (make-lane-gate #:lane lane
                                        #:evidence-said evidence-said)))

(define (lane-gate-of book lane) (assoc-ref book lane))

(define (gate-evidence book lane)
  (let ((g (lane-gate-of book lane)))
    (and g (lane-gate-evidence-said g))))


;;; ── intents: the lane check, nothing else ───────────────────────────────
;;; An intent is (lane params) — it asks to ride a lane. The gate answers
;;; before params are even looked at: refused lanes refuse always, consent
;;; lanes demand the joint consent, admitted lanes demand evidence, and
;;; unknown lanes refuse as unknown. Only then does the intent pass.

(define (valid-consent? c)
  (and (list? c)
       (assq-ref c 'guardian)
       (assq-ref c 'operator)
       (assq-ref c 'said)
       #t))

(define (admit-intent book lane params)
  (cond
   ((not (lane-known? lane))
    (refused lane 'unknown-lane
             "the commons does not name this lane"))
   ((lane-refused? lane)
    (refused lane 'lane-refused
             "no evidence on file; hop/compute/engineered stay refused"))
   ((lane-consent-gated? lane)
    (let ((c (consent-of params))
          (cell (assq-ref params 'cell)))
      (cond
       ((not (valid-consent? c))
        (refused lane 'consent-required
                 "emit/cast/store ride the joint consent of guardian and node operator"))
       ((and (eq? lane 'store) cell (cell-decl? cell)
             (not (cell-decl-accepts-write cell)))
        (refused lane 'write-refused
                 "the cell declared it accepts no writes"))
       (else (admitted lane)))))
   ((not (gate-evidence book lane))
    (refused lane 'evidence-required
             "the lane's gate carries no evidence SAID"))
   (else (admitted lane))))


;;; ── offers: the declared-and-calibrated check ───────────────────────────
;;; A sense offer is declared when kind, cadence, duty-cycle and taxa-scope
;;; are all present — the offer's own constructor forces most of this, so
;;; the check that remains is the honest one: does the offer cite the same
;;; evidence SAID the lane's gate carries. Calibration is folded into that
;;; SAID: the reference-tone evidence is what makes the source calibrated.

(define (offer-declared? o)
  (and (sense-offer? o)
       (sense-offer-kind o)
       (sense-offer-cadence o)
       (sense-offer-duty-cycle o)
       (sense-offer-taxa-scope o)
       #t))

(define (admit-offer book offer)
  (cond
   ((not (sense-offer? offer))
    (refused 'sense 'incomplete-declaration
             "not a sense-offer record"))
   ((not (offer-declared? offer))
    (refused 'sense 'incomplete-declaration
             "kind, cadence, duty-cycle and taxa-scope must all be declared"))
   ((not (gate-evidence book 'sense))
    (refused 'sense 'evidence-required
             "the sense lane's gate carries no evidence SAID"))
   ((not (equal? (sense-offer-evidence-said offer)
                 (gate-evidence book 'sense)))
    (refused 'sense 'evidence-required
             "the offer must cite the evidence SAID the gate holds"))
   (else (admitted offer))))


;;; ── readings: the subject boundary ──────────────────────────────────────
;;; A reading enters only against a registered, consenting subject. AGENTS
;;; is an alist subject-id → <ecological-agent>. The checks, in order:
;;; the reading names a subject, the subject is registered, the subject is
;;; not revoked, guardian consent is on file. Only then is it admitted.

(define (admit-reading agents r)
  (cond
   ((not (reading? r))
    (refused 'sense 'incomplete-declaration "not a reading record"))
   ((not (reading-subject r))
    (refused 'sense 'subject-required
             "a reading must name its ecological subject"))
   ((not (assoc-ref agents (reading-subject r)))
    (refused 'sense 'unknown-subject
             "no registered subject by that name"))
   (else
    (let ((agent (assoc-ref agents (reading-subject r))))
      (if (ecological-agent-consent agent)
          (admitted r)
          (refused 'sense 'consent-required
                   "the subject's guardian has granted no consent credential"))))))
