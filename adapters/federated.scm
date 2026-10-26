;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; adapters/federated.scm — the catalogue and the shared shape for imports
;;; from allied device networks.
;;;
;;; WHAT THE FILE HOLDS. The federated lane admits an intent that names its
;;; source network and the upstream record id — provenance, not our quorum.
;;; This file is the shared record for that import plus the readable map of
;;; the whole device-network landscape: *federated-sources* lists every
;;; network we have found, its direction (read | write | backhaul), and its
;;; status — live-now, public-verify, key-required, gated-partnership,
;;; opt-in-operator, open-invitation (owner has publicly opened the device),
;;; human-actuator, or excluded (with the reason — lethal actuation never
;;; carries a lane here).
;;;
;;; THE SOURCES' OWN APIS ARE THE OSS — the per-network files under
;;; adapters/ are thin seams that map an upstream record into this shape;
;;; none of them fetch by themselves. Fetches bind at deployment the same
;;; way *weather-fetch* does: a (web client) call, a pyinaturalist/ObsPy/
;;; erddapy/dataretrieval edge, or a farmbot-py / husqvarna-automower client
;;; for the write seams. Unbound seams answer 'no-source rather than invent.

(define-module (adapters federated)
  #:use-module (srfi srfi-1)
  #:use-module (srfi srfi-9)
  #:use-module (living specs)
  #:export (<federated-record> make-federated-record federated-record?
            federated-record-source federated-record-source-id
            federated-record-subject federated-record-channel
            federated-record-at federated-record-payload
            *federated-sources* source-status source-known?
            federated-record->intent))


;;; ── the record ──────────────────────────────────────────────────────────
;;; One imported observation: where it came from (source network + upstream
;;; id), which subject it speaks for, the channel name the commons gives it,
;;; when it happened, and the payload. The source pair is what the federated
;;; lane's admit-intent checks — a record without them is a rumour.

(define-record-type <federated-record>
  (%make-federated-record source source-id subject channel at payload)
  federated-record?
  (source    federated-record-source)    ; 'birdweather 'inaturalist …
  (source-id federated-record-source-id) ; upstream record/station id
  (subject   federated-record-subject)   ; ecological-agent id | #f
  (channel   federated-record-channel)   ; 'acoustic 'env 'seismic 'water …
  (at        federated-record-at)        ; epoch ms | ISO string upstream gave
  (payload   federated-record-payload))  ; alist — species, value, license…

(define* (make-federated-record #:key source source-id subject channel at
                                payload)
  (unless (and source source-id)
    (error "federated-record: provenance required" source source-id))
  (%make-federated-record source source-id subject channel at payload))

