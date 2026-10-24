;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/sonar.scm — Doppler canopy-motion frames to readings.
;;;
;;; WHAT THE FILE HOLDS. The E1 seam: a 19–22 kHz emission + mic Doppler
;;; pipeline produces motion records — {motion, band_hz, depth_m, snr,
;;; timestamp, node, consent_said} — and this adapter shapes them into
;;; <reading> records of kind doppler-motion. The DSP is NOT here (SciPy
;;; runs edge-side); and the emission half is NOT a sense matter at all —
;;; it rides the emit lane's consent gate upstream. A sonar frame that
;;; arrives carrying no consent_said parses fine and refuses at the gate
;;; where that decision belongs.
;;;
;;; THE WIRE. Same dual-format parse as the other adapters: JSON when
;;; (json) resolves, a Scheme alist literal always. (skipped . line) for
;;; anything that is not a sonar frame.

(define-module (adapters sonar)
  #:use-module (srfi srfi-1)
  #:use-module (ice-9 rdelim)
  #:use-module (living specs)
  #:export (parse-sonar-line sonar->reading
            read-sonar))


(define %json-parse
  (false-if-exception
    (module-ref (resolve-interface '(json)) 'json-string->scm)))

(define (json-keyed-alist v)
  (map (lambda (p) (cons (string->symbol (car p)) (cdr p))) v))

(define (parse-sonar-line line)
  "LINE → (sonar . alist) | (skipped . line)."
  (cond
   ((or (not (string? line)) (zero? (string-length line)))
    (cons 'skipped line))
   ((and (char=? (string-ref line 0) #\{) %json-parse)
    (catch #t
      (lambda () (cons 'sonar (json-keyed-alist (%json-parse line))))
      (lambda _ (cons 'skipped line))))
   ((char=? (string-ref line 0) #\()
    (catch #t
      (lambda ()
        (let ((v (call-with-input-string line read)))
          (if (list? v) (cons 'sonar v) (cons 'skipped line))))
      (lambda _ (cons 'skipped line))))
   (else (cons 'skipped line))))


(define* (sonar->reading s #:key (subject #f))
  "A sonar frame → a <reading>. The consent SAID rides in the payload so
   the record itself can show which joint consent the emission ran under."
  (let ((get (lambda (k) (assq-ref s k))))
    (make-reading
     #:subject (or (get 'subject) subject)
     #:channel (or (get 'node) (get 'channel) (get 'node_id))
     #:timestamp (or (get 'timestamp) (get 'ts) 0)
     #:payload `((kind . doppler-motion)
                 (motion . ,(get 'motion))
                 (band-hz . ,(get 'band_hz))
                 (depth-m . ,(get 'depth_m))
                 (snr . ,(get 'snr))
                 (consent-said . ,(get 'consent_said)))
     #:mic-cal (get 'calibration)
     #:gain 0)))


(define* (read-sonar #:optional (port (current-input-port))
                     #:key (subject #f))
  "Read every line on PORT: (reading . r) per sonar frame,
   (skipped . line) for the rest."
  (let loop ((acc '()))
    (let ((line (read-line port)))
      (if (eof-object? line)
          (reverse acc)
          (let ((p (parse-sonar-line line)))
            (loop (cons (if (eq? 'sonar (car p))
                            (cons 'reading (sonar->reading (cdr p)
                                                           #:subject subject))
                            p)
                        acc)))))))
