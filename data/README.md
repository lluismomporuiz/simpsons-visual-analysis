# Data

Source: [The Simpsons Dataset](https://www.kaggle.com/datasets/prashant111/the-simpsons-dataset) on Kaggle
(Prashant Banerjee). The dataset has four files; this project uses two of them.

| File | Derived from | Description |
|---|---|---|
| `simpsons-episodes-clean.csv` | `simpsons_episodes.csv` | Episode data after cleaning with OpenRefine (596 rows, 8 columns). Used by both dashboards. **Included.** |
| `simpsons-script-lines-clean.csv` | `simpsons_script_lines.csv` | Cleaned script lines (~140k rows, 29 MB). Needed only by the scripts dashboard. **Not included.** |

The script lines are copyrighted dialogue, so the cleaned file is not redistributed in this repository. To
run the scripts dashboard, download the original dataset from Kaggle, prepare the cleaned file and place it
in this folder as `simpsons-script-lines-clean.csv`. Check the dataset's licence and terms on its Kaggle page
before redistributing any derivative of it.