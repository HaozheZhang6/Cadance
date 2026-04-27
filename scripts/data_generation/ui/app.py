"""CAD Data Pipeline — Overview + Stem Viewer."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "data_generation"))

VERIFIED_CSV = ROOT / "data/data_generation/verified_parts.csv"
PARTS_CSV = ROOT / "data/data_generation/parts.csv"
SYNTH_CSV = ROOT / "data/data_generation/synth_parts.csv"
BLOCKLIST_CSV = ROOT / "data/data_generation/upload_blocklist.csv"
STEM_FS = ROOT / "data/data_generation/generated_data/fusion360"

st.set_page_config(page_title="CAD Pipeline Monitor", layout="wide")


# ── data ─────────────────────────────────────────────────────────────────────

F360_RECON = (
    ROOT
    / "data/data_generation/open_source/fusion360_gallery/raw/r1.0.1/reconstruction"
)
# DeepCAD: adjust path when integrated
DEEPCAD_RECON = ROOT / "data/data_generation/open_source/deepcad"


@st.cache_data(ttl=30)
def load_data():
    verified_schema = {
        "stem": "",
        "data_source": "",
        "sft_ready": "",
        "cq_code_path": "",
        "norm_cq_code_path": "",
        "pipeline_run": "",
        "timestamp": "",
        "iou": pd.NA,
        "norm_iou": pd.NA,
        "gt_norm_step_path": "",
        "gt_step_path": "",
        "gt_views_norm_dir": "",
    }
    parts_schema = {
        "stem": "",
        "status": "",
        "iou": pd.NA,
        "pipeline_run": "",
        "failure_code": "",
        "retry_reason": "",
        "gen_step_path": "",
        "cq_code_path": "",
        "run": "",
        "source": "",
    }

    def _read_csv_or_empty(path: Path, schema: dict) -> pd.DataFrame:
        if path.exists():
            df = pd.read_csv(path)
        else:
            df = pd.DataFrame(columns=list(schema))
        for col, default in schema.items():
            if col not in df.columns:
                df[col] = default
        return df

    vdf = _read_csv_or_empty(VERIFIED_CSV, verified_schema)
    pdf = _read_csv_or_empty(PARTS_CSV, parts_schema)
    return vdf, pdf


@st.cache_data(ttl=10)
def load_synth() -> pd.DataFrame:
    """Load synth_parts.csv, return empty df if missing."""
    if not SYNTH_CSV.exists():
        return pd.DataFrame()
    return pd.read_csv(SYNTH_CSV)


@st.cache_data(ttl=10)
def load_blocklist() -> pd.DataFrame:
    """Load upload filter blocklist (stem/reason/pipeline_run)."""
    if not BLOCKLIST_CSV.exists():
        return pd.DataFrame(columns=["stem", "reason", "pipeline_run"])
    return pd.read_csv(BLOCKLIST_CSV)


@st.cache_data(ttl=300)
def load_source_universe() -> dict:
    """Count raw stems per source from disk. Cached 5 min (slow glob)."""
    f360_total = len(list(F360_RECON.glob("*.json"))) if F360_RECON.exists() else 0
    deepcad_total = (
        len(list(DEEPCAD_RECON.glob("**/*.json"))) if DEEPCAD_RECON.exists() else 0
    )
    return {"fusion360": f360_total, "deepcad": deepcad_total}


def _s(v) -> str:
    if v is None:
        return ""
    s = str(v)
    return "" if s in ("nan", "None", "") else s


def _strip_suffix(stem: str) -> str:
    for sfx in ("_claude_fixed", "_copy_gt", "_manual_fix"):
        if stem.endswith(sfx):
            return stem[: -len(sfx)]
    return stem


def _display_value(v):
    if pd.isna(v):
        return ""
    if isinstance(v, bytes):
        try:
            return v.decode("utf-8")
        except UnicodeDecodeError:
            return repr(v)
    if isinstance(v, (list, tuple, dict, set)):
        return repr(v)
    return v


def show_df(df: pd.DataFrame, **kwargs):
    """Normalize mixed object columns so Streamlit/pyarrow can render them."""
    safe = df.copy()
    for col in safe.columns:
        if pd.api.types.is_object_dtype(safe[col]):
            safe[col] = safe[col].map(_display_value)
    st.dataframe(safe, **kwargs)


# ── overview page ─────────────────────────────────────────────────────────────


def page_overview():
    st.title("Pipeline Monitor")
    vdf, pdf = load_data()
    n = len(vdf)

    # ── Section 1: SFT dataset (verified_parts.csv) ───────────────────────────
    st.subheader("SFT Dataset  (verified_parts.csv)")

    universe = load_source_universe()
    v_by_src = vdf["data_source"].fillna("unknown").value_counts().to_dict()
    n_sft = int((vdf["sft_ready"].astype(str) == "True").sum())
    n_f360 = v_by_src.get("fusion360", 0)
    n_synth = v_by_src.get("synthetic", 0)
    n_has_cq = int((vdf["cq_code_path"].notna() & (vdf["cq_code_path"] != "")).sum())
    n_has_norm = int(
        (vdf["norm_cq_code_path"].notna() & (vdf["norm_cq_code_path"] != "")).sum()
    )
    f360_total = universe["fusion360"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total verified pairs", n)
    c2.metric("sft_ready  (norm_iou ≥ 0.99)", n_sft)
    c3.metric("Fusion360", n_f360)
    c4.metric("Synthetic", n_synth)

    # SFT funnel with progress bars
    st.caption("SFT normalization funnel")
    stages = [
        ("Verified pairs", n, n),
        ("Has CQ code", n_has_cq, n),
        ("Has norm_cq", n_has_norm, n),
        ("norm_iou ≥ 0.99", n_sft, n),
    ]
    for label, val, total_ref in stages:
        pct = val / total_ref if total_ref else 0
        st.progress(pct, text=f"{label}: {val:,} / {total_ref:,}  ({100*pct:.1f}%)")

    # F360 universe coverage
    if f360_total:
        pct = n_f360 / f360_total
        st.progress(
            pct,
            text=f"Fusion360 coverage: {n_f360:,} / {f360_total:,}  ({100*pct:.1f}%)",
        )

    st.divider()

    # ── Section 2: Generation pipeline (parts.csv) ────────────────────────────
    st.subheader("Generation Pipeline  (parts.csv)")

    last = pdf.groupby("stem").last().reset_index()
    total = len(last)
    n_verified = int(last["status"].isin(["verified", "manually_fixed"]).sum())
    n_near_miss = int((last["status"] == "near_miss").sum())
    n_failed = int(last["status"].isin(["failed", "codegen_fail", "no_gt"]).sum())
    n_demoted = int((last["status"] == "demoted").sum())

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Unique stems tried", total)
    c2.metric("Verified", n_verified)
    c3.metric("Near miss", n_near_miss)
    c4.metric("Failed", n_failed)
    c5.metric("Demoted", n_demoted)

    st.progress(
        n_verified / total if total else 0,
        text=f"Verified: {n_verified:,} / {total:,}  ({100*n_verified/total:.1f}%)",
    )
    if f360_total:
        pct2 = total / f360_total
        st.progress(
            min(pct2, 1.0),
            text=f"F360 stems attempted: {total:,} / {f360_total:,}  ({100*pct2:.1f}%)",
        )

    col_l, col_r = st.columns(2)
    with col_l:
        st.caption("Verified by pipeline_run (top 15)")
        v_runs = (
            vdf["pipeline_run"]
            .value_counts()
            .head(15)
            .rename_axis("run")
            .reset_index(name="count")
        )
        st.bar_chart(v_runs.set_index("run")["count"])
    with col_r:
        failed_all = last[last["status"].isin(["failed", "near_miss"])]
        if "failure_code" in failed_all.columns:
            st.caption("Failure codes")
            fc = (
                failed_all["failure_code"]
                .fillna("")
                .replace("", "unlabeled")
                .value_counts()
                .rename_axis("code")
                .reset_index(name="count")
            )
            st.bar_chart(fc.set_index("code")["count"])

    st.divider()

    # ── Section 3: Near-miss / fixable failures ───────────────────────────────
    st.subheader("Near miss — fix candidates")
    nm = last[last["status"] == "near_miss"].copy()
    if nm.empty:
        st.info("No near_miss stems.")
    else:
        nm["iou"] = pd.to_numeric(nm["iou"], errors="coerce")
        cols = [
            c
            for c in ["stem", "iou", "pipeline_run", "failure_code"]
            if c in nm.columns
        ]
        show_df(
            nm[cols].sort_values("iou", ascending=False).reset_index(drop=True),
            use_container_width=True,
        )


# ── stem viewer page ──────────────────────────────────────────────────────────


def badge(text: str, color: str) -> str:
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:12px">{text}</span>'


def norm_badges(has_norm_step: bool, has_norm_cq: bool) -> str:
    b1 = (
        badge("GT norm ✓", "#2196F3")
        if has_norm_step
        else badge("GT norm ✗", "#9E9E9E")
    )
    b2 = badge("CQ norm ✓", "#2196F3") if has_norm_cq else badge("CQ norm ✗", "#9E9E9E")
    return b1 + " " + b2


def show_image(path: str | None, caption: str = ""):
    p = _s(path)
    if p and Path(p).exists():
        st.image(p, caption=caption, use_container_width=True)
    else:
        st.markdown(
            '<div style="height:160px;background:#f0f0f0;display:flex;align-items:center;justify-content:center;color:#888">no image</div>',
            unsafe_allow_html=True,
        )


def _find_composite(row: dict) -> str | None:
    """Find gen composite image: DB field → stem-centric FS → legacy fallback."""
    stem = row["stem"]
    base = _strip_suffix(stem)
    run = _s(row.get("pipeline_run")) or _s(row.get("run")) or _s(row.get("source"))
    status = _s(row.get("status"))

    candidates = []

    # 1. DB field gen_views_norm_dir
    gvn = _s(row.get("gen_views_norm_dir"))
    if gvn:
        candidates.append(Path(gvn) / "composite.png")

    # 2. new stem-centric FS
    if run:
        run_folder = (
            f"verified_{run}" if status in ("verified", "manually_fixed") else run
        )
        candidates.append(STEM_FS / base / run_folder / "views" / "composite.png")

    return next((str(p) for p in candidates if p.exists()), None)


def _render_dir_for(row: dict) -> Path:
    stem = row["stem"]
    base = _strip_suffix(stem)
    run = _s(row.get("pipeline_run")) or _s(row.get("run")) or _s(row.get("source"))
    status = _s(row.get("status"))
    if run:
        run_folder = (
            f"verified_{run}" if status in ("verified", "manually_fixed") else run
        )
        return STEM_FS / base / run_folder / "views"
    return STEM_FS / base / "views"


def do_render(row: dict) -> tuple[str | None, str | None]:
    out_dir = _render_dir_for(row)
    gen_step = _s(row.get("gen_step_path"))
    cq_path = _s(row.get("cq_code_path"))

    if gen_step and Path(gen_step).exists():
        from render_normalized_views import render_step_normalized

        try:
            paths = render_step_normalized(gen_step, str(out_dir))
            return paths["composite"], None
        except Exception as e:
            return None, str(e)
    elif cq_path and Path(cq_path).exists():
        from render import render_cq

        return render_cq(cq_path, str(out_dir))
    return None, "no gen_step_path or cq_code_path on disk"


def show_version_card(row: dict, vdf, is_verified: bool, show_paths: bool = False):
    stem = row["stem"]
    iou = row.get("iou") or 0
    try:
        iou = float(iou)
    except:
        iou = 0.0
    status = _s(row.get("status"))
    run = _s(row.get("pipeline_run")) or _s(row.get("run")) or _s(row.get("source"))
    cq = _s(row.get("cq_code_path"))
    fc = _s(row.get("failure_code"))
    rr = _s(row.get("retry_reason"))

    vrow = vdf[vdf["stem"] == stem]
    has_norm_step = not vrow.empty and bool(
        _s(vrow.iloc[0].get("gt_norm_step_path", ""))
    )
    has_norm_cq = not vrow.empty and bool(_s(vrow.iloc[0].get("norm_cq_code_path", "")))

    name_color = "#4CAF50" if is_verified else ("#FF9800" if iou >= 0.9 else "#F44336")
    iou_str = f"{iou:.4f}" if iou else "—"

    st.markdown(
        f'<b style="color:{name_color}">{stem}</b> &nbsp; IoU: <b>{iou_str}</b> &nbsp; '
        f'{badge(status, "#4CAF50" if is_verified else "#607D8B")} &nbsp; '
        f'<span style="font-size:12px;color:#888">{run}</span>',
        unsafe_allow_html=True,
    )
    st.markdown(norm_badges(has_norm_step, has_norm_cq), unsafe_allow_html=True)

    card_key = f"{stem}__{run}"
    gen_composite = _find_composite(row)
    gen_step = _s(row.get("gen_step_path"))

    col_img, col_info = st.columns([1, 1])
    with col_img:
        if gen_composite:
            show_image(gen_composite, f"generated ({run})")
            if show_paths:
                st.caption(f"`{gen_composite}`")
            if st.button("↺ Re-render", key=f"rerender_{card_key}"):
                with st.spinner("rendering..."):
                    composite, err = do_render(row)
                if err:
                    st.error(f"render failed: {err[:300]}")
                else:
                    st.rerun()
        elif (
            status not in ("verified", "manually_fixed")
            and "exec" in rr
            and not (gen_step and Path(gen_step).exists())
        ):
            st.warning("⚠️ exec failed — no valid STEP on disk")
        elif (cq and Path(cq).exists()) or (gen_step and Path(gen_step).exists()):
            if st.button("▶ Render", key=f"render_{card_key}"):
                with st.spinner("rendering..."):
                    composite, err = do_render(row)
                if err:
                    st.error(f"render failed: {err[:300]}")
                else:
                    st.rerun()
        else:
            st.caption("no gen_step or CQ file on disk")

    with col_info:
        if fc:
            st.markdown(f"**failure_code:** `{fc}`")
        if rr:
            st.markdown(f"**retry_reason:** `{rr}`")
        if cq and Path(cq).exists():
            with st.expander("view code"):
                st.code(Path(cq).read_text(), language="python")
        elif cq:
            st.caption(f"file missing: `{cq}`")

    st.divider()


def _render_gt(base: str, vdf) -> None:
    import glob

    out_dir = STEM_FS / base / "gt" / "views"
    out_dir.mkdir(parents=True, exist_ok=True)

    vrow = vdf[vdf["stem"].str.startswith(base + "_") | (vdf["stem"] == base)]
    step = ""
    if not vrow.empty:
        step = _s(vrow.iloc[0].get("gt_step_path"))
    if not step or not Path(step).exists():
        hits = sorted(
            glob.glob(
                str(
                    ROOT
                    / "data/data_generation/open_source/fusion360_gallery/raw/r1.0.1_extrude_tools/extrude_tools"
                    / f"{base}_*.step"
                )
            )
        )
        if hits:
            step = hits[0]

    if not step:
        st.warning(f"No GT STEP found for {base}")
        return

    from render_normalized_views import render_step_normalized

    try:
        render_step_normalized(step, str(out_dir))
    except Exception as e:
        st.error(f"GT render failed: {e}")


def search_stems(query: str, vdf, pdf) -> list[str]:
    q = query.strip()
    if not q:
        return []
    v_stems = set(vdf[vdf["stem"].str.contains(q, case=False, na=False)]["stem"])
    p_stems = set(pdf[pdf["stem"].str.contains(q, case=False, na=False)]["stem"])
    return sorted(v_stems | p_stems)


def page_stem_viewer():
    st.title("Stem Viewer")
    vdf, pdf = load_data()

    with st.sidebar:
        show_paths = st.checkbox("Show image paths", value=False, key="show_paths")

    # Pre-fill from Stem List click (set key state once, then widget owns it)
    if "viewer_query" in st.session_state:
        st.session_state["_viewer_input"] = st.session_state.pop("viewer_query")
    query = st.text_input(
        "Stem (prefix or exact)", key="_viewer_input", placeholder="e.g. 25338_b3f9f319"
    )
    if not query:
        st.caption("Enter a stem prefix to search")
        return

    matches = search_stems(query, vdf, pdf)
    if not matches:
        st.warning("No stems found.")
        return

    with st.sidebar:
        st.markdown("### Matching stems")
        for s in matches:
            is_v = s in set(vdf["stem"])
            color = "#4CAF50" if is_v else "#9E9E9E"
            st.markdown(
                f'<span style="color:{color}">{"✓" if is_v else "○"} {s}</span>',
                unsafe_allow_html=True,
            )

    groups: dict[str, list[str]] = {}
    for s in matches:
        b = _strip_suffix(s)
        groups.setdefault(b, []).append(s)

    for b, stems in groups.items():
        st.header(f"📦 {b}")

        # GT image from new stem-centric FS
        gt_img_path = None
        gt_views_dir = STEM_FS / b / "gt" / "views"
        for name in ("composite.png", "raw_composite.png"):
            if (gt_views_dir / name).exists():
                gt_img_path = str(gt_views_dir / name)
                break
        # Fallback: DB field
        if not gt_img_path:
            vrow_base = vdf[vdf["stem"].str.startswith(b)]
            if not vrow_base.empty:
                gvd = _s(vrow_base.iloc[0].get("gt_views_norm_dir", ""))
                if gvd and Path(gvd + "/composite.png").exists():
                    gt_img_path = gvd + "/composite.png"

        gt_col, info_col = st.columns([1, 2])
        with gt_col:
            show_image(gt_img_path, "GT")
            if show_paths and gt_img_path:
                st.caption(f"`{gt_img_path}`")
            if st.button("↺ Re-render GT", key=f"gt_render_{b}"):
                with st.spinner("rendering GT..."):
                    _render_gt(b, vdf)
                st.rerun()

        with info_col:
            for s in sorted(stems):
                is_v = s in set(vdf["stem"])
                color = "#4CAF50" if is_v else "#9E9E9E"
                label = (
                    "verified"
                    if is_v
                    else ("manually_fixed" if "claude_fixed" in s else "")
                )
                st.markdown(
                    f'<span style="color:{color};font-weight:bold">{s}</span>'
                    + (
                        f' <span style="background:#4CAF50;color:white;padding:1px 6px;border-radius:3px;font-size:11px">{label}</span>'
                        if label
                        else ""
                    ),
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        st.subheader("Generated versions")

        stem_set = set(stems)
        parts_rows = pdf[pdf["stem"].isin(stem_set)].sort_values("iou", ascending=False)
        run_col = "pipeline_run" if "pipeline_run" in parts_rows.columns else None
        parts_rows = parts_rows.drop_duplicates(
            subset=["stem", run_col] if run_col else ["stem"]
        )

        if parts_rows.empty:
            for s in stems:
                vrow = vdf[vdf["stem"] == s]
                if not vrow.empty:
                    r = vrow.iloc[0].to_dict()
                    r["status"] = "verified"
                    show_version_card(r, vdf, is_verified=True, show_paths=show_paths)
        else:
            verified_stems = set(vdf["stem"])
            for _, row in parts_rows.iterrows():
                is_v = row["stem"] in verified_stems
                r = row.to_dict()
                if is_v:
                    vrow = vdf[vdf["stem"] == row["stem"]]
                    if not vrow.empty:
                        for col in vrow.columns:
                            if not _s(r.get(col)):
                                r[col] = vrow.iloc[0][col]
                show_version_card(r, vdf, is_verified=is_v, show_paths=show_paths)


# ── stem list page ────────────────────────────────────────────────────────────


def _go_viewer(stem: str):
    st.session_state["viewer_query"] = stem
    st.session_state["_nav_pending"] = "Stem Viewer"
    st.rerun()


def page_stem_list():
    st.title("Verified Stems")
    vdf, _ = load_data()

    # Filters
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        sft_filter = st.multiselect("sft_ready", ["True", "False", "skip"], default=[])
    with col2:
        src_filter = st.multiselect(
            "data_source",
            sorted(vdf["data_source"].dropna().unique().tolist()),
            default=[],
        )
    with col3:
        search = st.text_input("Stem contains", "")
    with col4:
        sort_by = st.selectbox("Sort by", ["Newest first", "SFT priority", "IoU desc"])

    df = vdf.copy()
    if sft_filter:
        df = df[df["sft_ready"].astype(str).isin(sft_filter)]
    if src_filter:
        df = df[df["data_source"].isin(src_filter)]
    if search:
        df = df[df["stem"].str.contains(search, case=False, na=False)]

    if sort_by == "Newest first":
        if "timestamp" in df.columns:
            df = df.sort_values("timestamp", ascending=False, na_position="last")
        df = df.reset_index(drop=True)
    elif sort_by == "SFT priority":
        df["_sort_sft"] = (
            df["sft_ready"]
            .astype(str)
            .map(lambda x: 0 if x == "False" else (1 if x == "True" else 2))
        )
        df = df.sort_values(["_sort_sft", "iou"], ascending=[True, False]).drop(
            columns=["_sort_sft"]
        )
        df = df.reset_index(drop=True)
    else:  # IoU desc
        df = df.sort_values("iou", ascending=False).reset_index(drop=True)

    PAGE_SIZE = 100
    total = len(df)
    n_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page_num = (
        st.number_input(
            f"Page (1–{n_pages})", min_value=1, max_value=n_pages, value=1, step=1
        )
        - 1
    )
    start = page_num * PAGE_SIZE
    page_df = df.iloc[start : start + PAGE_SIZE]

    st.caption(
        f"{total} stems total · page {page_num+1}/{n_pages} · rows {start+1}–{min(start+PAGE_SIZE, total)}"
    )

    # Header row
    h0, h1, h2, h3, h4, h5, h6 = st.columns([0.5, 3, 0.7, 0.8, 0.8, 1.5, 1.5])
    h0.markdown("**View**")
    h1.markdown("**Stem**")
    h2.markdown("**SFT**")
    h3.markdown("**IoU**")
    h4.markdown("**normIoU**")
    h5.markdown("**run**")
    h6.markdown("**time**")

    has_ts = "timestamp" in df.columns
    for _, row in page_df.iterrows():
        stem = row["stem"]
        sft = str(row.get("sft_ready", ""))
        iou = row.get("iou", 0)
        niou = row.get("norm_iou", None)
        run = str(row.get("pipeline_run", ""))[:20]
        sft_color = (
            "#4CAF50" if sft == "True" else ("#9E9E9E" if sft == "skip" else "#F44336")
        )
        ts_raw = row.get("timestamp", "") if has_ts else ""
        ts_str = str(ts_raw)[:16] if ts_raw and str(ts_raw) not in ("nan", "") else "—"

        c0, c1, c2, c3, c4, c5, c6 = st.columns([0.5, 3, 0.7, 0.8, 0.8, 1.5, 1.5])
        if c0.button("▶", key=f"view_{stem}", help=stem):
            _go_viewer(stem)
        c1.markdown(
            f'<span style="font-size:12px">{stem}</span>', unsafe_allow_html=True
        )
        c2.markdown(
            f'<span style="color:{sft_color};font-size:12px">{sft}</span>',
            unsafe_allow_html=True,
        )
        c3.markdown(
            f'<span style="font-size:12px">{iou:.4f}</span>', unsafe_allow_html=True
        )
        niou_str = f"{niou:.4f}" if niou and niou == niou else "—"
        c4.markdown(
            f'<span style="font-size:12px">{niou_str}</span>', unsafe_allow_html=True
        )
        c5.markdown(
            f'<span style="font-size:12px;color:#888">{run}</span>',
            unsafe_allow_html=True,
        )
        c6.markdown(
            f'<span style="font-size:11px;color:#888">{ts_str}</span>',
            unsafe_allow_html=True,
        )

    # Stats
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("sft_ready=True", int((vdf["sft_ready"] == "True").sum()))
    c2.metric("sft_ready=False", int((vdf["sft_ready"] == "False").sum()))
    c3.metric("sft_ready=skip", int((vdf["sft_ready"] == "skip").sum()))


_FAMILY_COLOR = {
    "mounting_plate": "#2196F3",
    "round_flange": "#4CAF50",
    "l_bracket": "#FF9800",
    "enclosure": "#9C27B0",
    "vented_panel": "#00BCD4",
}
_DIFF_COLOR = {"easy": "#66BB6A", "medium": "#FFA726", "hard": "#EF5350"}


def _iso_badge(std: str | None) -> str:
    if not std or str(std).strip() in ("", "N/A", "None", "nan"):
        return ""
    return (
        f'<span style="background:#1565C0;color:#E3F2FD;padding:1px 6px;'
        f'border-radius:8px;font-size:10px;font-weight:bold">{std}</span>'
    )


def _badge(label: str, color: str) -> str:
    return (
        f'<span style="background:{color};color:white;padding:2px 8px;'
        f'border-radius:10px;font-size:11px;font-weight:bold">{label}</span>'
    )


def _tag_pills(tags: dict) -> str:
    active = [k.replace("has_", "") for k, v in tags.items() if v]
    if not active:
        return '<span style="color:#888;font-size:11px">—</span>'
    return " ".join(
        f'<span style="background:#424242;color:#eee;padding:1px 6px;'
        f'border-radius:8px;font-size:10px">{t}</span>'
        for t in active
    )


_RENDER_NAMES = (
    "view_3.png",
    "composite.png",
    "raw_composite.png",
    "raw_iso.png",
    "view_0.png",
    "raw_front.png",
)


def _render_img(row) -> Path | None:
    """Return path to the isometric render image for a synth row."""
    # 1. render_dir column → check all known render filenames
    rd = _s(row.get("render_dir", ""))
    if rd:
        views_dir = ROOT / rd
        for name in _RENDER_NAMES:
            p = views_dir / name
            if p.exists():
                return p

    # 2. fallback: old render_N.png in same dir as code
    code_p = _s(row.get("code_path", ""))
    if code_p:
        sample_dir = ROOT / Path(code_p).parent
        for name in ("render_3.png", "render_0.png"):
            p = sample_dir / name
            if p.exists():
                return p
        for name in _RENDER_NAMES:
            p = sample_dir / "views" / name
            if p.exists():
                return p

    return None


def page_synth():
    """Visual gallery + live progress monitor for synthetic data batches."""
    st.title("Synth Data Monitor")

    sdf = load_synth()
    if sdf.empty:
        st.info(
            "synth_parts.csv not found or empty.  Start a batch run:\n\n"
            "```bash\ncd scripts/data_generation\n"
            "python3 -m cad_synth.pipeline.runner --config cad_synth/configs/batch_medium.yaml\n```"
        )
        return

    # ── Run selector + refresh ─────────────────────────────────────────────
    runs = sorted(sdf["pipeline_run"].dropna().unique().tolist(), reverse=True)
    rc1, rc2 = st.columns([4, 1])
    run_sel = rc1.selectbox("Run", ["(all)"] + runs)
    if rc2.button("↺ Refresh"):
        st.cache_data.clear()
        st.rerun()

    df = sdf if run_sel == "(all)" else sdf[sdf["pipeline_run"] == run_sel]
    acc = df[df["status"] == "accepted"]
    rej = df[df["status"] != "accepted"]
    total = len(df)
    n_acc = len(acc)

    # ── Top metrics ────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Samples", total)
    m2.metric("Accepted", n_acc)
    m3.metric("Rejected", len(rej))
    m4.metric("Accept rate", f"{n_acc/total*100:.1f}%" if total else "—")
    if "created_at" in df.columns:
        latest = df["created_at"].max()
        m5.metric(
            "Last update", str(latest)[:16] if latest and str(latest) != "nan" else "—"
        )

    st.progress(n_acc / max(total, 1))

    # ── Distribution mini-tables ───────────────────────────────────────────
    d1, d2, d3 = st.columns(3)
    with d1:
        st.caption("**Family**")
        fc = acc["family"].value_counts().reset_index()
        fc.columns = ["family", "n"]
        fam_std = (
            acc.dropna(subset=["standard"])
            .drop_duplicates("family")
            .set_index("family")["standard"]
            if "standard" in acc.columns
            else {}
        )
        fc["ISO/DIN"] = fc["family"].map(
            lambda f: "" if (s := fam_std.get(f, "")) in ("N/A", "None", None) else s
        )
        show_df(fc, use_container_width=True, hide_index=True, height=200)
    with d2:
        st.caption("**Difficulty**")
        dc = acc["difficulty"].value_counts().reset_index()
        dc.columns = ["difficulty", "n"]
        show_df(dc, use_container_width=True, hide_index=True, height=200)
    with d3:
        st.caption("**Rejections**")
        if len(rej):
            rc_df = rej["reject_reason"].value_counts().reset_index()
            rc_df.columns = ["reason", "n"]
            show_df(rc_df, use_container_width=True, hide_index=True, height=200)
        else:
            st.success("No rejections")

    st.divider()

    # ── Gallery filters ────────────────────────────────────────────────────
    f1, f2, f3, f4, f5, f6, f7 = st.columns(7)
    fam_opts = sorted(acc["family"].dropna().unique().tolist())
    diff_opts = sorted(acc["difficulty"].dropna().unique().tolist())
    bp_opts = (
        sorted(acc["base_plane"].dropna().unique().tolist())
        if "base_plane" in acc.columns
        else []
    )
    fam_sel = f1.multiselect("Family", fam_opts, default=[])
    diff_sel = f2.multiselect("Difficulty", diff_opts, default=[])
    bp_sel = f3.multiselect("Base plane", bp_opts, default=[])
    tag_sel = f4.text_input("Feature tag contains", "")
    gid_sel = f5.text_input("GID", "", placeholder="e.g. 12811")
    sort_sel = f6.selectbox("Show", ["Newest first", "Oldest first"])
    # is_preflight filter: default hides test/smoke runs
    pf_opts = ["all", "production only", "preflight only"]
    pf_sel = f7.selectbox("Source", pf_opts, index=0)

    gdf = acc.copy()
    if gid_sel.strip():
        try:
            gid_val = int(gid_sel.strip())
            gdf = gdf[gdf["gid"] == gid_val]
        except ValueError:
            st.warning("GID must be an integer")
    if fam_sel:
        gdf = gdf[gdf["family"].isin(fam_sel)]
    if bp_sel and "base_plane" in gdf.columns:
        gdf = gdf[gdf["base_plane"].isin(bp_sel)]
    if diff_sel:
        gdf = gdf[gdf["difficulty"].isin(diff_sel)]
    if tag_sel and "feature_tags" in gdf.columns:
        gdf = gdf[gdf["feature_tags"].str.contains(tag_sel, case=False, na=False)]
    if "sample_type" in gdf.columns:
        if pf_sel == "production only":
            gdf = gdf[gdf["sample_type"] == "production"]
        elif pf_sel == "preflight only":
            gdf = gdf[gdf["sample_type"] == "test"]

    # ── Upload-filter blocklist toggle ─────────────────────────────────────
    block = load_blocklist()
    if run_sel != "(all)":
        block = block[block["pipeline_run"] == run_sel]
    block_map = dict(zip(block["stem"], block["reason"])) if len(block) else {}
    if block_map:
        b1, b2 = st.columns([3, 1])
        up_only = b1.checkbox(
            f"Upload-ready only — hide {len(block_map)} filter-blocked stems",
            value=True,
            help="Hides stems dropped by the HF upload filter "
            "(status!=accepted, missing files, code.py exec fails).",
        )
        show_reasons = b2.checkbox("Show block reason on cards", value=False)
        if up_only:
            gdf = gdf[~gdf["stem"].isin(block_map)]
    else:
        up_only, show_reasons = False, False

    if "created_at" in gdf.columns:
        gdf = gdf.sort_values("created_at", ascending=(sort_sel == "Oldest first"))
    gdf = gdf.reset_index(drop=True)

    # ── Pagination ─────────────────────────────────────────────────────────
    GRID_COLS = 3
    PAGE_CARDS = 100
    n_total = len(gdf)
    n_pages = max(1, (n_total + PAGE_CARDS - 1) // PAGE_CARDS)
    pg = st.number_input(f"Page (1–{n_pages})", 1, n_pages, 1, key="synth_page") - 1
    page_rows = gdf.iloc[pg * PAGE_CARDS : (pg + 1) * PAGE_CARDS]

    st.caption(f"{n_total} accepted samples · page {pg+1}/{n_pages}")

    # ── Gallery grid ───────────────────────────────────────────────────────
    rows_iter = [
        page_rows.iloc[i : i + GRID_COLS] for i in range(0, len(page_rows), GRID_COLS)
    ]
    for chunk in rows_iter:
        cols = st.columns(GRID_COLS)
        for col, (_, row) in zip(cols, chunk.iterrows()):
            family = _s(row.get("family", ""))
            diff = _s(row.get("difficulty", ""))
            bp = _s(row.get("base_plane", ""))
            stem = _s(row.get("stem", ""))
            gid = _s(row.get("gid", ""))
            sample_id = _s(row.get("sample_id", ""))
            ops_raw = _s(row.get("ops_used", "[]"))
            tags_raw = _s(row.get("feature_tags", "{}"))
            params_raw = _s(row.get("params_json", "{}"))
            code_path = _s(row.get("code_path", ""))
            created = str(row.get("created_at", ""))[:16]

            try:
                import json as _json

                ops_list = _json.loads(ops_raw) if ops_raw else []
                tags_dict = _json.loads(tags_raw) if tags_raw else {}
                params_dict = _json.loads(params_raw) if params_raw else {}
            except Exception:
                ops_list, tags_dict, params_dict = [], {}, {}

            fam_color = _FAMILY_COLOR.get(family, "#607D8B")
            diff_color = _DIFF_COLOR.get(diff, "#9E9E9E")
            img_path = _render_img(row)

            with col:
                # Render image
                if img_path:
                    st.image(str(img_path), use_container_width=True)
                else:
                    st.markdown(
                        '<div style="height:160px;background:#2a2a2a;border-radius:6px;'
                        "display:flex;align-items:center;justify-content:center;"
                        'color:#666">no render</div>',
                        unsafe_allow_html=True,
                    )

                # Badges + stem
                iso_b = _iso_badge(_s(row.get("standard", "")))
                bp_badge = (
                    f'<span style="background:#37474F;color:#CFD8DC;padding:1px 5px;'
                    f'border-radius:8px;font-size:10px">{bp}</span>'
                    if bp
                    else ""
                )
                block_reason = block_map.get(stem, "")
                block_b = (
                    f' {_badge("BLOCKED: " + block_reason, "#C62828")}'
                    if block_reason and show_reasons
                    else ""
                )
                st.markdown(
                    f"{_badge(family, fam_color)} {_badge(diff, diff_color)}"
                    + (f" {iso_b}" if iso_b else "")
                    + (f" {bp_badge}" if bp_badge else "")
                    + block_b
                    + f'<br><span style="font-size:10px;color:#888">#{gid} · {sample_id} · {created}</span>',
                    unsafe_allow_html=True,
                )

                # Feature tags
                st.markdown(_tag_pills(tags_dict), unsafe_allow_html=True)

                # Ops count + key params
                ops_unique = list(dict.fromkeys(ops_list))
                st.markdown(
                    f'<span style="font-size:11px;color:#aaa">'
                    f'ops: {", ".join(ops_unique[:5])}{"…" if len(ops_unique)>5 else ""}</span>',
                    unsafe_allow_html=True,
                )

                # Expandable detail: all 4 renders + code + params
                with st.expander("Details"):
                    # 4 renders in 2x2 — check render_dir first, then old render_N.png
                    rd = _s(row.get("render_dir", ""))
                    views_dir = ROOT / rd if rd else None
                    if code_path and not rd:
                        views_dir = ROOT / Path(code_path).parent / "views"
                    _view_sets = [
                        ["view_0.png", "view_1.png", "view_2.png", "view_3.png"],
                        [
                            "raw_front.png",
                            "raw_right.png",
                            "raw_top.png",
                            "raw_iso.png",
                        ],
                        [
                            "render_0.png",
                            "render_1.png",
                            "render_2.png",
                            "render_3.png",
                        ],
                    ]
                    labels = ["front", "right", "top", "iso"]
                    existing = []
                    if views_dir and views_dir.exists():
                        for vset in _view_sets:
                            cands = [views_dir / n for n in vset]
                            hits = [p for p in cands if p.exists()]
                            if hits:
                                existing = hits
                                break
                    if not existing and code_path:
                        sample_dir = ROOT / Path(code_path).parent
                        for vset in _view_sets:
                            hits = [
                                sample_dir / n
                                for n in vset
                                if (sample_dir / n).exists()
                            ]
                            if hits:
                                existing = hits
                                break
                    if existing:
                        r_cols = st.columns(min(len(existing), 4))
                        for rc, rp, lb in zip(r_cols, existing, labels):
                            rc.image(str(rp), caption=lb, use_container_width=True)

                    # Params table
                    if params_dict:
                        st.caption("**Params**")
                        p_rows = [
                            {
                                "param": k,
                                "value": (
                                    repr(v) if isinstance(v, (list, tuple, dict)) else v
                                ),
                            }
                            for k, v in params_dict.items()
                            if k != "difficulty"
                        ]
                        show_df(
                            pd.DataFrame(p_rows),
                            hide_index=True,
                            use_container_width=True,
                            height=min(200, len(p_rows) * 38 + 38),
                        )

                    # Feature tags detail
                    if tags_dict:
                        st.caption("**Feature tags**")
                        t_rows = [
                            {"tag": k, "value": "✓" if v else "✗"}
                            for k, v in tags_dict.items()
                        ]
                        show_df(
                            pd.DataFrame(t_rows),
                            hide_index=True,
                            use_container_width=True,
                            height=min(200, len(t_rows) * 38 + 38),
                        )

                    # CadQuery code
                    if code_path and (ROOT / code_path).exists():
                        st.caption("**Code**")
                        code_text = (ROOT / code_path).read_text()
                        st.code(code_text, language="python")

                st.markdown("---")


# ── code edit bench page (interactive review) ────────────────────────────────

BENCH_EDIT = ROOT / "data" / "data_generation" / "bench_edit"
EDIT_SOURCES = {
    "pairs_curated": (BENCH_EDIT / "pairs_curated.jsonl", BENCH_EDIT),
    "topup_final": (
        BENCH_EDIT / "topup_final" / "records.jsonl",
        BENCH_EDIT / "topup_final",
    ),
    # `from_hf` 由 `bench/fetch_data.py` 解包,fresh clone 跑一次即可直读
    "from_hf": (
        BENCH_EDIT / "from_hf" / "records.jsonl",
        BENCH_EDIT / "from_hf",
    ),
}
EDIT_CACHE = ROOT / "bench" / "ui" / "edit_cache"


def _eb_load_jsonl(p: Path):
    import json

    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]


def _eb_write_jsonl(p: Path, rows: list):
    import json
    import shutil
    from datetime import datetime

    if p.exists():
        bak = p.with_suffix(p.suffix + f".bak_{datetime.now():%Y%m%d_%H%M%S}")
        shutil.copy2(p, bak)
    with p.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _eb_iou(rec):
    return rec.get("iou") if rec.get("iou") is not None else rec.get("iou_orig_gt")


def _eb_render_step(
    step_abs: Path, cache_png: Path, size: int = 320, timeout: int = 120
) -> tuple[bool, str]:
    if cache_png.exists():
        return True, ""
    if not step_abs.exists():
        return False, f"STEP not found: {step_abs}"
    import os
    import shutil as _sh
    import subprocess
    import tempfile

    code = (
        "import sys\n"
        "from scripts.data_generation.render_normalized_views import render_step_normalized\n"
        "r = render_step_normalized(sys.argv[1], sys.argv[2], size=int(sys.argv[3]))\n"
        "print(r['composite'])\n"
    )
    td = tempfile.mkdtemp(prefix="editbench_")
    env = {**os.environ, "LD_LIBRARY_PATH": "/workspace/.local/lib"}
    try:
        r = subprocess.run(
            [sys.executable, "-c", code, str(step_abs), td, str(size)],
            env=env,
            timeout=timeout,
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        if r.returncode != 0:
            return False, (r.stderr or r.stdout)[-500:]
        out = r.stdout.strip().splitlines()
        if not out:
            return False, "no output"
        cache_png.parent.mkdir(parents=True, exist_ok=True)
        _sh.copy2(out[-1], cache_png)
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "timeout"
    finally:
        import shutil as _sh2

        _sh2.rmtree(td, ignore_errors=True)


def _eb_render_code(
    code_text: str, size: int = 320, timeout: int = 120
) -> tuple[Path | None, str]:
    import os
    import subprocess
    import tempfile

    code_file = Path(tempfile.mktemp(suffix=".py"))
    code_file.write_text(code_text)
    out_dir = Path(tempfile.mkdtemp(prefix="editbench_render_"))
    env = {**os.environ, "LD_LIBRARY_PATH": "/workspace/.local/lib"}
    try:
        r = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/data_generation/render_cq_file.py"),
                "--code",
                str(code_file),
                "--out",
                str(out_dir),
                "--size",
                str(size),
                "--timeout",
                str(timeout),
            ],
            env=env,
            timeout=timeout + 20,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            return None, (r.stderr or r.stdout)[-2000:]
        comp = out_dir / "composite.png"
        return (comp if comp.exists() else None), ""
    except subprocess.TimeoutExpired:
        return None, "timeout"
    finally:
        code_file.unlink(missing_ok=True)


def _eb_orig_code_path(rec, base_dir: Path) -> Path | None:
    p = rec.get("original_code_path") or rec.get("orig_code_path")
    return (base_dir / p) if p else None


def _eb_sanitize(name: str) -> str:
    import re

    return re.sub(r"[^A-Za-z0-9_\-]", "_", name)[:60]


def _eb_shared_count(recs, field, value) -> int:
    return sum(1 for r in recs if r.get(field) == value)


def _eb_unique_path(p: Path, tag: str) -> Path:
    return p.with_name(f"{p.stem}__{tag}{p.suffix}")


def _eb_save_gt_code(
    rec, recs, rec_idx, new_code: str, base_dir: Path, jsonl_path: Path
) -> tuple[bool, str]:
    """Render edited code → STEP, auto-unshare shared gt_code_path / gt_step_path,
    then rewrite JSONL. Returns (ok, message)."""
    import os
    import shutil as _sh
    import subprocess
    import tempfile

    tag = _eb_sanitize(rec["record_id"])
    code_rel = rec["gt_code_path"]
    step_rel = rec["gt_step_path"]
    code_abs = base_dir / code_rel
    step_abs = base_dir / step_rel

    tmp_code = Path(tempfile.mktemp(suffix=".py"))
    tmp_code.write_text(new_code)
    out_dir = Path(tempfile.mkdtemp(prefix="eb_save_"))
    env = {**os.environ, "LD_LIBRARY_PATH": "/workspace/.local/lib"}
    try:
        r = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/data_generation/render_cq_file.py"),
                "--code",
                str(tmp_code),
                "--out",
                str(out_dir),
                "--size",
                "320",
                "--timeout",
                "120",
                "--keep-step",
            ],
            env=env,
            timeout=140,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        tmp_code.unlink(missing_ok=True)
        _sh.rmtree(out_dir, ignore_errors=True)
        return False, "渲染超时"
    tmp_code.unlink(missing_ok=True)

    if r.returncode != 0:
        _sh.rmtree(out_dir, ignore_errors=True)
        return False, (r.stderr or r.stdout)[-1200:]
    new_step = next(out_dir.glob("*.step"), None)
    if new_step is None:
        _sh.rmtree(out_dir, ignore_errors=True)
        return False, "STEP 未导出"

    code_shared = _eb_shared_count(recs, "gt_code_path", code_rel) > 1
    step_shared = _eb_shared_count(recs, "gt_step_path", step_rel) > 1
    final_code = _eb_unique_path(code_abs, tag) if code_shared else code_abs
    final_step = _eb_unique_path(step_abs, tag) if step_shared else step_abs

    final_code.parent.mkdir(parents=True, exist_ok=True)
    final_step.parent.mkdir(parents=True, exist_ok=True)
    final_code.write_text(new_code)
    _sh.copy2(new_step, final_step)
    _sh.rmtree(out_dir, ignore_errors=True)

    recs[rec_idx]["gt_code_path"] = str(final_code.relative_to(base_dir))
    recs[rec_idx]["gt_step_path"] = str(final_step.relative_to(base_dir))
    _eb_write_jsonl(jsonl_path, recs)
    msg = []
    msg.append(f"{'解除共用，' if code_shared else ''}代码 → {final_code.name}")
    msg.append(f"{'解除共用，' if step_shared else ''}STEP → {final_step.name}")
    return True, "  ·  ".join(msg)


def page_edit_bench():
    st.title("代码编辑 Bench — 交互式审查")

    with st.sidebar:
        src_key = st.selectbox("数据源", list(EDIT_SOURCES.keys()), key="eb_source")
    jsonl_path, base_dir = EDIT_SOURCES[src_key]

    recs = _eb_load_jsonl(jsonl_path)
    if not recs:
        st.error(f"{jsonl_path} 无记录")
        return

    n = len(recs)

    # 用 position(int) 作为唯一导航 key —— record_id 不一定唯一（有重复会卡住）
    pending_key = f"_eb_pending_pos_{src_key}"
    if pending_key in st.session_state:
        p = st.session_state.pop(pending_key)
        if isinstance(p, int) and 0 <= p < n:
            st.session_state["eb_pos"] = p
            st.session_state["eb_jump"] = p + 1
    # 切换数据源后，清掉无效状态
    if not isinstance(st.session_state.get("eb_pos"), int) or not (
        0 <= st.session_state.get("eb_pos", -1) < n
    ):
        st.session_state.pop("eb_pos", None)
        st.session_state.pop("eb_jump", None)
    if "eb_jump" not in st.session_state:
        st.session_state["eb_jump"] = (st.session_state.get("eb_pos") or 0) + 1

    with st.sidebar:
        fams = sorted({r.get("family", "") for r in recs})
        sel_fam = st.selectbox("Family", ["全部"] + fams, key="eb_fam")
        types = sorted({r.get("edit_type", "") for r in recs})
        sel_type = st.selectbox("编辑类型", ["全部"] + types, key="eb_type")
        diffs = sorted({r.get("difficulty", "") for r in recs if r.get("difficulty")})
        sel_diff = st.selectbox("难度", ["全部"] + diffs, key="eb_diff")
        iou_range = st.slider("IoU 区间", 0.0, 1.0, (0.0, 1.0), 0.01, key="eb_iou")

    def _match(r):
        if sel_fam != "全部" and r.get("family") != sel_fam:
            return False
        if sel_type != "全部" and r.get("edit_type") != sel_type:
            return False
        if sel_diff != "全部" and r.get("difficulty") != sel_diff:
            return False
        iv = _eb_iou(r) or 0
        return iou_range[0] <= iv <= iou_range[1]

    filtered_pos = [i for i, r in enumerate(recs) if _match(r)]
    st.sidebar.caption(f"{len(filtered_pos)} / {n} 条（筛选后 / 全量）")

    # selectbox 选项 = 筛选位置；若当前 pos 被筛掉，临时塞进来避免报错
    cur_pos = st.session_state.get("eb_pos")
    sel_pos_options = list(filtered_pos)
    if cur_pos is not None and cur_pos not in sel_pos_options:
        sel_pos_options = [cur_pos] + sel_pos_options
    if not sel_pos_options:
        st.info("无符合筛选的记录（上一条/下一条仍可在全量中循环）")
        sel_pos_options = [cur_pos if cur_pos is not None else 0]

    def _fmt_pos(pos):
        r = recs[pos]
        iou = _eb_iou(r) or 0
        return f"#{pos + 1:>3}  {r['record_id']}  (IoU={iou:.3f})"

    sel_pos = st.sidebar.selectbox(
        "记录",
        sel_pos_options,
        format_func=_fmt_pos,
        key="eb_pos",
    )
    rec = recs[sel_pos]
    rec_idx = sel_pos
    sel_rid = rec["record_id"]
    wid = f"{sel_pos}"  # widget key 后缀（用 position 保证 record_id 重复时也唯一）

    # 上一条 / 跳转 / 下一条（按 records.jsonl 全量顺序循环）
    nav_l, nav_mid, nav_r = st.columns([1, 2, 1])
    if nav_l.button("⬅ 上一条", use_container_width=True, key="eb_prev"):
        st.session_state[pending_key] = (rec_idx - 1) % n
        st.rerun()
    with nav_mid:
        target = st.number_input(
            f"跳转到第 N 条 / 共 {n} 条（回车确认）",
            min_value=1,
            max_value=n,
            step=1,
            key="eb_jump",
            label_visibility="collapsed",
        )
        if int(target) - 1 != rec_idx:
            st.session_state[pending_key] = int(target) - 1
            st.rerun()
        st.caption(f"当前：第 **{rec_idx + 1}** / {n} 条")
    if nav_r.button("下一条 ➡", use_container_width=True, key="eb_next"):
        st.session_state[pending_key] = (rec_idx + 1) % n
        st.rerun()

    # 顶部三栏：信息 | ORI | GT
    col_info, col_ori, col_gt = st.columns([2, 3, 3])

    with col_info:
        st.markdown(f"### `{rec['record_id']}`")
        iou_val = _eb_iou(rec)
        iou_s = f"{iou_val:.3f}" if isinstance(iou_val, (float, int)) else "?"
        st.markdown(
            f"**Family**: `{rec.get('family','?')}`  ·  "
            f"**类型**: `{rec.get('edit_type','?')}`"
        )
        st.markdown(
            f"**难度**: `{rec.get('difficulty','?')}`  ·  " f"**IoU**: `{iou_s}`"
        )
        extras = []
        for k in (
            "level",
            "axis",
            "pct_delta",
            "orig_value",
            "target_value",
            "unit",
            "human_name",
            "dl_est",
        ):
            if k in rec and rec[k] not in (None, ""):
                extras.append(f"**{k}**={rec[k]}")
        if extras:
            st.caption(" · ".join(extras))
        st.divider()

        instr_key = f"eb_instr_{wid}"
        new_instr = st.text_area(
            "Prompt（指令）",
            value=rec.get("instruction", ""),
            height=130,
            key=instr_key,
        )

        b1, b2 = st.columns(2)
        if b1.button(
            "💾 保存 Prompt", use_container_width=True, key=f"eb_save_instr_{wid}"
        ):
            recs[rec_idx]["instruction"] = new_instr
            _eb_write_jsonl(jsonl_path, recs)
            st.success("已保存")
            st.rerun()

        del_flag = f"eb_confirm_del_{wid}"
        if b2.button("🗑 删除该条", use_container_width=True, key=f"eb_del_btn_{wid}"):
            st.session_state[del_flag] = True
        if st.session_state.get(del_flag):
            st.warning(f"确认从 {jsonl_path.name} 中永久删除 `{sel_rid}`？")
            cc1, cc2 = st.columns(2)
            if cc1.button(
                "确认删除",
                type="primary",
                use_container_width=True,
                key=f"eb_del_yes_{wid}",
            ):
                recs.pop(rec_idx)
                _eb_write_jsonl(jsonl_path, recs)
                st.session_state[del_flag] = False
                st.success(f"已删除 {sel_rid}")
                st.rerun()
            if cc2.button("取消", use_container_width=True, key=f"eb_del_no_{wid}"):
                st.session_state[del_flag] = False
                st.rerun()

    with col_ori:
        st.markdown("#### 原图 (ORI)")
        step_orig = base_dir / rec["orig_step_path"]
        orig_png = EDIT_CACHE / sel_rid / "orig.png"
        ok, err = _eb_render_step(step_orig, orig_png)
        if ok:
            st.image(str(orig_png), use_container_width=True)
        else:
            st.error(f"渲染失败：{err}")
        st.caption(f"`{rec['orig_step_path']}`")

    with col_gt:
        st.markdown("#### 目标 (GT)")
        step_gt = base_dir / rec["gt_step_path"]
        gt_png = EDIT_CACHE / sel_rid / "gt.png"
        ok, err = _eb_render_step(step_gt, gt_png)
        if ok:
            st.image(str(gt_png), use_container_width=True)
        else:
            st.error(f"渲染失败：{err}")
        st.caption(f"`{rec['gt_step_path']}`")

    st.divider()
    with st.expander("📝 代码（编辑 & 重渲染）", expanded=False):
        tab_gt, tab_orig = st.tabs(["GT 代码（可编辑）", "原始代码"])
        gt_code_path = base_dir / rec["gt_code_path"]
        orig_code_path = _eb_orig_code_path(rec, base_dir)

        with tab_gt:
            st.caption(f"`{rec['gt_code_path']}`")
            code_shared = _eb_shared_count(recs, "gt_code_path", rec["gt_code_path"])
            step_shared = _eb_shared_count(recs, "gt_step_path", rec["gt_step_path"])
            if code_shared > 1 or step_shared > 1:
                st.info(
                    f"ℹ️ 当前文件被 {max(code_shared, step_shared)} 条记录共用 — "
                    "保存时会自动解除共用（只为本条写入独立文件）。"
                )
            gt_code = gt_code_path.read_text() if gt_code_path.exists() else ""
            code_key = f"eb_gtcode_{wid}"
            new_code = st.text_area("GT 代码", value=gt_code, height=400, key=code_key)
            bc1, bc2, _ = st.columns([1, 1, 2])
            rerender_clicked = bc1.button(
                "▶ 重渲染",
                type="primary",
                key=f"eb_rerender_{wid}",
                use_container_width=True,
            )
            save_code_clicked = bc2.button(
                "💾 保存代码 → GT",
                key=f"eb_savecode_{wid}",
                use_container_width=True,
            )
            if rerender_clicked:
                with st.spinner("正在渲染编辑后的代码…"):
                    comp, err = _eb_render_code(new_code)
                if comp is None:
                    st.error("渲染失败")
                    if err:
                        st.code(err, language="text")
                    st.session_state.pop(f"eb_last_comp_{wid}", None)
                else:
                    stash = EDIT_CACHE / sel_rid / "rerender.png"
                    stash.parent.mkdir(parents=True, exist_ok=True)
                    import shutil as _sh

                    _sh.copy2(comp, stash)
                    st.session_state[f"eb_last_comp_{wid}"] = str(stash)
            if save_code_clicked:
                with st.spinner("正在渲染并保存（如共用会自动解除）…"):
                    ok, msg = _eb_save_gt_code(
                        rec, recs, rec_idx, new_code, base_dir, jsonl_path
                    )
                if not ok:
                    st.error("保存失败 — 记录未变更")
                    if msg:
                        st.code(msg, language="text")
                else:
                    gt_png.unlink(missing_ok=True)
                    (EDIT_CACHE / sel_rid / "rerender.png").unlink(missing_ok=True)
                    st.success(msg)
                    st.rerun()
            last = st.session_state.get(f"eb_last_comp_{wid}")
            if last and Path(last).exists():
                st.markdown("**重渲染结果**")
                st.image(last, use_container_width=True)

        with tab_orig:
            if orig_code_path and orig_code_path.exists():
                st.caption(f"`{orig_code_path.relative_to(base_dir)}`")
                st.code(
                    orig_code_path.read_text(), language="python", line_numbers=True
                )
            else:
                st.caption("无原始代码路径")


# ── CQ Playground ─────────────────────────────────────────────────────────────

_CQ_PLACEHOLDER = """\
import cadquery as cq

