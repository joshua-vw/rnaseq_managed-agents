# RNA-seq Managed Agents

Multi-agent orchestration for differential gene expression pipeline monitoring, built around GenPipes RNA-seq Light (C3G, McGill). Agents are coordinated using Anthropic's Managed Agents framework.

**Author:** Joshua Virani-Wall
**Contact:** joshuajamesvw@gmail.com

---

## Project Overview

This project investigates how variation in wetlab protocol — RNA extraction method, library fragmentation, and sequencing platform — propagates into systematic gene expression differences. It uses publicly available ENCODE RNA-seq data from the GM12878 human cell line, where the same biological sample was independently processed by two labs using distinct protocols (Gingeras/CSHL and Wold/Caltech).

---

## Environment Setup

### Prerequisites
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or Anaconda installed

- [Anthropic CLI](https://github.com/anthropics/anthropic-cli) installed via Homebrew:
```bash
  brew install anthropics/tap/ant
```

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
│   │   │   ├── ENCFF001REK.fastq.gz   # replicate 1, R1 (7.31 GB)
│   │   │   └── ENCFF001REI.fastq.gz   # replicate 2, R1 (7.01 GB)
│   │   └── R2/
│   │       ├── ENCFF001REJ.fastq.gz   # replicate 1, R2 (7.48 GB)
│   │       └── ENCFF001REH.fastq.gz   # replicate 2, R2 (7.18 GB)
│   └── metadata/
│       └── ENCSR000AED.json
└── wold_caltech/
    ├── raw_data/
    │   ├── R1/
    │   │   ├── ENCFF001RVY.fastq.gz   # replicate 1, R1 (7.85 GB)
    │   │   └── ENCFF001RVS.fastq.gz   # replicate 2, R1 (7.64 GB)
    │   └── R2/
    │       ├── ENCFF001RVR.fastq.gz   # replicate 1, R2 (7.64 GB)
    │       └── ENCFF001RVW.fastq.gz   # replicate 2, R2 (7.86 GB)
    └── metadata/
        └── ENCSR000AEG.json
```

Total download size: ~59 GB

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