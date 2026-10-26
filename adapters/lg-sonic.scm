;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/lg-sonic.scm — ultrasound algae buoys, partnership seam.
;;;
;;; gated-partnership: LG Sonic's MPC-Buoy fleet literally emits ultrasound
;;; into lakes — the reference case for the commons' acoustic write-kinds.
;;; No public API; the seam stays unbound until a partnership lands, and
;;; even then every emission still rides emit's two-key consent (buoy
;;; operator + the water body's guardian).

(define-module (adapters lg-sonic)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*lgsonic-credentials* *lgsonic-send* lgsonic-status import-status))

(define *lgsonic-credentials* (make-parameter #f))
(define *lgsonic-send* (make-parameter #f))

(define (lgsonic-status)
  (if (not (and (*lgsonic-credentials*) (*lgsonic-send*)))
      'no-source
      ((*lgsonic-send*) 'status (*lgsonic-credentials*))))

(define (import-status s subject)
  (make-federated-record
   #:source 'lg-sonic
   #:source-id (or (assq-ref s 'buoy_id) (assq-ref s 'id))
   #:subject subject
   #:channel 'acoustic
   #:at (assq-ref s 'at)
   #:payload `((program . ,(assq-ref s 'program))   ; which ultrasonic program ran
               (chlorophyll . ,(assq-ref s 'chl-a)))))
