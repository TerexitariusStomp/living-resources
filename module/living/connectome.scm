;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; module/living/connectome.scm — biological wiring as a witness class.
;;;
;;; WHAT THE FILE HOLDS. A packed connectome (real EM-derived synaptic
;;; wiring, packed CSR + LIF inference — tools/connectome/lif.py, the
;;; FlyEngine semantics) answers an encoded observation with a verdict:
;;; action, confidence, spike digest. That verdict is a *witness
;;; signature* — deterministic, replayable, bound to a distinct wiring
;;; diagram — not a detection and not a claim about the organism. This
;;; module carries the record, stamps verdicts as legs, and folds a
;;; quorum of verdicts into one evidence digest a receipt may bind.
;;;
;;; WHERE IT SITS. Connectome evidence is ADDITIVE: a witnessed receipt
;;; still requires its audio and detection SAIDs; the connectome digest
;;; rides alongside as a third, optional leg. The evidence gate in
;;; offers.scm is untouched — sense/fleet remain the only evidence-
;;; bearing lanes, and no connectome verdict can manufacture a detection
;;; that nodes did not witness.

(define-module (living connectome)
  #:use-module (srfi srfi-1)
  #:use-module (srfi srfi-9)
  #:use-module (living specs)
  #:export (<connectome-verdict> make-connectome-verdict
            connectome-verdict? connectome-verdict-id
            connectome-verdict-connectome connectome-verdict-input-said
            connectome-verdict-action connectome-verdict-confidence
            connectome-verdict-spike-count connectome-verdict-spike-digest
            connectome-verdict-steps connectome-verdict-encoder
            verdict->leg distinct-connectomes connectome-quorum?
            verdicts-digest *connectome-quorum-size*
            ;; the compute task — replay as proof
            <connectome-task> make-connectome-task connectome-task?
            connectome-task-id connectome-task-connectome
            connectome-task-input-said connectome-task-trace-digest
            connectome-task-steps connectome-task-encoder
            replays-agree? task-evidence-digest))


;;; ── the verdict ─────────────────────────────────────────────────────────
;;; One packed wiring diagram's response signature to one encoded reading.
;;; input-said commits to the encoded features; spike-digest commits to the
;;; raster + membrane state the simulation produced; encoder names the
;;; rasterizer version so a replay knows exactly what to recompute.

(define-record-type <connectome-verdict>
  (%make-connectome-verdict id connectome input-said action confidence
                            spike-count spike-digest steps encoder)
  connectome-verdict?
  (id           connectome-verdict-id)
  (connectome   connectome-verdict-connectome)   ; e.g. 'celegans
  (input-said   connectome-verdict-input-said)   ; digest of features | #f
  (action       connectome-verdict-action)       ; -1 | 0 | +1
  (confidence   connectome-verdict-confidence)   ; 50..100
  (spike-count  connectome-verdict-spike-count)  ; total fires over steps
  (spike-digest connectome-verdict-spike-digest) ; raster+v digest | #f
  (steps        connectome-verdict-steps)        ; LIF steps run
  (encoder      connectome-verdict-encoder))     ; rasterizer version

