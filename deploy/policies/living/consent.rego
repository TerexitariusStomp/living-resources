# SPDX-License-Identifier: AGPL-3.0-or-later
# deploy/policies/living/consent.rego — the guardian and the zero-disruption edge.
#
# The custody boundary as policy: an ecological subject has voice 0, so a
# reading may only ride consent the guardian signed; and the deployment
# itself stays minimum-disruption — nothing attached to an organism,
# nothing in soil, no anchor moorings, and any emission only under an
# explicit joint consent credential. Duty-cycle is declared so the power
# budget is itself evidence.
#
# Input shape:
#   {"subject": "eco:…", "guardian_aid": "did:keri:…",
#    "consent_said": "said:…", "guardian_signature": "sig…",
#    "duty_cycle": 0.3, "attachment": false, "soil_probe": false,
#    "emission": false, "mooring": "shore-dock"}

package living.consent

import rego.v1

default allow := false

# the subject never signs for itself — consent is the guardian's act
deny contains msg if {
	not input.guardian_aid
	msg := "guardian-required: a voiceless subject needs a named guardian"
}

deny contains msg if {
	not input.consent_said
	msg := "consent-required: no consent credential on file"
}

deny contains msg if {
	not input.guardian_signature
	msg := "signature-required: consent must arrive guardian-signed"
}

# zero-disruption, stated as denials — the deployment rules are code
deny contains msg if {
	input.attachment == true
	msg := "no-attachment: nothing attaches to an organism"
}

deny contains msg if {
	input.soil_probe == true
	msg := "no-soil: nothing enters the soil"
}

# emission is consent-gated, not banned — it needs the joint approval of
# the subject's guardian and the node operator (checked in lane-gate.rego);
# here we only insist the decision be explicit, never implied.
deny contains msg if {
	input.emission == true
	not input.emit_consent_said
	msg := "emit-consent-required: emission rides a joint consent credential, not a default"
}

deny contains msg if {
	input.mooring
	not input.mooring in {"shore-dock", "free-float-tether", "existing-structure", "terrestrial"}
	msg := "no-anchor: mooring must be shore/dock, free-float or existing structure"
}

deny contains msg if {
	not input.duty_cycle
	msg := "duty-cycle-required: the power budget is part of the declaration"
}

deny contains msg if {
	input.duty_cycle
	input.duty_cycle > 1
	msg := "duty-cycle-invalid: a fraction in (0,1]"
}

allow if {
	input.guardian_aid
	input.consent_said
	input.guardian_signature
	input.duty_cycle
	count(deny) == 0
}

decision := {"allow": allow, "deny": deny}
