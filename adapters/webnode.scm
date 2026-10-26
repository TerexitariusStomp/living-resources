;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/webnode.scm — a visitor's browser as a living-cloud node.
;;;
;;; Every visitor's device is already a sensor node: mic, camera, light,
;;; accelerometer — and a weak actuator: speaker, screen, vibration. The
;;; browser's permission prompt IS the operator consent — per-session,
;;; revocable, platform-enforced. Reads import as federated records with
;;; source 'web-visitor and an honest uncalibrated flag; writes ride the
;;; normal emit gate (guardian + operator), the browser supplying only
;;; the operator half.
;;;
;;; Minimum-disruption by architecture: classification happens on-device
;;; (TFJS/wasm — YAMNet/BirdNET-lite class); what leaves is the detection
;;; receipt, never raw media. *webnode-import* is the seam the site's
;;; WebNode component posts to; unbound → 'no-source.

(define-module (adapters webnode)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*webnode-import* webnode-record webnode-write-kinds
            browser-session->cell))

;;; (proc record) → receipt | #f — bound at deployment to the worker POST.
(define *webnode-import* (make-parameter #f))

;;; What a browser session can honestly declare — a subset of
;;; *write-kinds* that the platform can carry.
(define (webnode-write-kinds)
  '(soundscape acoustic-playback gpio-feeder))

(define (browser-session->cell session-id caps)
  "A visitor session → a cell-decl the offers gate understands.
   caps is what the browser actually granted (each permission prompt is
   the operator's signature); write-kinds narrow to what was granted."
  (make-cell-decl #:node-id session-id
                  #:heads (or (assq-ref caps 'heads) '(mic camera))
                  #:link-type 'wifi
                  #:location-class 'private
                  #:accepts-write (and (assq-ref caps 'actuate) #t)
                  #:write-kinds (assq-ref caps 'write-kinds)))

(define* (webnode-record session-id channel payload #:key subject at)
  "A visitor session's detection → <federated-record>. Uncalibrated and
   provenance-tagged — the record can never masquerade as quorum-grade."
  (let ((rec (make-federated-record
              #:source 'web-visitor
              #:source-id session-id
              #:subject subject
              #:channel channel
              #:at at
              #:payload `(,@payload
                        (uncalibrated . #t)
                        (consent . operator-session)))))
    (let ((import (*webnode-import*)))
      (if import (import rec) rec))))
