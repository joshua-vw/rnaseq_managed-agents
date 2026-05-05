# RNA-seq Managed Agents

Multi-agent orchestration for differential gene expression pipeline monitoring, built around GenPipes RNA-seq Light (C3G, McGill). Agents are coordinated using Anthropic's Managed Agents framework.

**Author:** Joshua Virani-Wall
**Contact:** joshuajamesvw@gmail.com

---

## Project Overview

This project investigates how variation in wetlab protocol — RNA extraction method, library fragmentation, and sequencing platform — propagates into systematic gene expression differences. It uses publicly available ENCODE RNA-seq data from the GM12878 human cell line, where the same biological sample was independently processed by two labs using distinct protocols (Gingeras/CSHL and Wold/Caltech).

---

## Platform Notes

This project was developed and tested on the following system. Several setup steps — Homebrew installs, macFUSE, and Docker Desktop — are macOS-specific. Linux users should refer to the official docs for each tool. The Python/conda environment, Anthropic API setup, and GenPipes pipeline steps are platform-independent.

| Component | Version |
|---|---|
| Hardware | MacBook Pro 14-inch, Nov 2024, Apple M4 Max |
| macOS | Sequoia 15.7.3 |
| Homebrew | 5.1.9 |
| Docker Desktop | 4.71.0 |
| macFUSE | 5.2.0 |
| seqtk | 1.5 |
| GenPipes (container) | 6.1.1 |
| Python | 3.11.15 |
| anthropic SDK | 0.97.0 |

---

## Environment Setup

### Prerequisites
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or Anaconda installed

### Create the conda environment
```bash
conda env create -f environment.yml
conda activate managed-agents
```

### API Key

This project requires an Anthropic API key.

