;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/mic.scm — detection streams to readings: the thin seam.
;;;
;;; WHAT THE FILE HOLDS. One direction only: OpenSoundscape-style detection
;;; records in, <reading> records out. The classifier is deliberately NOT
;;; here — it runs in Python on the edge (OpenSoundscape, BirdNET); this
;;; adapter just parses what the detector already decided and shapes it for
;;; sense-subject. Keeping the ML out of Scheme keeps the ≤5% custom rule
;;; honest and the seam auditable.
;;;
;;; THE WIRE. One detection per line: a JSON object when (json) resolves —
;;; the edge's real format — or a Scheme alist literal as the no-dependency
;;; fallback. Either parses to an alist; detection->reading maps the keys
;;; the detector emits: species, confidence, timestamp, node, mic_cal,
;;; gain, audio_said, subject. A line that parses to nothing is skipped
;;; with a reason, not swallowed: (skipped . line).

(define-module (adapters mic)
  #:use-module (srfi srfi-1)
  #:use-module (ice-9 rdelim)
  #:use-module (living specs)
  #:export (parse-detection-line detection->reading
            read-detections))


;;; the JSON seam — resolved once, at load; #f where guile-json is absent.
(define %json-parse
  (false-if-exception
    (module-ref (resolve-interface '(json)) 'json-string->scm)))

(define (json-keyed-alist v)
  "guile-json returns an alist with string keys; symbolize what we read."
  (map (lambda (p) (cons (string->symbol (car p)) (cdr p))) v))

(define (parse-detection-line line)
  "LINE → (det . alist) | (skipped . line). A JSON object when (json)
   resolves; a Scheme alist literal always."
  (cond
   ((or (not (string? line)) (zero? (string-length line)))
    (cons 'skipped line))
   ((and (char=? (string-ref line 0) #\{) %json-parse)
    (catch #t
      (lambda ()
        (cons 'det (json-keyed-alist (%json-parse line))))
      (lambda _ (cons 'skipped line))))
   ((char=? (string-ref line 0) #\()
    (catch #t
      (lambda ()
        (let ((v (call-with-input-string line read)))
          (if (list? v) (cons 'det v) (cons 'skipped line))))
      (lambda _ (cons 'skipped line))))
   (else (cons 'skipped line))))


;;; the mapping — detector keys to reading fields. 'subject' wins; a
;;; detection that names no subject still parses (the gate refuses it,
;;; which is the correct place for that decision).
(define* (detection->reading det #:key (subject #f))
  (let ((get (lambda (k) (assq-ref det k))))
    (make-reading
     #:subject (or (get 'subject) subject)
     #:channel (or (get 'node) (get 'channel) (get 'node_id))
     #:timestamp (or (get 'timestamp) (get 'ts) 0)
     #:payload `((species . ,(get 'species))
                 (confidence . ,(get 'confidence))
                 (band . ,(get 'band))
                 (start . ,(get 'start))
                 (end . ,(get 'end))
                 (audio-said . ,(get 'audio_said))))
     #:mic-cal (or (get 'mic_cal) (get 'mic-cal) (get 'calibration))
     #:gain (or (get 'gain) 0))))


(define* (read-detections #:optional (port (current-input-port))
                          #:key (subject #f))
  "Read every line on PORT: (reading . r) for each parse, (skipped . line)
   for each that is not a detection. SUBJECT stamps a default when the
   detection itself names none."
  (let loop ((acc '()))
    (let ((line (read-line port)))
      (if (eof-object? line)
          (reverse acc)
          (let ((p (parse-detection-line line)))
            (loop (cons (if (eq? 'det (car p))
                            (cons 'reading (detection->reading (cdr p)
                                                             #:subject subject))
                            p)
                        acc)))))))
