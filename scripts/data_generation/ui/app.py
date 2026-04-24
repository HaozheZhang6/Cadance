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


# ── eval page (bench scoring viewer) ──────────────────────────────────────────

BENCH_CACHE = ROOT / "bench" / "ui" / "cache"
BENCH_IMG = BENCH_CACHE / "images"


@st.cache_data(ttl=60)
def load_bench_data():
    p = BENCH_CACHE / "data.json"
    if not p.exists():
        return None
    import json

    return json.loads(p.read_text())


def _score_bar(label: str, value, weight=None, disabled: bool = False):
    if value is None:
        st.caption(f"{label}: —")
        return
    suffix = f"  _(wt={weight})_" if weight is not None else ""
    color = "🟢" if value >= 0.80 else "🟡" if value >= 0.50 else "🔴"
    prefix = "~~" if disabled else ""
    suffix2 = "~~" if disabled else ""
    st.markdown(f"{prefix}{color} **{label}**: `{value:.3f}`{suffix2}{suffix}")
    if not disabled:
        st.progress(value)


def _show_bench_scores(scores: dict):
    if not scores:
        st.warning("执行失败，无评分")
        return
    fs = scores.get("feature_score")
    ts = scores.get("tag_score")
    ss = scores.get("shape_score")
    color = "green" if (fs or 0) >= 0.8 else "orange" if (fs or 0) >= 0.5 else "red"
    st.markdown(
        f"## :{color}[{fs:.3f}]  feature_score"
        if fs is not None
        else "## — feature_score"
    )
    st.divider()
    st.markdown("#### ① tag_score `× 0.25`")
    _score_bar("tag_score", ts, weight=0.25)
    tag_keys = ["has_hole", "has_fillet", "has_chamfer", "rotational"]
    gt_tags = scores.get("gt_tags", {})
    case_tags = scores.get("case_tags", {})
    match_map = scores.get("tag_match", {})
    cols = st.columns(4)
    for i, k in enumerate(tag_keys):
        ok = match_map.get(k, False)
        cols[i].markdown(f"{'✅' if ok else '❌'} **{k}**")
        cols[i].caption(
            f"GT {'✓' if gt_tags.get(k) else '✗'} → Case {'✓' if case_tags.get(k) else '✗'}"
        )
    st.divider()
    st.markdown("#### ② shape_score `× 0.75`")
    _score_bar("shape_score", ss, weight=0.75)
    c1, c2 = st.columns(2)
    with c1:
        iou = scores.get("iou")
        cd_s = scores.get("cd_score")
        cd_r = scores.get("cd")
        st.markdown("**主要权重**")
        _score_bar("IoU (3D voxel)", iou, weight=0.375)
        if cd_s is not None:
            _score_bar(f"CD score  (CD={cd_r:.4f})", cd_s, weight=0.375)
    with c2:
        mv = scores.get("mv_iou")
        hd_s = scores.get("hd_score")
        hd_r = scores.get("hd")
        fs_v = scores.get("fscore")
        fp = scores.get("fprecision")
        fr = scores.get("frecall")
        st.markdown("**扩展指标（权重 = 0）**")
        _score_bar("Multi-view IoU", mv, disabled=True)
        if hd_s is not None:
            _score_bar(f"HD score  (HD={hd_r:.4f})", hd_s, disabled=True)
        if fs_v is not None:
            _score_bar(
                f"F-score @ τ=0.05  (P={fp:.2f} R={fr:.2f})", fs_v, disabled=True
            )


def _show_bench_img(path_str, caption=""):
    if path_str:
        p = BENCH_IMG / path_str
        if p.exists():
            st.image(str(p), caption=caption, use_container_width=True)
            return
    st.caption(f"_{caption}: 无图像_")


def page_eval():
    st.title("Eval — Bench Score Viewer")
    data = load_bench_data()
    if data is None:
        st.error("Bench cache not found.")
        st.code(
            "LD_LIBRARY_PATH=/workspace/.local/lib uv run python3 bench/ui/prepare_data.py"
        )
        return

    gts = data["gts"]

    with st.sidebar:
        st.markdown("**评分公式**")
        st.markdown(
            "```\nfeature_score =\n  0.25 × tag_score\n  0.75 × shape_score\n\nshape_score =\n  0.5 × iou\n  0.5 × cd_score\n```"
        )
        st.caption("HD / F-score / MultiView IoU 权重 = 0")
        st.divider()
        families = sorted(set(g["family"] for g in gts))
        sel_family = st.selectbox("Family", ["All"] + families, key="eval_family")
        filtered = (
            gts
            if sel_family == "All"
            else [g for g in gts if g["family"] == sel_family]
        )
        gt_options = {g["uid"]: g for g in filtered}
        sel_uid = st.selectbox(
            "GT 样本",
            list(gt_options.keys()),
            format_func=lambda uid: f"{gt_options[uid]['family']}  ·  {gt_options[uid]['stem'][-20:]}",
            key="eval_uid",
        )

    gt = gt_options[sel_uid]
    st.markdown(f"# `{gt['family']}`")
    st.caption(gt["stem"])

    col_gt_img, col_gt_info = st.columns([1, 2])
    with col_gt_img:
        _show_bench_img(gt["image"], "GT 渲染")
    with col_gt_info:
        st.markdown("### Ground Truth")
        feats = gt["features"]
        fc = st.columns(4)
        for i, (k, v) in enumerate(feats.items()):
            fc[i].metric(k, "✓" if v else "✗")
        with st.expander("GT Code", expanded=False):
            st.code(gt["code"], language="python", line_numbers=True)

    st.divider()
    case_order = ["A_self", "C_cross", "D_same", "B_pred"]
    case_icons = {
        "A_self": "🔵 A — GT 自检",
        "C_cross": "🔴 C — 跨 Family",
        "D_same": "🟡 D — 同 Family 不同实例",
        "B_pred": "🟢 B — 模型预测",
    }
    available = [k for k in case_order if k in gt["cases"]]
    if not available:
        st.warning("无 case 数据")
        return

    tabs = st.tabs([case_icons[k] for k in available])
    for tab, key in zip(tabs, available):
        case = gt["cases"][key]
        scores = case.get("scores", {})
        with tab:
            is_self = key == "A_self"
            col_img, col_code, col_score = st.columns([1, 1, 2])
            with col_img:
                st.markdown("**渲染**")
                gid = case.get("gid", "")
                if gid:
                    st.caption(f"`{gid}`")
                if is_self:
                    _show_bench_img(gt["image"], "（同 GT）")
                else:
                    _show_bench_img(case.get("image"), "Case 渲染")
            with col_code:
                st.markdown("**代码**")
                code = gt["code"] if is_self else case.get("code")
                if code:
                    with st.expander("查看代码", expanded=False):
                        st.code(code, language="python", line_numbers=True)
                else:
                    st.caption("无代码（exec failed）")
            with col_score:
                _show_bench_scores(scores)


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


# ── navigation ────────────────────────────────────────────────────────────────


def main():
    pages = [
        "Overview",
        "Stem List",
        "Stem Viewer",
        "Synth Monitor",
        "Eval",
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
    elif page == "Eval":
        page_eval()
    elif page == "CQ Playground":
        page_cq_playground()
    else:
        page_stem_viewer()


if __name__ == "__main__":
    main()