1. Create an account at [platform.claude.com](https://platform.claude.com)
2. Go to Settings → API Keys → Create Key
3. Create a `.env` file in the project root (see `.env.example` for the required variables)
4. Add your key to `.env`:
```
ANTHROPIC_API_KEY=your-key-here
```

---

## GenPipes Setup

GenPipes runs inside a Docker container provided by C3G. This allows the full pipeline to run locally on your machine without a cluster.

### Prerequisites

Install Docker Desktop and macFUSE via Homebrew:

```bash
brew install --cask docker
brew install --cask macfuse
```

After installing macFUSE, go to **System Settings → Privacy & Security** and allow the kernel extension from Benjamin Fleischer.

### CVMFS Cache

Create a local cache folder for reference genomes and bioinformatics tools (this will grow over time):

```bash
mkdir -p ~/genpipes-cvmfs-cache
```

### Launch the GenPipes Container

From your project folder, run:

```bash
cd ~/Projects/rnaseq_managed-agents

docker run --rm \
  --device /dev/fuse \
  --cap-add SYS_ADMIN \
  -v /tmp:/tmp \
  -it \
  -w $PWD \
  -v $HOME:$HOME \
  -v ~/genpipes-cvmfs-cache:/cvmfs-cache/ \
  ghcr.io/c3g/genpipes_in_a_container:latest
```

This mounts your project folder and home directory into the container. Reference genomes and tools are streamed on demand via CVMFS and cached in `~/genpipes-cvmfs-cache`.

---

## Data

### Experiments

Two ENCODE RNA-seq experiments on the GM12878 human cell line, using the same biological replicates processed by different labs:

| Experiment | Lab | Protocol | Accession |
|---|---|---|---|
| Gingeras | Thomas Gingeras, CSHL | dUTP, reverse stranded, PE101nt, HiSeq 2000 | ENCSR000AED |
| Wold | Barbara Wold, Caltech | Nextera tagmentation, unstranded, PE100nt, HiSeq 2000 | ENCSR000AEG |

Both experiments share the same biosamples (ENCBS089RNA, ENCBS090RNA) — any expression differences are technical, not biological.

### Folder Structure

```
~/Projects/rnaseq_managed-agents/
├── gingeras_cshl/
│   ├── raw_data/
│   │   ├── R1/
│   │   │   ├── ENCFF001REK.fastq.gz        # replicate 1, R1 (7.31 GB)
│   │   │   ├── ENCFF001REK_3M.fastq.gz     # replicate 1, R1 subsampled
│   │   │   ├── ENCFF001REI.fastq.gz        # replicate 2, R1 (7.01 GB)
│   │   │   └── ENCFF001REI_3M.fastq.gz     # replicate 2, R1 subsampled
│   │   └── R2/
│   │       ├── ENCFF001REJ.fastq.gz        # replicate 1, R2 (7.48 GB)
│   │       ├── ENCFF001REJ_3M.fastq.gz     # replicate 1, R2 subsampled
│   │       ├── ENCFF001REH.fastq.gz        # replicate 2, R2 (7.18 GB)
│   │       └── ENCFF001REH_3M.fastq.gz     # replicate 2, R2 subsampled
│   └── metadata/
│       └── ENCSR000AED.json
└── wold_caltech/
    ├── raw_data/
    │   ├── R1/
    │   │   ├── ENCFF001RVY.fastq.gz        # replicate 1, R1 (7.85 GB)
    │   │   ├── ENCFF001RVY_3M.fastq.gz     # replicate 1, R1 subsampled
    │   │   ├── ENCFF001RVS.fastq.gz        # replicate 2, R1 (7.64 GB)
    │   │   └── ENCFF001RVS_3M.fastq.gz     # replicate 2, R1 subsampled
    │   └── R2/
    │       ├── ENCFF001RVR.fastq.gz        # replicate 1, R2 (7.64 GB)
    │       ├── ENCFF001RVR_3M.fastq.gz     # replicate 1, R2 subsampled
    │       ├── ENCFF001RVW.fastq.gz        # replicate 2, R2 (7.86 GB)
    │       └── ENCFF001RVW_3M.fastq.gz     # replicate 2, R2 subsampled
    └── metadata/
        └── ENCSR000AEG.json
```

Full dataset: ~59 GB. Subsampled files (`_3M`): ~3 GB total. GenPipes uses the subsampled files for local development.

### Downloading the FASTQ files

Use `curl` with the `-C -` flag to resume interrupted downloads:

```bash
cd ~/Projects/rnaseq_managed-agents

# Gingeras CSHL
curl -C - -O -L https://www.encodeproject.org/files/ENCFF001REK/@@download/ENCFF001REK.fastq.gz
curl -C - -O -L https://www.encodeproject.org/files/ENCFF001REJ/@@download/ENCFF001REJ.fastq.gz
curl -C - -O -L https://www.encodeproject.org/files/ENCFF001REI/@@download/ENCFF001REI.fastq.gz
curl -C - -O -L https://www.encodeproject.org/files/ENCFF001REH/@@download/ENCFF001REH.fastq.gz

# Wold Caltech
curl -C - -O -L https://www.encodeproject.org/files/ENCFF001RVY/@@download/ENCFF001RVY.fastq.gz
curl -C - -O -L https://www.encodeproject.org/files/ENCFF001RVR/@@download/ENCFF001RVR.fastq.gz
curl -C - -O -L https://www.encodeproject.org/files/ENCFF001RVS/@@download/ENCFF001RVS.fastq.gz
curl -C - -O -L https://www.encodeproject.org/files/ENCFF001RVW/@@download/ENCFF001RVW.fastq.gz
```

Then organise into the folder structure above:

```bash
mkdir -p ~/Projects/rnaseq_managed-agents/gingeras_cshl/raw_data/R1
mkdir -p ~/Projects/rnaseq_managed-agents/gingeras_cshl/raw_data/R2
mkdir -p ~/Projects/rnaseq_managed-agents/wold_caltech/raw_data/R1
mkdir -p ~/Projects/rnaseq_managed-agents/wold_caltech/raw_data/R2

mv ENCFF001REK.fastq.gz ~/Projects/rnaseq_managed-agents/gingeras_cshl/raw_data/R1/
mv ENCFF001REI.fastq.gz ~/Projects/rnaseq_managed-agents/gingeras_cshl/raw_data/R1/
mv ENCFF001REJ.fastq.gz ~/Projects/rnaseq_managed-agents/gingeras_cshl/raw_data/R2/
mv ENCFF001REH.fastq.gz ~/Projects/rnaseq_managed-agents/gingeras_cshl/raw_data/R2/

mv ENCFF001RVY.fastq.gz ~/Projects/rnaseq_managed-agents/wold_caltech/raw_data/R1/
mv ENCFF001RVS.fastq.gz ~/Projects/rnaseq_managed-agents/wold_caltech/raw_data/R1/
mv ENCFF001RVR.fastq.gz ~/Projects/rnaseq_managed-agents/wold_caltech/raw_data/R2/
mv ENCFF001RVW.fastq.gz ~/Projects/rnaseq_managed-agents/wold_caltech/raw_data/R2/
```

### Downloading the metadata

```bash
mkdir -p ~/Projects/rnaseq_managed-agents/gingeras_cshl/metadata
mkdir -p ~/Projects/rnaseq_managed-agents/wold_caltech/metadata

curl -o ~/Projects/rnaseq_managed-agents/gingeras_cshl/metadata/ENCSR000AED.json \
  "https://www.encodeproject.org/experiments/ENCSR000AED/?format=json"

curl -o ~/Projects/rnaseq_managed-agents/wold_caltech/metadata/ENCSR000AEG.json \
  "https://www.encodeproject.org/experiments/ENCSR000AEG/?format=json"
```

### Subsampling

Full FASTQ files are subsampled to 3 million reads per file for local development. 3M reads is sufficient for meaningful differential expression results with Kallisto.

Install seqtk:

```bash
brew install seqtk
```

Run subsampling (seed 42 must be identical across all R1/R2 pairs to preserve read pairing):

```bash
cd ~/Projects/rnaseq_managed-agents

# Gingeras CSHL
seqtk sample -s42 gingeras_cshl/raw_data/R1/ENCFF001REK.fastq.gz 3000000 | gzip > gingeras_cshl/raw_data/R1/ENCFF001REK_3M.fastq.gz
seqtk sample -s42 gingeras_cshl/raw_data/R2/ENCFF001REJ.fastq.gz 3000000 | gzip > gingeras_cshl/raw_data/R2/ENCFF001REJ_3M.fastq.gz
seqtk sample -s42 gingeras_cshl/raw_data/R1/ENCFF001REI.fastq.gz 3000000 | gzip > gingeras_cshl/raw_data/R1/ENCFF001REI_3M.fastq.gz
seqtk sample -s42 gingeras_cshl/raw_data/R2/ENCFF001REH.fastq.gz 3000000 | gzip > gingeras_cshl/raw_data/R2/ENCFF001REH_3M.fastq.gz

# Wold Caltech
seqtk sample -s42 wold_caltech/raw_data/R1/ENCFF001RVY.fastq.gz 3000000 | gzip > wold_caltech/raw_data/R1/ENCFF001RVY_3M.fastq.gz
seqtk sample -s42 wold_caltech/raw_data/R2/ENCFF001RVR.fastq.gz 3000000 | gzip > wold_caltech/raw_data/R2/ENCFF001RVR_3M.fastq.gz
seqtk sample -s42 wold_caltech/raw_data/R1/ENCFF001RVS.fastq.gz 3000000 | gzip > wold_caltech/raw_data/R1/ENCFF001RVS_3M.fastq.gz
seqtk sample -s42 wold_caltech/raw_data/R2/ENCFF001RVW.fastq.gz 3000000 | gzip > wold_caltech/raw_data/R2/ENCFF001RVW_3M.fastq.gz
```

Sanity check — read counts should match exactly between R1 and R2 for each pair:

```bash
zcat gingeras_cshl/raw_data/R1/ENCFF001REK_3M.fastq.gz | echo "R1: $(($(wc -l)/4)) reads"
zcat gingeras_cshl/raw_data/R2/ENCFF001REJ_3M.fastq.gz | echo "R2: $(($(wc -l)/4)) reads"
```