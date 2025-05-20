#!/usr/bin/env python3
"""
aln2xf.py

Compute a single rigid 3×4 IMOD transform between two tomograms, either:

 • from AreTomo .aln files (using ROT, TX, TY around zero‐tilt), or  
 • from per‐image .xf files (using median Δrotation & Δtranslation across all images).

Usage:

# 1) .aln mode (default tilt cutoff = ±5°):
python aln2xf.py \
  --aln1 Position_2.aln \
  --aln2 Position_5.aln \
  --out  aln_transform.xf \
  [--tilt-cutoff 5] \
  [--flip-z]

# 2) .xf mode:
python aln2xf.py \
  --xf1  tomogram1.xf \
  --xf2  tomogram2.xf \
  --out  xf_transform.xf \
  [--flip-z]
"""

import argparse, sys, math
from statistics import median

def parse_aln(path):
    d = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) < 5:
                break
            try:
                sec  = int(parts[0])
                rot  = float(parts[1])
                tx   = float(parts[2])
                ty   = float(parts[3])
                tilt = float(parts[4])
            except ValueError:
                break
            d[sec] = (rot, tx, ty, tilt)
    return d

def parse_xf(path):
    """
    Read an IMOD .xf with one line per tilt image:
      A11 A12 A21 A22 DX DY
    Returns list of tuples (rot_deg, dx, dy).
    """
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            vals = line.split()
            if len(vals) < 6:
                continue
            a11, a12, a21, a22, dx, dy = map(float, vals[:6])
            # in‐plane rotation around Z:
            rot = math.degrees(math.atan2(a21, a11))
            entries.append((rot, dx, dy))
    return entries

def build_transform(dR, dX, dY, flip_z):
    # rotation about Z by dR degrees
    theta = math.radians(dR)
    c, s = math.cos(theta), math.sin(theta)
    zsign = -1.0 if flip_z else 1.0
    lines = [
        f"{c: .6f} {-s: .6f}  0.000000 {dX: .6f}",
        f"{s: .6f} { c: .6f}  0.000000 {dY: .6f}",
        f"0.000000  0.000000 {zsign: .6f}  0.000000"
    ]
    return "\n".join(lines) + "\n"

def main():
    p = argparse.ArgumentParser()
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument('--aln1', help='.aln for source tomogram')
    grp.add_argument('--xf1',  help='.xf for source tomogram')
    grp2 = p.add_mutually_exclusive_group(required=True)
    grp2.add_argument('--aln2', help='.aln for target tomogram')
    grp2.add_argument('--xf2',  help='.xf for target tomogram')

    p.add_argument('--out',         required=True, help='output .xf filename')
    p.add_argument('--tilt-cutoff', type=float, default=5.0,
                   help='|tilt|≤cutoff° for .aln mode (default 5°)')
    p.add_argument('--flip-z',      action='store_true',
                   help='flip Z axis (0→N-1) in output transform')
    args = p.parse_args()

    if args.aln1 and args.aln2:
        # --- .aln mode ---
        d1 = parse_aln(args.aln1)
        d2 = parse_aln(args.aln2)
        secs = sorted(set(d1) & set(d2))
        if not secs:
            sys.exit("❌ No common tilt indices in the two .aln files")
        drots, dtxs, dtys = [], [], []
        for sec in secs:
            rot1, tx1, ty1, tilt1 = d1[sec]
            rot2, tx2, ty2, tilt2 = d2[sec]
            if abs(tilt1) <= args.tilt_cutoff:
                drots.append(rot2 - rot1)
                dtxs.append(tx2  - tx1)
                dtys.append(ty2  - ty1)
        if not drots:
            sys.exit(f"❌ No entries within ±{args.tilt_cutoff}° of zero‐tilt")
        dR = median(drots)
        dX = median(dtxs)
        dY = median(dtys)

    else:
        # --- .xf mode ---
        xf1 = parse_xf(args.xf1)
        xf2 = parse_xf(args.xf2)
        n1, n2 = len(xf1), len(xf2)
        if n1==0 or n2==0:
            sys.exit("❌ Could not parse any entries from one of the .xf files")
        n = min(n1, n2)
        if n1 != n2:
            print(f"⚠️  Different lengths: using first {n} entries of each")
        drots = [xf2[i][0] - xf1[i][0] for i in range(n)]
        dtxs  = [xf2[i][1] - xf1[i][1] for i in range(n)]
        dtys  = [xf2[i][2] - xf1[i][2] for i in range(n)]
        dR = median(drots)
        dX = median(dtxs)
        dY = median(dtys)

    # --- build and write the final 3×4 .xf ---
    xf_text = build_transform(dR, dX, dY, args.flip_z)
    with open(args.out, 'w') as f:
        f.write(xf_text)

    print(f"✅ Wrote rigid transform to {args.out}")
    print(f"   Δrotation = {dR:.3f}°,  ΔX = {dX:.3f}px,  ΔY = {dY:.3f}px,  flip-Z = {args.flip_z}")

if __name__ == '__main__':
    main()
