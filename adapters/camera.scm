;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/camera.scm — photo detections to readings: the visual seam.
;;;
;;; WHAT THE FILE HOLDS. Same one-direction contract as adapters/mic.scm,
;;; for the OV2640 lane: vision-model detection records in, <reading>
;;; records out. The model is NOT here — phenology, species and pollinator
;;; inference runs Python-side on the edge; this adapter parses what the
;;; model decided: {taxon, confidence, frame_said, pheno_stage, count,
;;; timestamp, node}. A frame's content hash (frame_said) is the evidence
;;; link — the photo itself lives in the content store.
;;;
;;; THE WIRE. Same dual-format parse as mic.scm: JSON when (json)
;;; resolves, a Scheme alist literal otherwise. Anything that is not a
;;; photo-detection object is skipped with a reason, never swallowed.

(define-module (adapters camera)
  #:use-module (srfi srfi-1)
  #:use-module (ice-9 rdelim)
  #:use-module (living specs)
  #:export (parse-photo-line photo->reading
            read-photos))


;;; the JSON seam — resolved once, at load; #f where guile-json is absent.
(define %json-parse
  (false-if-exception
    (module-ref (resolve-interface '(json)) 'json-string->scm)))

(define (json-keyed-alist v)
  (map (lambda (p) (cons (string->symbol (car p)) (cdr p))) v))

(define (parse-photo-line line)
  "LINE → (photo . alist) | (skipped . line)."
  (cond
   ((or (not (string? line)) (zero? (string-length line)))
    (cons 'skipped line))
   ((and (char=? (string-ref line 0) #\{) %json-parse)
    (catch #t
      (lambda ()
        (cons 'photo (json-keyed-alist (%json-parse line))))
      (lambda _ (cons 'skipped line))))
   ((char=? (string-ref line 0) #\()
    (catch #t
      (lambda ()
        (let ((v (call-with-input-string line read)))
          (if (list? v) (cons 'photo v) (cons 'skipped line))))
      (lambda _ (cons 'skipped line))))
   (else (cons 'skipped line))))


;;; the mapping — photo-detections ride the same <reading> record as
;;; audio; the payload carries what only a frame can say: pheno_stage,
;;; count, frame_said. channel is the node that exposed the frame; the
;;; reading's mic-cal slot carries the frame's content SAID — the photo
;;; IS its own calibration evidence.
(define* (photo->reading ph #:key (subject #f))
  (let ((get (lambda (k) (assq-ref ph k))))
    (make-reading
     #:subject (or (get 'subject) subject)
     #:channel (or (get 'node) (get 'channel) (get 'node_id))
     #:timestamp (or (get 'timestamp) (get 'ts) 0)
     #:payload `((species . ,(get 'taxon))
                 (confidence . ,(get 'confidence))
                 (pheno-stage . ,(get 'pheno_stage))
                 (count . ,(get 'count))
                 (frame-said . ,(get 'frame_said))))
     #:mic-cal (get 'frame_said)
     #:gain 0)))


(define* (read-photos #:optional (port (current-input-port))
                      #:key (subject #f))
  "Read every line on PORT: (reading . r) per photo-detection,
   (skipped . line) for the rest."
  (let loop ((acc '()))
    (let ((line (read-line port)))
      (if (eof-object? line)
          (reverse acc)
          (let ((p (parse-photo-line line)))
            (loop (cons (if (eq? 'photo (car p))
                            (cons 'reading (photo->reading (cdr p)
                                                           #:subject subject))
                            p)
                        acc)))))))
