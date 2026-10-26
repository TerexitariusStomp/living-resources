#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Render the funding PDFs (cap table + technical one-pager).

    python3 docs/funding/render-pdfs.py
"""

from fpdf import FPDF

GREEN = (45, 106, 79)
INK = (26, 31, 22)
MUTED = (90, 107, 94)


class Doc(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 8, self.foot_text, align="L")


def cap_table():
    pdf = Doc()
    pdf.foot_text = "Treetable LLC d/b/a Temple Earth - hello@templeearth.cc"
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.set_text_color(*INK)
    pdf.cell(0, 10, "Treetable LLC - Capitalization Table", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(0, 5.5, new_x="LMARGIN", new_y="NEXT", text=
                   "Colorado DLLC, ID 20208111742 (Good Standing) - formed January 1, 2021\n"
                   "Operating publicly as Temple Earth (templeearth.cc)\n"
                   "Prepared October 2026")
    pdf.ln(6)
    pdf.set_font("helvetica", "B", 9)
    pdf.set_text_color(*GREEN)
    for w, h in ((90, "HOLDER"), (60, "SECURITY"), (40, "OWNERSHIP %")):
        pdf.cell(w, 8, h, border="B")
    pdf.ln()
    pdf.set_font("helvetica", "", 11)
    pdf.set_text_color(*INK)
    for w, v in ((90, "T.R. Price"), (60, "Membership interest"), (40, "100%")):
        pdf.cell(w, 8, v, border="B")
    pdf.ln(14)
    pdf.set_font("helvetica", "", 10)
    pdf.multi_cell(0, 5.5, new_x="LMARGIN", new_y="NEXT", text=
                   "No options, SAFEs, convertible notes, warrants, or other "
                   "commitments outstanding. Fully diluted ownership is "
                   "identical to issued ownership.")
    pdf.output("temple-earth-cap-table.pdf")


def onepager():
    pdf = Doc()
    pdf.foot_text = ("Temple Earth (Treetable LLC) - T.R. Price - "
                     "hello@templeearth.cc - templeearth.cc")
    pdf.add_page()
    pdf.set_font("helvetica", "B", 15)
    pdf.set_text_color(*INK)
    pdf.cell(0, 8, "Temple Earth / the living cloud - Technical One-Pager",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 5, "Treetable LLC - templeearth.cc - hello@templeearth.cc",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    def head(t):
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(*GREEN)
        pdf.cell(0, 7, t.upper(), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*GREEN)
        pdf.line(pdf.l_margin, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(1)

    def bullet(t):
        pdf.set_font("helvetica", "", 9.5)
        pdf.set_text_color(*INK)
        pdf.set_x(pdf.l_margin)
        pdf.cell(5, 5, "-")
        pdf.multi_cell(0, 5, t, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("helvetica", "", 9.5)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 5, new_x="LMARGIN", new_y="NEXT", text=
                   "Evidence layer for ecological sensing: every field reading "
                   "carries a witnessed, replayable receipt. Non-invasive "
                   "sensing only - nothing attaches to an organism, nothing "
                   "enters the habitat, emission lanes are consent-gated "
                   "(joint guardian + operator approval) and logged. The "
                   "living system is the participant; computers are "
                   "scaffolding and verification.")

    head("Live product - replay-verified compute API")
    pdf.set_font("helvetica", "", 9.5)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 5, "templeearth.cc - /task /verdict /verify /receipts")
    bullet("Deterministic LIF simulation over 15 real EM-derived connectome "
           "wirings (C. elegans, Drosophila, hemibrain, medulla ~40k neurons, "
           "mouse retina, macaque, human segments and more).")
    bullet("Every task returns task_said + trace_digest; POST /verify replays "
           "the task and confirms byte-identical digests. Compute you can "
           "check - every task ships its own proof.")
    bullet("TypeScript port verified bit-identical to the Python reference "
           "engine (930/930 checks, Q24 fixed-point, banker's rounding, "
           "int64-LE digests, BLAKE2s content addressing).")

    head("Edge / protocol layer")
    bullet("Receipt chain: content-addressed evidence bundles, quorum "
           "witnessing, replay bundles - public ledger at /receipts.")
    bullet("EcoCell One node: XIAO ESP32-S3 + E22-400M22S Reticulum radio, "
           "BME280/BH1750/AD7746, TP4056 charge + MT3608 boost, SMA antenna, "
           "consent-gated emit path - manufacturable Gerber/drill/BOM/"
           "pick-and-place package complete (Seeed-ready). ~$40 BOM.")
    bullet("BYOD mode: the same evidence path runs on phones/Raspberry Pis - "
           "no custom hardware needed.")
    bullet("Federation: provenance-preserving adapters for 20+ allied sensor "
           "networks (BirdWeather, iNaturalist, Argo, PhenoCam and more).")

    head("Measured positioning")
    bullet("Sparse temporal computation benchmarked against dense O(n^2) "
           "baselines; honest result: advantage derives from sparsity - "
           "biological topology provides identity, provenance and replayable "
           "structure. Refused-lane results are published, not hidden.")
    bullet("License: AGPL-3.0-or-later. Suites green end-to-end: 63/63 "
           "protocol e2e, 71/71 live-site e2e, 930/930 compute parity.")

    head("Traction")
    bullet("API live in production; verification-audit offers out to "
           "Cortical Labs + FinalSpark.")
    bullet("NSF SBIR/STTR Project Pitch #00131003 submitted; Crowd Supply "
           "under review; Elemental Impact application submitted.")

    pdf.output("temple-earth-onepager.pdf")


if __name__ == "__main__":
    cap_table()
    onepager()
    print("wrote temple-earth-cap-table.pdf + temple-earth-onepager.pdf")
