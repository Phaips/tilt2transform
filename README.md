# Rigid Tomogram Alignment Utility

Compute a single rigid 3×4 [IMOD](https://bio3d.colorado.edu/imod/) transform to bring one tomogram into the coordinate frame of another, using either [AreTomo](https://github.com/czimaginginstitute/AreTomo3) global-alignment files (`.aln`) or IMOD transform files (`.xf`).

## Features

* **Dual-mode input**

  * `.aln` mode: parses two AreTomo `.aln` files, uses median differences in ROT/TX/TY around zero-tilt.
  * `.xf` mode: parses two IMOD per-image `.xf` files, uses median differences in in-plane rotation and translation.
* **Optional Z-flip** (`--flip-z`) to correct reversed slice-order or reflections in the Z axis.

## Installation

```bash
# Clone or download the script
git clone https://github.com/Phaips/tilt2transform.git
cd aln2xf

# Install required Python packages
pip install numpy mrcfile SimpleITK
```

## Usage

```bash
python aln2xf.py [MODE] --out rigid_transform.xf [OPTIONS]
```

**`.aln` mode** (default ±5° tilt cutoff)

```bash
python aln2xf.py \
  --aln1 source_tomo.aln \
  --aln2 target_tomo.aln \
  --out  aln_transform.xf \
  [--tilt-cutoff 5] \
  [--flip-z]
```

* Reads ROT, TX, TY, TILT from each global alignment file.
* Keeps only entries with |TILT| ≤ `--tilt-cutoff`°.
* Computes median ΔROT, ΔTX, ΔTY.

**`.xf` mode**

```bash
python aln2xf.py \
  --xf1 source_tomo.xf \
  --xf2 target_tomo.xf \
  --out xf_transform.xf \
  [--flip-z]
```

* Parses each line of A11 A12 A21 A22 DX DY.
* Converts A11–A22 to an angle via `atan2(A21, A11)`.
* Takes medians of Δrotation and Δtranslation.

## Common Options

* `--out <file>`
  Output filename for the single 3×4 IMOD transform.
* `--tilt-cutoff <degrees>`
  (Only in `.aln` mode) Maximum |tilt| to include in the estimate (default 5°).
* `--flip-z`
  Flip the Z-axis (changes the third row from `[0 0 1 0]` to `[0 0 -1 0]`) to correct slice-order or reflection mismatches.

## Output

Writes a 3×4 IMOD-style `.xf`:

```text
 A11  A12   0   ΔX
 A21  A22   0   ΔY
  0    0  ±1    0
```

Apply with IMOD's `matchvol`:

```bash
matchvol \
  -input  tomo_source.mrc \
  -xffile rigid_transform.xf \
  -output tomo_target.mrc
```

## How It Works

1. **Parse inputs**

   * `.aln` mode: extract (ROT, TX, TY, TILT) for each tilt image index.
   * `.xf` mode: read (A11, A12, A21, A22, DX, DY) per image.

2. **Select/filter**
   * In `.aln` mode, only use images with |TILT| ≤ cutoff to avoid projection-induced X/Y shifts.

3. **Compute medians**
   * ΔROT = median(ROT₂ − ROT₁)
   * ΔX   = median(TX₂ − TX₁)
   * ΔY   = median(TY₂ − TY₁)

4. **Build rigid transform**
   * In-plane rotation about Z by ΔROT°
   * Translation (ΔX, ΔY) in X/Y
   * Z row is `[0 0 1 0]` (or `[0 0 -1 0]` with `--flip-z`)
