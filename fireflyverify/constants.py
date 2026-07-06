"""Shared physical / acquisition defaults — the single source of truth.

Both ``adapters`` and ``scoring`` import from here (this lives at the package
root, so nothing creates a scoring→adapters import cycle). These are the values
used only as a *fallback*, when a tool's manifest or an imported ground-truth
file does not supply the real acquisition parameters.
"""
from __future__ import annotations

# Acquisition fallbacks (used when a file/manifest omits the real value).
DEFAULT_PX_UM = 0.106          # µm per pixel
DEFAULT_DT_S = 0.02            # s per frame

# Gaussian-PSF approximation of the diffraction-limited spot: σ_nm ≈ 0.21·λ/NA.
DEFAULT_WAVELENGTH_NM = 660.0  # emission wavelength
DEFAULT_NA = 1.4               # objective numerical aperture
MIN_PSF_SIGMA_PX = 0.5         # floor so σ never collapses sub-half-pixel

# CRLB (Mortensen 2010) background-photon floor, avoids a divide-by-zero when a
# dataset reports zero background.
CRLB_BG_FLOOR = 1e-9


def default_psf_sigma_px(pixel_size_um: float,
                         wavelength_nm: float = DEFAULT_WAVELENGTH_NM,
                         na: float = DEFAULT_NA) -> float:
    """Default Gaussian-PSF σ in PIXELS from the diffraction limit ≈ 0.21·λ/NA.

    Matches the historical formula used across the adapters
    (``max(0.5, (0.21·λ/NA) / (px·1000))``), centralised here so the pixel
    size, wavelength and NA live in exactly one place.
    """
    sigma_nm = 0.21 * float(wavelength_nm) / float(na)
    px_nm = float(pixel_size_um) * 1000.0
    return max(MIN_PSF_SIGMA_PX, sigma_nm / px_nm)
