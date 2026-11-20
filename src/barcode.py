"""Barcode helpers: validation, normalisation, variants and image decoding."""

import re


def normalize_barcode(s) -> str:
    """Strip whitespace, dashes and other separators."""
    return re.sub(r'[\s\-_.]', '', str(s or ''))


def is_barcode(s) -> bool:
    s = normalize_barcode(s)
    return s.isdigit() and 8 <= len(s) <= 14


def _upce_to_upca(code: str) -> str | None:
    """Expand an 8-digit UPC-E (number system 0/1) to 12-digit UPC-A."""
    if len(code) != 8 or code[0] not in '01':
        return None
    ns, d, chk = code[0], code[1:7], code[7]
    last = d[5]
    if last in '012':
        body = d[0:2] + last + '0000' + d[2:5]
    elif last == '3':
        body = d[0:3] + '00000' + d[3:5]
    elif last == '4':
        body = d[0:4] + '00000' + d[4]
    else:
        body = d[0:5] + '0000' + last
    return ns + body + chk


def barcode_variants(code) -> list[str]:
    """Candidate codes to try against OFF, in priority order, deduplicated."""
    code = normalize_barcode(code)
    if not code:
        return []
    out = [code]
    if len(code) < 13:
        out.append(code.zfill(13))
    stripped = code.lstrip('0')
    if stripped and len(stripped) >= 6:
        out.append(stripped)
        if len(stripped) < 13:
            out.append(stripped.zfill(13))
    upca = _upce_to_upca(code)
    if upca:
        out += [upca, upca.zfill(13)]
    seen, res = set(), []
    for c in out:
        if c not in seen:
            seen.add(c)
            res.append(c)
    return res


def decode_image(pil_img) -> str | None:
    """Decode a barcode from a PIL image. Returns the string or None."""
    try:
        import pyzbar.pyzbar as pyzbar
        from PIL import Image
    except ImportError:
        return None
    try:
        import cv2
        import numpy as np
    except ImportError:
        cv2 = np = None

    try:
        base = pil_img.convert('RGB')
    except Exception:
        return None

    variants = [base]
    if cv2 is not None:
        try:
            gray = cv2.cvtColor(np.array(base), cv2.COLOR_RGB2GRAY)
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            variants.append(Image.fromarray(cv2.filter2D(gray, -1, kernel)))
            variants.append(Image.fromarray(cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)))
        except Exception:
            pass

    for v in variants:
        for angle in (0, 90, 180, 270):
            try:
                img = v if angle == 0 else v.rotate(angle, expand=True)
                res = pyzbar.decode(img)
            except Exception:
                continue
            for r in res:
                try:
                    return r.data.decode('utf-8')
                except Exception:
                    continue
    return None
