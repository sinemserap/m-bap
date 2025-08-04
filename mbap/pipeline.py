#!/usr/bin/env python
import json, yaml, os, shutil, warnings, mne, matplotlib.pyplot as plt
from mne_bids import BIDSPath, read_raw_bids, print_dir_tree
from mne.preprocessing import ICA
from autoreject import get_rejection_threshold, Ransac
from mne_icalabel import label_components, IC_LABELS
from pathlib import Path
from datetime import datetime

# ---------- Load configuration ---------- #
cfg_f = Path(__file__).with_name("config.yml")
cfg = yaml.safe_load(cfg_f.read_text())

bids_root   = Path(cfg["bids_root"]).resolve()
deriv_root  = Path(cfg["derivatives_root"]).resolve()
deriv_root.mkdir(parents=True, exist_ok=True)

# ---------- Helper: plot PSD ---------- #
def plot_psd(raw, title, out_png):
    fig = raw.compute_psd().plot(average=True, show=False)
    fig.suptitle(title)
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)

# ---------- Main per‑subject routine ---------- #
def preprocess_subject(sub):
    print(f"\n=== {sub} ===")
    bids_path = BIDSPath(root=bids_root, subject=sub.replace('sub-', ''),
                         task=None, session=None, run=None, datatype='eeg')
    raw = read_raw_bids(bids_path=bids_path, verbose=False)
    raw.load_data()

    # -- Resample (if needed) -- #
    if cfg["resample_sfreq"] < raw.info['sfreq']:
        raw.resample(cfg["resample_sfreq"])
    
    # -- Line‑noise & band filtering -- #
    raw.notch_filter(cfg["notch_freq"])
    raw.filter(cfg["high_pass"], cfg["low_pass"], fir_design='firwin', verbose=False)
    if cfg["save_intermediate"]:
        raw.copy().save(deriv_root / f"{sub}_filt_raw.fif", overwrite=True)

    # -- Bad‑channel detection via RANSAC -- #
    ransac = Ransac(n_resample=cfg["ransac_n_resample"],
                    min_corr=cfg["ransac_min_corr"],
                    min_channels=0.25, picks="eeg",
                    random_state=97, verbose=False,
                    threshold_k=cfg["ransac_threshold_k"])
    raw = ransac.fit_transform(raw)
    raw.info['bads'].extend(ransac.bad_chs_)
    raw.interpolate_bads(reset_bads=True)

    # -- Robust average reference -- #
    raw.set_eeg_reference('average', projection=False)

    # -- Artefact Subspace Reconstruction (ASR) -- #
    try:
        from meegkit.asr import ASR          # preferred
    except ImportError:
        from asrpy.src.asrpy import ASR      # fallback to asrpy
    asr = ASR(sfreq=raw.info['sfreq'],
              cutoff=cfg["asr_cutoff"],
              win_len=cfg["asr_window_len"])
    cleaned, _ = asr.fit_transform(raw.get_data().T)   # (samples, chans)
    raw._data = cleaned.T                              # back to (ch, samples)
    if cfg["save_intermediate"]:
        raw.copy().save(deriv_root / f"{sub}_asr_raw.fif", overwrite=True)

    # -- ICA decomposition -- #
    n_components = None if cfg["ica_n_components"] == "auto" else cfg["ica_n_components"]
    ica = ICA(n_components=n_components, method='infomax', random_state=97, max_iter='auto')
    ica.fit(raw.copy().filter(1., 45., fir_design='firwin'))  # fit on 1‑45 Hz
    # Label components
    ica_labels = label_components(raw, ica, method='iclabel')
    bad_idx = [idx for idx, lab in enumerate(ica_labels['labels'])
               if lab in cfg["iclabel_remove"]
               and ica_labels['y_pred_proba'][idx, IC_LABELS.index(lab)] >= cfg["iclabel_prob_thresh"]]
    ica.exclude = bad_idx
    raw = ica.apply(raw.copy())
    
    # ---------- Optional epoching & Autoreject‑local ---------- #
    if cfg["make_epochs"]:
        events = mne.read_events(bids_path.copy().update(suffix='events'))
        epochs = mne.Epochs(raw, events, tmin=cfg["tmin"], tmax=cfg["tmax"],
                            baseline=tuple(cfg["baseline"]), preload=True)
        reject = get_rejection_threshold(epochs, decim=4)          # global p‑p
        epochs.drop_bad(reject=reject)
        epochs.save(deriv_root / f"{sub}_epo.fif", overwrite=True)
    
    # ---------- Save cleaned continuous data ---------- #
    out_fif = deriv_root / f"{sub}_clean_raw.fif"
    raw.save(out_fif, overwrite=True)

    # ---------- QC report ---------- #
    report_dir = deriv_root / "reports"
    report_dir.mkdir(exist_ok=True)
    plot_psd(raw, f"{sub} – Cleaned PSD", report_dir / f"{sub}_psd.png")
    # record parameters + counts
    meta = {
        "date": datetime.now().isoformat(timespec='minutes'),
        "n_samples": raw.n_times,
        "sfreq": raw.info['sfreq'],
        "n_channels": len(raw.ch_names),
        "bad_channels_after_ransac": ransac.bad_chs_,
        "ica_components_removed": bad_idx,
    }
    (report_dir / f"{sub}_meta.json").write_text(json.dumps(meta, indent=2))

# ---------- Run ---------- #
if __name__ == "__main__":
    subs = cfg["subjects"]
    if not subs:
        subs = ["sub-"+s for s in mne_bids.get_entity_vals(bids_root, 'subject')]
    for sub in subs:
        preprocess_subject(sub)

    print("\nDone. Cleaned files are in:", deriv_root)
