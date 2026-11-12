
















| Lane | `pm` — evidence-gated, same class as `env` |

**I2C level caveat (verify before committing):** the SPS30 runs on 5 V
and its module pull-ups reference VDD. The ESP32-S3's I2C pins are
3.3 V — powering the sensor at 5 V while pulling SDA/SCL to 3.3 V is
the standard field workaround and generally works, but confirm against
the datasheet/rev at order time. If it doesn't, a $1 BSS138 level-
shifter on SDA/SCL is the fallback. Do **not** pull the bus to 5 V —
that kills the XIAO.

**Placement:** connector J4 ("any 3.3 V I2C module") — repurpose as the
dedicated PM head; keep one J4 channel free for expansion by moving
SPS30 to a two-channel I2C mux only if a second I2C head appears.
Siting rule stays: nothing in the airstream disturbance of the sampler
intake — offset ≥ 0.5 m, same height band.

## H2S — two honest options

