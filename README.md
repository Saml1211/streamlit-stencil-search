# Visio Stencil Search

A lightweight Streamlit application to catalog and search for shapes in Visio stencil files across network directories.

## Features

- Network directory scanning for Visio stencil files (.vss, .vssx, .vssm)
- Search functionality to find shapes and their corresponding stencils
- Zero Visio dependencies - works without Visio installation

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
streamlit run app/Home.py
```

## Project Structure

```
streamlit-stencil-search/
├── app/
│   ├── pages/            # Additional pages for the Streamlit app
│   ├── core/             # Business logic
│   └── Home.py           # Main entry point for Streamlit
├── data/                 # Directory for cached stencil data
├── docs/                 # Documentation
└── requirements.txt      # Python dependencies
```

## Documentation

See the [requirements document](docs/requirements.md) for detailed project specifications. 