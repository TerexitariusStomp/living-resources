;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; module/living/sense-subject.scm — one sense node per subject.
;;;
;;; WHAT THE FILE HOLDS. The ^sense-node actor: the per-subject intake that
;;; accepts readings and emits fleet-legs for the quorum merge. A node is
;;; small on purpose — it checks that a reading names its subject and that
;;; the reading is evidence-shaped (mic-cal present, a timestamp, a named
;;; channel), then stamps the leg and keeps it. The quorum itself is not
;;; here: attest.scm counts legs and decides when a window is witnessed.
;;;
;;; A REFUSED READING IS ANSWERED, NOT DROPPED. ingest returns the leg on
;;; accept; on refuse it raises with a reason, the same posture the lane
;;; gate takes — silence is how bad data gets in.

(define-module (living sense-subject)
  #:use-module (srfi srfi-1)
  #:use-module (srfi srfi-9)
  #:use-module (living specs)
  #:export (^sense-node sense-node-env
            reading-evidence-shaped?))


;;; a reading is evidence-shaped when it names a channel, carries an
;;; edge-synced timestamp, and its mic-cal SAID is present — the calibration
;;; record is what lets a buyer trust the channel. gain rides the record
;;; regardless; it is declared, not gated.
(define (reading-evidence-shaped? r)
  (and (reading? r)
       (reading-channel r)
       (number? (reading-timestamp r))
       (reading-mic-cal r)
       #t))


(define-actor (^sense-node bcom subject-id offer-id readings legs
                           quorum-size quorum-nodes)
  #:portrait
  (lambda () (list subject-id offer-id readings legs
                   quorum-size quorum-nodes))
  #:version 1
  #:restore
  (lambda (version data)
    (case version
      ((1) (spawn ^sense-node (list-ref data 0) (list-ref data 1)
                  (list-ref data 2) (list-ref data 3)
                  (list-ref data 4) (list-ref data 5)))
      (else (error "Unknown ^sense-node version" version))))

  (methods

    ((subject) subject-id)

    ((offer) offer-id)

    ((readings) readings)

    ((legs) legs)

    ((pending-count) (length readings))

    ;; ingest — a reading becomes a leg when it names THIS subject and is
    ;; evidence-shaped. The leg is both the ledger of what the node heard
    ;; and the unit the quorum counts.
    ((ingest r)
     (cond
      ((not (reading? r))
       (error "sense-node: not a reading" r))
      ((not (equal? subject-id (reading-subject r)))
       (error "sense-node: reading names another subject"
              (reading-subject r)))
      ((not (reading-evidence-shaped? r))
       (error "sense-node: reading is not evidence-shaped — channel, timestamp and mic-cal are required"))
      (else
       (let ((leg (make-fleet-leg #:node-id (reading-channel r)
                                  #:subject subject-id
                                  #:reading r
                                  #:at (reading-timestamp r))))
         (bcom (^sense-node bcom subject-id offer-id
                            (append readings (list r))
                            (append legs (list leg))
                            quorum-size quorum-nodes)
               leg)))))

    ;; quorum? asks the legs, not the readings — a node may hold readings
    ;; still travelling to the fleet; the legs already emitted are what a
    ;; merge can count. The test is here (not in attest) so a caller can
    ;; ask the node itself.
    ((quorum?)
     (let ((nodes (delete-duplicates (map fleet-leg-node-id legs))))
       (and (>= (length legs) quorum-size)
            (>= (length nodes) quorum-nodes))))

    ((quorum-params) (list quorum-size quorum-nodes))))

(define sense-node-env
  (make-persistence-env
    `((((living sense-subject) ^sense-node) ,^sense-node))))
