;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; tests/e2e/backhaul.scm — the ordered backhaul seam.
;;; Paths are bound at deployment; the order is a parameter; caps are
;;; honest (LPWAN-class → detections, broadband → snippets/full); only
;;; third-party transports produce federated imports. Unbound answers
;;; 'no-source/refused, never silence.
;;; Run: guile --no-auto-compile -L module -L . tests/e2e/backhaul.scm

(use-modules (adapters backhaul) (adapters federated)
             (srfi srfi-1) (ice-9 format))

(define pass-count 0) (define fail-count 0)
(define (check label . args)
  (let ((pass? (if (null? (cdr args)) (car args) (equal? (car args) (cadr args)))))
    (if pass? (set! pass-count (+ 1 pass-count))
        (begin (set! fail-count (+ 1 fail-count))
               (format #t "  FAIL: ~a~%" label)
               (unless (null? (cdr args))
                 (format #t "    expected: ~s~%    got: ~s~%" (cadr args) (car args)))))))
(define (scenario s) (format #t "~%── ~a ──~%" s))
(define (test-summary!)
  (format #t "~%=== Results: ~a passed, ~a failed ===~%" pass-count fail-count)
  (exit (if (zero? fail-count) 0 1)))

(scenario "the capability table is honest")
(check "caps" (list (payload-cap 'lora) (payload-cap 'wifi)
                    (payload-cap 'cat1-sat) (payload-cap 'starlink-sat))
       '(detections full snippets full))
(check "fits/degrade"
       (list (payload-fits? 'lora 'detections)
             (payload-fits? 'lora 'full)
             (payload-fits? 'starlink-sat 'full)
             (degrade-kind 'lora 'full)
             (degrade-kind 'starlink-sat 'full))
       '(#t #f #t detections full))
(check "channels" (list (path->channel 'lora) (path->channel 'wifi)
                        (path->channel 'cat1-sat) (path->channel 'starlink-sat))
       '(relay direct satellite satellite))

(scenario "unbound world answers, never invents")
(check "choose-backhaul unbound → #f" (choose-backhaul) #f)
(check "send-via-backhaul refuses no-backhaul"
       (let ((r (send-via-backhaul '((species . x)))))
         (and (eq? 'refused (car r))
              (eq? 'no-backhaul (assq-ref (cdr r) 'reason))))
       #t)

(scenario "bound paths walk the order, degrade honestly")
(define seen '())
(define (spy path)
  (lambda (req payload)
    (set! seen (cons (cons path (assq-ref req 'kind)) seen)) 'ok))
(define links (list (cons 'starlink-sat (spy 'starlink-sat))
                    (cons 'wifi (spy 'wifi))
                    (cons 'lora (spy 'lora))))
(check "default order: detections→lora, full→wifi"
       (list (choose-backhaul #:kind 'detections #:links links)
             (choose-backhaul #:kind 'full #:links links))
       '(lora wifi))
(*backhaul-order* '(starlink-sat wifi lora))
(check "order param prefers satellite"
       (choose-backhaul #:kind 'full #:links links) 'starlink-sat)
(let ((r (send-via-backhaul '((d . 1)) #:kind 'full #:links links)))
  (check "sent reply: path/channel/kind, not degraded"
         (and (eq? 'sent (car r))
              (eq? 'starlink-sat (assq-ref (cdr r) 'path))
              (eq? 'satellite (assq-ref (cdr r) 'channel))
              (eq? 'full (assq-ref (cdr r) 'kind))
              (eq? #f (assq-ref (cdr r) 'degraded)))
         #t))
(define lora-only (list (cons 'lora (spy 'lora))))
(let ((r (send-via-backhaul '((d . 1)) #:kind 'full #:links lora-only)))
  (check "lora-only degrades full→detections, flagged"
         (and (eq? 'sent (car r))
              (eq? 'lora (assq-ref (cdr r) 'path))
              (eq? 'detections (assq-ref (cdr r) 'kind))
              (eq? #t (assq-ref (cdr r) 'degraded)))
         #t))
(check "lora spy saw degraded kind" (cdr (assq 'lora seen)) 'detections)
(define dead (list (cons 'wifi (lambda (req payload) #f))))
(let ((r (send-via-backhaul '((d . 1)) #:links dead)))
  (check "link failure refuses with path named"
         (and (eq? 'refused (car r))
              (eq? 'backhaul-failed (assq-ref (cdr r) 'reason))
              (eq? 'wifi (assq-ref (cdr r) 'path)))
         #t))
(*backhaul-order* '(lora wifi cat1-sat starlink-sat))

(scenario "only third-party transports become imports")
(check "starlink → federated record"
       (let ((r (uplink->federated-record 'starlink-sat "node-9" 1730000000
                                          '((d . 1)))))
         (and (federated-record? r)
              (eq? 'starlink (federated-record-source r))
              (eq? 'satellite (federated-record-channel r))
              (equal? "node-9" (federated-record-source-id r))))
       #t)
(check "cat1 → direct-to-cell import"
       (federated-record-source
        (uplink->federated-record 'cat1-sat "n1" 1 '((d . 1))))
       'direct-to-cell)
(check "wifi/lora stay site-local"
       (list (uplink->federated-record 'wifi "n1" 1 '((d . 1)))
             (uplink->federated-record 'lora "n1" 1 '((d . 1))))
       '(#f #f))

(test-summary!)
