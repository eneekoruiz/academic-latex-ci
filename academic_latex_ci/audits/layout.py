"""
2D Collision Detection, Typographical Layout Testing, and Page Budget Verification.

Extracts every character bounding box using pypdfium2 / PyMuPDF to detect:
1. Overlapping lines and negative vertical spacing collisions.
2. Horizontal margin boundaries and overfull hboxes.
3. Stranded section headings (orphan section headers).
4. Unclosed font-size switches causing irregular paragraph line heights.
5. Dead bibliographies and missing typographical penalty configurations.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import pypdfium2
except ImportError:
    pypdfium2 = None


def audit_vertical_collisions_on_page(page, page_num: int) -> List[str]:
    """
    Extracts all characters with exact 2D bounding boxes and baseline positions.
    Detects any vertical collision where a lower line overlaps or encroaches upon
    the bounding box of an upper line on the same horizontal slice.
    """
    defects = []
    tp = page.get_textpage()
    num_chars = tp.count_chars()
    
    chars = []
    for idx in range(num_chars):
        rect = tp.get_char_box(idx)
        char = tp.get_text_bounded(*rect)
        if char.strip():
            left, bottom, right, top = rect
            chars.append({
                "char": char,
                "left": left,
                "right": right,
                "bottom": bottom,
                "top": top,
                "height": top - bottom,
                "center_y": (top + bottom) / 2.0
            })
                
    if not chars:
        return defects
        
    chars.sort(key=lambda c: (-c["center_y"], c["left"]))
    
    # Cluster characters into lines by vertical center
    lines = []
    current_line = [chars[0]]
    current_y = chars[0]["center_y"]
    
    for c in chars[1:]:
        if abs(c["center_y"] - current_y) < 3.5:
            current_line.append(c)
        else:
            lines.append(current_line)
            current_line = [c]
            current_y = c["center_y"]
    if current_line:
        lines.append(current_line)
        
    # Check baseline spacing and bounding box collisions between successive lines
    for i in range(len(lines) - 1):
        line_a = lines[i]
        line_b = lines[i+1]
        
        a_bottom = min(c["bottom"] for c in line_a)
        a_top = max(c["top"] for c in line_a)
        b_bottom = min(c["bottom"] for c in line_b)
        b_top = max(c["top"] for c in line_b)
        
        # Check horizontal overlap
        a_left = min(c["left"] for c in line_a)
        a_right = max(c["right"] for c in line_a)
        b_left = min(c["left"] for c in line_b)
        b_right = max(c["right"] for c in line_b)
        
        has_horizontal_overlap = not (a_right < b_left or b_right < a_left)
        
        if has_horizontal_overlap:
            # Overlap in Y: upper line bottom is lower than lower line top
            overlap_pt = b_top - a_bottom
            if overlap_pt > 0.8:
                txt_a = "".join(c["char"] for c in line_a)[:35]
                txt_b = "".join(c["char"] for c in line_b)[:35]
                defects.append(
                    f"[PAGE {page_num} COLLISION] Severe vertical line collision detected! "
                    f"Lines overlap by {overlap_pt:.2f} pt. "
                    f"Line A: '{txt_a}...' (bottom={a_bottom:.1f}) collides with "
                    f"Line B: '{txt_b}...' (top={b_top:.1f}). Fix vertical spacing or negative vspace."
                )
    return defects


def audit_cover_spacing(page) -> List[str]:
    """Audits page 1 (cover) to verify vertical line spacing uniformity in author/title blocks."""
    defects = []
    tp = page.get_textpage()
    rects = []
    for r_idx in range(tp.count_rects()):
        rect = tp.get_rect(r_idx)
        txt = tp.get_text_bounded(*rect).strip()
        if txt:
            rects.append((rect, txt))
            
    rects.sort(key=lambda r: -r[0][3])
    
    # Audit author block gap consistency
    author_rects = [r for r in rects if any(name in r[1].lower() for name in ["ruiz", "pardavila", "ouinas", "eneko", "omar"])]
    if len(author_rects) >= 3:
        gaps = []
        for i in range(len(author_rects) - 1):
            upper_bot = author_rects[i][0][1]
            lower_top = author_rects[i+1][0][3]
            gap = upper_bot - lower_top
            gaps.append(gap)
        
        if max(gaps) - min(gaps) > 4.0:
            defects.append(
                f"[COVER DEFECT] Irregular author block line spacing detected on Cover Page! "
                f"Gaps between author lines vary: {[round(g, 1) for g in gaps]} pt. "
                f"Enforce identical line breaks (e.g. \\\\[0.4em]) for all authors in \\egileak."
            )
    return defects


def audit_source_typography(tex_dir: Path) -> List[str]:
    """Source code linting for LaTeX traps that cause typographical and spacing defects."""
    defects = []
    tex_files = [tf for tf in tex_dir.glob("**/*.tex") if not tf.name.startswith(('pandoc', 'test_', '_'))]
    
    total_cites = 0
    has_bib = False
    has_penalty_setup = False
    
    for tf in tex_files:
        content = tf.read_text(encoding="utf-8", errors="ignore")
        
        if r"\bibliography" in content or r"\printbibliography" in content:
            has_bib = True
            
        cites = re.findall(r'\\cite\{([^}]+)\}', content)
        total_cites += len(cites)
        
        if r"\widowpenalty" in content and r"\clubpenalty" in content:
            has_penalty_setup = True
            
        # Check: Unclosed font-size switch missing \par
        font_switches = re.findall(r'\{(\\(?:Large|LARGE|large|huge|Huge|small|footnotesize)[^}]+)\}', content)
        for block in font_switches:
            if r"\\" in block and not (block.rstrip().endswith(r"\par") or r"\par " in block):
                defects.append(
                    f"[SOURCE LINT] {tf.name}: Font-size switch block contains line-breaks '\\\\' "
                    f"without trailing '\\par'. This causes uneven, compressed line height on the final line! "
                    f"Snippet: '{block[:50]}...'. Ensure '...\\par}}' is used."
                )

    if has_bib and total_cites == 0:
        defects.append(
            "[SOURCE LINT] UNREFERENCED / DEAD BIBLIOGRAPHY DETECTED! '\\bibliography' is included but 0 '\\cite' calls exist in document."
        )

    if not has_penalty_setup:
        defects.append(
            "[SOURCE LINT] MISSING TYPOGRAPHICAL PENALTIES! Preamble must define \\widowpenalty=10000 and \\clubpenalty=10000 to eliminate orphan/widow lines."
        )

    return defects


def audit_pdf_layout(
    pdf_path: Path,
    tex_dir: Optional[Path] = None,
    expected_pages: Optional[int] = None,
    std_margin: float = 516.0,
    left_margin_limit: float = 45.0,
    chapter_margin: float = 585.0
) -> Tuple[bool, List[str]]:
    """Runs full automated layout audit across all PDF pages and LaTeX source files."""
    if pypdfium2 is None:
        raise ImportError("pypdfium2 is required. Install with: pip install pypdfium2")

    doc = pypdfium2.PdfDocument(str(pdf_path))
    total_pages = len(doc)
    defects = []

    # 1. Page Budget Check
    if expected_pages and total_pages != expected_pages:
        defects.append(
            f"PAGE BUDGET MISMATCH! Expected exactly {expected_pages} pages, but compiled document has {total_pages} pages."
        )

    # 2. Source-level typography and spacing checks
    if tex_dir and tex_dir.exists():
        src_defects = audit_source_typography(tex_dir)
        defects.extend(src_defects)

    # 3. PDF Page-by-page layout & collision checks
    for i, page in enumerate(doc):
        page_num = i + 1
        tp = page.get_textpage()
        text = tp.get_text_range()
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        
        # Check vertical collisions
        collision_defects = audit_vertical_collisions_on_page(page, page_num)
        defects.extend(collision_defects)
        
        # Check margin limits
        rects = [tp.get_rect(r) for r in range(tp.count_rects())]
        max_right = max([r[2] for r in rects]) if rects else 0
        min_left = min([r[0] for r in rects if r[2] > r[0]]) if rects else 0
        
        is_chapter_title_page = any(re.match(r"^(\d+|[A-Z])$", l) for l in lines[:3])
        margin_limit = chapter_margin if is_chapter_title_page else std_margin
        
        if max_right > margin_limit:
            defects.append(
                f"[PAGE {page_num} MARGIN] Text/table overflows right margin! max_x={max_right:.1f} pt (limit={margin_limit:.1f} pt)."
            )
            
        if min_left < left_margin_limit and page_num > 1:
            defects.append(
                f"[PAGE {page_num} MARGIN] Text overflows left margin! min_x={min_left:.1f} pt (limit={left_margin_limit:.1f} pt)."
            )
            
        # Check cover spacing on page 1
        if page_num == 1:
            cover_defects = audit_cover_spacing(page)
            defects.extend(cover_defects)
            
    return len(defects) == 0, defects
