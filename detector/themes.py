"""Candidate discovery, stage 3: group candidate bigrams into technology themes.

The grouping below is keyword grouping (the one LLM-assisted step CLAUDE.md allows); every number in
the output is read from outputs/candidates_bigrams.csv, nothing is scored or ranked by judgement.
Bigrams not listed here are patent-drafting fragments ("trained machine", "store instructions"),
layout boilerplate, or unassigned; they stay in candidates_bigrams.csv untouched.
Output: outputs/candidates_themes.md
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"

# theme -> (sub-theme -> bigrams). Written 2026-11-06 from the first candidate run.
THEMES = {
    "Generative AI / ML methods (vocabulary note: the market phrase is 'generative AI' / 'artificial intelligence', which is T2 by any count — listed for completeness, not as a candidate)": {
        "LLM / generative": ["language model", "diffusion model", "transformer model", "generative model", "trained language", "model mlm", "input query", "generating content", "few shot", "teacher model", "student model", "knowledge distillation"],
        "training methods": ["contrastive learning", "self supervised", "self attention", "attention mechanism", "fine tuning", "fine tuned", "transfer learning", "pre training", "federated learning", "graph neural", "network gnn", "reinforcement learning", "synthetic data", "data augmentation", "representation learning", "knowledge graph", "encoder decoder", "latent space", "embedding vector", "series forecasting", "tabular data"],
    },
    "AI compute & memory hardware": {
        "accelerators / memory": ["neural processing", "bandwidth memory", "computational storage", "heterogeneous computing", "network accelerator", "crossbar array", "memory lstm", "3d nand", "row hammer", "page buffer", "memory dies", "ferroelectric memory", "ferroelectric layer"],
        "advanced packaging / backside power": ["hybrid bonding", "hybrid bonded", "direct bond", "backside power", "backside contact", "backside metal", "power rail", "die package", "semiconductor packaging", "trench capacitor", "bond wire", "metallization layers"],
        "process / devices": ["euv light", "mobility transistor", "transistor hemt", "power transistors", "semiconductor switching", "selective deposition", "gap filling"],
    },
    "Wireless: 5G-Advanced / 6G / Wi-Fi 7 / NTN": {
        "non-terrestrial & satellite": ["network ntn", "terrestrial network", "satellite network"],
        "Wi-Fi 7 multi-link / TWT": ["ap mld", "ap multi", "multi link", "time twt", "target wake", "wake time", "stations stas", "link operation"],
        "O-RAN / RIC / network energy": ["open radio", "rt ric", "controller ric", "intelligent controller", "network energy", "spectrum management", "5g core", "service mesh"],
        "6G research: RIS, sensing, joint transmission": ["intelligent surfaces", "sensing measurement", "rf sensing", "radar sensing", "coherent joint", "joint transmission", "beam prediction", "beam management", "5g 6g"],
        "sidelink / V2X / positioning": ["sidelink sl", "physical sidelink", "sidelink positioning", "sidelink feedback", "sidelink synchronization", "channel pssch", "channel pscch", "channel psfch", "sl transmission", "sl communication", "sl resource", "ultra wideband", "wideband uwb", "band uwb", "uwb communication", "function lmf", "arrival aoa"],
        "5G core / RRC procedures (standards vocabulary)": ["rrc inactive", "rrc release", "rrc reconfiguration", "rrc connected", "rrc idle", "pdu session", "mbs session", "drx configuration", "function upf", "function smf", "function amf", "function pcf", "policy ursp", "slice information", "conditional handover", "cell switching", "cell mobility"],
    },
    "Batteries & electrification": {
        "cell chemistry": ["state electrolyte", "electrolyte material", "lithium salt", "bis fluorosulfonyl", "fluorosulfonyl imide", "lithium bis", "fluorine free", "sulfur battery", "metal battery", "iron phosphate", "lithium iron", "single particle", "negative active", "positive electrodes", "capacity retention", "cycling performance", "lifespan characteristics"],
        "cell manufacturing & formats": ["dry electrode", "electrode slurry", "electrode sheet", "electrode stack", "current collector", "current collecting", "jelly roll", "wound electrode", "pouch type", "cylindrical battery", "cell stacks", "battery manufacturing", "manufacturing battery", "battery production", "lamination direction"],
        "thermal management / safety": ["thermal runaway", "battery thermal", "battery cooling", "battery temperature", "immersion cooling", "cold plate", "thermal event", "health soh", "battery data"],
        "lithium supply & recycling": ["lithium extraction", "lithium carbonate", "lithium source", "recycling process"],
        "charging & drives": ["fast charging", "charging pile", "charging socket", "charge port", "vehicle charger", "ev charging", "axial flux", "electric drive", "electric machines", "electric compressor", "flow batteries", "battery storage", "grid power"],
    },
    "Hydrogen, carbon capture, chemical recycling": {
        "hydrogen production & storage": ["hydrogen production", "producing hydrogen", "produce hydrogen", "hydrogen generation", "hydrogen gas", "hydrogen storage", "hydrogen tank", "hydrogen supply", "hydrogen stream", "hydrogen rich", "liquid hydrogen", "gaseous hydrogen", "hydrogen fuel", "water electrolysis", "electrolysis cell", "water gas", "gas shift"],
        "carbon capture": ["direct air", "air capture", "dioxide capture", "dioxide recovery", "carbon sequestration", "dioxide co", "reducing carbon", "carbon emission"],
        "plastics circularity": ["plastic pyrolysis", "pyrolysis oil", "pyrolysis reactor", "waste plastic", "plastic waste", "post consumer", "biodegradable material"],
        "other energy": ["offshore wind", "rocket engine", "aircraft propulsion", "electric propulsion", "combustion section", "combustor section"],
    },
    "Quantum & photonics": {
        "quantum computing": ["quantum computer", "quantum circuit", "quantum processor", "quantum state", "quantum states", "quantum information", "quantum error", "superconducting quantum", "superconducting material", "classical computing"],
        "quantum-safe & quantum comms": ["post quantum", "quantum key", "quantum communication", "quantum cryptography", "homomorphic encryption", "zero knowledge", "party computation", "secure multi", "elliptic curve"],
        "photonics": ["circuit pic", "lithium niobate", "ring resonator", "waveguide core", "laser vcsel", "vertical cavity", "wavelength converter", "holographic optical", "delayed fluorescence", "delayed fluorescent"],
    },
    "Biotech & medtech": {
        "nucleic-acid delivery & gene therapy": ["lipid nanoparticle", "lipid nanoparticles", "nanoparticle lnp", "ionizable lipid", "cationic lipid", "recombinant aav", "viral vector", "viral vectors", "guide rna", "gene editing", "target rna"],
        "cell therapy & immunology": ["nk cells", "nk cell", "natural killer", "killer cells", "adoptive cell", "receptors tcrs", "modified immune", "myeloid cells", "bispecific antibodies", "multispecific antibodies", "binding fragment", "binding domains", "antibodies targeting", "intracellular signaling"],
        "protein degradation & vesicles": ["protein degradation", "extracellular vesicles", "extracellular vesicle", "vesicles evs"],
        "diagnostics & sequencing": ["free dna", "free nucleic", "sequencing data", "sequence reads", "rolling circle", "fluorescence imaging", "ray fluorescence"],
        "medtech & neuro": ["deep brain", "aspiration catheter", "intraoral scanner", "continuous analyte", "glucose measurement", "surgical robotic", "treatment planning", "patient anatomy", "anatomical features", "respiratory therapy", "sleep quality", "depressive disorder", "major depressive", "herpes simplex", "fibrotic disorders"],
    },
    "XR, displays, consumer hardware": {
        "XR": ["extended reality", "reality xr", "xr environment", "mixed reality", "ar glasses", "ar vr", "vr headset", "eye box", "spatial audio", "virtual character", "virtual scene", "virtual content", "3d environment", "haptic actuator"],
        "foldables & displays": ["foldable electronic", "folded state", "unfolded state", "bending area", "bending stiffness", "pixel circuits", "pixel driver", "pixel drive", "emission area", "emitting area", "led display", "micro led"],
        "consumer devices": ["watch case", "watch band", "watch dial", "air fryer", "hair dryer", "hair clipper", "electric bicycle", "human powered", "home appliance", "home appliances", "aerosol generator", "electronic game", "toy gun", "toy vehicle", "toy building", "shaving razor", "hair cutting", "impact tool", "outdoor power", "electric tool"],
    },
    "Autonomy, robotics, industrial": {
        "autonomous driving sensing": ["lidar sensor", "lidar data", "radar sensor", "radar data", "radar signals", "wave fmcw", "ego vehicle", "vehicle av", "advanced driver", "path planning", "planned path", "predicted trajectory", "pose estimation", "depth estimation", "motion prediction", "3d point", "imu data", "sensor calibration", "sensor suite", "lane line", "connected vehicle", "intelligent vehicle"],
        "robots & automation": ["robotic arms", "robotic manipulator", "mechanical arm", "autonomous robot", "transfer robot", "guided vehicle", "automated storage", "storage rack", "container handling", "work machine", "agricultural machine", "agricultural field", "digital twin", "robotic process", "automation rpa"],
        "additive manufacturing": ["additive manufacture", "bed fusion", "build plate", "build surface", "manufacturing am", "dimensional printed"],
        "aerospace & marine": ["air vehicle", "aircraft wing", "aircraft power", "marine vessel"],
    },
    "Software infrastructure, crypto, security": {
        "blockchain / tokens": ["distributed ledger", "ledger technology", "smart contract", "fungible token", "token nft", "off chain", "digital currency", "decentralized network", "wallet application", "digital identity", "digital key"],
        "cloud native & edge": ["cloud native", "container orchestration", "containerized application", "multi cloud", "cloud provider", "cloud environments", "sd wan", "edge application", "edge data", "data lake", "data warehouse", "data platform", "zero trust", "access tokens"],
        "media": ["live streaming", "live stream", "streaming platform", "virtual meeting", "virtual conference", "video editing", "video decoding", "speech enhancement", "special effect"],
    },
}


def main() -> None:
    rows = {r["bigram"]: r for r in csv.DictReader(open(OUT / "candidates_bigrams.csv", encoding="utf-8"))}
    assigned = set()
    lines = ["# Candidate themes (keyword grouping of outputs/candidates_bigrams.csv)", "",
             "Columns: bigram (signal year, latest-year applications / distinct applicants, 10-K filings in the newest EDGAR year). "
             "Tier per settings.yml: T0 < 50 10-K filings, T1 50–199, T2 ≥ 200. Bigrams absent from the candidate file are shown as 'not a candidate' "
             "(no Rule G signal 2017–2023, fading, or filtered).", ""]
    summary = []
    for theme, subs in THEMES.items():
        lines.append(f"## {theme}")
        t_n = t_items = 0
        t_k = 0
        for sub, bgs in subs.items():
            items, missing = [], []
            for b in bgs:
                r = rows.get(b)
                if not r:
                    missing.append(b); continue
                assigned.add(b)
                k = r["edgar_latest"] or "–"
                items.append(f"{b} ({r['signal_year']}, {r['latest_count']}/{r['n_assignees']}, 10-K {k}, {r['tier'] or '–'})")
                t_n += int(r["latest_count"]); t_items += 1
                t_k = max(t_k, int(r["edgar_latest"] or 0))
            line = f"- {sub}: " + "; ".join(items)
            if missing:
                line += f" — not a candidate: {', '.join(missing)}"
            lines.append(line)
        lines.append("")
        summary.append((theme.split(" (")[0], t_items, t_n, t_k))
    lines += ["## Theme totals (candidate bigrams, 2023 applications summed over them, max 10-K count among them)", "",
              "| theme | bigrams | applications 2023 | max 10-K |", "|---|---|---|---|"]
    for name, n_items, n_apps, k in summary:
        lines.append(f"| {name} | {n_items} | {n_apps} | {k} |")
    unassigned = [b for b in rows if b not in assigned and rows[b]["tier"] in ("TW", "T0", "T1")]
    lines += ["", f"Unassigned T0/T1 candidate bigrams (drafting fragments, layout boilerplate, or not yet grouped): {len(unassigned)} — kept in candidates_bigrams.csv."]
    (OUT / "candidates_themes.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"themes: {len(THEMES)}; assigned {len(assigned)} bigrams; unassigned T0/T1 {len(unassigned)}")


if __name__ == "__main__":
    main()
