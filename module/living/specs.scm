;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; module/living/specs.scm — the living commons vocabulary.
;;;
;;; WHAT THE FILE HOLDS. The record and sum types every other living module
;;; speaks: the ecological subject (an agent with a human guardian and voice
;;; 0), the sense offer a cell declares, the cell declaration a field node
;;; carries, the reading a detection becomes, the witnessed receipt a fleet
;;; quorum produces, and the lane gate that decides whether a lane may be
;;; offered at all. Plus the lane vocabulary itself: sense/fleet are the only
;;; lanes this commons admits; emit, cast, hop, compute, store and engineered
;;; are named here so the refusal in offers.scm can name them back.
;;;
;;; THE LAST SECTION IS PLUMBING, NOT VOCABULARY. When (goblins) resolves the
;;; real machinery is re-exported through this module and the ^actors in
;;; agents.scm / sense-subject.scm are genuine persisted Goblins actors.
;;; Where it does not — a bare Guile, a CI box — a small shim answers the
;;; same call shape (spawn / $ / bcom on a synchronous cell) so the
;;; pure-logic suites still run end to end. Persistence portraits are the
;;; real stack's concern; the shim ignores them on purpose.

(define-module (living specs)
  #:use-module (srfi srfi-1)
  #:use-module (srfi srfi-9)
  #:export (;; lanes
            *living-lanes* *admitted-lanes* *consent-lanes* *refused-lanes*
            *transport-lanes*
            lane-known? lane-refused? lane-consent-gated? lane-transport?
            consent-of sense-kind? taxa-scope?
            ;; ids and quorum parameters
            generate-id *default-quorum-size* *default-quorum-nodes*
            ;; the subject
            <ecological-agent> make-ecological-agent ecological-agent?
            ecological-agent-id ecological-agent-guardian-aid
            ecological-agent-voice ecological-agent-taxa-scope
            ecological-agent-consent ecological-agent-custody
            ecological-agent->list list->ecological-agent
            ;; the offer and the cell
            <sense-offer> make-sense-offer sense-offer?
            sense-offer-id sense-offer-subject sense-offer-kind
            sense-offer-cadence sense-offer-duty-cycle
            sense-offer-taxa-scope sense-offer-evidence-said
            <cell-decl> make-cell-decl cell-decl?
            cell-decl-node-id cell-decl-heads cell-decl-link-type
            cell-decl-location-class cell-decl-accepts-write
            ;; the reading, the leg, the receipt
            <reading> make-reading reading?
            reading-subject reading-channel reading-timestamp
            reading-payload reading-mic-cal reading-gain
            <fleet-leg> make-fleet-leg fleet-leg?
            fleet-leg-id fleet-leg-node-id fleet-leg-subject
            fleet-leg-reading fleet-leg-at
            <witnessed-receipt> make-witnessed-receipt witnessed-receipt?
            receipt-id receipt-subject receipt-witnessed
            receipt-audio-said receipt-detection-said
            receipt-window receipt-quantity receipt-digest
            receipt-connectome-said
            ;; the gate
            <lane-gate> make-lane-gate lane-gate?
            lane-gate-lane lane-gate-evidence-said
            ;; plumbing flag — #t when real goblins backs the actors
            living-goblins?))


;;; ── the lane vocabulary ─────────────────────────────────────────────────
;;; Nine names, deliberately small, in four classes. sense and fleet are
;;; the commons' admitted lanes: passive listening and the quorum merge
;;; over it. emit, cast and store are CONSENT lanes — a guardian + node
;;; operator decide to ride them (bio-write, downlink tasking, node-SD
;;; storage); they refuse without both approvals, never on absent evidence.
;;; hop, compute and engineered stay refused outright — no evidence on file,
;;; and no consent can substitute for it. relay is the TRANSPORT lane:
;;; node→node forwarding of already content-addressed bundles — an offer
;;; may ride it only naming the packet SAID it carries; it moves receipts,
;;; it never touches an organism. A lane not in this list is unknown; a
;;; refusal always names why.

