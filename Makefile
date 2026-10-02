.PHONY: all fetch repeat gates clean

all:
	python -m pipeline.run_all

# VIX is pinned to the upstream commit whose file matches data/raw/manifest_vix.json's sha256: the
# source's `main` updates daily, so an unpinned fetch drifts past 2026-09-11 (measured 2026-10-02).
VIX_URL = https://raw.githubusercontent.com/datasets/finance-vix/dfa11a56046c1a7fe5315e93aebf3232373f6674/data/vix-daily.csv

fetch:
	python -m pipeline.units.fetch_vix --in $(VIX_URL) --out data/raw/vix_daily.parquet
	python -m pipeline.units.fetch_oanda --in SPX500_USD --out data/raw/oanda_SPX500_USD.parquet
	python -m pipeline.units.fetch_oanda_xau --out data/raw/oanda_XAU_USD.parquet
	for i in SPXUSD GRXEUR ETXEUR JPXJPY; do python -m pipeline.units.fetch_histdata --in $$i --out data/raw/histdata_$$i.parquet; done
	python -m pipeline.units.fetch_bigmovers --in spy --out data/raw/spy_daily.parquet
	python -m pipeline.units.fetch_bigmovers --in stocks --out data/raw/stocks_daily.parquet
	python -m pipeline.units.fetch_etf_kaggle --in ETFs --out data/raw/etf_daily_kaggle.parquet

gates:
	python -m pipeline.sessions oanda data/raw/oanda_SPX500_USD.parquet
	python -m pipeline.sessions histdata data/raw/histdata_SPXUSD.parquet
	python -m pipeline.reproduce

# D7: a second full run must produce byte-identical outputs
repeat:
	rm -rf out_repeat && cp -r out out_repeat
	python -m pipeline.run_all
	diff -r out out_repeat && echo "REPEAT: byte-identical"

clean:
	rm -rf out out_repeat
