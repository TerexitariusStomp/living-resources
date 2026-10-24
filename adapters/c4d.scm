;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/c4d.scm — contactless biofilm conductivity frames to readings.
;;;
;;; WHAT THE FILE HOLDS. The E3 seam: the C4D front-end reads K⁺-wave
;;; dynamics through a culture vessel wall — {conductance, wave_period_s,
;;; amplitude, timestamp, node, vessel_id} — and this adapter shapes them
;;; into <reading> records of kind c4d-readout. Nothing enters the culture
;;; and nothing here interprets the wave as computation: a readout lane is
;;; all this is until an experiment says otherwise — the read→compute
;;; claim belongs to the gate, not the adapter.
;;;
;;; THE WIRE. Same dual-format parse as the other adapters: JSON when
;;; (json) resolves, a Scheme alist literal always. (skipped . line) for
;;; anything that is not a c4d frame.

(define-module (adapters c4d)
  #:use-module (srfi srfi-1)
  #:use-module (ice-9 rdelim)
  #:use-module (living specs)
  #:export (parse-c4d-line c4d->reading
            read-c4d))


(define %json-parse
  (false-if-exception
    (module-ref (resolve-interface '(json)) 'json-string->scm)))

(define (json-keyed-alist v)
  (map (lambda (p) (cons (string->symbol (car p)) (cdr p))) v))

(define (parse-c4d-line line)
  "LINE → (c4d . alist) | (skipped . line)."
  (cond
   ((or (not (string? line)) (zero? (string-length line)))
    (cons 'skipped line))
   ((and (char=? (string-ref line 0) #\{) %json-parse)
    (catch #t
      (lambda () (cons 'c4d (json-keyed-alist (%json-parse line))))
      (lambda _ (cons 'skipped line))))
   ((char=? (string-ref line 0) #\()
    (catch #t
      (lambda ()
        (let ((v (call-with-input-string line read)))
          (if (list? v) (cons 'c4d v) (cons 'skipped line))))
      (lambda _ (cons 'skipped line))))
   (else (cons 'skipped line))))


(define* (c4d->reading c #:key (subject #f))
  "A c4d frame → a <reading>. vessel_id identifies the culture; the
   front-end's electrode calibration SAID rides mic-cal."
  (let ((get (lambda (k) (assq-ref c k))))
    (make-reading
     #:subject (or (get 'subject) subject)
     #:channel (or (get 'node) (get 'channel) (get 'node_id))
     #:timestamp (or (get 'timestamp) (get 'ts) 0)
     #:payload `((kind . c4d-readout)
                 (conductance . ,(get 'conductance))
                 (wave-period-s . ,(get 'wave_period_s))
                 (amplitude . ,(get 'amplitude))
                 (vessel-id . ,(get 'vessel_id))))
     #:mic-cal (get 'electrode_cal)
     #:gain 0)))


(define* (read-c4d #:optional (port (current-input-port))
                   #:key (subject #f))
  "Read every line on PORT: (reading . r) per c4d frame,
   (skipped . line) for the rest."
  (let loop ((acc '()))
    (let ((line (read-line port)))
      (if (eof-object? line)
          (reverse acc)
          (let ((p (parse-c4d-line line)))
            (loop (cons (if (eq? 'c4d (car p))
                            (cons 'reading (c4d->reading (cdr p)
                                                         #:subject subject))
                            p)
                        acc)))))))
