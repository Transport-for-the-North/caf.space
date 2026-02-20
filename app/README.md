# CAF.Space Dash App

Web UI for running **spatial zone translations** between two zoning systems. 

## Running the app

1. **Install dependencies** (from the project root):

   ```bash
   pip install -e .
   pip install -r app/requirements.txt
   ```

2. **Start the app** (from the project root):

   ```bash
   python app/app.py
   ```

3. Open the URL shown in the terminal (e.g. `http://127.0.0.1:8050`) in your browser.

## Using the app

- **Cache Path** — Directory for translation cache/output. Optional; defaults to the current directory if left empty or invalid.
- **Output Folder** — If set, used as the output directory, defaults to the current directory if left empty or invalid.

- **Zone 1 / Zone 2** — For each zone system:
  - **Shapefile** — Full path to the `.shp` file (type or paste the path).
  - **Zone system name** — Short label for the zone system (e.g. `MSOAs`, `Wards`).
  - **ID Column Name** — Dropdown is filled automatically after you enter a valid shapefile path; choose the column that uniquely identifies each zone.

- **Run translation** — Click once when all required fields are filled.

- **Translation output** — Shows either the path to the saved CSV or an error message. The CSV is written under the chosen output directory in a folder named `{zone1}_{zone2}` as `{zone1}_to_{zone2}_spatial.csv`.

## Requirements

- Python 3.13
- Project and app dependencies (see root `requirements.txt` and `app/requirements.txt`). The app uses the `caf.space` package from the repo, so install from root with `pip install -e .` before the app requirements.