;;; the intent shape admit-intent consumes.
(define (federated-record->intent r)
  `(federated . ((source . ,(federated-record-source r))
                 (source-id . ,(federated-record-source-id r))
                 (subject . ,(federated-record-subject r))
                 (channel . ,(federated-record-channel r))
                 (at . ,(federated-record-at r))
                 (payload . ,(federated-record-payload r)))))


;;; ── the catalogue ───────────────────────────────────────────────────────
;;; (name endpoint direction status note) — the map, in one place.

(define *federated-sources*
  '(;; ── reads: live now, no key ─────────────────────────────────────
    (birdweather   "https://app.birdweather.com/graphql"          read  live-now           "26k+ acoustic stations (PUC); public GraphQL")
    (sensorcommunity "https://data.sensor.community"              read  live-now           "~14k DIY air/noise/env boxes; open, no key; data CC-BY-SA")
    (raspberryshake "https://data.raspberryshake.org/fdsnws"      read  live-now           "~6k citizen seismographs; FDSN std — ObsPy")
    (usgs-water    "https://waterservices.usgs.gov"               read  live-now           "~11k river gauges; WaterML/JSON — dataretrieval")
    (ea-water      "https://environment.data.gov.uk/hydrology"    read  live-now           "~2k UK hydrology stations; open")
    (argo          "https://erddap.ifremer.fr/erddap"             read  live-now           "~4k ocean floats — erddapy")
    (neon          "https://data.neonscience.org/api/v0"          read  live-now           "81 instrumented eco-sites; open API")
    (phenocam      "https://phenocam.nau.edu"                     read  live-now           "~900 vegetation cams; open")
    (orcasound     "https://live.orcasound.net"                   read  public-verify      "hydrophones; live audio + detections")
    (safecast      "https://api.safecast.org"                     read  public-verify      "radiation network; open")
    (inaturalist   "https://api.inaturalist.org/v1"               read  live-now           "app observations, CC0/CC-BY — pyinaturalist; feeds GoE Realms in ~24h")
    (gbif          "https://www.gbif.org"                         read  live-now           "weekly research-grade DwC-A — pygbif; citable DOI")
    (metwow        "https://wow.metoffice.gov.uk"                 read  public-verify      "~10k citizen weather stations; open API")
    (mesowest      "https://api.synopticdata.com"                 read  public-verify      "aggregator: ~100k stations, free tier")
    (openaq        "https://api.openaq.org"                       read  public-verify      "aggregator: ~30k official air monitors")
    (ndbc          "https://www.ndbc.noaa.gov"                    read  public-verify      "~290 ocean buoys/coastal stations")
    (phenocam-eu   "https://europeanphenocam.net"                 read  public-verify      "European sister of PhenoCam")
    (movebank      "https://www.movebank.org"                     read  public-verify      "tens of thousands of tagged animals; public studies")
    (otn           "https://oceantrackingnetwork.org"             read  gated-partnership  "fish telemetry receivers; data portal registration")
    (ismn          "https://ismn.earth"                           read  public-verify      "~2.8k soil-moisture stations; registration")
    (snotel        "https://wcc.sc.egov.usda.gov"                 read  public-verify      "~900 automated snow sensors")
    (fluxnet       "https://fluxnet.org"                          read  gated-partnership  "~1k flux towers; data portal")
    (alertwildfire "https://www.alertwildfire.org"                read  public-verify      "~800 forest fire-watch cams")
    (myshake       "https://myshake.berkeley.edu"                 read  gated-partnership  "phones as seismometers; Berkeley app")
    (acousticcommons "https://acousticcommons.net"                read  public-verify      "~50 live environmental audio streams")
    ;; ── reads: key required ─────────────────────────────────────────
    (purpleair     "https://api.purpleair.com"                    read  key-required       "~30k air sensors; free API key")
    (ebird         "https://api.ebird.org"                        read  key-required       "Cornell API key; feeds GoE")
    (motus         "https://motus.org"                            read  key-required       "~1.7k wildlife receiver towers; registration")
    ;; ── reads: partnership ──────────────────────────────────────────
    (goe           "https://api.guardiansofearth.io"              read  gated-partnership  "Realms/BioScore/BCU; advisor access pending")
    (rfcx          "https://arbimon.org"                          read  gated-partnership  "canopy Guardian devices; Arbimon gated")
    (frogid        "https://www.frogid.net.au"                    read  gated-partnership  "frog-call network; feeds GoE")
    ;; ── writes: open invitation (owner publicly opened the device) ──
    (farmbot-demo  "https://demo.farm.bot"                        write open-invitation   "real garden robot anyone may drive — farmbot-py")
    (opensprinkler-demo "https://demo.opensprinkler.com"          write open-invitation   "live demo irrigation unit")
    (labsland      "https://labsland.com"                         write open-invitation   "remote labs incl. aquarium/environment rigs")
    (robotarium    "https://www.robotarium.gatech.edu"            write open-invitation   "public multi-robot testbed")
    (iot-lab       "https://www.iot-lab.info"                     write open-invitation   "~2k programmable nodes incl. robots; open")
    ;; ── writes: owner opt-in required ───────────────────────────────
    (opensprinkler "https://opensprinkler.com"                    write opt-in-operator   "irrigation; HTTP/OTC owner token")
    (farmbot       "https://my.farm.bot"                          write opt-in-operator   "water/seed robots; owner MQTT+REST")
    (husqvarna     "https://developer.husqvarnagroup.cloud"       write opt-in-operator   "mowers + Gardena irrigation; owner OAuth")
    (reef-pi       "https://reef-pi.github.io"                    write opt-in-operator   "aquarium pumps/lights/feeders; on-device REST")
    (tasmota       "https://tasmota.github.io"                    write opt-in-operator   "open-firmware relays/pumps; owner LAN/MQTT")
    (esphome       "https://esphome.io"                           write opt-in-operator   "same shape as Tasmota")
    (openmower     "https://github.com/ClemensElflein/OpenMower"  write opt-in-operator   "open-source mowers; ROS")
    (marsfarm      "https://marsfarm.io"                          write opt-in-operator   "open food computers in schools")
    (mycodo        "https://kizniche.github.io/Mycodo"            write opt-in-operator   "grow-chamber climate; self-hosted")
    (audiomoth-dev "https://www.openacousticdevices.info"         write opt-in-operator   "Dev board is playback-capable; owner-deployed")
    (petcube       "https://petcube.com"                          write opt-in-operator   "public play sessions — laser + pets")
    ;; ── humans as actuators ─────────────────────────────────────────
    (litterati     "https://www.litterati.org"                    write human-actuator    "photo-verified cleanup — person is the actuator")
    (goe-bioquest  "https://www.guardiansofearth.io"              write human-actuator    "GoE tasks humans onto nature; advisor link")
    ;; ── writes: gated partnership ───────────────────────────────────
    (lg-sonic      "https://www.lgsonic.com"                      write gated-partnership "ultrasound algae buoys — the literal emit example")
    ;; ── backhaul ────────────────────────────────────────────────────
    (ttn           "https://www.thethingsnetwork.org"             backhaul live-now       "21k LoRaWAN gateways; webhook + downlinks — paho-mqtt")
    (helium        "https://helium.com"                           backhaul live-now       "~370k hotspots; same LoRaWAN shape")
    (meshtastic    "https://meshtastic.org"                       backhaul live-now       "public MQTT + mesh; remote GPIO opt-in")
    (aprs          "https://aprs.fi"                              backhaul public-verify  "~30k stations; API key for api.aprs.fi")
    ;; ── excluded — named, never carried ─────────────────────────────
    (goodnature    "https://goodnature.co.nz"                     write excluded          "lethal pest traps — outside the consent model")
    (felixer       "https://www.thylation.com"                    write excluded          "lethal spray units — same boundary")
    ))

(define (source-status name)
  (let ((e (assq name *federated-sources*)))
    (and e (list-ref e 3))))

(define (source-known? name) (and (assq name *federated-sources*) #t))