(define *living-lanes*
  '(sense fleet emit cast hop compute store engineered relay))

(define *admitted-lanes* '(sense fleet))

(define *consent-lanes* '(emit cast store))

(define *refused-lanes* '(hop compute engineered))

(define *transport-lanes* '(relay))

(define (lane-known? x)         (and (memq x *living-lanes*) #t))
(define (lane-refused? x)       (and (memq x *refused-lanes*) #t))
(define (lane-consent-gated? x) (and (memq x *consent-lanes*) #t))
(define (lane-transport? x)     (and (memq x *transport-lanes*) #t))

;;; A consent is an alist — ((guardian . aid) (operator . aid) (said . s))
;;; — naming the two humans whose joint approval unlocks a consent lane and
;;; the SAID of the consent credential they signed. admit-intent checks all
;;; three fields are present; whether the signature verifies is the same
;;; *guardian-verify* seam every guardian act already passes through.

(define (consent-of params) (assq-ref params 'consent))

;;; sense kinds: what a passive head can honestly read. doppler-motion is
;;; E1-gated (speaker sonar is an emitting lane's read side — it stays
;;; declared-not-admitted until the evidence lands); ultrasonic-click and
;;; c4d-readout wait on heads, not on policy.
(define *sense-kinds*
  '(bioacoustic rustle-spectra rain-spectra reef-health
    photo-phenology env-context
    doppler-motion ultrasonic-click c4d-readout))

(define (sense-kind? x) (and (memq x *sense-kinds*) #t))

;;; taxa-scope declares what a subject honestly covers — a mic hears the
;;; vocal slice, never the whole assemblage. Declared per SAGED: buyers of
;;; the data read this before they trust a receipt.
(define *taxa-scopes*
  '(vocal ultrasonic assemblage plant reef biofilm))

(define (taxa-scope? x) (and (memq x *taxa-scopes*) #t))


;;; ── ids and quorum parameters ───────────────────────────────────────────

(define %id-counter 0)

(define (generate-id prefix)
  (set! %id-counter (+ 1 %id-counter))
  (let ((now (gettimeofday)))
    (string-append prefix
                   (number->string (+ (* (car now) 1000000) (cdr now)) 36)
                   "-" (number->string %id-counter 36))))

;;; a witnessed receipt needs enough legs and enough distinct channels that
;;; no single node — honest or otherwise — can witness itself.
(define *default-quorum-size* 3)
(define *default-quorum-nodes* 2)


;;; ── the subject ─────────────────────────────────────────────────────────
;;; A species, assemblage, plant or culture that the commons senses and
;;; credits. It is an agent — it holds custody, it earns credit — but it
;;; never speaks: voice is 0 by construction, not by default. The guardian
;;; is the human AID who signs for it; consent is the SAID of the guardian's
;;; consent credential; custody is the custodial account the guardian holds
;;; for the subject, where its credit lands.

(define-record-type <ecological-agent>
  (%make-ecological-agent id guardian-aid voice taxa-scope consent custody)
  ecological-agent?
  (id           ecological-agent-id)
  (guardian-aid ecological-agent-guardian-aid)
  (voice        ecological-agent-voice)
  (taxa-scope   ecological-agent-taxa-scope)
  (consent      ecological-agent-consent)
  (custody      ecological-agent-custody))

(define* (make-ecological-agent #:key id guardian-aid taxa-scope
                                (consent #f) custody)
  (unless (and (string? id) (positive? (string-length id)))
    (error "eco-agent: id must be a non-empty string" id))
  (unless (string? guardian-aid)
    (error "eco-agent: a guardian AID is required — voiceless, not orphaned"))
  (unless (taxa-scope? taxa-scope)
    (error "eco-agent: not a taxa scope" taxa-scope))
  (unless (or (not consent) (string? consent))
    (error "eco-agent: consent is a SAID or #f" consent))
  (%make-ecological-agent id guardian-aid 0 taxa-scope consent custody))

(define (ecological-agent->list a)
  (list (ecological-agent-id a) (ecological-agent-guardian-aid a)
        (ecological-agent-voice a) (symbol->string (ecological-agent-taxa-scope a))
        (ecological-agent-consent a) (ecological-agent-custody a)))

(define (list->ecological-agent l)
  (make-ecological-agent
   #:id (list-ref l 0) #:guardian-aid (list-ref l 1)
   #:taxa-scope (string->symbol (list-ref l 3))
   #:consent (list-ref l 4) #:custody (list-ref l 5)))


;;; ── the offer ───────────────────────────────────────────────────────────
;;; What a cell declares it can sense on a subject's behalf. cadence is
;;; seconds between reading windows; duty-cycle is the fraction of time the
;;; node is awake listening (declared, never implied — the power budget is
;;; part of the evidence); evidence-said is the SAID of the calibration and
;;; validation evidence that lets this offer exist at all.

(define-record-type <sense-offer>
  (%make-sense-offer id subject kind cadence duty-cycle taxa-scope
                     evidence-said)
  sense-offer?
  (id            sense-offer-id)
  (subject       sense-offer-subject)       ; ecological-agent id
  (kind          sense-offer-kind)          ; one of *sense-kinds*
  (cadence       sense-offer-cadence)       ; seconds between windows
  (duty-cycle    sense-offer-duty-cycle)    ; fraction awake, 0 < d <= 1
  (taxa-scope    sense-offer-taxa-scope)
  (evidence-said sense-offer-evidence-said)) ; string | #f — the gate reads this

(define* (make-sense-offer #:key id subject kind cadence duty-cycle
                           taxa-scope (evidence-said #f))
  (unless (sense-kind? kind)
    (error "sense-offer: not a sense kind" kind))
  (unless (and (number? cadence) (positive? cadence))
    (error "sense-offer: cadence must be positive seconds" cadence))
  (unless (and (number? duty-cycle) (< 0 duty-cycle 1.0000001))
    (error "sense-offer: duty-cycle is a fraction in (0,1]" duty-cycle))
  (unless (taxa-scope? taxa-scope)
    (error "sense-offer: not a taxa scope" taxa-scope))
  (%make-sense-offer id subject kind cadence duty-cycle taxa-scope
                     evidence-said))


;;; ── the cell ────────────────────────────────────────────────────────────
;;; A field node's declaration: its id, its head set, its link tier, and
;;; its location class. The hardware spec is universal — every node ships
;;; every head's electronics, so heads declares what is deployed-facing,
;;; never what the board lacks. The canonical full list is 'cam 'mic 'env
;;; 'hydro 'ultra 'c4d 'emit; 'emit is populated live and consent-gated,
;;; a policy flag — never a purchase and never a missing part.

(define-record-type <cell-decl>
  (%make-cell-decl node-id heads link-type location-class accepts-write)
  cell-decl?
  (node-id        cell-decl-node-id)
  (heads          cell-decl-heads)          ; list of head symbols
  (link-type      cell-decl-link-type)      ; 'wifi 'lora 'lte-m 'satellite 'serial
  (location-class cell-decl-location-class) ; 'garden 'shore-dock 'reef-float …
  (accepts-write  cell-decl-accepts-write)) ; #t: node processes task/store intents

(define *link-types* '(wifi lora lte-m satellite serial mesh))

(define* (make-cell-decl #:key node-id heads link-type location-class
                         (accepts-write #t))
  (unless (memq link-type *link-types*)
    (error "cell-decl: not a link type" link-type))
  (%make-cell-decl node-id heads link-type location-class accepts-write))


;;; ── the reading ─────────────────────────────────────────────────────────
;;; One detection as it crosses into the commons: the subject it is about,
;;; the channel (node-id) that heard it, an edge-synced timestamp, the
;;; detection payload itself (species, confidence, band…), the mic-cal SAID
;;; of the node's reference-tone calibration, and the gain the channel ran
;;; at. mic-cal and gain are the MRV requirement end-to-end — a reading
;;; without them is a rumour, not evidence.

(define-record-type <reading>
  (%make-reading subject channel timestamp payload mic-cal gain)
  reading?
  (subject    reading-subject)      ; ecological-agent id | #f
  (channel    reading-channel)      ; node-id that heard it
  (timestamp  reading-timestamp)    ; epoch ms, edge-synced
  (payload    reading-payload)      ; alist — species, confidence, band, …
  (mic-cal    reading-mic-cal)      ; SAID of the calibration tone | #f
  (gain       reading-gain))        ; dB the channel ran at

(define* (make-reading #:key subject channel timestamp payload
                       (mic-cal #f) (gain 0))
  (%make-reading subject channel timestamp payload mic-cal gain))


;;; ── the fleet leg ───────────────────────────────────────────────────────
;;; A sense node's contribution to a fleet merge: one reading, stamped with
;;; the node that stands behind it. Legs are what quorum counts — a fleet
;;; is a quorum of legs, nothing more.

(define-record-type <fleet-leg>
  (%make-fleet-leg id node-id subject reading at)
  fleet-leg?
  (id       fleet-leg-id)
  (node-id  fleet-leg-node-id)
  (subject  fleet-leg-subject)
  (reading  fleet-leg-reading)
  (at       fleet-leg-at))

(define* (make-fleet-leg #:key id node-id subject reading at)
  (%make-fleet-leg (or id (generate-id "leg-"))
                   node-id subject reading at))


;;; ── the witnessed receipt ───────────────────────────────────────────────
;;; A quorum's product: which subject, which nodes witnessed, the two SAIDs
;;; that are its evidence — the lossless audio in the content store and the
;;; detection in the ledger — the window it covers, the contribution count,
;;; and the digest that binds all of it. witnessed is a list of node-ids;
;;; the quorum that produced them is attest.scm's decision, this record
;;; just carries the result.

(define-record-type <witnessed-receipt>
  (%make-witnessed-receipt id subject witnessed audio-said detection-said
                           window quantity digest connectome-said)
  witnessed-receipt?
  (id             receipt-id)
  (subject        receipt-subject)
  (witnessed      receipt-witnessed)      ; list of node-ids
  (audio-said     receipt-audio-said)     ; SAID of the lossless audio | #f
  (detection-said receipt-detection-said) ; SAID of the detection record | #f
  (window         receipt-window)         ; (start-ms . end-ms)
  (quantity       receipt-quantity)       ; readings the receipt attests
  (digest         receipt-digest)         ; string | #f
  (connectome-said receipt-connectome-said)) ; connectome verdict digest | #f

(define* (make-witnessed-receipt #:key id subject witnessed audio-said
                                 detection-said window quantity
                                 (digest #f) (connectome-said #f))
  (%make-witnessed-receipt id subject witnessed audio-said detection-said
                           window quantity digest connectome-said))


;;; ── the lane gate ───────────────────────────────────────────────────────
;;; The atomic unit of the evidence gate: a lane and the evidence SAID that
;;; unlocks it, or #f. A gate with #f is not a missing record — it is the
;;; commons saying no evidence exists, and no offer may pass. offers.scm
;;; reads gates; this record just names the pair.

(define-record-type <lane-gate>
  (%make-lane-gate lane evidence-said)
  lane-gate?
  (lane          lane-gate-lane)
  (evidence-said lane-gate-evidence-said))  ; string | #f

(define* (make-lane-gate #:key lane (evidence-said #f))
  (unless (lane-known? lane)
    (error "lane-gate: not a lane" lane))
  (%make-lane-gate lane evidence-said))


;;; ── actor plumbing ──────────────────────────────────────────────────────
;;; Real Goblins, when it is on the load path: re-exported through this
;;; module so agents.scm and sense-subject.scm write plain define-actor and
;;; get persisted actors. The shim, when it is not: spawn/$/bcom over a
;;; synchronous variable cell, enough of the same shape that the e2e suites
;;; exercise every act. The shim knows nothing about vats, sturdyrefs or
;;; portraits — those are the real stack's.

(define %goblins-modules
  '((goblins) (goblins vat) (goblins actor-lib methods)))

(define %goblins-ifaces
  (filter-map (lambda (m) (false-if-exception (resolve-interface m)))
              %goblins-modules))

(define living-goblins?
  (= (length %goblins-ifaces) (length %goblins-modules)))

(cond
 (living-goblins?
  (for-each (lambda (iface)
              (module-use! (module-public-interface (current-module)) iface))
            %goblins-ifaces))
 (else
  ;; the shim is installed by eval so define-syntax lands as a module-level
  ;; macro: a define-syntax inside this cond's clause would bind locally
  ;; and importers would see nothing.
  (eval
   '(begin
     (define %bcom-tag (list 'bcom))

     (define (%bcom-for cell)
       (lambda (next . vals) (list %bcom-tag next vals)))

     ;; (spawn ^actor . init-args) — the constructor's first formal is
     ;; bcom; goblins supplies it, the shim supplies a cell-bound version.
     (define (spawn ctor . args)
       (let ((cell (make-variable #f)))
         (variable-set! cell (apply ctor (%bcom-for cell) args))
         cell))

     ;; ($ ref msg . args) — dispatch to the current behaviour; a method
     ;; answering a bcom package commits the new behaviour, returns values.
     (define ($ cell msg . args)
       (let ((result (apply (variable-ref cell) msg args)))
         (if (and (pair? result) (eq? (car result) %bcom-tag))
             (begin (variable-set! cell (cadr result))
                    (apply values (caddr result)))
             result)))

     (define (spawn-vat . _ignored) 'shim-vat)

     ;; define-actor keeps the goblins surface shape — #:portrait,
     ;; #:version, #:restore are matched and ignored; the method table
     ;; alone becomes the synchronous dispatcher.
     (define-syntax define-actor
       (syntax-rules (methods)
         ((_ (name bcom sarg ...) _opt ...
             (methods ((mname margs ...) mbody ...) ...))
          (define (name bcom sarg ...)
            (lambda (msg . args)
              (case msg
                ((mname) (apply (lambda (margs ...) mbody ...) args)) ...
                (else (error "actor: no such method" msg))))))))

     (define-syntax-rule (with-vat _vat body ...) (let () body ...))

     (define (make-persistence-env spec) spec))
   (current-module))
  (module-export! (current-module)
                  '(spawn $ spawn-vat with-vat define-actor
                    make-persistence-env))))
