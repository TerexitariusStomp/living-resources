;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/connectome.scm — LIF verdict JSONL to connectome-verdicts.
;;;
;;; WHAT THE FILE HOLDS. The seam between tools/connectome/lif.py and the
;;; commons: the runner emits one JSON object per packed connectome —
;;; {connectome, input_said, action, confidence, spike_count,
;;; spike_digest, steps, encoder, features} — and this adapter parses
;;; them into <connectome-verdict> records. Like every adapter here it
;;; parses and validates shape; it never interprets what a verdict means
;;; about the organism. A connectome signature is evidence machinery,
;;; not a mind.

(define-module (adapters connectome)
  #:use-module (srfi srfi-1)
  #:use-module (ice-9 rdelim)
  #:use-module (living specs)
  #:use-module (living connectome)
  #:export (parse-verdict-line verdict-line->verdict
            read-verdicts))


(define %json-parse
  (false-if-exception
    (module-ref (resolve-interface '(json)) 'json-string->scm)))

(define (json-keyed-alist v)
  (map (lambda (p) (cons (string->symbol (car p)) (cdr p))) v))

;;; LINE → (verdict . alist) | (skipped . line). Dual format like the
;;; other adapters: JSON when (json) resolves, a Scheme alist literal
;;; always — sim fixtures can carry the alist form with no json module.

(define (parse-verdict-line line)
  (cond
   ((or (not (string? line)) (zero? (string-length line)))
    (cons 'skipped line))
   ((and (char=? (string-ref line 0) #\{) %json-parse)
    (catch #t
      (lambda () (cons 'verdict (json-keyed-alist (%json-parse line))))
      (lambda _ (cons 'skipped line))))
   ((char=? (string-ref line 0) #\()
    (catch #t
      (lambda ()
        (let ((v (call-with-input-string line read)))
          (if (and (list? v) (every pair? v))
              (cons 'verdict v)
              (cons 'skipped line))))
      (lambda _ (cons 'skipped line))))
   (else (cons 'skipped line))))


(define (verdict-line->verdict line)
  "LINE → <connectome-verdict> | #f. Accepts the runner's JSON keys and
   the alist form; missing or out-of-domain fields refuse quietly (#f)
   rather than minting a malformed verdict."
  (let ((parsed (parse-verdict-line line)))
    (and (eq? 'verdict (car parsed))
         (let* ((a (cdr parsed))
                (get (lambda (k) (assq-ref a k)))
                (action (get 'action))
                (confidence (get 'confidence)))
           (and (get 'connectome)
                (memv action '(-1 0 1))
                (number? confidence)
                (make-connectome-verdict
                 #:id (generate-id "cv-")
                 #:connectome (if (symbol? (get 'connectome))
                                  (get 'connectome)
                                  (string->symbol (get 'connectome)))
                 #:input-said (get 'input_said)
                 #:action (inexact->exact (round action))
                 #:confidence (inexact->exact (round confidence))
                 #:spike-count (or (get 'spike_count) 0)
                 #:spike-digest (get 'spike_digest)
                 #:steps (or (get 'steps) 0)
                 #:encoder (or (get 'encoder) "unknown")))))))

(define (read-verdicts port)
  "Read runner JSONL from PORT → list of <connectome-verdict>."
  (let loop ((line (read-line port)) (acc '()))
    (if (eof-object? line)
        (reverse acc)
        (loop (read-line port)
              (let ((v (verdict-line->verdict line)))
                (if v (cons v acc) acc))))))
