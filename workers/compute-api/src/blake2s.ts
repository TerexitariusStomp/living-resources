// SPDX-License-Identifier: AGPL-3.0-or-later
// blake2s.ts — unkeyed BLAKE2s-256 (RFC 7693), self-contained.
// Adopted-OSS-equivalent port of the public-domain reference algorithm;
// kept in-repo so the worker has zero npm deps. Verified byte-for-byte
// against hashlib.blake2s in test/diff.mjs.

const IV = new Uint32Array([
  0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
  0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
]);

const SIGMA = [
  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
  [14, 10, 4, 8, 9, 15, 13, 6, 1, 12, 0, 2, 11, 7, 5, 3],
  [11, 8, 12, 0, 5, 2, 15, 13, 10, 14, 3, 6, 7, 1, 9, 4],
  [7, 9, 3, 1, 13, 12, 11, 14, 2, 6, 5, 10, 4, 0, 15, 8],
  [9, 0, 5, 7, 2, 4, 10, 15, 14, 1, 11, 12, 6, 8, 3, 13],
  [2, 12, 6, 10, 0, 11, 8, 3, 4, 13, 7, 5, 15, 14, 1, 9],
  [12, 5, 1, 15, 14, 13, 4, 10, 0, 7, 6, 3, 9, 2, 8, 11],
  [13, 11, 7, 14, 12, 1, 3, 9, 5, 0, 15, 4, 8, 6, 2, 10],
  [6, 15, 14, 9, 11, 3, 0, 8, 12, 2, 13, 7, 1, 4, 10, 5],
  [10, 2, 8, 4, 7, 6, 1, 5, 15, 11, 9, 14, 3, 12, 13, 0],
];

const rotr = (x: number, r: number): number =>
  ((x >>> r) | (x << (32 - r))) >>> 0;

export function blake2s(data: Uint8Array, outLen = 32): Uint8Array {
  const h = new Uint32Array(IV);
  // param block: digest_length | key_length<<8 | fanout<<16 | depth<<24
  h[0] ^= 0x01010000 ^ outLen;
  const v = new Uint32Array(16);
  const m = new Uint32Array(16);
  const block = new Uint8Array(64);
  const dv = new DataView(block.buffer);
  let t0 = 0, t1 = 0; // 64-bit byte counter, split

  const compress = (last: boolean): void => {
    for (let i = 0; i < 16; i++) m[i] = dv.getUint32(i * 4, true);
    v.set(h); v.set(IV, 8);
    v[12] ^= t0; v[13] ^= t1;
    if (last) v[14] = ~v[14];
    for (let r = 0; r < 10; r++) {
      const s = SIGMA[r];
      const G = (a: number, b: number, c: number, d: number,
                 x: number, y: number): void => {
        v[a] = (v[a] + v[b] + x) >>> 0; v[d] = rotr(v[d] ^ v[a], 16);
        v[c] = (v[c] + v[d]) >>> 0; v[b] = rotr(v[b] ^ v[c], 12);
        v[a] = (v[a] + v[b] + y) >>> 0; v[d] = rotr(v[d] ^ v[a], 8);
        v[c] = (v[c] + v[d]) >>> 0; v[b] = rotr(v[b] ^ v[c], 7);
      };
      G(0, 4, 8, 12, m[s[0]], m[s[1]]);
      G(1, 5, 9, 13, m[s[2]], m[s[3]]);
      G(2, 6, 10, 14, m[s[4]], m[s[5]]);
      G(3, 7, 11, 15, m[s[6]], m[s[7]]);
      G(0, 5, 10, 15, m[s[8]], m[s[9]]);
      G(1, 6, 11, 12, m[s[10]], m[s[11]]);
      G(2, 7, 8, 13, m[s[12]], m[s[13]]);
      G(3, 4, 9, 14, m[s[14]], m[s[15]]);
    }
    for (let i = 0; i < 8; i++) h[i] = (h[i] ^ v[i] ^ v[i + 8]) >>> 0;
  };

  let off = 0;
  while (data.length - off > 64) {
    block.set(data.subarray(off, off + 64));
    off += 64;
    t0 += 64; if (t0 > 0xffffffff) { t0 >>>= 0; t1 = (t1 + 1) >>> 0; }
    compress(false);
  }
  block.fill(0);
  block.set(data.subarray(off));
  const rem = data.length - off;
  t0 += rem; if (t0 > 0xffffffff) { t0 >>>= 0; t1 = (t1 + 1) >>> 0; }
  compress(true);

  const out = new Uint8Array(outLen);
  const odv = new DataView(out.buffer);
  for (let i = 0; i < outLen / 4; i++) odv.setUint32(i * 4, h[i], true);
  return out;
}

const HEX = "0123456789abcdef";
export function hex(b: Uint8Array): string {
  let s = "";
  for (let i = 0; i < b.length; i++)
    s += HEX[b[i] >>> 4] + HEX[b[i] & 15];
  return s;
}

export function blake2sHex(data: Uint8Array | string): string {
  const bytes = typeof data === "string"
    ? new TextEncoder().encode(data) : data;
  return hex(blake2s(bytes));
}
