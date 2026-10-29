# Time-series sales forecasting

Task 1 explores Olist purchase records, prepares a daily merchandise-value series, and compares a seasonal-naive forecast with a tuned random forest for the next seven days.

The analysis is in [the notebook](notebooks/1-sales-forecasting-preprocessing-analysis.ipynb). See [the review](docs/notebook-analysis.md) for methodology and limitations.

## Run the analysis

1. Open the notebook in Kaggle or Google Colab.
2. On Kaggle, attach the Olist dataset as an input. On Colab, upload `olist_orders_dataset.csv` and `olist_order_items_dataset.csv` when prompted.
3. Run all cells in order. Install packages from `requirements.txt` if the environment lacks them.
4. Download the generated `olist_task1_outputs.zip` using the final cell.

The current notebook discovers data under `/kaggle/input` or `/content`; it does not automatically use this repository's local `data/` folder. For a local run, adapt `ROOT`, `OUT`, and the archive destination to writable local paths before execution.

## Data and target

`data/` contains the nine supplied Olist CSV files. Only orders and order items are required by this notebook; the remaining tables support future work.

The target is the daily sum of item prices in BRL by purchase date, excluding freight. It includes every order status with usable item values, so it measures recorded merchandise value rather than net revenue. The analysis window is January 2017 through August 2018.

Source: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Consult the source for licensing and attribution terms before redistributing or publishing the data.

Database design, APIs, and deployment forecasting scripts are outside the current notebook's scope.
