"""Generate sample_sales.csv for demo purposes."""

import pandas as pd
import numpy as np
import os

np.random.seed(42)
n = 500

months = pd.date_range("2022-01-01", periods=n, freq="D")
regions = np.random.choice(["North", "South", "East", "West"], n, p=[0.3, 0.25, 0.25, 0.2])
channels = np.random.choice(["Online", "Retail", "Wholesale"], n, p=[0.5, 0.3, 0.2])

# Simulate declining sales trend with noise
base_sales = 10000 - np.linspace(0, 3000, n) + np.random.normal(0, 800, n)
discount = np.random.uniform(0, 0.4, n)
sales = base_sales * (1 - discount * 0.5)

# Correlated: high discount → higher units sold
units = (sales / 15 + discount * 200 + np.random.normal(0, 30, n)).clip(0)

# Customer satisfaction: declines slightly over time
satisfaction = np.clip(4.5 - np.linspace(0, 1, n) + np.random.normal(0, 0.3, n), 1, 5)

df = pd.DataFrame({
    "date": months.strftime("%Y-%m-%d"),
    "region": regions,
    "channel": channels,
    "sales_usd": sales.round(2),
    "units_sold": units.astype(int),
    "discount_rate": discount.round(3),
    "customer_satisfaction": satisfaction.round(2),
    "marketing_spend": (sales * np.random.uniform(0.05, 0.15, n)).round(2),
    "returns": (units * np.random.uniform(0.01, 0.1, n)).astype(int),
})
# Introduce some missing values
df.loc[df.sample(frac=0.03).index, "customer_satisfaction"] = None
df.loc[df.sample(frac=0.02).index, "marketing_spend"] = None

out = os.path.join(os.path.dirname(__file__), "sample_sales.csv")
df.to_csv(out, index=False)
print(f"Saved {len(df)} rows → {out}")
