;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; module/living/agents.scm — the ecological subject as an agent.
;;;
;;; WHAT THE FILE HOLDS. One ^eco-agent actor per registered subject: the
;;; record of who it is, who guards it, what consent is on file, and the
;;; custody boundary around all of it. The actor is the custody boundary
;;; made executable — the subject itself has voice 0 and cannot move its own
;;; state; every mutation arrives carrying a guardian signature, and the
;;; actor checks the guardian before it checks anything else.
;;;
;;; THE SIGNATURE SEAM. *guardian-verify* is the one place cryptography
;;; lives, and it is a parameter on purpose: the real stack binds it to
;;; verify-said-signature over the guardian's KERI AID; this skeleton ships
;;; a transparent placeholder — (guardian-sig AID PAYLOAD) — so tests can
;;; sign without a key store and anyone reading the code can see exactly
;;; what is checked: that the named guardian signed this payload.

(define-module (living agents)
  #:use-module (srfi srfi-1)
  #:use-module (srfi srfi-9)
  #:use-module (living specs)
  #:export (^eco-agent eco-agent-env
            *guardian-verify* guardian-sig))


;;; ── the signature seam ──────────────────────────────────────────────────
;;; A signature is valid when it is the tuple (guardian-sig AID PAYLOAD) —
;;; the placeholder shape. Swapping in verify-said-signature changes what a
;;; signature IS, never where it is checked: every mutating method passes
;;; GUARDIAN-AID, SIGNATURE and the payload it covers through this one gate.

(define (guardian-sig aid payload)
  "The placeholder signature a test produces: (guardian-sig AID PAYLOAD)."
  (list 'guardian-sig aid payload))

(define *guardian-verify*
  (make-parameter
   (lambda (aid signature payload)
     (equal? signature (guardian-sig aid payload)))))

(define (guardian-verified? agent signature payload)
  ((*guardian-verify*) (ecological-agent-guardian-aid agent)
                       signature payload))


;;; ── the actor ───────────────────────────────────────────────────────────
;;; State is the agent record plus a revoked? flag — a revoked subject keeps
;;; its history but accepts nothing new, consent included.

(define-actor (^eco-agent bcom agent revoked?)
  #:portrait
  (lambda () (list (ecological-agent->list agent) revoked?))
  #:version 1
  #:restore
  (lambda (version data)
    (case version
      ((1) (spawn ^eco-agent (list->ecological-agent (car data)) (cadr data)))
      (else (error "Unknown ^eco-agent version" version))))

  (methods

    ((who) agent)

    ;; the voice rule, stated as code: the subject never votes, never
    ;; amends, never consents — this method exists so a caller reading the
    ;; agent sees 0 rather than asking why there is no ballot door.
    ((voice) (ecological-agent-voice agent))

    ((consented?) (and (not revoked?)
                       (ecological-agent-consent agent)
                       #t))

    ((consent-said) (ecological-agent-consent agent))

    ;; PAYLOAD for the signature is the consent SAID itself: the guardian
    ;; signs the credential's name, binding this agent to that consent.
    ((grant-consent guardian-aid signature consent-said)
     (cond
      (revoked? (error "eco-agent: revoked subjects take no new consent"))
      ((not (equal? guardian-aid (ecological-agent-guardian-aid agent)))
       (error "eco-agent: only the guardian grants consent"))
      ((not (guardian-verified? agent signature consent-said))
       (error "eco-agent: bad guardian signature"))
      (else
       (bcom (^eco-agent bcom
                         (make-ecological-agent
                          #:id (ecological-agent-id agent)
                          #:guardian-aid guardian-aid
                          #:taxa-scope (ecological-agent-taxa-scope agent)
                          #:consent consent-said
                          #:custody (ecological-agent-custody agent))
                         revoked?)
             consent-said))))

    ((revoke-consent guardian-aid signature)
     (cond
      ((not (equal? guardian-aid (ecological-agent-guardian-aid agent)))
       (error "eco-agent: only the guardian revokes consent"))
      ((not (guardian-verified? agent signature 'revoke-consent))
       (error "eco-agent: bad guardian signature"))
      (else
       (bcom (^eco-agent bcom
                         (make-ecological-agent
                          #:id (ecological-agent-id agent)
                          #:guardian-aid guardian-aid
                          #:taxa-scope (ecological-agent-taxa-scope agent)
                          #:consent #f
                          #:custody (ecological-agent-custody agent))
                         #t)))))

    ;; amend — the subject cannot self-modify; only the guardian, only the
    ;; declared fields, and voice is not among them. FIELDS is an alist
    ;; with keys in {taxa-scope, custody}; 'voice or 'guardian-aid or
    ;; 'consent in FIELDS refuses — those move through their own methods.
    ((amend guardian-aid signature fields)
     (let ((guardians-only '(voice guardian-aid consent id)))
       (cond
        (revoked? (error "eco-agent: revoked subjects are immutable"))
        ((not (equal? guardian-aid (ecological-agent-guardian-aid agent)))
         (error "eco-agent: only the guardian amends"))
        ((any (lambda (f) (memq (car f) guardians-only)) fields)
         (error "eco-agent: fields refuse guardian-only keys" fields))
        ((not (guardian-verified? agent signature fields))
         (error "eco-agent: bad guardian signature"))
        (else
         (let ((taxa (or (assq-ref fields 'taxa-scope)
                         (ecological-agent-taxa-scope agent)))
               (custody (or (assq-ref fields 'custody)
                            (ecological-agent-custody agent))))
           (bcom (^eco-agent bcom
                             (make-ecological-agent
                              #:id (ecological-agent-id agent)
                              #:guardian-aid guardian-aid
                              #:taxa-scope taxa
                              #:consent (ecological-agent-consent agent)
                              #:custody custody)
                             revoked?)))))))

    ;; transfer — custody moves whole: new guardian, new custodial account,
    ;; consent cleared (the new guardian re-grants; consent is never
    ;; inherited). The signature payload is the transfer pair.
    ((transfer guardian-aid signature new-guardian-aid new-custody)
     (let ((payload (list 'transfer new-guardian-aid new-custody)))
       (cond
        (revoked? (error "eco-agent: revoked subjects do not transfer"))
        ((not (equal? guardian-aid (ecological-agent-guardian-aid agent)))
         (error "eco-agent: only the sitting guardian transfers custody"))
        ((not (guardian-verified? agent signature payload))
         (error "eco-agent: bad guardian signature"))
        (else
         (bcom (^eco-agent bcom
                           (make-ecological-agent
                            #:id (ecological-agent-id agent)
                            #:guardian-aid new-guardian-aid
                            #:taxa-scope (ecological-agent-taxa-scope agent)
                            #:consent #f
                            #:custody new-custody)
                           revoked?))))))))

(define eco-agent-env
  (make-persistence-env
    `((((living agents) ^eco-agent) ,^eco-agent))))
