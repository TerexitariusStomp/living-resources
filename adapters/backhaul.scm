;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/backhaul.scm — ordered backhaul paths and their provenance.
;;;
;;; WHAT THE FILE HOLDS. The transport-selection seam the spec's T4 tier
;;; names: a node or edge may reach the commons over LoRa mesh, site WiFi
;;; (a Starlink Mini's LAN counts), a CAT-1 modem riding carrier
;;; direct-to-cell, or a broadband satellite terminal. This file holds the
;;; ORDER, the per-path capability table, and the mapping from path to the
;;; provenance label a reading carries — it moves packets, it never
;;; classifies and it never invents a link that is not bound.
;;;
;;; THE LINKS ARE THE SEAMS. *backhaul-links* is an alist of path →
;;; (proc kind payload-alist) → reply, bound at deployment: the LoRa entry
;;; wraps the RNode/µReticulum uplink, wifi the UDP listener path, cat1-sat
;;; a ModemManager/qmicli client on the phone edge, starlink-sat the
;;; dish→WiFi edge. Unbound paths are simply absent from the alist —
;;; choose-backhaul walks *backhaul-order* and takes the first bound path
;;; whose payload cap covers what is being sent. When nothing is bound the
;;; answer is 'no-source, the same posture as *ttn-downlink*.
;;;
;;; CAPABILITIES ARE HONEST. LPWAN-satellite competitors carry ~46-byte
;;; detections on an hourly cadence; our broadband paths carry audio
;;; snippets. The cap table says what each path can honestly move:
;;;   detections — the small DET1/ENV1 frame contract
;;;   snippets   — detections plus bounded audio excerpts
;;;   full       — detections, snippets, scheduled media
;;; A payload kind above a path's cap is degraded to the cap, never
;;; silently dropped: the caller sees the (path . actual-kind) pair and
;;; the receipt records what actually travelled.

(define-module (adapters backhaul)
  #:use-module (srfi srfi-1)
  #:use-module (living specs)
  #:use-module (adapters federated)
  #:export (*backhaul-order* *backhaul-links* *backhaul-paths*
            backhaul-paths payload-cap payload-kind-rank
            payload-fits? degrade-kind
            path->channel path->federated-source
            choose-backhaul send-via-backhaul
            uplink->federated-record))


;;; ── the order and the links ─────────────────────────────────────────────
;;; Deployment binds *backhaul-links*; the order parameter lets a site
;;; prefer satellite over mesh (or the reverse) without code changes.

(define *backhaul-order*
  (make-parameter '(lora wifi cat1-sat starlink-sat)))

;;; (path . proc) — proc receives (kind payload-alist) and answers a reply
;;; alist or #f. Absent path = unbound = skipped, never an error.
(define *backhaul-links* (make-parameter '()))


;;; ── the capability table ────────────────────────────────────────────────
;;; channel is the provenance label the reading/receipt carries — the same
;;; vocabulary the federated lane already uses ('relay 'direct 'satellite).

(define *backhaul-paths*
  '((lora         . ((channel . relay)     (cap . detections)))
    (wifi         . ((channel . direct)    (cap . full)))
    (cat1-sat     . ((channel . satellite) (cap . snippets)))
    (starlink-sat . ((channel . satellite) (cap . full)))))

(define (backhaul-paths) *backhaul-paths*)

(define (payload-cap path)
  (let ((e (assq path *backhaul-paths*)))
    (and e (assq-ref (cdr e) 'cap))))

(define (payload-kind-rank k)
  (case k
    ((detections) 1)
    ((snippets)   2)
    ((full)       3)
    (else 0)))

(define (payload-fits? path kind)
  (let ((cap (payload-cap path)))
    (and cap (>= (payload-kind-rank cap)
                 (payload-kind-rank kind)))))

(define (degrade-kind path kind)
  "The honest payload kind PATH can carry — min(requested, cap)."
  (let ((cap (payload-cap path)))
    (if (and cap (payload-kind-rank cap) < (payload-kind-rank kind))
        cap
        kind)))

(define (path->channel path)
  (let ((e (assq path *backhaul-paths*)))
    (and e (assq-ref (cdr e) 'channel))))

;;; The federated source name a path's records cite — only paths that
;;; ride a THIRD-PARTY network produce imports; site-local transports
;;; (our LoRa mesh, the site LAN) stay 'direct/'relay and are not
;;; re-labeled as someone else's observation.
(define (path->federated-source path)
  (case path
    ((cat1-sat) 'direct-to-cell)
    ((starlink-sat) 'starlink)
    (else #f)))


;;; ── selection ───────────────────────────────────────────────────────────
;;; choose-backhaul walks the order, skips unbound paths, and returns the
;;; first path whose cap covers KIND — or, when nothing covers it, the
;;; first bound path at all (the caller then sees the degraded kind).
;;; Returns #f when no path is bound at all.

(define* (choose-backhaul #:key (kind 'detections) (links #f))
  (let* ((order (*backhaul-order*))
         (links (or links (*backhaul-links*)))
         (bound? (lambda (p) (assq p links))))
    (or (let loop ((ps order))
          (cond
           ((null? ps) #f)
           ((and (bound? (car ps)) (payload-fits? (car ps) kind))
            (car ps))
           (else (loop (cdr ps)))))
        (let loop ((ps order))
          (cond
           ((null? ps) #f)
           ((bound? (car ps)) (car ps))
           (else (loop (cdr ps))))))))

;;; send-via-backhaul dispatches one payload. The reply is the link
;;; proc's own answer; an unbound world answers a refused record naming
;;; the reason — answered, never dropped.
(define* (send-via-backhaul payload #:key (kind 'detections)
                             (subject #f) (at #f) (links #f))
  (let ((path (choose-backhaul #:kind kind #:links links)))
    (cond
     ((not path)
      (cons 'refused '((reason . no-backhaul)
                       (detail . "no backhaul path is bound"))))
     (else
      (let* ((links (or links (*backhaul-links*)))
             (proc (cdr (assq path links)))
             (actual (degrade-kind path kind))
             (reply (proc `((kind . ,actual)) payload)))
        (if reply
            (cons 'sent
                  `((path . ,path)
                    (channel . ,(path->channel path))
                    (kind . ,actual)
                    (degraded . ,(not (eq? actual kind)))
                    (reply . ,reply)))
            (cons 'refused
                  `((reason . backhaul-failed)
                    (path . ,path)
                    (detail . "link proc answered #f")))))))))


;;; ── provenance ──────────────────────────────────────────────────────────
;;; A payload that travelled a non-local path becomes a federated record —
;;; the same rule TTN uplinks already follow: imports are labeled theirs,
;;; never our quorum. LOCAL paths (wifi on the site LAN) stay 'direct and
;;; are not re-labeled as imports.

(define* (uplink->federated-record path node-id at payload
                                  #:key (subject #f))
  (let ((src (path->federated-source path)))
    (and src
         (make-federated-record
          #:source src
          #:source-id (or node-id "unknown-node")
          #:subject subject
          #:channel (path->channel path)
          #:at at
          #:payload payload))))
