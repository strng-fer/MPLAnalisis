# Publishing checklist

Two targets: GitHub (code + data) and Kaggle (data only). Both are one-time
credential setups followed by repeatable commands.

## GitHub

### 1. Authenticate once

Option A — GitHub CLI, interactive browser login:

```powershell
gh auth login          # GitHub.com -> HTTPS -> login with a browser
```

Option B — personal access token (fine-grained, scope `repo`):

```powershell
$env:GH_TOKEN = "ghp_xxx"
```

Option C — plain git with a token in the remote URL (no `gh` needed):

```powershell
git remote add origin https://<token>@github.com/<user>/MPLAnalisis.git
```

### 2. Create the repository and push

```powershell
# with gh, this creates the repo and sets the remote in one step
gh repo create MPLAnalisis --public --source . --remote origin --push
```

Without `gh`:

```powershell
git remote add origin https://github.com/<user>/MPLAnalisis.git
git branch -M main
git push -u origin main
```

### 3. Repository settings worth changing after the first push

- **Description:** `MPL Indonesia esports dataset + scraper: drafts, hero pools, match stats, standings`
- **Topics:** `esports`, `mobile-legends`, `mpl`, `dataset`, `web-scraping`, `sports-analytics`
- **About → Website:** link to the Kaggle dataset once published
- Keep Actions enabled; `CI` runs the 84 tests on Linux and Windows

### 4. Later updates

```powershell
python -m mplid --out ./data --refresh     # refresh the data
pytest -q                                  # verify
git add -A
git commit -m "data: refresh season 18 through <date>"
git push
```

## Kaggle

### 1. Credentials

Create an API token at <https://www.kaggle.com/settings> → *Create New Token*.
This downloads `kaggle.json`. Put it at:

```
C:\Users\<you>\.kaggle\kaggle.json
```

or export the values:

```powershell
$env:KAGGLE_USERNAME = "your-username"
$env:KAGGLE_KEY      = "your-api-key"
```

### 2. Fix the dataset id

`kaggle/dataset-metadata.json` ships with `"id": "strng-fer/mpl-indonesia-s18"`.
Change the owner part to your Kaggle username if it differs. The publish script
rewrites it from the environment, but the committed file should be correct too.

### 3. Validate, stage, publish

```powershell
python kaggle/publish.py --check          # 21 tables, row counts, metadata
python kaggle/publish.py --zip            # dist/mpl-indonesia-s18.zip for manual upload
python kaggle/publish.py --upload         # first publish: creates the dataset
python kaggle/publish.py --upload --version   # later: adds a new version
```

Manual alternative: upload `dist/mpl-indonesia-s18.zip` at
<https://www.kaggle.com/datasets> → *New Dataset*.

### 4. After publishing

- Set the dataset to **public** and pick `CC BY 4.0` as the licence.
- Copy the dataset URL into `README.md` and `kaggle/README.md`.
- Attach `notebooks/01_explore.ipynb` to the dataset so the starter analysis
  appears in the notebook tab.

### 5. Refreshing later

```powershell
python -m mplid --out ./data --refresh
python kaggle/publish.py --upload --version
```

## What is inside the Kaggle staging directory

`kaggle/publish.py` copies `data/mpl-*.csv`, `manifest.json`, `data-quality.md`,
`data-quality.json`, the dataset card as `README.md`, and a rewritten
`dataset-metadata.json`. That is 26 files, 133 KB zipped.

The staging directory `kaggle/_staging/` is gitignored; only the metadata and the
card are versioned.