result = (
    cq.Workplane("XY")
    .circle(20).circle(12).extrude(8)   # annular ring
)
"""


def page_cq_playground():
    import os, subprocess, sys, tempfile, shutil

    st.title("CQ Playground")
    st.caption("Paste CadQuery code → Render → see 4-view composite")

    code = st.text_area(
        "CadQuery code",
        value=st.session_state.get("cq_code", _CQ_PLACEHOLDER),
        height=380,
        key="cq_code_input",
    )
    col_btn, col_size, col_timeout = st.columns([1, 1, 1])
    render_size = col_size.selectbox("Size", [128, 256, 512], index=1, key="cq_size")
    timeout_s = col_timeout.number_input("Timeout (s)", 10, 300, 90, key="cq_timeout")
    run_btn = col_btn.button("▶ Render", type="primary", use_container_width=True)

    if run_btn:
        st.session_state["cq_code"] = code
        with st.spinner("Building & rendering…"):
            # Write code to temp file
            with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
                f.write(code)
                code_path = f.name
            out_dir = Path(tempfile.mkdtemp())
            render_script = ROOT / "scripts/data_generation/render_cq_file.py"
            env = {
                **os.environ,
                "LD_LIBRARY_PATH": "/workspace/.local/lib",
                "PYTHONPATH": "/workspace/.venv/lib/python3.11/site-packages",
            }
            r = subprocess.run(
                [
                    sys.executable,
                    str(render_script),
                    "--code",
                    code_path,
                    "--out",
                    str(out_dir),
                    "--size",
                    str(render_size),
                    "--timeout",
                    str(timeout_s),
                    "--keep-step",
                ],
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout_s + 15,
            )
            Path(code_path).unlink(missing_ok=True)

        if r.returncode != 0:
            st.error("Build/render failed")
            st.code(r.stderr or r.stdout, language="text")
        else:
            composite = out_dir / "composite.png"
            if composite.exists():
                st.image(
                    str(composite),
                    caption="4-view composite",
                    use_container_width=False,
                )
            views = [out_dir / f"view_{i}.png" for i in range(4)]
            existing = [v for v in views if v.exists()]
            if existing:
                cols = st.columns(len(existing))
                for col, v in zip(cols, existing):
                    col.image(str(v), caption=v.name, use_container_width=True)
            step = next(out_dir.glob("*.step"), None)
            if step:
                st.download_button(
                    "Download STEP",
                    step.read_bytes(),
                    file_name="result.step",
                    mime="application/octet-stream",
                )
            if r.stdout:
                with st.expander("Output"):
                    st.code(r.stdout, language="text")
            shutil.rmtree(str(out_dir), ignore_errors=True)


def page_bench_curator():
    """Scrolling per-row curator: ~100 cases/page, case_id sorted by family."""
    import io
    import json as _json

    from datasets import load_dataset

    st.title("Bench Curator")
    st.caption("Each row = 1 case. case_id sorted by family asc. ~100/page. "
               "Persisted to bench_curator_state.json.")

    DATA = ROOT / "data" / "data_generation"
    SUBSET_JSON = DATA / "bench_subset_1200.json"
    STATE_JSON = DATA / "bench_curator_state.json"

    SOURCE_PRIMARY = "qixiaoqi/cad_diverse_800"
    SOURCE_SECONDARY = "BenchCAD/cad_bench (subset_1200)"

    # ── source selector (top of page) ──
    source = st.radio(
        "Data source",
        [SOURCE_PRIMARY, SOURCE_SECONDARY],
        horizontal=True,
        key="cur_source",
        help="Primary = qixiaoqi/cad_diverse_800 (800 rows). "
             "Secondary = our BenchCAD subset_1200 (~1k). "
             "code & image are looked up from BenchCAD/cad_bench when available."
    )
    st.divider()

    @st.cache_resource(show_spinner="Loading BenchCAD/cad_bench (image/code lookup) ...")
    def _load_bench():
        ds = load_dataset("BenchCAD/cad_bench", split="test")
        idx = {r["stem"]: i for i, r in enumerate(ds)}
        return ds, idx

    @st.cache_resource(show_spinner="Loading qixiaoqi/cad_diverse_800 ...")
    def _load_diverse():
        ds = load_dataset("qixiaoqi/cad_diverse_800", split="train")
        idx = {r["stem"]: i for i, r in enumerate(ds)}
        return ds, idx

    bench_ds, bench_idx = _load_bench()
    if source == SOURCE_PRIMARY:
        diverse_ds, diverse_idx = _load_diverse()
        # Stems list = unique stems from cad_diverse_800
        selected_stems = sorted({diverse_ds[i]["stem"] for i in range(len(diverse_ds))})
        # `ds` for row metadata: prefer diverse_ds; fall back to bench_ds for fields
        # we need (gt_code / composite_png). We pass (primary, fallback) below.
        primary_ds, primary_idx = diverse_ds, diverse_idx
    else:
        if not SUBSET_JSON.exists():
            st.error(f"Subset file missing: {SUBSET_JSON}")
            return
        sub = _json.loads(SUBSET_JSON.read_text())
        selected_stems = list(sub["stems"])
        primary_ds, primary_idx = bench_ds, bench_idx

    # Unified row accessor: returns dict of fields for a given stem,
    # merging primary (metadata) + bench (gt_code / composite_png).
    def _get_row(stem: str) -> dict:
        out = {}
        if stem in primary_idx:
            r = primary_ds[primary_idx[stem]]
            out.update({k: r[k] for k in r.keys() if k in primary_ds.column_names})
        if stem in bench_idx:
            br = bench_ds[bench_idx[stem]]
            for k in ("gt_code", "composite_png"):
                if k in bench_ds.column_names:
                    out.setdefault(k, br[k])
            # If primary is missing fields, fill from bench.
            for k in ("family", "difficulty", "base_plane",
                      "feature_tags", "ops_used"):
                out.setdefault(k, br.get(k))
        return out

    # Family-diff-plane substitution: cad_diverse stems missing per-case
    # image/code in HF → swap with a same-(family,diff,plane) stem from
    # BenchCAD/cad_bench so we still have full data to curate.
    from collections import defaultdict as _dd

    @st.cache_resource(show_spinner="Building substitution map ...")
    def _build_substitution(_primary_ds_id):
        if source != SOURCE_PRIMARY:
            return {}, []
        bench_fdp = _dd(list)
        for i in range(len(bench_ds)):
            r = bench_ds[i]
            key = (r["family"], r["difficulty"], r.get("base_plane", "XY"))
            bench_fdp[key].append(r["stem"])
        for k in bench_fdp:
            bench_fdp[k].sort()
        substitutions = {}
        final_stems = []
        used_subs = set()
        for s in sorted(primary_idx.keys()):
            if s in bench_idx:
                final_stems.append(s)
                continue
            r = primary_ds[primary_idx[s]]
            key = (r["family"], r["difficulty"], r.get("base_plane", "XY"))
            cands = [c for c in bench_fdp.get(key, []) if c not in used_subs]
            if cands:
                sub = cands[0]
                substitutions[s] = sub
                used_subs.add(sub)
                final_stems.append(sub)
            # else: drop (no candidate)
        return substitutions, final_stems

    if source == SOURCE_PRIMARY:
        substitutions, final_stems = _build_substitution(id(primary_ds))
        st.caption(
            f"Source: **{source}** · {len(primary_idx)} primary stems · "
            f"**{len(substitutions)} substituted** from BenchCAD via "
            f"(family, diff, plane) match · final pool = {len(final_stems)}"
        )
    else:
        substitutions = {}
        final_stems = sorted(primary_idx.keys())

    # Adapter to match the older `ds[stem_idx[stem]]` API used below.
    # `_stems[i]` is the effective stem (substitute applied for missing-img cases).
    class _DSAdapter:
        column_names = list(set(primary_ds.column_names) |
                            {"gt_code", "composite_png"})
        def __getitem__(self, i):
            return _get_row(self._stems[i])
    ds_adapter = _DSAdapter()
    ds_adapter._stems = final_stems
    stem_to_pos = {s: i for i, s in enumerate(ds_adapter._stems)}
    ds = ds_adapter
    stem_idx = stem_to_pos
    if source == SOURCE_PRIMARY:
        selected_stems = list(final_stems)
    subset = {"stems": selected_stems}

    if STATE_JSON.exists():
        state = _json.loads(STATE_JSON.read_text())
    else:
        state = {"removed": [], "notes": {}}
    removed_set = set(state.get("removed", []))
    notes = dict(state.get("notes", {}))

    # ── controls ──
    c1, c2, c3, c4, c5 = st.columns([1.4, 1, 1, 1.4, 1])
    with c1:
        view = st.radio("View", ["Selected", "Removed", "Full pool"],
                        horizontal=True, key="cur_view")
    with c2:
        diff_filter = st.selectbox("Difficulty", ["all", "easy", "medium", "hard"], key="cur_diff")
    with c3:
        plane_filter = st.selectbox("Plane", ["all", "XY", "YZ", "XZ"], key="cur_plane")
    with c4:
        fam_filter = st.text_input("Family contains", "", key="cur_fam")
    with c5:
        page_size = int(st.selectbox("Per page", [50, 100, 200], index=1, key="cur_psize"))

    # ── pool ──
    if view == "Selected":
        pool_stems = [s for s in selected_stems if s not in removed_set]
    elif view == "Removed":
        pool_stems = sorted(removed_set)
    else:
        pool_stems = list(stem_idx.keys())

    # case_id assigned by sorting (family ASC, then stem). Stable across runs.
    pool_with_meta = []
    for stem in pool_stems:
        if stem not in stem_idx:
            continue
        r = ds[stem_idx[stem]]
        pool_with_meta.append((r["family"], stem))
    pool_with_meta.sort(key=lambda x: (x[0], x[1]))
    cid_of = {stem: cid for cid, (_, stem) in enumerate(pool_with_meta)}

    # Filter
    rows = []
    for cid, (fam, stem) in enumerate(pool_with_meta):
        r = ds[stem_idx[stem]]
        if diff_filter != "all" and r["difficulty"] != diff_filter:
            continue
        if plane_filter != "all" and r.get("base_plane", "XY") != plane_filter:
            continue
        if fam_filter and fam_filter.lower() not in fam.lower():
            continue
        rows.append((cid, stem, r))

    n_total = len(rows)
    n_pages = max(1, (n_total + page_size - 1) // page_size)

    # Pagination state — keep page in session_state so prev/next buttons can mutate.
    if "cur_page_n" not in st.session_state:
        st.session_state["cur_page_n"] = 1
    if st.session_state["cur_page_n"] > n_pages:
        st.session_state["cur_page_n"] = 1

    nav_prev, nav_lbl, nav_next, nav_num, nav_stat = st.columns([0.6, 0.6, 0.6, 1, 3])
    with nav_prev:
        if st.button("⬅ Prev", use_container_width=True,
                     disabled=st.session_state["cur_page_n"] <= 1):
            st.session_state["cur_page_n"] -= 1
            st.rerun()
    with nav_lbl:
        st.markdown(f"<div style='text-align:center; padding-top:6px'>"
                    f"**{st.session_state['cur_page_n']} / {n_pages}**</div>",
                    unsafe_allow_html=True)
    with nav_next:
        if st.button("Next ➡", use_container_width=True,
                     disabled=st.session_state["cur_page_n"] >= n_pages):
            st.session_state["cur_page_n"] += 1
            st.rerun()
    with nav_num:
        page = st.number_input("Jump", min_value=1, max_value=n_pages,
                               value=st.session_state["cur_page_n"], step=1,
                               key="cur_page_jump",
                               label_visibility="collapsed")
        if page != st.session_state["cur_page_n"]:
            st.session_state["cur_page_n"] = page
            st.rerun()
    with nav_stat:
        st.markdown(f"**{n_total}** matching · "
                    f"selected={len(selected_stems) - len(removed_set & set(selected_stems))} / "
                    f"{len(selected_stems)} · removed={len(removed_set)} · "
                    f"noted={len(notes)}")

    if not rows:
        st.info("No rows.")
        return

    page = st.session_state["cur_page_n"]
    start = (page - 1) * page_size
    end = min(start + page_size, n_total)
    page_rows = rows[start:end]
    st.caption(f"Showing {start + 1}–{end} of {n_total}")

    # Bulk export buttons
    bk1, bk2, bk3 = st.columns([1.2, 1.6, 3])
    with bk1:
        if st.button("🔄 Export curated", help="Write bench_subset_1200_curated.json"):
            curated_stems = [s for s in selected_stems if s not in removed_set]
            out = SUBSET_JSON.with_name("bench_subset_1200_curated.json")
            out.write_text(_json.dumps({
                **subset,
                "actual": len(curated_stems),
                "stems": curated_stems,
                "removed_count": len(removed_set & set(selected_stems)),
                "notes_count": len(notes),
            }, indent=2, default=str))
            st.success(f"Wrote {out.name} ({len(curated_stems)})")
    with bk2:
        if st.button("✨ Export final merged",
                     help="primary kept ∪ promoted secondary → bench_final_merged.json"):
            # Primary kept = cad_diverse_800 stems minus those marked removed.
            try:
                _diverse_ds, _ = _load_diverse()
                primary_pool = sorted({_diverse_ds[i]["stem"] for i in range(len(_diverse_ds))})
            except Exception:
                primary_pool = []
            primary_kept = [s for s in primary_pool if s not in removed_set]
            promoted = state.get("promoted", [])
            merged = sorted(set(primary_kept) | set(promoted))
            out = DATA / "bench_final_merged.json"
            out.write_text(_json.dumps({
                "primary_source": "qixiaoqi/cad_diverse_800",
                "secondary_source": "BenchCAD/cad_bench (subset_1200)",
                "primary_kept": len(primary_kept),
                "promoted_secondary": len(promoted),
                "merged_total": len(merged),
                "stems": merged,
            }, indent=2, default=str))
            st.success(
                f"Wrote {out.name}: primary_kept={len(primary_kept)} + "
                f"promoted={len(promoted)} = total {len(merged)}"
            )
    with bk3:
        st.caption(f"State file: `{STATE_JSON.name}` · "
                   f"promoted={len(state.get('promoted', []))} · "
                   f"removed={len(removed_set)}")

    st.divider()

    # ── render rows ──
    from PIL import Image as _PIL

    def _resolve_png(png):
        if png is None:
            return None
        if isinstance(png, dict) and "bytes" in png:
            png = png["bytes"]
        if isinstance(png, bytes):
            return _PIL.open(io.BytesIO(png))
        return png

    for cid, stem, r in page_rows:
        is_removed = stem in removed_set
        in_subset = stem in selected_stems
        col_id, col_img, col_meta, col_note, col_act = st.columns([0.5, 1, 2.4, 3, 1.2])

        with col_id:
            # case_id leftmost, 1-indexed.
            st.markdown(f"<div style='font-size:22px; font-weight:700; "
                        f"color:#1f77b4; padding-top:18px; text-align:center;'>"
                        f"{cid + 1}</div>", unsafe_allow_html=True)

        with col_img:
            # Prefer rendered-edit composite if user ran "Render edit"; else GT png.
            rendered_state = st.session_state.get(f"rendered_{stem}")
            shown_path = None
            if rendered_state and rendered_state[0] and not rendered_state[1]:
                shown_path = rendered_state[0]
                img = shown_path
                cap_extra = " · :green[edited]"
            else:
                img = _resolve_png(r.get("composite_png"))
                cap_extra = ""
            if img is not None:
                st.image(img, width=130)
                try:
                    with st.popover("🔍 Large", use_container_width=True):
                        st.image(img, width=520,
                                 caption=f"{stem} · {r['family']}{cap_extra}")
                except Exception:
                    with st.expander("🔍 Large"):
                        st.image(img, width=520)

        ops_list = _json.loads(r.get("ops_used", "[]") or "[]")
        with col_meta:
            badges = []
            if is_removed:
                badges.append(":red[REMOVED]")
            if not in_subset and view == "Full pool":
                badges.append(":gray[not in subset]")
            if stem in notes:
                badges.append(":orange[📝]")
            if badges:
                st.markdown(" ".join(badges))
            st.markdown(f"`{stem}`", help="case stem")
            st.caption(f"{r['family']} · {r['difficulty']} · "
                       f"{r.get('base_plane', 'XY')} · n_ops={len(ops_list)}")
            # Inline ops chip-like list (truncated if very long).
            ops_str = ", ".join(ops_list[:20])
            if len(ops_list) > 20:
                ops_str += f", … (+{len(ops_list) - 20})"
            st.markdown(f":gray[ops:] {ops_str}" if ops_list else ":gray[ops: (none)]")

        with col_note:
            cur = notes.get(stem, "")
            new = st.text_input("note", value=cur, key=f"note_{stem}",
                                label_visibility="collapsed",
                                placeholder="leave a note (auto-save on change)")
            if new != cur:
                if new.strip():
                    notes[stem] = new.strip()
                else:
                    notes.pop(stem, None)
                state["notes"] = notes
                STATE_JSON.write_text(_json.dumps(state, indent=2))

        with col_act:
            label = "↩ Restore" if is_removed else "🗑 Remove"
            if st.button(label, key=f"rm_{stem}", use_container_width=True):
                if is_removed:
                    removed_set.discard(stem)
                else:
                    removed_set.add(stem)
                state["removed"] = sorted(removed_set)
                STATE_JSON.write_text(_json.dumps(state, indent=2))
                st.rerun()
            # Promote to primary (only when viewing secondary source).
            if source == SOURCE_SECONDARY:
                promoted = set(state.get("promoted", []))
                is_promoted = stem in promoted
                pl = "★ Unpromote" if is_promoted else "➕ Promote"
                if st.button(pl, key=f"pr_{stem}", use_container_width=True,
                             help="Add this case to final merged dataset "
                                  "(primary kept ∪ promoted secondary)"):
                    if is_promoted:
                        promoted.discard(stem)
                    else:
                        promoted.add(stem)
                    state["promoted"] = sorted(promoted)
                    STATE_JSON.write_text(_json.dumps(state, indent=2))
                    st.rerun()
                if is_promoted:
                    st.markdown(":green[**★ promoted**]")
            # NB: legacy `removed` block retained below but unreachable
            # (the button above already triggered rerun).
            if False:
                pass
                state["removed"] = sorted(removed_set)
                STATE_JSON.write_text(_json.dumps(state, indent=2))
                st.rerun()

        with st.expander(f"▶ #{cid + 1} code & full ops"):
            tab_code, tab_ops, tab_tags = st.tabs(
                ["code (editable)", "ops (full)", "feature_tags"])
            with tab_code:
                code_edits = state.get("code_edits", {})
                cur_code = code_edits.get(stem, r.get("gt_code", ""))
                edited = st.text_area("CadQuery code", value=cur_code,
                                      height=320, key=f"code_{stem}",
                                      label_visibility="collapsed")
                bc1, bc2, bc3, bc4 = st.columns(4)
                with bc1:
                    if st.button("💾 Save edit", key=f"sve_{stem}",
                                 use_container_width=True):
                        code_edits = state.get("code_edits", {})
                        if edited.strip() and edited != r.get("gt_code", ""):
                            code_edits[stem] = edited
                        else:
                            code_edits.pop(stem, None)
                        state["code_edits"] = code_edits
                        STATE_JSON.write_text(_json.dumps(state, indent=2))
                        st.success("Saved")
                with bc2:
                    if st.button("🔧 Render edit", key=f"rnd_{stem}",
                                 use_container_width=True):
                        import tempfile
                        from pathlib import Path as _P
                        from render import render_cq
                        # OCP 7.9.3 shim — same prefix as run_iso_106_codegen
                        # uses, so faces()/edges() selectors work in subprocess.
                        shim = (
                            "from OCP.TopoDS import (TopoDS_Compound, "
                            "TopoDS_CompSolid, TopoDS_Edge, TopoDS_Face, "
                            "TopoDS_Shape, TopoDS_Shell, TopoDS_Solid, "
                            "TopoDS_Vertex, TopoDS_Wire)\n"
                            "for _cls in (TopoDS_Shape, TopoDS_Face, "
                            "TopoDS_Edge, TopoDS_Vertex, TopoDS_Wire, "
                            "TopoDS_Shell, TopoDS_Solid, TopoDS_Compound, "
                            "TopoDS_CompSolid):\n"
                            "    if not hasattr(_cls, 'HashCode'):\n"
                            "        _cls.HashCode = lambda self, ub=2147483647: id(self) % ub\n"
                        )
                        body = edited if "TopoDS_Shape" in edited else shim + edited
                        with tempfile.NamedTemporaryFile(
                                "w", suffix=".py", delete=False) as f:
                            f.write(body)
                            f.flush()
                            cq_path = f.name
                        out_dir = _P(tempfile.mkdtemp(prefix="cur_render_"))
                        comp, err = render_cq(cq_path, str(out_dir))
                        st.session_state[f"rendered_{stem}"] = (comp, err,
                                                                 str(out_dir))
                        st.rerun()
                with bc3:
                    if st.button("↩ Reset to GT", key=f"rst_{stem}",
                                 use_container_width=True):
                        code_edits = state.get("code_edits", {})
                        code_edits.pop(stem, None)
                        state["code_edits"] = code_edits
                        STATE_JSON.write_text(_json.dumps(state, indent=2))
                        st.rerun()
                with bc4:
                    is_edited = stem in state.get("code_edits", {})
                    st.markdown(":green[**EDITED**]" if is_edited
                                else ":gray[unmodified]")

                rkey = f"rendered_{stem}"
                if rkey in st.session_state:
                    comp, err, _odir = st.session_state[rkey]
                    if err:
                        st.error(f"Render failed:\n{err[:500]}")
                    elif comp:
                        st.success("Render OK")
                        st.image(comp, width=400, caption="rendered preview")

            with tab_ops:
                st.code(_json.dumps(ops_list, indent=2), language="json")
            with tab_tags:
                st.code(_json.dumps(_json.loads(r.get("feature_tags", "{}") or "{}"),
                                    indent=2), language="json")

        st.divider()

    return  # end render

    # ── (legacy single-stem detail kept below for reference, never reached) ──
    if False:
        pick_stem = ""
        return  # noqa: B012 — never reached


# ── navigation ────────────────────────────────────────────────────────────────


def main():
    pages = [
        "Overview",
        "Stem List",
        "Stem Viewer",
        "Synth Monitor",
        "Bench Curator",
        "编辑 Bench",
        "CQ Playground",
    ]

    # Apply pending navigation BEFORE the widget is instantiated
    if "_nav_pending" in st.session_state:
        st.session_state["nav_radio"] = st.session_state.pop("_nav_pending")

    with st.sidebar:
        page = st.radio(
            "Navigation",
            pages,
            key="nav_radio",
            label_visibility="collapsed",
        )

    if page == "Overview":
        page_overview()
    elif page == "Synth Monitor":
        page_synth()
    elif page == "Stem List":
        page_stem_list()
    elif page == "Bench Curator":
        page_bench_curator()
    elif page == "编辑 Bench":
        page_edit_bench()
    elif page == "CQ Playground":
        page_cq_playground()
    else:
        page_stem_viewer()


if __name__ == "__main__":
    main()
