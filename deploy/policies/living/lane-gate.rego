# SPDX-License-Identifier: AGPL-3.0-or-later
# deploy/policies/living/lane-gate.rego — the evidence gate as policy.
#
# The same rule module/living/offers.scm enforces in code, stated for OPA
# so a deployment's policy engine can audit it independently: an offer or
# intent is admitted only if its lane carries an evidence SAID — except the
# consent lanes (emit, cast, store), which ride the joint approval of the
# subject's guardian and the node operator. hop/compute/engineered are
# denied outright: consent is not evidence. relay is the transport lane:
# node-to-node forwarding, admitted only when it names the content-
# addressed packet SAID it carries. No silent defaults.
#
# Input shape:
#   {"lane": "sense", "evidence_said": "said:…", "duty_cycle_declared": true,
#    "calibrated": true, "params": {…}}
#   {"lane": "emit", "consent": {"guardian": "did:keri:…",
#    "operator": "aid:…", "said": "said:…"}}

package living.lanegate

import rego.v1

default allow := false

# the closed vocabulary — anything not named is denied as unknown
lanes := {"sense", "fleet", "emit", "cast", "hop", "compute", "store", "engineered", "relay", "federated"}

consent_lanes := {"emit", "cast", "store"}

refused_lanes := {"hop", "compute", "engineered"}

transport_lanes := {"relay"}

federated_lanes := {"federated"}

deny contains msg if {
	not lanes[input.lane]
	msg := sprintf("unknown-lane: the commons does not name '%v'", [input.lane])
}

deny contains msg if {
	refused_lanes[input.lane]
	msg := sprintf("lane-refused: %v stays refused — no evidence on file", [input.lane])
}

# consent lanes demand the joint approval — both humans, one credential
deny contains msg if {
	consent_lanes[input.lane]
	not input.consent.guardian
	msg := sprintf("consent-required: %v needs the guardian's approval", [input.lane])
}

deny contains msg if {
	consent_lanes[input.lane]
	not input.consent.operator
	msg := sprintf("consent-required: %v needs the node operator's approval", [input.lane])
}

deny contains msg if {
	consent_lanes[input.lane]
	not input.consent.said
	msg := sprintf("consent-required: %v needs the consent credential SAID", [input.lane])
}

# transport lanes forward only content-addressed bundles — name the packet
deny contains msg if {
	transport_lanes[input.lane]
	not input.packet_said
	msg := "payload-required: relay forwards only content-addressed bundles"
}

deny contains msg if {
	input.lane in {"sense", "fleet"}
	not input.evidence_said
	msg := "evidence-required: the lane's gate carries no evidence SAID"
}

# federated rides provenance: name the source network and the record it
# stands on — not our evidence gate, not consent
deny contains msg if {
	federated_lanes[input.lane]
	not input.source
	msg := "source-required: federated imports must name their source network"
}

deny contains msg if {
	federated_lanes[input.lane]
	not input.source_id
	msg := "source-required: federated imports must name the upstream record id"
}

deny contains msg if {
	input.lane == "sense"
	not input.duty_cycle_declared
	msg := "incomplete-declaration: duty-cycle must be declared"
}

deny contains msg if {
	input.lane == "sense"
	not input.calibrated
	msg := "incomplete-declaration: a reference-tone calibration is required"
}

allow if {
	input.lane in {"sense", "fleet"}
	input.evidence_said
	count(deny) == 0
}

allow if {
	consent_lanes[input.lane]
	count(deny) == 0
}

allow if {
	transport_lanes[input.lane]
	count(deny) == 0
}

allow if {
	federated_lanes[input.lane]
	count(deny) == 0
}

# the refusal a caller reads: allowed, or the full reason set
decision := {"allow": allow, "deny": deny}