(define* (make-connectome-verdict #:key id connectome input-said action
                                  confidence spike-count spike-digest
                                  steps encoder)
  (unless (symbol? connectome)
    (error "connectome-verdict: connectome must be a symbol" connectome))
  (unless (memv action '(-1 0 1))
    (error "connectome-verdict: action must be -1, 0 or +1" action))
  (unless (and (integer? confidence) (<= 0 confidence 100))
    (error "connectome-verdict: confidence is 0..100" confidence))
  (%make-connectome-verdict id connectome input-said action confidence
                            spike-count spike-digest steps encoder))


;;; ── verdicts as legs ────────────────────────────────────────────────────
;;; A verdict becomes a leg stamped with channel "connectome:<name>" —
;;; distinct-nodes then counts each wiring diagram as its own channel, so
;;; a connectome can never pose as a second copy of itself. The leg's
;;; reading is the reading being witnessed: connectomes sign the
;;; observation, they do not originate it.

(define (verdict->leg verdict subject reading)
  "VERDICT witnessing READING on SUBJECT → a fleet leg on channel
   connectome:<connectome>."
  (make-fleet-leg
   #:node-id (string->symbol
              (string-append "connectome:"
                             (symbol->string
                              (connectome-verdict-connectome verdict))))
   #:subject subject
   #:reading reading
   #:at (reading-timestamp reading)))


;;; ── the connectome quorum ───────────────────────────────────────────────
;;; One wiring diagram may not witness alone: quorum is *n* verdicts across
;;; *n* DISTINCT connectomes — the witness set is diverse topology or it is
;;; not a quorum. Mirrors the fleet rule (legs × distinct channels).

(define *connectome-quorum-size* 3)

(define (distinct-connectomes verdicts)
  (delete-duplicates (map connectome-verdict-connectome verdicts)))

(define* (connectome-quorum? verdicts #:key (size *connectome-quorum-size*))
  (and (>= (length verdicts) size)
       (>= (length (distinct-connectomes verdicts)) size)))


;;; ── the evidence digest ─────────────────────────────────────────────────
;;; One digest binds the whole witness set: connectome ids, actions and
;;; spike digests in canonical order. Same gcrypt seam as attest.scm —
;;; sha256 when it resolves, a clearly-marked string-hash fallback where
;;; it does not, so a fallback digest can never be mistaken for a real one.

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

(define (verdicts-digest verdicts)
  "Fold VERDICTS into one evidence digest, or #f on an empty set —
   nothing witnessed is nothing to bind."
  (and (pair? verdicts)
       (%digest-fields 'living-connectome/v1
                       (sort (map (lambda (v)
                                    (list (connectome-verdict-connectome v)
                                          (connectome-verdict-action v)
                                          (connectome-verdict-input-said v)
                                          (connectome-verdict-spike-digest v)))
                                  verdicts)
                             (lambda (a b)
                               (string<? (symbol->string (car a))
                                         (symbol->string (car b))))))))


;;; ── the compute task — replay as proof ─────────────────────────────────
;;; A connectome compute task is honest about its shape: an input committed
;;; by input-said, a transform committed by trace-digest, and the wiring
;;; that ran it named outright. The proof property is REPLAY: independent
;;; verifiers recompute input→trace; identical digests mean the compute
;;; demonstrably happened on that topology — no redundancy machinery, no
;;; trusted execution. replays-agree? is the quorum of that: every replay
;;; must land the same trace or the evidence bundle does not exist.
;;;
;;; What this is NOT: storage (LIF state fades — trace digests are
;;; commitments, not persistence), throughput (topology not speed), or the
;;; living organism computing (preserved wiring, simulated dynamics).
;;; The refused `compute` lane — living systems computing — is untouched;
;;; a task's replay bundle is the evidence material that could one day
;;; graduate a connectome-compute lane of its own.

(define-record-type <connectome-task>
  (%make-connectome-task id connectome input-said trace-digest
                         steps encoder)
  connectome-task?
  (id           connectome-task-id)
  (connectome   connectome-task-connectome)    ; which wiring ran it
  (input-said   connectome-task-input-said)    ; digest of the input
  (trace-digest connectome-task-trace-digest)  ; digest of raster+v tail
  (steps        connectome-task-steps)
  (encoder      connectome-task-encoder))      ; e.g. lif-task-v1

(define* (make-connectome-task #:key id connectome input-said
                               trace-digest steps encoder)
  (unless (symbol? connectome)
    (error "connectome-task: connectome must be a symbol" connectome))
  (unless (and input-said trace-digest)
    (error "connectome-task: input-said and trace-digest are required"))
  (%make-connectome-task id connectome input-said trace-digest
                         steps encoder))

(define (replays-agree? digests)
  "DIGESTS is the list of trace digests independent replays produced.
   #t iff there is at least one replay and every digest is identical —
   agreement is unanimity, not majority: the same computation is
   deterministic or the bundle is invalid."
  (and (pair? digests)
       (every (lambda (d) (equal? d (car digests))) digests)))

(define (task-evidence-digest task replays)
  "TASK + its agreeing REPLAY digests → one evidence digest | #f.
   The replays must unanimously reproduce the task's claimed
   trace-digest — replays that agree with each other but not with the
   claim prove a different computation, so they mint nothing."
  (and (replays-agree? replays)
       (equal? (connectome-task-trace-digest task) (car replays))
       (%digest-fields 'living-task/v1
                       (connectome-task-connectome task)
                       (connectome-task-input-said task)
                       (connectome-task-trace-digest task)
                       replays)))
